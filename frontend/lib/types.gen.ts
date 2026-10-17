/* Generated from the Pydantic schemas by `npm run gen:types`. Do not edit. */

/**
 * This interface was referenced by `MockAudit`'s JSON-Schema
 * via the `definition` "Frequency".
 */
export type Frequency = "event" | "continuous" | "daily" | "weekly" | "monthly" | "quarterly" | "annual";

export interface MockAudit {
  Candidate?: Candidate;
  CheckResult?: CheckResult;
  Citation?: Citation;
  ControlResult?: ControlResult;
  ControlSpec?: ControlSpec;
  Coverage?: Coverage1;
  Dismissal?: Dismissal;
  Finding?: Finding;
  ReasoningStep?: ReasoningStep;
  RunConfig?: RunConfig;
  SkepticVerdict?: SkepticVerdict;
}
/**
 * An item code flagged (check failure or missing from the population).
 *
 * This interface was referenced by `MockAudit`'s JSON-Schema
 * via the `definition` "Candidate".
 */
export interface Candidate {
  candidate_id: string;
  /**
   * @minItems 1
   */
  citations: [Citation, ...Citation[]];
  control_id: string;
  detail: string;
  gap_type:
    | "operating"
    | "population_completeness"
    | "segregation_of_duties"
    | "frequency_gap"
    | "sla_breach"
    | "evidence_out_of_period"
    | "missing_evidence"
    | "design";
  record_id: string;
  test_step: string;
}
/**
 * This interface was referenced by `MockAudit`'s JSON-Schema
 * via the `definition` "Citation".
 */
export interface Citation {
  record_id: string;
  source: string;
}
/**
 * This interface was referenced by `MockAudit`'s JSON-Schema
 * via the `definition` "CheckResult".
 */
export interface CheckResult {
  detail?: {
    [k: string]: unknown;
  };
  passed: boolean;
  record_id: string | null;
  step_id: string;
}
/**
 * This interface was referenced by `MockAudit`'s JSON-Schema
 * via the `definition` "ControlResult".
 */
export interface ControlResult {
  agent?: string;
  candidates?: Candidate[];
  check_results?: CheckResult[];
  control_id: string;
  cost_usd?: number;
  coverage?: Coverage;
  dismissals?: Dismissal[];
  dropped_citations?: Citation[];
  error?: string | null;
  findings?: Finding[];
  missing_from_population?: string[];
  model?: string;
  notes?: string[];
  owner_questions?: {
    [k: string]: unknown;
  }[];
  population_complete?: boolean;
  population_size?: number;
  revision_round?: number;
  run_id?: string;
  sample?: string[];
  sample_facts?: {
    [k: string]: {
      [k: string]: unknown;
    };
  };
  samples?: {
    [k: string]: string[];
  };
  status: "pass" | "exceptions" | "error";
  tested_counts?: {
    [k: string]: number;
  };
  tokens?: number;
}
export interface Coverage {
  not_tested?: {
    [k: string]: unknown;
  }[];
  tested: string[];
}
/**
 * This interface was referenced by `MockAudit`'s JSON-Schema
 * via the `definition` "Dismissal".
 */
export interface Dismissal {
  candidate_id: string;
  /**
   * @minItems 1
   */
  citations: [Citation, ...Citation[]];
  control_id: string;
  reason: string;
  reasoning?: ReasoningStep[];
}
/**
 * This interface was referenced by `MockAudit`'s JSON-Schema
 * via the `definition` "ReasoningStep".
 */
export interface ReasoningStep {
  kind: "check" | "tool" | "owner" | "llm" | "rule";
  text: string;
}
/**
 * This interface was referenced by `MockAudit`'s JSON-Schema
 * via the `definition` "Finding".
 */
export interface Finding {
  cause?: string | null;
  /**
   * @minItems 1
   */
  citations: [Citation, ...Citation[]];
  condition: string;
  control_id: string;
  criteria: string;
  effect: string;
  exceptions: number;
  finding_id: string;
  gap_type:
    | "operating"
    | "population_completeness"
    | "segregation_of_duties"
    | "frequency_gap"
    | "sla_breach"
    | "evidence_out_of_period"
    | "missing_evidence"
    | "design";
  reasoning?: ReasoningStep[];
  recommendation: string;
  severity?: ("low" | "moderate" | "high") | null;
  severity_rule?: number | null;
  status?: "draft" | "kept" | "unresolved" | "rejected" | "approved" | "dismissed";
  test_step: string;
  tested: number;
}
/**
 * This interface was referenced by `MockAudit`'s JSON-Schema
 * via the `definition` "ControlSpec".
 */
export interface ControlSpec {
  agent_type?: string;
  automated: boolean;
  control_id: string;
  description: string;
  /**
   * @minItems 1
   */
  evidence: [EvidenceSource, ...EvidenceSource[]];
  frequency: Frequency;
  owner: string;
  /**
   * @minItems 2
   * @maxItems 2
   */
  period: [unknown, unknown];
  risk: "low" | "moderate" | "high";
  /**
   * @minItems 1
   */
  test_recipe: [TestStep, ...TestStep[]];
  /**
   * @minItems 1
   */
  tsc: [string, ...string[]];
}
/**
 * This interface was referenced by `MockAudit`'s JSON-Schema
 * via the `definition` "EvidenceSource".
 */
export interface EvidenceSource {
  name: string;
  path: string;
  record_id_field?: string | null;
  role: "population" | "independent" | "supporting" | "policy" | "artifact";
}
/**
 * This interface was referenced by `MockAudit`'s JSON-Schema
 * via the `definition` "TestStep".
 */
export interface TestStep {
  check?: string | null;
  description: string;
  gap_type?:
    | "operating"
    | "population_completeness"
    | "segregation_of_duties"
    | "frequency_gap"
    | "sla_breach"
    | "evidence_out_of_period"
    | "missing_evidence"
    | "design";
  id: string;
  judge?: "none" | "llm";
  params?: {
    [k: string]: unknown;
  };
}
/**
 * This interface was referenced by `MockAudit`'s JSON-Schema
 * via the `definition` "Coverage".
 */
export interface Coverage1 {
  not_tested?: {
    [k: string]: unknown;
  }[];
  tested: string[];
}
/**
 * This interface was referenced by `MockAudit`'s JSON-Schema
 * via the `definition` "RunConfig".
 */
export interface RunConfig {
  control_timeout_s?: number;
  controls?: string[] | null;
  max_concurrency?: number;
  mode?: "agent" | "skeptic_off" | "checks_only";
  review_mode?: "human" | "skip";
  run_id: string;
  run_spend_cap_usd?: number;
  skeptic_model?: string;
  tester_model?: string;
  variant?: string;
}
/**
 * This interface was referenced by `MockAudit`'s JSON-Schema
 * via the `definition` "SkepticVerdict".
 */
export interface SkepticVerdict {
  checks_failed?: (
    | "citation_mismatch"
    | "out_of_period"
    | "out_of_scope"
    | "innocent_explanation"
    | "logic_error"
    | "insufficient_evidence"
  )[];
  decision: "keep" | "revise" | "reject";
  finding_id: string;
  reason: string;
  reviewer?: string;
}
