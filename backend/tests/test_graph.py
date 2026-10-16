"""Phase 3 criteria: the audit graph, run with stub LLMs (spec 2026-10-15-mock-audit-mvp §5, Phase 3)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from langgraph.checkpoint.memory import InMemorySaver
from stubs import SkepticScript, StubModels, TesterScript

from mockaudit.datagen.ledgerly import generate
from mockaudit.graph import build_graph, merge_findings
from mockaudit.runner import make_context, resume_audit, run_audit
from mockaudit.schemas import ControlResult, RunConfig
from mockaudit.scoring import evaluate_run

KINDS = {"check", "tool", "owner", "llm", "rule"}


@pytest.fixture(scope="module")
def data_root(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("ledgerly")
    generate("base", root)
    return root


@pytest.fixture(scope="module")
def key(data_root) -> dict:
    return yaml.safe_load((data_root / "base" / "answer_key.yaml").read_text())


def good_tester(key) -> TesterScript:
    """Dismisses the four traps, flags the judgment gaps G3/G10: what a perfect tester would do."""
    traps = {t["record_ids"][0] for t in key["traps"]}
    judgment = {r for g in key["gaps"] if g["tag"] == "judgment" for r in g["record_ids"]}
    return TesterScript(dismiss=traps, flag=judgment)


def cfg(run_id: str, **kw) -> RunConfig:
    return RunConfig(run_id=run_id, variant="base", mode=kw.pop("mode", "agent"), review_mode=kw.pop("review_mode", "skip"),
                     max_concurrency=kw.pop("max_concurrency", 4), **kw)


async def run(tmp_path, data_root, run_id, models, **kw) -> tuple[dict, Path]:
    out = await run_audit(cfg(run_id, **kw), data_root, tmp_path, models, spend_path=tmp_path / "spend.jsonl")
    return out, tmp_path / run_id


def results(run_dir: Path) -> dict[str, ControlResult]:
    return {p.stem: ControlResult.model_validate_json(p.read_text()) for p in (run_dir / "controls").glob("*.json")}


# ---------- criterion: --review skip produces 12 control results and a report ----------

@pytest.fixture(scope="module")
async def full_run(data_root, key, tmp_path_factory):
    tmp = tmp_path_factory.mktemp("runs")
    models = StubModels(good_tester(key))
    out, run_dir = await run(tmp, data_root, "full", models)
    return out, run_dir, models


async def test_review_skip_writes_12_results_and_report(full_run):
    out, run_dir, models = full_run
    assert out["status"] == "done"
    assert sorted(p.name for p in (run_dir / "controls").glob("*.json")) == sorted(f"C{i}.json" for i in range(1, 13))
    for name in ["report.md", "report.json", "verdicts.json", "run.json"]:
        assert (run_dir / name).is_file()
    md = (run_dir / "report.md").read_text()
    assert "Not an audit opinion" in md and "pass badge" not in md.lower()
    assert "stub-tester" in models.log and "stub-skeptic" in models.log


async def test_full_stub_run_scores_perfectly_with_a_perfect_tester(full_run):
    """End-to-end plumbing check: dismissing traps and flagging judgment gaps gives 10/10 and no false positives."""
    _, run_dir, _ = full_run
    m = evaluate_run(run_dir)["metrics"]
    assert m["recall"]["n"] == 10 and m["precision"]["value"] == 1.0
    assert m["clean_control_accuracy"]["value"] == 1.0 and m["traps_raised"]["n"] == 0
    assert m["severity_agreement"]["value"] == 1.0 and m["citation_validity"]["value"] == 1.0
    r = results(run_dir)
    assert {d.candidate_id for x in r.values() for d in x.dismissals} == {
        "C2-timeliness-E1083", "C1-approval-AR-0031", "C8-critical_sla-VULN-0028", "C9-pir-INC-22"}


# ---------- criterion: every finding and dismissal carries reasoning steps ----------

async def test_every_finding_and_dismissal_has_reasoning_steps(full_run):
    _, run_dir, _ = full_run
    r = results(run_dir)
    items = [f for x in r.values() for f in x.findings] + [d for x in r.values() for d in x.dismissals]
    assert items
    for item in items:
        kinds = {s.kind for s in item.reasoning}
        assert item.reasoning and kinds <= KINDS
    tester_found = next(f for f in r["C2"].findings if f.test_step == "timeliness")
    assert {"check", "tool", "llm", "rule"} <= {s.kind for s in tester_found.reasoning}
    code_found = next(f for f in r["C8"].findings if f.test_step == "weekly_scan")
    assert {"check", "rule"} <= {s.kind for s in code_found.reasoning}


# ---------- criterion: findings merge by finding_id; a revision keeps kept findings unchanged ----------

def test_merge_findings_reducer_never_lets_a_draft_overwrite_a_reviewed_finding():
    kept = {"f1": {"finding_id": "f1", "status": "kept", "condition": "original"}}
    assert merge_findings(kept, {"f1": {"finding_id": "f1", "status": "draft", "condition": "rewrite"}})["f1"]["condition"] == "original"
    assert merge_findings(kept, {"f1": {"finding_id": "f1", "status": "approved", "condition": "original"}})["f1"]["status"] == "approved"
    draft = {"f2": {"finding_id": "f2", "status": "draft", "condition": "v1"}}
    assert merge_findings(draft, {"f2": {"finding_id": "f2", "status": "draft", "condition": "v2"}})["f2"]["condition"] == "v2"


async def test_revise_round_reenters_tester_and_keeps_kept_findings(tmp_path, data_root, key):
    """Also covers 'at least one revise round' with a stub (criterion 3)."""
    skeptic = SkepticScript(lambda fid, rnd: "revise" if fid == "C2-timeliness" and rnd == 0 else "keep")
    baseline_models = StubModels(good_tester(key))
    _, base_dir = await run(tmp_path / "a", data_root, "baseline", baseline_models, controls=["C2", "C8"])
    _, rev_dir = await run(tmp_path / "b", data_root, "revised", StubModels(good_tester(key), skeptic), controls=["C2", "C8"])
    base, rev = results(base_dir), results(rev_dir)
    timeliness = next(f for f in rev["C2"].findings if f.test_step == "timeliness")
    assert timeliness.condition.startswith("revised: ") and timeliness.status == "kept"
    assert rev["C2"].revision_round == 1
    # kept findings are unchanged, and the unrequested rewrite was ignored
    completeness = lambda r: next(f for f in r["C2"].findings if f.test_step == "completeness")
    assert completeness(rev).model_dump(exclude={"reasoning"}) == completeness(base).model_dump(exclude={"reasoning"})
    assert all("SHOULD NOT APPEAR" not in f.condition for x in rev.values() for f in x.findings)
    assert [f.model_dump() for f in rev["C8"].findings] == [f.model_dump() for f in base["C8"].findings]
    verdicts = json.loads((rev_dir / "verdicts.json").read_text())
    assert verdicts["C2-timeliness#r0"]["decision"] == "revise" and verdicts["C2-timeliness#r1"]["decision"] == "keep"


async def test_second_revise_request_becomes_unresolved(tmp_path, data_root, key):
    skeptic = SkepticScript(lambda fid, rnd: "revise" if fid == "C2-timeliness" else "keep")
    _, run_dir = await run(tmp_path, data_root, "unresolved", StubModels(good_tester(key), skeptic), controls=["C2"])
    f = next(f for f in results(run_dir)["C2"].findings if f.test_step == "timeliness")
    assert f.status == "unresolved"
    assert "**unresolved**" in (run_dir / "report.md").read_text()


async def test_rejected_finding_stays_visible_but_not_in_report(tmp_path, data_root, key):
    skeptic = SkepticScript(lambda fid, rnd: "reject" if fid == "C8-weekly_scan" else "keep")
    _, run_dir = await run(tmp_path, data_root, "reject", StubModels(good_tester(key), skeptic), controls=["C8"])
    rep = json.loads((run_dir / "report.json").read_text())
    assert rep["rejected_by_skeptic"] == ["C8-weekly_scan"]
    assert "C8-weekly_scan" not in [f["finding_id"] for f in rep["findings"]]
    assert next(f for f in results(run_dir)["C8"].findings if f.finding_id == "C8-weekly_scan").status == "rejected"


# ---------- criterion: nothing to review → straight to severity ----------

async def test_nothing_to_review_goes_straight_to_severity(tmp_path, data_root):
    models = StubModels()
    c = cfg("clean", controls=["C4", "C11"])
    ctx = make_context(c, data_root, tmp_path, models, tmp_path / "spend.jsonl")
    ctx.run_dir.mkdir(parents=True)
    app = build_graph().compile(checkpointer=InMemorySaver())
    nodes = []
    async for update in app.astream({"config": c.model_dump()}, config={"configurable": {"thread_id": "clean"}},
                                    context=ctx, stream_mode="updates"):
        nodes += list(update)
    assert "skeptic_one" not in nodes and "route_after_skeptic" not in nodes
    assert nodes.index("await_controls") < nodes.index("severity") < nodes.index("report")
    assert models.log == []                                         # no LLM call at all


# ---------- criterion: an exception or timeout in one control errors only that control ----------

async def test_exception_in_one_control_errors_only_that_control(tmp_path, data_root, key):
    tester = good_tester(key)
    tester.fail = {"C5"}
    out, run_dir = await run(tmp_path, data_root, "boom", StubModels(tester))
    r = results(run_dir)
    assert out["status"] == "done" and len(r) == 12
    assert r["C5"].status == "error" and "stub tester exploded on C5" in r["C5"].error
    assert all(x.status != "error" for cid, x in r.items() if cid != "C5")
    assert "error (RuntimeError" in (run_dir / "report.md").read_text()


async def test_timeout_in_one_control_errors_only_that_control(tmp_path, data_root, key):
    models = StubModels(good_tester(key), slow={"C3": 5.0})
    _, run_dir = await run(tmp_path, data_root, "slow", models, control_timeout_s=1)
    r = results(run_dir)
    assert r["C3"].status == "error" and r["C3"].error == "timeout after 1 s"
    assert all(x.status != "error" for cid, x in r.items() if cid != "C3")


# ---------- criterion: spend over the run cap stops new LLM calls; the rest error spend_cap ----------

async def test_spend_cap_stops_llm_calls_and_marks_remaining_controls(tmp_path, data_root, key):
    models = StubModels(good_tester(key), cost=0.4)
    out, run_dir = await run(tmp_path, data_root, "cap", models, max_concurrency=1, run_spend_cap_usd=1.0)
    r = results(run_dir)
    lines = (tmp_path / "spend.jsonl").read_text().splitlines()
    assert len(models.log) == len(lines) == 3                       # 0.4, 0.8 → third call allowed; then blocked
    capped = [cid for cid, x in r.items() if x.status == "error"]
    assert capped and all(r[c].error.startswith("spend_cap") for c in capped)
    assert out["llm_calls"] == 3 and round(out["cost_usd"], 2) == 1.2


# ---------- criterion: --review human pauses; resuming gives a report with only approved findings ----------

async def test_human_review_pauses_and_resume_reports_only_approved(tmp_path, data_root, key):
    models = StubModels(good_tester(key))
    out, run_dir = await run(tmp_path, data_root, "human", models, review_mode="human", controls=["C2", "C8"])
    assert out["status"] == "paused" and not (run_dir / "report.json").exists()
    request = json.loads((run_dir / "review_request.json").read_text())
    ids = [d["finding_id"] for d in request["decisions"]]
    assert set(ids) == {"C2-completeness", "C2-timeliness", "C8-weekly_scan", "C8-critical_sla"}
    for d in request["decisions"]:
        d["decision"] = "approve" if d["finding_id"] == "C2-timeliness" else "dismiss"
        d["note"] = "checked with IT"
    done = await resume_audit(run_dir, request, models)
    rep = json.loads((run_dir / "report.json").read_text())
    assert done["status"] == "done" and [f["finding_id"] for f in rep["findings"]] == ["C2-timeliness"]
    statuses = {f.finding_id: f.status for x in results(run_dir).values() for f in x.findings}
    assert statuses["C2-timeliness"] == "approved" and statuses["C8-weekly_scan"] == "dismissed"


# ---------- tester structured output: one retry with the error, then the control errors ----------

async def test_tester_schema_failure_is_retried_once(tmp_path, data_root, key):
    tester = good_tester(key)
    tester.invalid_first = True
    _, run_dir = await run(tmp_path, data_root, "retry", StubModels(tester), controls=["C2"])
    assert results(run_dir)["C2"].status == "exceptions"


async def test_tester_schema_failure_twice_errors_the_control(tmp_path, data_root, key):
    tester = good_tester(key)
    tester.always_invalid = {"C2"}
    _, run_dir = await run(tmp_path, data_root, "retry2", StubModels(tester), controls=["C2", "C8"])
    r = results(run_dir)
    assert r["C2"].status == "error" and "StructuredOutputValidationError" in r["C2"].error
    assert r["C8"].status == "exceptions"
