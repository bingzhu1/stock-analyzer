"""Pure-function adapter that translates a legacy main_projection_layer
output dict into a ``projection_result.v1`` standard payload and
self-validates via ``services.projection_result_contract`` (Step 18L /
PR-PROJ-2).

Spec source of truth:

- `tasks/record_1_0_architecture_reset_canonical_principles.md` §8 (Branch 3)
- `tasks/record_07a_projection_system_contract.md` §3 / §9
- `tasks/record_17g_projection_layer_rebuild_plan.md` §8 / §13
- `tasks/record_18a_first_layer_based_implementation_batch_selection.md` §13
- `tasks/record_18j_second_layer_based_implementation_batch_selection.md` §6 / §13

Status (per 18J §6 / §14 batch ordering):

- This module is the **Projection Layer (Branch 3) producer adapter**
  for the second batch — wires PR-PROJ-1 (``projection_result.v1``
  validator, commit ``f719d71``) into a real callable shape **without
  touching active path**. Producers in the active path (notably
  ``services.main_projection_layer.build_main_projection_layer`` /
  ``run_main_projection_layer``) continue to emit their existing dict
  shape with legacy ``kind="main_projection_layer"`` /
  ``predicted_top1`` / ``predicted_top2``; this adapter is opt-in and
  unused by V2 orchestrator / home_terminal / predict at landing time.
- 18L explicitly chose Plan A (adapter-only) over Plan B (modify
  ``main_projection_layer`` active output) because the legacy output
  contains ``predicted_top1`` / ``predicted_top2`` at top level —
  ``projection_result_contract.FORBIDDEN_FIELDS`` explicitly rejects
  them (18A §13 Option A), so direct alias-on-top-level cannot pass the
  validator. The adapter route preserves legacy output unchanged for
  active callers and exposes a pure-function translation for new
  callers.

Boundary contract (1.0 / 16A / 16C / 16F / 17G / 18J):

- This module is a **pure translator + self-validator**. It:
  - Accepts a legacy projection dict + the caller's ``symbol`` (and
    optional ``feature_snapshot_ref``) via keyword arguments.
  - Composes a ``projection_result.v1`` dict with the exact 15 top-level
    keys defined by ``services.projection_result_contract``.
  - Calls ``validate_projection_result`` on the assembled payload and
    returns the resulting ``list[str]`` unchanged (warnings + errors
    pass through with their original prefixes).
  - Never mutates the legacy input (deep-copies all mutable sections
    that flow through to the returned payload).
  - Never raises business errors. (May raise ``TypeError`` only if
    Python itself rejects the keyword call signature.)
  - Never re-runs the projection / re-ranks / re-normalizes
    probabilities / reads ``exclusion_result`` / ``confidence_result`` /
    ``final_report``.
  - Never reads files / calls external APIs / imports business modules /
    invokes a language-model client / writes to any DB.
- It **must not** import any of: ``services.main_projection_layer``,
  ``services.exclusion_layer``, ``services.peer_alignment``,
  ``services.confidence_evaluator``, ``services.final_decision``,
  ``services.consistency_layer``, ``services.review_orchestrator``,
  ``services.projection_orchestrator``,
  ``services.projection_orchestrator_v2``,
  ``services.projection_entrypoint``,
  ``services.projection_v2_adapter``,
  ``services.home_terminal_orchestrator``,
  ``services.feature_payload_contract``,
  ``services.feature_payload_adapter``,
  ``services.standard_projection_payload``,
  ``predict``, ``app``, ``ui.*``, ``streamlit``, any DB / sqlite3 /
  yfinance / external LLM SDK.

Why pure translator (not "auto-correct"):

Per 18J §7 / 16F no-patching, the second batch must "let producers emit
standard schema" — the adapter therefore translates the **observable
shape** of legacy projection output into the standard schema, but does
not invent fields that the legacy output did not produce. Missing /
malformed legacy fields surface as ``validation_errors`` from the
validator, so the caller can act on them explicitly.

Public API:

- ``build_projection_result_from_legacy(legacy_projection, *, symbol,
  feature_snapshot_ref=None) -> dict[str, Any]``

  Returns a dict ``{"payload": <projection_result.v1>,
  "validation_errors": [...]}``. ``validation_errors`` is the unchanged
  return of ``validate_projection_result(payload)``.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from services.projection_result_contract import (
    PROJECTION_RESULT_KIND,
    PROJECTION_RESULT_SCHEMA_VERSION,
    VALID_STATES,
    validate_projection_result,
)


_NON_MUTATION_DEFAULTS: dict[str, bool] = {
    "projection_did_not_read_exclusion": True,
    "projection_did_not_read_confidence": True,
    "projection_did_not_read_final_report": True,
    "projection_did_not_read_future_outcome": True,
}


def _coerce_float_or_zero(value: Any) -> float:
    """Internal: convert a value to ``float`` for ranking; non-numeric /
    bool / None all map to 0.0. Used only inside ``ranked_states`` sort
    when ``state_probabilities`` is the source — does not affect the
    returned ``state_probabilities`` content."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0.0
    return float(value)


def _extract_most_likely_state(legacy: dict[str, Any]) -> str | None:
    """Internal: pull a 5-state label from legacy ``predicted_top1.state``.

    Returns one of ``VALID_STATES`` if the legacy field is well-formed,
    else ``None``. The validator interprets ``None`` as valid only when
    ``ready=False``."""
    top1 = legacy.get("predicted_top1")
    if isinstance(top1, dict):
        candidate = top1.get("state")
        if candidate in VALID_STATES:
            return candidate
    return None


def _build_ranked_states(
    legacy: dict[str, Any], most_likely_state: str | None
) -> list[str]:
    """Internal: derive ``ranked_states`` from the most reliable legacy
    source available — sorted ``state_probabilities`` first, else
    ``predicted_top1`` / ``predicted_top2`` pair, else
    ``[most_likely_state]`` if it exists, else ``[]``.

    The function never re-runs the projection: it only orders existing
    legacy values."""
    state_probs = legacy.get("state_probabilities")
    if isinstance(state_probs, dict) and state_probs:
        state_index = {state: idx for idx, state in enumerate(VALID_STATES)}
        valid_pairs = [
            (state, _coerce_float_or_zero(prob))
            for state, prob in state_probs.items()
            if state in VALID_STATES
        ]
        # Sort by probability desc, then by canonical 5-state order for
        # stable tie-breaks.
        valid_pairs.sort(key=lambda kv: (-kv[1], state_index[kv[0]]))
        ranked = [state for state, _ in valid_pairs]
        if ranked:
            return ranked

    # Fallback: predicted_top1 / predicted_top2 pair.
    ranked: list[str] = []
    if most_likely_state is not None:
        ranked.append(most_likely_state)
    top2 = legacy.get("predicted_top2")
    if isinstance(top2, dict):
        candidate = top2.get("state")
        if (
            candidate in VALID_STATES
            and candidate not in ranked
        ):
            ranked.append(candidate)
    return ranked


def _pick_evidence(legacy: dict[str, Any]) -> dict[str, Any] | list[Any]:
    """Internal: prefer ``evidence`` when present; otherwise fall back
    to ``key_observations`` then ``basis``. Default ``{}``."""
    for key in ("evidence", "key_observations", "basis"):
        candidate = legacy.get(key)
        if isinstance(candidate, (dict, list)):
            return candidate
    return {}


def _pick_rationale(legacy: dict[str, Any]) -> str | list[Any]:
    """Internal: prefer ``rationale``; otherwise ``reason`` /
    ``explanation`` / ``summary``. Default ``[]`` (validator accepts
    str or list)."""
    for key in ("rationale", "reason", "explanation", "summary"):
        candidate = legacy.get(key)
        if isinstance(candidate, (str, list)):
            return candidate
    return []


def _pick_raw_score(legacy: dict[str, Any]) -> float | int | None:
    """Internal: prefer ``raw_score``; otherwise ``score``. Default
    ``None``. Bool is rejected (validator forbids bool numerics)."""
    for key in ("raw_score", "score"):
        candidate = legacy.get(key)
        if isinstance(candidate, bool):
            continue
        if isinstance(candidate, (int, float)):
            return candidate
    return None


def _pick_warnings(legacy: dict[str, Any]) -> list[Any]:
    """Internal: passthrough ``warnings`` if list; else ``[]``."""
    candidate = legacy.get("warnings")
    if isinstance(candidate, list):
        return candidate
    return []


def _pick_historical_match_summary(legacy: dict[str, Any]) -> dict[str, Any]:
    """Internal: passthrough ``historical_match_summary`` if dict; else
    ``{}``."""
    candidate = legacy.get("historical_match_summary")
    if isinstance(candidate, dict):
        return candidate
    return {}


def _pick_peer_alignment_summary(legacy: dict[str, Any]) -> dict[str, Any]:
    """Internal: prefer ``peer_alignment_summary`` if dict; else fall
    back to legacy ``peer_alignment`` dict (which legacy
    main_projection_layer emits at top level). Default ``{}``."""
    candidate = legacy.get("peer_alignment_summary")
    if isinstance(candidate, dict):
        return candidate
    candidate = legacy.get("peer_alignment")
    if isinstance(candidate, dict):
        return candidate
    return {}


def build_projection_result_from_legacy(
    legacy_projection: dict[str, Any],
    *,
    symbol: str,
    feature_snapshot_ref: str | dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble a ``projection_result.v1`` payload from a legacy
    main_projection_layer output dict.

    Returns a dict ``{"payload": <projection_result.v1>,
    "validation_errors": [...]}``. ``validation_errors`` is the
    unchanged return of ``validate_projection_result(payload)`` — empty
    list on success, otherwise a list of human-readable strings carrying
    the validator's stable prefixes (``"missing section: ..."``,
    ``"invalid value: ..."``, etc.).

    The function never mutates ``legacy_projection`` (all mutable
    sections that flow through are deep-copied before being placed in
    the returned payload). It never raises business errors.

    Per 18J §7 + 16F no-patching, the function is a **pure translator**:
    it does not auto-fill missing sections, re-run the projection,
    re-rank, or normalize probabilities. Any contract violation surfaces
    in ``validation_errors`` for the caller to handle explicitly.
    """
    legacy = legacy_projection if isinstance(legacy_projection, dict) else {}

    most_likely_state = _extract_most_likely_state(legacy)
    ranked_states = _build_ranked_states(legacy, most_likely_state)

    state_probabilities = legacy.get("state_probabilities")
    if not isinstance(state_probabilities, dict):
        state_probabilities = {}

    payload: dict[str, Any] = {
        "schema_version": PROJECTION_RESULT_SCHEMA_VERSION,
        "kind": PROJECTION_RESULT_KIND,
        "symbol": symbol,
        "ready": legacy.get("ready", False),
        "most_likely_state": most_likely_state,
        "ranked_states": ranked_states,
        "state_probabilities": deepcopy(state_probabilities),
        "evidence": deepcopy(_pick_evidence(legacy)),
        "rationale": deepcopy(_pick_rationale(legacy)),
        "raw_score": _pick_raw_score(legacy),
        "warnings": deepcopy(_pick_warnings(legacy)),
        "feature_snapshot_ref": deepcopy(feature_snapshot_ref),
        "historical_match_summary": deepcopy(
            _pick_historical_match_summary(legacy)
        ),
        "peer_alignment_summary": deepcopy(
            _pick_peer_alignment_summary(legacy)
        ),
        "non_mutation_confirmations": dict(_NON_MUTATION_DEFAULTS),
    }

    return {
        "payload": payload,
        "validation_errors": validate_projection_result(payload),
    }
