"""Step 12E-X4-C: isolated bridge from V2 payload to legacy PredictResult.

This helper is the offline / diagnostic entry point for invoking
``predict.run_predict``'s X4-B opt-in adapter without modifying any
existing active caller. It lets a future replay / diagnostic / contract
playback tool that already has a V2 orchestrator payload obtain a
legacy-shaped prediction result, by routing through
``run_predict(..., v2_payload=...)`` (which itself calls the pure
``services.predict_legacy_adapter.adapt_v2_payload_to_predict_legacy``).

Boundary contract (X4-C):

- The bridge is NOT imported by any active path: not by app.py, not by
  ui/, not by command bar, not by live prediction. It is opt-in for
  offline / diagnostic / contract callers only.
- The bridge does NOT execute the V2 orchestrator. The caller must
  supply ``v2_payload`` from an existing source (for example a captured
  V2 payload snapshot). The bridge never constructs one.
- The bridge does NOT call the LLM, write the database, read future
  data, or invoke ``services.projection_orchestrator_v2``.
- Missing / non-dict ``v2_payload`` is non-fatal: the bridge returns the
  legacy baseline (``run_predict`` with ``v2_payload=None``) and records
  a warning in ``v2_adapter_warnings``. The bridge never raises on
  caller mistakes.
- The bridge never mutates ``v2_payload`` or
  ``fallback_legacy_payload`` (the underlying adapter is pure and the
  wrapper takes a fresh copy before overlaying).

Design contracts: 06 / 07A / 07C / 07D / 11E / 11H.
"""

from __future__ import annotations

from typing import Any


BRIDGE_KIND = "predict_legacy_v2_bridge"
BRIDGE_VERSION = "predict_legacy_v2_bridge.v1"


def build_legacy_prediction_from_v2_payload(
    *,
    v2_payload: dict[str, Any] | None,
    fallback_legacy_payload: dict[str, Any] | None = None,
    symbol: str = "AVGO",
) -> dict[str, Any]:
    """Return a legacy-shaped ``PredictResult`` from a V2 payload.

    Always routes through ``predict.run_predict``'s X4-B opt-in path,
    which calls ``adapt_v2_payload_to_predict_legacy`` and overlays the
    allowlisted compat keys onto the wrapper output. The returned dict
    is the wrapper's full ``PredictResult`` shape plus ``bridge_kind``
    / ``bridge_version`` markers and any bridge-level warnings appended
    onto ``v2_adapter_warnings``.

    Parameters
    ----------
    v2_payload:
        A V2 orchestrator payload dict. When ``None`` or any non-dict,
        the bridge returns the legacy baseline (``run_predict`` called
        with ``v2_payload=None``) and records a warning entry.
    fallback_legacy_payload:
        Accepted for API symmetry with the underlying adapter. The
        wrapper builds its own fallback from the legacy missing-scan
        baseline before invoking the adapter, so this kwarg is
        informational only — it is not threaded down. The signature
        documents the bridge as a stable extension point for future
        callers that want to express a fallback.
    symbol:
        Symbol label forwarded to ``run_predict``. Defaults to ``"AVGO"``.

    Notes
    -----
    The import of ``predict.run_predict`` is intentionally lazy: that
    way, callers that only read ``BRIDGE_KIND`` / ``BRIDGE_VERSION``
    constants do not pull ``predict.py`` into their module-load graph.
    The lazy import also keeps the bridge from inflating the active
    import chain at startup.
    """
    from predict import run_predict

    bridge_warnings: list[str] = []

    if not isinstance(v2_payload, dict):
        bridge_warnings.append(
            "predict_legacy_v2_bridge: v2_payload missing or not a dict; "
            "returned legacy baseline without V2 overlay."
        )
        result = run_predict(None, research_result=None, symbol=symbol)
    else:
        result = run_predict(
            None,
            research_result=None,
            symbol=symbol,
            v2_payload=v2_payload,
        )

    output = dict(result)
    output["bridge_kind"] = BRIDGE_KIND
    output["bridge_version"] = BRIDGE_VERSION
    if bridge_warnings:
        existing = list(output.get("v2_adapter_warnings") or [])
        existing.extend(bridge_warnings)
        output["v2_adapter_warnings"] = existing
    return output
