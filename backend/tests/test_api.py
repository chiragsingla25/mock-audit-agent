"""Phase 5 (backend): the local FastAPI that the live-mode UI calls. Stub LLMs only."""

from __future__ import annotations

import time
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient
from stubs import StubModels, TesterScript

from mockaudit.api import create_app
from mockaudit.datagen.ledgerly import generate


@pytest.fixture(scope="module")
def data_root(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("ledgerly")
    generate("base", root)
    return root


def perfect(data_root) -> TesterScript:
    k = yaml.safe_load((data_root / "base" / "answer_key.yaml").read_text())
    return TesterScript(dismiss={t["record_ids"][0] for t in k["traps"]},
                        flag={r for g in k["gaps"] if g["tag"] == "judgment" for r in g["record_ids"]})


def wait_for(client, run_id, statuses, timeout=30):
    end = time.time() + timeout
    while time.time() < end:
        body = client.get(f"/audits/{run_id}").json()
        if body["status"] in statuses:
            return body
        time.sleep(0.05)
    raise AssertionError(f"audit {run_id} stuck in {body['status']}")


@pytest.fixture
def client(data_root, tmp_path):
    app = create_app(data_root, tmp_path, lambda: StubModels(perfect(data_root), cost=0.001))
    with TestClient(app) as c:
        yield c


def test_config_reports_models_variants_and_spend(client, monkeypatch):
    body = client.get("/config").json()
    assert body["variants"] == ["base"] and body["spend_usd"] == 0 and body["busy"] is False
    assert {"tester_model", "skeptic_model", "project_cap_usd", "run_cap_usd"} <= set(body)


def test_full_flow_start_progress_findings_review_report(client):
    run_id = client.post("/audits", json={"variant": "base"}).json()["run_id"]
    status = wait_for(client, run_id, {"paused", "error"})
    assert status["status"] == "paused" and len(status["controls"]) == 12
    assert set(status["controls"].values()) == {"done"} and status["cost_usd"] > 0

    body = client.get(f"/audits/{run_id}/findings").json()
    findings = [f for f in body["findings"] if f["group"] == "findings"]
    ids = {f["finding_id"] for f in findings}
    assert "C2-timeliness" in ids and len(findings) == 10
    g1 = next(f for f in findings if f["finding_id"] == "C2-timeliness")
    assert g1["reasoning"] and g1["verdicts"][0]["decision"] == "keep"
    assert all(c["record"] is not None for c in g1["cited"])                  # cited rows resolved server-side
    assert {x["candidate_id"] for x in body["not_raised"]} >= {"C1-approval-AR-0031", "C9-pir-INC-22"}

    decisions = [{"finding_id": f, "decision": "approve" if f == "C2-timeliness" else "dismiss", "note": "ok"} for f in ids]
    assert client.post(f"/audits/{run_id}/review", json={"decisions": decisions}).status_code == 202
    assert wait_for(client, run_id, {"done", "error"})["status"] == "done"
    report = client.get(f"/audits/{run_id}/report").json()
    assert [f["finding_id"] for f in report["findings"]] == ["C2-timeliness"]
    md = client.get(f"/audits/{run_id}/report?format=md")
    assert md.headers["content-type"].startswith("text/markdown") and "C2-timeliness" in md.text
    assert "pass badge" not in md.text.lower() and "Not an audit opinion" in md.text
    assert client.get("/audits").json()[0] == {"run_id": run_id, "variant": "base", "mode": "agent",
                                               "review_mode": "human", "status": "done"}


def test_second_start_while_running_is_409_and_findings_wait(data_root, tmp_path):
    models = StubModels(perfect(data_root), slow={"C1": 1.5})
    with TestClient(create_app(data_root, tmp_path, lambda: models)) as client:
        run_id = client.post("/audits", json={"variant": "base"}).json()["run_id"]
        assert client.post("/audits", json={"variant": "base"}).status_code == 409
        assert client.get(f"/audits/{run_id}/findings").status_code == 409
        end = time.time() + 5
        while "running" not in (running := client.get(f"/audits/{run_id}").json())["controls"].values() and time.time() < end:
            time.sleep(0.02)
        assert running["status"] == "running" and "running" in running["controls"].values()
        assert wait_for(client, run_id, {"paused"})["status"] == "paused"


def test_errors_for_unknown_runs_and_wrong_states(client):
    assert client.get("/audits/nope").status_code == 404
    run_id = client.post("/audits", json={"variant": "base", "mode": "checks_only"}).json()["run_id"]
    wait_for(client, run_id, {"paused"})
    assert client.get(f"/audits/{run_id}/report").status_code == 409               # not written until review
    assert client.post("/audits", json={"variant": "a"}).status_code == 400          # no dataset for a here
    client.post(f"/audits/{run_id}/review", json={"decisions": []})
    wait_for(client, run_id, {"done"})
    assert client.post(f"/audits/{run_id}/review", json={"decisions": []}).status_code == 409


def test_checks_only_audit_needs_no_models(data_root, tmp_path):
    def no_models():
        raise AssertionError("models must not be created for checks-only")
    with TestClient(create_app(data_root, tmp_path, no_models)) as client:
        run_id = client.post("/audits", json={"variant": "base", "mode": "checks_only"}).json()["run_id"]
        assert wait_for(client, run_id, {"paused", "error"})["status"] == "paused"



def test_progress_marks_running_only_when_the_body_starts_and_done_after_a_revise():
    from mockaudit.api import Progress
    run = {"controls": {"C1": "queued", "C2": "queued"}, "phase": "", "error": None}
    p = Progress(run)
    p({"id": "t1", "name": "control", "input": {"spec": {"control_id": "C1"}}})
    assert run["controls"]["C1"] == "queued"                          # scheduled is not running
    p.control("C1", "running")
    assert run["controls"]["C1"] == "running"
    p({"id": "t1", "name": "control", "result": {"results": {"C1": {"status": "pass"}}}, "error": None})
    assert run["controls"]["C1"] == "done"
    p({"id": "t2", "name": "control", "input": {"spec": {"control_id": "C2"}, "revise": {"C2-x": {}}}})
    p.control("C2", "revising")
    p({"id": "t2", "name": "control", "result": {"findings": {}}, "error": None})   # revise passes return findings only
    assert run["controls"]["C2"] == "done"
