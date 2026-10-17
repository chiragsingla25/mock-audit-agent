"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import type { Report } from "@/lib/api-types";
import { ApiError, data } from "@/lib/data";
import { Badge, Button, Card, ErrorBanner, PageTitle, severityTone, usd } from "./ui";
import { useRunId } from "./useRunId";

function download(name: string, text: string, type: string) {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

/** Coverage status in words. There is deliberately no pass badge: no exceptions found is not an audit opinion. */
function coverageLabel(status: string, notes: string[], tested: string[]) {
  if (status !== "pass") return status;
  if (notes.some((n) => n.includes("dismissed in review"))) return "exceptions dismissed in review";
  return tested.length ? "no exceptions found" : "not tested";
}

export function ReportScreen() {
  const runId = useRunId();
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!runId) return;
    data.getReport(runId).then(setReport).catch((e) =>
      setError(e instanceof ApiError && e.status === 409 ? "The report is written after the review is submitted." : (e as Error).message));
  }, [runId]);

  async function exportMd() {
    try {
      download(`${runId}-report.md`, await data.getReportMarkdown(runId), "text/markdown");
    } catch (e) {
      setError((e as Error).message);
    }
  }

  if (!runId) return <ErrorBanner message="No audit selected." />;
  return (
    <div>
      <PageTitle title="Readiness report" sub={<>{runId} · {report ? `${report.variant} · ${report.mode}` : "loading…"}</>} />
      {error && <div className="mb-4 space-y-2"><ErrorBanner message={error} /><Link className="text-sm underline" href={`/findings?run=${runId}`}>Go to findings</Link></div>}
      {report && (
        <div className="space-y-5">
          <Card className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm">{report.statement}</p>
            <div className="flex gap-2">
              <Button variant="secondary" onClick={exportMd}>Export Markdown</Button>
              <Button variant="secondary" onClick={() => download(`${runId}-report.json`, JSON.stringify(report, null, 2), "application/json")}>Export JSON</Button>
            </div>
          </Card>

          <section>
            <h2 className="mb-2 font-semibold">
              {report.review_mode === "human" ? "Approved findings" : "Findings"} ({report.findings.length})
            </h2>
            {report.review_mode !== "human" && (
              <p className="mb-2 text-sm text-slate-500">Not reviewed by a person: these are the findings this run kept, before any human review.</p>
            )}
            <div className="space-y-3">
              {report.findings.length === 0 && <Card className="text-sm text-slate-500">No findings were approved.</Card>}
              {report.findings.map((f) => (
                <Card key={f.finding_id}>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-semibold">{f.finding_id}</span>
                    <Badge tone={severityTone(f.severity)}>{f.severity}</Badge>
                    <span className="text-sm text-slate-500">{f.exceptions} of {f.tested}</span>
                  </div>
                  <p className="mt-2 text-sm">{f.condition}</p>
                  <p className="mt-1 text-sm text-slate-500"><b>Criteria:</b> {f.criteria}</p>
                  {f.review_note && <p className="mt-1 text-sm"><b>Reviewer note:</b> {f.review_note}</p>}
                </Card>
              ))}
            </div>
          </section>

          <section>
            <h2 className="mb-2 font-semibold">Coverage per control</h2>
            <Card className="overflow-x-auto p-0">
              <table className="w-full text-sm">
                <thead className="text-left text-xs text-slate-500"><tr>
                  <th className="px-3 py-2">Control</th><th className="px-3 py-2">Status</th><th className="px-3 py-2">Steps tested</th>
                  <th className="px-3 py-2">Not tested</th><th className="px-3 py-2">Population</th></tr></thead>
                <tbody>
                  {report.coverage.map((c) => (
                    <tr key={c.control_id} className="border-t border-slate-100 dark:border-slate-800">
                      <td className="px-3 py-2 font-medium">{c.control_id}</td>
                      <td className="px-3 py-2">{c.status === "error" ? <Badge tone="red">error</Badge> : coverageLabel(c.status, c.notes, c.tested)}</td>
                      <td className="px-3 py-2">{c.tested.join(", ") || "—"}</td>
                      <td className="px-3 py-2">{c.not_tested.map((n) => n.step_id).join(", ") || "—"}</td>
                      <td className="px-3 py-2">{c.population_size}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          </section>

          <section>
            <h2 className="mb-2 font-semibold">Remediation tasks</h2>
            <Card>
              <ul className="space-y-1.5 text-sm">
                {report.remediation_tasks.map((t) => (
                  <li key={t.finding_id}><Badge tone={severityTone(t.severity)}>{t.severity}</Badge> <b>{t.finding_id}</b>: {t.task}</li>
                ))}
                {report.remediation_tasks.length === 0 && <li className="text-slate-500">None.</li>}
              </ul>
            </Card>
          </section>
          {report.rejected_by_skeptic.length > 0 && (
            <p className="text-sm text-slate-500">Rejected by the skeptic: {report.rejected_by_skeptic.join(", ")}</p>
          )}
          <p className="text-xs text-slate-500">
            Cost {usd(report.totals.cost_usd)} · {report.totals.tokens.toLocaleString()} tokens · {report.totals.llm_calls} LLM calls
          </p>
        </div>
      )}
    </div>
  );
}
