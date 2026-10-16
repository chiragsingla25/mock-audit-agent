"""Load a control's evidence files and answer record-id lookups (used by checks and citations)."""

from __future__ import annotations

import csv
import json
import re
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from mockaudit.schemas import ControlSpec

ARTIFACT_FIELD = re.compile(r"^([A-Z][A-Za-z ]+): (.*)$", re.MULTILINE)


def parse_artifact(path: Path) -> dict:
    text = path.read_text()
    fields = {k: v.strip() for k, v in ARTIFACT_FIELD.findall(text)}
    return {**fields, "text": text, "file": path.name}


def parse_ts(value: str, tz: str | None = None) -> datetime:
    """'2026-03-01T10:00:00Z' (UTC), '2026-03-01 09:00' (local, tz) or '2026-03-01' (date at 00:00)."""
    if value.endswith("Z"):
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    fmt = "%Y-%m-%d %H:%M" if " " in value else "%Y-%m-%d"
    return datetime.strptime(value, fmt).replace(tzinfo=ZoneInfo(tz) if tz else UTC)


def local_date(value: str, tz: str | None = None) -> date:
    """The calendar date as recorded (local dates stay local)."""
    return parse_ts(value, tz).date()


def matches(row: dict, where: dict | None, period: tuple[date, date]) -> bool:
    for k, v in (where or {}).items():
        if k == "terminated_in_period":
            t = row.get("termination_local")
            ok = (bool(t) and period[0] <= local_date(t, row.get("timezone")) <= period[1]) == bool(v)
        elif k == "hired_in_period":
            ok = (period[0] <= local_date(row["hire_local"], row.get("timezone")) <= period[1]) == bool(v)
        elif k == "employed_throughout":
            start, end = (date.fromisoformat(str(x)) for x in v)
            t = row.get("termination_local")
            ok = local_date(row["hire_local"], row.get("timezone")) <= start and (
                not t or local_date(t, row.get("timezone")) >= end)
        elif isinstance(v, list):
            ok = row.get(k) in v
        else:
            ok = str(row.get(k)) == str(v)
        if not ok:
            return False
    return True


class Evidence:
    """A control's sources by name: csv → list of rows, artifact → list of parsed docs, json → dict, policy → text."""

    def __init__(self, data: dict[str, Any], id_fields: dict[str, str | None], period: tuple[date, date]):
        self.data, self.id_fields, self.period = data, id_fields, period

    @classmethod
    def load(cls, spec: ControlSpec, data_dir: Path) -> Evidence:
        data, ids = {}, {}
        for src in spec.evidence:
            path = Path(data_dir) / src.path
            if src.role == "policy":
                data[src.name] = path.read_text()
            elif path.is_dir():
                data[src.name] = [parse_artifact(p) for p in sorted(path.glob("*.md"))]
            elif path.suffix == ".md":
                data[src.name] = [parse_artifact(path)]
            elif path.suffix == ".json":
                data[src.name] = json.loads(path.read_text())
            else:
                with open(path, newline="") as f:
                    data[src.name] = list(csv.DictReader(f))
            ids[src.name] = src.record_id_field
        return cls(data, ids, spec.period)

    def rows(self, name: str, where: dict | None = None) -> list[dict]:
        return [r for r in self.data[name] if matches(r, where, self.period)]

    def rid(self, name: str, row: dict) -> str:
        return str(row[self.id_fields[name]])

    def index(self) -> set[tuple[str, str]]:
        """Every (source, record_id) that a citation may point at."""
        out = set()
        for name, field in self.id_fields.items():
            value = self.data[name]
            if field is None or isinstance(value, str):
                continue
            if isinstance(value, list):
                out |= {(name, str(r[field])) for r in value if r.get(field)}
            else:
                out |= {(name, i) for i in _json_ids(value, field)}
        return out

    def get(self, name: str, record_id: str) -> Any:
        value, field = self.data[name], self.id_fields.get(name)
        if isinstance(value, list) and field:
            return next((r for r in value if str(r.get(field)) == record_id), None)
        return None


def _json_ids(obj: Any, field: str) -> list[str]:
    if isinstance(obj, dict):
        return ([str(obj[field])] if field in obj else []) + [i for v in obj.values() for i in _json_ids(v, field)]
    if isinstance(obj, list):
        return [i for v in obj for i in _json_ids(v, field)]
    return []
