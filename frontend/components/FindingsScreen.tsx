"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import type { CitedRecord, Decision, FindingView, FindingsResponse, NotRaised } from "@/lib/api-types";
import { ApiError, data } from "@/lib/data";
import type { ReasoningStep } from "@/lib/types.gen";
import { Badge, Button, Card, ErrorBanner, PageTitle, cx, severityTone } from "./ui";
import { useRunId } from "./useRunId";

type Selected = { kind: "finding"; id: string } | { kind: "not_raised"; id: string };

export function FindingsScreen() {
  const runId = useRunId();
  const router = useRouter();
  const [res, setRes] = useState<FindingsResponse | null>(null);
  const [error, setError] = useState("");
  const [stillRunning, setStillRunning] = useState(false);
  const [selected, setSelected] = useState<Selected | null>(null);
  const [decisions, setDecisions] = useState<Record<string, Decision>>({});
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!runId) return;
    data.getFindings(runId).then((r) => {
      setRes(r);
      const first = r.findings.find((f) => f.group === "findings");
      if (first) setSelected({ kind: "finding", id: first.finding_id });
    }).catch((e) => {
      if (e instanceof ApiError && e.status === 409) setStillRunning(true);
      else setError((e as Error).message);
    });
  }, [runId]);

  const groups = useMemo(() => ({
    findings: res?.findings.filter((f) => f.group === "findings") ?? [],
    rejected: res?.findings.filter((f) => f.group !== "findings") ?? [],
    notRaised: res?.not_raised ?? [],
  }), [res]);
  const reviewable = res?.status === "paused";
  const decided = groups.findings.filter((f) => decisions[f.finding_id]).length;

  function decide(id: string, decision: Decision["decision"]) {
    setDecisions((d) => ({ ...d, [id]: { finding_id: id, decision, note: d[id]?.note ?? "" } }));
  }
  function note(id: string, text: string) {
    setDecisions((d) => ({ ...d, [id]: { finding_id: id, decision: d[id]?.decision ?? "approve", note: text } }));
  }
  async function submit() {
    setSubmitting(true);
    setError("");
    try {
      await data.submitReview(runId, Object.values(decisions));
      router.push(`/audit?run=${encodeURIComponent(runId)}`);
    } catch (e) {
      setError((e as Error).message);
      setSubmitting(false);
    }
  }

  if (!runId) return <ErrorBanner message="No audit selected." />;
  if (stillRunning) {
    return (
      <div className="space-y-3">
        <ErrorBanner message="This audit is still running; findings appear when it pauses for review." />
        <Link className="text-sm underline" href={`/audit?run=${runId}`}>Back to progress</Link>
      </div>
    );
  }
  const finding = selected?.kind === "finding" ? res?.findings.find((f) => f.finding_id === selected.id) : undefined;
  const dismissal = selected?.kind === "not_raised" ? res?.not_raised.find((x) => x.candidate_id === selected.id) : undefined;

  return (
    <div>
      <PageTitle title="Findings" sub={<>{runId} · {reviewable ? "approve or dismiss each finding, then submit" : `status: ${res?.status ?? "loading…"}`}</>} />
      {error && <div className="mb-4"><ErrorBanner message={error} /></div>}
      <div className="grid gap-5 md:grid-cols-[18rem_1fr]">
        <aside className="space-y-5">
          <ListGroup title={`Findings (${groups.findings.length})`}>
            {groups.findings.map((f) => (
              <ListItem key={f.finding_id} active={selected?.id === f.finding_id} onClick={() => setSelected({ kind: "finding", id: f.finding_id })}
                title={f.finding_id} right={<>
                  {(decisions[f.finding_id] ?? f.decision) && (
                    <Badge tone={(decisions[f.finding_id] ?? f.decision)?.decision === "approve" ? "green" : "neutral"}>
                      {(decisions[f.finding_id] ?? f.decision)?.decision === "approve" ? "approved" : "dismissed"}
                    </Badge>
                  )}
                  <Badge tone={severityTone(f.severity)}>{f.severity}</Badge>
                </>} sub={f.status === "unresolved" ? "unresolved" : `${f.exceptions} of ${f.tested}`} />
            ))}
          </ListGroup>
          <ListGroup title={`Not raised by the tester (${groups.notRaised.length})`}>
            {groups.notRaised.map((x) => (
              <ListItem key={x.candidate_id} active={selected?.id === x.candidate_id} onClick={() => setSelected({ kind: "not_raised", id: x.candidate_id })}
                title={x.candidate_id} sub="dismissed with a documented reason" />
            ))}
          </ListGroup>
          {groups.rejected.length > 0 && (
            <ListGroup title={`Rejected by the skeptic (${groups.rejected.length})`}>
              {groups.rejected.map((f) => (
                <ListItem key={f.finding_id} active={selected?.id === f.finding_id} onClick={() => setSelected({ kind: "finding", id: f.finding_id })}
                  title={f.finding_id} sub={f.group === "rejected" ? "rejected" : "dropped on revision"} />
              ))}
            </ListGroup>
          )}
          {reviewable && (
            <Card className="space-y-2">
              <div className="text-sm">{decided} of {groups.findings.length} decided</div>
              <Button onClick={submit} disabled={submitting || decided < groups.findings.length}>
                {submitting ? "Submitting…" : "Submit review"}
              </Button>
            </Card>
          )}
        </aside>
        <section>
          {finding && <FindingDetail f={finding} reviewable={reviewable && finding.group === "findings"}
            decision={decisions[finding.finding_id]} onDecide={(d) => decide(finding.finding_id, d)} onNote={(t) => note(finding.finding_id, t)} />}
          {dismissal && <NotRaisedDetail x={dismissal} />}
          {!finding && !dismissal && res && <Card>Select a finding.</Card>}
        </section>
      </div>
    </div>
  );
}

function ListGroup({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</div>
      <ul className="space-y-1">{children}</ul>
    </div>
  );
}

function ListItem({ title, sub, right, active, onClick }: {
  title: string; sub?: string; right?: React.ReactNode; active: boolean; onClick: () => void;
}) {
  return (
    <li>
      <button onClick={onClick} className={cx("w-full rounded-md border px-2.5 py-1.5 text-left text-sm",
        active ? "border-slate-900 bg-white dark:border-slate-200 dark:bg-slate-900" : "border-transparent hover:bg-white dark:hover:bg-slate-900")}>
        <div className="flex items-center justify-between gap-2"><span className="truncate font-medium">{title}</span><span className="flex gap-1">{right}</span></div>
        {sub && <div className="text-xs text-slate-500">{sub}</div>}
      </button>
    </li>
  );
}

function FindingDetail({ f, reviewable, decision, onDecide, onNote }: {
  f: FindingView; reviewable: boolean; decision?: Decision; onDecide: (d: Decision["decision"]) => void; onNote: (t: string) => void;
}) {
  return (
    <div className="space-y-4">
      <Card>
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-lg font-semibold">{f.finding_id}</h2>
          <Badge tone={severityTone(f.severity)}>{f.severity} (rule {f.severity_rule})</Badge>
          <Badge>{f.gap_type.replaceAll("_", " ")}</Badge>
          <Badge tone={f.status === "unresolved" ? "amber" : "neutral"}>{f.status}</Badge>
          <span className="text-sm text-slate-500">{f.exceptions} of {f.tested} items</span>
        </div>
        <dl className="mt-3 grid gap-2 text-sm">
          {([["Condition", f.condition], ["Criteria", f.criteria], ["Cause", f.cause || "not determined"], ["Effect", f.effect],
            ["Recommendation", f.recommendation]] as const).map(([k, v]) => (
            <div key={k} className="grid grid-cols-[8.5rem_1fr] gap-2"><dt className="font-medium text-slate-500">{k}</dt><dd>{v}</dd></div>
          ))}
        </dl>
      </Card>
      {reviewable && (
        <Card className="space-y-2">
          <div className="text-sm font-medium">Your review</div>
          <div className="flex gap-2">
            <Button variant={decision?.decision === "approve" ? "primary" : "secondary"} onClick={() => onDecide("approve")}>Approve</Button>
            <Button variant={decision?.decision === "dismiss" ? "primary" : "secondary"} onClick={() => onDecide("dismiss")}>Dismiss</Button>
          </div>
          <textarea aria-label="Review note" placeholder="Note (optional)" value={decision?.note ?? ""} onChange={(e) => onNote(e.target.value)}
            className="w-full rounded-md border border-slate-300 bg-white p-2 text-sm dark:border-slate-700 dark:bg-slate-900" rows={2} />
        </Card>
      )}
      {f.decision && <Card><span className="text-sm">Review: <b>{f.decision.decision}</b>{f.decision.note && ` — ${f.decision.note}`}</span></Card>}
      <Card>
        <div className="mb-2 text-sm font-medium">Skeptic verdict</div>
        {f.verdicts.length === 0 && <div className="text-sm text-slate-500">Not reviewed (skeptic off or checks only).</div>}
        {f.verdicts.map((v) => (
          <div key={v.round} className="mb-2 text-sm">
            <Badge tone={v.decision === "keep" ? "green" : v.decision === "reject" ? "red" : "amber"}>{v.decision}</Badge>
            <span className="ml-2 text-xs text-slate-500">round {v.round}{v.answered_by === "fallback" ? " · fallback call" : ""}</span>
            <p className="mt-1">{v.reason}</p>
          </div>
        ))}
      </Card>
      <Steps steps={f.reasoning ?? []} />
      <Cited items={f.cited} />
    </div>
  );
}

function NotRaisedDetail({ x }: { x: NotRaised }) {
  return (
    <div className="space-y-4">
      <Card>
        <h2 className="text-lg font-semibold">{x.candidate_id}</h2>
        <p className="mt-1 text-sm text-slate-500">Flagged by the checks, then dismissed by the tester with a documented reason.</p>
        <p className="mt-3 text-sm"><span className="font-medium">Reason: </span>{x.reason}</p>
      </Card>
      <Steps steps={x.reasoning ?? []} />
      <Cited items={x.cited} />
    </div>
  );
}

const KIND_TONE: Record<string, "neutral" | "blue" | "green" | "amber"> = { check: "neutral", tool: "blue", owner: "amber", llm: "green", rule: "neutral" };

function Steps({ steps }: { steps: ReasoningStep[] }) {
  return (
    <Card>
      <div className="mb-2 text-sm font-medium">How this was reached ({steps.length} steps)</div>
      <ol className="space-y-1.5 text-sm">
        {steps.map((s, i) => (
          <li key={i} className="flex gap-2">
            <span className="w-5 shrink-0 text-right text-slate-400">{i + 1}.</span>
            <Badge tone={KIND_TONE[s.kind] ?? "neutral"}>{s.kind}</Badge>
            <span className="break-words">{s.text}</span>
          </li>
        ))}
      </ol>
    </Card>
  );
}

function Cited({ items }: { items: CitedRecord[] }) {
  return (
    <Card>
      <div className="mb-2 text-sm font-medium">Cited records ({items.length})</div>
      <div className="space-y-3">
        {items.map((c) => (
          <div key={`${c.source}/${c.record_id}`} className="rounded-md border border-slate-200 dark:border-slate-800">
            <div className="border-b border-slate-200 px-2.5 py-1 text-xs font-medium dark:border-slate-800">{c.source} / {c.record_id}</div>
            {!c.record && <div className="px-2.5 py-1.5 text-xs text-red-700">Record not found.</div>}
            {c.record && typeof c.record.text === "string" ? (
              <pre className="max-h-64 overflow-auto whitespace-pre-wrap px-2.5 py-1.5 text-xs">{c.record.text}</pre>
            ) : c.record && (
              <table className="w-full text-xs"><tbody>
                {Object.entries(c.record).map(([k, v]) => (
                  <tr key={k} className="border-t border-slate-100 first:border-0 dark:border-slate-800">
                    <td className="w-44 px-2.5 py-1 text-slate-500">{k}</td><td className="px-2.5 py-1 font-mono">{String(v ?? "")}</td>
                  </tr>
                ))}
              </tbody></table>
            )}
          </div>
        ))}
      </div>
    </Card>
  );
}
