"""Phase 6: export-showcase writes the static JSON (cited records only) and it validates against the schemas."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError
from stubs import StubModels, TesterScript

from mockaudit.cli import main as cli_main
from mockaudit.datagen.ledgerly import generate
from mockaudit.evaluation import run_eval_all
from mockaudit.runner import resume_audit, run_audit
from mockaudit.schemas import RunConfig
from mockaudit.showcase import export_showcase, export_showcase_async, validate_showcase

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def data_root(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("ledgerly")
    for v in ["base", "a", "b"]:
        generate(v, root)
    return root


def perfect(data_root) -> TesterScript:
    keys = [yaml.safe_load((data_root / v / "answer_key.yaml").read_text()) for v in ["base", "a", "b"]]
    return TesterScript(dismiss={t["record_ids"][0] for k in keys for t in k["traps"]},
                        flag={r for k in keys for g in k["gaps"] if g["tag"] == "judgment" for r in g["record_ids"]})


@pytest.fixture(scope="module")
async def published(data_root, tmp_path_factory):
    runs = tmp_path_factory.mktemp("runs")
    models = StubModels(perfect(data_root), cost=0.001)
    ev = await run_eval_all(data_root, runs, models, runs / "spend.jsonl",
                            {"max_concurrency": 4, "control_timeout_s": 60, "run_spend_cap_usd": 1.0}, plan=[("base", 1)])
    reviewed = RunConfig(run_id="reviewed-base", variant="base", mode="agent", review_mode="human")
    await run_audit(reviewed, data_root, runs, models, runs / "spend.jsonl")
    request = json.loads((runs / "reviewed-base" / "review_request.json").read_text())
    for d in request["decisions"]:
        d["decision"], d["note"] = ("dismiss", "not convinced") if d["finding_id"] == "C12-restore_test" else ("approve", "")
    await resume_audit(runs / "reviewed-base", request, models)
    run_ids = ["reviewed-base"] + [r["run_id"] for r in ev["rows"] if r["mode"] in ("agent", "checks_only")]
    out = tmp_path_factory.mktemp("frontend") / "public" / "data"
    await export_showcase_async(run_ids, runs, data_root, out, ev["eval_id"])
    return out, runs, run_ids


def test_export_writes_index_and_three_files_per_run_and_validates(published):
    out, _, run_ids = published
    index = json.loads((out / "index.json").read_text())
    assert [r["run_id"] for r in index["runs"]] == run_ids
    for run_id in run_ids:
        assert sorted(p.name for p in (out / "runs" / run_id).iterdir()) == ["audit.json", "findings.json", "report.json",
                                                                            "report.md"]
    assert validate_showcase(out) == 1 + 4 * len(run_ids)
    assert "Not an audit opinion" in index["statement"]


def test_showcase_contains_cited_records_only(published, data_root):
    out, _, _ = published
    all_findings = [json.loads(p.read_text()) for p in out.glob("runs/*/findings.json")]
    published_ids = {c["record_id"] for fs in all_findings for f in fs["findings"] + fs["not_raised"] for c in f["cited"]}
    findings = json.loads((out / "runs" / "reviewed-base" / "findings.json").read_text())
    blob = "".join(p.read_text() for p in out.rglob("*.json"))
    hr = (data_root / "base" / "exports" / "hr_roster.csv").read_text().splitlines()[1:]
    unpublished = [line.split(",")[0] for line in hr if line.split(",")[0] not in published_ids]
    leaked = [e for e in unpublished if f'"employee_id": "{e}"' in blob]
    assert unpublished and not leaked, leaked[:5]                                          # rows nobody cited stay out
    assert all(c["record"] is not None for f in findings["findings"] for c in f["cited"])


def test_reviewed_run_carries_recorded_decisions(published):
    out, _, _ = published
    index = json.loads((out / "index.json").read_text())
    entry = next(r for r in index["runs"] if r["run_id"] == "reviewed-base")
    assert entry["reviewed"] and entry["label"].endswith("human-reviewed")
    findings = json.loads((out / "runs" / "reviewed-base" / "findings.json").read_text())
    c12 = next(f for f in findings["findings"] if f["finding_id"] == "C12-restore_test")
    assert c12["decision"] == {"finding_id": "C12-restore_test", "decision": "dismiss", "note": "not convinced"}
    report = json.loads((out / "runs" / "reviewed-base" / "report.json").read_text())
    assert "C12-restore_test" not in [f["finding_id"] for f in report["findings"]]


def test_index_carries_the_comparison(published):
    out, _, _ = published
    ev = json.loads((out / "index.json").read_text())["eval"]
    assert {r["mode"] for r in ev["rows"]} == {"agent", "skeptic_off", "checks_only"}
    assert {t["metric"] for t in ev["targets"]} >= {"recall", "precision", "stability"}


def test_export_refuses_unfinished_runs_and_odd_output_folders(published, data_root, tmp_path):
    _, runs, run_ids = published
    for odd in (tmp_path / "public", tmp_path / "data"):                       # e.g. `--out data` at the repo root
        with pytest.raises(ValueError, match="public/data"):
            export_showcase(run_ids[:1], runs, data_root, odd)
    (runs / "paused").mkdir()
    (runs / "paused" / "config.json").write_text(json.dumps({"config": {"run_id": "paused", "variant": "base",
                                                                         "mode": "agent", "review_mode": "human"}}))
    (runs / "paused" / "review_request.json").write_text("{}")
    with pytest.raises(ValueError, match="only finished runs"):
        export_showcase(["paused"], runs, data_root, tmp_path / "public" / "data")


def test_a_bad_run_id_deletes_nothing(published, data_root, tmp_path):
    """Review M2 note: validation happens before the output folder is replaced."""
    _, runs, _ = published
    out = tmp_path / "public" / "data"
    out.mkdir(parents=True)
    (out / "precious.txt").write_text("keep me")
    with pytest.raises(FileNotFoundError, match="no run 'no-such-run'"):
        export_showcase(["no-such-run"], runs, data_root, out)
    assert (out / "precious.txt").read_text() == "keep me"


def test_unreviewed_runs_are_marked_and_their_reports_do_not_claim_approval(published):
    """Review M2 FAIL (Phase 6 rule: eval runs are published marked unreviewed)."""
    out, _, _ = published
    index = json.loads((out / "index.json").read_text())
    for r in index["runs"]:
        assert r["label"].endswith("human-reviewed") if r["reviewed"] else " · not reviewed" in r["label"]
        md = (out / "runs" / r["run_id"] / "report.md").read_text()
        if r["reviewed"]:
            assert "## Approved findings" in md and "Not reviewed by a person" not in md
        else:
            assert "## Approved findings" not in md and "Not reviewed by a person" in md


def test_validation_catches_a_broken_file(published, tmp_path):
    import shutil
    out, _, _ = published
    copy = tmp_path / "public" / "data"
    shutil.copytree(out, copy)
    f = copy / "runs" / "reviewed-base" / "findings.json"
    body = json.loads(f.read_text())
    del body["findings"][0]["cited"]
    f.write_text(json.dumps(body))
    with pytest.raises(ValidationError):
        validate_showcase(copy)


def test_validate_showcase_cli_on_committed_data():
    """CI: the JSON committed for GitHub Pages validates against the schemas."""
    data = REPO / "frontend" / "public" / "data"
    if not (data / "index.json").exists():
        pytest.skip("no showcase exported yet")
    assert cli_main(["validate-showcase", "--dir", str(data)]) == 0
