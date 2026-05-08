"""Projection-facing advisory briefing from experience memory.

Boundary contract (06 / 07A / 11D): forwards ``target_date`` to
``build_memory_feedback`` so reminders never leak future memory; the
resulting ``cutoff_guard`` audit summary is surfaced on the briefing
output. Legacy callers that omit ``target_date`` see the original
behaviour with no ``cutoff_guard`` field.
"""

from __future__ import annotations

from typing import Any

from services.memory_feedback import build_memory_feedback


def _caution_level(matched_count: int) -> str:
    if matched_count <= 0:
        return "none"
    if matched_count <= 2:
        return "low"
    if matched_count <= 4:
        return "medium"
    return "high"


def build_projection_memory_briefing(
    *,
    symbol: str,
    error_category: str | None = None,
    limit: int = 5,
    target_date: str | None = None,
) -> dict[str, Any]:
    """
    Build an advisory pre-projection memory briefing.

    This helper packages reminders only. It does not adjust scores, confidence,
    weights, projection inputs, or prediction logic.

    When ``target_date`` is provided, the underlying memory feedback applies
    the 11D cutoff guard, and the resulting audit summary is forwarded as
    ``cutoff_guard`` on this briefing.
    """
    feedback = build_memory_feedback(
        symbol=symbol,
        error_category=error_category,
        limit=limit,
        target_date=target_date,
    )
    matched_count = int(feedback["matched_count"])

    briefing: dict[str, Any] = {
        "symbol": feedback["symbol"],
        "matched_count": matched_count,
        "top_categories": feedback["top_categories"],
        "reminder_lines": feedback["reminders"],
        "caution_level": _caution_level(matched_count),
        "advisory_only": True,
    }
    if "cutoff_guard" in feedback:
        briefing["cutoff_guard"] = feedback["cutoff_guard"]
    return briefing
