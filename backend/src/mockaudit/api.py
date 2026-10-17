"""Local FastAPI for the live-mode UI (spec Phase 5). Runs only on this machine; the published site has no backend.

One audit runs at a time, in this process's event loop. Browser-started audits always pause for human review.
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from mockaudit.datagen.ledgerly import VARIANT_SEEDS
from mockaudit.runner import new_run_id, resume_audit, run_audit
from mockaudit.schemas import RunConfig
from mockaudit.specs import load_controls
from mockaudit.views import findings_view


class StartAudit(BaseModel):
    variant: Literal["base", "a", "b"] = "base"
    mode: Literal["agent", "skeptic_off", "checks_only"] = "agent"


class Decision(BaseModel):
    finding_id: str
    decision: Literal["approve", "dismiss"]
    note: str = ""


class Review(BaseModel):
    decisions: list[Decision]


class Live:
    """In-memory progress for runs started by this server process (status on disk covers the rest)."""

    def __init__(self):
        self.runs: dict[str, dict] = {}
        self.task: asyncio.Task | None = None

    def busy(self) -> bool:
        return self.task is not None and not self.task.done()

    def progress(self, run_id: str) -> Progress:
        return Progress(self.runs[run_id])


STAGES = {"skeptic_one": "skeptic review", "severity": "severity", "human_review": "awaiting review",
          "report": "writing report"}


class Progress:
    """Live progress for one run: control cards from the control node itself, stages from the task stream."""

    def __init__(self, run: dict):
        self.run, self.tasks = run, {}

    def control(self, control_id: str, state: str) -> None:
        self.run["controls"][control_id] = state

    def __call__(self, chunk: dict) -> None:
        name = chunk.get("name")
        if name == "control" and "input" in chunk:          # scheduled; it turns "running" when its body starts
            self.tasks[chunk["id"]] = (chunk["input"] or {}).get("spec", {}).get("control_id")
        elif name == "control" and "result" in chunk:
            cid = self.tasks.pop(chunk.get("id"), None)
            results = (chunk.get("result") or {}).get("results") or {}
            for rid, res in results.items():
                self.run["controls"][rid] = "error" if res.get("status") == "error" else "done"
            if cid and cid not in results:                    # a revise pass returns findings only
                self.run["controls"][cid] = "error" if chunk.get("error") else "done"
            if chunk.get("error"):
                self.run["error"] = str(chunk["error"])
        elif name in STAGES and "input" in chunk:
            self.run["phase"] = STAGES[name]


def create_app(data_root: Path, runs_dir: Path, models_factory=None, spend_path: Path | None = None) -> FastAPI:
    """`models_factory()` returns an object with .tester() / .skeptic() (OpenRouter by default; stubs in tests)."""
    data_root, runs_dir = Path(data_root), Path(runs_dir)
    spend_path = spend_path or runs_dir / "spend.jsonl"
    live = Live()
    app = FastAPI(title="Mock Audit Agent (local)", version="0.1.0")
    app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
                       allow_methods=["*"], allow_headers=["*"])
    app.state.live = live

    def models():
        if models_factory is not None:
            return models_factory()
        from mockaudit.llm import OpenRouterModels
        return OpenRouterModels()

    def run_dir(run_id: str) -> Path:
        d = runs_dir / run_id
        if not (d / "config.json").exists():
            raise HTTPException(404, f"no audit {run_id!r}")
        return d

    def run_meta(run_id: str) -> dict:
        return json.loads((run_dir(run_id) / "config.json").read_text())["config"]

    def run_cost(run_id: str) -> dict:
        cost, tokens, calls = 0.0, 0, 0
        if spend_path.exists():
            for line in spend_path.read_text().splitlines():
                x = json.loads(line) if line.strip() else {}
                if x.get("run") == run_id:
                    cost, tokens, calls = cost + x["cost"], tokens + x["tokens"], calls + 1
        return {"cost_usd": round(cost, 6), "tokens": tokens, "llm_calls": calls}

    def disk_status(run_id: str) -> str:
        d = runs_dir / run_id
        if (d / "report.json").exists():
            return "done"
        if (d / "review_request.json").exists():
            return "paused"
        return "interrupted"            # started by a previous server process and never finished

    def status(run_id: str) -> str:
        return live.runs[run_id]["status"] if run_id in live.runs else disk_status(run_id)

    async def drive(run_id: str, coro) -> None:
        run = live.runs[run_id]
        try:
            out = await coro
            run["status"] = out["status"]
            run["phase"] = "awaiting review" if out["status"] == "paused" else "done"
        except Exception as e:          # noqa: BLE001 - surfaced through GET /audits/{id}
            run["status"], run["error"] = "error", f"{type(e).__name__}: {e}"

    @app.get("/config")
    def config() -> dict:
        total = 0.0
        if spend_path.exists():
            total = sum(json.loads(x)["cost"] for x in spend_path.read_text().splitlines() if x.strip())
        return {"tester_model": os.environ.get("TESTER_MODEL", ""), "skeptic_model": os.environ.get("SKEPTIC_MODEL", ""),
                "variants": [v for v in VARIANT_SEEDS if (data_root / v / "controls.yaml").exists()],
                "spend_usd": round(total, 4), "project_cap_usd": float(os.environ.get("PROJECT_SPEND_CAP_USD", "9.50")),
                "run_cap_usd": float(os.environ.get("RUN_SPEND_CAP_USD", "1.00")), "busy": live.busy()}

    @app.get("/audits")
    def list_audits() -> list[dict]:
        out = []
        for d in sorted(runs_dir.glob("*/config.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:20]:
            cfg = json.loads(d.read_text())["config"]
            out.append({"run_id": cfg["run_id"], "variant": cfg["variant"], "mode": cfg["mode"],
                        "review_mode": cfg["review_mode"], "status": status(cfg["run_id"])})
        return out

    @app.post("/audits", status_code=202)
    async def start(body: StartAudit) -> dict:
        if live.busy():
            raise HTTPException(409, "an audit is already running; wait for it to finish or pause")
        if not (data_root / body.variant / "controls.yaml").exists():
            raise HTTPException(400, f"no dataset for variant {body.variant!r}; run `mockaudit gen --variant {body.variant}`")
        m = models() if body.mode != "checks_only" else None
        cfg = RunConfig(run_id=new_run_id(body.mode, body.variant), variant=body.variant, mode=body.mode, review_mode="human",
                        tester_model=getattr(m, "tester_name", ""), skeptic_model=getattr(m, "skeptic_name", ""),
                        max_concurrency=int(os.environ.get("MAX_CONCURRENCY", "4")),
                        control_timeout_s=int(os.environ.get("CONTROL_TIMEOUT_S", "420")),
                        run_spend_cap_usd=float(os.environ.get("RUN_SPEND_CAP_USD", "1.00")))
        ids = [s.control_id for s in load_controls(data_root / body.variant / "controls.yaml")]
        live.runs[cfg.run_id] = {"status": "running", "phase": "testing controls", "error": None,
                                 "controls": dict.fromkeys(ids, "queued"),
                                 "started": datetime.now(UTC).isoformat()}
        live.task = asyncio.create_task(drive(cfg.run_id, run_audit(cfg, data_root, runs_dir, m, spend_path,
                                                                    live.progress(cfg.run_id))))
        return {"run_id": cfg.run_id}

    @app.get("/audits/{run_id}")
    def get_audit(run_id: str) -> dict:
        cfg = run_meta(run_id)
        d = runs_dir / run_id
        if run_id in live.runs:
            r = live.runs[run_id]
            controls, phase, error = r["controls"], r["phase"], r["error"]
        else:
            controls = {p.stem: ("error" if json.loads(p.read_text())["status"] == "error" else "done")
                        for p in (d / "controls").glob("*.json")} if (d / "controls").exists() else {}
            phase, error = disk_status(run_id), None
        errors = {}
        if (d / "controls").exists():
            for p in (d / "controls").glob("*.json"):
                r = json.loads(p.read_text())
                if r["status"] == "error":
                    errors[r["control_id"]] = r["error"]
        return {"run_id": run_id, "variant": cfg["variant"], "mode": cfg["mode"], "status": status(run_id),
                "phase": phase, "error": error, "controls": dict(sorted(controls.items(), key=lambda kv: int(kv[0][1:]))),
                "control_errors": errors, **run_cost(run_id)}

    @app.get("/audits/{run_id}/findings")
    async def findings(run_id: str) -> dict:
        d = run_dir(run_id)
        if status(run_id) == "running":
            raise HTTPException(409, "the audit is still running")
        return await findings_view(d, data_root, status(run_id))

    @app.post("/audits/{run_id}/review", status_code=202)
    async def review(run_id: str, body: Review) -> dict:
        d = run_dir(run_id)
        if status(run_id) != "paused":
            raise HTTPException(409, f"audit {run_id} is not waiting for review (status: {status(run_id)})")
        if live.busy():
            raise HTTPException(409, "another audit is running")
        cfg = run_meta(run_id)
        m = models() if cfg["mode"] != "checks_only" else None
        decisions = {"decisions": [x.model_dump() for x in body.decisions]}
        req = d / "review_request.json"
        if req.exists():                # keep a copy of what the reviewer submitted next to the request
            (d / "review_submitted.json").write_text(json.dumps(decisions, indent=2))
        prior = live.runs.get(run_id, {"controls": {}})
        live.runs[run_id] = {"status": "running", "phase": "applying review", "error": None,
                             "controls": prior["controls"], "started": datetime.now(UTC).isoformat()}
        live.task = asyncio.create_task(drive(run_id, resume_audit(d, decisions, m, live.progress(run_id))))
        return {"run_id": run_id, "status": "running"}

    @app.get("/audits/{run_id}/report")
    def report(run_id: str, format: Literal["json", "md"] = "json"):
        d = run_dir(run_id)
        if not (d / "report.json").exists():
            raise HTTPException(409, "the report is written after review is submitted")
        if format == "md":
            return PlainTextResponse((d / "report.md").read_text(), media_type="text/markdown")
        return json.loads((d / "report.json").read_text())

    return app
