"""Load and validate controls.yaml into ControlSpec objects."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from mockaudit.schemas import ControlSpec


class ControlSpecError(ValueError):
    """An invalid controls.yaml entry. The message names the control and the field."""


def load_controls(path: str | Path) -> list[ControlSpec]:
    try:
        raw = yaml.safe_load(Path(path).read_text())
    except yaml.YAMLError as e:
        raise ControlSpecError(f"{path}: not valid YAML: {e}") from e
    if not isinstance(raw, list):
        raise ControlSpecError(f"{path}: expected a list of controls")
    specs, seen = [], set()
    for i, entry in enumerate(raw):
        cid = entry.get("control_id", f"<entry {i}>") if isinstance(entry, dict) else f"<entry {i}>"
        try:
            spec = ControlSpec.model_validate(entry)
        except ValidationError as e:
            problems = "; ".join(
                f"field '{'.'.join(str(p) for p in err['loc']) or '<root>'}': {err['msg']}"
                for err in e.errors()
            )
            raise ControlSpecError(f"control {cid}: {problems}") from e
        if spec.control_id in seen:
            raise ControlSpecError(f"control {cid}: field 'control_id': duplicate id")
        seen.add(spec.control_id)
        specs.append(spec)
    return specs
