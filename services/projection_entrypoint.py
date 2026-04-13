"""Callable entrypoint for the current projection orchestration chain."""

from __future__ import annotations

from typing import Any

from services.projection_orchestrator import build_projection_orchestrator_result


def run_projection_entrypoint(
    *,
    symbol: str,
    error_category: str | None = None,
    limit: int = 5,
    lookback_days: int | None = None,
) -> dict[str, Any]:
    """
    Call the current projection orchestrator through one stable interface.

    This delegates to existing projection, scan, and predict helpers. It does
    not change scanner or predict scoring rules.
    """
    return build_projection_orchestrator_result(
        symbol=symbol,
        error_category=error_category,
        limit=limit,
        lookback_days=lookback_days,
    )
