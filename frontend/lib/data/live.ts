import type { AppConfig, Audit, AuditSummary, Decision, FindingsResponse, Mode, Report } from "../api-types";
import { ApiError, ApiUnreachableError } from "./errors";
import type { DataSource } from "./source";

/** Talks to the local FastAPI (`uv run mockaudit serve`). */
export function liveSource(base: string, fetchImpl: typeof fetch = (...a) => fetch(...a)): DataSource {
  async function call(path: string, init?: RequestInit): Promise<Response> {
    let res: Response;
    try {
      res = await fetchImpl(`${base}${path}`, {
        ...init,
        headers: { "content-type": "application/json", ...(init?.headers ?? {}) },
      });
    } catch {
      throw new ApiUnreachableError();
    }
    if (!res.ok) {
      let detail = `${res.status} ${res.statusText}`;
      try {
        const body = await res.json();
        if (typeof body?.detail === "string") detail = body.detail;
      } catch {
        /* not JSON */
      }
      throw new ApiError(res.status, detail);
    }
    return res;
  }
  const json = async <T>(path: string, init?: RequestInit) => (await (await call(path, init)).json()) as T;

  return {
    mode: "live",
    getConfig: () => json<AppConfig>("/config"),
    listAudits: () => json<AuditSummary[]>("/audits"),
    startAudit: (variant, mode: Mode) =>
      json<{ run_id: string }>("/audits", { method: "POST", body: JSON.stringify({ variant, mode }) }),
    getAudit: (id) => json<Audit>(`/audits/${encodeURIComponent(id)}`),
    getFindings: (id) => json<FindingsResponse>(`/audits/${encodeURIComponent(id)}/findings`),
    submitReview: async (id, decisions: Decision[]) => {
      await call(`/audits/${encodeURIComponent(id)}/review`, { method: "POST", body: JSON.stringify({ decisions }) });
    },
    getReport: (id) => json<Report>(`/audits/${encodeURIComponent(id)}/report`),
    getReportMarkdown: async (id) => (await call(`/audits/${encodeURIComponent(id)}/report?format=md`)).text(),
  };
}
