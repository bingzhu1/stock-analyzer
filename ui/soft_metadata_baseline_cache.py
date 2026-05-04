"""ui/soft_metadata_baseline_cache.py — session_state baseline cache.

Step 2G-6B.6 implementation per Step 2G-6B.4/6B.5 design (commit
`35b239d`). Lazy-builds ``soft_metadata_baseline`` once per Streamlit
session and stashes it in ``session_state``, so the Predict /
Review pages can pass a populated baseline to
``enrich_predict_result_with_soft_metadata`` without each render
re-running the SELECT-only baseline query.

Design contract (Step 2G-6B.4/6B.5 §5):
- pure-ish function: only side effect is writing two keys to
  ``session_state``; never raises
- never writes DB / file / network (delegates baseline build to
  ``services.soft_metadata_simulator.build_soft_metadata_baseline``,
  which is SELECT-only)
- never imports trading APIs / ``yfinance`` / ``requests`` / v1 stub trio
- failure mode: builder exception → ``soft_metadata_baseline_error``
  recorded in session_state; returns None
- not called at import time

Public API:
    ensure_soft_metadata_baseline_cached(
        *, symbol="AVGO", limit=450, session_state=None,
    ) -> dict | None

``session_state`` may be passed explicitly (for testing / non-Streamlit
callers); when None, attempts to import ``streamlit.session_state``.
When neither is available, the function returns None (no caching) so
the helper degrades gracefully outside a Streamlit context.
"""
from __future__ import annotations

from typing import Any

from services.soft_metadata_simulator import build_soft_metadata_baseline


CACHE_KEY = "soft_metadata_baseline"
ERROR_KEY = "soft_metadata_baseline_error"


def _resolve_session_state(session_state: Any) -> Any:
    """Return a usable session_state-like object, or None.

    Tests pass a dict explicitly. Production Streamlit callers usually
    pass ``st.session_state``; we also lazily import streamlit when
    the caller doesn't supply one.
    """
    if session_state is not None:
        return session_state
    try:
        import streamlit as st
        return st.session_state
    except Exception:  # noqa: BLE001
        return None


def ensure_soft_metadata_baseline_cached(
    *,
    symbol: str = "AVGO",
    limit: int = 450,
    session_state: Any = None,
) -> dict | None:
    """Lazy-build + cache ``soft_metadata_baseline`` in session_state.

    Returns the cached baseline dict, or None when no session is
    available / build failed. Never raises.
    """
    state = _resolve_session_state(session_state)
    if state is None:
        # Defensive: no session to cache into. Build once anyway so the
        # caller still gets a usable baseline (no caching benefit, but
        # also no crash). We swallow exceptions for symmetry.
        try:
            return build_soft_metadata_baseline(symbol=symbol, limit=limit)
        except Exception:  # noqa: BLE001
            return None

    # Session-cache hit — return memoized value.
    try:
        cached = state[CACHE_KEY]
    except (KeyError, TypeError):
        cached = None
    if isinstance(cached, dict):
        return cached

    try:
        baseline = build_soft_metadata_baseline(symbol=symbol, limit=limit)
    except Exception as exc:  # noqa: BLE001
        try:
            state[ERROR_KEY] = f"baseline_build_failed: {exc}"
        except Exception:  # noqa: BLE001
            pass
        return None

    if not isinstance(baseline, dict):
        return None

    try:
        state[CACHE_KEY] = baseline
    except Exception:  # noqa: BLE001
        # Read-only / unsupported session_state. Caller still gets the
        # built baseline; just no caching for next call.
        pass
    return baseline
