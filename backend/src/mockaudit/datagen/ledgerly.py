"""Seeded Ledgerly generator: exports, artifacts, policies, owner answers and the answer key.

Spec Phase 1. Everything is derived from (variant, seed) through per-domain random streams, and no
wall-clock time is read, so the same inputs give byte-identical files.
"""

from __future__ import annotations

import csv
import io
import json
import random
import shutil
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from mockaudit.datagen.policies import POLICIES
from mockaudit.schemas import PERIOD
from mockaudit.severity import severity
from mockaudit.specs import load_controls

SYD = ZoneInfo("Australia/Sydney")   # HR and LMS export in local time
P0, P1 = PERIOD
CONTROLS_YAML = Path(__file__).with_name("controls.yaml")
ALL_GAPS = [f"G{i}" for i in range(1, 11)]
JUDGMENT_GAPS = {"G3", "G10"}
VARIANT_SEEDS = {"base": 7, "a": 11, "b": 23}
GAPS_PER_VARIANT = 7
QUARTERS = [("2025Q4", date(2025, 12, 31)), ("2026Q1", date(2026, 3, 31)),
            ("2026Q2", date(2026, 6, 30)), ("2026Q3", date(2026, 9, 30))]

FIRST = ["Ava", "Liam", "Noah", "Mia", "Ethan", "Isla", "Leo", "Zoe", "Jack", "Ruby", "Oscar", "Chloe",
         "Henry", "Grace", "Lucas", "Ella", "Max", "Lily", "Sam", "Amelia", "James", "Olivia", "William",
         "Charlotte", "Thomas", "Sophie", "Harper", "Lachlan", "Matilda", "Archie", "Evie", "Hugo", "Ivy",
         "Finn", "Nina", "Ravi", "Priya", "Arjun", "Mei", "Kenji"]
LAST = ["Chen", "O'Brien", "Patel", "Rossi", "Kim", "Nguyen", "Martin", "Walker", "Singh", "Taylor", "Lee",
        "Brown", "Wu", "Hall", "Green", "Scott", "Young", "King", "Davis", "Smith", "Jones", "Williams",
        "Wilson", "Anderson", "Thompson", "White", "Harris", "Clarke", "Kelly", "Murphy", "Ryan", "Tran",
        "Khan", "Sato", "Ali", "Costa", "Novak", "Fischer", "Silva", "Moreau"]
DEPTS = {"Engineering": ["Software Engineer", "Senior Software Engineer", "Site Reliability Engineer"],
         "Product": ["Product Manager", "Product Designer"], "Sales": ["Account Executive", "SDR"],
         "Customer Success": ["Customer Success Manager", "Support Engineer"],
         "Finance": ["Accountant", "Financial Analyst"], "People": ["People Partner", "Recruiter"],
         "Security": ["Security Engineer"]}
DEPT_WEIGHTS = {"Engineering": 40, "Product": 10, "Sales": 18, "Customer Success": 16, "Finance": 6,
                "People": 5, "Security": 5}
OWNERS = {"it": "Dana Whitfield", "eng": "Marcus Bell", "sec": "Anika Rao", "cto": "Jonah Price",
          "platform": "Elena Petrov", "people": "Grace Okafor"}


# ---------- small helpers ----------

def utc_s(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def loc_s(dt: datetime) -> str:
    return dt.astimezone(SYD).strftime("%Y-%m-%d %H:%M")


def at_local(d: date, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(d, time(hour, minute), tzinfo=SYD)


def at_utc(d: date, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(d, time(hour, minute), tzinfo=UTC)


def add_business_days(d: date, n: int) -> date:
    while n > 0:
        d += timedelta(days=1)
        if d.weekday() < 5:
            n -= 1
    return d


def rand_date(rng: random.Random, start: date, end: date) -> date:
    return start + timedelta(days=rng.randint(0, (end - start).days))


def csv_text(fields: list[str], rows: list[dict]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in fields})
    return buf.getvalue()


def yaml_text(obj) -> str:
    return yaml.safe_dump(obj, sort_keys=False, allow_unicode=True, width=110)


# ---------- generator ----------

class Ledgerly:
    def __init__(self, variant: str, seed: int):
        self.variant, self.seed = variant, seed
        if variant == "base":
            self.planted = list(ALL_GAPS)
        else:
            picked = random.Random(f"{seed}:gaps").sample(ALL_GAPS, GAPS_PER_VARIANT)
            self.planted = [g for g in ALL_GAPS if g in picked]
        self.controls = {c.control_id: c for c in load_controls(CONTROLS_YAML)}
        self.files: dict[str, str] = {}
        self.gaps: list[dict] = []
        self.traps: list[dict] = []
        self.noise: list[dict] = []
        self.answers: list[dict] = []
        self.jira: list[dict] = []

    def rng(self, domain: str) -> random.Random:
        return random.Random(f"{self.seed}:{domain}")

    def on(self, gid: str) -> bool:
        return gid in self.planted

    def gap(self, gid, control_id, test_step, gap_type, record_ids, exceptions, tested, description, **extra):
        c = self.controls[control_id]
        sev, rule = severity(gap_type, exceptions, tested, c.risk, c.periodic)
        self.gaps.append({"id": gid, "control_id": control_id, "test_step": test_step, "gap_type": gap_type,
                          "tag": "judgment" if gid in JUDGMENT_GAPS else "code", "record_ids": record_ids,
                          "exceptions": exceptions, "tested": tested, "control_risk": c.risk,
                          "severity": sev, "severity_rule": rule, "description": description, **extra})

    def trap(self, tid, control_id, test_step, record_ids, explanation):
        self.traps.append({"id": tid, "control_id": control_id, "test_step": test_step,
                           "record_ids": record_ids, "explanation": explanation})

    def note_noise(self, control_id, kind, record_ids, description):
        self.noise.append({"control_id": control_id, "kind": kind, "record_ids": record_ids,
                           "description": description})

    def answer(self, control_id, record_ids, text):
        self.answers.append({"control_id": control_id, "record_ids": record_ids, "answer": text})

    # ----- people -----

    def build_people(self):
        rng = self.rng("people")
        names = [(f, la) for f in FIRST for la in LAST]
        rng.shuffle(names)
        depts = [d for d, w in DEPT_WEIGHTS.items() for _ in range(w)]
        hires = sorted(rand_date(rng, date(2019, 1, 7), date(2025, 9, 19)) for _ in range(120))
        new = sorted(rand_date(rng, date(2025, 10, 6), date(2026, 8, 14)) for _ in range(29))
        new = sorted(new + [date(2025, 12, 15)])           # handover §11 edge: Dec 15 hire
        self.people = []
        for i, d in enumerate(hires + new):
            first, last = names[i]
            dept = rng.choice(depts)
            self.people.append({
                "employee_id": f"E{1001 + i}", "first": first, "last": last,
                "email": f"{first}.{last}".lower().replace("'", "") + "@ledgerly.io",
                "department": dept, "title": rng.choice(DEPTS[dept]), "worker_type": "employee",
                "hire": at_local(d, 9), "term": None, "termination_reason": "", "prior_employee_id": "",
                "okta": True, "new_hire": d >= P0,
            })
        self.existing = [p for p in self.people if not p["new_hire"]]
        self.new_hires = [p for p in self.people if p["new_hire"]]
        self.engineers = [p for p in self.existing if p["department"] == "Engineering"]
        ids = self.rng("okta-ids")
        for p in self.people:
            p["user_id"] = f"00u{ids.getrandbits(40):010x}"

    # ----- C2: terminations and Okta -----

    def build_c2(self):
        rng = self.rng("c2")
        events = []                                   # (dt, dict) before ids are assigned

        def ev(dt, p, etype, detail=""):
            e = {"dt": dt, "published_utc": utc_s(dt), "event_type": etype, "target_login": p["email"],
                 "target_user_id": p["user_id"], "actor": "okta-workflows" if "lifecycle" in etype else p["email"],
                 "detail": detail}
            events.append(e)
            return e

        leavers = sorted(rng.sample(self.existing[:-10], 19), key=lambda p: p["employee_id"])
        n = len(leavers)
        for i, p in enumerate(leavers):
            d = P0 + timedelta(days=int((i + 0.5) * 340 / n) + rng.randint(-3, 3))
            p["term"] = at_local(d, rng.choice([9, 12, 15, 16, 17, 17, 18]), rng.choice([0, 15, 30, 45]))
            p["termination_reason"] = rng.choice(["Resignation", "Resignation", "Involuntary", "End of fixed term"])
        order = list(range(n))
        rng.shuffle(order)
        k_late = 2 if self.variant == "base" else rng.choice([1, 2, 3])
        trap_i = next(i for i in order if leavers[i]["term"].date() <= date(2026, 6, 30))
        rest = [i for i in order if i != trap_i]
        late_i, rest = rest[:k_late], rest[k_late:]
        g2_i, sd_i, tz_i = rest[0], rest[1], rest[2:4]

        removal = {}
        for i, p in enumerate(leavers):
            t = p["term"]
            if i == trap_i:
                continue
            if i == g2_i and self.on("G2"):
                ev(t + timedelta(days=3, hours=2), p, "user.session.start")
                continue
            if i in late_i and self.on("G1"):
                if self.variant == "base" and i == late_i[0]:      # handover §11 edge: Fri 18:00 → Mon 09:00
                    fri = t.date() + timedelta(days=(4 - t.date().weekday()) % 7)
                    while at_local(fri, 18).utcoffset() != at_local(fri + timedelta(days=3), 9).utcoffset():
                        fri += timedelta(days=7)                    # skip a DST-change weekend: keep 63 h
                    p["term"] = t = at_local(fri, 18)
                    when = at_local(fri + timedelta(days=3), 9)
                elif self.variant == "base":
                    when = t + timedelta(days=9, hours=3)
                else:
                    when = t + timedelta(hours=rng.randint(30, 300))
            elif i in tz_i:
                p["term"] = t = at_local(t.date(), 8)              # before 10:00 local = previous UTC day
                when = t + timedelta(minutes=rng.randint(20, 90))
            elif i == sd_i:
                p["term"] = t = at_local(t.date(), 13)             # suspended same day, local and UTC
                when = t + timedelta(minutes=rng.randint(60, 180))
            else:
                when = t + timedelta(hours=rng.uniform(0.5, 23.5))
            removal[i] = ev(when, p, rng.choice(["user.lifecycle.suspend", "user.lifecycle.deactivate"]))
            if i == sd_i:
                removal[i]["event_type"] = "user.lifecycle.suspend"
                p["sd_delete"] = ev(when + timedelta(days=6), p, "user.lifecycle.delete")

        # trap T1: employee converted to contractor; account kept until the contract ended
        tp = leavers[trap_i]
        tp["termination_reason"] = "Conversion to contractor"
        contractor = dict(tp, employee_id=f"C{2001 + int(tp['employee_id'][1:]) % 97}", worker_type="contractor",
                          hire=tp["term"], term=tp["term"] + timedelta(days=rng.randint(55, 80)),
                          termination_reason="Contract end", prior_employee_id=tp["employee_id"],
                          new_hire=False, okta=False)
        self.people.append(contractor)
        upd = ev(tp["term"] + timedelta(hours=1), tp, "user.account.update_profile",
                 f"employmentType: Employee -> Contractor; employeeNumber: {tp['employee_id']} -> {contractor['employee_id']}")
        deact = ev(contractor["term"] + timedelta(hours=2), tp, "user.lifecycle.deactivate")

        # contractor never provisioned in Okta (note only, handover §11)
        ghost_first, ghost_last = "Dana", "Ford"
        ghost = {"employee_id": "X3001", "first": ghost_first, "last": ghost_last,
                 "email": "dana.ford@contractor.example", "department": "Finance", "title": "Contract Accountant",
                 "worker_type": "contractor", "hire": at_local(date(2025, 11, 3), 9),
                 "term": at_local(date(2026, 3, 20), 17), "termination_reason": "Contract end",
                 "prior_employee_id": "", "okta": False, "new_hire": False, "user_id": ""}
        self.people.append(ghost)

        # background noise: creates for new hires, sign-ins
        for p in self.new_hires:
            ev(p["hire"] - timedelta(days=2), p, "user.lifecycle.create")
        for _ in range(240):
            p = rng.choice(self.existing)
            d = rand_date(rng, P0, P1)
            if p["term"] and d >= p["term"].date():
                continue
            ev(at_utc(d, rng.randint(0, 23), rng.randint(0, 59)), p, "user.session.start")

        events.sort(key=lambda e: (e["dt"], e["target_login"], e["event_type"]))
        for j, e in enumerate(events, 1):
            e["event_id"] = f"OK-{j:06d}"
        self.okta_events = events

        tested = sum(1 for i in range(n) if i in removal or i == trap_i)
        if self.on("G1"):
            ids = [x for i in late_i for x in (leavers[i]["employee_id"], removal[i]["event_id"])]
            hours = [round((removal[i]["dt"].astimezone(UTC) - leavers[i]["term"].astimezone(UTC)).total_seconds() / 3600, 1)
                     for i in late_i]
            self.gap("G1", "C2", "timeliness", "operating", ids, len(late_i), tested,
                     f"{len(late_i)} of {tested} terminated users were suspended/deactivated late ({hours} hours).",
                     hours=hours)
            for i in late_i:
                self.answer("C2", [leavers[i]["employee_id"]],
                            f"The offboarding ticket for {leavers[i]['employee_id']} was actioned late; there is no approved exception.")
        if self.on("G2"):
            p = leavers[g2_i]
            self.gap("G2", "C2", "completeness", "population_completeness", [p["employee_id"], p["user_id"]], 1,
                     sum(1 for q in leavers if q["okta"]),
                     f"{p['employee_id']} was terminated but their Okta account was never suspended or deactivated.")
            self.answer("C2", [p["employee_id"]], f"I can't find a deactivation for {p['employee_id']}. It looks like it was missed.")
        self.trap("T1", "C2", "timeliness", [tp["employee_id"], contractor["employee_id"], deact["event_id"]],
                  "Employee converted to contractor the same day (policy 4.4); access correctly continued until the contract ended.")
        self.answer("C2", [tp["employee_id"], contractor["employee_id"]],
                    f"{tp['employee_id']} converted to contractor {contractor['employee_id']} on the same day under policy 4.4, "
                    f"so the account stayed active. It was deactivated when the contract ended.")
        self.note_noise("C2", "suspend_then_delete", [leavers[sd_i]["employee_id"], p_ev(leavers[sd_i])],
                        "Suspended the same day and deleted 6 days later: suspension removed access (not a gap).")
        self.note_noise("C2", "time_zone", [leavers[i]["employee_id"] for i in tz_i],
                        "Morning AEST terminations revoked on the previous UTC calendar day; compare in UTC (not a gap).")
        self.note_noise("C2", "never_provisioned", ["X3001"], "Contractor never had an Okta account; note only.")
        self.note_noise("C2", "name_format", [], "HR names are 'Last, First'; Okta display names are 'First Last'.")
        if self.variant == "base" and self.on("G1"):
            self.note_noise("C2", "edge_weekend", [leavers[late_i[0]]["employee_id"]],
                            "Terminated Friday 18:00, suspended Monday 09:00 (63 clock hours): an exception (part of G1).")
        _ = upd

    # ----- C1: access requests -----

    def build_c1(self):
        rng = self.rng("c1")
        apps = [("GitHub", "Developer"), ("AWS", "ReadOnly"), ("Jira", "User"), ("Salesforce", "Sales User"),
                ("Datadog", "Viewer"), ("NetSuite", "AP Clerk"), ("Figma", "Editor")]
        approvers = [OWNERS["eng"], OWNERS["platform"], OWNERS["it"]]
        rows = []
        for _ in range(64):
            p = rng.choice(self.people[:150])
            d = rand_date(rng, max(P0, p["hire"].date()), P1 - timedelta(days=5))
            if p["term"] and d >= p["term"].date():
                continue
            req = at_utc(d, rng.randint(0, 6), rng.randint(0, 59))
            app, role = rng.choice(apps)
            appr = req + timedelta(hours=rng.uniform(0.3, 30))
            rows.append({"user_employee_id": p["employee_id"], "user_email": p["email"], "application": app,
                         "role": role, "requested_utc": req, "approver": rng.choice(approvers),
                         "approved_utc": appr, "granted_utc": appr + timedelta(hours=rng.uniform(0.05, 20)),
                         "granted_by": "it-ops"})
        hire = rng.choice([p for p in self.new_hires if p["hire"].date() < date(2026, 8, 1)])
        g = hire["hire"]
        trap_row = {"user_employee_id": hire["employee_id"], "user_email": hire["email"], "application": "Okta",
                    "role": "Employee-Base", "requested_utc": g + timedelta(days=2), "approver": OWNERS["people"],
                    "approved_utc": g + timedelta(days=2, hours=1), "granted_utc": g, "granted_by": "hr-provisioning"}
        rows.append(trap_row)
        rows.sort(key=lambda r: (r["requested_utc"], r["user_employee_id"]))
        for j, r in enumerate(rows, 1):
            r["request_id"] = f"AR-{j:04d}"
            for k in ("requested_utc", "approved_utc", "granted_utc"):
                r[k] = utc_s(r[k])
        self.files["exports/access_requests.csv"] = csv_text(
            ["request_id", "user_employee_id", "user_email", "application", "role", "requested_utc", "approver",
             "approved_utc", "granted_utc", "granted_by"], rows)
        self.trap("T2", "C1", "approval", [trap_row["request_id"]],
                  "Birthright role Employee-Base is provisioned from the HR hire record and pre-approved (policy 4.2); "
                  "the request record is for tracking only.")
        self.answer("C1", [trap_row["request_id"], hire["employee_id"]],
                    f"{trap_row['request_id']} is the tracking record for {hire['employee_id']}'s birthright Employee-Base "
                    "role. It's provisioned automatically from the HR hire record and pre-approved under policy 4.2.")

    # ----- C3 / C5: quarterly reviews -----

    def build_reviews(self):
        rng = self.rng("reviews")
        other_q = [q for q, _ in QUARTERS if q != "2026Q3"]          # variants: not base's record
        g3_q = "2026Q3" if self.variant == "base" else rng.choice(other_q)
        g4_q = "2026Q3" if self.variant == "base" else rng.choice(other_q)
        # AWS admins
        admins = []
        names = ["platform-admin", "break-glass", "terraform-ci", "sre-oncall", "elena.petrov", "marcus.bell",
                 "data-migration", "security-audit"]
        for j, nm in enumerate(names):
            created = (at_utc(date(2023, 3, 1) + timedelta(days=97 * j), 3) if j < 6
                       else at_utc(date(2026, 1, 12) + timedelta(days=60 * (j - 6)), 4))
            admins.append({"principal_id": f"AIDA{rng.getrandbits(48):012X}", "name": nm,
                           "arn": f"arn:aws:iam::418295730012:{'role' if '-' in nm and '.' not in nm else 'user'}/{nm}",
                           "policy": "AdministratorAccess", "created_utc": created})
        self.files["exports/aws_iam_admins.csv"] = csv_text(
            ["principal_id", "name", "arn", "policy", "created_utc"],
            [dict(a, created_utc=utc_s(a["created_utc"])) for a in admins])

        for q, qend in QUARTERS:
            performed = add_business_days(qend, rng.randint(1, 5))
            signed = add_business_days(performed, rng.randint(0, 3))
            active = [p for p in self.people if p["okta"] and p["hire"].date() <= qend
                      and (not p["term"] or p["term"].date() > qend)]
            sample = rng.sample(active, 6)
            rows = "\n".join(f"| {p['first']} {p['last']} | {p['department']} | Keep | Role matches job |" for p in sample)
            unsigned = q == g3_q and self.on("G3")
            sign = ("Reviewer: Dana Whitfield, IT Operations Manager\nSigned: (not signed)" if unsigned
                    else f"Reviewer: Dana Whitfield, IT Operations Manager\nSigned: {signed.isoformat()}")
            self.files[f"artifacts/access_reviews/UAR-{q}.md"] = (
                f"# User Access Review {q}\nID: UAR-{q}\nSystem: Okta (all active users)\n"
                f"Quarter end: {qend.isoformat()}\nReview performed: {performed.isoformat()}\n"
                f"Population reviewed: {len(active)} active users\n\n"
                f"| User | Department | Decision | Note |\n|---|---|---|---|\n{rows}\n\n{sign}\n")
            if unsigned:
                self.gap("G3", "C3", "signoff", "missing_evidence", [f"UAR-{q}"], 1, len(QUARTERS),
                         f"The {q} user access review has no reviewer sign-off.")
                self.answer("C3", [f"UAR-{q}"], f"Dana ran the {q} review but never signed it off; we don't have a signed copy.")

            as_of = at_utc(performed, 0)
            listed = [a for a in admins if a["created_utc"] <= as_of]
            omitted = None
            if q == g4_q and self.on("G4"):
                omitted = rng.choice(listed)
                listed = [a for a in listed if a is not omitted]
            rows = "\n".join(f"| {a['principal_id']} | {a['name']} | Keep |" for a in listed)
            psigned = add_business_days(performed, rng.randint(0, 2))
            self.files[f"artifacts/access_reviews/PAR-{q}.md"] = (
                f"# Privileged Access Review {q}\nID: PAR-{q}\nSystem: AWS IAM principals with AdministratorAccess\n"
                f"Quarter end: {qend.isoformat()}\nReview date: {performed.isoformat()}\n\n"
                f"| Principal | Name | Decision |\n|---|---|---|\n{rows}\n\n"
                f"Reviewer: Elena Petrov, Head of Platform\nSigned: {psigned.isoformat()}\n")
            if omitted is not None:
                self.gap("G4", "C5", "completeness", "population_completeness", [omitted["principal_id"], f"PAR-{q}"],
                         1, len(listed) + 1,
                         f"AWS admin {omitted['name']} existed at the {q} review but is not on the reviewed list.")
                self.answer("C5", [omitted["principal_id"]],
                            f"{omitted['name']} should have been on the {q} list. The export we reviewed from was filtered wrongly.")
            if q == "2026Q3":
                if not unsigned:
                    self.note_noise("C3", "signoff_after_period", [f"UAR-{q}"],
                                    "Q3-26 user access review signed in October 2026, within 10 business days (pass).")
                self.note_noise("C5", "signoff_after_period", [f"PAR-{q}"],
                                "Q3-26 privileged access review signed in October 2026, within 10 business days (pass).")
        self.admins = admins

    # ----- C4: MFA config -----

    def build_c4(self):
        groups = ["Everyone"] + sorted(DEPTS) + ["Contractors", "Admins"]
        rows = [{"group_id": f"00g{i:04d}", "name": g} for i, g in enumerate(groups, 1)]
        self.files["exports/okta_groups.csv"] = csv_text(["group_id", "name"], rows)
        policy = {"policies": [{"id": "pol-signon-01", "name": "Require MFA for all users", "status": "ACTIVE",
                                "rules": [{"id": "rule-mfa-01", "name": "All groups: password + second factor",
                                           "status": "ACTIVE", "groups_included": [r["group_id"] for r in rows],
                                           "factor_required": True,
                                           "factor_types": ["okta_verify_push", "webauthn"]}]}]}
        self.files["exports/okta_mfa_policy.json"] = json.dumps(policy, indent=2) + "\n"

    # ----- C6 / C7: changes and deploys -----

    def build_changes(self):
        rng = self.rng("c6")
        repos = ["ledgerly-api", "ledgerly-web", "billing-worker", "infra"]
        prs = []
        for j in range(320):
            author = rng.choice(self.engineers)
            others = [e for e in self.engineers if e is not author]
            merged = at_utc(rand_date(rng, P0, P1 - timedelta(days=1)), rng.randint(0, 23), rng.randint(0, 59))
            approvers = [x["email"].split("@")[0] for x in rng.sample(others, rng.choice([1, 1, 2]))]
            prs.append({"pr_id": f"PR-{1000 + j}", "repo": rng.choice(repos), "title": f"Change {1000 + j}",
                        "author": author["email"].split("@")[0], "approvers": approvers, "base_branch": "main",
                        "merged_utc": merged})
        prs.sort(key=lambda r: (r["merged_utc"], r["pr_id"]))
        k = 4 if self.variant == "base" else rng.randint(2, 5)
        self_appr = sorted(rng.sample(range(len(prs)), k)) if self.on("G5") else []
        for i in self_appr:
            prs[i]["approvers"] = [prs[i]["author"]]
        self.files["exports/github_pull_requests.csv"] = csv_text(
            ["pr_id", "repo", "title", "author", "approvers", "base_branch", "merged_utc"],
            [dict(r, approvers=";".join(r["approvers"]), merged_utc=utc_s(r["merged_utc"])) for r in prs])
        if self.on("G5"):
            ids = [prs[i]["pr_id"] for i in self_appr]
            self.gap("G5", "C6", "segregation", "segregation_of_duties", ids, k, len(prs),
                     f"{k} PRs were merged with the author as the only approver.")
            self.answer("C6", ids, "Those were merged during a busy release; branch protection allowed admins to self-approve. No exception.")

        rng = self.rng("c7")
        deploys = []
        for _ in range(880):
            pr = rng.choice(prs)
            dt = pr["merged_utc"] + timedelta(minutes=rng.randint(5, 600))
            if dt.date() > P1:
                continue
            deploys.append({"deployed_utc": dt, "service": pr["repo"], "change_type": "standard",
                            "pr_id": pr["pr_id"], "ticket": "", "deployer": "github-actions"})
        n_emerg = 8
        k6 = (2 if self.variant == "base" else rng.randint(1, 3)) if self.on("G6") else 0
        emerg = []
        fri = date(2026, 2, 13)                                        # compliant Friday hotfix (noise)
        for j in range(n_emerg):
            d = fri if j == 0 else rand_date(rng, P0, P1 - timedelta(days=7))
            if j and d.weekday() >= 5:
                d -= timedelta(days=d.weekday() - 4)
            dt = at_utc(d, rng.randint(1, 22), rng.randint(0, 59))
            emerg.append({"deployed_utc": dt, "service": rng.choice(repos), "change_type": "emergency",
                          "pr_id": "", "ticket": "", "deployer": rng.choice(self.engineers)["email"].split("@")[0]})
        unticketed = rng.sample(range(1, n_emerg), k6)
        deploys += emerg
        deploys.sort(key=lambda r: (r["deployed_utc"], r["service"], r["pr_id"]))
        for j, r in enumerate(deploys, 1):
            r["deploy_id"] = f"D-{j:05d}"
        for j, e in enumerate(emerg):
            if j in unticketed:
                continue
            key = f"CHG-{101 + j}"
            e["ticket"] = key
            bd = 2 if j == 0 else rng.randint(0, 2)
            appr_day = add_business_days(e["deployed_utc"].date(), bd) if bd else e["deployed_utc"].date()
            appr = at_utc(appr_day, 23, 0) if bd else e["deployed_utc"] + timedelta(hours=2)
            self.jira.append({"key": key, "issue_type": "Emergency Change", "summary": f"Hotfix {e['service']}",
                              "created_utc": e["deployed_utc"] + timedelta(minutes=20), "resolved_utc": appr,
                              "status": "Done", "resolution": "Approved", "approver": OWNERS["eng"],
                              "approved_utc": appr, "linked_deploy": e["deploy_id"], "linked_doc": ""})
        self.note_noise("C7", "compliant_emergency", [emerg[0]["deploy_id"], emerg[0]["ticket"]],
                        "Friday hotfix approved the following Tuesday: exactly 2 business days (pass).")
        self.files["exports/deploy_log.csv"] = csv_text(
            ["deploy_id", "deployed_utc", "service", "change_type", "pr_id", "ticket", "deployer"],
            [dict(r, deployed_utc=utc_s(r["deployed_utc"])) for r in deploys])
        if self.on("G6"):
            ids = [emerg[j]["deploy_id"] for j in sorted(unticketed)]
            self.gap("G6", "C7", "ticketed", "population_completeness", ids, k6, n_emerg,
                     f"{k6} emergency deploy{'s have' if k6 > 1 else ' has'} no emergency change ticket or retroactive approval.")
            self.answer("C7", ids, "Those hotfixes went out overnight and nobody raised the change ticket afterwards.")

    # ----- C8: scans and vulnerabilities -----

    def build_c8(self):
        rng = self.rng("c8")
        weds = [P0 + timedelta(days=7 * i) for i in range(53)]       # 2025-10-01 is a Wednesday
        gap_start = 44 if self.variant == "base" else rng.randint(8, 46)   # base: Aug 5, 12, 19 2026
        missing = set(range(gap_start, gap_start + 3)) if self.on("G7") else set()
        late_week = rng.choice([i for i in range(2, 50) if abs(i - gap_start) > 4])
        rows = []
        for i, d in enumerate(weds):
            if i in missing:
                continue
            day = d + timedelta(days=3) if i == late_week else d     # Saturday instead of Wednesday
            y, w, _ = d.isocalendar()
            rows.append({"scan_id": f"SCAN-{y}-W{w:02d}", "started_utc": utc_s(at_utc(day, 2, 0)),
                         "scanner": "Nessus", "target": "prod", "status": "completed",
                         "critical": rng.randint(0, 2), "high": rng.randint(0, 9)})
        self.files["exports/scanner_runs.csv"] = csv_text(
            ["scan_id", "started_utc", "scanner", "target", "status", "critical", "high"], rows)
        late_id = next(r["scan_id"] for r in rows if r["started_utc"].startswith((weds[late_week] + timedelta(days=3)).isoformat()))
        self.note_noise("C8", "late_in_week_scan", [late_id], "Scan ran on Saturday instead of Wednesday, same ISO week (pass).")
        if self.on("G7"):
            before = f"SCAN-{weds[gap_start - 1].isocalendar()[0]}-W{weds[gap_start - 1].isocalendar()[1]:02d}"
            after = f"SCAN-{weds[gap_start + 3].isocalendar()[0]}-W{weds[gap_start + 3].isocalendar()[1]:02d}"
            miss_weeks = [f"{weds[i].isocalendar()[0]}-W{weds[i].isocalendar()[1]:02d}" for i in sorted(missing)]
            self.gap("G7", "C8", "weekly_scan", "frequency_gap", [before, after], 3, len(weds),
                     f"No scan results for 3 consecutive weeks ({', '.join(miss_weeks)}).", missing_weeks=miss_weeks)
            self.answer("C8", [before, after], "The scanner licence lapsed for a few weeks and we didn't notice until it renewed.")

        vulns = []

        def vuln(sev, opened, closed, accept=""):
            vulns.append({"severity": sev, "opened_utc": opened, "closed_utc": closed, "risk_acceptance": accept,
                          "cve": f"CVE-2026-{rng.randint(10000, 49999)}", "asset": rng.choice(["api", "web", "db", "worker"])})
            return vulns[-1]

        for _ in range(6):
            o = at_utc(rand_date(rng, P0, P1 - timedelta(days=40)), rng.randint(0, 23))
            vuln("critical", o, o + timedelta(days=rng.randint(3, 28), hours=rng.randint(0, 6)))
        edge = vuln("critical", at_utc(date(2026, 1, 31), 10), at_utc(date(2026, 3, 2), 16))   # exactly 30 days
        g8 = None
        if self.on("G8"):
            days = 47 if self.variant == "base" else rng.randint(35, 60)
            o = at_utc(rand_date(rng, P0, P1 - timedelta(days=days + 5)), 8)
            g8 = vuln("critical", o, o + timedelta(days=days, hours=3))
        risk_key = "RISK-7"
        o = at_utc(rand_date(rng, P0, P1 - timedelta(days=80)), 9)
        t3 = vuln("critical", o, o + timedelta(days=60, hours=1), risk_key)
        self.jira.append({"key": risk_key, "issue_type": "Risk Acceptance",
                          "summary": "Accept risk on legacy PDF renderer until vendor patch (WAF rule compensates)",
                          "created_utc": o + timedelta(days=5), "resolved_utc": o + timedelta(days=6), "status": "Done",
                          "resolution": "Approved", "approver": f"{OWNERS['sec']}; {OWNERS['cto']}",
                          "approved_utc": o + timedelta(days=6), "linked_deploy": "", "linked_doc": "",
                          "expires_utc": o + timedelta(days=90)})
        for _ in range(28):
            o = at_utc(rand_date(rng, P0, P1 - timedelta(days=100)), rng.randint(0, 23))
            vuln(rng.choice(["high", "medium", "medium", "low"]), o, o + timedelta(days=rng.randint(5, 90)))
        vulns.sort(key=lambda v: (v["opened_utc"], v["cve"]))
        for j, v in enumerate(vulns, 1):
            v["vuln_id"] = f"VULN-{j:04d}"
        self.files["exports/vulnerabilities.csv"] = csv_text(
            ["vuln_id", "cve", "severity", "asset", "opened_utc", "closed_utc", "status", "risk_acceptance"],
            [dict(v, opened_utc=utc_s(v["opened_utc"]), closed_utc=utc_s(v["closed_utc"]), status="closed") for v in vulns])
        n_crit = sum(v["severity"] == "critical" for v in vulns)
        self.note_noise("C8", "edge_30_days", [edge["vuln_id"]], "Critical opened 2026-01-31, closed 2026-03-02: exactly 30 days (pass).")
        if g8:
            days = (g8["closed_utc"].date() - g8["opened_utc"].date()).days
            self.gap("G8", "C8", "critical_sla", "sla_breach", [g8["vuln_id"]], 1, n_crit,
                     f"Critical {g8['vuln_id']} was open {days} days (limit 30).", days_open=days)
            self.answer("C8", [g8["vuln_id"]], f"{g8['vuln_id']} slipped through triage; there's no risk acceptance for it.")
        self.trap("T3", "C8", "critical_sla", [t3["vuln_id"], risk_key],
                  "Open 60 days, but covered by approved, unexpired risk acceptance RISK-7 (policy 2.3).")
        self.answer("C8", [t3["vuln_id"], risk_key],
                    f"{t3['vuln_id']} is covered by risk acceptance {risk_key}, signed by Anika and Jonah, with a WAF rule as the compensating control.")

    # ----- C9: incidents -----

    def build_c9(self):
        rng = self.rng("c9")
        dates = sorted(rand_date(rng, P0, P1 - timedelta(days=30)) for _ in range(7))
        trap_j = rng.randrange(7)
        for j, d in enumerate(dates):
            key = f"INC-{21 + j}"
            created = at_utc(d, rng.randint(0, 23), rng.randint(0, 59))
            resolved = created + timedelta(hours=rng.randint(2, 40))
            if j == trap_j:
                self.jira.append({"key": key, "issue_type": "Incident", "summary": "GuardDuty alert: unusual API calls from CI runner",
                                  "created_utc": created, "resolved_utc": resolved, "status": "Done",
                                  "resolution": "Not an incident (false positive)", "approver": "", "approved_utc": None,
                                  "linked_deploy": "", "linked_doc": ""})
                self.trap("T4", "C9", "pir", [key],
                          "Triaged as a false positive and resolved 'Not an incident'; policy 5.2 needs no PIR.")
                self.answer("C9", [key], f"{key} was a false positive: the CI runner's new IP range. Closed after triage; no PIR needed.")
                continue
            doc = f"PIR-{key}"
            self.jira.append({"key": key, "issue_type": "Incident", "summary": rng.choice(
                ["Phishing email clicked by staff member", "Leaked test API key in public repo", "Credential stuffing on login",
                 "Misconfigured S3 bucket policy", "Lost laptop (encrypted)", "Suspicious OAuth app consent"]),
                "created_utc": created, "resolved_utc": resolved, "status": "Done", "resolution": "Resolved",
                "approver": "", "approved_utc": None, "linked_deploy": "", "linked_doc": doc})
            pir_day = add_business_days(resolved.date(), rng.randint(2, 10))
            self.files[f"artifacts/post_incident_reviews/{doc}.md"] = (
                f"# Post-incident review {key}\nID: {doc}\nIncident: {key}\nDate: {pir_day.isoformat()}\n"
                f"Facilitator: Anika Rao, Security Lead\n\n## Summary\nContained within the incident window.\n\n"
                f"## Actions\n- Owner assigned and tracked in Jira.\n")

    # ----- C10: training -----

    def build_c10(self):
        rng = self.rng("c10")
        rows = []
        hires = [p for p in self.new_hires]
        k = 3 if self.variant == "base" else rng.randint(2, 4)
        eligible = [p for p in hires if p["hire"].date() <= date(2026, 7, 15) and p["hire"].date() != date(2025, 12, 15)]
        pick = rng.sample(eligible, k + 1)
        late, edge30 = (pick[:k] if self.on("G9") else []), pick[k]
        late_days = ([31, 44, 58] if self.variant == "base" else sorted(rng.randint(31, 60) for _ in range(k)))
        late_map = {p["employee_id"]: d for p, d in zip(late, late_days)}
        for p in hires:
            hd = p["hire"].date()
            if p["employee_id"] in late_map:
                days = late_map[p["employee_id"]]
            elif p is edge30:
                days = 30
            elif hd == date(2025, 12, 15):
                days = 26                                    # trained Jan 10 (handover §11)
            else:
                days = rng.randint(2, 28)
            rows.append({"employee_id": p["employee_id"], "course": "Security Awareness - New Hire",
                         "completed_local": (hd + timedelta(days=days)).isoformat(), "score": rng.randint(80, 100)})
        campaign = (date(2026, 3, 1), date(2026, 5, 31))
        for p in self.people:
            if p["worker_type"] != "employee" or p["hire"].date() > campaign[0]:
                continue
            if p["term"] and p["term"].date() < campaign[1]:
                continue
            rows.append({"employee_id": p["employee_id"], "course": "Security Awareness - Annual 2026",
                         "completed_local": rand_date(rng, date(2026, 3, 2), date(2026, 5, 29)).isoformat(),
                         "score": rng.randint(75, 100)})
        rows.sort(key=lambda r: (r["completed_local"], r["employee_id"], r["course"]))
        for j, r in enumerate(rows, 1):
            r["completion_id"] = f"LMS-{j:05d}"
        self.files["exports/lms_completions.csv"] = csv_text(
            ["completion_id", "employee_id", "course", "completed_local", "score"], rows)
        by_emp = {(r["employee_id"], r["course"]): r["completion_id"] for r in rows}
        dec15 = next(p for p in hires if p["hire"].date() == date(2025, 12, 15))
        self.note_noise("C10", "edge_cross_year", [dec15["employee_id"]], "Hired 2025-12-15, trained 2026-01-10 (pass).")
        self.note_noise("C10", "edge_30_days", [edge30["employee_id"]], "Trained exactly 30 days after hire (pass).")
        if late:
            ids = [x for p in late for x in (p["employee_id"], by_emp[(p["employee_id"], "Security Awareness - New Hire")])]
            self.gap("G9", "C10", "new_hire", "operating", ids, k, len(hires),
                     f"{k} new hires completed security training after 30 days ({sorted(late_map.values())} days).",
                     days_after_hire=sorted(late_map.values()))
            self.answer("C10", [p["employee_id"] for p in late], "Their managers didn't chase the new-hire course; no exception was approved.")

    # ----- C11 / C12 -----

    def build_c11_c12(self):
        rng = self.rng("c11")
        vendors = ["AWS", "Stripe", "Okta", "GitHub", "Datadog", "Slack", "Google Workspace", "Atlassian", "Figma",
                   "Zendesk", "HubSpot", "Gusto", "DocuSign", "Snyk", "Notion"]
        critical = {"AWS", "Stripe", "Okta", "GitHub", "Datadog"}
        rows = []
        for j, v in enumerate(vendors, 1):
            crit = v in critical
            d = rand_date(rng, P0 + timedelta(days=20), P1 - timedelta(days=20)) if crit else rand_date(rng, date(2024, 6, 1), P1)
            rows.append({"vendor_id": f"V-{j:03d}", "name": v, "criticality": "critical" if crit else "standard",
                         "owner": OWNERS["sec"], "last_risk_review_date": d.isoformat(),
                         "review_doc": f"VRA-{v.replace(' ', '')}-{d.year}"})
        self.files["exports/vendor_register.csv"] = csv_text(
            ["vendor_id", "name", "criticality", "owner", "last_risk_review_date", "review_doc"], rows)

        d = date(2025, 9, 12) if self.on("G10") else rand_date(self.rng("c12"), date(2026, 2, 1), date(2026, 8, 31))
        rid = f"RST-{d.strftime('%Y-%m')}"
        self.files["artifacts/backup_restore_test_report.md"] = (
            f"# Backup Restore Test Report\nID: {rid}\nSystem: ledgerly-prod PostgreSQL (RDS)\n"
            f"Test date: {d.isoformat()}\nBackup restored: automated snapshot from {(d - timedelta(days=1)).isoformat()}\n"
            "Result: restore completed in 42 minutes; row counts reconciled; RTO (4 h) met.\n\n"
            f"Performed by: Elena Petrov, Head of Platform\nSigned: {d.isoformat()}\n")
        if self.on("G10"):
            self.gap("G10", "C12", "restore_test", "evidence_out_of_period", [rid], 1, 1,
                     f"The only restore test report is dated {d.isoformat()}, before the period starts.")
            self.answer("C12", [rid], "That September 2025 test is the latest one. The 2026 test got pushed back and hasn't happened yet.")

    # ----- assembly -----

    def build_hr_okta_files(self):
        hr = []
        for p in self.people:
            hr.append({"employee_id": p["employee_id"], "name": f"{p['last']}, {p['first']}", "email": p["email"],
                       "worker_type": p["worker_type"], "department": p["department"], "title": p["title"],
                       "hire_local": loc_s(p["hire"]), "termination_local": loc_s(p["term"]) if p["term"] else "",
                       "timezone": "Australia/Sydney", "status": "terminated" if p["term"] else "active",
                       "termination_reason": p["termination_reason"], "prior_employee_id": p["prior_employee_id"]})
        hr.sort(key=lambda r: r["employee_id"])
        self.files["exports/hr_roster.csv"] = csv_text(list(hr[0]), hr)
        removed = {e["target_login"]: e["event_type"] for e in self.okta_events
                   if e["event_type"] in ("user.lifecycle.suspend", "user.lifecycle.deactivate", "user.lifecycle.delete")}
        status = {"user.lifecycle.suspend": "SUSPENDED", "user.lifecycle.deactivate": "DEPROVISIONED",
                  "user.lifecycle.delete": "DELETED"}
        users = []
        for p in self.people:
            if not p["okta"]:
                continue
            users.append({"user_id": p["user_id"], "login": p["email"], "display_name": f"{p['first']} {p['last']}",
                          "status": status.get(removed.get(p["email"]), "ACTIVE"),
                          "created_utc": utc_s(p["hire"] - timedelta(days=2)),
                          "groups": ";".join(["Everyone", p["department"]] + (["Admins"] if p["title"] == "Site Reliability Engineer" else []))})
        users.sort(key=lambda r: r["user_id"])
        self.files["exports/okta_users.csv"] = csv_text(list(users[0]), users)
        self.files["exports/okta_system_log.csv"] = csv_text(
            ["event_id", "published_utc", "event_type", "target_login", "target_user_id", "actor", "detail"],
            self.okta_events)
        jira = sorted(self.jira, key=lambda r: r["key"])
        fields = ["key", "issue_type", "summary", "created_utc", "resolved_utc", "status", "resolution", "approver",
                  "approved_utc", "expires_utc", "linked_deploy", "linked_doc"]
        self.files["exports/jira_tickets.csv"] = csv_text(
            fields, [{k: (utc_s(v) if isinstance(v, datetime) else v) for k, v in r.items()} for r in jira])

    def build(self) -> dict[str, str]:
        self.build_people()
        self.build_c2()
        self.build_c1()
        self.build_reviews()
        self.build_c4()
        self.build_changes()
        self.build_c8()
        self.build_c9()
        self.build_c10()
        self.build_c11_c12()
        self.build_hr_okta_files()
        self.files["controls.yaml"] = CONTROLS_YAML.read_text()
        for name, text in POLICIES.items():
            self.files[f"policies/{name}"] = text
        self.files["answers.yaml"] = yaml_text({"owner_answers": self.answers})
        gapped = {g["control_id"] for g in self.gaps}
        self.files["answer_key.yaml"] = yaml_text({
            "dataset": {"variant": self.variant, "seed": self.seed, "period": [P0.isoformat(), P1.isoformat()]},
            "gaps": sorted(self.gaps, key=lambda g: int(g["id"][1:])),
            "not_planted": [g for g in ALL_GAPS if g not in self.planted],
            "traps": self.traps,
            "clean_controls": sorted((c for c in self.controls if c not in gapped), key=lambda c: int(c[1:])),
            "noise": self.noise,
        })
        return self.files


def p_ev(p: dict) -> str:
    return p["sd_delete"]["event_id"] if "sd_delete" in p else ""


def generate(variant: str, out_root: Path, seed: int | None = None) -> Path:
    if variant not in VARIANT_SEEDS:
        raise ValueError(f"unknown variant {variant!r}; choose from {sorted(VARIANT_SEEDS)}")
    seed = VARIANT_SEEDS[variant] if seed is None else seed
    files = Ledgerly(variant, seed).build()
    out = Path(out_root) / variant
    if out.exists():
        shutil.rmtree(out)
    for rel in sorted(files):
        path = out / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(files[rel])
    return out
