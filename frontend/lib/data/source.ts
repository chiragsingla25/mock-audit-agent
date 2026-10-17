import type { AppConfig, Audit, AuditSummary, Decision, FindingsResponse, Mode, Report } from "../api-types";

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
}
