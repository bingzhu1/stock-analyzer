"""Minimal projection orchestrator MVP.

This module only packages request inputs with advisory preflight output. It
does not compute projections or modify scores, confidence, or weights.
"""

from __future__ import annotations

from typing import Any

from services.projection_orchestrator_preflight import (
    build_projection_orchestrator_preflight,
)

_NO_PROJECTION_NOTE = "Projection engine not invoked; advisory package only."


def build_projection_orchestrator_result(
    *,
    symbol: str,
    error_category: str | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    """Return a stable orchestration result for future projection workflows."""
    advisory = build_projection_orchestrator_preflight(
        symbol=symbol,
        error_category=error_category,
        limit=limit,
    )
    request = {
        "symbol": advisory["symbol"],
        "error_category": error_category,
        "limit": limit,
    }

    return {
        "symbol": advisory["symbol"],
        "request": request,
        "advisory": advisory,
        "ready": advisory["ready"],
        "notes": [_NO_PROJECTION_NOTE],
        "advisory_only": True,
    }
