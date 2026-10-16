"""Pydantic contracts shared by the generator, checks, graph, API and showcase (spec §4)."""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

PERIOD = (date(2025, 10, 1), date(2026, 9, 30))

GapType = Literal[
    "operating", "population_completeness", "segregation_of_duties", "frequency_gap",
    "sla_breach", "evidence_out_of_period", "missing_evidence", "design",
]
Risk = Literal["low", "moderate", "high"]
Severity = Literal["low", "moderate", "high"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Frequency(str, Enum):
    event = "event"
    continuous = "continuous"
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"
    quarterly = "quarterly"
    annual = "annual"


class EvidenceSource(Strict):
    name: str                                   # "okta_events"
    path: str                                   # "exports/okta_system_log.csv"
    role: Literal["population", "independent", "supporting", "policy", "artifact"]
    record_id_field: str | None = None          # column used as record_id for citations


class TestStep(Strict):
    id: str
    description: str
    check: str | None = None                    # name in CHECKS, or None for pure judgment
    params: dict = {}
    judge: Literal["none", "llm"] = "llm"

    @model_validator(mode="after")
    def _judgment_needs_llm(self):
        if self.check is None and self.judge == "none":
            raise ValueError("a step with no check must have judge: llm")
        return self


class ControlSpec(Strict):
    control_id: str = Field(pattern=r"^C\d+$")
    agent_type: str = "default"
    description: str
    tsc: list[str] = Field(min_length=1)
    frequency: Frequency
    automated: bool
    risk: Risk
    owner: str
    period: tuple[date, date]
    evidence: list[EvidenceSource] = Field(min_length=1)
    test_recipe: list[TestStep] = Field(min_length=1)

    @model_validator(mode="after")
    def _period_ordered(self):
        if self.period[0] > self.period[1]:
            raise ValueError("period start is after period end")
        return self

    @property
    def periodic(self) -> bool:
        return self.frequency in {Frequency.daily, Frequency.weekly, Frequency.monthly,
                                  Frequency.quarterly, Frequency.annual}


class Citation(Strict):
    source: str
    record_id: str


class CheckResult(Strict):
    step_id: str
    record_id: str | None
    passed: bool
    detail: dict = {}


class ReasoningStep(Strict):
    kind: Literal["check", "tool", "owner", "llm", "rule"]
    text: str


class Candidate(Strict):
    """An item code flagged (check failure or missing from the population)."""
    candidate_id: str
    control_id: str
    test_step: str
    record_id: str
    gap_type: GapType
    detail: str
    citations: list[Citation] = Field(min_length=1)


class Finding(Strict):
    finding_id: str
    control_id: str
    test_step: str
    gap_type: GapType
    exceptions: int                             # set by code
    tested: int                                 # set by code
    condition: str
    criteria: str
    cause: str | None = None
    effect: str
    recommendation: str
    citations: list[Citation] = Field(min_length=1)
    severity: Severity | None = None            # set by rules, never the LLM
    severity_rule: int | None = None
    status: Literal["draft", "kept", "unresolved", "rejected", "approved", "dismissed"] = "draft"
    reasoning: list[ReasoningStep] = []


class Dismissal(Strict):
    candidate_id: str
    control_id: str
    reason: str
    citations: list[Citation] = Field(min_length=1)
    reasoning: list[ReasoningStep] = []


class Coverage(Strict):
    tested: list[str]
    not_tested: list[dict] = []


class ControlResult(Strict):
    control_id: str
    status: Literal["pass", "exceptions", "error"]
    error: str | None = None
    population_size: int = 0
    population_complete: bool = True
    missing_from_population: list[str] = []
    notes: list[str] = []
    sample: list[str] = []
    check_results: list[CheckResult] = []
    findings: list[Finding] = []
    dismissals: list[Dismissal] = []
    coverage: Coverage = Coverage(tested=[])
    owner_questions: list[dict] = []
    agent: str = "default"
    model: str = ""
    run_id: str = ""
    revision_round: int = 0


class SkepticVerdict(Strict):
    finding_id: str
    decision: Literal["keep", "revise", "reject"]
    reason: str
    checks_failed: list[Literal["citation_mismatch", "out_of_period", "out_of_scope",
                                "innocent_explanation", "logic_error",
                                "insufficient_evidence"]] = []
    reviewer: str = ""


class RunConfig(Strict):
    run_id: str
    variant: str = "base"
    mode: Literal["agent", "skeptic_off", "checks_only"] = "agent"
    review_mode: Literal["human", "skip"] = "skip"
    tester_model: str = ""
    skeptic_model: str = ""
    max_concurrency: int = 4
    control_timeout_s: int = 180
    run_spend_cap_usd: float = 1.0
