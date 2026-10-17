"""Static showcase export (spec Phase 6): the JSON the GitHub Pages site reads, validated against these models.

Layout under frontend/public/data/:
  index.json                         runs + evaluation summary
  runs/<run_id>/audit.json           same shape as GET /audits/{id}
  runs/<run_id>/findings.json        same shape as GET /audits/{id}/findings (cited records only)
  runs/<run_id>/report.json          same shape as GET /audits/{id}/report
  runs/<run_id>/report.md            same as GET /audits/{id}/report?format=md
"""

from __future__ import annotations

import asyncio
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from mockaudit.evaluation import metrics_for
from mockaudit.report import render_md
from mockaudit.schemas import Citation, Dismissal, Finding, SkepticVerdict
from mockaudit.views import audit_from_disk, disk_status, findings_view, run_config


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CitedRecord(Citation):
    record: dict | None


class VerdictView(SkepticVerdict):
    decision: Literal["keep", "revise", "reject", "error"]
    answered_by: str | None = None
    round: int


class FindingView(Finding):
    group: Literal["findings", "rejected", "dismissed_on_revision"]
    cited: list[CitedRecord]
    verdicts: list[VerdictView]
    decision: dict | None


class NotRaisedView(Dismissal):
    cited: list[CitedRecord]


class FindingsView(Strict):
    run_id: str
    status: str
    findings: list[FindingView]
    not_raised: list[NotRaisedView]


class AuditView(Strict):
    run_id: str
    variant: str
    mode: str
    status: str
    phase: str
    error: str | None
    controls: dict[str, Literal["queued", "running", "revising", "done", "error"]]
    control_errors: dict[str, str]
    cost_usd: float
    tokens: int
    llm_calls: int


class ReportFinding(Finding):
    review_note: str = ""


class CoverageRow(Strict):
    control_id: str
    status: str
    error: str | None
    tested: list[str]
    not_tested: list[dict]
    population_size: int
    notes: list[str]


class ReportView(Strict):
    run_id: str
    variant: str
    mode: str
    review_mode: str
    statement: str
    findings: list[ReportFinding]
    rejected_by_skeptic: list[str]
    coverage: list[CoverageRow]
    remediation_tasks: list[dict]
    totals: dict


class Ratio(Strict):
    n: int
    of: int
    value: float | None


class RunMetrics(Strict):
    recall: Ratio
    precision: Ratio
    clean_control_accuracy: Ratio
    citation_validity: Ratio
    severity_agreement: Ratio
    traps_raised: Ratio


class RunEntry(Strict):
    run_id: str
    variant: str
    mode: str
    review_mode: str
    status: str
    reviewed: bool
    label: str
    metrics: RunMetrics | None
    cost_usd: float
    tokens: int


class EvalRow(Strict):
    run_id: str
    variant: str
    mode: Literal["agent", "skeptic_off", "checks_only"]
    repeat: int
    metrics: RunMetrics
    cost_usd: float
    tokens: int


class EvalSummary(Strict):
    eval_id: str
    rows: list[EvalRow]
    targets: list[dict]
    stability: dict
    cost: dict


class ShowcaseIndex(Strict):
    generated: str
    statement: str
    runs: list[RunEntry]
    eval: EvalSummary | None


METRIC_KEYS = list(RunMetrics.model_fields)


def _metrics(m: dict) -> dict:
    return {k: m[k] for k in METRIC_KEYS}


def export_showcase(run_ids: list[str], runs_dir: Path, data_root: Path, out_dir: Path, eval_id: str | None = None) -> Path:
    return asyncio.run(export_showcase_async(run_ids, runs_dir, data_root, out_dir, eval_id))


async def export_showcase_async(run_ids: list[str], runs_dir: Path, data_root: Path, out_dir: Path,
                                eval_id: str | None = None) -> Path:
    runs_dir, data_root, out_dir = Path(runs_dir), Path(data_root), Path(out_dir)
    if out_dir.parts[-2:] != ("public", "data"):
        raise ValueError(f"refusing to replace {out_dir}: the showcase output folder must be <frontend>/public/data")
    for run_id in run_ids:                          # check everything before deleting anything
        d = runs_dir / run_id
        if not (d / "config.json").exists():
            raise FileNotFoundError(f"no run {run_id!r} in {runs_dir}")
        if disk_status(d) != "done":
            raise ValueError(f"run {run_id} is {disk_status(d)}; only finished runs (report written) are published")
    if eval_id and not (runs_dir / eval_id / "eval.json").exists():
        raise FileNotFoundError(f"no evaluation {eval_id!r} in {runs_dir}")
    if out_dir.exists():
        shutil.rmtree(out_dir)
    spend = runs_dir / "spend.jsonl"
    entries = []
    for run_id in run_ids:
        d = runs_dir / run_id
        if not (d / "config.json").exists():
            raise FileNotFoundError(f"no run {run_id} in {runs_dir}")
        cfg, status = run_config(d), disk_status(d)
        if status != "done":
            raise ValueError(f"run {run_id} is {status}; only finished runs (report written) are published")
        target = out_dir / "runs" / run_id
        target.mkdir(parents=True)
        audit = AuditView.model_validate(audit_from_disk(d, spend))
        findings = FindingsView.model_validate(await findings_view(d, data_root, status))
        report = ReportView.model_validate(json.loads((d / "report.json").read_text()))
        for name, model in [("audit.json", audit), ("findings.json", findings), ("report.json", report)]:
            (target / name).write_text(model.model_dump_json(indent=1) + "\n")
        (target / "report.md").write_text(render_md(report.model_dump()))       # re-rendered with current wording
        reviewed = cfg["review_mode"] == "human" and (d / "review_decisions.json").exists()
        label = f"{'Ledgerly base' if cfg['variant'] == 'base' else 'Variant ' + cfg['variant'].upper()} · " \
                f"{cfg['mode'].replace('_', ' ')}" + (" · human-reviewed" if reviewed else " · not reviewed") + \
                (f" · stability run {run_id[-1]}" if run_id[-3:] in ("-r2", "-r3") else "")
        entries.append(RunEntry(run_id=run_id, variant=cfg["variant"], mode=cfg["mode"], review_mode=cfg["review_mode"],
                                status=status, reviewed=reviewed, label=label,
                                metrics=RunMetrics.model_validate(_metrics(metrics_for(d, data_root / cfg["variant"]))),
                                cost_usd=audit.cost_usd, tokens=audit.tokens))
    summary = None
    if eval_id:
        e = json.loads((runs_dir / eval_id / "eval.json").read_text())
        rows = [EvalRow(run_id=r.get("derived_from", r["run_id"]), variant=r["variant"], mode=r["mode"],
                        repeat=r.get("repeat", 1), metrics=RunMetrics.model_validate(_metrics(r["metrics"])),
                        cost_usd=r["cost_usd"], tokens=r["tokens"]) for r in e["rows"]]
        summary = EvalSummary(eval_id=eval_id, rows=rows, targets=e["targets"], stability=e["stability"], cost=e["cost"])
    index = ShowcaseIndex(generated=datetime.now(UTC).isoformat(timespec="seconds"),
                          statement="Readiness forecast from synthetic evidence (Ledgerly is fictional). Not an audit opinion.",
                          runs=entries, eval=summary)
    (out_dir / "index.json").write_text(index.model_dump_json(indent=1) + "\n")
    return out_dir


def validate_showcase(out_dir: Path) -> int:
    """Re-validate every published file (CI). Returns the number of files checked."""
    out_dir = Path(out_dir)
    index = ShowcaseIndex.model_validate_json((out_dir / "index.json").read_text())
    n = 1
    for run in index.runs:
        d = out_dir / "runs" / run.run_id
        AuditView.model_validate_json((d / "audit.json").read_text())
        FindingsView.model_validate_json((d / "findings.json").read_text())
        ReportView.model_validate_json((d / "report.json").read_text())
        if "Not an audit opinion" not in (d / "report.md").read_text():
            raise ValueError(f"{d / 'report.md'} lacks the readiness statement")
        n += 4
    published = {r.run_id for r in index.runs}
    if index.eval:
        for row in index.eval.rows:
            if row.mode != "skeptic_off" and row.run_id not in published:
                raise ValueError(f"eval row {row.run_id} has no published run")
    return n
