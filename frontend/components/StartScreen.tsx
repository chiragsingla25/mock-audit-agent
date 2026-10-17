"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import type { AppConfig, AuditSummary, Mode } from "@/lib/api-types";
import { data } from "@/lib/data";
import { Badge, Button, Card, ErrorBanner, PageTitle, usd } from "./ui";

const MODES: { id: Mode; label: string; hint: string }[] = [
  { id: "agent", label: "Agent", hint: "Checks + tester + skeptic (LLM calls, about US$0.03)" },
  { id: "skeptic_off", label: "Skeptic off", hint: "Checks + tester only" },
  { id: "checks_only", label: "Checks only", hint: "Rules-only baseline, no LLM calls" },
];

export function StartScreen() {
  const router = useRouter();
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [recent, setRecent] = useState<AuditSummary[]>([]);
  const [variant, setVariant] = useState("base");
  const [mode, setMode] = useState<Mode>("agent");
  const [error, setError] = useState("");
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    data.getConfig().then(setConfig).catch((e: Error) => setError(e.message));
    data.listAudits().then(setRecent).catch(() => {});
  }, []);

  async function start() {
    setError("");
    setStarting(true);
    try {
      const { run_id } = await data.startAudit(variant, mode);
      router.push(`/audit?run=${encodeURIComponent(run_id)}`);
    } catch (e) {
      setError((e as Error).message);
      setStarting(false);
    }
  }

  return (
    <div className="grid gap-6 md:grid-cols-[2fr_1fr]">
      <div>
        <PageTitle title="Start an audit" sub="Twelve SOC 2 controls over Ledgerly's synthetic evidence for 2025-10-01 to 2026-09-30." />
        {error && <div className="mb-4"><ErrorBanner message={error} /></div>}
        <Card className="space-y-5">
          <div>
            <label className="mb-1 block text-sm font-medium" htmlFor="variant">Dataset</label>
            <select id="variant" value={variant} onChange={(e) => setVariant(e.target.value)}
              className="rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm dark:border-slate-700 dark:bg-slate-900">
              {(config?.variants.length ? config.variants : ["base"]).map((v) => (
                <option key={v} value={v}>{v === "base" ? "Ledgerly base" : `Variant ${v.toUpperCase()}`}</option>
              ))}
            </select>
          </div>
          <fieldset>
            <legend className="mb-1 text-sm font-medium">Mode</legend>
            <div className="space-y-1.5">
              {MODES.map((m) => (
                <label key={m.id} className="flex items-start gap-2 text-sm">
                  <input type="radio" name="mode" value={m.id} checked={mode === m.id} onChange={() => setMode(m.id)} className="mt-1" />
                  <span><span className="font-medium">{m.label}</span> <span className="text-slate-500">— {m.hint}</span></span>
                </label>
              ))}
            </div>
          </fieldset>
          <div className="text-sm">
            <div className="mb-1 font-medium">Models (set in <code>.env</code>)</div>
            <div className="text-slate-600 dark:text-slate-400">Tester: {config?.tester_model || "—"} · Skeptic: {config?.skeptic_model || "—"}</div>
          </div>
          <div className="flex items-center gap-3">
            <Button onClick={start} disabled={starting || !!config?.busy}>{starting ? "Starting…" : "Start audit"}</Button>
            {config?.busy && <span className="text-sm text-amber-700">Another audit is running.</span>}
          </div>
          <p className="text-xs text-slate-500">Findings pause for your review before the report is written.</p>
        </Card>
      </div>
      <div className="space-y-4">
        <Card>
          <div className="text-sm font-medium">Spend so far</div>
          <div className="mt-1 text-2xl font-semibold">{config ? usd(config.spend_usd) : "—"}</div>
          <div className="text-xs text-slate-500">
            Project cap {config ? `US$${config.project_cap_usd.toFixed(2)}` : "—"} · run cap {config ? `US$${config.run_cap_usd.toFixed(2)}` : "—"}
          </div>
        </Card>
        <Card>
          <div className="mb-2 text-sm font-medium">Recent audits</div>
          {recent.length === 0 && <div className="text-sm text-slate-500">None yet.</div>}
          <ul className="space-y-1.5 text-sm">
            {recent.map((r) => (
              <li key={r.run_id} className="flex items-center justify-between gap-2">
                <Link className="truncate underline-offset-2 hover:underline" href={
                  r.status === "done" ? `/report?run=${r.run_id}` : r.status === "paused" ? `/findings?run=${r.run_id}` : `/audit?run=${r.run_id}`
                }>{r.run_id}</Link>
                <Badge tone={r.status === "done" ? "green" : r.status === "paused" ? "amber" : "neutral"}>{r.status}</Badge>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </div>
  );
}
