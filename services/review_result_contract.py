"""Pure-function validator for the ``review_result.v1`` contract
(Step 18G / PR-REVIEW-1).

Spec source of truth:

- `tasks/record_1_0_architecture_reset_canonical_principles.md` §8 (Branch 7)
- `tasks/record_06_three_system_independence_principle.md` §6 / §7
- `tasks/record_17k_review_learning_layer_rebuild_plan.md` §12 / §15
- `tasks/record_18a_first_layer_based_implementation_batch_selection.md` §13

Status (per 17K §15 / 18A §11):

- This module is the **Review & Learning Layer (Branch 7) output contract**
  introduced as PR-REVIEW-1, the sixth batch of layer-based implementation
  PRs after the 17D ~ 17M nine-branch plans landed.
- It is **not yet wired into any active path**. Producers (notably
  ``services.review_orchestrator``, ``services.review_classifier``,
  ``services.review_comparator``) continue to emit their existing dict
  shapes; alignment to ``review_result.v1`` is deferred to later batches.
- 18A explicitly defers ``predict._apply_briefing_caution`` rewrite
  (PR-REVIEW-2) to a later batch; this contract module is read-only and
  does not change ``_apply_briefing_caution`` behavior.

Boundary contract (1.0 / 16A / 16C / 16F / 17K):

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
  ``services.review_orchestrator``, ``services.review_store``,
  ``services.review_agent``, ``services.review_center``,
  ``services.review_analyzer``, ``services.review_classifier``,
  ``services.review_comparator``, ``services.outcome_capture``,
  ``services.memory_store``, ``services.memory_feedback``,
  ``services.projection_memory_briefing``, ``services.pre_prediction_briefing``,
  ``services.exclusion_reliability_review``, ``services.anti_false_exclusion_audit``,
  ``services.projection_review_closed_loop``, ``services.main_projection_layer``,
  ``services.exclusion_layer``, ``services.peer_alignment``,
  ``services.confidence_evaluator``, ``services.final_decision``,
  ``services.consistency_layer``, ``services.feature_payload_contract``,
  ``services.projection_result_contract``, ``services.exclusion_result_contract``,
  ``services.confidence_result_contract``, ``services.final_report_result_contract``,
  ``services.standard_projection_payload``, ``ui.*``, ``app``, any DB /
  sqlite, ``yfinance``.
- It **must not** create, infer, or modify any payload field. It also
  **must not** compute ``correctness`` / ``error_type`` / read actual
  outcome / write memory_updates / call review / memory / outcome
  modules.

Error message shapes (stable; tests rely on the prefix):

    invalid type: payload expected dict
    invalid type: <field> expected <type>
    invalid value: schema_version expected 'review_result.v1'
    invalid value: kind expected 'review'
    invalid value: symbol expected non-empty string
    invalid value: prediction_id expected non-empty str/int
    invalid value: projected_state expected one of [...] or None
    invalid value: excluded_states[i] expected one of [...]
    invalid value: correctness expected one of [...]
    invalid value: error_type expected one of [...]
    invalid value: non_mutation_confirmations.<key> expected True
    missing section: <section>
    missing field: non_mutation_confirmations.<key>
    forbidden field: <field> at <location>

Public API:

- ``REVIEW_RESULT_SCHEMA_VERSION`` — the canonical schema version string.
- ``REVIEW_RESULT_KIND`` — the canonical ``kind`` value (``"review"``).
- ``REVIEW_RESULT_SECTIONS`` — the 25 top-level keys, in fixed order.
- ``VALID_STATES`` — the five-state vocabulary
  (``"大涨"`` / ``"小涨"`` / ``"震荡"`` / ``"小跌"`` / ``"大跌"``).
- ``VALID_CORRECTNESS`` — accepted values for ``correctness``
  (``"correct"`` / ``"incorrect"`` / ``"partial"`` / ``"unknown"`` /
  ``"not_ready"``).
- ``VALID_ERROR_TYPES`` — accepted values for ``error_type``
  (``"none"`` / ``"projection_error"`` / ``"exclusion_error"`` /
  ``"confidence_error"`` / ``"final_report_error"`` / ``"data_issue"`` /
  ``"mixed"`` / ``"unknown"``).
- ``FORBIDDEN_FIELDS`` — keys that are never allowed at top level
  (raw upstream sections + Branch 3/4/5 verdict fields + downstream
  result sections + legacy bridge fields + trading / hard / forced /
  required tokens + review-specific mutation hooks).
- ``validate_review_result(payload)`` — return ``[]`` on success,
  otherwise a list of human-readable error strings.
"""

from __future__ import annotations

from typing import Any


REVIEW_RESULT_SCHEMA_VERSION: str = "review_result.v1"

# 1.0 / 06 / 17K canonical ``kind`` for this contract.
REVIEW_RESULT_KIND: str = "review"

# 25 top-level keys (18A §13 / 17K §12). Order is fixed.
REVIEW_RESULT_SECTIONS: tuple[str, ...] = (
    "schema_version",
    "kind",
    "symbol",
    "ready",
    "prediction_id",
    "prediction_date",
    "target_date",
    "review_timestamp",
    "projected_state",
    "excluded_states",
    "confidence_level",
    "final_summary_snapshot",
    "actual_outcome",
    "correctness",
    "error_type",
    "missed_signals",
    "false_exclusion_notes",
    "false_confidence_notes",
    "confidence_calibration_notes",
    "lesson_candidates",
    "rule_candidates",
    "memory_updates",
    "review_summary",
    "reviewer",
    "non_mutation_confirmations",
)

# Five-state vocabulary (1.0 §8 / 17K §12). Fixed order matches the
# project-wide convention (大涨 → 大跌, descending bullishness).
VALID_STATES: tuple[str, ...] = ("大涨", "小涨", "震荡", "小跌", "大跌")

# 17K §12 — correctness enum.
VALID_CORRECTNESS: tuple[str, ...] = (
    "correct",
    "incorrect",
    "partial",
    "unknown",
    "not_ready",
)

# 17K §12 — error_type enum (8 values).
VALID_ERROR_TYPES: tuple[str, ...] = (
    "none",
    "projection_error",
    "exclusion_error",
    "confidence_error",
    "final_report_error",
    "data_issue",
    "mixed",
    "unknown",
)

# 06 / 07A §3.2 / 07B §3.2 / 07C §3.3 / 07D §11 / 17K §12 — Review &
# Learning Layer must declare it does not mutate any of the four upstream
# system results, and does not affect the current prediction nor leak
# future outcomes back into the current prediction path.
_NON_MUTATION_CONFIRMATIONS_REQUIRED: tuple[str, ...] = (
    "review_did_not_mutate_projection_result",
    "review_did_not_mutate_exclusion_result",
    "review_did_not_mutate_confidence_result",
    "review_did_not_mutate_final_report",
    "review_did_not_affect_current_prediction",
    "review_did_not_use_future_outcome_for_current_prediction",
)

# Forbidden field names at the top level. Anchored to:
#   - 1.0 §6 / §8 (Branch 7 may not output raw upstream sections, verdicts,
#     or trading / hard / forced / required tokens)
#   - 06 §6 / §7 / 07A §3.2 / 07B §3.2 / 07C §3.3 (Review only learns
#     after the fact; must not write back to projection / exclusion /
#     confidence / final_report)
#   - 17K §12 + 18A §13 (forbidden top-level set for review_result.v1)
#
# 18A explicitly forbids review-specific mutation hooks at top level
# (``current_prediction_mutated`` / ``briefing_mutated_confidence`` /
# ``memory_forced_decision``). These are exactly the kinds of fields a
# producer-side bug could introduce when bridging into the current
# prediction path; the contract makes them an explicit shape failure.
FORBIDDEN_FIELDS: frozenset[str] = frozenset({
    # Raw upstream payload / result sections — Review only carries
    # snapshot fields, never raw upstream payload at top level.
    "feature_payload",
    "projection_result",
    "exclusion_result",
    "confidence_result",
    "final_report",
    "evaluation_result",
    # Branch 3 Projection verdict fields (must live inside
    # ``projected_state`` snapshot or absent entirely)
    "most_likely_state",
    "ranked_states",
    "state_probabilities",
    "predicted_top1",
    "predicted_top2",
    # Branch 4 Exclusion verdict fields (must live inside
    # ``excluded_states`` snapshot or absent entirely)
    "most_unlikely_state",
    "ranked_unlikely_states",
    "triggered_rules",
    "triggered_rule",
    "false_exclusion_risk",
    # Branch 5 Confidence verdict fields (must live inside
    # ``confidence_level`` snapshot or absent entirely)
    "agreement_status",
    "conflict_level",
    "combined_confidence",
    "projection_confidence",
    "exclusion_confidence",
    # Legacy bridge fields — 18A §13 forbids these at top level
    "final_direction",
    "final_confidence",
    "final_bias",
    "final_projection",
    "primary_projection",
    "peer_adjustment",
    "path_risk",
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
    # Review-specific mutation hooks (18A §13 explicit list)
    "current_prediction_mutated",
    "briefing_mutated_confidence",
    "memory_forced_decision",
})


def validate_review_result(payload: Any) -> list[str]:
    """Validate ``payload`` against ``review_result.v1``.

    Returns ``[]`` on success; otherwise a list of human-readable error
    strings. Never raises. Never mutates ``payload``.

    See module docstring for the full set of error prefixes.
    """
    errors: list[str] = []

    # Rule 1: payload must be a dict.
    if not isinstance(payload, dict):
        return [
            f"invalid type: payload expected dict (got {type(payload).__name__})"
        ]

    # Rule 3: every REVIEW_RESULT_SECTIONS key must be present.
    for section in REVIEW_RESULT_SECTIONS:
        if section not in payload:
            errors.append(f"missing section: {section}")

    # Rule 2: schema_version must equal REVIEW_RESULT_SCHEMA_VERSION.
    if "schema_version" in payload:
        if payload["schema_version"] != REVIEW_RESULT_SCHEMA_VERSION:
            errors.append(
                f"invalid value: schema_version expected "
                f"{REVIEW_RESULT_SCHEMA_VERSION!r} "
                f"(got {payload['schema_version']!r})"
            )

    # Rule 4: kind must equal "review".
    if "kind" in payload and payload["kind"] != REVIEW_RESULT_KIND:
        errors.append(
            f"invalid value: kind expected {REVIEW_RESULT_KIND!r} "
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

    # Rule 7: prediction_id must be non-empty str OR int (not bool).
    if "prediction_id" in payload:
        pid = payload["prediction_id"]
        if isinstance(pid, bool) or not isinstance(pid, (str, int)):
            errors.append(
                f"invalid value: prediction_id expected non-empty str/int "
                f"(got {type(pid).__name__})"
            )
        elif isinstance(pid, str) and not pid:
            errors.append(
                f"invalid value: prediction_id expected non-empty str/int "
                f"(got empty string)"
            )

    # Rule 8: prediction_date / target_date / review_timestamp must be
    # str or None.
    for date_field in ("prediction_date", "target_date", "review_timestamp"):
        if date_field in payload:
            value = payload[date_field]
            if value is not None and not isinstance(value, str):
                errors.append(
                    f"invalid type: {date_field} expected str or None "
                    f"(got {type(value).__name__})"
                )

    # Rule 9: projected_state must be in VALID_STATES or None.
    if "projected_state" in payload:
        ps = payload["projected_state"]
        if ps is not None and ps not in VALID_STATES:
            errors.append(
                f"invalid value: projected_state expected one of "
                f"{list(VALID_STATES)!r} or None (got {ps!r})"
            )

    # Rule 10 + 11: excluded_states must be a list of valid states.
    if "excluded_states" in payload:
        es = payload["excluded_states"]
        if not isinstance(es, list):
            errors.append(
                f"invalid type: excluded_states expected list "
                f"(got {type(es).__name__})"
            )
        else:
            for index, element in enumerate(es):
                if element not in VALID_STATES:
                    errors.append(
                        f"invalid value: excluded_states[{index}] expected "
                        f"one of {list(VALID_STATES)!r} (got {element!r})"
                    )

    # Rule 12: confidence_level must be str or None.
    if "confidence_level" in payload:
        cl = payload["confidence_level"]
        if cl is not None and not isinstance(cl, str):
            errors.append(
                f"invalid type: confidence_level expected str or None "
                f"(got {type(cl).__name__})"
            )

    # Rule 13: final_summary_snapshot must be dict / str / None.
    if "final_summary_snapshot" in payload:
        fss = payload["final_summary_snapshot"]
        if fss is not None and not isinstance(fss, (dict, str)):
            errors.append(
                f"invalid type: final_summary_snapshot expected dict, str, "
                f"or None (got {type(fss).__name__})"
            )

    # Rule 14: actual_outcome must be dict / str / None.
    if "actual_outcome" in payload:
        ao = payload["actual_outcome"]
        if ao is not None and not isinstance(ao, (dict, str)):
            errors.append(
                f"invalid type: actual_outcome expected dict, str, or None "
                f"(got {type(ao).__name__})"
            )

    # Rule 15: correctness must be in VALID_CORRECTNESS.
    if "correctness" in payload:
        correctness = payload["correctness"]
        if correctness not in VALID_CORRECTNESS:
            errors.append(
                f"invalid value: correctness expected one of "
                f"{list(VALID_CORRECTNESS)!r} (got {correctness!r})"
            )

    # Rule 16: error_type must be in VALID_ERROR_TYPES.
    if "error_type" in payload:
        et = payload["error_type"]
        if et not in VALID_ERROR_TYPES:
            errors.append(
                f"invalid value: error_type expected one of "
                f"{list(VALID_ERROR_TYPES)!r} (got {et!r})"
            )

    # Rule 17: missed_signals must be list.
    if "missed_signals" in payload and not isinstance(
        payload["missed_signals"], list
    ):
        errors.append(
            f"invalid type: missed_signals expected list "
            f"(got {type(payload['missed_signals']).__name__})"
        )

    # Rules 18 / 19 / 20: notes fields must be list or str.
    for notes_field in (
        "false_exclusion_notes",
        "false_confidence_notes",
        "confidence_calibration_notes",
    ):
        if notes_field in payload:
            value = payload[notes_field]
            if not isinstance(value, (list, str)):
                errors.append(
                    f"invalid type: {notes_field} expected list or str "
                    f"(got {type(value).__name__})"
                )

    # Rules 21 / 22 / 23: candidate-list fields must be list.
    for list_field in ("lesson_candidates", "rule_candidates", "memory_updates"):
        if list_field in payload and not isinstance(payload[list_field], list):
            errors.append(
                f"invalid type: {list_field} expected list "
                f"(got {type(payload[list_field]).__name__})"
            )

    # Rule 24: review_summary must be str or list.
    if "review_summary" in payload:
        rs = payload["review_summary"]
        if not isinstance(rs, (str, list)):
            errors.append(
                f"invalid type: review_summary expected str or list "
                f"(got {type(rs).__name__})"
            )

    # Rule 25: reviewer must be str or dict.
    if "reviewer" in payload:
        reviewer = payload["reviewer"]
        if not isinstance(reviewer, (str, dict)):
            errors.append(
                f"invalid type: reviewer expected str or dict "
                f"(got {type(reviewer).__name__})"
            )

    # Rules 26 + 27: non_mutation_confirmations must be a dict containing
    # the six required keys, each set to True.
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
