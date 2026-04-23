"""Orchestration-facing advisory block for projection preflight."""

from __future__ import annotations

from typing import Any

from services.projection_preflight import build_projection_preflight


def build_projection_orchestrator_preflight(
    *,
    symbol: str,
    error_category: str | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    """
    Package projection preflight output for future orchestration flows.

    This helper is advisory-only. It does not adjust scores, confidence,
    weights, projection inputs, or prediction logic.
    """
    preflight = build_projection_preflight(
        symbol=symbol,
        error_category=error_category,
        limit=limit,
    )
    advisory_block = {
        "kind": "projection_preflight_advisory",
        "source": "projection_preflight",
        "preflight": preflight,
        "advisory_only": True,
    }

    return {
        "symbol": preflight["symbol"],
        "advisory_block": advisory_block,
        "reminder_lines": preflight["reminder_lines"],
        "caution_level": preflight["caution_level"],
        "matched_count": preflight["matched_count"],
        "ready": preflight["ready"],
        "advisory_only": True,
    }
