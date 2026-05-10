"""Boundary + contract tests for ``services.evaluation_result_contract``
(Step 18H / PR-EVAL-1).

Spec source of truth:

- `tasks/record_1_0_architecture_reset_canonical_principles.md` §8 (Branch 8)
- `tasks/record_17l_evaluation_layer_rebuild_plan.md` §8 / §13 / §15
- `tasks/record_18a_first_layer_based_implementation_batch_selection.md` §13

PR-EVAL-1 is a **pure addition** — a new schema constant + validator with
zero changes to any existing business code. This suite verifies:

1.  valid minimal payload returns ``[]``
2.  non-dict payload returns error (no raise)
3.  wrong ``schema_version`` returns ``invalid value:``
4.  each missing top-level section returns ``missing section:``
5.  ``kind`` must equal ``"evaluation"``
6.  ``symbol`` must be a non-empty string
7.  ``ready`` must be a bool
8.  ``evaluation_id`` must be non-empty str or int
9.  ``evaluation_type`` must be a valid enum
10. ``evaluation_timestamp`` must be str or None
11. ``train_window`` / ``validation_window`` / ``holdout_window`` must
    be dict or None
12. ``data_cutoff`` must be str or None
13. ``sample_count`` must be int >= 0
14. ``projection_accuracy`` must be dict or None
15. ``exclusion_hit_rate`` must be dict or None
16. ``false_exclusion_rate`` must be dict or None
17. ``confidence_calibration_summary`` must be dict or None
18. ``final_report_quality_summary`` must be dict or None
19. ``review_lesson_validation_summary`` must be dict or None
20. missing ``anti_lookahead_confirmations`` required keys returns error
21. ``anti_lookahead_confirmations`` required values must be ``True``
22. ``holdout_touch_status`` must be a valid enum
23. ``calibration_output`` must be dict or None
24. ``artifact_manifest`` must be a dict
25. ``artifact_manifest`` missing ``summary_path`` / ``raw_artifacts_tracked``
    returns error
26. ``artifact_manifest.raw_artifacts_tracked`` must be False
27. ``status`` must be a valid enum
28. ``warnings`` must be a list
29. ``skipped_records`` must be a list
30. missing ``non_mutation_confirmations`` required keys returns error
31. ``non_mutation_confirmations`` required values must be ``True``
32. forbidden upstream result sections rejected
33. forbidden prediction / confidence / final fields rejected
34. forbidden rule promotion fields rejected
35. forbidden trading / hard / forced fields rejected
36. forbidden raw artifact dump fields rejected
37. validator does not mutate input payload
38. module import boundary
39. ``EVALUATION_RESULT_SECTIONS`` matches the expected fixed order
40. ``EVALUATION_RESULT_SCHEMA_VERSION`` equals ``"evaluation_result.v1"``
41. ``EVALUATION_RESULT_KIND`` equals ``"evaluation"``
42. enum constants equal expected values

The validator must never raise (returns errors as a list).
"""

from __future__ import annotations

import copy
import unittest
from pathlib import Path

import services.evaluation_result_contract as erc_mod
from services.evaluation_result_contract import (
    EVALUATION_RESULT_KIND,
    EVALUATION_RESULT_SCHEMA_VERSION,
    EVALUATION_RESULT_SECTIONS,
    FORBIDDEN_FIELDS,
    VALID_EVALUATION_TYPES,
    VALID_HOLDOUT_TOUCH_STATUS,
    VALID_STATUS,
    validate_evaluation_result,
)


_REPO_ROOT = Path(__file__).resolve().parent.parent


def _read(rel: str) -> str:
    return (_REPO_ROOT / rel).read_text(encoding="utf-8")


def _valid_minimal_payload() -> dict:
    """Build a payload that satisfies every PR-EVAL-1 shape rule."""
    return {
        "schema_version": EVALUATION_RESULT_SCHEMA_VERSION,
        "kind": EVALUATION_RESULT_KIND,
        "symbol": "AVGO",
        "ready": True,
        "evaluation_id": "eval-2026-05-08",
        "evaluation_type": "replay",
        "evaluation_timestamp": "2026-05-10T00:00:00Z",
        "train_window": {"start_date": "2016-05-18", "end_date": "2024-12-31"},
        "validation_window": {"start_date": "2025-01-01", "end_date": "2025-12-31"},
        "holdout_window": {"start_date": "2026-01-01", "end_date": None},
        "data_cutoff": "2025-12-31",
        "sample_count": 100,
        "projection_accuracy": None,
        "exclusion_hit_rate": None,
        "false_exclusion_rate": None,
        "confidence_calibration_summary": None,
        "final_report_quality_summary": None,
        "review_lesson_validation_summary": None,
        "anti_lookahead_confirmations": {
            "replay_only_used_past_data": True,
            "outcome_loaded_after_prediction": True,
            "no_future_outcome_in_features": True,
            "holdout_not_used_for_training": True,
        },
        "holdout_touch_status": "untouched",
        "calibration_output": None,
        "artifact_manifest": {
            "summary_path": "logs/historical_training/2026_05_10/summary.md",
            "raw_artifacts_tracked": False,
        },
        "status": "ok",
        "warnings": [],
        "skipped_records": [],
        "non_mutation_confirmations": {
            "evaluation_did_not_mutate_prediction_payload": True,
            "evaluation_did_not_mutate_review_memory": True,
            "evaluation_did_not_write_active_rules": True,
            "evaluation_did_not_run_live_trading": True,
        },
    }


# ---------------------------------------------------------------------------
# 0. Constants (test items 39-42)
# ---------------------------------------------------------------------------

class EvaluationResultConstantsTests(unittest.TestCase):
    def test_schema_version_is_v1(self) -> None:
        self.assertEqual(EVALUATION_RESULT_SCHEMA_VERSION, "evaluation_result.v1")

    def test_kind_is_evaluation(self) -> None:
        self.assertEqual(EVALUATION_RESULT_KIND, "evaluation")

    def test_twenty_six_top_level_sections_in_fixed_order(self) -> None:
        self.assertEqual(
            EVALUATION_RESULT_SECTIONS,
            (
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
            ),
        )

    def test_valid_evaluation_types_enum(self) -> None:
        self.assertEqual(
            VALID_EVALUATION_TYPES,
            (
                "replay",
                "validation",
                "calibration",
                "audit",
                "trend",
                "diff",
                "correlation",
                "extras_dashboard",
            ),
        )

    def test_valid_holdout_touch_status_enum(self) -> None:
        self.assertEqual(
            VALID_HOLDOUT_TOUCH_STATUS,
            ("untouched", "validated_only", "violated", "unknown"),
        )

    def test_valid_status_enum(self) -> None:
        self.assertEqual(
            VALID_STATUS,
            ("ok", "partial", "skipped", "error", "not_ready"),
        )

    def test_forbidden_fields_includes_upstream_raw_sections(self) -> None:
        for required in (
            "feature_payload",
            "projection_result",
            "exclusion_result",
            "confidence_result",
            "final_report",
            "review_result",
        ):
            self.assertIn(
                required, FORBIDDEN_FIELDS,
                msg=f"FORBIDDEN_FIELDS must include {required!r}",
            )

    def test_forbidden_fields_includes_prediction_confidence_final_keys(self) -> None:
        for required in (
            "most_likely_state",
            "most_unlikely_state",
            "agreement_status",
            "combined_confidence",
            "final_direction",
            "final_confidence",
        ):
            self.assertIn(required, FORBIDDEN_FIELDS)

    def test_forbidden_fields_includes_rule_promotion_keys(self) -> None:
        for required in ("active_rule_promotion", "promote_rule"):
            self.assertIn(
                required, FORBIDDEN_FIELDS,
                msg=f"FORBIDDEN_FIELDS must include {required!r}",
            )

    def test_forbidden_fields_includes_trading_and_forced_tokens(self) -> None:
        for required in (
            "trading_action",
            "buy",
            "sell",
            "hold",
            "hard",
            "forced",
            "required",
            "live_trade",
            "broker_order",
        ):
            self.assertIn(required, FORBIDDEN_FIELDS)

    def test_forbidden_fields_includes_raw_artifact_dump_keys(self) -> None:
        for required in ("raw_replay_rows", "raw_predictions_dump"):
            self.assertIn(
                required, FORBIDDEN_FIELDS,
                msg=f"FORBIDDEN_FIELDS must include {required!r}",
            )


# ---------------------------------------------------------------------------
# 1. Valid minimal payload returns []
# ---------------------------------------------------------------------------

class ValidMinimalPayloadTests(unittest.TestCase):
    def test_valid_minimal_payload_returns_empty_list(self) -> None:
        errors = validate_evaluation_result(_valid_minimal_payload())
        self.assertEqual(errors, [], msg=f"unexpected errors: {errors}")

    def test_each_evaluation_type_is_accepted(self) -> None:
        for value in VALID_EVALUATION_TYPES:
            with self.subTest(evaluation_type=value):
                payload = _valid_minimal_payload()
                payload["evaluation_type"] = value
                errors = validate_evaluation_result(payload)
                bad = [e for e in errors if e.startswith("invalid value: evaluation_type")]
                self.assertEqual(bad, [])

    def test_each_holdout_touch_status_is_accepted(self) -> None:
        for value in VALID_HOLDOUT_TOUCH_STATUS:
            with self.subTest(holdout_touch_status=value):
                payload = _valid_minimal_payload()
                payload["holdout_touch_status"] = value
                errors = validate_evaluation_result(payload)
                bad = [e for e in errors if e.startswith("invalid value: holdout_touch_status")]
                self.assertEqual(bad, [])

    def test_each_status_is_accepted(self) -> None:
        for value in VALID_STATUS:
            with self.subTest(status=value):
                payload = _valid_minimal_payload()
                payload["status"] = value
                errors = validate_evaluation_result(payload)
                bad = [e for e in errors if e.startswith("invalid value: status")]
                self.assertEqual(bad, [])

    def test_int_evaluation_id_is_ok(self) -> None:
        payload = _valid_minimal_payload()
        payload["evaluation_id"] = 12345
        errors = validate_evaluation_result(payload)
        self.assertEqual(errors, [])

    def test_optional_summary_fields_may_be_dicts(self) -> None:
        payload = _valid_minimal_payload()
        payload["projection_accuracy"] = {"top1_accuracy": 0.50}
        payload["exclusion_hit_rate"] = {"hit_rate": 0.60}
        payload["false_exclusion_rate"] = {"rate": 0.10}
        payload["confidence_calibration_summary"] = {"brier": 0.20}
        payload["final_report_quality_summary"] = {"coverage": 0.95}
        payload["review_lesson_validation_summary"] = {"validated": 5}
        payload["calibration_output"] = {"weights": {"high": 0.7}}
        errors = validate_evaluation_result(payload)
        self.assertEqual(errors, [])


# ---------------------------------------------------------------------------
# 2. Non-dict payload returns error (no raise)
# ---------------------------------------------------------------------------

class NonDictPayloadTests(unittest.TestCase):
    def test_none_payload(self) -> None:
        errors = validate_evaluation_result(None)
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("invalid type: payload expected dict"))

    def test_list_payload(self) -> None:
        errors = validate_evaluation_result([])
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("invalid type: payload expected dict"))

    def test_str_payload(self) -> None:
        errors = validate_evaluation_result("not a dict")
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("invalid type: payload expected dict"))

    def test_int_payload(self) -> None:
        errors = validate_evaluation_result(42)
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("invalid type: payload expected dict"))

    def test_non_dict_input_does_not_raise(self) -> None:
        for value in (None, 42, "x", [], (), 1.5, object()):
            with self.subTest(value=value):
                result = validate_evaluation_result(value)
                self.assertIsInstance(result, list)


# ---------------------------------------------------------------------------
# 3. Wrong schema_version
# ---------------------------------------------------------------------------

class SchemaVersionTests(unittest.TestCase):
    def test_wrong_schema_version_returns_invalid_value_error(self) -> None:
        payload = _valid_minimal_payload()
        payload["schema_version"] = "evaluation_result.v2"
        errors = validate_evaluation_result(payload)
        matches = [e for e in errors if e.startswith("invalid value: schema_version")]
        self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 4. Missing top-level section
# ---------------------------------------------------------------------------

class MissingTopLevelSectionTests(unittest.TestCase):
    def test_each_missing_section_yields_missing_section_error(self) -> None:
        for section in EVALUATION_RESULT_SECTIONS:
            with self.subTest(section=section):
                payload = _valid_minimal_payload()
                payload.pop(section)
                errors = validate_evaluation_result(payload)
                self.assertIn(
                    f"missing section: {section}",
                    errors,
                    msg=f"validator did not catch missing {section}; got {errors}",
                )


# ---------------------------------------------------------------------------
# 5. kind must equal "evaluation"
# ---------------------------------------------------------------------------

class KindTests(unittest.TestCase):
    def test_wrong_kind_returns_invalid_value_error(self) -> None:
        for bad in ("evaluator", "replay", "review", "", None, 42):
            with self.subTest(kind=bad):
                payload = _valid_minimal_payload()
                payload["kind"] = bad
                errors = validate_evaluation_result(payload)
                matches = [e for e in errors if e.startswith("invalid value: kind")]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 6. symbol must be non-empty string
# ---------------------------------------------------------------------------

class SymbolTests(unittest.TestCase):
    def test_symbol_must_be_non_empty_string(self) -> None:
        for bad in ("", None, 42, [], {}):
            with self.subTest(symbol=bad):
                payload = _valid_minimal_payload()
                payload["symbol"] = bad
                errors = validate_evaluation_result(payload)
                matches = [e for e in errors if e.startswith("invalid value: symbol")]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 7. ready must be bool
# ---------------------------------------------------------------------------

class ReadyTests(unittest.TestCase):
    def test_ready_must_be_bool(self) -> None:
        for bad in (None, 0, 1, "True", "False", []):
            with self.subTest(ready=bad):
                payload = _valid_minimal_payload()
                payload["ready"] = bad
                errors = validate_evaluation_result(payload)
                matches = [e for e in errors if e.startswith("invalid type: ready")]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 8. evaluation_id must be non-empty str or int
# ---------------------------------------------------------------------------

class EvaluationIdTests(unittest.TestCase):
    def test_evaluation_id_str_non_empty_is_ok(self) -> None:
        payload = _valid_minimal_payload()
        payload["evaluation_id"] = "abc-123"
        errors = validate_evaluation_result(payload)
        self.assertEqual(errors, [])

    def test_evaluation_id_int_is_ok(self) -> None:
        payload = _valid_minimal_payload()
        payload["evaluation_id"] = 0
        errors = validate_evaluation_result(payload)
        self.assertEqual(errors, [])

    def test_evaluation_id_empty_string_returns_error(self) -> None:
        payload = _valid_minimal_payload()
        payload["evaluation_id"] = ""
        errors = validate_evaluation_result(payload)
        matches = [e for e in errors if e.startswith("invalid value: evaluation_id")]
        self.assertEqual(len(matches), 1)

    def test_evaluation_id_other_types_return_error(self) -> None:
        for bad in (None, [], {}, 1.5, True):
            with self.subTest(evaluation_id=bad):
                payload = _valid_minimal_payload()
                payload["evaluation_id"] = bad
                errors = validate_evaluation_result(payload)
                matches = [
                    e for e in errors if e.startswith("invalid value: evaluation_id")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 9. evaluation_type must be valid enum
# ---------------------------------------------------------------------------

class EvaluationTypeTests(unittest.TestCase):
    def test_invalid_evaluation_type_returns_error(self) -> None:
        for bad in ("REPLAY", "promotion", "training", "", None, 42):
            with self.subTest(evaluation_type=bad):
                payload = _valid_minimal_payload()
                payload["evaluation_type"] = bad
                errors = validate_evaluation_result(payload)
                matches = [
                    e for e in errors if e.startswith("invalid value: evaluation_type")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 10. evaluation_timestamp must be str or None
# ---------------------------------------------------------------------------

class EvaluationTimestampTests(unittest.TestCase):
    def test_evaluation_timestamp_must_be_str_or_none(self) -> None:
        for bad in (42, 1.5, [], {}):
            with self.subTest(evaluation_timestamp=bad):
                payload = _valid_minimal_payload()
                payload["evaluation_timestamp"] = bad
                errors = validate_evaluation_result(payload)
                matches = [
                    e for e in errors
                    if e.startswith("invalid type: evaluation_timestamp")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 11. train / validation / holdout windows must be dict or None
# ---------------------------------------------------------------------------

class WindowFieldsTests(unittest.TestCase):
    def test_each_window_field_must_be_dict_or_none(self) -> None:
        for window_field in ("train_window", "validation_window", "holdout_window"):
            for bad in ("string", 42, []):
                with self.subTest(field=window_field, value=bad):
                    payload = _valid_minimal_payload()
                    payload[window_field] = bad
                    errors = validate_evaluation_result(payload)
                    matches = [
                        e for e in errors
                        if e.startswith(f"invalid type: {window_field}")
                    ]
                    self.assertEqual(len(matches), 1)

    def test_window_fields_may_be_none(self) -> None:
        payload = _valid_minimal_payload()
        payload["train_window"] = None
        payload["validation_window"] = None
        payload["holdout_window"] = None
        errors = validate_evaluation_result(payload)
        self.assertEqual(errors, [])


# ---------------------------------------------------------------------------
# 12. data_cutoff must be str or None
# ---------------------------------------------------------------------------

class DataCutoffTests(unittest.TestCase):
    def test_data_cutoff_must_be_str_or_none(self) -> None:
        for bad in (42, 1.5, [], {}):
            with self.subTest(data_cutoff=bad):
                payload = _valid_minimal_payload()
                payload["data_cutoff"] = bad
                errors = validate_evaluation_result(payload)
                matches = [
                    e for e in errors if e.startswith("invalid type: data_cutoff")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 13. sample_count must be int >= 0
# ---------------------------------------------------------------------------

class SampleCountTests(unittest.TestCase):
    def test_negative_sample_count_returns_error(self) -> None:
        payload = _valid_minimal_payload()
        payload["sample_count"] = -1
        errors = validate_evaluation_result(payload)
        matches = [e for e in errors if e.startswith("invalid value: sample_count")]
        self.assertEqual(len(matches), 1)

    def test_non_int_sample_count_returns_error(self) -> None:
        for bad in (None, 1.5, "100", [], {}, True):
            with self.subTest(sample_count=bad):
                payload = _valid_minimal_payload()
                payload["sample_count"] = bad
                errors = validate_evaluation_result(payload)
                matches = [
                    e for e in errors if e.startswith("invalid value: sample_count")
                ]
                self.assertEqual(len(matches), 1)

    def test_zero_sample_count_is_ok(self) -> None:
        payload = _valid_minimal_payload()
        payload["sample_count"] = 0
        errors = validate_evaluation_result(payload)
        self.assertEqual(errors, [])


# ---------------------------------------------------------------------------
# 14-19. optional summary fields must be dict or None
# ---------------------------------------------------------------------------

class OptionalSummaryFieldsTests(unittest.TestCase):
    def test_each_optional_summary_must_be_dict_or_none(self) -> None:
        for field in (
            "projection_accuracy",
            "exclusion_hit_rate",
            "false_exclusion_rate",
            "confidence_calibration_summary",
            "final_report_quality_summary",
            "review_lesson_validation_summary",
        ):
            for bad in ("string", 42, [], True):
                with self.subTest(field=field, value=bad):
                    payload = _valid_minimal_payload()
                    payload[field] = bad
                    errors = validate_evaluation_result(payload)
                    matches = [
                        e for e in errors
                        if e.startswith(f"invalid type: {field}")
                    ]
                    self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 20. Missing anti_lookahead_confirmations required keys
# ---------------------------------------------------------------------------

class MissingAntiLookaheadKeysTests(unittest.TestCase):
    def test_each_missing_key_yields_missing_field_error(self) -> None:
        for key in (
            "replay_only_used_past_data",
            "outcome_loaded_after_prediction",
            "no_future_outcome_in_features",
            "holdout_not_used_for_training",
        ):
            with self.subTest(key=key):
                payload = _valid_minimal_payload()
                payload["anti_lookahead_confirmations"].pop(key)
                errors = validate_evaluation_result(payload)
                self.assertIn(
                    f"missing field: anti_lookahead_confirmations.{key}",
                    errors,
                )


# ---------------------------------------------------------------------------
# 21. anti_lookahead_confirmations required values must be True
# ---------------------------------------------------------------------------

class AntiLookaheadValueTests(unittest.TestCase):
    def test_each_required_key_must_be_true(self) -> None:
        for key in (
            "replay_only_used_past_data",
            "outcome_loaded_after_prediction",
            "no_future_outcome_in_features",
            "holdout_not_used_for_training",
        ):
            for bad in (False, None, 0, 1, "true", []):
                with self.subTest(key=key, value=bad):
                    payload = _valid_minimal_payload()
                    payload["anti_lookahead_confirmations"][key] = bad
                    errors = validate_evaluation_result(payload)
                    self.assertTrue(
                        any(
                            e.startswith(
                                f"invalid value: anti_lookahead_confirmations.{key}"
                            )
                            for e in errors
                        ),
                        msg=f"expected error for {key}={bad!r}; got {errors}",
                    )


# ---------------------------------------------------------------------------
# 22. holdout_touch_status must be valid enum
# ---------------------------------------------------------------------------

class HoldoutTouchStatusTests(unittest.TestCase):
    def test_invalid_holdout_touch_status_returns_error(self) -> None:
        for bad in ("UNTOUCHED", "leaked", "", None, 42):
            with self.subTest(holdout_touch_status=bad):
                payload = _valid_minimal_payload()
                payload["holdout_touch_status"] = bad
                errors = validate_evaluation_result(payload)
                matches = [
                    e for e in errors
                    if e.startswith("invalid value: holdout_touch_status")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 23. calibration_output must be dict or None
# ---------------------------------------------------------------------------

class CalibrationOutputTests(unittest.TestCase):
    def test_calibration_output_must_be_dict_or_none(self) -> None:
        for bad in ("string", 42, [], True):
            with self.subTest(calibration_output=bad):
                payload = _valid_minimal_payload()
                payload["calibration_output"] = bad
                errors = validate_evaluation_result(payload)
                matches = [
                    e for e in errors
                    if e.startswith("invalid type: calibration_output")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 24. artifact_manifest must be dict
# ---------------------------------------------------------------------------

class ArtifactManifestTypeTests(unittest.TestCase):
    def test_artifact_manifest_must_be_dict(self) -> None:
        for bad in ([], "string", 42, None):
            with self.subTest(artifact_manifest=bad):
                payload = _valid_minimal_payload()
                payload["artifact_manifest"] = bad
                errors = validate_evaluation_result(payload)
                matches = [
                    e for e in errors
                    if e.startswith("invalid type: artifact_manifest")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 25. artifact_manifest missing summary_path / raw_artifacts_tracked
# ---------------------------------------------------------------------------

class ArtifactManifestRequiredKeysTests(unittest.TestCase):
    def test_missing_summary_path_returns_error(self) -> None:
        payload = _valid_minimal_payload()
        payload["artifact_manifest"].pop("summary_path")
        errors = validate_evaluation_result(payload)
        self.assertIn("missing field: artifact_manifest.summary_path", errors)

    def test_missing_raw_artifacts_tracked_returns_error(self) -> None:
        payload = _valid_minimal_payload()
        payload["artifact_manifest"].pop("raw_artifacts_tracked")
        errors = validate_evaluation_result(payload)
        self.assertIn(
            "missing field: artifact_manifest.raw_artifacts_tracked", errors
        )


# ---------------------------------------------------------------------------
# 26. artifact_manifest.raw_artifacts_tracked must be False
# ---------------------------------------------------------------------------

class ArtifactManifestRawArtifactsTrackedTests(unittest.TestCase):
    def test_raw_artifacts_tracked_must_be_false(self) -> None:
        for bad in (True, None, 0, 1, "false", []):
            with self.subTest(raw_artifacts_tracked=bad):
                payload = _valid_minimal_payload()
                payload["artifact_manifest"]["raw_artifacts_tracked"] = bad
                errors = validate_evaluation_result(payload)
                self.assertTrue(
                    any(
                        e.startswith(
                            "invalid value: artifact_manifest.raw_artifacts_tracked"
                        )
                        for e in errors
                    ),
                    msg=f"expected error for {bad!r}; got {errors}",
                )


# ---------------------------------------------------------------------------
# 27. status must be valid enum
# ---------------------------------------------------------------------------

class StatusTests(unittest.TestCase):
    def test_invalid_status_returns_error(self) -> None:
        for bad in ("OK", "running", "", None, 42):
            with self.subTest(status=bad):
                payload = _valid_minimal_payload()
                payload["status"] = bad
                errors = validate_evaluation_result(payload)
                matches = [e for e in errors if e.startswith("invalid value: status")]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 28. warnings must be list
# ---------------------------------------------------------------------------

class WarningsTypeTests(unittest.TestCase):
    def test_warnings_must_be_list(self) -> None:
        for bad in ({}, "list", 42, None):
            with self.subTest(warnings=bad):
                payload = _valid_minimal_payload()
                payload["warnings"] = bad
                errors = validate_evaluation_result(payload)
                matches = [e for e in errors if e.startswith("invalid type: warnings")]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 29. skipped_records must be list
# ---------------------------------------------------------------------------

class SkippedRecordsTypeTests(unittest.TestCase):
    def test_skipped_records_must_be_list(self) -> None:
        for bad in ({}, "list", 42, None):
            with self.subTest(skipped_records=bad):
                payload = _valid_minimal_payload()
                payload["skipped_records"] = bad
                errors = validate_evaluation_result(payload)
                matches = [
                    e for e in errors if e.startswith("invalid type: skipped_records")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 30. Missing non_mutation_confirmations required keys
# ---------------------------------------------------------------------------

class MissingNonMutationConfirmationKeysTests(unittest.TestCase):
    def test_each_missing_key_yields_missing_field_error(self) -> None:
        for key in (
            "evaluation_did_not_mutate_prediction_payload",
            "evaluation_did_not_mutate_review_memory",
            "evaluation_did_not_write_active_rules",
            "evaluation_did_not_run_live_trading",
        ):
            with self.subTest(key=key):
                payload = _valid_minimal_payload()
                payload["non_mutation_confirmations"].pop(key)
                errors = validate_evaluation_result(payload)
                self.assertIn(
                    f"missing field: non_mutation_confirmations.{key}",
                    errors,
                )


# ---------------------------------------------------------------------------
# 31. non_mutation_confirmations required values must be True
# ---------------------------------------------------------------------------

class NonMutationConfirmationValueTests(unittest.TestCase):
    def test_each_required_key_must_be_true(self) -> None:
        for key in (
            "evaluation_did_not_mutate_prediction_payload",
            "evaluation_did_not_mutate_review_memory",
            "evaluation_did_not_write_active_rules",
            "evaluation_did_not_run_live_trading",
        ):
            for bad in (False, None, 0, 1, "true", []):
                with self.subTest(key=key, value=bad):
                    payload = _valid_minimal_payload()
                    payload["non_mutation_confirmations"][key] = bad
                    errors = validate_evaluation_result(payload)
                    self.assertTrue(
                        any(
                            e.startswith(
                                f"invalid value: non_mutation_confirmations.{key}"
                            )
                            for e in errors
                        ),
                        msg=f"expected error for {key}={bad!r}; got {errors}",
                    )


# ---------------------------------------------------------------------------
# 32. Forbidden upstream raw sections rejected
# ---------------------------------------------------------------------------

class ForbiddenUpstreamSectionsTests(unittest.TestCase):
    def test_forbidden_upstream_raw_sections_at_top_level(self) -> None:
        for forbidden in (
            "feature_payload",
            "projection_result",
            "exclusion_result",
            "confidence_result",
            "final_report",
            "review_result",
        ):
            with self.subTest(forbidden=forbidden):
                payload = _valid_minimal_payload()
                payload[forbidden] = {}
                errors = validate_evaluation_result(payload)
                self.assertIn(
                    f"forbidden field: {forbidden} at top-level",
                    errors,
                )


# ---------------------------------------------------------------------------
# 33. Forbidden prediction / confidence / final fields rejected
# ---------------------------------------------------------------------------

class ForbiddenPredictionFieldsTests(unittest.TestCase):
    def test_forbidden_prediction_fields_at_top_level(self) -> None:
        for forbidden in (
            "most_likely_state",
            "most_unlikely_state",
            "agreement_status",
            "combined_confidence",
            "final_direction",
            "final_confidence",
        ):
            with self.subTest(forbidden=forbidden):
                payload = _valid_minimal_payload()
                payload[forbidden] = "anything"
                errors = validate_evaluation_result(payload)
                self.assertIn(
                    f"forbidden field: {forbidden} at top-level",
                    errors,
                )


# ---------------------------------------------------------------------------
# 34. Forbidden rule promotion fields rejected
# ---------------------------------------------------------------------------

class ForbiddenRulePromotionFieldsTests(unittest.TestCase):
    def test_forbidden_rule_promotion_at_top_level(self) -> None:
        for forbidden in ("active_rule_promotion", "promote_rule"):
            with self.subTest(forbidden=forbidden):
                payload = _valid_minimal_payload()
                payload[forbidden] = "anything"
                errors = validate_evaluation_result(payload)
                self.assertIn(
                    f"forbidden field: {forbidden} at top-level",
                    errors,
                )


# ---------------------------------------------------------------------------
# 35. Forbidden trading / hard / forced fields rejected
# ---------------------------------------------------------------------------

class ForbiddenTradingForcedFieldsTests(unittest.TestCase):
    def test_forbidden_trading_and_forced_at_top_level(self) -> None:
        for forbidden in (
            "trading_action",
            "buy",
            "sell",
            "hold",
            "hard",
            "forced",
            "required",
            "live_trade",
            "broker_order",
        ):
            with self.subTest(forbidden=forbidden):
                payload = _valid_minimal_payload()
                payload[forbidden] = "anything"
                errors = validate_evaluation_result(payload)
                self.assertIn(
                    f"forbidden field: {forbidden} at top-level",
                    errors,
                )


# ---------------------------------------------------------------------------
# 36. Forbidden raw artifact dump fields rejected
# ---------------------------------------------------------------------------

class ForbiddenRawArtifactDumpFieldsTests(unittest.TestCase):
    def test_forbidden_raw_artifact_dump_at_top_level(self) -> None:
        for forbidden in ("raw_replay_rows", "raw_predictions_dump"):
            with self.subTest(forbidden=forbidden):
                payload = _valid_minimal_payload()
                payload[forbidden] = "anything"
                errors = validate_evaluation_result(payload)
                self.assertIn(
                    f"forbidden field: {forbidden} at top-level",
                    errors,
                )


# ---------------------------------------------------------------------------
# 37. Validator does not mutate input
# ---------------------------------------------------------------------------

class NonMutationTests(unittest.TestCase):
    def test_valid_payload_unchanged(self) -> None:
        payload = _valid_minimal_payload()
        snapshot = copy.deepcopy(payload)
        validate_evaluation_result(payload)
        self.assertEqual(payload, snapshot)

    def test_invalid_payload_unchanged(self) -> None:
        payload = _valid_minimal_payload()
        payload.pop("status")
        snapshot = copy.deepcopy(payload)
        errors = validate_evaluation_result(payload)
        self.assertNotEqual(errors, [])
        self.assertEqual(payload, snapshot)

    def test_pure_function_repeatable_output(self) -> None:
        payload = _valid_minimal_payload()
        first = validate_evaluation_result(payload)
        second = validate_evaluation_result(payload)
        self.assertEqual(first, second)


# ---------------------------------------------------------------------------
# 38. Module import boundary
# ---------------------------------------------------------------------------

class ImportBoundaryTests(unittest.TestCase):
    """``services.evaluation_result_contract`` must remain a pure shape
    validator with zero coupling to any business / orchestrator / UI / DB
    module."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = _read("services/evaluation_result_contract.py")

    def test_no_business_module_imports(self) -> None:
        forbidden = (
            "from services.predict_legacy_adapter",
            "import services.predict_legacy_adapter",
            "from services.predict_legacy_v2_bridge",
            "import services.predict_legacy_v2_bridge",
            "from services.projection_orchestrator",
            "import services.projection_orchestrator",
            "from services.projection_orchestrator_v2",
            "import services.projection_orchestrator_v2",
            "from services.projection_entrypoint",
            "import services.projection_entrypoint",
            "from services.projection_v2_adapter",
            "import services.projection_v2_adapter",
            "from services.home_terminal_orchestrator",
            "import services.home_terminal_orchestrator",
            "from services.contract_outcome_correlation",
            "import services.contract_outcome_correlation",
            "from services.three_system_replay_audit",
            "import services.three_system_replay_audit",
            "from services.historical_replay_training",
            "import services.historical_replay_training",
            "from services.regime_validation_helper",
            "import services.regime_validation_helper",
            "from services.active_rule_pool_calibration",
            "import services.active_rule_pool_calibration",
            "from services.contract_payload_inspector",
            "import services.contract_payload_inspector",
            "from services.contract_payload_diff",
            "import services.contract_payload_diff",
            "from services.contract_payload_trend",
            "import services.contract_payload_trend",
            "from services.contract_payload_extras_dashboard",
            "import services.contract_payload_extras_dashboard",
            "from services.anti_false_exclusion_dashboard",
            "import services.anti_false_exclusion_dashboard",
            "from services.primary_bias_diagnosis",
            "import services.primary_bias_diagnosis",
            "from services.outcome_capture",
            "import services.outcome_capture",
            "from services.main_projection_layer",
            "import services.main_projection_layer",
            "from services.exclusion_layer",
            "import services.exclusion_layer",
            "from services.peer_alignment",
            "import services.peer_alignment",
            "from services.confidence_evaluator",
            "import services.confidence_evaluator",
            "from services.final_decision",
            "import services.final_decision",
            "from services.consistency_layer",
            "import services.consistency_layer",
            "from services.review_orchestrator",
            "import services.review_orchestrator",
            "from services.feature_payload_contract",
            "import services.feature_payload_contract",
            "from services.projection_result_contract",
            "import services.projection_result_contract",
            "from services.exclusion_result_contract",
            "import services.exclusion_result_contract",
            "from services.confidence_result_contract",
            "import services.confidence_result_contract",
            "from services.final_report_result_contract",
            "import services.final_report_result_contract",
            "from services.review_result_contract",
            "import services.review_result_contract",
            "from services.standard_projection_payload",
            "import services.standard_projection_payload",
            "from predict",
            "import predict",
            "from app",
            "import app",
            "from ui",
            "import ui",
            "import sqlite3",
            "from sqlite3",
            "import yfinance",
            "from yfinance",
            "import streamlit",
            "from streamlit",
            "import matcher",
            "from matcher",
        )
        for f in forbidden:
            self.assertNotIn(
                f,
                self.source,
                msg=f"services.evaluation_result_contract must not contain `{f}`",
            )

    def test_no_io_or_llm_calls(self) -> None:
        for f in ("open(", "Path(", "requests.", "urllib", "http.client",
                  "openai", "OpenAI", "anthropic", "Anthropic"):
            self.assertNotIn(
                f,
                self.source,
                msg=f"services.evaluation_result_contract must not contain `{f}`",
            )


# ---------------------------------------------------------------------------
# Sanity check on module reference
# ---------------------------------------------------------------------------

class ModuleReferenceTests(unittest.TestCase):
    def test_validate_function_lives_in_module(self) -> None:
        self.assertEqual(
            validate_evaluation_result.__module__,
            "services.evaluation_result_contract",
        )
        self.assertIs(
            erc_mod.validate_evaluation_result,
            validate_evaluation_result,
        )


if __name__ == "__main__":
    unittest.main()
