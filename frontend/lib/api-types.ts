// Shapes the local API returns. Domain types come from the generated Pydantic schema (types.gen.ts).
import type { Citation, Dismissal, Finding, SkepticVerdict } from "./types.gen";

export type ControlState = "queued" | "running" | "revising" | "done" | "error";
export type AuditStatus = "running" | "paused" | "done" | "error" | "interrupted";
export type Mode = "agent" | "skeptic_off" | "checks_only";

export interface AppConfig {
  tester_model: string;
  skeptic_model: string;
  variants: string[];
  spend_usd: number;
  project_cap_usd: number;
  run_cap_usd: number;
  busy: boolean;
}

export interface AuditSummary {
  run_id: string;
  variant: string;
  mode: Mode;
  review_mode: "human" | "skip";
  status: AuditStatus;
}

export interface Audit {
  run_id: string;
  variant: string;
  mode: Mode;
  status: AuditStatus;
  phase: string;
  error: string | null;
  controls: Record<string, ControlState>;
  control_errors: Record<string, string>;
  cost_usd: number;
  tokens: number;
  llm_calls: number;
}

export type CitedRecord = Citation & { record: Record<string, unknown> | null };
export type Verdict = SkepticVerdict & { answered_by?: string; round: number };

export interface FindingView extends Finding {
  group: "findings" | "rejected" | "dismissed_on_revision";
  cited: CitedRecord[];
  verdicts: Verdict[];
  decision: { decision: string; note: string } | null;
}

export interface NotRaised extends Dismissal {
  cited: CitedRecord[];
}

export interface FindingsResponse {
  run_id: string;
  status: AuditStatus;
  findings: FindingView[];
  not_raised: NotRaised[];
}

export interface Decision {
  finding_id: string;
  decision: "approve" | "dismiss";
  note: string;
}

export interface Report {
  run_id: string;
  variant: string;
  mode: Mode;
  review_mode: string;
  statement: string;
  findings: (Finding & { review_note?: string })[];
  rejected_by_skeptic: string[];
  coverage: {
    control_id: string;
    status: string;
    error: string | null;
    tested: string[];
    not_tested: { step_id: string; reason: string }[];
    population_size: number;
    notes: string[];
  }[];
  remediation_tasks: { finding_id: string; owner_control: string; task: string; severity: string | null }[];
  totals: { cost_usd: number; tokens: number; llm_calls: number };
}

export interface Ratio {
  n: number;
  of: number;
  value: number | null;
}

export interface RunMetrics {
  recall: Ratio;
  precision: Ratio;
  clean_control_accuracy: Ratio;
  citation_validity: Ratio;
  severity_agreement: Ratio;
  traps_raised: Ratio;
}

/** frontend/public/data/index.json, written by `mockaudit export-showcase`. */
export interface ShowcaseIndex {
  generated: string;
  statement: string;
  runs: (AuditSummary & { reviewed: boolean; label: string; metrics: RunMetrics | null; cost_usd: number; tokens: number })[];
  eval: {
    eval_id: string;
    rows: { run_id: string; variant: string; mode: Mode; repeat: number; metrics: RunMetrics; cost_usd: number; tokens: number }[];
    targets: { metric: string; base: number | null; variant_mean: number | null; target: number; met: boolean }[];
    stability: { runs: string[]; pairwise: number[]; value: number | null; recall_per_run: number[] };
    cost: { per_audit_usd: number | null; per_audit_tokens: number | null; eval_total_usd: number; eval_cap_usd: number };
  } | null;
}
