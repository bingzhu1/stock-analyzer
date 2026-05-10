"""Pure-function validator for the ``evaluation_result.v1`` contract
(Step 18H / PR-EVAL-1).

Spec source of truth:

- `tasks/record_1_0_architecture_reset_canonical_principles.md` §8 (Branch 8)
- `tasks/record_17l_evaluation_layer_rebuild_plan.md` §8 / §13 / §15
- `tasks/record_18a_first_layer_based_implementation_batch_selection.md` §13

Status (per 17L §15 / 18A §11):

- This module is the **Evaluation Layer (Branch 8) output contract**
  introduced as PR-EVAL-1, the seventh batch of layer-based implementation
  PRs after the 17D ~ 17M nine-branch plans landed.
- It is **not yet wired into any active path**. Producers (notably
  ``services.contract_outcome_correlation``,
  ``services.three_system_replay_audit``,
  ``services.historical_replay_training``,
  ``services.regime_validation_helper``,
  ``services.active_rule_pool_calibration``,
  ``services.contract_payload_inspector``,
  ``services.contract_payload_diff``,
  ``services.contract_payload_trend``,
  ``services.contract_payload_extras_dashboard``,
  ``services.anti_false_exclusion_dashboard``) continue to emit their
  existing dict shapes; alignment to ``evaluation_result.v1`` is deferred
  to PR-EVAL-3 / PR-EVAL-4 / later batches.

Boundary contract (1.0 / 16A / 16C / 16F / 17L):

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
  ``services.contract_outcome_correlation``,
  ``services.three_system_replay_audit``,
  ``services.historical_replay_training``,
  ``services.regime_validation_helper``,
  ``services.active_rule_pool_calibration``,
  ``services.contract_payload_inspector``,
  ``services.contract_payload_diff``,
  ``services.contract_payload_trend``,
  ``services.contract_payload_extras_dashboard``,
  ``services.anti_false_exclusion_dashboard``,
  ``services.primary_bias_diagnosis``, ``services.outcome_capture``,
  ``matcher``, ``services.main_projection_layer``,
  ``services.exclusion_layer``, ``services.peer_alignment``,
  ``services.confidence_evaluator``, ``services.final_decision``,
  ``services.consistency_layer``, ``services.review_orchestrator``,
  ``services.feature_payload_contract``,
  ``services.projection_result_contract``,
  ``services.exclusion_result_contract``,
  ``services.confidence_result_contract``,
  ``services.final_report_result_contract``,
  ``services.review_result_contract``,
  ``services.standard_projection_payload``, ``ui.*``, ``app``, any DB /
  sqlite, ``yfinance``.
- It **must not** create, infer, or modify any payload field. It also
  **must not** compute accuracy / win-rate / calibration / read
  historical results / call replay / calibration / dashboard modules.

Error message shapes (stable; tests rely on the prefix):

    invalid type: payload expected dict
    invalid type: <field> expected <type>
    invalid value: schema_version expected 'evaluation_result.v1'
    invalid value: kind expected 'evaluation'
    invalid value: symbol expected non-empty string
    invalid value: evaluation_id expected non-empty str/int
    invalid value: evaluation_type expected one of [...]
    invalid value: sample_count expected int >= 0
    invalid value: holdout_touch_status expected one of [...]
    invalid value: status expected one of [...]
    invalid value: <block>.raw_artifacts_tracked expected False
    invalid value: anti_lookahead_confirmations.<key> expected True
    invalid value: non_mutation_confirmations.<key> expected True
    missing section: <section>
    missing field: artifact_manifest.<key>
    missing field: anti_lookahead_confirmations.<key>
    missing field: non_mutation_confirmations.<key>
    forbidden field: <field> at <location>

Public API:

- ``EVALUATION_RESULT_SCHEMA_VERSION`` — the canonical schema version string.
- ``EVALUATION_RESULT_KIND`` — the canonical ``kind`` value
  (``"evaluation"``).
- ``EVALUATION_RESULT_SECTIONS`` — the 26 top-level keys, in fixed order.
- ``VALID_EVALUATION_TYPES`` — accepted values for ``evaluation_type``
  (8 values: replay / validation / calibration / audit / trend / diff /
  correlation / extras_dashboard).
- ``VALID_HOLDOUT_TOUCH_STATUS`` — accepted values for
  ``holdout_touch_status`` (4 values: untouched / validated_only /
  violated / unknown).
- ``VALID_STATUS`` — accepted values for ``status`` (5 values: ok /
  partial / skipped / error / not_ready).
- ``FORBIDDEN_FIELDS`` — keys that are never allowed at top level
  (raw upstream sections + Branch 3/4/5 verdict fields + downstream
  result sections + legacy bridge fields + rule-promotion fields +
  trading / hard / forced / required tokens + raw artifact dump fields).
- ``validate_evaluation_result(payload)`` — return ``[]`` on success,
  otherwise a list of human-readable error strings.
"""

from __future__ import annotations

from typing import Any


EVALUATION_RESULT_SCHEMA_VERSION: str = "evaluation_result.v1"

# 1.0 / 17L canonical ``kind`` for this contract.
EVALUATION_RESULT_KIND: str = "evaluation"

# 26 top-level keys (18A §13 / 17L §13). Order is fixed.
EVALUATION_RESULT_SECTIONS: tuple[str, ...] = (
    "schema_version",
    "kind",
    "symbol",
    "ready",
    "evaluation_id",
    "evaluation_type",
    "evaluation_timestamp",
    "train_window",
    "validation_window",
    "holdout_window",
    "data_cutoff",
    "sample_count",
    "projection_accuracy",
    "exclusion_hit_rate",
    "false_exclusion_rate",
    "confidence_calibration_summary",
    "final_report_quality_summary",
    "review_lesson_validation_summary",
    "anti_lookahead_confirmations",
    "holdout_touch_status",
    "calibration_output",
    "artifact_manifest",
    "status",
    "warnings",
    "skipped_records",
    "non_mutation_confirmations",
)

# 17L §13 — evaluation_type enum (8 values).
VALID_EVALUATION_TYPES: tuple[str, ...] = (
    "replay",
    "validation",
    "calibration",
    "audit",
    "trend",
    "diff",
    "correlation",
    "extras_dashboard",
)

# 17L §8 — holdout_touch_status enum (4 values).
VALID_HOLDOUT_TOUCH_STATUS: tuple[str, ...] = (
    "untouched",
    "validated_only",
    "violated",
    "unknown",
)

# 17L §13 — status enum (5 values).
VALID_STATUS: tuple[str, ...] = (
    "ok",
    "partial",
    "skipped",
    "error",
    "not_ready",
)

# 17L §13 — required keys inside ``artifact_manifest``. The raw artifacts
# tracked flag must be False (1.0 §11 / 14K / 16H raw artifact policy).
_ARTIFACT_MANIFEST_REQUIRED: tuple[str, ...] = (
    "summary_path",
    "raw_artifacts_tracked",
)

# 17L §8 / §13 — Evaluation Layer must declare it did not leak future
# outcome into any in-sample path nor train on holdout data.
_ANTI_LOOKAHEAD_CONFIRMATIONS_REQUIRED: tuple[str, ...] = (
    "replay_only_used_past_data",
    "outcome_loaded_after_prediction",
    "no_future_outcome_in_features",
    "holdout_not_used_for_training",
)

# 1.0 §6 / §13 / 17L §13 — Evaluation Layer must declare it does not
# mutate prediction / review payloads, does not write active rules, and
# does not run live trading.
_NON_MUTATION_CONFIRMATIONS_REQUIRED: tuple[str, ...] = (
    "evaluation_did_not_mutate_prediction_payload",
    "evaluation_did_not_mutate_review_memory",
    "evaluation_did_not_write_active_rules",
    "evaluation_did_not_run_live_trading",
)

# Forbidden field names at the top level. Anchored to:
#   - 1.0 §6 / §8 (Branch 8 may not output raw upstream sections, verdicts,
#     or trading / hard / forced / required tokens)
#   - 17L §8 + §13 + 18A §13 (forbidden top-level set for evaluation_result.v1)
#
# 18A explicitly forbids rule-promotion fields (``active_rule_promotion`` /
# ``promote_rule``) and raw artifact dump fields (``raw_replay_rows`` /
# ``raw_predictions_dump``) at top level. Calibration outputs may live
# inside ``calibration_output`` as offline summary; rule promotion stays
# outside of the active inference path per 1.0 §6 / 11G OFFLINE_ONLY.
FORBIDDEN_FIELDS: frozenset[str] = frozenset({
    # Raw upstream payload / result sections — Evaluation only carries
    # summary metrics, never raw upstream payload at top level.
    "feature_payload",
    "projection_result",
    "exclusion_result",
    "confidence_result",
    "final_report",
    "review_result",
    # Branch 3 Projection verdict fields
    "most_likely_state",
    "ranked_states",
    "state_probabilities",
    "predicted_top1",
    "predicted_top2",
    # Branch 4 Exclusion verdict fields
    "most_unlikely_state",
    "ranked_unlikely_states",
    "excluded_states",
    "triggered_rules",
    "triggered_rule",
    "false_exclusion_risk",
    # Branch 5 Confidence verdict fields
    "agreement_status",
    "conflict_level",
    "combined_confidence",
    "projection_confidence",
    "exclusion_confidence",
    # Legacy bridge fields
    "final_direction",
    "final_confidence",
    "final_bias",
    "final_projection",
    "primary_projection",
    "peer_adjustment",
    "path_risk",
    # Rule-promotion fields — 18A §13 forbids these (must stay OFFLINE_ONLY)
    "active_rule_promotion",
    "promote_rule",
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
    # Live trading hooks — 18A §13 explicit list
    "live_trade",
    "broker_order",
    # Raw artifact dump fields — 18A §13 explicit list
    "raw_replay_rows",
    "raw_predictions_dump",
})


def validate_evaluation_result(payload: Any) -> list[str]:
    """Validate ``payload`` against ``evaluation_result.v1``.

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

    # Rule 3: every EVALUATION_RESULT_SECTIONS key must be present.
    for section in EVALUATION_RESULT_SECTIONS:
        if section not in payload:
            errors.append(f"missing section: {section}")

    # Rule 2: schema_version must equal EVALUATION_RESULT_SCHEMA_VERSION.
    if "schema_version" in payload:
        if payload["schema_version"] != EVALUATION_RESULT_SCHEMA_VERSION:
            errors.append(
                f"invalid value: schema_version expected "
                f"{EVALUATION_RESULT_SCHEMA_VERSION!r} "
                f"(got {payload['schema_version']!r})"
            )

    # Rule 4: kind must equal "evaluation".
    if "kind" in payload and payload["kind"] != EVALUATION_RESULT_KIND:
        errors.append(
            f"invalid value: kind expected {EVALUATION_RESULT_KIND!r} "
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

    # Rule 7: evaluation_id must be non-empty str OR int (not bool).
    if "evaluation_id" in payload:
        eid = payload["evaluation_id"]
        if isinstance(eid, bool) or not isinstance(eid, (str, int)):
            errors.append(
                f"invalid value: evaluation_id expected non-empty str/int "
                f"(got {type(eid).__name__})"
            )
        elif isinstance(eid, str) and not eid:
            errors.append(
                f"invalid value: evaluation_id expected non-empty str/int "
                f"(got empty string)"
            )

    # Rule 8: evaluation_type must be in VALID_EVALUATION_TYPES.
    if "evaluation_type" in payload:
        et = payload["evaluation_type"]
        if et not in VALID_EVALUATION_TYPES:
            errors.append(
                f"invalid value: evaluation_type expected one of "
                f"{list(VALID_EVALUATION_TYPES)!r} (got {et!r})"
            )

    # Rule 9: evaluation_timestamp must be str or None.
    if "evaluation_timestamp" in payload:
        ts = payload["evaluation_timestamp"]
        if ts is not None and not isinstance(ts, str):
            errors.append(
                f"invalid type: evaluation_timestamp expected str or None "
                f"(got {type(ts).__name__})"
            )

    # Rule 10: train_window / validation_window / holdout_window must be
    # dict or None.
    for window_field in ("train_window", "validation_window", "holdout_window"):
        if window_field in payload:
            value = payload[window_field]
            if value is not None and not isinstance(value, dict):
                errors.append(
                    f"invalid type: {window_field} expected dict or None "
                    f"(got {type(value).__name__})"
                )

    # Rule 11: data_cutoff must be str or None.
    if "data_cutoff" in payload:
        dc = payload["data_cutoff"]
        if dc is not None and not isinstance(dc, str):
            errors.append(
                f"invalid type: data_cutoff expected str or None "
                f"(got {type(dc).__name__})"
            )

    # Rule 12: sample_count must be int >= 0 (and not bool).
    if "sample_count" in payload:
        sc = payload["sample_count"]
        if isinstance(sc, bool) or not isinstance(sc, int):
            errors.append(
                f"invalid value: sample_count expected int >= 0 "
                f"(got {type(sc).__name__})"
            )
        elif sc < 0:
            errors.append(
                f"invalid value: sample_count expected int >= 0 "
                f"(got {sc!r})"
            )

    # Rules 13-18: optional summary dict fields must be dict or None.
    for summary_field in (
        "projection_accuracy",
        "exclusion_hit_rate",
        "false_exclusion_rate",
        "confidence_calibration_summary",
        "final_report_quality_summary",
        "review_lesson_validation_summary",
    ):
        if summary_field in payload:
            value = payload[summary_field]
            if value is not None and not isinstance(value, dict):
                errors.append(
                    f"invalid type: {summary_field} expected dict or None "
                    f"(got {type(value).__name__})"
                )

    # Rules 19 + 20: anti_lookahead_confirmations must be a dict containing
    # the four required keys, each set to True.
    if "anti_lookahead_confirmations" in payload:
        alc = payload["anti_lookahead_confirmations"]
        if not isinstance(alc, dict):
            errors.append(
                f"invalid type: anti_lookahead_confirmations expected dict "
                f"(got {type(alc).__name__})"
            )
        else:
            for key in _ANTI_LOOKAHEAD_CONFIRMATIONS_REQUIRED:
                if key not in alc:
                    errors.append(
                        f"missing field: anti_lookahead_confirmations.{key}"
                    )
                elif alc[key] is not True:
                    errors.append(
                        f"invalid value: anti_lookahead_confirmations.{key} "
                        f"expected True (got {alc[key]!r})"
                    )

    # Rule 21: holdout_touch_status must be in VALID_HOLDOUT_TOUCH_STATUS.
    if "holdout_touch_status" in payload:
        hts = payload["holdout_touch_status"]
        if hts not in VALID_HOLDOUT_TOUCH_STATUS:
            errors.append(
                f"invalid value: holdout_touch_status expected one of "
                f"{list(VALID_HOLDOUT_TOUCH_STATUS)!r} (got {hts!r})"
            )

    # Rule 22: calibration_output must be dict or None.
    if "calibration_output" in payload:
        co = payload["calibration_output"]
        if co is not None and not isinstance(co, dict):
            errors.append(
                f"invalid type: calibration_output expected dict or None "
                f"(got {type(co).__name__})"
            )

    # Rules 23 + 24: artifact_manifest must be a dict containing
    # ``summary_path`` and ``raw_artifacts_tracked``; the latter must be
    # exactly False.
    if "artifact_manifest" in payload:
        am = payload["artifact_manifest"]
        if not isinstance(am, dict):
            errors.append(
                f"invalid type: artifact_manifest expected dict "
                f"(got {type(am).__name__})"
            )
        else:
            for key in _ARTIFACT_MANIFEST_REQUIRED:
                if key not in am:
                    errors.append(f"missing field: artifact_manifest.{key}")
            if "raw_artifacts_tracked" in am:
                rat = am["raw_artifacts_tracked"]
                if rat is not False:
                    errors.append(
                        f"invalid value: artifact_manifest.raw_artifacts_tracked "
                        f"expected False (got {rat!r})"
                    )

    # Rule 25: status must be in VALID_STATUS.
    if "status" in payload:
        status = payload["status"]
        if status not in VALID_STATUS:
            errors.append(
                f"invalid value: status expected one of "
                f"{list(VALID_STATUS)!r} (got {status!r})"
            )

    # Rule 26: warnings must be list.
    if "warnings" in payload and not isinstance(payload["warnings"], list):
        errors.append(
            f"invalid type: warnings expected list "
            f"(got {type(payload['warnings']).__name__})"
        )

    # Rule 27: skipped_records must be list.
    if "skipped_records" in payload and not isinstance(
        payload["skipped_records"], list
    ):
        errors.append(
            f"invalid type: skipped_records expected list "
            f"(got {type(payload['skipped_records']).__name__})"
        )

    # Rules 28 + 29: non_mutation_confirmations must be a dict containing
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
