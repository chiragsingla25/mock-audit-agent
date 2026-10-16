"""Run and resume audits: compile the graph with a SQLite checkpointer and invoke it."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command

from mockaudit.graph import AuditContext, build_graph
from mockaudit.schemas import RunConfig


def new_run_id(mode: str, variant: str) -> str:
    prefix = {"agent": "audit", "checks_only": "checks", "skeptic_off": "noskeptic"}[mode]
    return f"{prefix}-{variant}-{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ')[:-4]}"


def make_context(cfg: RunConfig, data_root: Path, runs_dir: Path, models=None, spend_path: Path | None = None) -> AuditContext:
    spend = None
    if cfg.mode != "checks_only":
        from mockaudit.llm import Spend
        spend = Spend(spend_path or Path(runs_dir) / "spend.jsonl", cfg.run_id, cfg.run_spend_cap_usd,
                      float(os.environ.get("PROJECT_SPEND_CAP_USD", "9.50")))
    return AuditContext(data_dir=Path(data_root) / cfg.variant, run_dir=Path(runs_dir) / cfg.run_id, models=models,
                        spend=spend, timeout_s=cfg.control_timeout_s)


def _invoke_config(cfg: RunConfig) -> dict:
    return {"configurable": {"thread_id": cfg.run_id}, "max_concurrency": cfg.max_concurrency,
            "run_name": f"audit:{cfg.run_id}", "tags": [cfg.mode, cfg.variant], "recursion_limit": 100}


async def run_audit(cfg: RunConfig, data_root: Path, runs_dir: Path, models=None, spend_path: Path | None = None) -> dict:
    data_dir = Path(data_root) / cfg.variant
    if not (data_dir / "controls.yaml").exists():
        raise FileNotFoundError(f"no dataset at {data_dir}; run `mockaudit gen --variant {cfg.variant}` first")
    ctx = make_context(cfg, data_root, runs_dir, models, spend_path)
    ctx.run_dir.mkdir(parents=True, exist_ok=True)
    (ctx.run_dir / "config.json").write_text(json.dumps({"config": cfg.model_dump(), "data_root": str(Path(data_root).resolve()),
                                                          "spend_path": str(spend_path) if spend_path else None}, indent=2))
    async with AsyncSqliteSaver.from_conn_string(str(ctx.run_dir / "checkpoints.db")) as saver:
        app = build_graph().compile(checkpointer=saver)
        out = await app.ainvoke({"config": cfg.model_dump()}, config=_invoke_config(cfg), context=ctx)
    return _summary(out, ctx)


async def resume_audit(run_dir: Path, decisions: dict | list, models=None) -> dict:
    meta = json.loads((Path(run_dir) / "config.json").read_text())
    cfg = RunConfig.model_validate(meta["config"])
    spend_path = Path(meta["spend_path"]) if meta.get("spend_path") else None
    ctx = make_context(cfg, Path(meta["data_root"]), Path(run_dir).parent, models, spend_path)
    async with AsyncSqliteSaver.from_conn_string(str(ctx.run_dir / "checkpoints.db")) as saver:
        app = build_graph().compile(checkpointer=saver)
        out = await app.ainvoke(Command(resume=decisions), config=_invoke_config(cfg), context=ctx)
    return _summary(out, ctx)


def _summary(out: dict, ctx: AuditContext) -> dict:
    if out.get("__interrupt__"):
        return {"status": "paused", "run_dir": str(ctx.run_dir), "review_request": str(ctx.run_dir / "review_request.json")}
    return {"status": "done", "run_dir": str(ctx.run_dir), **out.get("report", {})}
