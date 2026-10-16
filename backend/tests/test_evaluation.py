"""Phase 4 criteria: eval --all, its metrics, the eval spend cap, honest targets, CI (spec Phase 4). Stub LLMs only."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from stubs import SkepticScript, StubModels, TesterScript

from mockaudit.datagen.ledgerly import generate
from mockaudit.evaluation import AGENT_PLAN, jaccard, run_eval_all

REPO = Path(__file__).resolve().parents[2]
BASE_CFG = {"max_concurrency": 4, "control_timeout_s": 60, "run_spend_cap_usd": 1.0}


@pytest.fixture(scope="module")
def data_root(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("ledgerly")
    for v in ["base", "a", "b"]:
        generate(v, root)
    return root


def perfect_tester(data_root) -> TesterScript:
    keys = [yaml.safe_load((data_root / v / "answer_key.yaml").read_text()) for v in ["base", "a", "b"]]
    traps = {t["record_ids"][0] for k in keys for t in k["traps"]}
    judgment = {r for k in keys for g in k["gaps"] if g["tag"] == "judgment" for r in g["record_ids"]}
    return TesterScript(dismiss=traps, flag=judgment)


@pytest.fixture(scope="module")
async def full_eval(data_root, tmp_path_factory):
    runs = tmp_path_factory.mktemp("runs")
    models = StubModels(perfect_tester(data_root), cost=0.001)
    result = await run_eval_all(data_root, runs, models, runs / "spend.jsonl", BASE_CFG)
    return result, runs, models


# ---------- criterion: eval --all runs everything and writes eval.json + a Markdown table ----------

async def test_eval_all_runs_agent_variants_stability_checks_only_and_skeptic_off(full_eval):
    result, runs, _ = full_eval
    modes = [(r["mode"], r["variant"]) for r in result["rows"]]
    assert modes.count(("agent", "base")) == 3 and ("agent", "a") in modes and ("agent", "b") in modes
    assert sorted(v for m, v in modes if m == "checks_only") == ["a", "b", "base"]
    assert sum(m == "skeptic_off" for m, _ in modes) == len(AGENT_PLAN)
    out = runs / result["eval_id"]
    assert json.loads((out / "eval.json").read_text())["eval_id"] == result["eval_id"]
    md = (out / "eval.md").read_text()
    assert "| Metric | Result | Target |" in md and "| Run | Variant | Mode |" in md


async def test_skeptic_off_is_derived_with_no_extra_llm_calls(full_eval):
    result, runs, models = full_eval
    agent_calls = sum(r["llm_calls"] for r in result["rows"] if r["mode"] == "agent")
    assert agent_calls == len(models.log) == len((runs / "spend.jsonl").read_text().splitlines())
    for r in result["rows"]:
        if r["mode"] == "skeptic_off":
            assert r["llm_calls"] == 0 and r["cost_usd"] == 0 and r["derived_from"] == r["run_id"]


# ---------- criterion: reports every metric, comparisons, stability and cost ----------

async def test_eval_reports_all_metrics_comparisons_stability_and_cost(full_eval):
    result, _, _ = full_eval
    assert {t["metric"] for t in result["targets"]} == {"recall", "precision", "clean_control_accuracy",
                                                         "citation_validity", "severity_agreement", "stability"}
    for row in result["rows"]:
        assert {"recall", "precision", "clean_control_accuracy", "citation_validity", "severity_agreement",
                "traps_raised"} <= set(row["metrics"])
    assert set(result["comparisons"]) == {"base", "a", "b"}
    base = result["comparisons"]["base"]
    assert base["recall"] == {"agent": 1.0, "skeptic_off": 1.0, "checks_only": 0.8}
    assert base["traps_raised"] == {"agent": 0, "skeptic_off": 0, "checks_only": 4}
    assert len(result["stability"]["runs"]) == 3 and result["stability"]["value"] == 1.0
    c = result["cost"]
    assert c["per_audit_usd"] > 0 and c["per_audit_tokens"] > 0 and c["within_cap"]


async def test_skeptic_on_vs_off_differs_when_the_skeptic_rejects(data_root, tmp_path):
    skeptic = SkepticScript(lambda fid, rnd: "reject" if fid == "C8-weekly_scan" else "keep")
    result = await run_eval_all(data_root, tmp_path, StubModels(perfect_tester(data_root), skeptic), tmp_path / "s.jsonl",
                                BASE_CFG, plan=[("base", 1)])
    recall = result["comparisons"]["base"]["recall"]
    assert recall["agent"] == 0.9 and recall["skeptic_off"] == 1.0          # the rejected G7 finding counts again


def test_jaccard():
    assert jaccard({1, 2}, {1, 2}) == 1.0 and jaccard({1, 2}, {2, 3}) == pytest.approx(1 / 3) and jaccard(set(), set()) == 1.0


# ---------- criterion: total evaluation spend stays within the cap ----------

async def test_eval_spend_cap_skips_runs_that_would_exceed_it(data_root, tmp_path):
    models = StubModels(perfect_tester(data_root), cost=0.05)
    cfg = {**BASE_CFG, "max_concurrency": 1}
    result = await run_eval_all(data_root, tmp_path, models, tmp_path / "s.jsonl", cfg, eval_cap=1.5)
    spent = sum(json.loads(x)["cost"] for x in (tmp_path / "s.jsonl").read_text().splitlines())
    assert result["skipped"] and all("eval spend cap" in s["reason"] for s in result["skipped"])
    assert spent == pytest.approx(result["cost"]["eval_total_usd"]) and spent <= 1.5 and result["cost"]["within_cap"]


# ---------- criterion: targets are reported honestly ----------

async def test_missed_targets_are_shown_not_hidden(data_root, tmp_path):
    blind = TesterScript()
    blind.dismiss = _Everything()                             # dismisses every candidate → recall collapses
    result = await run_eval_all(data_root, tmp_path, StubModels(blind), tmp_path / "s.jsonl", BASE_CFG, plan=[("base", 1)])
    recall = next(t for t in result["targets"] if t["metric"] == "recall")
    assert recall["met"] is False and recall["base"] < 0.8
    md = (tmp_path / result["eval_id"] / "eval.md").read_text()
    assert "| recall |" in md and "**missed**" in md


class _Everything:
    def __contains__(self, item):
        return True


# ---------- criterion: CI runs ruff + pytest with no secrets and no LLM calls ----------

def test_ci_workflow_runs_lint_and_tests_without_secrets():
    ci = (REPO / ".github" / "workflows" / "ci.yml").read_text()
    wf = yaml.safe_load(ci)
    steps = " ".join(str(s.get("run", "")) for job in wf["jobs"].values() for s in job["steps"])
    assert "ruff check" in steps and "pytest" in steps
    assert "secrets." not in ci and "OPENROUTER" not in ci and "LANGSMITH_API_KEY" not in ci


async def test_skeptic_off_counts_a_finding_dropped_after_a_skeptic_revise(data_root, tmp_path):
    """Without the skeptic there would have been no revision, so the dropped finding counts in the skeptic-off view."""
    tester = perfect_tester(data_root)
    tester.dismiss_on_revise = True
    skeptic = SkepticScript(lambda fid, rnd: "revise" if fid == "C3-signoff" and rnd == 0 else "keep")
    result = await run_eval_all(data_root, tmp_path, StubModels(tester, skeptic), tmp_path / "s.jsonl", BASE_CFG,
                                plan=[("base", 1)])
    recall = result["comparisons"]["base"]["recall"]
    assert recall["agent"] == 0.9 and recall["skeptic_off"] == 1.0


async def test_rescore_rebuilds_eval_without_llm_calls(full_eval, data_root):
    from mockaudit.evaluation import rescore
    result, runs, models = full_eval
    calls = len(models.log)
    again = rescore(runs, result["eval_id"], data_root)
    assert len(models.log) == calls and again["targets"] == result["targets"]
