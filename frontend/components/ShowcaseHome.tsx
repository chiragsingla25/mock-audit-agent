"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import type { Ratio, ShowcaseIndex } from "@/lib/api-types";
import { data } from "@/lib/data";
import { Badge, Card, ErrorBanner, PageTitle, usd } from "./ui";

const frac = (r: Ratio) => `${r.n}/${r.of}`;
const pct = (v: number | null | undefined) => (v == null ? "n/a" : `${Math.round(v * 100)}%`);
const MODE_LABEL = { agent: "Agent", skeptic_off: "Skeptic off (view)", checks_only: "Checks only" } as const;

/** Showcase home: the published runs and the agent vs checks-only vs skeptic-off comparison. No start button. */
export function ShowcaseHome() {
  const [index, setIndex] = useState<ShowcaseIndex | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    data.getIndex().then(setIndex).catch((e: Error) => setError(e.message));
  }, []);

  if (error) return <ErrorBanner message={error} />;
  if (!index) return <p className="text-sm text-slate-500">Loading…</p>;
  const ev = index.eval;
  const firstRows = ev?.rows.filter((r) => r.repeat === 1) ?? [];

  return (
    <div className="space-y-6">
      <PageTitle title="A skeptical SOC 2 mock auditor" sub={index.statement} />
      <Card className="space-y-2 text-sm">
        <p>
          Two cheap LLMs (a Qwen tester and a DeepSeek skeptic) audit twelve SOC 2 controls at a fictional company,
          Ledgerly, over a year of synthetic evidence. Code runs every check on the full population and computes counts,
          dates and severity; the tester judges the exceptions code flags, citing records; the skeptic challenges each
          finding; a person approves or dismisses. Every finding cites the records behind it.
        </p>
        <p className="text-slate-500">
          The data has 10 planted gaps, 4 traps (exceptions with a documented innocent explanation) and 4 clean controls,
          so accuracy is measured, not asserted. Runs are made locally and published here with their review decisions.
        </p>
      </Card>

      <section>
        <h2 className="mb-2 font-semibold">Published runs</h2>
        <Card className="overflow-x-auto p-0">
          <table className="w-full text-sm">
            <thead className="text-left text-xs text-slate-500"><tr>
              <th className="px-3 py-2">Run</th><th className="px-3 py-2">Recall</th><th className="px-3 py-2">Precision</th>
              <th className="px-3 py-2">Clean controls</th><th className="px-3 py-2">Traps raised</th><th className="px-3 py-2">Cost</th>
              <th className="px-3 py-2" /></tr></thead>
            <tbody>
              {index.runs.map((r) => (
                <tr key={r.run_id} className="border-t border-slate-100 dark:border-slate-800">
                  <td className="px-3 py-2">
                    <div className="font-medium">
                      {r.label}{" "}
                      {r.reviewed ? <Badge tone="green">review decisions recorded</Badge> : <Badge>not reviewed by a person</Badge>}
                    </div>
                    <div className="text-xs text-slate-500">{r.run_id}</div>
                    {r.reviewed && <div className="text-xs text-slate-500">Scores count only the findings the reviewer approved.</div>}
                  </td>
                  <td className="px-3 py-2">{r.metrics ? frac(r.metrics.recall) : "—"}</td>
                  <td className="px-3 py-2">{r.metrics ? frac(r.metrics.precision) : "—"}</td>
                  <td className="px-3 py-2">{r.metrics ? frac(r.metrics.clean_control_accuracy) : "—"}</td>
                  <td className="px-3 py-2">{r.metrics ? frac(r.metrics.traps_raised) : "—"}</td>
                  <td className="px-3 py-2">{r.cost_usd ? usd(r.cost_usd) : "free"}</td>
                  <td className="whitespace-nowrap px-3 py-2">
                    <Link className="underline underline-offset-2" href={`/findings?run=${r.run_id}`}>Findings</Link>{" · "}
                    <Link className="underline underline-offset-2" href={`/report?run=${r.run_id}`}>Report</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </section>

      {ev && (
        <section>
          <h2 className="mb-2 font-semibold">Agent vs checks-only vs skeptic off</h2>
          <Card className="overflow-x-auto p-0">
            <table className="w-full text-sm">
              <thead className="text-left text-xs text-slate-500"><tr>
                <th className="px-3 py-2">Dataset</th><th className="px-3 py-2">Mode</th><th className="px-3 py-2">Recall</th>
                <th className="px-3 py-2">Precision</th><th className="px-3 py-2">Clean controls</th><th className="px-3 py-2">Severity</th>
                <th className="px-3 py-2">Traps raised</th></tr></thead>
              <tbody>
                {firstRows.map((r) => (
                  <tr key={`${r.run_id}-${r.mode}`} className="border-t border-slate-100 dark:border-slate-800">
                    <td className="px-3 py-2">{r.variant === "base" ? "Ledgerly base" : `Variant ${r.variant.toUpperCase()}`}</td>
                    <td className="px-3 py-2"><Link className="underline underline-offset-2" href={`/findings?run=${r.run_id}`}>{MODE_LABEL[r.mode]}</Link></td>
                    <td className="px-3 py-2">{frac(r.metrics.recall)}</td>
                    <td className="px-3 py-2">{frac(r.metrics.precision)}</td>
                    <td className="px-3 py-2">{frac(r.metrics.clean_control_accuracy)}</td>
                    <td className="px-3 py-2">{frac(r.metrics.severity_agreement)}</td>
                    <td className="px-3 py-2">{frac(r.metrics.traps_raised)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
          <div className="mt-3 grid gap-3 sm:grid-cols-3">
            <Card><div className="text-xs text-slate-500">Stability (3 base runs)</div><div className="font-semibold">{pct(ev.stability.value)} overlap</div></Card>
            <Card><div className="text-xs text-slate-500">Cost per audit</div><div className="font-semibold">{usd(ev.cost.per_audit_usd ?? 0)}</div></Card>
            <Card><div className="text-xs text-slate-500">Targets met</div><div className="font-semibold">{ev.targets.filter((t) => t.met).length} of {ev.targets.length}</div></Card>
          </div>
          <p className="mt-2 text-xs text-slate-500">
            Skeptic off is the same agent runs scored as if the skeptic had not run (no extra calls). Evaluation {ev.eval_id}.
          </p>
        </section>
      )}
    </div>
  );
}
