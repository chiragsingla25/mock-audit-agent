"""The two LLM roles: `tester` (create_agent + ToolStrategy(TesterOutput)) and `skeptic_one`.

Code around them sets every count, date, severity and finding id. The LLM only judges.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_core.tools import StructuredTool

from mockaudit.evidence import Evidence
from mockaudit.schemas import (
    Candidate,
    ControlSpec,
    Finding,
    ReasoningStep,
    SkepticOutput,
    TesterOutput,
)

# ---------- tools (bound to one control's evidence) ----------


def make_tools(spec: ControlSpec, ev: Evidence, data_dir: Path, owner_log: list[dict]):
    answers = yaml.safe_load((Path(data_dir) / "answers.yaml").read_text())["owner_answers"]
    sources = [s.name for s in spec.evidence if s.role != "policy"]
    policies = {s.name: ev.data[s.name] for s in spec.evidence if s.role == "policy"}

    def get_record(source: str, record_id: str) -> str:
        """Fetch one record by id from one of this control's evidence sources."""
        if source not in sources:
            return json.dumps({"error": f"unknown source {source!r}; available: {sources}"})
        rec = ev.get(source, record_id)
        if rec is None:
            return json.dumps({"error": f"no {source} record {record_id!r}"})
        out = {"record": {k: v for k, v in rec.items() if k != "file"}}
        if source == "hr_roster":           # linked worker records and that person's Okta events
            out["linked_records"] = [r for r in ev.data[source] if r.get("prior_employee_id") == record_id
                                     or (rec.get("prior_employee_id") and r["employee_id"] == rec["prior_employee_id"])]
            if "okta_events" in ev.data:
                out["okta_events_for_user"] = [e for e in ev.data["okta_events"] if e["target_login"] == rec["email"]]
        return json.dumps(out, default=str)

    def read_policy(name: str) -> str:
        """Return the text of one of this control's policies."""
        return policies.get(name) or f"No policy {name!r}. Available: {sorted(policies)}"

    def ask_owner(question: str) -> str:
        """Ask the control owner a question. Mention the record ids you are asking about."""
        hits = [a["answer"] for a in answers if a["control_id"] == spec.control_id and any(r in question for r in a["record_ids"])]
        answer = " ".join(hits) or "I don't have anything more on that."
        owner_log.append({"q": question, "a": answer})
        return answer

    get_record.__doc__ += f" Sources: {', '.join(sources)}."
    read_policy.__doc__ += f" Policies: {', '.join(policies)}."
    return [StructuredTool.from_function(f) for f in (get_record, read_policy, ask_owner)]


# ---------- tester ----------

TESTER_PROMPT = """You are a skeptical SOC 2 Type II auditor testing control {cid}: "{desc}" (risk: {risk}).
Observation period {p0} to {p1}. Code has already run every check over the full population; its results are facts.
Never recompute hours, dates or counts. Your job is judgment:
1. For each candidate exception, look at the records (get_record), the policy (read_policy) and, if useful, ask the
   owner (ask_owner). Decide "raise" (a real exception) or "dismiss" (a valid, documented explanation exists).
   A delay or omission with no approved exception is NOT a valid explanation.
2. For each judgment-only step, inspect every listed item with get_record and raise a finding if the step's
   requirement is not met, citing the item id.
3. Write one finding per test step that has raised items, in auditor format (condition, criteria, cause, effect,
   recommendation). Cite only record ids you have seen, as {{"source": <source name>, "record_id": <id>}}.
Then return TesterOutput."""


def tester_message(spec: ControlSpec, candidates: list[Candidate], samples: dict[str, list[str]],
                   notes: list[str], revise: dict[str, dict] | None) -> str:
    steps = {s.id: s.description for s in spec.test_recipe}
    judgment = [{"test_step": sid, "requirement": steps[sid], "source": spec_step_source(spec, sid), "items": ids}
                for sid, ids in samples.items()]
    parts = [f"Recipe steps: {json.dumps(steps)}",
             "CANDIDATES_JSON:\n" + json.dumps([c.model_dump() for c in candidates], indent=1),
             "JUDGMENT_STEPS_JSON:\n" + json.dumps(judgment, indent=1)]
    if notes:
        parts.append("Notes from the checks (not exceptions): " + "; ".join(notes))
    if revise:
        parts.append("REVISE_JSON (the reviewer asked you to revise these findings; return a corrected finding for "
                     "the same test_step, or dismiss its candidates):\n" + json.dumps(revise, indent=1))
    return "\n\n".join(parts)


def spec_step_source(spec: ControlSpec, step_id: str) -> str | None:
    return next((s.params.get("source") for s in spec.test_recipe if s.id == step_id), None)


async def run_tester(model, spec: ControlSpec, tools, message: str, callbacks) -> tuple[TesterOutput | None, list, int]:
    """Tool loop with structured output. A schema failure is retried once with the error, then raised."""
    attempts = {"n": 0}

    def handle(exc):
        attempts["n"] += 1
        if attempts["n"] > 1:
            raise exc
        return f"Your TesterOutput failed validation: {exc}. Fix it and call TesterOutput again."

    p0, p1 = spec.period
    agent = create_agent(model, tools=tools, response_format=ToolStrategy(TesterOutput, handle_errors=handle),
                         system_prompt=TESTER_PROMPT.format(cid=spec.control_id, desc=spec.description, risk=spec.risk,
                                                            p0=p0, p1=p1))
    out = await agent.ainvoke({"messages": [{"role": "user", "content": message}]},
                              config={"callbacks": callbacks, "recursion_limit": 40, "run_name": f"tester:{spec.control_id}"})
    return out.get("structured_response"), out["messages"], attempts["n"]


def reasoning_from_messages(messages) -> list[ReasoningStep]:
    steps = []
    for m in messages:
        for call in getattr(m, "tool_calls", None) or []:
            if call["name"] == "TesterOutput":
                steps.append(ReasoningStep(kind="llm", text="tester decided and wrote the finding (structured output)"))
            else:
                kind = "owner" if call["name"] == "ask_owner" else "tool"
                args = ", ".join(f"{k}={v!r}" for k, v in call["args"].items())
                steps.append(ReasoningStep(kind=kind, text=f"{call['name']}({args})"[:200]))
    return steps


# ---------- skeptic ----------

SKEPTIC_PROMPT = """You are the audit senior reviewing one draft finding for control {cid}: "{desc}".
Period {p0} to {p1}. Counts and severity were computed by code; don't question arithmetic.
Check: do the cited records actually show the condition? Is it inside the period? Is there an innocent, documented
explanation in the records or the policy? Return keep, revise (a fixable problem; say exactly what) or reject."""


async def skeptic_one(model, spec: ControlSpec, ev: Evidence, finding: Finding, callbacks) -> SkepticOutput:
    cited = [{"source": c.source, "record_id": c.record_id,
              "record": {k: v for k, v in (ev.get(c.source, c.record_id) or {}).items() if k != "file"}}
             for c in finding.citations[:20]]
    policies = {s.name: ev.data[s.name] for s in spec.evidence if s.role == "policy"}
    p0, p1 = spec.period
    s = model.with_structured_output(SkepticOutput, method="function_calling", include_raw=True)
    out = await s.ainvoke(
        [{"role": "system", "content": SKEPTIC_PROMPT.format(cid=spec.control_id, desc=spec.description, p0=p0, p1=p1)},
         {"role": "user", "content": json.dumps({"finding": finding.model_dump(exclude={"reasoning"}),
                                                 "cited_records": cited, "policies": policies}, default=str)}],
        config={"callbacks": callbacks, "run_name": f"skeptic_one:{finding.finding_id}"})
    if out.get("parsed") is None:
        raise ValueError(f"skeptic output did not parse: {out.get('parsing_error')}")
    return out["parsed"]
