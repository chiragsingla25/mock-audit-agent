"""Read models shared by the live API and the static showcase export, so both serve identical JSON."""

from __future__ import annotations

import json
from pathlib import Path

from mockaudit.evidence import Evidence
from mockaudit.runner import load_state
from mockaudit.schemas import ControlSpec, Finding


def run_config(run_dir: Path) -> dict:
    return json.loads((Path(run_dir) / "config.json").read_text())["config"]


def disk_status(run_dir: Path) -> str:
    d = Path(run_dir)
    if (d / "report.json").exists():
        return "done"
    if (d / "review_request.json").exists():
        return "paused"
    return "interrupted"


def run_cost(spend_path: Path, run_id: str) -> dict:
    cost, tokens, calls = 0.0, 0, 0
    if Path(spend_path).exists():
        for line in Path(spend_path).read_text().splitlines():
            x = json.loads(line) if line.strip() else {}
            if x.get("run") == run_id:
                cost, tokens, calls = cost + x["cost"], tokens + x["tokens"], calls + 1
    return {"cost_usd": round(cost, 6), "tokens": tokens, "llm_calls": calls}


def audit_from_disk(run_dir: Path, spend_path: Path) -> dict:
    """GET /audits/{id} for a run that is not live in this process."""
    d, cfg = Path(run_dir), run_config(run_dir)
    controls, errors = {}, {}
    for p in sorted((d / "controls").glob("*.json"), key=lambda p: int(p.stem[1:])) if (d / "controls").exists() else []:
        r = json.loads(p.read_text())
        controls[r["control_id"]] = "error" if r["status"] == "error" else "done"
        if r["status"] == "error":
            errors[r["control_id"]] = r["error"]
    status = disk_status(d)
    return {"run_id": cfg["run_id"], "variant": cfg["variant"], "mode": cfg["mode"], "status": status, "phase": status,
            "error": None, "controls": controls, "control_errors": errors, **run_cost(spend_path, cfg["run_id"])}


async def findings_view(run_dir: Path, data_root: Path, status: str) -> dict:
    """GET /audits/{id}/findings: findings with cited records resolved (only the cited ones), verdicts, decisions."""
    state = await load_state(run_dir)
    cfg = run_config(run_dir)
    specs = {s["control_id"]: ControlSpec.model_validate(s) for s in state.get("specs", [])}
    evidence: dict[str, Evidence] = {}

    def ev(cid):
        if cid not in evidence:
            evidence[cid] = Evidence.load(specs[cid], Path(data_root) / cfg["variant"])
        return evidence[cid]

    def cited(control_id, citations):
        out = []
        for c in citations:
            rec = ev(control_id).get(c["source"], c["record_id"])
            out.append({**c, "record": {k: v for k, v in (rec or {}).items() if k != "file"} if rec else None})
        return out

    verdicts = state.get("verdicts", {})
    decisions = state.get("decisions") or {}
    items = []
    for f in sorted(state.get("findings", {}).values(), key=lambda f: (int(f["control_id"][1:]), f["finding_id"])):
        fv = sorted((v for k, v in verdicts.items() if k.split("#")[0] == f["finding_id"]), key=lambda v: v["round"])
        group = "rejected" if f["status"] == "rejected" else \
            "dismissed_on_revision" if f["status"] == "dismissed" and f["finding_id"] not in decisions else "findings"
        items.append({**Finding.model_validate(f).model_dump(), "group": group, "cited": cited(f["control_id"], f["citations"]),
                      "verdicts": fv, "decision": decisions.get(f["finding_id"])})
    not_raised = [{**x, "cited": cited(x["control_id"], x["citations"])}
                  for x in sorted(state.get("dismissals", {}).values(), key=lambda x: x["candidate_id"])]
    return {"run_id": cfg["run_id"], "status": status, "findings": items, "not_raised": not_raised}
