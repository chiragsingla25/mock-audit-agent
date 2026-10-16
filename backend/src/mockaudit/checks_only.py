"""`run --checks-only`: every check over every control, candidates grouped into findings. No LLM.

This is the rules-only baseline the agent is compared against (spec Phase 2).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from mockaudit.checks import run_control_checks
from mockaudit.citations import check_citations
from mockaudit.evidence import Evidence
from mockaudit.schemas import (
    Candidate,
    ControlResult,
    ControlSpec,
    Coverage,
    Finding,
    ReasoningStep,
    RunConfig,
)
from mockaudit.severity import severity
from mockaudit.specs import load_controls


def findings_from_candidates(spec: ControlSpec, step_id: str, cands: list[Candidate], tested: int) -> Finding:
    """One finding per (control, step), grouping the step's failed records. Severity from the rules."""
    step = next(s for s in spec.test_recipe if s.id == step_id)
    sev, rule = severity(step.gap_type, len(cands), tested, spec.risk, spec.periodic)
    cites, seen = [], set()
    for c in cands:
        for cit in c.citations:
            if (cit.source, cit.record_id) not in seen:
                seen.add((cit.source, cit.record_id))
                cites.append(cit)
    listed = ", ".join(c.record_id for c in cands[:6]) + (" …" if len(cands) > 6 else "")
    return Finding(
        finding_id=f"{spec.control_id}-{step_id}", control_id=spec.control_id, test_step=step_id,
        gap_type=step.gap_type, exceptions=len(cands), tested=tested,
        condition=f"{len(cands)} of {tested} items failed: {listed}. {cands[0].detail}",
        criteria=step.description, cause=None,
        effect=f"The control '{spec.description}' did not operate as designed for these items.",
        recommendation="Investigate each exception with the control owner and remediate.",
        citations=cites, severity=sev, severity_rule=rule, status="kept",
        reasoning=[ReasoningStep(kind="check", text=f"{step.check}: {len(cands)} of {tested} failed"),
                   ReasoningStep(kind="rule", text=f"severity rule {rule} → {sev}")])


def run_checks_on_control(spec: ControlSpec, data_dir: Path, run_id: str) -> ControlResult:
    ev = Evidence.load(spec, data_dir)
    cc = run_control_checks(spec, ev)
    index = ev.index()
    findings, dropped = [], []
    for step in spec.test_recipe:
        cands = [c for c in cc.candidates if c.test_step == step.id]
        if not cands:
            continue
        f = findings_from_candidates(spec, step.id, cands, cc.tested[step.id])
        f.citations, gone = check_citations(f.citations, index, f.finding_id)
        dropped += gone
        if f.citations:
            findings.append(f)
    missing = [c.record_id for c in cc.candidates if c.gap_type == "population_completeness"]
    return ControlResult(
        control_id=spec.control_id, status="exceptions" if findings else "pass",
        population_size=max(cc.tested.values(), default=0), population_complete=not missing,
        missing_from_population=missing, notes=cc.notes, candidates=cc.candidates, dropped_citations=dropped,
        check_results=cc.results, findings=findings,
        coverage=Coverage(tested=[s.id for s in spec.test_recipe if s.check],
                          not_tested=[{"step_id": s.id, "reason": "judgment-only step (checks-only mode)"}
                                      for s in spec.test_recipe if not s.check]),
        agent="checks-only", model="none", run_id=run_id)


def run_checks_only(variant: str, data_root: Path, runs_dir: Path, run_id: str | None = None) -> Path:
    data_dir = Path(data_root) / variant
    if not (data_dir / "controls.yaml").exists():
        raise FileNotFoundError(f"no dataset at {data_dir}; run `mockaudit gen --variant {variant}` first")
    run_id = run_id or f"checks-{variant}-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    out = Path(runs_dir) / run_id
    (out / "controls").mkdir(parents=True, exist_ok=True)
    results = [run_checks_on_control(s, data_dir, run_id) for s in load_controls(data_dir / "controls.yaml")]
    for r in results:
        (out / "controls" / f"{r.control_id}.json").write_text(r.model_dump_json(indent=2))
    cfg = RunConfig(run_id=run_id, variant=variant, mode="checks_only", review_mode="skip")
    (out / "run.json").write_text(json.dumps({"config": cfg.model_dump(), "data_dir": str(data_dir.resolve()),
                                              "findings": sum(len(r.findings) for r in results)}, indent=2))
    (Path(runs_dir) / "LATEST").write_text(run_id + "\n")
    return out
