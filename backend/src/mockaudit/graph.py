"""The audit: one LangGraph StateGraph (spec Phase 3; proposal §4).

load_specs → dispatch_controls (Send × N) → control [population_check → run_checks → sample → tester → finalize]
→ await_controls → skeptic_one (Send per draft finding) → route_after_skeptic (max 1 revise round, re-entering the
control subgraph at `tester`) → severity → human_review (interrupt, or skipped) → report.

Code sets every count, date, severity and id. The only LLM nodes are `tester` and `skeptic_one`.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime
from langgraph.types import RetryPolicy, Send, interrupt

from mockaudit.checks import run_control_checks
from mockaudit.checks_only import findings_from_candidates
from mockaudit.citations import check_citations
from mockaudit.evidence import Evidence
from mockaudit.schemas import (
    Candidate,
    ControlResult,
    ControlSpec,
    Coverage,
    Dismissal,
    Finding,
    ReasoningStep,
    RunConfig,
    TesterOutput,
)
from mockaudit.severity import severity
from mockaudit.specs import load_controls

log = logging.getLogger("mockaudit.graph")
MAX_REVISE_ROUNDS = 1


@dataclass
class AuditContext:
    """Per-run runtime context (not checkpointed)."""
    data_dir: Path
    run_dir: Path
    models: Any = None             # .tester() / .skeptic() → chat models; None for checks-only
    spend: Any = None              # mockaudit.llm.Spend
    timeout_s: float = 420
    sample_cap: int = 25


# ---------- reducers ----------

def merge_dict(old: dict | None, new: dict | None) -> dict:
    return {**(old or {}), **(new or {})}


def merge_findings(old: dict | None, new: dict | None) -> dict:
    """Merge by finding_id. A draft can't overwrite a finding that was already reviewed (kept, rejected …)."""
    out = dict(old or {})
    for fid, f in (new or {}).items():
        prev = out.get(fid)
        if prev is not None and prev["status"] != "draft" and f["status"] == "draft":
            log.info("ignored a draft for %s: it is already %s", fid, prev["status"])
            continue
        out[fid] = f
    return out


class AuditState(TypedDict, total=False):
    config: dict
    specs: list[dict]
    results: Annotated[dict, merge_dict]          # control_id → ControlResult (without findings)
    findings: Annotated[dict, merge_findings]     # finding_id → Finding
    dismissals: Annotated[dict, merge_dict]       # candidate_id → Dismissal
    verdicts: Annotated[dict, merge_dict]         # "<finding_id>#r<round>" → verdict
    revise_round: int
    decisions: dict
    report: dict


class ControlState(TypedDict, total=False):
    spec: dict
    config: dict
    revise: dict                   # finding_id → {test_step, reason, condition} (revise re-entry)
    prior_drafts: dict             # finding_id → the draft being revised
    prior_result: dict             # the control's result from the first pass
    candidates: list[dict]
    notes: list[str]
    check_results: list[dict]
    tested: dict
    samples: dict
    code_findings: list[dict]
    drafts: list[dict]
    dismissed: list[dict]
    owner_questions: list[dict]
    tester_meta: dict
    result: dict
    findings: dict
    dismissals: dict


# ---------- control subgraph ----------

def _spec(state) -> ControlSpec:
    return ControlSpec.model_validate(state["spec"])


def _ev(state, runtime: Runtime[AuditContext]) -> Evidence:
    return Evidence.load(_spec(state), runtime.context.data_dir)


def _population_steps(spec: ControlSpec) -> set[str]:
    return {s.id for s in spec.test_recipe if s.check and s.gap_type == "population_completeness"}


def population_check(state: ControlState, runtime: Runtime[AuditContext]) -> dict:
    """Reconcile the population against its independent source; list missing items."""
    spec = _spec(state)
    cc = run_control_checks(spec, _ev(state, runtime), only=_population_steps(spec))
    return {"candidates": [c.model_dump() for c in cc.candidates], "notes": cc.notes,
            "check_results": [r.model_dump() for r in cc.results], "tested": cc.tested}


def run_checks(state: ControlState, runtime: Runtime[AuditContext]) -> dict:
    """Every other recipe check over the full population. `judge: none` failures become code findings."""
    spec = _spec(state)
    others = {s.id for s in spec.test_recipe if s.check} - _population_steps(spec)
    cc = run_control_checks(spec, _ev(state, runtime), only=others)
    cands = state.get("candidates", []) + [c.model_dump() for c in cc.candidates]
    tested = {**state.get("tested", {}), **cc.tested}
    code = []
    for step in spec.test_recipe:
        mine = [Candidate.model_validate(c) for c in cands if c["test_step"] == step.id]
        if mine and step.judge == "none":
            f = findings_from_candidates(spec, step.id, mine, tested[step.id])
            if state["config"]["mode"] != "checks_only":
                f.status = "draft"      # the skeptic reviews every finding (Phase 3 ruling)
            code.append(f.model_dump())
    return {"candidates": cands, "tested": tested, "notes": state.get("notes", []) + cc.notes,
            "check_results": state.get("check_results", []) + [r.model_dump() for r in cc.results],
            "code_findings": code}


def sample(state: ControlState, runtime: Runtime[AuditContext]) -> dict:
    """Judgment-only steps: every item up to the cap, else a seeded random sample."""
    spec, ev = _spec(state), _ev(state, runtime)
    samples = {}
    for step in spec.test_recipe:
        if step.check is not None or "source" not in step.params:
            continue
        src = step.params["source"]
        ids = sorted(ev.rid(src, r) for r in ev.rows(src) if r.get("ID", "").startswith(step.params.get("prefix", "")))
        if len(ids) > runtime.context.sample_cap:
            ids = sorted(random.Random(f"{spec.control_id}:{step.id}").sample(ids, runtime.context.sample_cap))
        samples[step.id] = ids
    return {"samples": samples}


def _resolve(ref: str, cands: list[Candidate], step: str | None = None) -> str | None:
    """Map what the model wrote (candidate id or a cited record id) to a candidate id."""
    for c in cands:
        if (step is None or c.test_step == step) and (ref in (c.candidate_id, c.record_id) or ref.endswith("-" + c.record_id)):
            return c.candidate_id
    return None


def tester_findings(spec: ControlSpec, out: TesterOutput, cands: list[Candidate], tested: dict, samples: dict,
                    revise: dict, steps: list[ReasoningStep]) -> tuple[list[Finding], list[Dismissal]]:
    """Turn the tester's judgment into findings. Code sets ids, counts and types; the LLM supplied the words."""
    decided = {}
    for d in out.decisions:
        cid = _resolve(d.candidate_id, cands)
        if cid:
            decided[cid] = d
    dismissed = {cid for cid, d in decided.items() if d.decision == "dismiss"}
    raised = {c.candidate_id for c in cands} - dismissed        # undecided candidates stay raised
    recipe = {s.id: s for s in spec.test_recipe}
    revise_by_step = {v["test_step"]: fid for fid, v in (revise or {}).items()}
    findings, covered = [], set()
    for fd in out.findings:
        step = fd.test_step if fd.test_step in recipe else None
        refs = fd.candidate_ids + [c.record_id for c in fd.citations]
        if step is None:
            step = next((c.test_step for r in refs for c in cands if _resolve(r, [c])), None)
        if step is None or (revise and step not in revise_by_step):
            continue
        if recipe[step].check:
            ids = sorted({x for r in refs if (x := _resolve(r, cands, step))} & raised)
            if not ids:
                continue
            covered |= set(ids)
            exceptions, n = len(ids), tested.get(step, len(ids))
        elif step in samples:
            exceptions = max(1, len({c.record_id for c in fd.citations} & set(samples[step])))
            n = len(samples[step])
        else:
            continue
        cites = list(fd.citations)
        if recipe[step].check:          # add the code-verified citations of the covered candidates
            seen = {(c.source, c.record_id) for c in cites}
            for c in cands:
                if c.candidate_id in ids:
                    cites += [x for x in c.citations if (x.source, x.record_id) not in seen
                              and not seen.add((x.source, x.record_id))]
        fid = revise_by_step.get(step) or f"{spec.control_id}-{step}"
        if any(f.finding_id == fid for f in findings):
            fid = f"{fid}-{sum(f.finding_id.startswith(fid) for f in findings) + 1}"
        sev, rule = severity(recipe[step].gap_type, exceptions, n, spec.risk, spec.periodic)
        findings.append(Finding(
            finding_id=fid, control_id=spec.control_id, test_step=step, gap_type=recipe[step].gap_type,
            exceptions=exceptions, tested=n, condition=fd.condition, criteria=fd.criteria, cause=fd.cause,
            effect=fd.effect, recommendation=fd.recommendation, citations=cites, severity=sev,
            severity_rule=rule, status="draft", reasoning=list(steps)))
    if not revise:      # raised candidates the tester didn't write up still become findings (code template)
        for step in recipe:
            left = [c for c in cands if c.test_step == step and c.candidate_id in raised - covered]
            if left and not any(f.test_step == step for f in findings):
                f = findings_from_candidates(spec, step, left, tested.get(step, len(left)))
                f.status, f.reasoning = "draft", list(steps) + [ReasoningStep(kind="rule", text="raised by default: no tester write-up")]
                findings.append(f)
    dismissals = [Dismissal(candidate_id=cid, control_id=spec.control_id, reason=decided[cid].reason,
                            citations=decided[cid].citations, reasoning=list(steps)) for cid in sorted(dismissed)]
    return findings, dismissals


async def tester(state: ControlState, runtime: Runtime[AuditContext]) -> dict:
    """LLM node: raise or dismiss each candidate; judge judgment-only steps. Checks-only: raise everything."""
    spec, cfg = _spec(state), RunConfig.model_validate(state["config"])
    recipe = {s.id: s for s in spec.test_recipe}
    cands = [Candidate.model_validate(c) for c in state.get("candidates", []) if recipe[c["test_step"]].judge == "llm"]
    samples = state.get("samples", {})
    revise = state.get("revise") or {}
    if revise:
        steps_to_redo = {v["test_step"] for v in revise.values()}
        cands = [c for c in cands if c.test_step in steps_to_redo]
        samples = {k: v for k, v in samples.items() if k in steps_to_redo}
    if cfg.mode == "checks_only":
        code = [findings_from_candidates(spec, s, [c for c in cands if c.test_step == s], state["tested"][s]).model_dump()
                for s in recipe if any(c.test_step == s for c in cands)]
        return {"drafts": code, "dismissed": [], "tester_meta": {"model": "none"}}
    if not cands and not samples:
        return {"drafts": [], "dismissed": [], "tester_meta": {"model": "none (nothing to judge)"}}

    from mockaudit.agents import make_tools, reasoning_from_messages, run_tester, tester_message
    from mockaudit.llm import SpendCallback

    ctx = runtime.context
    ctx.spend.guard()
    ev = _ev(state, runtime)
    owner_log: list[dict] = []
    model = ctx.models.tester()
    message = tester_message(spec, cands, samples, state.get("notes", []), revise)
    out, msgs, retries = await run_tester(model, spec, make_tools(spec, ev, ctx.data_dir, owner_log), message,
                                          [SpendCallback(ctx.spend, "tester", spec.control_id)])
    if out is None:
        raise ValueError("tester returned no structured output")
    steps = [ReasoningStep(kind="check", text=f"{c.test_step}: {c.detail}") for c in cands[:10]] + reasoning_from_messages(msgs)
    findings, dismissals = tester_findings(spec, out, cands, state.get("tested", {}), samples, revise, steps)
    return {"drafts": [f.model_dump() for f in findings], "dismissed": [d.model_dump() for d in dismissals],
            "owner_questions": owner_log,
            "tester_meta": {"model": getattr(model, "model_name", type(model).__name__), "retries": retries}}


def finalize(state: ControlState, runtime: Runtime[AuditContext]) -> dict:
    """Citation check (drop and log), coverage, and the control result."""
    spec, cfg = _spec(state), RunConfig.model_validate(state["config"])
    index = _ev(state, runtime).index()
    findings, dropped = {}, []
    for f in [Finding.model_validate(x) for x in (state.get("code_findings", []) if not state.get("revise") else [])
              + state.get("drafts", [])]:
        kept, gone = check_citations(f.citations, index, f.finding_id)
        dropped += gone
        if not kept:
            log.warning("%s dropped: no valid citation", f.finding_id)
            continue
        f.citations = kept
        if cfg.mode == "checks_only" and f.status == "draft":
            f.status = "kept"
        findings[f.finding_id] = f.model_dump()
    dismissals = {}
    for d in [Dismissal.model_validate(x) for x in state.get("dismissed", [])]:
        kept, gone = check_citations(d.citations, index, d.candidate_id)
        dropped += gone
        if kept:
            d.citations = kept
            dismissals[d.candidate_id] = d.model_dump()
    if state.get("revise"):
        for fid, f in (state.get("prior_drafts") or {}).items():
            if fid not in findings:
                step = ReasoningStep(kind="llm", text="tester dismissed this finding's items on revision").model_dump()
                findings[fid] = dict(f, status="dismissed", reasoning=f["reasoning"] + [step])
        return {"findings": findings, "dismissals": dismissals,
                "result": {"dropped_citations": [c.model_dump() for c in dropped], "revision_round": 1}}
    cands = [Candidate.model_validate(c) for c in state.get("candidates", [])]
    missing = [c.record_id for c in cands if c.gap_type == "population_completeness"]
    judgment = [s.id for s in spec.test_recipe if not s.check]
    not_tested = ([{"step_id": s, "reason": "judgment-only step (checks-only mode)"} for s in judgment]
                  if cfg.mode == "checks_only" else [])
    result = ControlResult(
        control_id=spec.control_id, status="exceptions" if findings else "pass",
        population_size=max(state.get("tested", {}).values(), default=0), population_complete=not missing,
        missing_from_population=missing, notes=state.get("notes", []), candidates=cands,
        tested_counts=state.get("tested", {}), samples=state.get("samples", {}),
        sample=sorted({i for ids in state.get("samples", {}).values() for i in ids}),
        dropped_citations=dropped, check_results=state.get("check_results", []),
        coverage=Coverage(tested=[s.id for s in spec.test_recipe if s.check or cfg.mode != "checks_only"],
                          not_tested=not_tested),
        owner_questions=state.get("owner_questions", []), agent="checks-only" if cfg.mode == "checks_only" else "default",
        model=state.get("tester_meta", {}).get("model", ""), run_id=cfg.run_id)
    return {"findings": findings, "dismissals": dismissals, "result": result.model_dump(exclude={"findings", "dismissals"})}


TRANSIENT = {"TooManyRequestsResponseError", "InternalServerResponseError", "ServiceUnavailableResponseError",
             "BadGatewayResponseError", "GatewayTimeoutResponseError", "ConnectError", "ReadTimeout", "RemoteProtocolError"}


def is_transient(exc: Exception) -> bool:
    """Provider rate limits and network blips are retried; schema failures and the spend cap are not."""
    return type(exc).__name__ in TRANSIENT


def build_control_graph():
    g = StateGraph(ControlState, context_schema=AuditContext)
    g.add_node("population_check", population_check)
    g.add_node("run_checks", run_checks)
    g.add_node("sample", sample)
    g.add_node("tester", tester, retry_policy=RetryPolicy(max_attempts=2, initial_interval=2.0, retry_on=is_transient))
    g.add_node("finalize", finalize)
    g.add_conditional_edges(START, lambda s: "tester" if s.get("revise") else "population_check",
                            ["tester", "population_check"])
    g.add_edge("population_check", "run_checks")
    g.add_edge("run_checks", "sample")
    g.add_edge("sample", "tester")
    g.add_edge("tester", "finalize")
    g.add_edge("finalize", END)
    return g.compile()


CONTROL_GRAPH = build_control_graph()


# ---------- parent graph ----------

def load_specs(state: AuditState, runtime: Runtime[AuditContext]) -> dict:
    cfg = RunConfig.model_validate(state["config"])
    specs = load_controls(runtime.context.data_dir / "controls.yaml")
    if cfg.controls:
        specs = [s for s in specs if s.control_id in cfg.controls]
    return {"specs": [s.model_dump(mode="json") for s in specs], "revise_round": 0}


def dispatch_controls(state: AuditState) -> list[Send]:
    return [Send("control", {"spec": s, "config": state["config"]}) for s in state["specs"]]


def _error_result(spec: dict, cfg: dict, error: str) -> dict:
    return ControlResult(control_id=spec["control_id"], status="error", error=error,
                         run_id=cfg["run_id"]).model_dump(exclude={"findings", "dismissals"})


async def control(state: ControlState, runtime: Runtime[AuditContext]) -> dict:
    """Runs the control subgraph. A timeout, exception or spend cap marks only this control as error."""
    cid = state["spec"]["control_id"]
    try:
        out = await asyncio.wait_for(CONTROL_GRAPH.ainvoke(state, context=runtime.context), runtime.context.timeout_s)
    except Exception as e:              # noqa: BLE001 - isolate the failure to this control
        name = type(e).__name__
        if name == "SpendCapExceeded":
            error = f"spend_cap: {e}"
        elif isinstance(e, TimeoutError):
            error = f"timeout after {runtime.context.timeout_s:g} s"
        else:
            error = f"{name}: {str(e)[:300]}"
        log.warning("control %s failed: %s", cid, error)
        if state.get("revise"):         # keep the first-pass result; the revised drafts become unresolved
            step = ReasoningStep(kind="rule", text=f"revision failed ({error}); left unresolved").model_dump()
            prior = state.get("prior_result") or {}
            return {"findings": {fid: dict(f, status="unresolved", reasoning=f["reasoning"] + [step])
                                 for fid, f in (state.get("prior_drafts") or {}).items()},
                    "results": {cid: dict(prior, notes=prior.get("notes", []) + [f"revise round failed: {error}"])}}
        return {"results": {cid: _error_result(state["spec"], state["config"], error)}}
    if state.get("revise"):
        return {"findings": out.get("findings", {}), "dismissals": out.get("dismissals", {})}
    return {"results": {cid: out["result"]}, "findings": out.get("findings", {}), "dismissals": out.get("dismissals", {})}


def await_controls(state: AuditState) -> dict:
    """Fan-in: waits for every control branch (deferred)."""
    return {}


def to_skeptic(state: AuditState) -> list[Send] | str:
    mode = state["config"]["mode"]
    drafts = [f for f in state.get("findings", {}).values() if f["status"] == "draft"]
    if mode in ("checks_only", "skeptic_off") or not drafts:
        return "severity"
    specs = {s["control_id"]: s for s in state["specs"]}
    return [Send("skeptic_one", {"finding": f, "spec": specs[f["control_id"]], "round": state.get("revise_round", 0)})
            for f in sorted(drafts, key=lambda f: f["finding_id"])]


async def skeptic_one(payload: dict, runtime: Runtime[AuditContext]) -> dict:
    """LLM node: one structured review of one draft finding."""
    from mockaudit.agents import skeptic_one as review
    from mockaudit.llm import SpendCallback

    f = Finding.model_validate(payload["finding"])
    spec = ControlSpec.model_validate(payload["spec"])
    key = f"{f.finding_id}#r{payload['round']}"
    ctx = runtime.context
    try:
        ctx.spend.guard()
        model = ctx.models.skeptic()
        out = await review(model, spec, Evidence.load(spec, ctx.data_dir), f,
                           [SpendCallback(ctx.spend, "skeptic", spec.control_id)])
        v = {"finding_id": f.finding_id, **out.model_dump(), "reviewer": f"skeptic:{getattr(model, 'model_name', type(model).__name__)}",
             "round": payload["round"]}
    except Exception as e:              # noqa: BLE001 - a failed review leaves the finding unresolved
        v = {"finding_id": f.finding_id, "decision": "error", "reason": f"{type(e).__name__}: {str(e)[:200]}",
             "checks_failed": [], "reviewer": "skeptic", "round": payload["round"]}
    return {"verdicts": {key: v}}


def route_after_skeptic(state: AuditState) -> dict:
    """Apply verdicts. `revise` gets one more tester pass; after that it is unresolved."""
    rnd = state.get("revise_round", 0)
    updates, revising = {}, False
    for fid, f in state.get("findings", {}).items():
        if f["status"] != "draft":
            continue
        v = state.get("verdicts", {}).get(f"{fid}#r{rnd}")
        decision = v["decision"] if v else "error"
        step = ReasoningStep(kind="llm", text=f"skeptic round {rnd}: {decision} — {(v or {}).get('reason', 'no verdict')}"[:300])
        new = dict(f, reasoning=f["reasoning"] + [step.model_dump()])
        if decision == "keep":
            new["status"] = "kept"
        elif decision == "reject":
            new["status"] = "rejected"
        elif decision == "revise" and rnd < MAX_REVISE_ROUNDS:
            revising = True
            continue                    # stays draft; the revise branch replaces it by finding_id
        else:
            new["status"] = "unresolved"
        updates[fid] = new
    return {"findings": updates, "revise_round": rnd + 1 if revising else rnd}


def after_route(state: AuditState) -> list[Send] | str:
    drafts = [f for f in state.get("findings", {}).values() if f["status"] == "draft"]
    if not drafts:
        return "severity"
    rnd = state["revise_round"] - 1
    by_control: dict[str, dict] = {}
    for f in drafts:
        v = state["verdicts"].get(f"{f['finding_id']}#r{rnd}", {})
        by_control.setdefault(f["control_id"], {})[f["finding_id"]] = {
            "test_step": f["test_step"], "reason": v.get("reason", ""), "condition": f["condition"]}
    specs = {s["control_id"]: s for s in state["specs"]}
    sends = []
    for cid, revise in sorted(by_control.items()):
        prior = state["results"][cid]
        drafts = {f["finding_id"]: f for f in state["findings"].values() if f["finding_id"] in revise}
        sends.append(Send("control", {"spec": specs[cid], "config": state["config"], "revise": revise,
                                      "prior_drafts": drafts, "prior_result": prior,
                                      "candidates": [c for c in prior.get("candidates", [])],
                                      "tested": prior.get("tested_counts", {}), "samples": prior.get("samples", {}),
                                      "notes": prior.get("notes", [])}))
    return sends


def severity_node(state: AuditState) -> dict:
    """The 7 rules (code). Findings with no skeptic pass (checks-only, skeptic-off) are kept as-is."""
    specs = {s["control_id"]: ControlSpec.model_validate(s) for s in state["specs"]}
    updates = {}
    for fid, f in state.get("findings", {}).items():
        if f["status"] == "rejected":
            continue
        spec = specs[f["control_id"]]
        sev, rule = severity(f["gap_type"], f["exceptions"], f["tested"], spec.risk, spec.periodic)
        step = ReasoningStep(kind="rule", text=f"severity rule {rule}: {f['gap_type']}, {f['exceptions']}/{f['tested']}, "
                                               f"{spec.risk}-risk control → {sev}")
        updates[fid] = dict(f, severity=sev, severity_rule=rule, status="kept" if f["status"] == "draft" else f["status"],
                            reasoning=[r for r in f["reasoning"] if not r["text"].startswith("severity rule")] + [step.model_dump()])
    return {"findings": updates}


def human_review(state: AuditState, runtime: Runtime[AuditContext]) -> dict:
    """interrupt() for approve/dismiss decisions; skipped when review_mode is skip."""
    if state["config"]["review_mode"] == "skip":
        return {}
    pending = [f for f in state["findings"].values() if f["status"] in ("kept", "unresolved")]
    request = {"run_id": state["config"]["run_id"],
               "instructions": "Set each decision to approve or dismiss, add a note if useful, then run "
                               "`mockaudit review --run <run_id> --decisions <this file>`.",
               "decisions": [{"finding_id": f["finding_id"], "control_id": f["control_id"], "severity": f["severity"],
                              "status": f["status"], "condition": f["condition"], "decision": "", "note": ""}
                             for f in sorted(pending, key=lambda f: f["finding_id"])]}
    req = runtime.context.run_dir / "review_request.json"
    if not req.exists():                # interrupt() re-runs this node on resume; don't clobber the edited file
        req.write_text(json.dumps(request, indent=2))
    answer = interrupt(request)
    decisions = {d["finding_id"]: d for d in (answer.get("decisions", []) if isinstance(answer, dict) else answer)}
    updates = {}
    for fid, d in decisions.items():
        if fid in state["findings"] and d.get("decision") in ("approve", "dismiss"):
            updates[fid] = dict(state["findings"][fid], status="approved" if d["decision"] == "approve" else "dismissed")
    return {"findings": updates, "decisions": decisions}


def report_node(state: AuditState, runtime: Runtime[AuditContext]) -> dict:
    from mockaudit.report import write_run
    return {"report": write_run(state, runtime.context)}


def build_graph() -> StateGraph:
    g = StateGraph(AuditState, context_schema=AuditContext)
    g.add_node("load_specs", load_specs)
    g.add_node("control", control, input_schema=ControlState)
    g.add_node("await_controls", await_controls, defer=True)
    g.add_node("skeptic_one", skeptic_one)
    g.add_node("route_after_skeptic", route_after_skeptic, defer=True)
    g.add_node("severity", severity_node)
    g.add_node("human_review", human_review)
    g.add_node("report", report_node)
    g.add_edge(START, "load_specs")
    g.add_conditional_edges("load_specs", dispatch_controls, ["control"])
    g.add_edge("control", "await_controls")
    g.add_conditional_edges("await_controls", to_skeptic, ["skeptic_one", "severity"])
    g.add_edge("skeptic_one", "route_after_skeptic")
    g.add_conditional_edges("route_after_skeptic", after_route, ["control", "severity"])
    g.add_edge("severity", "human_review")
    g.add_edge("human_review", "report")
    g.add_edge("report", END)
    return g

