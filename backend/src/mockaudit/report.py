"""Run artifacts: controls/<id>.json, verdicts.json, report.md, report.json, run.json (spec §4).

The report states readiness, never an audit opinion. There is no pass badge.
"""

from __future__ import annotations

import json
from pathlib import Path

from mockaudit.schemas import ControlResult, Dismissal, Finding

SEV_ORDER = {"high": 0, "moderate": 1, "low": 2, None: 3}


def write_run(state: dict, ctx) -> dict:
    cfg = state["config"]
    run_dir: Path = ctx.run_dir
    (run_dir / "controls").mkdir(parents=True, exist_ok=True)
    findings = [Finding.model_validate(f) for f in state.get("findings", {}).values()]
    dismissals = [Dismissal.model_validate(d) for d in state.get("dismissals", {}).values()]
    spend = ctx.spend
    results = []
    for cid, raw in sorted(state.get("results", {}).items(), key=lambda kv: int(kv[0][1:])):
        mine = sorted([f for f in findings if f.control_id == cid], key=lambda f: f.finding_id)
        r = ControlResult.model_validate({**raw, "findings": [f.model_dump() for f in mine],
                                          "dismissals": [d.model_dump() for d in dismissals if d.control_id == cid]})
        if r.status != "error":
            r.status = "exceptions" if any(f.status not in ("rejected", "dismissed") for f in mine) else "pass"
        if spend is not None and cid in spend.by_control:
            r.cost_usd, r.tokens = round(spend.by_control[cid][0], 6), spend.by_control[cid][1]
        r.revision_round = int(any(s.text.startswith("skeptic round 1") for f in mine for s in f.reasoning))
        (run_dir / "controls" / f"{cid}.json").write_text(r.model_dump_json(indent=2))
        results.append(r)
    (run_dir / "verdicts.json").write_text(json.dumps(state.get("verdicts", {}), indent=2))

    human = cfg["review_mode"] == "human"
    shown = [f for f in findings if f.status == "approved"] if human else \
            [f for f in findings if f.status in ("kept", "unresolved", "approved")]
    shown.sort(key=lambda f: (SEV_ORDER[f.severity], f.finding_id))
    rejected = sorted((f for f in findings if f.status == "rejected"), key=lambda f: f.finding_id)
    totals = {"cost_usd": round(spend.run_cost, 6) if spend else 0.0, "tokens": spend.run_tokens if spend else 0,
              "llm_calls": spend.calls if spend else 0}
    decisions = state.get("decisions") or {}
    if decisions:
        (run_dir / "review_decisions.json").write_text(json.dumps(decisions, indent=2))
    report = {"run_id": cfg["run_id"], "variant": cfg["variant"], "mode": cfg["mode"], "review_mode": cfg["review_mode"],
              "statement": "Readiness forecast from synthetic evidence. Not an audit opinion.",
              "findings": [{**f.model_dump(), "review_note": decisions.get(f.finding_id, {}).get("note", "")} for f in shown],
              "rejected_by_skeptic": [f.finding_id for f in rejected],
              "coverage": [{"control_id": r.control_id, "status": r.status, "error": r.error, "tested": r.coverage.tested,
                            "not_tested": r.coverage.not_tested, "population_size": r.population_size,
                            "notes": r.notes} for r in results],
              "remediation_tasks": [{"finding_id": f.finding_id, "owner_control": f.control_id,
                                     "task": f.recommendation, "severity": f.severity} for f in shown],
              "totals": totals}
    (run_dir / "report.json").write_text(json.dumps(report, indent=2, default=str))
    (run_dir / "report.md").write_text(render_md(report, results))
    (run_dir / "run.json").write_text(json.dumps({"config": cfg, "data_dir": str(Path(ctx.data_dir).resolve()),
                                                  "totals": totals, "findings": len(shown)}, indent=2))
    (run_dir.parent / "LATEST").write_text(cfg["run_id"] + "\n")
    return {"path": str(run_dir), "findings": len(shown), **totals}


def render_md(rep: dict, results: list[ControlResult]) -> str:
    out = [f"# Ledgerly SOC 2 readiness report — {rep['run_id']}", "",
           f"_{rep['statement']}_ Mode: {rep['mode']}, review: {rep['review_mode']}.", "",
           "## Coverage", "", "| Control | Status | Steps tested | Not tested | Notes |", "|---|---|---|---|---|"]
    for c in rep["coverage"]:
        status = {"error": f"error ({c['error']})", "pass": "no exceptions found"}.get(c["status"], c["status"])
        nt = ", ".join(f"{x['step_id']} ({x['reason']})" for x in c["not_tested"]) or "—"
        out.append(f"| {c['control_id']} | {status} | {', '.join(c['tested']) or '—'} | {nt} | {'; '.join(c['notes'])[:120] or '—'} |")
    out += ["", f"## Findings ({len(rep['findings'])})", ""]
    for f in rep["findings"]:
        cites = ", ".join(f"{c['source']}/{c['record_id']}" for c in f["citations"][:12])
        failed = any(w in s["text"] for s in f["reasoning"][-2:] for w in ("revision failed", ": error"))
        flag = "" if f["status"] != "unresolved" else (" — **unresolved** (the review could not complete)" if failed
                                                       else " — **unresolved** (reviewer and tester disagree)")
        out += [f"### {f['finding_id']} · {f['severity']} · {f['exceptions']} of {f['tested']}{flag}", "",
                f"- **Condition:** {f['condition']}", f"- **Criteria:** {f['criteria']}",
                f"- **Cause:** {f['cause'] or 'not determined'}", f"- **Effect:** {f['effect']}",
                f"- **Recommendation:** {f['recommendation']}", f"- **Evidence:** {cites}"]
        out += [f"- **Reviewer note:** {f['review_note']}", ""] if f.get("review_note") else [""]
    if rep["rejected_by_skeptic"]:
        out += ["## Rejected by the skeptic", "", ", ".join(rep["rejected_by_skeptic"]), ""]
    out += ["## Remediation tasks", ""] + [f"- [{t['severity']}] {t['finding_id']}: {t['task']}" for t in rep["remediation_tasks"]]
    t = rep["totals"]
    out += ["", f"Cost: US${t['cost_usd']:.4f} · {t['tokens']:,} tokens · {t['llm_calls']} LLM calls", ""]
    return "\n".join(out)
