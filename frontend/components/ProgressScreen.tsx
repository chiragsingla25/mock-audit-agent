"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import type { Audit, ControlState } from "@/lib/api-types";
import { data } from "@/lib/data";
import { Badge, Card, ErrorBanner, PageTitle, cx, usd } from "./ui";
import { useRunId } from "./useRunId";

const STATE_TONE: Record<ControlState, "neutral" | "blue" | "green" | "red" | "amber"> = {
  queued: "neutral", running: "blue", revising: "amber", done: "green", error: "red",
};

export function ProgressScreen() {
  const runId = useRunId();
  const [audit, setAudit] = useState<Audit | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!runId) return;
    let stop = false;
    let timer: ReturnType<typeof setTimeout>;
    const tick = async () => {
      try {
        const a = await data.getAudit(runId);
        if (stop) return;
        setAudit(a);
        setError("");
        if (a.status === "running") timer = setTimeout(tick, 1000);
      } catch (e) {
        if (stop) return;
        setError((e as Error).message);
        timer = setTimeout(tick, 2000);
      }
    };
    tick();
    return () => { stop = true; clearTimeout(timer); };
  }, [runId]);

  if (!runId) return <ErrorBanner message="No audit selected." />;
  const controls = Object.entries(audit?.controls ?? {});
  const done = controls.filter(([, s]) => s === "done" || s === "error").length;

  return (
    <div>
      <PageTitle title={data.mode === "showcase" ? "Run overview" : "Audit progress"} sub={<>{runId} · {audit ? `${audit.variant} · ${audit.mode}` : "loading…"}</>} />
      {error && <div className="mb-4"><ErrorBanner message={error} /></div>}
      {audit?.error && <div className="mb-4"><ErrorBanner message={`The audit stopped: ${audit.error}`} /></div>}
      <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label="Controls tested" value={`${done} / ${controls.length || 12}`} />
        <Stat label="Stage" value={audit?.phase ?? "—"} />
        <Stat label="Cost" value={audit ? usd(audit.cost_usd) : "—"} />
        <Stat label="Tokens · LLM calls" value={audit ? `${audit.tokens.toLocaleString()} · ${audit.llm_calls}` : "—"} />
      </div>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        {controls.map(([cid, state]) => (
          <Card key={cid} className={cx("min-h-20", state === "running" && "ring-1 ring-blue-300 dark:ring-blue-800")}>
            <div className="flex items-center justify-between">
              <span className="font-semibold">{cid}</span>
              <Badge tone={STATE_TONE[state]}>{state}</Badge>
            </div>
            {audit?.control_errors[cid] && <p className="mt-2 text-xs text-red-700 dark:text-red-300">{audit.control_errors[cid]}</p>}
          </Card>
        ))}
      </div>
      <div className="mt-6 flex gap-3">
        {audit?.status === "paused" && (
          <Link href={`/findings?run=${runId}`} className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white dark:bg-slate-100 dark:text-slate-900">
            Review findings →
          </Link>
        )}
        {audit?.status === "done" && (
          <Link href={`/report?run=${runId}`} className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white dark:bg-slate-100 dark:text-slate-900">
            Open report →
          </Link>
        )}
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <div className="text-xs text-slate-500">{label}</div>
      <div className="mt-0.5 truncate font-semibold">{value}</div>
    </Card>
  );
}
