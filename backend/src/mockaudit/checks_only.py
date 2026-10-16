"""Code findings from candidates: one finding per (control, step). Used by checks-only runs and `judge: none` steps."""

from __future__ import annotations

from mockaudit.schemas import (
    Candidate,
    ControlSpec,
    Finding,
    ReasoningStep,
)
from mockaudit.severity import severity


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
