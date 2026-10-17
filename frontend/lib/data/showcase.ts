import type { AppConfig, Audit, AuditSummary, FindingsResponse, Report, ShowcaseIndex } from "../api-types";
import { ApiError } from "./errors";
import type { DataSource } from "./source";

const READ_ONLY = "This is the static showcase: audits are run locally and published with their review decisions.";

/** Static showcase (GitHub Pages): reads the JSON `mockaudit export-showcase` wrote under /data. Read-only. */
export function showcaseSource(basePath = "", fetchImpl: typeof fetch = (...a) => fetch(...a)): DataSource {
  async function get(path: string): Promise<Response> {
    const res = await fetchImpl(`${basePath}/data/${path}`);
    if (!res.ok) throw new ApiError(res.status, res.status === 404 ? "This run isn't published." : `${res.status} ${res.statusText}`);
    return res;
  }
  const json = async <T>(path: string) => (await (await get(path)).json()) as T;
  const run = (id: string, file: string) => `runs/${encodeURIComponent(id)}/${file}`;
  let index: Promise<ShowcaseIndex> | null = null;
  const getIndex = () => (index ??= json<ShowcaseIndex>("index.json"));

  return {
    mode: "showcase",
    getIndex,
    getConfig: async (): Promise<AppConfig> => ({
      tester_model: "", skeptic_model: "", variants: [], spend_usd: 0, project_cap_usd: 0, run_cap_usd: 0, busy: false,
    }),
    listAudits: async (): Promise<AuditSummary[]> => (await getIndex()).runs,
    startAudit: () => Promise.reject(new Error(READ_ONLY)),
    submitReview: () => Promise.reject(new Error(READ_ONLY)),
    getAudit: (id) => json<Audit>(run(id, "audit.json")),
    getFindings: (id) => json<FindingsResponse>(run(id, "findings.json")),
    getReport: (id) => json<Report>(run(id, "report.json")),
    getReportMarkdown: async (id) => (await get(run(id, "report.md"))).text(),
  };
}
