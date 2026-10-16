"""Phase 1 dataset tests (spec 2026-10-15-mock-audit-mvp §5, Phase 1).

Each gap/trap has a documented query below that finds it in the *raw files* (csv/md), written
independently of the generator. Tests compare those queries with each variant's answer key.
"""

from __future__ import annotations

import csv
import re
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
import yaml

from mockaudit.cli import main as cli_main
from mockaudit.datagen.ledgerly import generate
from mockaudit.severity import severity
from mockaudit.specs import ControlSpecError, load_controls

SYD = ZoneInfo("Australia/Sydney")
P0, P1 = date(2025, 10, 1), date(2026, 9, 30)
VARIANTS = ["base", "a", "b"]
REMOVAL = {"user.lifecycle.suspend", "user.lifecycle.deactivate"}


# ---------- fixtures and raw-file helpers ----------

@pytest.fixture(scope="session")
def data_root(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("ledgerly")
    for v in VARIANTS:
        generate(v, root)
    return root


@pytest.fixture(params=VARIANTS)
def ds(request, data_root) -> Path:
    return data_root / request.param


def rows(d: Path, rel: str) -> list[dict]:
    with open(d / rel, newline="") as f:
        return list(csv.DictReader(f))


def key(d: Path) -> dict:
    return yaml.safe_load((d / "answer_key.yaml").read_text())


def utc(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


def local(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=SYD)


def artifact_field(text: str, name: str) -> str:
    m = re.search(rf"^{name}: (.*)$", text, re.MULTILINE)
    return m.group(1).strip() if m else ""


def gap(d: Path, gid: str) -> dict | None:
    return next((g for g in key(d)["gaps"] if g["id"] == gid), None)


def trap(d: Path, tid: str) -> dict:
    return next(t for t in key(d)["traps"] if t["id"] == tid)


# ---------- documented queries (one per gap / trap) ----------

def first_removal_hours(d: Path) -> dict[str, float | None]:
    """C2: hours from HR termination to the first Okta suspend/deactivate, per terminated employee
    that has an Okta account (joined on email). None = no removal event at all."""
    okta_logins = {u["login"] for u in rows(d, "exports/okta_users.csv")}
    events = rows(d, "exports/okta_system_log.csv")
    out = {}
    for p in rows(d, "exports/hr_roster.csv"):
        if p["worker_type"] != "employee" or not p["termination_local"] or p["email"] not in okta_logins:
            continue
        t = local(p["termination_local"])
        times = sorted(utc(e["published_utc"]) for e in events
                       if e["target_login"] == p["email"] and e["event_type"] in REMOVAL and utc(e["published_utc"]) >= t)
        out[p["employee_id"]] = round((times[0] - t).total_seconds() / 3600, 1) if times else None
    return out


def q_g1_late_revocations(d):          # G1 (+ trap T1, which code also flags)
    return {e for e, h in first_removal_hours(d).items() if h is not None and h > 24}


def q_g2_never_revoked(d):             # G2
    return {e for e, h in first_removal_hours(d).items() if h is None}


def q_g3_unsigned_user_reviews(d):     # G3 (judgment: reads the review documents)
    return {artifact_field(p.read_text(), "ID") for p in (d / "artifacts/access_reviews").glob("UAR-*.md")
            if artifact_field(p.read_text(), "Signed") in ("", "(not signed)")}


def q_g4_admins_missing_from_review(d):   # G4
    admins = rows(d, "exports/aws_iam_admins.csv")
    found = set()
    for p in sorted((d / "artifacts/access_reviews").glob("PAR-*.md")):
        text = p.read_text()
        as_of = datetime.fromisoformat(artifact_field(text, "Review date")).replace(tzinfo=UTC)
        for a in admins:
            if utc(a["created_utc"]) <= as_of and a["principal_id"] not in text:
                found.add((a["principal_id"], artifact_field(text, "ID")))
    return found


def q_g5_self_approved_prs(d):         # G5
    return {r["pr_id"] for r in rows(d, "exports/github_pull_requests.csv")
            if r["base_branch"] == "main" and not (set(r["approvers"].split(";")) - {r["author"], ""})}


def q_g6_unticketed_emergency_deploys(d):   # G6
    return {r["deploy_id"] for r in rows(d, "exports/deploy_log.csv") if r["change_type"] == "emergency" and not r["ticket"]}


def period_iso_weeks() -> list[str]:
    weeks, day = [], P0
    while day <= P1:
        y, w, _ = day.isocalendar()
        if f"{y}-W{w:02d}" not in weeks:
            weeks.append(f"{y}-W{w:02d}")
        day += timedelta(days=1)
    return weeks


def q_g7_weeks_without_scan(d):        # G7
    scanned = {"{}-W{:02d}".format(*utc(r["started_utc"]).date().isocalendar()[:2])
               for r in rows(d, "exports/scanner_runs.csv") if r["status"] == "completed"}
    return [w for w in period_iso_weeks() if w not in scanned]


def critical_days_open(d) -> dict[str, int]:
    return {v["vuln_id"]: (utc(v["closed_utc"]).date() - utc(v["opened_utc"]).date()).days
            for v in rows(d, "exports/vulnerabilities.csv") if v["severity"] == "critical"}


def q_g8_critical_sla_breaches(d):     # G8 (+ trap T3, which code also flags)
    return {v for v, days in critical_days_open(d).items() if days > 30}


def training_days(d) -> dict[str, int]:
    """C10: days from hire (local date) to new-hire course completion, for employees hired in the period."""
    done = {r["employee_id"]: date.fromisoformat(r["completed_local"])
            for r in rows(d, "exports/lms_completions.csv") if r["course"] == "Security Awareness - New Hire"}
    out = {}
    for p in rows(d, "exports/hr_roster.csv"):
        hired = local(p["hire_local"]).date()
        if p["worker_type"] == "employee" and P0 <= hired <= P1:
            out[p["employee_id"]] = (done[p["employee_id"]] - hired).days
    return out


def q_g9_late_training(d):             # G9
    return {e for e, days in training_days(d).items() if days > 30}


def q_g10_restore_test_out_of_period(d):   # G10 (judgment: reads the report)
    text = (d / "artifacts/backup_restore_test_report.md").read_text()
    tested = date.fromisoformat(artifact_field(text, "Test date"))
    return {artifact_field(text, "ID")} if not (P0 <= tested <= P1) else set()


def q_t2_granted_before_approval(d):   # T2 (code flags; policy 4.2 explains)
    return {r["request_id"] for r in rows(d, "exports/access_requests.csv") if utc(r["approved_utc"]) > utc(r["granted_utc"])}


def q_t4_incidents_without_pir(d):     # T4 (code flags; resolution explains)
    docs = {p.stem for p in (d / "artifacts/post_incident_reviews").glob("*.md")}
    return {r["key"] for r in rows(d, "exports/jira_tickets.csv")
            if r["issue_type"] == "Incident" and r["linked_doc"] not in docs}


# ---------- criterion: gen writes the layout and is byte-identical ----------

def snapshot(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def test_gen_writes_layout_and_twice_is_byte_identical(tmp_path):
    """`mockaudit gen --variant base --seed 7` writes the layout; running it twice gives identical bytes."""
    assert cli_main(["gen", "--variant", "base", "--seed", "7", "--out", str(tmp_path / "one")]) == 0
    assert cli_main(["gen", "--variant", "base", "--seed", "7", "--out", str(tmp_path / "one")]) == 0  # rerun in place
    assert cli_main(["gen", "--variant", "base", "--seed", "7", "--out", str(tmp_path / "two")]) == 0
    one, two = tmp_path / "one" / "base", tmp_path / "two" / "base"
    for name in ["controls.yaml", "answers.yaml", "answer_key.yaml"]:
        assert (one / name).is_file()
    for folder in ["policies", "exports", "artifacts"]:
        assert any((one / folder).iterdir())
    assert snapshot(one) == snapshot(two)


# ---------- criterion: the answer key ----------

RESEARCH_TABLE = {  # research.md §4: control, gap type, severity
    "G1": ("C2", "operating", "high"), "G2": ("C2", "population_completeness", "high"),
    "G3": ("C3", "missing_evidence", "high"), "G4": ("C5", "population_completeness", "high"),
    "G5": ("C6", "segregation_of_duties", "high"), "G6": ("C7", "population_completeness", "moderate"),
    "G7": ("C8", "frequency_gap", "moderate"), "G8": ("C8", "sla_breach", "moderate"),
    "G9": ("C10", "operating", "moderate"), "G10": ("C12", "evidence_out_of_period", "moderate"),
}


def test_answer_key_lists_gaps_traps_clean_controls(data_root):
    """Base key: G1–G10 tagged code/judgment, traps T1–T4, clean C1/C4/C9/C11, research-table severities."""
    k = key(data_root / "base")
    assert [g["id"] for g in k["gaps"]] == [f"G{i}" for i in range(1, 11)]
    assert {g["id"]: g["tag"] for g in k["gaps"]} == {f"G{i}": ("judgment" if i in (3, 10) else "code") for i in range(1, 11)}
    assert [t["id"] for t in k["traps"]] == ["T1", "T2", "T3", "T4"]
    assert [t["control_id"] for t in k["traps"]] == ["C2", "C1", "C8", "C9"]
    assert k["clean_controls"] == ["C1", "C4", "C9", "C11"]
    for g in k["gaps"]:
        assert (g["control_id"], g["gap_type"], g["severity"]) == RESEARCH_TABLE[g["id"]]
    g1 = gap(data_root / "base", "G1")
    assert (g1["exceptions"], g1["tested"]) == (2, 18)


def test_severities_come_from_the_seven_rules(ds):
    """Every key severity equals the rule output for that control's risk and frequency."""
    controls = {c.control_id: c for c in load_controls(ds / "controls.yaml")}
    for g in key(ds)["gaps"]:
        c = controls[g["control_id"]]
        assert (g["severity"], g["severity_rule"]) == severity(g["gap_type"], g["exceptions"], g["tested"], c.risk, c.periodic)


# ---------- criterion: every gap and trap is found by its documented query (all variants) ----------

def test_queries_find_every_gap_and_trap(ds):
    k = key(ds)
    planted = {g["id"] for g in k["gaps"]}
    t1 = trap(ds, "T1")["record_ids"][0]
    g1 = set(gap(ds, "G1")["record_ids"][::2]) if "G1" in planted else set()
    assert q_g1_late_revocations(ds) == g1 | {t1}                       # G1 + trap T1
    assert q_g2_never_revoked(ds) == ({gap(ds, "G2")["record_ids"][0]} if "G2" in planted else set())
    assert q_g3_unsigned_user_reviews(ds) == (set(gap(ds, "G3")["record_ids"]) if "G3" in planted else set())
    assert q_g4_admins_missing_from_review(ds) == ({tuple(gap(ds, "G4")["record_ids"])} if "G4" in planted else set())
    assert q_g5_self_approved_prs(ds) == (set(gap(ds, "G5")["record_ids"]) if "G5" in planted else set())
    assert q_g6_unticketed_emergency_deploys(ds) == (set(gap(ds, "G6")["record_ids"]) if "G6" in planted else set())
    assert q_g7_weeks_without_scan(ds) == (gap(ds, "G7")["missing_weeks"] if "G7" in planted else [])
    t3 = trap(ds, "T3")["record_ids"][0]
    assert q_g8_critical_sla_breaches(ds) == (set(gap(ds, "G8")["record_ids"]) if "G8" in planted else set()) | {t3}
    assert q_g9_late_training(ds) == (set(gap(ds, "G9")["record_ids"][::2]) if "G9" in planted else set())
    assert q_g10_restore_test_out_of_period(ds) == (set(gap(ds, "G10")["record_ids"]) if "G10" in planted else set())
    assert q_t2_granted_before_approval(ds) == set(trap(ds, "T2")["record_ids"])
    assert q_t4_incidents_without_pir(ds) == set(trap(ds, "T4")["record_ids"])


def test_every_cited_record_id_exists(ds):
    """Answer-key record ids exist in the raw files (so citations to them can be valid)."""
    blob = "\n".join(p.read_text() for p in ds.rglob("*") if p.is_file() and p.name != "answer_key.yaml")
    k = key(ds)
    for item in k["gaps"] + k["traps"]:
        for rid in item["record_ids"]:
            assert rid in blob, f"{item['id']}: {rid} not in raw files"


def test_traps_have_grounded_explanations(ds):
    """Each trap's innocent explanation is in the raw files (policy text, linked record or owner answer)."""
    hr = {r["employee_id"]: r for r in rows(ds, "exports/hr_roster.csv")}
    e, c, _ = trap(ds, "T1")["record_ids"]
    assert hr[e]["termination_reason"] == "Conversion to contractor" and hr[c]["prior_employee_id"] == e
    req = next(r for r in rows(ds, "exports/access_requests.csv") if r["request_id"] == trap(ds, "T2")["record_ids"][0])
    assert req["role"] == "Employee-Base" and "Employee-Base" in (ds / "policies/access_control.md").read_text()
    vuln_id, risk = trap(ds, "T3")["record_ids"]
    vuln = next(v for v in rows(ds, "exports/vulnerabilities.csv") if v["vuln_id"] == vuln_id)
    ticket = next(t for t in rows(ds, "exports/jira_tickets.csv") if t["key"] == risk)
    assert vuln["risk_acceptance"] == risk and ticket["resolution"] == "Approved" and utc(ticket["expires_utc"]) > utc(vuln["closed_utc"])
    inc = next(t for t in rows(ds, "exports/jira_tickets.csv") if t["key"] == trap(ds, "T4")["record_ids"][0])
    assert inc["resolution"].startswith("Not an incident")
    answers = yaml.safe_load((ds / "answers.yaml").read_text())["owner_answers"]
    for tid in ["T1", "T2", "T3", "T4"]:
        assert any(set(trap(ds, tid)["record_ids"]) & set(a["record_ids"]) for a in answers), tid


# ---------- criterion: noise is present ----------

def test_noise_is_present_and_not_a_gap(data_root):
    d = data_root / "base"
    hr = {r["email"]: r for r in rows(d, "exports/hr_roster.csv")}
    users = rows(d, "exports/okta_users.csv")
    # name-format mismatch: HR "Last, First" vs Okta "First Last" for the same login
    u = users[0]
    first, last = u["display_name"].split(" ", 1)
    assert hr[u["login"]]["name"] == f"{last}, {first}"
    # mixed time zones: HR local Sydney, Okta UTC; morning terminations revoked on the previous UTC day, still on time
    assert {r["timezone"] for r in hr.values()} == {"Australia/Sydney"}
    hours = first_removal_hours(d)
    tz_rows = next(n for n in key(d)["noise"] if n["kind"] == "time_zone")["record_ids"]
    by_id = {r["employee_id"]: r for r in hr.values()}
    events = rows(d, "exports/okta_system_log.csv")
    for e in tz_rows:
        t = local(by_id[e]["termination_local"])
        first_ev = min(utc(x["published_utc"]) for x in events if x["target_login"] == by_id[e]["email"] and x["event_type"] in REMOVAL)
        assert first_ev.date() < t.date() and hours[e] <= 24
    # same-day suspension then deletion 6 days later: not a gap
    e, delete_id = next(n for n in key(d)["noise"] if n["kind"] == "suspend_then_delete")["record_ids"]
    assert hours[e] <= 24 and e not in q_g1_late_revocations(d)
    term = local(by_id[e]["termination_local"])
    susp = min(utc(x["published_utc"]) for x in events if x["target_login"] == by_id[e]["email"] and x["event_type"] in REMOVAL)
    assert susp.astimezone(SYD).date() == term.date() and susp.date() == term.astimezone(UTC).date()
    assert next(x for x in events if x["event_id"] == delete_id)["event_type"] == "user.lifecycle.delete"
    # compliant emergency change: Friday deploy, approved the following Tuesday
    dep_id, chg = next(n for n in key(d)["noise"] if n["kind"] == "compliant_emergency")["record_ids"]
    dep = next(r for r in rows(d, "exports/deploy_log.csv") if r["deploy_id"] == dep_id)
    tick = next(r for r in rows(d, "exports/jira_tickets.csv") if r["key"] == chg)
    assert utc(dep["deployed_utc"]).weekday() == 4 and utc(tick["approved_utc"]).weekday() == 1
    assert (utc(tick["approved_utc"]).date() - utc(dep["deployed_utc"]).date()).days == 4
    # scan late in the same week: not a missing week
    late = next(r for r in rows(d, "exports/scanner_runs.csv") if utc(r["started_utc"]).weekday() != 2)
    week = "{}-W{:02d}".format(*utc(late["started_utc"]).date().isocalendar()[:2])
    assert week not in q_g7_weeks_without_scan(d)


# ---------- criterion: handover §11 domain-rule edges ----------

def test_domain_rule_edges(data_root):
    d = data_root / "base"
    hr = {r["employee_id"]: r for r in rows(d, "exports/hr_roster.csv")}
    # Friday 18:00 → Monday 09:00 is an exception (63 clock hours, part of G1)
    e = next(n for n in key(d)["noise"] if n["kind"] == "edge_weekend")["record_ids"][0]
    t = local(hr[e]["termination_local"])
    assert (t.weekday(), t.hour) == (4, 18)
    assert first_removal_hours(d)[e] == 63.0 and e in q_g1_late_revocations(d) and e in gap(d, "G1")["record_ids"]
    # exactly 30 days passes, 31 fails (C8 critical at 30; C10 trainees at 30 and 31)
    v30 = next(n for n in key(d)["noise"] if n["control_id"] == "C8" and n["kind"] == "edge_30_days")["record_ids"][0]
    assert critical_days_open(d)[v30] == 30 and v30 not in q_g8_critical_sla_breaches(d)
    days = training_days(d)
    h30 = next(n for n in key(d)["noise"] if n["control_id"] == "C10" and n["kind"] == "edge_30_days")["record_ids"][0]
    assert days[h30] == 30 and h30 not in q_g9_late_training(d)
    h31 = [x for x, n in days.items() if n == 31]
    assert len(h31) == 1 and h31[0] in q_g9_late_training(d) and h31[0] in gap(d, "G9")["record_ids"]
    # a Dec 15 hire trained Jan 10 passes
    dec15 = next(n for n in key(d)["noise"] if n["kind"] == "edge_cross_year")["record_ids"][0]
    assert hr[dec15]["hire_local"].startswith("2025-12-15") and days[dec15] == 26 and dec15 not in q_g9_late_training(d)


# ---------- criterion: variants re-plant gaps, keys match ----------

def test_variants_replant_different_combinations(data_root):
    keys = {v: key(data_root / v) for v in VARIANTS}
    planted = {v: {g["id"] for g in k["gaps"]} for v, k in keys.items()}
    assert len(planted["base"]) == 10 and len(planted["a"]) == len(planted["b"]) == 7
    assert planted["a"] != planted["b"]
    for v in ["a", "b"]:
        assert sorted(keys[v]["not_planted"], key=lambda g: int(g[1:])) == sorted(set(planted["base"]) - planted[v], key=lambda g: int(g[1:]))
        dropped_controls = {RESEARCH_TABLE[g][0] for g in keys[v]["not_planted"]}
        gapped = {g["control_id"] for g in keys[v]["gaps"]}
        assert dropped_controls - gapped <= set(keys[v]["clean_controls"])
        # re-placed on different records than base
        for gid in planted[v]:
            assert gap(data_root / v, gid)["record_ids"] != gap(data_root / "base", gid)["record_ids"], gid
        assert trap(data_root / v, "T1")["record_ids"] != trap(data_root / "base", "T1")["record_ids"]
    # "keys match": test_queries_find_every_gap_and_trap runs on base, a and b


# ---------- criterion: invalid controls.yaml names the control and the field ----------

def test_invalid_controls_yaml_names_control_and_field(tmp_path, data_root):
    controls = yaml.safe_load((data_root / "base" / "controls.yaml").read_text())
    assert len(load_controls(data_root / "base" / "controls.yaml")) == 12
    controls[2]["frequency"] = "fortnightly"            # C3
    bad = tmp_path / "controls.yaml"
    bad.write_text(yaml.safe_dump(controls))
    with pytest.raises(ControlSpecError, match=r"control C3: field 'frequency'"):
        load_controls(bad)
    controls[2]["frequency"] = "quarterly"
    del controls[7]["risk"]                             # C8
    bad.write_text(yaml.safe_dump(controls))
    with pytest.raises(ControlSpecError, match=r"control C8: field 'risk'"):
        load_controls(bad)
    controls[7]["risk"] = "moderate"
    controls[0]["period"] = ["2026-09-30", "2025-10-01"]      # reversed, C1
    bad.write_text(yaml.safe_dump(controls))
    with pytest.raises(ControlSpecError, match=r"control C1: field 'period'"):
        load_controls(bad)
    bad.write_text("- control_id: C1\n  description: [unclosed\n")
    with pytest.raises(ControlSpecError, match="not valid YAML"):
        load_controls(bad)


def test_c10_new_hire_step_is_scoped_to_employees(data_root):
    """Contractors hired in the period (e.g. the T1 conversion, X3001) are out of C10 new-hire scope (policy 2.1)."""
    c10 = next(c for c in load_controls(data_root / "base" / "controls.yaml") if c.control_id == "C10")
    step = next(s for s in c10.test_recipe if s.id == "new_hire")
    assert step.params["where"] == {"worker_type": "employee"}
    assert "Contractors" in (data_root / "base" / "policies/security_training.md").read_text()
