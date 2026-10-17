import type { AppConfig, Audit, AuditSummary, Decision, FindingsResponse, Mode, Report, ShowcaseIndex } from "../api-types";

/** Everything a screen can ask for. Screens use this, never `fetch`. */
export interface DataSource {
  mode: "live" | "showcase";
  getConfig(): Promise<AppConfig>;
  listAudits(): Promise<AuditSummary[]>;
  startAudit(variant: string, mode: Mode): Promise<{ run_id: string }>;
  getAudit(runId: string): Promise<Audit>;
  getFindings(runId: string): Promise<FindingsResponse>;
  submitReview(runId: string, decisions: Decision[]): Promise<void>;
  getReport(runId: string): Promise<Report>;
  getReportMarkdown(runId: string): Promise<string>;
  /** Showcase only: the published runs and evaluation summary (live mode: null). */
  getIndex(): Promise<ShowcaseIndex | null>;
}
