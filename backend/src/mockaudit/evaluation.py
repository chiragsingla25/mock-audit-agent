"""`mockaudit eval --all` (spec Phase 4): agent runs on base, a, b and 2 more base runs (stability), checks-only
on all three, skeptic-off scored from the same agent runs, cost per audit, all under an eval spend cap.

Targets are reported as met or missed; nothing is hidden.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from itertools import combinations
from pathlib import Path

import yaml

from mockaudit.datagen.ledgerly import generate
from mockaudit.runner import new_run_id, run_audit
from mockaudit.schemas import RunConfig
from mockaudit.scoring import KEPT, SKEPTIC_OFF, data_index, load_run, score

VARIANTS = ["base", "a", "b"]
AGENT_PLAN = [("base", 1), ("a", 1), ("b", 1), ("base", 2), ("base", 3)]
TARGETS = {"recall": 0.80, "precision": 0.80, "clean_control_accuracy": 1.0, "citation_validity": 1.0,
           "severity_agreement": 0.80, "stability": 0.90}


def run_spend(spend_path: Path, run_id: str) -> dict:
    cost, tokens, calls = 0.0, 0, 0
    if Path(spend_path).exists():
        for line in Path(spend_path).read_text().splitlines():
            x = json.loads(line) if line.strip() else {}
            if x.get("run") == run_id:
                cost, tokens, calls = cost + x["cost"], tokens + x["tokens"], calls + 1
    return {"cost_usd": round(cost, 6), "tokens": tokens, "llm_calls": calls}


def finding_keys(run_dir: Path) -> set[tuple[str, str]]:
    results, _ = load_run(run_dir)
    return {(f.control_id, f.test_step) for r in results for f in r.findings if f.status in KEPT}


def jaccard(a: set, b: set) -> float:
    return 1.0 if not a and not b else len(a & b) / len(a | b)


def metrics_for(run_dir: Path, data_dir: Path, kept: set[str] = KEPT) -> dict:
    results, _ = load_run(run_dir)
    key = yaml.safe_load((data_dir / "answer_key.yaml").read_text())
    return score(results, key, data_index(data_dir), kept)


def value(m: dict, name: str) -> float | None:
    return m[name]["value"]


async def run_eval_all(data_root: Path, runs_dir: Path, models, spend_path: Path, base_cfg: dict,
                       eval_cap: float = 2.0, plan=AGENT_PLAN) -> dict:
    data_root, runs_dir = Path(data_root), Path(runs_dir)
    eval_id = f"eval-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    out_dir = runs_dir / eval_id
    out_dir.mkdir(parents=True, exist_ok=True)
    for v in VARIANTS:
        if not (data_root / v / "answer_key.yaml").exists():
            generate(v, data_root)

    agent, skipped, spent, dearest = [], [], 0.0, 0.0
    for variant, rep in plan:
        if dearest and spent + dearest > eval_cap:
            skipped.append({"variant": variant, "repeat": rep,
                            "reason": f"eval spend cap: US${spent:.4f} spent + US${dearest:.4f} for the next run > US${eval_cap:.2f}"})
            continue
        cfg = RunConfig(run_id=f"{new_run_id('agent', variant)}-r{rep}", variant=variant, mode="agent",
                        review_mode="skip", **base_cfg)
        await run_audit(cfg, data_root, runs_dir, models, spend_path)
        cost = run_spend(spend_path, cfg.run_id)
        spent += cost["cost_usd"]
        dearest = max(dearest, cost["cost_usd"])
        agent.append({"run_id": cfg.run_id, "variant": variant, "repeat": rep, **cost})

    checks = []
    for variant in VARIANTS:
        cfg = RunConfig(run_id=f"{new_run_id('checks_only', variant)}-e", variant=variant, mode="checks_only")
        await run_audit(cfg, data_root, runs_dir, None)
        checks.append({"run_id": cfg.run_id, "variant": variant})

    result = build_result(eval_id, agent, checks, skipped, spent, eval_cap, data_root, runs_dir)
    write_eval(result, runs_dir)
    (runs_dir / "LATEST_EVAL").write_text(eval_id + "\n")
    return result


def write_eval(result: dict, runs_dir: Path) -> None:
    out_dir = Path(runs_dir) / result["eval_id"]
    (out_dir / "eval.json").write_text(json.dumps(result, indent=2))
    (out_dir / "eval.md").write_text(render(result))


def rescore(runs_dir: Path, eval_id: str, data_root: Path) -> dict:
    """Re-score an existing evaluation from its runs on disk. No LLM calls."""
    old = json.loads((Path(runs_dir) / eval_id / "eval.json").read_text())
    keep = ("run_id", "variant", "repeat", "cost_usd", "tokens", "llm_calls")
    agent = [{k: r[k] for k in keep} for r in old["rows"] if r["mode"] == "agent"]
    checks = [{"run_id": r["run_id"], "variant": r["variant"]} for r in old["rows"] if r["mode"] == "checks_only"]
    result = build_result(eval_id, agent, checks, old["skipped"], old["cost"]["eval_total_usd"],
                          old["cost"]["eval_cap_usd"], Path(data_root), Path(runs_dir))
    write_eval(result, runs_dir)
    return result


def build_result(eval_id: str, agent: list[dict], checks: list[dict], skipped: list[dict], spent: float,
                 eval_cap: float, data_root: Path, runs_dir: Path) -> dict:
    rows = []
    for r in agent:
        d = data_root / r["variant"]
        rows.append({**r, "mode": "agent", "metrics": metrics_for(runs_dir / r["run_id"], d)})
        rows.append({**r, "mode": "skeptic_off", "cost_usd": 0.0, "tokens": 0, "llm_calls": 0,
                     "derived_from": r["run_id"], "metrics": metrics_for(runs_dir / r["run_id"], d, SKEPTIC_OFF)})
    for r in checks:
        rows.append({**r, "repeat": 1, "mode": "checks_only", "cost_usd": 0.0, "tokens": 0, "llm_calls": 0,
                     "metrics": metrics_for(runs_dir / r["run_id"], data_root / r["variant"])})

    base_runs = [r for r in agent if r["variant"] == "base"]
    keys = [finding_keys(runs_dir / r["run_id"]) for r in base_runs]
    pairs = [jaccard(a, b) for a, b in combinations(keys, 2)]
    stability = {"runs": [r["run_id"] for r in base_runs], "pairwise": [round(p, 4) for p in pairs],
                 "value": round(sum(pairs) / len(pairs), 4) if pairs else None,
                 "recall_per_run": [value(next(x["metrics"] for x in rows if x.get("run_id") == r["run_id"]
                                               and x["mode"] == "agent"), "recall") for r in base_runs]}

    def first(mode, variant):
        return next((x for x in rows if x["mode"] == mode and x["variant"] == variant and x.get("repeat", 1) == 1), None)

    comparisons = {}
    for variant in VARIANTS:
        a, s, c = first("agent", variant), first("skeptic_off", variant), first("checks_only", variant)
        if a is None:
            continue
        comparisons[variant] = {
            name: {"agent": value(a["metrics"], name), "skeptic_off": value(s["metrics"], name),
                   "checks_only": value(c["metrics"], name)}
            for name in ["recall", "precision", "clean_control_accuracy", "severity_agreement"]}
        comparisons[variant]["traps_raised"] = {m: x["metrics"]["traps_raised"]["n"] for m, x in
                                                 [("agent", a), ("skeptic_off", s), ("checks_only", c)]}

    base = first("agent", "base")
    variant_agent = [first("agent", v) for v in VARIANTS if first("agent", v)]

    def mean(name):
        vals = [value(x["metrics"], name) for x in variant_agent if value(x["metrics"], name) is not None]
        return round(sum(vals) / len(vals), 4) if vals else None

    targets = []
    for name, target in TARGETS.items():
        got = stability["value"] if name == "stability" else (value(base["metrics"], name) if base else None)
        targets.append({"metric": name, "base": got, "variant_mean": None if name == "stability" else mean(name),
                        "target": target, "met": got is not None and got >= target})
    cost = {"per_audit_usd": round(sum(r["cost_usd"] for r in agent) / len(agent), 6) if agent else None,
            "per_audit_tokens": round(sum(r["tokens"] for r in agent) / len(agent)) if agent else None,
            "eval_total_usd": round(spent, 6), "eval_cap_usd": eval_cap, "within_cap": spent <= eval_cap}
    return {"eval_id": eval_id, "rows": rows, "skipped": skipped, "stability": stability,
            "comparisons": comparisons, "targets": targets, "cost": cost}


def pct(v) -> str:
    return "n/a" if v is None else f"{v:.0%}"


def render(e: dict) -> str:
    out = [f"# Evaluation {e['eval_id']}", "",
           ("Scored by code against each variant's answer key: a finding matches a gap on control id plus at least "
           "one cited record id. Readiness forecast on synthetic data, not an audit opinion."), "",
           "## Targets (base run 1; variant mean in brackets)", "", "| Metric | Result | Target | |", "|---|---|---|---|"]
    for t in e["targets"]:
        extra = f" ({pct(t['variant_mean'])} avg)" if t["variant_mean"] is not None else ""
        out.append(f"| {t['metric'].replace('_', ' ')} | {pct(t['base'])}{extra} | ≥ {t['target']:.0%} | "
                   f"{'met' if t['met'] else '**missed**'} |")
    out += ["", "## All runs", "",
            "| Run | Variant | Mode | Recall | Precision | Clean controls | Citations | Severity | Traps raised | US$ | Tokens |",
            "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in e["rows"]:
        m = r["metrics"]

        def frac(k, m=m):
            return f"{m[k]['n']}/{m[k]['of']}"
        out.append(f"| {r.get('derived_from', r['run_id'])}{' (view)' if r['mode'] == 'skeptic_off' else ''} | "
                   f"{r['variant']} | {r['mode']} | {frac('recall')} | {frac('precision')} | {frac('clean_control_accuracy')} | "
                   f"{frac('citation_validity')} | {frac('severity_agreement')} | {frac('traps_raised')} | "
                   f"{r['cost_usd']:.4f} | {r['tokens']:,} |")
    out += ["", "## Agent vs checks-only vs skeptic off (first run per variant)", "",
            "| Variant | Metric | Agent | Skeptic off | Checks only |", "|---|---|---|---|---|"]
    for v, comp in e["comparisons"].items():
        for name, vals in comp.items():
            fmt = (lambda x: str(x)) if name == "traps_raised" else pct
            out.append(f"| {v} | {name.replace('_', ' ')} | {fmt(vals['agent'])} | {fmt(vals['skeptic_off'])} | "
                       f"{fmt(vals['checks_only'])} |")
    s, c = e["stability"], e["cost"]
    out += ["", (f"**Stability:** {pct(s['value'])} mean pairwise overlap of kept findings over {len(s['runs'])} base runs "
                f"(pairs: {', '.join(pct(p) for p in s['pairwise']) or 'n/a'}; recall per run: "
                f"{', '.join(pct(x) for x in s['recall_per_run'])})."),
            (f"**Cost:** US${c['per_audit_usd'] or 0:.4f} and {c['per_audit_tokens'] or 0:,} tokens per audit; "
            f"evaluation total US${c['eval_total_usd']:.4f} of a US${c['eval_cap_usd']:.2f} cap.")]
    if e["skipped"]:
        out += ["", "**Skipped:** " + "; ".join(f"{x['variant']} r{x['repeat']} ({x['reason']})" for x in e["skipped"])]
    return "\n".join(out) + "\n"
