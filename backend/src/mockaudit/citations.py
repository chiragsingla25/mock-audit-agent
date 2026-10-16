"""Citation check: keep citations that point at an existing record; drop and log the rest."""

from __future__ import annotations

import logging

from mockaudit.schemas import Citation

log = logging.getLogger("mockaudit.citations")


def check_citations(citations: list[Citation], index: set[tuple[str, str]], context: str = "") -> tuple[list[Citation], list[Citation]]:
    kept, dropped = [], []
    for c in citations:
        (kept if (c.source, c.record_id) in index else dropped).append(c)
    for c in dropped:
        log.warning("%sdropped citation to nonexistent record %s/%s", f"{context}: " if context else "", c.source, c.record_id)
    return kept, dropped
