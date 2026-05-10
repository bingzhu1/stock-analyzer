"""Pure-function adapter that assembles a ``feature_payload.v1`` dict
from already-computed feature parts and self-validates via
``services.feature_payload_contract`` (Step 18K / PR-FEATURE-2).

Spec source of truth:

- `tasks/record_1_0_architecture_reset_canonical_principles.md` §8 (Branch 2)
- `tasks/record_17f_feature_layer_rebuild_plan.md` §6 / §13
- `tasks/record_18a_first_layer_based_implementation_batch_selection.md` §13
- `tasks/record_18j_second_layer_based_implementation_batch_selection.md` §7 / §8

Status (per 18J §7 / §8):

- This module is the **Feature Layer (Branch 2) producer adapter** for
  the second batch of layer-based implementation PRs after the first
  batch (8/8 contract validators) landed.
- It is the **first PR of the second batch** that **wires PR-FEATURE-1**
  (``feature_payload.v1`` validator, commit ``3c9df83``) into a real
  callable shape, but **without** touching the active path. Producers in
  the active path (``services.projection_chain_contract.build_feature_payload_from_recent_window``,
  ``services.features_20d.compute_20d_features``, ``services.peer_alignment.build_peer_alignment``)
  continue to emit their existing dict shapes; this adapter is a pure
  assembler that callers may opt into in later batches.
- The adapter is intentionally a **skeleton**: it does not compute any
  feature, does not read any CSV, does not call ``yfinance``, does not
  call ``feature_builder`` / ``scanner`` / ``matcher`` / ``encoder`` /
  ``peer_alignment``.

Boundary contract (1.0 / 16A / 16C / 16F / 17F):

- This module is a **pure assembler + self-validator**. It:
  - Accepts already-computed feature sections via keyword arguments.
  - Composes a ``feature_payload.v1`` dict with the exact 10 top-level
    keys defined by ``services.feature_payload_contract``.
  - Calls ``validate_feature_payload`` on the assembled payload and
    returns the resulting ``list[str]`` unchanged (warnings + errors
    pass through with their original prefixes).
  - Never mutates its inputs (deep-copies all mutable sections).
  - Never raises business errors. (May raise ``TypeError`` only if Python
    itself rejects the keyword call signature; the body itself does not
    raise.)
  - Never reads files / calls external APIs / imports business modules /
    invokes a language-model client / writes to any DB.
- It **must not** import any of: ``yfinance``, ``pandas``, ``sqlite3``,
  ``feature_builder``, ``encoder``, ``scanner``, ``matcher``,
  ``services.peer_alignment``, ``services.data_query``,
  ``services.features_20d``, ``services.regime_features_builder``,
  ``services.regime_labels_builder``, ``services.projection_chain_contract``,
  ``services.main_projection_layer``, ``services.exclusion_layer``,
  ``services.confidence_evaluator``, ``services.final_decision``,
  ``services.consistency_layer``, ``services.review_orchestrator``,
  ``services.projection_orchestrator``, ``services.projection_orchestrator_v2``,
  ``services.projection_entrypoint``, ``services.projection_v2_adapter``,
  ``services.home_terminal_orchestrator``, ``predict``, ``app``,
  ``ui.*``, ``streamlit``, or any external LLM SDK.
- It **must not** auto-fill missing sections, auto-correct
  ``data_window_days``, normalize ``price_basis``, or compute / infer
  any feature value.

Why pure assembler (not "auto-correct"):

Per 18J §7, the second batch must "let producers emit standard schema"
and not "let consumers patch over producer gaps". Auto-correcting in the
adapter would let the active path keep shipping malformed payloads
indefinitely (16F no-patching). The validator's ``warning:`` /
``invalid value:`` / ``missing field:`` lines flow through to the
caller's ``validation_errors`` list so the caller can act on them
explicitly (e.g. log, raise its own error, or attach to a downstream
``warnings`` field).

Public API:

- ``build_feature_payload_from_parts(*, symbol, analysis_date,
  target_date, data_window_days, window_label, price_basis,
  ohlcv_window, returns, position, volume, candle, peer_alignment,
  code_features, data_quality) -> dict[str, Any]``

  Returns a dict with two top-level keys:

  - ``"payload"``: the assembled ``feature_payload.v1`` dict (deep-copies
    of all mutable inputs).
  - ``"validation_errors"``: ``validate_feature_payload(payload)`` —
    ``[]`` on success, otherwise a list of human-readable error /
    warning strings (prefixes preserved verbatim).
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from services.feature_payload_contract import (
    FEATURE_PAYLOAD_SCHEMA_VERSION,
    validate_feature_payload,
)


def build_feature_payload_from_parts(
    *,
    symbol: str,
    analysis_date: str | None,
    target_date: str | None,
    data_window_days: int,
    window_label: str | None,
    price_basis: str,
    ohlcv_window: list[dict[str, Any]],
    returns: dict[str, Any],
    position: dict[str, Any],
    volume: dict[str, Any],
    candle: dict[str, Any],
    peer_alignment: dict[str, Any],
    code_features: dict[str, Any],
    data_quality: dict[str, Any],
) -> dict[str, Any]:
    """Assemble a ``feature_payload.v1`` dict from already-computed parts.

    Returns a dict ``{"payload": <feature_payload.v1>,
    "validation_errors": [...]}``. ``validation_errors`` is the
    unchanged return of ``validate_feature_payload(payload)`` — empty
    list on success, otherwise a list of human-readable strings carrying
    the validator's stable prefixes (``"missing section: ..."``,
    ``"invalid value: ..."``, ``"warning: ..."``, etc.).

    The function never mutates its inputs (all mutable sections are
    deep-copied before being placed in the returned payload). It never
    raises business errors.

    Per 18J §7 / §8, the function is a **pure assembler**: it does not
    auto-fill missing sections, auto-correct ``data_window_days``,
    normalize ``price_basis``, or compute any feature value. Any
    contract violation surfaces in ``validation_errors`` for the caller
    to handle explicitly.
    """
    payload: dict[str, Any] = {
        "schema_version": FEATURE_PAYLOAD_SCHEMA_VERSION,
        "metadata": {
            "symbol": symbol,
            "analysis_date": analysis_date,
            "target_date": target_date,
            "data_window_days": data_window_days,
            "window_label": window_label,
            "price_basis": price_basis,
        },
        "ohlcv_window": deepcopy(ohlcv_window),
        "returns": deepcopy(returns),
        "position": deepcopy(position),
        "volume": deepcopy(volume),
        "candle": deepcopy(candle),
        "peer_alignment": deepcopy(peer_alignment),
        "code_features": deepcopy(code_features),
        "data_quality": deepcopy(data_quality),
    }

    return {
        "payload": payload,
        "validation_errors": validate_feature_payload(payload),
    }
