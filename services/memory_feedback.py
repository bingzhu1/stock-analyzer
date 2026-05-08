"""Lightweight reminders from stored experience memory.

Boundary contract (06 / 07A / 11D): when an online caller passes a
``target_date``, this helper filters the loaded experience records
through ``services.cutoff_guard.filter_records_by_cutoff`` so reminders
never leak future memory. ``target_date=None`` preserves the original
retrieval-only behaviour for legacy callers (offline scripts / tests
that pre-date the cutoff guard).
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from services.cutoff_guard import filter_records_by_cutoff
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
    target_date: str | None = None,
) -> dict[str, Any]:
    """
    Return lightweight reminders from prior experience records.

    This helper is retrieval-only. It does not change scores, weights, prompts,
    projections, or stored records.

    When ``target_date`` is provided, records dated after ``target_date`` (per
    the cutoff_guard audit rules in 11D §5–§6) are SKIPPED rather than returned
    as reminders, and the output dict carries a ``cutoff_guard`` audit summary.
    When ``target_date`` is omitted, the legacy retrieval behaviour is
    preserved and no ``cutoff_guard`` field is added (keeps offline callers
    backward compatible).
    """
    normalized_category = (
        normalize_error_category(error_category) if error_category is not None else None
    )
    records = list_experiences(
        symbol=symbol,
        error_category=normalized_category,
        limit=limit,
    )

    cutoff_guard: dict[str, Any] | None = None
    if target_date is not None:
        filtered = filter_records_by_cutoff(records, target_date=target_date)
        records = filtered["allowed_records"]
        cutoff_guard = filtered["cutoff_guard"]

    payload: dict[str, Any] = {
        "symbol": symbol.strip().upper(),
        "error_category": normalized_category,
        "matched_count": len(records),
        "reminders": [_reminder_for(record) for record in records],
        "top_categories": _category_counts(records),
    }
    if cutoff_guard is not None:
        payload["cutoff_guard"] = cutoff_guard
    return payload
