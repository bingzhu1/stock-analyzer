"""Pure-function validator for the ``projection_result.v1`` contract
(Step 18C / PR-PROJ-1).

Spec source of truth:

- `tasks/record_1_0_architecture_reset_canonical_principles.md` §8 (Branch 3)
- `tasks/record_07a_projection_system_contract.md` §3 / §9
- `tasks/record_17g_projection_layer_rebuild_plan.md` §8 / §14
- `tasks/record_18a_first_layer_based_implementation_batch_selection.md` §13

Status (per 17G §14 / 18A §11 / §12):

- This module is the **Projection Layer (Branch 3) output contract**
  introduced as PR-PROJ-1, the second batch of layer-based implementation
  PRs after the 17D ~ 17M nine-branch plans landed.
- It is **not yet wired into any active path**. Producers (notably
  ``services.main_projection_layer.build_main_projection_layer``) continue
  to emit their existing dict shapes; alignment to ``projection_result.v1``
  is deferred to PR-PROJ-2 / later batches.

Boundary contract (1.0 / 16A / 16C / 16F / 17G):

- This module is a **pure-function shape validator**. It:
  - Never mutates the input payload.
  - Never raises (returns errors as a plain ``list[str]``); even when the
    input is not a dict, it returns a single error string instead of
    raising ``TypeError``.
  - Never reads files / calls external APIs / imports business modules /
    invokes a language-model client / writes to any DB.
- It **must not** import any of: ``predict``, ``services.projection_orchestrator``,
  ``services.projection_orchestrator_v2``, ``services.projection_entrypoint``,
  ``services.projection_v2_adapter``, ``services.home_terminal_orchestrator``,
  ``services.main_projection_layer``, ``services.exclusion_layer``,
  ``services.confidence_evaluator``, ``services.final_decision``,
  ``services.review_orchestrator``, ``services.historical_probability``,
  ``services.feature_payload_contract``, ``services.standard_projection_payload``,
  ``ui.*``, ``app``, any DB / sqlite, ``yfinance``.
- It **must not** create, infer, or modify any payload field. It also
  **must not** compute probabilities / read feature_payload / call
  historical_probability / call main_projection_layer.

Error message shapes (stable; tests rely on the prefix):

    invalid type: payload expected dict
    invalid type: <field> expected <type>
    invalid value: schema_version expected 'projection_result.v1'
    invalid value: kind expected 'projection'
    invalid value: symbol expected non-empty string
    invalid value: most_likely_state expected one of [...] or None
    invalid value: most_likely_state may be None only when ready=False
    invalid value: ranked_states[i] expected one of [...]
    invalid value: state_probabilities key '<k>' not in [...]
    invalid value: state_probabilities['<k>'] expected within [0, 1]
    invalid value: non_mutation_confirmations.<key> expected True
    missing section: <section>
    missing field: non_mutation_confirmations.<key>
    warning: state_probabilities sum expected near 1.0
    forbidden field: <field> at <location>

The ``warning:`` prefix is reserved for non-blocking advisories that
callers can filter out (e.g. probability sums that round-trip to 0.99
or 1.01). Strict shape failures use the other prefixes.

Public API:

- ``PROJECTION_RESULT_SCHEMA_VERSION`` — the canonical schema version string.
- ``PROJECTION_RESULT_SECTIONS`` — the 15 top-level keys, in fixed order.
- ``PROJECTION_RESULT_KIND`` — the canonical ``kind`` value (``"projection"``).
- ``VALID_STATES`` — the five-state vocabulary
  (``"大涨"`` / ``"小涨"`` / ``"震荡"`` / ``"小跌"`` / ``"大跌"``).
- ``FORBIDDEN_FIELDS`` — keys that are never allowed at top level
  (downstream system result sections + Branch 4 exclusion fields +
  legacy bridge fields + legacy ``predicted_top1`` / ``predicted_top2``
  alias + trading / hard / forced / required tokens).
- ``validate_projection_result(payload)`` — return ``[]`` on success,
  otherwise a list of human-readable error / warning strings.
"""

from __future__ import annotations

from typing import Any


PROJECTION_RESULT_SCHEMA_VERSION: str = "projection_result.v1"

# 15 top-level keys (18A §13 / 17G §8). Order is fixed.
PROJECTION_RESULT_SECTIONS: tuple[str, ...] = (
    "schema_version",
    "kind",
    "symbol",
    "ready",
    "most_likely_state",
    "ranked_states",
    "state_probabilities",
    "evidence",
    "rationale",
    "raw_score",
    "warnings",
    "feature_snapshot_ref",
    "historical_match_summary",
    "peer_alignment_summary",
    "non_mutation_confirmations",
)

# 1.0 / 07A canonical ``kind`` for this contract.
PROJECTION_RESULT_KIND: str = "projection"

# Five-state vocabulary (1.0 §8 / 07A §9 / 17G §8). Fixed order matches the
# project-wide convention (大涨 → 大跌, descending bullishness).
VALID_STATES: tuple[str, ...] = ("大涨", "小涨", "震荡", "小跌", "大跌")

# 07A §3.2 / 17G §8 / 17C PR-D — Projection Layer must declare it does not
# read downstream system outputs nor future outcomes. The producer-side
# (PR-PROJ-2) sets all four to True; the validator only checks shape +
# value.
_NON_MUTATION_CONFIRMATIONS_REQUIRED: tuple[str, ...] = (
    "projection_did_not_read_exclusion",
    "projection_did_not_read_confidence",
    "projection_did_not_read_final_report",
    "projection_did_not_read_future_outcome",
)

# Tolerance for the ``state_probabilities`` sum advisory. 0.05 is generous
# enough to accept rounding through 1e-2 but tight enough to catch 0.5 or
# 1.5 mistakes.
_STATE_PROBABILITIES_SUM_TOLERANCE: float = 0.05

# Forbidden field names at the top level. Anchored to:
#   - 1.0 §6 / §8 (Branch 3 may not output exclusion / confidence / final /
#     trading / hard / forced / required)
#   - 07A §3.2 (Projection must not output ``most_unlikely_state`` etc.)
#   - 17G §8.4 + 18A §13 (forbidden top-level set for projection_result.v1)
#
# 18A explicitly prefers Option A for ``predicted_top1`` / ``predicted_top2``
# legacy alias: forbid them at top level. Producers may keep them in their
# own internal dict for legacy callers, but ``projection_result.v1`` does
# not carry them.
FORBIDDEN_FIELDS: frozenset[str] = frozenset({
    # Branch 4 Exclusion fields — Projection must not output them
    "most_unlikely_state",
    "ranked_unlikely_states",
    "excluded_states",
    "triggered_rules",
    "false_exclusion_risk",
    # Downstream system result sections
    "exclusion_result",
    "confidence_result",
    "final_report",
    "review_result",
    "evaluation_result",
    # Legacy bridge fields (07A §3.2 / 17G §8.4)
    "final_direction",
    "final_confidence",
    "final_bias",
    "final_projection",
    "primary_projection",
    "peer_adjustment",
    "path_risk",
    # Legacy interim alias — 18A §13 Option A (forbid at top level)
    "predicted_top1",
    "predicted_top2",
    # Trading actions / execution
    "trading_action",
    "order",
    "position_action",
    "execution",
    "simulated_trade",
    # Trading directions
    "buy",
    "sell",
    "hold",
    # Forced / hard semantics
    "hard",
    "forced",
    "required",
})


def validate_projection_result(payload: Any) -> list[str]:
    """Validate ``payload`` against ``projection_result.v1``.

    Returns ``[]`` on success; otherwise a list of human-readable error
    or warning strings. Never raises. Never mutates ``payload``.

    See module docstring for the full set of error / warning prefixes.
    """
    errors: list[str] = []

    # Rule 1: payload must be a dict.
    if not isinstance(payload, dict):
        return [
            f"invalid type: payload expected dict (got {type(payload).__name__})"
        ]

    # Rule 3: every PROJECTION_RESULT_SECTIONS key must be present.
    for section in PROJECTION_RESULT_SECTIONS:
        if section not in payload:
            errors.append(f"missing section: {section}")

    # Rule 2: schema_version must equal PROJECTION_RESULT_SCHEMA_VERSION.
    if "schema_version" in payload:
        if payload["schema_version"] != PROJECTION_RESULT_SCHEMA_VERSION:
            errors.append(
                f"invalid value: schema_version expected "
                f"{PROJECTION_RESULT_SCHEMA_VERSION!r} "
                f"(got {payload['schema_version']!r})"
            )

    # Rule 4: kind must equal "projection".
    if "kind" in payload and payload["kind"] != PROJECTION_RESULT_KIND:
        errors.append(
            f"invalid value: kind expected {PROJECTION_RESULT_KIND!r} "
            f"(got {payload['kind']!r})"
        )

    # Rule 5: symbol must be a non-empty string.
    if "symbol" in payload:
        sym = payload["symbol"]
        if not isinstance(sym, str) or not sym:
            errors.append(
                f"invalid value: symbol expected non-empty string "
                f"(got {sym!r})"
            )

    # Rule 6: ready must be a bool.
    if "ready" in payload and not isinstance(payload["ready"], bool):
        errors.append(
            f"invalid type: ready expected bool "
            f"(got {type(payload['ready']).__name__})"
        )

    # Rule 7: most_likely_state must be in VALID_STATES, or None when
    # ready=False.
    if "most_likely_state" in payload:
        mls = payload["most_likely_state"]
        ready = payload.get("ready")
        if mls is None:
            if ready is not False:
                errors.append(
                    "invalid value: most_likely_state may be None only when ready=False"
                )
        elif mls not in VALID_STATES:
            errors.append(
                f"invalid value: most_likely_state expected one of "
                f"{list(VALID_STATES)!r} or None (got {mls!r})"
            )

    # Rule 8 + 9: ranked_states must be a list whose elements are in
    # VALID_STATES (when non-empty).
    if "ranked_states" in payload:
        rs = payload["ranked_states"]
        if not isinstance(rs, list):
            errors.append(
                f"invalid type: ranked_states expected list "
                f"(got {type(rs).__name__})"
            )
        else:
            for index, element in enumerate(rs):
                if element not in VALID_STATES:
                    errors.append(
                        f"invalid value: ranked_states[{index}] expected "
                        f"one of {list(VALID_STATES)!r} (got {element!r})"
                    )

    # Rules 10 + 11 + 12 + 13: state_probabilities checks.
    if "state_probabilities" in payload:
        sp = payload["state_probabilities"]
        if not isinstance(sp, dict):
            errors.append(
                f"invalid type: state_probabilities expected dict "
                f"(got {type(sp).__name__})"
            )
        else:
            # Rule 11: keys must be valid states.
            for key in sp:
                if key not in VALID_STATES:
                    errors.append(
                        f"invalid value: state_probabilities key {key!r} "
                        f"not in {list(VALID_STATES)!r}"
                    )
            # Rule 12: values must be int/float in [0, 1].
            for key, value in sp.items():
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    errors.append(
                        f"invalid type: state_probabilities[{key!r}] expected "
                        f"int/float (got {type(value).__name__})"
                    )
                elif value < 0 or value > 1:
                    errors.append(
                        f"invalid value: state_probabilities[{key!r}] "
                        f"expected within [0, 1] (got {value!r})"
                    )
            # Rule 13: sum near 1.0 (warning only). Skip if any non-numeric
            # values already produced a hard error above.
            if sp:
                numeric_values = [
                    v for v in sp.values()
                    if isinstance(v, (int, float)) and not isinstance(v, bool)
                ]
                if len(numeric_values) == len(sp):
                    total = sum(numeric_values)
                    if abs(total - 1.0) > _STATE_PROBABILITIES_SUM_TOLERANCE:
                        errors.append(
                            f"warning: state_probabilities sum expected near "
                            f"1.0 (got {total!r})"
                        )

    # Rule 14: evidence must be dict or list.
    if "evidence" in payload:
        evidence = payload["evidence"]
        if not isinstance(evidence, (dict, list)):
            errors.append(
                f"invalid type: evidence expected dict or list "
                f"(got {type(evidence).__name__})"
            )

    # Rule 15: rationale must be str or list.
    if "rationale" in payload:
        rationale = payload["rationale"]
        if not isinstance(rationale, (str, list)):
            errors.append(
                f"invalid type: rationale expected str or list "
                f"(got {type(rationale).__name__})"
            )

    # Rule 16: raw_score must be int / float / None.
    if "raw_score" in payload:
        raw_score = payload["raw_score"]
        if raw_score is not None and (
            isinstance(raw_score, bool)
            or not isinstance(raw_score, (int, float))
        ):
            errors.append(
                f"invalid type: raw_score expected int/float/None "
                f"(got {type(raw_score).__name__})"
            )

    # Rule 17: warnings must be a list.
    if "warnings" in payload and not isinstance(payload["warnings"], list):
        errors.append(
            f"invalid type: warnings expected list "
            f"(got {type(payload['warnings']).__name__})"
        )

    # Rule 18: feature_snapshot_ref must be str / dict / None.
    if "feature_snapshot_ref" in payload:
        ref = payload["feature_snapshot_ref"]
        if ref is not None and not isinstance(ref, (str, dict)):
            errors.append(
                f"invalid type: feature_snapshot_ref expected str/dict/None "
                f"(got {type(ref).__name__})"
            )

    # Rule 19: historical_match_summary must be a dict.
    if "historical_match_summary" in payload:
        hms = payload["historical_match_summary"]
        if not isinstance(hms, dict):
            errors.append(
                f"invalid type: historical_match_summary expected dict "
                f"(got {type(hms).__name__})"
            )

    # Rule 20: peer_alignment_summary must be a dict.
    if "peer_alignment_summary" in payload:
        pas = payload["peer_alignment_summary"]
        if not isinstance(pas, dict):
            errors.append(
                f"invalid type: peer_alignment_summary expected dict "
                f"(got {type(pas).__name__})"
            )

    # Rule 21 + 22: non_mutation_confirmations must be a dict containing
    # the four required keys, each set to True.
    if "non_mutation_confirmations" in payload:
        nmc = payload["non_mutation_confirmations"]
        if not isinstance(nmc, dict):
            errors.append(
                f"invalid type: non_mutation_confirmations expected dict "
                f"(got {type(nmc).__name__})"
            )
        else:
            for key in _NON_MUTATION_CONFIRMATIONS_REQUIRED:
                if key not in nmc:
                    errors.append(
                        f"missing field: non_mutation_confirmations.{key}"
                    )
                elif nmc[key] is not True:
                    errors.append(
                        f"invalid value: non_mutation_confirmations.{key} "
                        f"expected True (got {nmc[key]!r})"
                    )

    # Forbidden field names at the top level. The validator is read-only
    # (does not write back), so this is the only enforcement point for
    # 18A §13 forbidden tokens.
    _check_forbidden_fields(payload, location="top-level", errors=errors)

    return errors


def _check_forbidden_fields(
    container: dict[str, Any],
    *,
    location: str,
    errors: list[str],
) -> None:
    """Internal: append ``forbidden field: <field> at <location>`` for
    every key in ``container`` that is in ``FORBIDDEN_FIELDS``."""
    for key in container:
        if key in FORBIDDEN_FIELDS:
            errors.append(f"forbidden field: {key} at {location}")
