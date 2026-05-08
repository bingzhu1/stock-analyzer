"""Orchestration-facing advisory block for projection preflight.

Boundary contract (06 / 07A / 11D): the orchestrator forwards
``target_date`` to ``build_projection_preflight`` so the downstream
memory briefing can apply the cutoff guard. Legacy callers that omit
``target_date`` see the original behaviour.
"""

from __future__ import annotations

from typing import Any

from services.projection_preflight import build_projection_preflight


def build_projection_orchestrator_preflight(
    *,
    symbol: str,
    error_category: str | None = None,
    limit: int = 5,
    target_date: str | None = None,
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
        target_date=target_date,
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
