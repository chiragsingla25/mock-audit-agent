"""Phase 2 criterion: each check has unit tests, including both edges of its threshold.

Also the 7 severity rules (rule edges). Fixtures are tiny in-memory evidence sets.
"""

from __future__ import annotations

from datetime import date

import pytest

from mockaudit.checks import CHECKS, business_days_between, iso_weeks, quarters
from mockaudit.evidence import Evidence
from mockaudit.severity import severity

PERIOD = (date(2025, 10, 1), date(2026, 9, 30))


def ev(data: dict, ids: dict) -> Evidence:
    return Evidence(data, ids, PERIOD)


def failed(run) -> list[str]:
    return [r.record_id for r in run.results if not r.passed]


def passed(run) -> list[str]:
    return [r.record_id for r in run.results if r.passed]


def test_registry_has_every_check_the_recipes_name():
    from mockaudit.datagen.ledgerly import CONTROLS_YAML
    from mockaudit.specs import load_controls
    named = {s.check for c in load_controls(CONTROLS_YAML) for s in c.test_recipe if s.check}
    assert named <= set(CHECKS)
    assert len(CHECKS) == 12


# ---------- revocation_delay: 24.0 h passes, 24.1 h fails; UTC across time zones ----------

def hr(eid, email, term, tz="Australia/Sydney", worker="employee"):
    return {"employee_id": eid, "email": email, "worker_type": worker, "hire_local": "2020-01-01 09:00",
            "termination_local": term, "timezone": tz}


def revocation_ev(rows, events):
    return ev({"hr": rows, "users": [{"user_id": f"u{i}", "login": r["email"]} for i, r in enumerate(rows)],
               "log": events}, {"hr": "employee_id", "users": "user_id", "log": "event_id"})


def evt(eid, login, ts, etype="user.lifecycle.suspend"):
    return {"event_id": eid, "target_login": login, "published_utc": ts, "event_type": etype}


P_REVOKE = {"hr": "hr", "accounts": "users", "events_source": "log", "max_hours": 24,
            "events": ["user.lifecycle.suspend", "user.lifecycle.deactivate"]}


def test_revocation_delay_edges():
    rows = [hr("E1", "a@x", "2026-03-02 10:00", "UTC"), hr("E2", "b@x", "2026-03-02 10:00", "UTC"),
            hr("E3", "c@x", "2026-03-06 18:00"), hr("E4", "d@x", "2026-03-10 08:00")]
    events = [evt("K1", "a@x", "2026-03-03T10:00:00Z"),                     # exactly 24.0 h → pass
              evt("K2", "b@x", "2026-03-03T10:06:00Z"),                     # 24.1 h → fail
              evt("K3", "c@x", "2026-03-08T22:00:00Z"),                     # Fri 18:00 AEDT → Mon 09:00 AEDT = 63 h → fail
              evt("K4", "d@x", "2026-03-09T22:00:00Z", "user.session.start"),  # not a removal
              evt("K5", "d@x", "2026-03-09T22:30:00Z")]                     # 08:00 AEDT = 21:00Z prev day → 1.5 h → pass
    run = CHECKS["revocation_delay"](revocation_ev(rows, events), "timeliness", P_REVOKE)
    assert passed(run) == ["E1", "E4"] and failed(run) == ["E2", "E3"]
    assert next(r for r in run.results if r.record_id == "E3").detail["hours"] == 63.0
    assert next(r for r in run.results if r.record_id == "E2").detail["citations"] == [
        {"source": "hr", "record_id": "E2"}, {"source": "log", "record_id": "K2"}]


def test_revocation_delay_skips_never_revoked_and_unprovisioned():
    rows = [hr("E1", "a@x", "2026-03-02 10:00", "UTC")]
    run = CHECKS["revocation_delay"](revocation_ev(rows, []), "timeliness", P_REVOKE)
    assert run.results == []                                        # completeness owns "never revoked"


# ---------- population_diff ----------

def test_population_diff_missing_and_never_provisioned():
    left = [hr("E1", "a@x", "2026-03-02 10:00"), hr("E2", "b@x", "2026-03-02 10:00"),
            hr("X1", "c@x", "2026-03-02 10:00", worker="contractor"), hr("E3", "d@x", "2025-09-30 10:00")]
    data = {"hr": left, "users": [{"user_id": "u1", "login": "a@x"}, {"user_id": "u2", "login": "b@x"}],
            "log": [evt("K1", "a@x", "2026-03-02T12:00:00Z")]}
    e = ev(data, {"hr": "employee_id", "users": "user_id", "log": "event_id"})
    p = {"left": "hr", "left_where": {"terminated_in_period": True}, "left_key": "email", "right": "log",
         "right_where": {"event_type": ["user.lifecycle.suspend"]}, "right_key": "target_login",
         "require_in": {"source": "users", "key": "login"}}
    run = CHECKS["population_diff"](e, "completeness", p)
    assert passed(run) == ["E1"] and failed(run) == ["E2"]          # E3 terminated before the period: out
    assert any("X1" in n for n in run.notes)
    assert run.results[1].detail["citations"][1] == {"source": "users", "record_id": "u2"}


def test_population_diff_employed_throughout_edges():
    people = [{"employee_id": "E1", "worker_type": "employee", "hire_local": "2026-03-01 09:00", "termination_local": ""},
              {"employee_id": "E2", "worker_type": "employee", "hire_local": "2026-03-02 09:00", "termination_local": ""},
              {"employee_id": "E3", "worker_type": "employee", "hire_local": "2020-01-01 09:00", "termination_local": "2026-05-31 17:00"},
              {"employee_id": "E4", "worker_type": "employee", "hire_local": "2020-01-01 09:00", "termination_local": "2026-05-30 17:00"}]
    e = ev({"hr": people, "lms": [{"completion_id": "L1", "employee_id": "E1", "course": "Annual"}]},
           {"hr": "employee_id", "lms": "completion_id"})
    p = {"left": "hr", "left_where": {"employed_throughout": ["2026-03-01", "2026-05-31"]}, "left_key": "employee_id",
         "right": "lms", "right_where": {"course": "Annual"}, "right_key": "employee_id"}
    run = CHECKS["population_diff"](e, "annual", p)
    assert passed(run) == ["E1"] and failed(run) == ["E3"]           # E2 hired after start, E4 left before end: out of scope


# ---------- approval_before_grant: equal passes, 1 s late fails ----------

def test_approval_before_grant_edges():
    rows = [{"request_id": "A1", "approved_utc": "2026-01-05T10:00:00Z", "granted_utc": "2026-01-05T10:00:00Z"},
            {"request_id": "A2", "approved_utc": "2026-01-05T10:00:01Z", "granted_utc": "2026-01-05T10:00:00Z"}]
    run = CHECKS["approval_before_grant"](ev({"req": rows}, {"req": "request_id"}), "approval",
                                          {"source": "req", "approved": "approved_utc", "granted": "granted_utc"})
    assert passed(run) == ["A1"] and failed(run) == ["A2"]


# ---------- periodic_occurrence ----------

def test_quarters_and_weeks_cover_the_period():
    assert [q for q, _ in quarters(PERIOD)] == ["2025Q4", "2026Q1", "2026Q2", "2026Q3"]
    weeks = iso_weeks(PERIOD)
    assert weeks[0] == "2025-W40" and weeks[-1] == "2026-W40" and len(weeks) == 53


def test_periodic_occurrence_quarter_missing():
    docs = [{"ID": f"UAR-{q}", "text": ""} for q in ["2025Q4", "2026Q1", "2026Q3"]] + [{"ID": "PAR-2026Q2", "text": ""}]
    run = CHECKS["periodic_occurrence"](ev({"docs": docs}, {"docs": "ID"}), "occurrence",
                                        {"source": "docs", "prefix": "UAR", "every": "quarter"})
    assert failed(run) == ["2026Q2"]                                  # PAR doesn't count for UAR
    assert run.results[2].detail["citations"] == [{"source": "docs", "record_id": "UAR-2026Q1"},
                                                  {"source": "docs", "record_id": "UAR-2026Q3"}]


def test_periodic_occurrence_week_edges():
    def scan(sid, ts, status="completed"):
        return {"scan_id": sid, "started_utc": ts, "status": status}
    weeks = iso_weeks(PERIOD)
    rows = [scan(f"S{i}", f"{d}T02:00:00Z") for i, d in enumerate(
        [f"{w}" for w in []])]
    # one scan per ISO week via its Wednesday, except: week 2026-W10 scanned on Sunday (last day of the week),
    # 2026-W11 only has a failed scan, and 2026-W12 has none
    from datetime import timedelta
    d = PERIOD[0]
    while d <= PERIOD[1]:
        label = "{}-W{:02d}".format(*d.isocalendar()[:2])
        if d.weekday() == 2 and label not in ("2026-W10", "2026-W11", "2026-W12"):
            rows.append(scan(f"S-{label}", f"{d}T02:00:00Z"))
        d += timedelta(days=1)
    rows += [scan("S-late", "2026-03-08T23:59:00Z"), scan("S-bad", "2026-03-11T02:00:00Z", "failed")]
    run = CHECKS["periodic_occurrence"](ev({"scans": rows}, {"scans": "scan_id"}), "weekly",
                                        {"source": "scans", "date": "started_utc", "where": {"status": "completed"},
                                         "every": "iso_week"})
    assert failed(run) == ["2026-W11", "2026-W12"] and len(run.results) == len(weeks)
    assert "2026-W10" in passed(run)


# ---------- set_mismatch: created on the review date counts, the day after does not ----------

def test_set_mismatch_as_of_edges():
    admins = [{"principal_id": "P1", "created_utc": "2026-01-07T23:00:00Z"},
              {"principal_id": "P2", "created_utc": "2026-01-07T01:00:00Z"},
              {"principal_id": "P3", "created_utc": "2026-01-08T00:00:00Z"}]
    review = {"ID": "PAR-2025Q4", "Review date": "2026-01-07", "text": "| P1 | keep |"}
    run = CHECKS["set_mismatch"](ev({"iam": admins, "rev": [review]}, {"iam": "principal_id", "rev": "ID"}), "completeness",
                                 {"left": "iam", "left_key": "principal_id", "left_created": "created_utc",
                                  "right": "rev", "prefix": "PAR", "as_of": "Review date"})
    assert passed(run) == ["P1@PAR-2025Q4"] and failed(run) == ["P2@PAR-2025Q4"]   # P3 created after: not expected


# ---------- config_assert ----------

def test_config_assert_uncovered_and_inactive():
    groups = [{"group_id": "g1", "name": "Everyone"}, {"group_id": "g2", "name": "Eng"}, {"group_id": "g3", "name": "Ops"}]
    policy = {"policies": [
        {"id": "p1", "status": "ACTIVE", "rules": [{"id": "r1", "status": "ACTIVE", "factor_required": True, "groups_included": ["g1"]},
                                                   {"id": "r2", "status": "INACTIVE", "factor_required": True, "groups_included": ["g2"]}]},
        {"id": "p2", "status": "INACTIVE", "rules": [{"id": "r3", "status": "ACTIVE", "factor_required": True, "groups_included": ["g3"]}]}]}
    run = CHECKS["config_assert"](ev({"pol": policy, "groups": groups}, {"pol": "id", "groups": "group_id"}), "coverage",
                                  {"policy": "pol", "groups": "groups", "require": "factor_required"})
    assert passed(run) == ["g1"] and failed(run) == ["g2", "g3"]


# ---------- author_ne_approver ----------

def test_author_ne_approver():
    prs = [{"pr_id": "P1", "author": "ann", "approvers": "bob"}, {"pr_id": "P2", "author": "ann", "approvers": "ann"},
           {"pr_id": "P3", "author": "ann", "approvers": "ann;bob"}, {"pr_id": "P4", "author": "ann", "approvers": ""}]
    run = CHECKS["author_ne_approver"](ev({"prs": prs}, {"prs": "pr_id"}), "segregation",
                                       {"source": "prs", "author": "author", "approvers": "approvers"})
    assert passed(run) == ["P1", "P3"] and failed(run) == ["P2", "P4"]


# ---------- unticketed_deploys ----------

def test_unticketed_deploys():
    deploys = [{"deploy_id": "D1", "change_type": "emergency", "ticket": "CHG-1"},
               {"deploy_id": "D2", "change_type": "emergency", "ticket": ""},
               {"deploy_id": "D3", "change_type": "emergency", "ticket": "CHG-404"},
               {"deploy_id": "D4", "change_type": "standard", "ticket": ""}]
    run = CHECKS["unticketed_deploys"](ev({"dep": deploys, "jira": [{"key": "CHG-1"}]}, {"dep": "deploy_id", "jira": "key"}),
                                       "ticketed", {"source": "dep", "where": {"change_type": "emergency"}, "link": "ticket", "tickets": "jira"})
    assert passed(run) == ["D1"] and failed(run) == ["D2", "D3"]


# ---------- sla_days: calendar 30 passes / 31 fails; business 2 passes / 3 fails ----------

def test_business_days_between():
    assert business_days_between(date(2026, 2, 13), date(2026, 2, 17)) == 2      # Fri → Tue
    assert business_days_between(date(2026, 2, 13), date(2026, 2, 18)) == 3      # Fri → Wed
    assert business_days_between(date(2026, 2, 13), date(2026, 2, 13)) == 0


def test_sla_days_calendar_edges():
    vulns = [{"vuln_id": "V1", "severity": "critical", "opened_utc": "2026-01-31T10:00:00Z", "closed_utc": "2026-03-02T16:00:00Z"},
             {"vuln_id": "V2", "severity": "critical", "opened_utc": "2026-01-31T10:00:00Z", "closed_utc": "2026-03-03T01:00:00Z"},
             {"vuln_id": "V3", "severity": "high", "opened_utc": "2026-01-01T10:00:00Z", "closed_utc": "2026-06-01T10:00:00Z"},
             {"vuln_id": "V4", "severity": "critical", "opened_utc": "2026-01-01T10:00:00Z", "closed_utc": ""}]
    run = CHECKS["sla_days"](ev({"v": vulns}, {"v": "vuln_id"}), "critical_sla",
                             {"source": "v", "where": {"severity": "critical"}, "start": "opened_utc", "end": "closed_utc",
                              "days": 30, "business": False})
    assert passed(run) == ["V1"] and failed(run) == ["V2", "V4"]     # 30 d 6 h counts as 30 calendar days


def test_sla_days_business_edges_with_join():
    deploys = [{"deploy_id": "D1", "change_type": "emergency", "ticket": "C1", "deployed_utc": "2026-02-13T22:00:00Z"},
               {"deploy_id": "D2", "change_type": "emergency", "ticket": "C2", "deployed_utc": "2026-02-13T22:00:00Z"},
               {"deploy_id": "D3", "change_type": "emergency", "ticket": "", "deployed_utc": "2026-02-13T22:00:00Z"}]
    jira = [{"key": "C1", "approved_utc": "2026-02-17T23:00:00Z"}, {"key": "C2", "approved_utc": "2026-02-18T00:30:00Z"}]
    run = CHECKS["sla_days"](ev({"dep": deploys, "jira": jira}, {"dep": "deploy_id", "jira": "key"}), "retro_approval",
                             {"source": "dep", "where": {"change_type": "emergency"}, "start": "deployed_utc",
                              "join": {"source": "jira", "link_field": "ticket", "key": "key"}, "end": "approved_utc",
                              "days": 2, "business": True})
    assert passed(run) == ["D1"] and failed(run) == ["D2"]           # D3 has no ticket: the ticketed step owns it


# ---------- required_link ----------

def test_required_link():
    tickets = [{"key": "I1", "issue_type": "Incident", "linked_doc": "PIR-I1"},
               {"key": "I2", "issue_type": "Incident", "linked_doc": ""},
               {"key": "I3", "issue_type": "Incident", "linked_doc": "PIR-MISSING"},
               {"key": "R1", "issue_type": "Risk Acceptance", "linked_doc": ""}]
    run = CHECKS["required_link"](ev({"jira": tickets, "pir": [{"ID": "PIR-I1", "text": ""}]}, {"jira": "key", "pir": "ID"}),
                                  "pir", {"source": "jira", "where": {"issue_type": "Incident"}, "link": "linked_doc", "target": "pir"})
    assert passed(run) == ["I1"] and failed(run) == ["I2", "I3"]


# ---------- days_after_event: 30 passes, 31 fails, cross-year, missing ----------

def test_days_after_event_edges():
    people = [{"employee_id": e, "worker_type": w, "hire_local": h, "timezone": "Australia/Sydney"}
              for e, w, h in [("E1", "employee", "2026-02-01 09:00"), ("E2", "employee", "2026-02-01 09:00"),
                              ("E3", "employee", "2025-12-15 09:00"), ("E4", "employee", "2026-02-01 09:00"),
                              ("C1", "contractor", "2026-02-01 09:00"), ("E5", "employee", "2025-09-15 09:00")]]
    lms = [{"completion_id": "L1", "employee_id": "E1", "course": "NH", "completed_local": "2026-03-03"},   # 30 days
           {"completion_id": "L2", "employee_id": "E2", "course": "NH", "completed_local": "2026-03-04"},   # 31 days
           {"completion_id": "L3", "employee_id": "E3", "course": "NH", "completed_local": "2026-01-10"},   # 26 days
           {"completion_id": "L4", "employee_id": "E4", "course": "Other", "completed_local": "2026-02-02"}]
    run = CHECKS["days_after_event"](ev({"hr": people, "lms": lms}, {"hr": "employee_id", "lms": "completion_id"}), "new_hire",
                                     {"people": "hr", "where": {"worker_type": "employee", "hired_in_period": True},
                                      "event": "hire_local", "done_source": "lms", "done": "completed_local", "course": "NH", "days": 30})
    assert passed(run) == ["E1", "E3"] and failed(run) == ["E2", "E4"]   # C1 contractor and E5 (pre-period) out of scope


# ---------- date_in_period: both period boundaries pass, the days outside fail ----------

def test_date_in_period_edges():
    vendors = [{"vendor_id": v, "criticality": "critical", "last_risk_review_date": d}
               for v, d in [("V1", "2025-10-01"), ("V2", "2026-09-30"), ("V3", "2025-09-30"), ("V4", "2026-10-01"), ("V5", "")]]
    vendors.append({"vendor_id": "V6", "criticality": "standard", "last_risk_review_date": "2020-01-01"})
    run = CHECKS["date_in_period"](ev({"vr": vendors}, {"vr": "vendor_id"}), "review_in_period",
                                   {"source": "vr", "where": {"criticality": "critical"}, "date": "last_risk_review_date"})
    assert passed(run) == ["V1", "V2"] and failed(run) == ["V3", "V4", "V5"]


# ---------- severity rules (architecture.md §6), first match wins ----------

@pytest.mark.parametrize("args, expected", [
    (("segregation_of_duties", 1, 300, "low", False), ("high", 1)),
    (("population_completeness", 1, 100, "high", False), ("high", 2)),
    (("population_completeness", 1, 100, "moderate", False), ("moderate", 6)),
    (("frequency_gap", 1, 53, "high", True), ("high", 3)),
    (("frequency_gap", 1, 53, "high", False), ("moderate", 5)),          # rule 3 needs a periodic control
    (("operating", 2, 18, "high", False), ("high", 4)),                  # 11.1% > 10%
    (("operating", 1, 10, "high", False), ("moderate", 5)),              # exactly 10% is not > 10%
    (("operating", 2, 19, "high", False), ("high", 4)),                  # 10.5%
    (("operating", 3, 30, "moderate", False), ("moderate", 6)),
    (("sla_breach", 1, 9, "low", False), ("low", 7)),
])
def test_severity_rules(args, expected):
    assert severity(*args) == expected
