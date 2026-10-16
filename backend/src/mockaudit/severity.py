"""Deterministic severity rules (architecture.md §6), first match wins. Never set by an LLM."""

from __future__ import annotations

PERIODIC_GAPS = {"frequency_gap", "missing_evidence", "evidence_out_of_period"}
HIGH_RATE = 0.10


def severity(gap_type: str, exceptions: int, tested: int, risk: str, periodic: bool) -> tuple[str, int]:
    """Return (severity, rule number)."""
    if gap_type == "segregation_of_duties":
        return "high", 1
    if gap_type == "population_completeness" and risk == "high":
        return "high", 2
    if periodic and gap_type in PERIODIC_GAPS and risk == "high":
        return "high", 3
    if risk == "high" and tested and exceptions / tested > HIGH_RATE:
        return "high", 4
    if risk == "high":
        return "moderate", 5
    if risk == "moderate":
        return "moderate", 6
    return "low", 7
