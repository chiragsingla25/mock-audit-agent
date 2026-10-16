"""Score a run's kept findings against the answer key (spec Phase 2; proposal §7)."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from mockaudit.evidence import Evidence
from mockaudit.schemas import ControlResult
from mockaudit.specs import load_controls

KEPT = {"draft", "kept", "unresolved", "approved"}


def cited_ids(finding) -> set[str]:
    return {c.record_id for c in finding.citations}


def matches(finding, gap: dict) -> bool:
    """A finding matches a gap on control id and ≥ 1 cited record id."""
    return finding.control_id == gap["control_id"] and bool(cited_ids(finding) & set(gap["record_ids"]))


SKEPTIC_OFF = "skeptic_off"


def counted(f, view) -> bool:
    """KEPT view: what the report keeps. Skeptic-off view: everything the tester raised, as if the skeptic hadn't run
    (rejected findings, and findings dropped only because the skeptic asked for a revision, count again)."""
    if view == SKEPTIC_OFF:
        on_revision = any(s.text == "tester dismissed this finding's items on revision" for s in f.reasoning)
        return f.status in KEPT | {"rejected"} or (f.status == "dismissed" and on_revision)
    return f.status in view


def score(results: list[ControlResult], key: dict, index: set[tuple[str, str]] | None = None,
          kept=KEPT) -> dict:
    findings = [f for r in results for f in r.findings if counted(f, kept)]
    gaps, traps, clean = key["gaps"], key["traps"], key["clean_controls"]

    matched_gaps = [g for g in gaps if any(matches(f, g) for f in findings)]
    code_gaps = [g for g in gaps if g["tag"] == "code"]
    matching_findings = [f for f in findings if any(matches(f, g) for g in gaps)]
    pairs = [(f, g) for g in gaps for f in findings if matches(f, g)]
    agree = [(f, g) for f, g in pairs if f.severity == g["severity"]]
    gapped_controls = {f.control_id for f in findings}
    raised_traps = [t for t in traps if any(f.control_id == t["control_id"] and cited_ids(f) & set(t["record_ids"])
                                            for f in findings)]
    cites = [c for f in findings for c in f.citations]
    valid = [c for c in cites if index is None or (c.source, c.record_id) in index]
    dropped = sum(len(r.dropped_citations) for r in results)

    def ratio(n, d):
        return {"n": n, "of": d, "value": round(n / d, 4) if d else None}

    return {
        "recall": ratio(len(matched_gaps), len(gaps)),
        "recall_code": ratio(sum(g in matched_gaps for g in code_gaps), len(code_gaps)),
        "precision": ratio(len(matching_findings), len(findings)),
        "clean_control_accuracy": ratio(sum(c not in gapped_controls for c in clean), len(clean)),
        "citation_validity": ratio(len(valid), len(cites) + dropped),
        "severity_agreement": ratio(len(agree), len(pairs)),
        "traps_raised": ratio(len(raised_traps), len(traps)),
        "matched_gaps": [g["id"] for g in matched_gaps],
        "missed_gaps": [g["id"] for g in gaps if g not in matched_gaps],
        "unmatched_findings": [f.finding_id for f in findings if f not in matching_findings],
        "traps_raised_ids": [t["id"] for t in raised_traps],
        "findings": len(findings),
    }


def load_run(run_dir: Path) -> tuple[list[ControlResult], dict]:
    meta = json.loads((run_dir / "run.json").read_text())
    results = [ControlResult.model_validate_json(p.read_text()) for p in sorted((run_dir / "controls").glob("*.json"))]
    return results, meta


def data_index(data_dir: Path) -> set[tuple[str, str]]:
    out = set()
    for spec in load_controls(data_dir / "controls.yaml"):
        out |= Evidence.load(spec, data_dir).index()
    return out


def evaluate_run(run_dir: Path) -> dict:
    results, meta = load_run(run_dir)
    data_dir = Path(meta["data_dir"])
    key = yaml.safe_load((data_dir / "answer_key.yaml").read_text())
    metrics = score(results, key, data_index(data_dir))
    out = {"run_id": meta["config"]["run_id"], "variant": meta["config"]["variant"],
           "mode": meta["config"]["mode"], "metrics": metrics}
    (run_dir / "eval.json").write_text(json.dumps(out, indent=2))
    return out


TARGETS = {"recall": "≥ 80%", "precision": "≥ 80%", "clean_control_accuracy": "all", "citation_validity": "100%",
           "severity_agreement": "≥ 80%", "traps_raised": "report", "recall_code": "report"}


def table(ev: dict) -> str:
    m = ev["metrics"]
    rows = [f"Run {ev['run_id']} · variant {ev['variant']} · mode {ev['mode']} · {m['findings']} kept findings", "",
            "| Metric | Result | Target |", "|---|---|---|"]
    for k in ["recall", "recall_code", "precision", "clean_control_accuracy", "citation_validity",
              "severity_agreement", "traps_raised"]:
        r = m[k]
        val = "n/a" if r["value"] is None else f"{r['n']}/{r['of']} ({r['value']:.0%})"
        rows.append(f"| {k.replace('_', ' ')} | {val} | {TARGETS[k]} |")
    summary = (f"Missed gaps: {', '.join(m['missed_gaps']) or 'none'} · "
               f"unmatched findings: {', '.join(m['unmatched_findings']) or 'none'} · "
               f"traps raised: {', '.join(m['traps_raised_ids']) or 'none'}")
    rows += ["", summary]
    return "\n".join(rows)
