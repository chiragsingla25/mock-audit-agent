"""Phase 2 criteria: checks-only run, scorer, and the citation check (spec Phase 2)."""

from __future__ import annotations

import json
import logging
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from mockaudit.citations import check_citations
from mockaudit.cli import main as cli_main
from mockaudit.datagen.ledgerly import generate
from mockaudit.schemas import Citation, ControlResult, Finding
from mockaudit.scoring import evaluate_run, load_run, score


@pytest.fixture(scope="module")
def data_root(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("ledgerly")
    for v in ["base", "a", "b"]:
        generate(v, root)
    return root


@pytest.fixture(scope="module")
def base_run(data_root, tmp_path_factory) -> Path:
    runs = tmp_path_factory.mktemp("runs")
    assert cli_main(["run", "--checks-only", "--variant", "base", "--data-root", str(data_root), "--runs-dir", str(runs)]) == 0
    return runs / (runs / "LATEST").read_text().strip()


# ---------- criterion: run --checks-only raises every candidate with citations, no LLM ----------

def test_checks_only_writes_12_results_with_cited_candidates(base_run):
    results, meta = load_run(base_run)
    assert meta["config"]["mode"] == "checks_only" and len(results) == 12
    cands = [c for r in results for c in r.candidates]
    assert cands and all(c.citations for c in cands)
    # check failures and items missing from the population are both candidates
    assert {c.test_step for c in cands if c.control_id == "C2"} == {"completeness", "timeliness"}
    c2 = next(r for r in results if r.control_id == "C2")
    assert c2.missing_from_population and not c2.population_complete
    assert any("X3001" in n for n in c2.notes)
    # every failed check result became a candidate
    for r in results:
        assert len([x for x in r.check_results if not x.passed]) == len(r.candidates)
    # judgment-only steps are reported as not tested
    c12 = next(r for r in results if r.control_id == "C12")
    assert c12.coverage.not_tested == [{"step_id": "restore_test", "reason": "judgment-only step (checks-only mode)"}]


def test_checks_only_makes_no_llm_calls(data_root, tmp_path):
    """Runs in a fresh interpreter and checks no LLM client module was ever imported."""
    code = (
        "import sys\n"
        "from mockaudit.cli import main\n"
        f"main(['run', '--checks-only', '--variant', 'base', '--data-root', {str(data_root)!r}, '--runs-dir', {str(tmp_path)!r}])\n"
        "bad = [m for m in sys.modules if m.startswith(('langchain', 'langgraph', 'openrouter', 'openai', 'httpx'))]\n"
        "print('IMPORTED:' + ','.join(bad))\n"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout
    assert out.strip().endswith("IMPORTED:")


# ---------- criterion: checks-only on base finds every code gap and raises every trap ----------

@pytest.mark.parametrize("variant", ["base", "a", "b"])
def test_checks_only_finds_every_code_gap_and_raises_every_trap(data_root, tmp_path, variant):
    cli_main(["run", "--checks-only", "--variant", variant, "--data-root", str(data_root), "--runs-dir", str(tmp_path)])
    ev = evaluate_run(tmp_path / (tmp_path / "LATEST").read_text().strip())
    m = ev["metrics"]
    key = yaml.safe_load((data_root / variant / "answer_key.yaml").read_text())
    code = {g["id"] for g in key["gaps"] if g["tag"] == "code"}
    assert code <= set(m["matched_gaps"])
    assert set(m["missed_gaps"]) == {g["id"] for g in key["gaps"] if g["tag"] == "judgment"}
    assert m["traps_raised"]["n"] == len(key["traps"]) == 4
    assert m["citation_validity"]["value"] == 1.0 and m["severity_agreement"]["value"] == 1.0


def test_eval_on_base_prints_table_and_writes_eval_json(base_run, capsys):
    assert cli_main(["eval", "--run", base_run.name, "--runs-dir", str(base_run.parent)]) == 0
    out = capsys.readouterr().out
    assert "| recall | 8/10 (80%)" in out and "| precision | 8/10 (80%)" in out
    assert "| clean control accuracy | 2/4 (50%)" in out and "| traps raised | 4/4 (100%)" in out
    saved = json.loads((base_run / "eval.json").read_text())
    assert saved["metrics"]["unmatched_findings"] == ["C1-approval", "C9-pir"]


def test_eval_latest_without_runs_says_how_to_start(tmp_path):
    with pytest.raises(SystemExit, match="mockaudit run --checks-only"):
        cli_main(["eval", "--run", "latest", "--runs-dir", str(tmp_path)])


# ---------- criterion: the scorer ----------

def finding(fid, control, ids, severity="high", status="kept"):
    return Finding(finding_id=fid, control_id=control, test_step="s", gap_type="operating", exceptions=1, tested=1,
                   condition="c", criteria="c", effect="e", recommendation="r", severity=severity, status=status,
                   citations=[Citation(source="src", record_id=i) for i in ids])


KEY = {"gaps": [{"id": "G1", "control_id": "C2", "tag": "code", "record_ids": ["E1", "E2"], "severity": "high"},
                {"id": "G2", "control_id": "C3", "tag": "judgment", "record_ids": ["UAR-1"], "severity": "high"},
                {"id": "G3", "control_id": "C5", "tag": "code", "record_ids": ["P1"], "severity": "moderate"}],
       "traps": [{"id": "T1", "control_id": "C2", "record_ids": ["E9"]}, {"id": "T2", "control_id": "C1", "record_ids": ["A1"]}],
       "clean_controls": ["C1", "C4"]}


def result(control, findings, dropped=()):
    return ControlResult(control_id=control, status="exceptions" if findings else "pass", findings=findings,
                         dropped_citations=list(dropped))


def test_scorer_matches_on_control_and_one_cited_record():
    results = [result("C2", [finding("f1", "C2", ["E2", "E9"])]),             # matches G1 via E2; also raises T1
               result("C3", [finding("f2", "C5", ["UAR-1"])]),                # right record, wrong control → no match
               result("C5", [finding("f3", "C5", ["P1"], severity="high")]),  # matches G3, severity disagrees
               result("C1", [finding("f4", "C1", ["A2"])]),                   # unmatched; C1 clean → not clean any more
               result("C4", [finding("f5", "C4", ["Z"], status="rejected")])]  # rejected findings don't count
    index = {("src", i) for i in ["E2", "E9", "UAR-1", "P1", "A2"]}
    m = score(results, KEY, index)
    assert m["matched_gaps"] == ["G1", "G3"] and m["missed_gaps"] == ["G2"]
    assert (m["recall"]["n"], m["recall"]["of"]) == (2, 3) and (m["recall_code"]["n"], m["recall_code"]["of"]) == (2, 2)
    assert (m["precision"]["n"], m["precision"]["of"]) == (2, 4)
    assert (m["clean_control_accuracy"]["n"], m["clean_control_accuracy"]["of"]) == (1, 2)
    assert (m["severity_agreement"]["n"], m["severity_agreement"]["of"]) == (1, 2)
    assert m["traps_raised_ids"] == ["T1"]
    assert m["citation_validity"]["value"] == 1.0


def test_scorer_counts_dropped_and_unknown_citations_against_validity():
    results = [result("C2", [finding("f1", "C2", ["E1", "GHOST"])], dropped=[Citation(source="src", record_id="NOPE")])]
    m = score(results, KEY, {("src", "E1")})
    assert (m["citation_validity"]["n"], m["citation_validity"]["of"]) == (1, 3)


def test_scorer_handles_no_findings():
    m = score([result("C2", [])], KEY, set())
    assert m["precision"]["value"] is None and m["recall"]["n"] == 0 and m["clean_control_accuracy"]["n"] == 2


# ---------- criterion (failure case): a nonexistent citation is dropped and logged ----------

def test_citation_check_drops_and_logs_nonexistent_record(caplog):
    cites = [Citation(source="hr_roster", record_id="E1001"), Citation(source="hr_roster", record_id="E9999")]
    with caplog.at_level(logging.WARNING, logger="mockaudit.citations"):
        kept, dropped = check_citations(cites, {("hr_roster", "E1001")}, "C2-timeliness")
    assert kept == [cites[0]] and dropped == [cites[1]]
    assert "C2-timeliness: dropped citation to nonexistent record hr_roster/E9999" in caplog.text


def test_citation_check_on_real_evidence_index(data_root):
    from mockaudit.scoring import data_index
    index = data_index(data_root / "base")
    assert ("hr_roster", "E1001") in index and ("okta_mfa_policy", "rule-mfa-01") in index
    assert ("user_access_reviews", "UAR-2026Q3") in index and ("restore_tests", "RST-2025-09") in index
    kept, dropped = check_citations([Citation(source="okta_events", record_id="OK-999999")], index)
    assert kept == [] and len(dropped) == 1
