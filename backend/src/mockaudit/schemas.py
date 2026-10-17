"""Pydantic contracts shared by the generator, checks, graph, API and showcase (spec §4)."""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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
    gap_type: GapType = "operating"             # what a failure of this step is, for findings

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

    @field_validator("period")
    @classmethod
    def _period_ordered(cls, v):
        if v[0] > v[1]:
            raise ValueError("period start is after period end")
        return v

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
    candidates: list[Candidate] = []
    tested_counts: dict[str, int] = {}          # step id → items tested (code)
    samples: dict[str, list[str]] = {}          # judgment-only step id → record ids the tester inspects
    sample_facts: dict[str, dict] = {}          # judgment-only step id → item id → date facts (code)
    dropped_citations: list[Citation] = []
    cost_usd: float = 0.0
    tokens: int = 0
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
    control_timeout_s: int = 420
    run_spend_cap_usd: float = 1.0
    controls: list[str] | None = None           # optional subset (tests, debugging)


# ---------- LLM output contracts ----------

class CandidateDecision(Strict):
    candidate_id: str = Field(description="candidate_id exactly as given")
    decision: Literal["raise", "dismiss"]
    reason: str = Field(description="Why, grounded in records you looked at")
    citations: list[Citation] = Field(min_length=1, description="Records you looked at that support the decision")


class FindingDraft(Strict):
    test_step: str = Field(description="The recipe step id this finding is about")
    candidate_ids: list[str] = Field(default=[], description="Raised candidates this finding covers (empty for judgment-only steps)")
    condition: str = Field(description="What you found, naming the records")
    criteria: str = Field(description="The policy requirement, quoted or paraphrased with its section")
    cause: str | None = None
    effect: str
    recommendation: str
    citations: list[Citation] = Field(min_length=1)


class TesterOutput(Strict):
    """Final answer: one decision per candidate, and one finding per test step with raised items."""
    decisions: list[CandidateDecision] = []
    findings: list[FindingDraft] = []


class SkepticOutput(Strict):
    """Review of one draft finding."""
    decision: Literal["keep", "revise", "reject"]
    reason: str
    checks_failed: list[Literal["citation_mismatch", "out_of_period", "out_of_scope", "innocent_explanation",
                                "logic_error", "insufficient_evidence"]] = []


# ---------- JSON Schema for the frontend's generated TypeScript types ----------

def write_json_schema(path) -> None:
    """One schema whose $defs hold every type the UI reads (frontend/lib/types.gen.ts is generated from it)."""
    import json
    from pathlib import Path

    from pydantic.json_schema import models_json_schema

    models = [ControlSpec, Citation, CheckResult, ReasoningStep, Candidate, Finding, Dismissal, Coverage,
              ControlResult, SkepticVerdict, RunConfig]
    _, top = models_json_schema([(m, "serialization") for m in models], ref_template="#/$defs/{model}")
    schema = {"$schema": "https://json-schema.org/draft/2020-12/schema", "title": "MockAudit",
              "type": "object", "properties": {m.__name__: {"$ref": f"#/$defs/{m.__name__}"} for m in models},
              "$defs": top.get("$defs", {})}
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")
