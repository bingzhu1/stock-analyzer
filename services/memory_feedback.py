"""Lightweight reminders from stored experience memory."""

from __future__ import annotations

from collections import Counter
from typing import Any

from services.error_taxonomy import normalize_error_category
from services.memory_store import list_experiences


def _category_counts(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts = Counter(str(record.get("error_category", "")) for record in records)
    return [
        {"error_category": category, "count": count}
        for category, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        if category
    ]


def _reminder_for(record: dict[str, Any]) -> str:
    symbol = str(record.get("symbol") or "UNKNOWN")
    category = str(record.get("error_category") or "insufficient_data")
    lesson = str(record.get("lesson") or "").strip()
    root_cause = str(record.get("root_cause") or "").strip()

    if lesson:
        return f"Prior {symbol} {category}: {lesson}"
    if root_cause:
        return f"Prior {symbol} {category}: {root_cause}"
    return f"Prior {symbol} {category}: review similar past cases before projecting."


def build_memory_feedback(
    *,
    symbol: str,
    error_category: str | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    """
    Return lightweight reminders from prior experience records.

    This helper is retrieval-only. It does not change scores, weights, prompts,
    projections, or stored records.
    """
    normalized_category = (
        normalize_error_category(error_category) if error_category is not None else None
    )
    records = list_experiences(
        symbol=symbol,
        error_category=normalized_category,
        limit=limit,
    )

    return {
        "symbol": symbol.strip().upper(),
        "error_category": normalized_category,
        "matched_count": len(records),
        "reminders": [_reminder_for(record) for record in records],
        "top_categories": _category_counts(records),
    }
