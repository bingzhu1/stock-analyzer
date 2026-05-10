"""Pure-function adapter that translates a legacy exclusion_layer output
dict into an ``exclusion_result.v1`` standard payload and self-validates
via ``services.exclusion_result_contract`` (Step 18M / PR-EXCL-2).

Spec source of truth:

- `tasks/record_1_0_architecture_reset_canonical_principles.md` §8 (Branch 4)
- `tasks/record_07b_exclusion_system_contract.md` §3 / §9
- `tasks/record_17h_exclusion_layer_rebuild_plan.md` §8 / §10 / §14
- `tasks/record_18a_first_layer_based_implementation_batch_selection.md` §13
- `tasks/record_18j_second_layer_based_implementation_batch_selection.md` §6 / §13

Status (per 18J §6 / §14 batch ordering):

- This module is the **Exclusion Layer (Branch 4) producer adapter**
  for the second batch — wires PR-EXCL-1 (``exclusion_result.v1``
  validator, commit ``bc22937``) into a real callable shape **without
  touching active path**. Producers in the active path (notably
  ``services.exclusion_layer.run_exclusion_layer`` /
  ``exclude_big_up`` / ``exclude_big_down``) continue to emit their
  existing dict shape with legacy ``triggered_rule`` (single) /
  ``action`` / ``excluded`` / ``summary`` / ``reasons`` /
  ``peer_alignment`` / ``feature_snapshot``; this adapter is opt-in and
  unused by V2 orchestrator / home_terminal / confidence_evaluator at
  landing time.
- 18M chose adapter-only (Plan A) over modifying ``exclusion_layer``
  active output because the legacy output contains ``triggered_rule``
  (singular) at top level — ``exclusion_result_contract.FORBIDDEN_FIELDS``
  explicitly rejects it (18A §13 / 17H §11). The adapter route preserves
  legacy output unchanged for active callers and exposes a pure-function
  translation for new callers.

Boundary contract (1.0 / 16A / 16C / 16F / 17H / 18J):

- This module is a **pure translator + self-validator**. It:
  - Accepts a legacy exclusion dict + the caller's ``symbol`` (and
    optional ``feature_snapshot_ref``) via keyword arguments.
  - Composes an ``exclusion_result.v1`` dict with the exact 16
    top-level keys defined by ``services.exclusion_result_contract``.
  - Calls ``validate_exclusion_result`` on the assembled payload and
    returns the resulting ``list[str]`` unchanged (warnings + errors
    pass through with their original prefixes).
  - Never mutates the legacy input (deep-copies all mutable sections
    that flow through to the returned payload).
  - Never raises business errors. (May raise ``TypeError`` only if
    Python itself rejects the keyword call signature.)
  - Never re-runs exclusion / re-derives triggered_rules / re-computes
    false_exclusion_risk / reads ``projection_result`` /
    ``confidence_result`` / ``final_report``.
  - Never reads files / calls external APIs / imports business modules /
    invokes a language-model client / writes to any DB.
- It **must not** import any of: ``services.exclusion_layer``,
  ``services.peer_alignment``, ``services.main_projection_layer``,
  ``services.confidence_evaluator``, ``services.final_decision``,
  ``services.consistency_layer``, ``services.review_orchestrator``,
  ``services.projection_orchestrator``,
  ``services.projection_orchestrator_v2``,
  ``services.projection_entrypoint``,
  ``services.projection_v2_adapter``,
  ``services.home_terminal_orchestrator``,
  ``services.feature_payload_contract``,
  ``services.feature_payload_adapter``,
  ``services.projection_result_contract``,
  ``services.projection_result_adapter``,
  ``services.standard_projection_payload``,
  ``predict``, ``app``, ``ui.*``, ``streamlit``, any DB / sqlite3 /
  yfinance / external LLM SDK.

Why pure translator (not "auto-correct"):

Per 18J §7 / 16F no-patching, the second batch must "let producers emit
standard schema" — the adapter therefore translates the **observable
shape** of legacy exclusion output into the standard schema, but does
not invent fields the legacy output did not produce. Missing /
malformed legacy fields surface as ``validation_errors`` from the
validator, so the caller can act on them explicitly.

Public API:

- ``build_exclusion_result_from_legacy(legacy_exclusion, *, symbol,
  feature_snapshot_ref=None) -> dict[str, Any]``

  Returns a dict ``{"payload": <exclusion_result.v1>,
  "validation_errors": [...]}``. ``validation_errors`` is the unchanged
  return of ``validate_exclusion_result(payload)``.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from services.exclusion_result_contract import (
    EXCLUSION_RESULT_KIND,
    EXCLUSION_RESULT_SCHEMA_VERSION,
    VALID_FALSE_EXCLUSION_RISK,
    VALID_STATES,
    validate_exclusion_result,
)


_NON_MUTATION_DEFAULTS: dict[str, bool] = {
    "exclusion_did_not_read_projection": True,
    "exclusion_did_not_read_confidence": True,
    "exclusion_did_not_read_final_report": True,
    "exclusion_did_not_read_future_outcome": True,
}

# Legacy ``triggered_rule`` single-value → 5-state Chinese label mapping.
# 17H §11 / 18A §13 — ``exclude_big_up`` means 大涨 is the unlikely state;
# ``exclude_big_down`` means 大跌 is the unlikely state.
_TRIGGERED_RULE_TO_STATE: dict[str, str] = {
    "exclude_big_up": "大涨",
    "exclude_big_down": "大跌",
}


def _state_from_triggered_rule(rule: Any) -> str | None:
    """Internal: map a legacy ``triggered_rule`` single value to a 5-state
    label, or None if not recognised."""
    if isinstance(rule, str):
        return _TRIGGERED_RULE_TO_STATE.get(rule)
    return None


def _extract_most_unlikely_state(legacy: dict[str, Any]) -> str | None:
    """Internal: pick the most unlikely state from the most reliable
    legacy source available.

    Priority:
      1. ``legacy["most_unlikely_state"]`` if in VALID_STATES
      2. ``legacy["triggered_rule"]`` mapped via _TRIGGERED_RULE_TO_STATE
      3. ``legacy["excluded_states"][0]`` if a valid state
      4. ``legacy["excluded"]`` (when the alt-shape uses str instead of
         bool) if in VALID_STATES
      5. ``legacy["exclude_big_up"] is True`` → 大涨
      6. ``legacy["exclude_big_down"] is True`` → 大跌
      7. ``None``
    """
    candidate = legacy.get("most_unlikely_state")
    if candidate in VALID_STATES:
        return candidate

    mapped = _state_from_triggered_rule(legacy.get("triggered_rule"))
    if mapped is not None:
        return mapped

    excluded_states = legacy.get("excluded_states")
    if isinstance(excluded_states, list):
        for entry in excluded_states:
            if entry in VALID_STATES:
                return entry

    excluded = legacy.get("excluded")
    if isinstance(excluded, str) and excluded in VALID_STATES:
        return excluded

    if legacy.get("exclude_big_up") is True:
        return "大涨"
    if legacy.get("exclude_big_down") is True:
        return "大跌"

    return None


def _build_excluded_states(
    legacy: dict[str, Any], most_unlikely_state: str | None
) -> list[str]:
    """Internal: derive the ``excluded_states`` list from legacy fields,
    preserving order and deduping. Never invents states."""
    out: list[str] = []

    def _add(state: Any) -> None:
        if state in VALID_STATES and state not in out:
            out.append(state)

    legacy_excluded = legacy.get("excluded_states")
    if isinstance(legacy_excluded, list):
        for entry in legacy_excluded:
            _add(entry)

    excluded = legacy.get("excluded")
    if isinstance(excluded, str):
        _add(excluded)

    if legacy.get("exclude_big_up") is True:
        _add("大涨")
    if legacy.get("exclude_big_down") is True:
        _add("大跌")

    mapped = _state_from_triggered_rule(legacy.get("triggered_rule"))
    if mapped is not None:
        _add(mapped)

    if most_unlikely_state is not None:
        _add(most_unlikely_state)

    return out


def _build_ranked_unlikely_states(
    legacy: dict[str, Any],
    excluded_states: list[str],
    most_unlikely_state: str | None,
) -> list[str]:
    """Internal: derive ``ranked_unlikely_states`` from the most reliable
    legacy source available.

    Priority:
      1. ``legacy["ranked_unlikely_states"]`` filtered to VALID_STATES
      2. ``excluded_states`` already built (already valid + deduped)
      3. ``[most_unlikely_state]`` if not None
      4. ``[]``
    """
    legacy_ranked = legacy.get("ranked_unlikely_states")
    if isinstance(legacy_ranked, list):
        ranked: list[str] = []
        for entry in legacy_ranked:
            if entry in VALID_STATES and entry not in ranked:
                ranked.append(entry)
        if ranked:
            return ranked

    if excluded_states:
        return list(excluded_states)

    if most_unlikely_state is not None:
        return [most_unlikely_state]

    return []


def _build_triggered_rules(legacy: dict[str, Any]) -> list[str]:
    """Internal: derive ``triggered_rules`` (plural list) from legacy.

    Priority:
      1. ``legacy["triggered_rules"]`` (list of non-empty strings only)
      2. ``[legacy["triggered_rule"]]`` (single non-empty string lifted
         into a list)
      3. ``[]``
    """
    legacy_rules = legacy.get("triggered_rules")
    if isinstance(legacy_rules, list):
        out = [r for r in legacy_rules if isinstance(r, str) and r]
        if out:
            return out

    single = legacy.get("triggered_rule")
    if isinstance(single, str) and single:
        return [single]

    return []


def _pick_state_impossibility_scores(
    legacy: dict[str, Any],
) -> dict[str, Any]:
    """Internal: passthrough ``state_impossibility_scores`` if dict; else
    ``{}``."""
    candidate = legacy.get("state_impossibility_scores")
    if isinstance(candidate, dict):
        return candidate
    return {}


def _pick_false_exclusion_risk(legacy: dict[str, Any]) -> str:
    """Internal: prefer ``legacy["false_exclusion_risk"]`` if in
    VALID_FALSE_EXCLUSION_RISK; else ``"unknown"``. The validator allows
    only the four enum values, so anything else falls back to a safe
    self-risk label rather than surfacing a hard error from a missing
    field."""
    candidate = legacy.get("false_exclusion_risk")
    if candidate in VALID_FALSE_EXCLUSION_RISK:
        return candidate
    return "unknown"


def _pick_evidence(legacy: dict[str, Any]) -> dict[str, Any] | list[Any]:
    """Internal: prefer ``evidence`` when present; otherwise fall back to
    ``key_observations`` then ``basis``. Default ``{}``."""
    for key in ("evidence", "key_observations", "basis"):
        candidate = legacy.get(key)
        if isinstance(candidate, (dict, list)):
            return candidate
    return {}


def _pick_rationale(legacy: dict[str, Any]) -> str | list[Any]:
    """Internal: prefer ``rationale``; otherwise ``reason`` /
    ``explanation`` / ``summary``. Default ``[]``."""
    for key in ("rationale", "reason", "explanation", "summary"):
        candidate = legacy.get(key)
        if isinstance(candidate, (str, list)):
            return candidate
    return []


def _pick_warnings(legacy: dict[str, Any]) -> list[Any]:
    """Internal: passthrough ``warnings`` if list; else ``[]``."""
    candidate = legacy.get("warnings")
    if isinstance(candidate, list):
        return candidate
    return []


def _pick_peer_alignment_summary(legacy: dict[str, Any]) -> dict[str, Any]:
    """Internal: prefer ``peer_alignment_summary`` if dict; else fall
    back to legacy ``peer_alignment`` (which legacy
    ``run_exclusion_layer`` emits at top level). Default ``{}``."""
    candidate = legacy.get("peer_alignment_summary")
    if isinstance(candidate, dict):
        return candidate
    candidate = legacy.get("peer_alignment")
    if isinstance(candidate, dict):
        return candidate
    return {}


def build_exclusion_result_from_legacy(
    legacy_exclusion: dict[str, Any],
    *,
    symbol: str,
    feature_snapshot_ref: str | dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble an ``exclusion_result.v1`` payload from a legacy
    exclusion_layer output dict.

    Returns a dict ``{"payload": <exclusion_result.v1>,
    "validation_errors": [...]}``. ``validation_errors`` is the
    unchanged return of ``validate_exclusion_result(payload)`` — empty
    list on success, otherwise a list of human-readable strings carrying
    the validator's stable prefixes (``"missing section: ..."``,
    ``"invalid value: ..."``, etc.).

    The function never mutates ``legacy_exclusion`` (all mutable
    sections that flow through are deep-copied before being placed in
    the returned payload). It never raises business errors.

    Per 18J §7 + 16F no-patching, the function is a **pure translator**:
    it does not auto-fill missing sections, re-run exclusion logic,
    re-derive ``triggered_rules`` from features, or compute
    ``false_exclusion_risk``. Any contract violation surfaces in
    ``validation_errors`` for the caller to handle explicitly.
    """
    legacy = legacy_exclusion if isinstance(legacy_exclusion, dict) else {}

    most_unlikely_state = _extract_most_unlikely_state(legacy)
    excluded_states = _build_excluded_states(legacy, most_unlikely_state)
    ranked_unlikely_states = _build_ranked_unlikely_states(
        legacy, excluded_states, most_unlikely_state
    )
    triggered_rules = _build_triggered_rules(legacy)
    state_impossibility_scores = _pick_state_impossibility_scores(legacy)
    false_exclusion_risk = _pick_false_exclusion_risk(legacy)

    payload: dict[str, Any] = {
        "schema_version": EXCLUSION_RESULT_SCHEMA_VERSION,
        "kind": EXCLUSION_RESULT_KIND,
        "symbol": symbol,
        "ready": legacy.get("ready", True),
        "most_unlikely_state": most_unlikely_state,
        "ranked_unlikely_states": ranked_unlikely_states,
        "state_impossibility_scores": deepcopy(state_impossibility_scores),
        "excluded_states": excluded_states,
        "triggered_rules": triggered_rules,
        "false_exclusion_risk": false_exclusion_risk,
        "evidence": deepcopy(_pick_evidence(legacy)),
        "rationale": deepcopy(_pick_rationale(legacy)),
        "warnings": deepcopy(_pick_warnings(legacy)),
        "feature_snapshot_ref": deepcopy(feature_snapshot_ref),
        "peer_alignment_summary": deepcopy(
            _pick_peer_alignment_summary(legacy)
        ),
        "non_mutation_confirmations": dict(_NON_MUTATION_DEFAULTS),
    }

    return {
        "payload": payload,
        "validation_errors": validate_exclusion_result(payload),
    }
