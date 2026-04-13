"""Stable advisory preflight package for future projection workflows."""

from __future__ import annotations

from typing import Any

from services.projection_memory_briefing import build_projection_memory_briefing


def build_projection_preflight(
    *,
    symbol: str,
    error_category: str | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    """
    Package pre-projection advisory context.

    This helper is packaging-only. It does not adjust scores, confidence,
    weights, projection inputs, or prediction logic.
    """
    clean_symbol = symbol.strip().upper()
    if not clean_symbol:
        raise ValueError("symbol is required")

    briefing = build_projection_memory_briefing(
        symbol=clean_symbol,
        error_category=error_category,
        limit=limit,
    )

    return {
        "symbol": clean_symbol,
        "briefing": briefing,
        "reminder_lines": briefing["reminder_lines"],
        "caution_level": briefing["caution_level"],
        "matched_count": briefing["matched_count"],
        "ready": True,
        "advisory_only": True,
    }
