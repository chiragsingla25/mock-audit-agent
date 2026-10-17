import type { DataSource } from "./source";

const notYet = () => Promise.reject(new Error("Showcase mode arrives in Phase 6 (static JSON under /data)."));

/** Static showcase (GitHub Pages). Filled in Phase 6; read-only, no start button. */
export function showcaseSource(): DataSource {
  return {
    mode: "showcase",
    getConfig: notYet,
    listAudits: notYet,
    startAudit: notYet,
    getAudit: notYet,
    getFindings: notYet,
    submitReview: notYet,
    getReport: notYet,
    getReportMarkdown: notYet,
  };
}
