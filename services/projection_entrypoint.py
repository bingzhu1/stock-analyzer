"""Callable entrypoint for the current projection orchestration chain."""

from __future__ import annotations

from typing import Any

from services.projection_orchestrator import build_projection_orchestrator_result


def run_projection_entrypoint(
    *,
    symbol: str,
    error_category: str | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    """
    Call the current projection orchestrator through one stable interface.

    This is packaging-only. It does not call scanner/predict, compute a
    projection, or adjust scores, confidence, or weights.
    """
    return build_projection_orchestrator_result(
        symbol=symbol,
        error_category=error_category,
        limit=limit,
    )
