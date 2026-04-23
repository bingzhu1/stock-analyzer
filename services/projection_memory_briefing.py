"""Projection-facing advisory briefing from experience memory."""

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
) -> dict[str, Any]:
    """
    Build an advisory pre-projection memory briefing.

    This helper packages reminders only. It does not adjust scores, confidence,
    weights, projection inputs, or prediction logic.
    """
    feedback = build_memory_feedback(
        symbol=symbol,
        error_category=error_category,
        limit=limit,
    )
    matched_count = int(feedback["matched_count"])

    return {
        "symbol": feedback["symbol"],
        "matched_count": matched_count,
        "top_categories": feedback["top_categories"],
        "reminder_lines": feedback["reminders"],
        "caution_level": _caution_level(matched_count),
        "advisory_only": True,
    }
