"""CHECKS registry: deterministic tests over the full population. Code does all counting, dates and SLAs.

Each check takes (evidence, params) and returns a CheckRun. A failed CheckResult carries the record
ids to cite in `detail["citations"]`. `run_control_checks` turns failures into Candidates.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, timedelta

from mockaudit.evidence import Evidence, local_date, parse_ts
from mockaudit.schemas import Candidate, CheckResult, Citation, ControlSpec


@dataclass
class CheckRun:
    results: list[CheckResult] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def ok(self, step: str, record_id: str, **detail):
        self.results.append(CheckResult(step_id=step, record_id=record_id, passed=True, detail=detail))

    def fail(self, step: str, record_id: str, reason: str, citations: list[tuple[str, str]], **detail):
        self.results.append(CheckResult(step_id=step, record_id=record_id, passed=False, detail={
            "reason": reason, "citations": [{"source": s, "record_id": r} for s, r in citations], **detail}))


CheckFn = Callable[[Evidence, str, dict], CheckRun]
CHECKS: dict[str, CheckFn] = {}


def check(name: str):
    def wrap(fn: CheckFn) -> CheckFn:
        CHECKS[name] = fn
        return fn
    return wrap


def business_days_between(start: date, end: date) -> int:
    """Mon–Fri days after `start` up to and including `end` (Fri → Tue = 2)."""
    n, d = 0, start
    while d < end:
        d += timedelta(days=1)
        n += d.weekday() < 5
    return n


def add_business_days(d: date, n: int) -> date:
    while n > 0:
        d += timedelta(days=1)
        n -= d.weekday() < 5
    return d


def signoff_facts(doc: dict, due_business_days: int, evidence: date | None) -> dict:
    """Sign-off dates computed by code for a review document, so the LLMs never count business days."""
    qend = date.fromisoformat(doc["Quarter end"])
    due = add_business_days(qend, due_business_days)
    raw = doc.get("Signed", "").strip()
    signed = date.fromisoformat(raw) if len(raw) == 10 and raw[4] == "-" else None
    passed = evidence > due if evidence else None
    return {"quarter_end": qend.isoformat(), "signoff_due": due.isoformat(),
            "signed": signed.isoformat() if signed else "not signed",
            "evidence_collected": evidence.isoformat() if evidence else None, "deadline_passed": passed,
            "signed_on_time": (signed <= due) if signed else (False if passed else None)}


def quarters(period: tuple[date, date]) -> list[tuple[str, date]]:
    out, y, q = [], period[0].year, (period[0].month - 1) // 3 + 1
    while True:
        end = date(y, 3 * q, 31 if q in (1, 4) else 30)
        out.append((f"{y}Q{q}", end))
        if end >= period[1]:
            return out
        y, q = (y + 1, 1) if q == 4 else (y, q + 1)


def iso_weeks(period: tuple[date, date]) -> list[str]:
    weeks, d = [], period[0]
    while d <= period[1]:
        label = "{}-W{:02d}".format(*d.isocalendar()[:2])
        if label not in weeks:
            weeks.append(label)
        d += timedelta(days=1)
    return weeks


def nearest(present: list[tuple[str, str]], label: str) -> list[str]:
    """Record ids of the nearest present units before and after a missing unit (sorted labels)."""
    before = [rid for lab, rid in present if lab < label]
    after = [rid for lab, rid in present if lab > label]
    return ([before[-1]] if before else []) + ([after[0]] if after else [])


# ---------- checks ----------

@check("population_diff")
def population_diff(ev: Evidence, step: str, p: dict) -> CheckRun:
    """Every left item appears in the right population (joined on left_key/right_key)."""
    run = CheckRun()
    right = {r[p["right_key"]] for r in ev.rows(p["right"], p.get("right_where"))}
    req = p.get("require_in")
    accounts = {r[req["key"]]: r for r in ev.rows(req["source"])} if req else {}
    for row in ev.rows(p["left"], p.get("left_where")):
        k, rid = row[p["left_key"]], ev.rid(p["left"], row)
        if req and k not in accounts:
            run.notes.append(f"{rid}: no {req['source']} record, so nothing to check (not an exception).")
            continue
        if k in right:
            run.ok(step, rid)
        else:
            cites = [(p["left"], rid)] + ([(req["source"], ev.rid(req["source"], accounts[k]))] if req else [])
            run.fail(step, rid, f"{rid} is missing from {p['right']}.", cites)
    return run


@check("revocation_delay")
def revocation_delay(ev: Evidence, step: str, p: dict) -> CheckRun:
    """Hours (UTC) from HR termination to the first removal event; fail if over max_hours."""
    run = CheckRun()
    logins = {r["login"] for r in ev.rows(p["accounts"])}
    events = [e for e in ev.rows(p["events_source"]) if e["event_type"] in p["events"]]
    for row in ev.rows(p["hr"], {"worker_type": "employee", "terminated_in_period": True}):
        if row["email"] not in logins:
            continue
        t = parse_ts(row["termination_local"], row["timezone"])
        after = sorted((parse_ts(e["published_utc"]), e) for e in events
                       if e["target_login"] == row["email"] and parse_ts(e["published_utc"]) >= t)
        rid = ev.rid(p["hr"], row)
        if not after:
            continue                                # no removal at all: the completeness step owns it
        when, e = after[0]
        hours = round((when - t).total_seconds() / 3600, 1)
        if hours <= p["max_hours"]:
            run.ok(step, rid, hours=hours)
        else:
            run.fail(step, rid, f"First suspend/deactivate {hours} h after termination (limit {p['max_hours']} h).",
                     [(p["hr"], rid), (p["events_source"], ev.rid(p["events_source"], e))], hours=hours)
    return run


@check("approval_before_grant")
def approval_before_grant(ev: Evidence, step: str, p: dict) -> CheckRun:
    run = CheckRun()
    for row in ev.rows(p["source"]):
        rid = ev.rid(p["source"], row)
        approved, granted = parse_ts(row[p["approved"]]), parse_ts(row[p["granted"]])
        if approved <= granted:
            run.ok(step, rid)
        else:
            hours = round((approved - granted).total_seconds() / 3600, 1)
            run.fail(step, rid, f"Granted {hours} h before it was approved.", [(p["source"], rid)], hours_early=hours)
    return run


@check("periodic_occurrence")
def periodic_occurrence(ev: Evidence, step: str, p: dict) -> CheckRun:
    """Each quarter (artifact ID `<prefix>-YYYYQn`) or ISO week (row date) in the period has an occurrence."""
    run = CheckRun()
    src = p["source"]
    if p["every"] == "quarter":
        units = [lab for lab, _ in quarters(ev.period)]
        present = sorted((r["ID"].split("-", 1)[1], r["ID"]) for r in ev.rows(src) if r.get("ID", "").startswith(p["prefix"] + "-"))
    else:
        units = iso_weeks(ev.period)
        present = sorted(("{}-W{:02d}".format(*parse_ts(r[p["date"]]).date().isocalendar()[:2]), ev.rid(src, r))
                         for r in ev.rows(src, p.get("where")))
    have = {lab for lab, _ in present}
    for unit in units:
        if unit in have:
            run.ok(step, unit)
        else:
            run.fail(step, unit, f"No {src} occurrence for {unit}.", [(src, r) for r in nearest(present, unit)])
    return run


@check("set_mismatch")
def set_mismatch(ev: Evidence, step: str, p: dict) -> CheckRun:
    """Every left item that existed at each review's date is listed in that review."""
    run = CheckRun()
    left = ev.rows(p["left"])
    for review in ev.rows(p["right"]):
        if not review.get("ID", "").startswith(p["prefix"] + "-"):
            continue
        as_of = date.fromisoformat(review[p["as_of"]])
        for row in left:
            k = row[p["left_key"]]
            if parse_ts(row[p["left_created"]]).date() > as_of:
                continue
            rid = f"{k}@{review['ID']}"
            if k in review["text"]:
                run.ok(step, rid)
            else:
                run.fail(step, rid, f"{k} existed on {as_of} but is not in {review['ID']}.",
                         [(p["left"], ev.rid(p["left"], row)), (p["right"], review["ID"])])
    return run


@check("config_assert")
def config_assert(ev: Evidence, step: str, p: dict) -> CheckRun:
    """Every group is covered by an ACTIVE rule (in an ACTIVE policy) with `require` true."""
    run = CheckRun()
    covered: dict[str, str] = {}
    for pol in ev.data[p["policy"]]["policies"]:
        if pol.get("status") != "ACTIVE":
            continue
        for rule in pol.get("rules", []):
            if rule.get("status") == "ACTIVE" and rule.get(p["require"]) is True:
                for g in rule.get("groups_included", []):
                    covered.setdefault(g, rule["id"])
    for g in ev.rows(p["groups"]):
        gid = ev.rid(p["groups"], g)
        if gid in covered:
            run.ok(step, gid, rule=covered[gid])
        else:
            run.fail(step, gid, f"Group {g['name']} is not covered by an active MFA rule.", [(p["groups"], gid)])
    return run


@check("author_ne_approver")
def author_ne_approver(ev: Evidence, step: str, p: dict) -> CheckRun:
    run = CheckRun()
    for row in ev.rows(p["source"]):
        rid = ev.rid(p["source"], row)
        others = {a for a in row[p["approvers"]].split(";") if a} - {row[p["author"]]}
        if others:
            run.ok(step, rid)
        else:
            run.fail(step, rid, f"Merged with no approver other than the author ({row[p['author']]}).", [(p["source"], rid)])
    return run


@check("unticketed_deploys")
def unticketed_deploys(ev: Evidence, step: str, p: dict) -> CheckRun:
    run = CheckRun()
    keys = {ev.rid(p["tickets"], t) for t in ev.rows(p["tickets"])}
    for row in ev.rows(p["source"], p.get("where")):
        rid = ev.rid(p["source"], row)
        if row[p["link"]] and row[p["link"]] in keys:
            run.ok(step, rid)
        else:
            run.fail(step, rid, "Emergency deploy has no linked change ticket.", [(p["source"], rid)])
    return run


@check("sla_days")
def sla_days(ev: Evidence, step: str, p: dict) -> CheckRun:
    """Days from start to end within `days` (calendar dates, or business days); a missing end fails."""
    run = CheckRun()
    join = p.get("join")
    joined = {r[join["key"]]: r for r in ev.rows(join["source"])} if join else {}
    for row in ev.rows(p["source"], p.get("where")):
        rid = ev.rid(p["source"], row)
        cites = [(p["source"], rid)]
        end_row = row
        if join:
            end_row = joined.get(row[join["link_field"]])
            if end_row is None:
                continue                            # no ticket: the ticketed step owns it
            cites.append((join["source"], ev.rid(join["source"], end_row)))
        start = parse_ts(row[p["start"]]).date()
        if not end_row.get(p["end"]):
            run.fail(step, rid, f"No {p['end']} recorded.", cites)
            continue
        end = parse_ts(end_row[p["end"]]).date()
        n = business_days_between(start, end) if p.get("business") else (end - start).days
        unit = "business days" if p.get("business") else "days"
        if n <= p["days"]:
            run.ok(step, rid, days=n)
        else:
            run.fail(step, rid, f"{n} {unit} (limit {p['days']}).", cites, days=n)
    return run


@check("required_link")
def required_link(ev: Evidence, step: str, p: dict) -> CheckRun:
    run = CheckRun()
    docs = {d["ID"] for d in ev.rows(p["target"]) if d.get("ID")}
    for row in ev.rows(p["source"], p.get("where")):
        rid = ev.rid(p["source"], row)
        if row[p["link"]] in docs:
            run.ok(step, rid)
        else:
            run.fail(step, rid, f"No linked {p['target']} document.", [(p["source"], rid)])
    return run


@check("days_after_event")
def days_after_event(ev: Evidence, step: str, p: dict) -> CheckRun:
    """Calendar days from each person's event date to their first completion of `course`."""
    run = CheckRun()
    done: dict[str, dict] = {}
    for r in sorted(ev.rows(p["done_source"], {"course": p["course"]}), key=lambda r: r[p["done"]]):
        done.setdefault(r["employee_id"], r)
    for person in ev.rows(p["people"], p.get("where")):
        rid = ev.rid(p["people"], person)
        start = local_date(person[p["event"]], person.get("timezone"))
        c = done.get(rid)
        if c is None:
            run.fail(step, rid, f"No completion of {p['course']}.", [(p["people"], rid)])
            continue
        n = (date.fromisoformat(c[p["done"]]) - start).days
        if n <= p["days"]:
            run.ok(step, rid, days=n)
        else:
            run.fail(step, rid, f"Completed {n} days after the event (limit {p['days']}).",
                     [(p["people"], rid), (p["done_source"], ev.rid(p["done_source"], c))], days=n)
    return run


@check("date_in_period")
def date_in_period(ev: Evidence, step: str, p: dict) -> CheckRun:
    run = CheckRun()
    for row in ev.rows(p["source"], p.get("where")):
        rid = ev.rid(p["source"], row)
        d = local_date(row[p["date"]]) if row.get(p["date"]) else None
        if d and ev.period[0] <= d <= ev.period[1]:
            run.ok(step, rid)
        else:
            run.fail(step, rid, f"{p['date']} {d} is outside the period.", [(p["source"], rid)])
    return run


# ---------- per control ----------

@dataclass
class ControlChecks:
    results: list[CheckResult]
    candidates: list[Candidate]
    notes: list[str]
    tested: dict[str, int]                         # step id → items tested


def run_control_checks(spec: ControlSpec, ev: Evidence, only: set[str] | None = None) -> ControlChecks:
    results, candidates, notes, tested = [], [], [], {}
    for step in spec.test_recipe:
        if step.check is None or (only is not None and step.id not in only):
            continue
        if step.check not in CHECKS:
            raise KeyError(f"control {spec.control_id}: step {step.id} names unknown check {step.check!r}")
        run = CHECKS[step.check](ev, step.id, step.params)
        results += run.results
        notes += run.notes
        tested[step.id] = len(run.results)
        for r in run.results:
            if r.passed:
                continue
            candidates.append(Candidate(
                candidate_id=f"{spec.control_id}-{step.id}-{r.record_id}", control_id=spec.control_id,
                test_step=step.id, record_id=r.record_id or "", gap_type=step.gap_type, detail=r.detail["reason"],
                citations=[Citation(**c) for c in r.detail["citations"]]))
    return ControlChecks(results, candidates, notes, tested)
