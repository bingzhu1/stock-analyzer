"""Boundary + contract tests for ``services.review_result_contract``
(Step 18G / PR-REVIEW-1).

Spec source of truth:

- `tasks/record_1_0_architecture_reset_canonical_principles.md` §8 (Branch 7)
- `tasks/record_06_three_system_independence_principle.md` §6 / §7
- `tasks/record_17k_review_learning_layer_rebuild_plan.md` §12 / §15
- `tasks/record_18a_first_layer_based_implementation_batch_selection.md` §13

PR-REVIEW-1 is a **pure addition** — a new schema constant + validator
with zero changes to any existing business code. This suite verifies:

1.  valid minimal payload returns ``[]``
2.  non-dict payload returns error (no raise)
3.  wrong ``schema_version`` returns ``invalid value:``
4.  each missing top-level section returns ``missing section:``
5.  ``kind`` must equal ``"review"``
6.  ``symbol`` must be a non-empty string
7.  ``ready`` must be a bool
8.  ``prediction_id`` must be non-empty str or int
9.  date fields may be str or None
10. ``projected_state`` must be a valid state or None
11. ``excluded_states`` must be a list
12. invalid state in ``excluded_states`` returns error
13. ``confidence_level`` must be str or None
14. ``final_summary_snapshot`` must be dict / str / None
15. ``actual_outcome`` must be dict / str / None
16. ``correctness`` must be a valid enum
17. ``error_type`` must be a valid enum
18. ``missed_signals`` must be a list
19. ``false_exclusion_notes`` must be list or str
20. ``false_confidence_notes`` must be list or str
21. ``confidence_calibration_notes`` must be list or str
22. ``lesson_candidates`` must be a list
23. ``rule_candidates`` must be a list
24. ``memory_updates`` must be a list
25. ``review_summary`` must be str or list
26. ``reviewer`` must be str or dict
27. missing ``non_mutation_confirmations`` required keys returns error
28. ``non_mutation_confirmations`` required values must be ``True``
29. forbidden upstream raw sections rejected
30. forbidden projection verdict fields rejected
31. forbidden exclusion verdict fields rejected
32. forbidden confidence verdict fields rejected
33. forbidden legacy final fields rejected
34. forbidden trading / hard / forced fields rejected
35. forbidden review-specific mutation hook fields rejected
36. validator does not mutate input payload
37. module import boundary
38. ``REVIEW_RESULT_SECTIONS`` matches the expected fixed order
39. ``REVIEW_RESULT_SCHEMA_VERSION`` equals ``"review_result.v1"``
40. ``REVIEW_RESULT_KIND`` equals ``"review"``
41. ``VALID_STATES`` equals the 5-state vocabulary
42. enum constants equal expected values

The validator must never raise (returns errors as a list).
"""

from __future__ import annotations

import copy
import unittest
from pathlib import Path

import services.review_result_contract as rrc_mod
from services.review_result_contract import (
    FORBIDDEN_FIELDS,
    REVIEW_RESULT_KIND,
    REVIEW_RESULT_SCHEMA_VERSION,
    REVIEW_RESULT_SECTIONS,
    VALID_CORRECTNESS,
    VALID_ERROR_TYPES,
    VALID_STATES,
    validate_review_result,
)


_REPO_ROOT = Path(__file__).resolve().parent.parent


def _read(rel: str) -> str:
    return (_REPO_ROOT / rel).read_text(encoding="utf-8")


def _valid_minimal_payload() -> dict:
    """Build a payload that satisfies every PR-REVIEW-1 shape rule."""
    return {
        "schema_version": REVIEW_RESULT_SCHEMA_VERSION,
        "kind": REVIEW_RESULT_KIND,
        "symbol": "AVGO",
        "ready": True,
        "prediction_id": "pred-2026-05-08-AVGO",
        "prediction_date": "2026-05-08",
        "target_date": "2026-05-09",
        "review_timestamp": "2026-05-10T00:00:00Z",
        "projected_state": "小涨",
        "excluded_states": ["大跌"],
        "confidence_level": "medium",
        "final_summary_snapshot": "snapshot text",
        "actual_outcome": {"actual_state": "小涨"},
        "correctness": "correct",
        "error_type": "none",
        "missed_signals": [],
        "false_exclusion_notes": [],
        "false_confidence_notes": [],
        "confidence_calibration_notes": [],
        "lesson_candidates": [],
        "rule_candidates": [],
        "memory_updates": [],
        "review_summary": "minimal review",
        "reviewer": "review_orchestrator",
        "non_mutation_confirmations": {
            "review_did_not_mutate_projection_result": True,
            "review_did_not_mutate_exclusion_result": True,
            "review_did_not_mutate_confidence_result": True,
            "review_did_not_mutate_final_report": True,
            "review_did_not_affect_current_prediction": True,
            "review_did_not_use_future_outcome_for_current_prediction": True,
        },
    }


# ---------------------------------------------------------------------------
# 0. Constants (test items 38-42)
# ---------------------------------------------------------------------------

class ReviewResultConstantsTests(unittest.TestCase):
    def test_schema_version_is_v1(self) -> None:
        self.assertEqual(REVIEW_RESULT_SCHEMA_VERSION, "review_result.v1")

    def test_kind_is_review(self) -> None:
        self.assertEqual(REVIEW_RESULT_KIND, "review")

    def test_twenty_five_top_level_sections_in_fixed_order(self) -> None:
        self.assertEqual(
            REVIEW_RESULT_SECTIONS,
            (
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
            ),
        )

    def test_valid_states_are_five_state_vocabulary(self) -> None:
        self.assertEqual(VALID_STATES, ("大涨", "小涨", "震荡", "小跌", "大跌"))

    def test_valid_correctness_enum(self) -> None:
        self.assertEqual(
            VALID_CORRECTNESS,
            ("correct", "incorrect", "partial", "unknown", "not_ready"),
        )

    def test_valid_error_types_enum(self) -> None:
        self.assertEqual(
            VALID_ERROR_TYPES,
            (
                "none",
                "projection_error",
                "exclusion_error",
                "confidence_error",
                "final_report_error",
                "data_issue",
                "mixed",
                "unknown",
            ),
        )

    def test_forbidden_fields_includes_upstream_raw_sections(self) -> None:
        for required in (
            "feature_payload",
            "projection_result",
            "exclusion_result",
            "confidence_result",
            "final_report",
            "evaluation_result",
        ):
            self.assertIn(
                required, FORBIDDEN_FIELDS,
                msg=f"FORBIDDEN_FIELDS must include {required!r}",
            )

    def test_forbidden_fields_includes_projection_verdict_keys(self) -> None:
        for required in (
            "most_likely_state",
            "ranked_states",
            "state_probabilities",
            "predicted_top1",
            "predicted_top2",
        ):
            self.assertIn(required, FORBIDDEN_FIELDS)

    def test_forbidden_fields_includes_exclusion_verdict_keys(self) -> None:
        for required in (
            "most_unlikely_state",
            "ranked_unlikely_states",
            "triggered_rules",
            "triggered_rule",
            "false_exclusion_risk",
        ):
            self.assertIn(required, FORBIDDEN_FIELDS)

    def test_forbidden_fields_includes_confidence_verdict_keys(self) -> None:
        for required in (
            "agreement_status",
            "conflict_level",
            "combined_confidence",
            "projection_confidence",
            "exclusion_confidence",
        ):
            self.assertIn(required, FORBIDDEN_FIELDS)

    def test_forbidden_fields_includes_legacy_bridge_keys(self) -> None:
        for required in (
            "final_direction",
            "final_confidence",
            "final_bias",
            "final_projection",
            "primary_projection",
            "peer_adjustment",
            "path_risk",
        ):
            self.assertIn(required, FORBIDDEN_FIELDS)

    def test_forbidden_fields_includes_trading_and_forced_tokens(self) -> None:
        for required in (
            "trading_action",
            "order",
            "position_action",
            "execution",
            "simulated_trade",
            "buy",
            "sell",
            "hold",
            "hard",
            "forced",
            "required",
        ):
            self.assertIn(required, FORBIDDEN_FIELDS)

    def test_forbidden_fields_includes_review_mutation_hooks(self) -> None:
        for required in (
            "current_prediction_mutated",
            "briefing_mutated_confidence",
            "memory_forced_decision",
        ):
            self.assertIn(
                required, FORBIDDEN_FIELDS,
                msg=f"FORBIDDEN_FIELDS must include {required!r}",
            )


# ---------------------------------------------------------------------------
# 1. Valid minimal payload returns []
# ---------------------------------------------------------------------------

class ValidMinimalPayloadTests(unittest.TestCase):
    def test_valid_minimal_payload_returns_empty_list(self) -> None:
        errors = validate_review_result(_valid_minimal_payload())
        self.assertEqual(errors, [], msg=f"unexpected errors: {errors}")

    def test_each_valid_correctness_is_accepted(self) -> None:
        for value in VALID_CORRECTNESS:
            with self.subTest(correctness=value):
                payload = _valid_minimal_payload()
                payload["correctness"] = value
                errors = validate_review_result(payload)
                bad = [e for e in errors if e.startswith("invalid value: correctness")]
                self.assertEqual(bad, [])

    def test_each_valid_error_type_is_accepted(self) -> None:
        for value in VALID_ERROR_TYPES:
            with self.subTest(error_type=value):
                payload = _valid_minimal_payload()
                payload["error_type"] = value
                errors = validate_review_result(payload)
                bad = [e for e in errors if e.startswith("invalid value: error_type")]
                self.assertEqual(bad, [])

    def test_int_prediction_id_is_ok(self) -> None:
        payload = _valid_minimal_payload()
        payload["prediction_id"] = 12345
        errors = validate_review_result(payload)
        self.assertEqual(errors, [])

    def test_reviewer_dict_is_ok(self) -> None:
        payload = _valid_minimal_payload()
        payload["reviewer"] = {"agent": "review_orchestrator", "version": "v1"}
        errors = validate_review_result(payload)
        self.assertEqual(errors, [])

    def test_dates_may_be_none(self) -> None:
        payload = _valid_minimal_payload()
        payload["prediction_date"] = None
        payload["target_date"] = None
        payload["review_timestamp"] = None
        errors = validate_review_result(payload)
        self.assertEqual(errors, [])


# ---------------------------------------------------------------------------
# 2. Non-dict payload returns error (no raise)
# ---------------------------------------------------------------------------

class NonDictPayloadTests(unittest.TestCase):
    def test_none_payload(self) -> None:
        errors = validate_review_result(None)
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("invalid type: payload expected dict"))

    def test_list_payload(self) -> None:
        errors = validate_review_result([])
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("invalid type: payload expected dict"))

    def test_str_payload(self) -> None:
        errors = validate_review_result("not a dict")
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("invalid type: payload expected dict"))

    def test_int_payload(self) -> None:
        errors = validate_review_result(42)
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("invalid type: payload expected dict"))

    def test_non_dict_input_does_not_raise(self) -> None:
        for value in (None, 42, "x", [], (), 1.5, object()):
            with self.subTest(value=value):
                result = validate_review_result(value)
                self.assertIsInstance(result, list)


# ---------------------------------------------------------------------------
# 3. Wrong schema_version
# ---------------------------------------------------------------------------

class SchemaVersionTests(unittest.TestCase):
    def test_wrong_schema_version_returns_invalid_value_error(self) -> None:
        payload = _valid_minimal_payload()
        payload["schema_version"] = "review_result.v2"
        errors = validate_review_result(payload)
        matches = [e for e in errors if e.startswith("invalid value: schema_version")]
        self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 4. Missing top-level section
# ---------------------------------------------------------------------------

class MissingTopLevelSectionTests(unittest.TestCase):
    def test_each_missing_section_yields_missing_section_error(self) -> None:
        for section in REVIEW_RESULT_SECTIONS:
            with self.subTest(section=section):
                payload = _valid_minimal_payload()
                payload.pop(section)
                errors = validate_review_result(payload)
                self.assertIn(
                    f"missing section: {section}",
                    errors,
                    msg=f"validator did not catch missing {section}; got {errors}",
                )


# ---------------------------------------------------------------------------
# 5. kind must equal "review"
# ---------------------------------------------------------------------------

class KindTests(unittest.TestCase):
    def test_wrong_kind_returns_invalid_value_error(self) -> None:
        for bad in ("review_orchestrator", "projection", "evaluation", "", None, 42):
            with self.subTest(kind=bad):
                payload = _valid_minimal_payload()
                payload["kind"] = bad
                errors = validate_review_result(payload)
                matches = [e for e in errors if e.startswith("invalid value: kind")]
                self.assertEqual(
                    len(matches), 1,
                    msg=f"expected one kind error for {bad!r}; got {matches}",
                )


# ---------------------------------------------------------------------------
# 6. symbol must be non-empty string
# ---------------------------------------------------------------------------

class SymbolTests(unittest.TestCase):
    def test_symbol_must_be_non_empty_string(self) -> None:
        for bad in ("", None, 42, [], {}):
            with self.subTest(symbol=bad):
                payload = _valid_minimal_payload()
                payload["symbol"] = bad
                errors = validate_review_result(payload)
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
                errors = validate_review_result(payload)
                matches = [e for e in errors if e.startswith("invalid type: ready")]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 8. prediction_id must be non-empty str or int
# ---------------------------------------------------------------------------

class PredictionIdTests(unittest.TestCase):
    def test_prediction_id_str_non_empty_is_ok(self) -> None:
        payload = _valid_minimal_payload()
        payload["prediction_id"] = "abc-123"
        errors = validate_review_result(payload)
        self.assertEqual(errors, [])

    def test_prediction_id_int_is_ok(self) -> None:
        payload = _valid_minimal_payload()
        payload["prediction_id"] = 0
        errors = validate_review_result(payload)
        self.assertEqual(errors, [])

    def test_prediction_id_empty_string_returns_error(self) -> None:
        payload = _valid_minimal_payload()
        payload["prediction_id"] = ""
        errors = validate_review_result(payload)
        matches = [e for e in errors if e.startswith("invalid value: prediction_id")]
        self.assertEqual(len(matches), 1)

    def test_prediction_id_other_types_return_error(self) -> None:
        for bad in (None, [], {}, 1.5, True):
            with self.subTest(prediction_id=bad):
                payload = _valid_minimal_payload()
                payload["prediction_id"] = bad
                errors = validate_review_result(payload)
                matches = [
                    e for e in errors if e.startswith("invalid value: prediction_id")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 9. dates may be str or None
# ---------------------------------------------------------------------------

class DateFieldsTests(unittest.TestCase):
    def test_each_date_field_must_be_str_or_none(self) -> None:
        for date_field in ("prediction_date", "target_date", "review_timestamp"):
            for bad in (42, 1.5, [], {}):
                with self.subTest(field=date_field, value=bad):
                    payload = _valid_minimal_payload()
                    payload[date_field] = bad
                    errors = validate_review_result(payload)
                    matches = [
                        e for e in errors
                        if e.startswith(f"invalid type: {date_field}")
                    ]
                    self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 10. projected_state must be valid state or None
# ---------------------------------------------------------------------------

class ProjectedStateTests(unittest.TestCase):
    def test_each_valid_state_is_ok(self) -> None:
        for state in VALID_STATES:
            with self.subTest(state=state):
                payload = _valid_minimal_payload()
                payload["projected_state"] = state
                errors = validate_review_result(payload)
                bad = [
                    e for e in errors
                    if e.startswith("invalid value: projected_state")
                ]
                self.assertEqual(bad, [])

    def test_none_projected_state_is_ok(self) -> None:
        payload = _valid_minimal_payload()
        payload["projected_state"] = None
        errors = validate_review_result(payload)
        self.assertEqual(errors, [])

    def test_invalid_projected_state_returns_error(self) -> None:
        for bad in ("BIG_UP", "横盘", "", 42):
            with self.subTest(state=bad):
                payload = _valid_minimal_payload()
                payload["projected_state"] = bad
                errors = validate_review_result(payload)
                matches = [
                    e for e in errors
                    if e.startswith("invalid value: projected_state")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 11. excluded_states must be list
# ---------------------------------------------------------------------------

class ExcludedStatesTypeTests(unittest.TestCase):
    def test_excluded_states_must_be_list(self) -> None:
        for bad in ({}, "list", 42, None):
            with self.subTest(excluded_states=bad):
                payload = _valid_minimal_payload()
                payload["excluded_states"] = bad
                errors = validate_review_result(payload)
                matches = [
                    e for e in errors
                    if e.startswith("invalid type: excluded_states")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 12. excluded_states invalid state returns error
# ---------------------------------------------------------------------------

class ExcludedStatesValueTests(unittest.TestCase):
    def test_excluded_states_invalid_state_returns_error(self) -> None:
        payload = _valid_minimal_payload()
        payload["excluded_states"] = ["大跌", "BAD"]
        errors = validate_review_result(payload)
        self.assertTrue(
            any(
                e.startswith("invalid value: excluded_states[1] expected")
                for e in errors
            ),
            msg=f"expected excluded_states[1] error; got {errors}",
        )


# ---------------------------------------------------------------------------
# 13. confidence_level must be str or None
# ---------------------------------------------------------------------------

class ConfidenceLevelTests(unittest.TestCase):
    def test_confidence_level_str_is_ok(self) -> None:
        payload = _valid_minimal_payload()
        payload["confidence_level"] = "high"
        errors = validate_review_result(payload)
        self.assertEqual(errors, [])

    def test_confidence_level_none_is_ok(self) -> None:
        payload = _valid_minimal_payload()
        payload["confidence_level"] = None
        errors = validate_review_result(payload)
        self.assertEqual(errors, [])

    def test_confidence_level_other_types_return_error(self) -> None:
        for bad in (42, 1.5, [], {}, True):
            with self.subTest(confidence_level=bad):
                payload = _valid_minimal_payload()
                payload["confidence_level"] = bad
                errors = validate_review_result(payload)
                matches = [
                    e for e in errors
                    if e.startswith("invalid type: confidence_level")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 14. final_summary_snapshot must be dict / str / None
# ---------------------------------------------------------------------------

class FinalSummarySnapshotTests(unittest.TestCase):
    def test_final_summary_snapshot_must_be_dict_str_or_none(self) -> None:
        for bad in (42, 1.5, [], True):
            with self.subTest(final_summary_snapshot=bad):
                payload = _valid_minimal_payload()
                payload["final_summary_snapshot"] = bad
                errors = validate_review_result(payload)
                matches = [
                    e for e in errors
                    if e.startswith("invalid type: final_summary_snapshot")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 15. actual_outcome must be dict / str / None
# ---------------------------------------------------------------------------

class ActualOutcomeTests(unittest.TestCase):
    def test_actual_outcome_must_be_dict_str_or_none(self) -> None:
        for bad in (42, 1.5, [], True):
            with self.subTest(actual_outcome=bad):
                payload = _valid_minimal_payload()
                payload["actual_outcome"] = bad
                errors = validate_review_result(payload)
                matches = [
                    e for e in errors
                    if e.startswith("invalid type: actual_outcome")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 16. correctness must be valid enum
# ---------------------------------------------------------------------------

class CorrectnessTests(unittest.TestCase):
    def test_invalid_correctness_returns_error(self) -> None:
        for bad in ("CORRECT", "wrong", "", None, 42):
            with self.subTest(correctness=bad):
                payload = _valid_minimal_payload()
                payload["correctness"] = bad
                errors = validate_review_result(payload)
                matches = [
                    e for e in errors
                    if e.startswith("invalid value: correctness")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 17. error_type must be valid enum
# ---------------------------------------------------------------------------

class ErrorTypeTests(unittest.TestCase):
    def test_invalid_error_type_returns_error(self) -> None:
        for bad in ("PROJECTION_ERROR", "blackbox", "", None, 42):
            with self.subTest(error_type=bad):
                payload = _valid_minimal_payload()
                payload["error_type"] = bad
                errors = validate_review_result(payload)
                matches = [
                    e for e in errors
                    if e.startswith("invalid value: error_type")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 18. missed_signals must be list
# ---------------------------------------------------------------------------

class MissedSignalsTests(unittest.TestCase):
    def test_missed_signals_must_be_list(self) -> None:
        for bad in ({}, "list", 42, None):
            with self.subTest(missed_signals=bad):
                payload = _valid_minimal_payload()
                payload["missed_signals"] = bad
                errors = validate_review_result(payload)
                matches = [
                    e for e in errors
                    if e.startswith("invalid type: missed_signals")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 19 / 20 / 21. notes fields must be list or str
# ---------------------------------------------------------------------------

class NotesFieldsTests(unittest.TestCase):
    def test_each_notes_field_must_be_list_or_str(self) -> None:
        for notes_field in (
            "false_exclusion_notes",
            "false_confidence_notes",
            "confidence_calibration_notes",
        ):
            for bad in ({}, 42, None, True):
                with self.subTest(field=notes_field, value=bad):
                    payload = _valid_minimal_payload()
                    payload[notes_field] = bad
                    errors = validate_review_result(payload)
                    matches = [
                        e for e in errors
                        if e.startswith(f"invalid type: {notes_field}")
                    ]
                    self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 22 / 23 / 24. candidate-list fields must be list
# ---------------------------------------------------------------------------

class CandidateListFieldsTests(unittest.TestCase):
    def test_each_candidate_list_field_must_be_list(self) -> None:
        for list_field in (
            "lesson_candidates",
            "rule_candidates",
            "memory_updates",
        ):
            for bad in ({}, "list", 42, None):
                with self.subTest(field=list_field, value=bad):
                    payload = _valid_minimal_payload()
                    payload[list_field] = bad
                    errors = validate_review_result(payload)
                    matches = [
                        e for e in errors
                        if e.startswith(f"invalid type: {list_field}")
                    ]
                    self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 25. review_summary must be str or list
# ---------------------------------------------------------------------------

class ReviewSummaryTests(unittest.TestCase):
    def test_review_summary_must_be_str_or_list(self) -> None:
        for bad in ({}, 42, None, True):
            with self.subTest(review_summary=bad):
                payload = _valid_minimal_payload()
                payload["review_summary"] = bad
                errors = validate_review_result(payload)
                matches = [
                    e for e in errors
                    if e.startswith("invalid type: review_summary")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 26. reviewer must be str or dict
# ---------------------------------------------------------------------------

class ReviewerTests(unittest.TestCase):
    def test_reviewer_must_be_str_or_dict(self) -> None:
        for bad in ([], 42, None, True):
            with self.subTest(reviewer=bad):
                payload = _valid_minimal_payload()
                payload["reviewer"] = bad
                errors = validate_review_result(payload)
                matches = [
                    e for e in errors
                    if e.startswith("invalid type: reviewer")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 27. Missing non_mutation_confirmations required keys
# ---------------------------------------------------------------------------

class MissingNonMutationConfirmationKeysTests(unittest.TestCase):
    def test_each_missing_key_yields_missing_field_error(self) -> None:
        for key in (
            "review_did_not_mutate_projection_result",
            "review_did_not_mutate_exclusion_result",
            "review_did_not_mutate_confidence_result",
            "review_did_not_mutate_final_report",
            "review_did_not_affect_current_prediction",
            "review_did_not_use_future_outcome_for_current_prediction",
        ):
            with self.subTest(key=key):
                payload = _valid_minimal_payload()
                payload["non_mutation_confirmations"].pop(key)
                errors = validate_review_result(payload)
                self.assertIn(
                    f"missing field: non_mutation_confirmations.{key}",
                    errors,
                )


# ---------------------------------------------------------------------------
# 28. non_mutation_confirmations required values must be True
# ---------------------------------------------------------------------------

class NonMutationConfirmationValueTests(unittest.TestCase):
    def test_each_required_key_must_be_true(self) -> None:
        for key in (
            "review_did_not_mutate_projection_result",
            "review_did_not_mutate_exclusion_result",
            "review_did_not_mutate_confidence_result",
            "review_did_not_mutate_final_report",
            "review_did_not_affect_current_prediction",
            "review_did_not_use_future_outcome_for_current_prediction",
        ):
            for bad in (False, None, 0, 1, "true", []):
                with self.subTest(key=key, value=bad):
                    payload = _valid_minimal_payload()
                    payload["non_mutation_confirmations"][key] = bad
                    errors = validate_review_result(payload)
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
# 29. Forbidden upstream raw sections rejected
# ---------------------------------------------------------------------------

class ForbiddenUpstreamSectionsTests(unittest.TestCase):
    def test_forbidden_upstream_raw_sections_at_top_level(self) -> None:
        for forbidden in (
            "feature_payload",
            "projection_result",
            "exclusion_result",
            "confidence_result",
            "final_report",
            "evaluation_result",
        ):
            with self.subTest(forbidden=forbidden):
                payload = _valid_minimal_payload()
                payload[forbidden] = {}
                errors = validate_review_result(payload)
                self.assertIn(
                    f"forbidden field: {forbidden} at top-level",
                    errors,
                )


# ---------------------------------------------------------------------------
# 30. Forbidden projection verdict fields rejected
# ---------------------------------------------------------------------------

class ForbiddenProjectionVerdictFieldsTests(unittest.TestCase):
    def test_forbidden_projection_verdict_at_top_level(self) -> None:
        for forbidden in (
            "most_likely_state",
            "ranked_states",
            "state_probabilities",
        ):
            with self.subTest(forbidden=forbidden):
                payload = _valid_minimal_payload()
                payload[forbidden] = "anything"
                errors = validate_review_result(payload)
                self.assertIn(
                    f"forbidden field: {forbidden} at top-level",
                    errors,
                )


# ---------------------------------------------------------------------------
# 31. Forbidden exclusion verdict fields rejected
# ---------------------------------------------------------------------------

class ForbiddenExclusionVerdictFieldsTests(unittest.TestCase):
    def test_forbidden_exclusion_verdict_at_top_level(self) -> None:
        for forbidden in (
            "most_unlikely_state",
            "ranked_unlikely_states",
            "triggered_rules",
        ):
            with self.subTest(forbidden=forbidden):
                payload = _valid_minimal_payload()
                payload[forbidden] = "anything"
                errors = validate_review_result(payload)
                self.assertIn(
                    f"forbidden field: {forbidden} at top-level",
                    errors,
                )


# ---------------------------------------------------------------------------
# 32. Forbidden confidence verdict fields rejected
# ---------------------------------------------------------------------------

class ForbiddenConfidenceVerdictFieldsTests(unittest.TestCase):
    def test_forbidden_confidence_verdict_at_top_level(self) -> None:
        for forbidden in (
            "agreement_status",
            "conflict_level",
            "combined_confidence",
        ):
            with self.subTest(forbidden=forbidden):
                payload = _valid_minimal_payload()
                payload[forbidden] = "anything"
                errors = validate_review_result(payload)
                self.assertIn(
                    f"forbidden field: {forbidden} at top-level",
                    errors,
                )


# ---------------------------------------------------------------------------
# 33. Forbidden legacy final fields rejected
# ---------------------------------------------------------------------------

class ForbiddenLegacyFinalFieldsTests(unittest.TestCase):
    def test_forbidden_legacy_final_fields_at_top_level(self) -> None:
        for forbidden in (
            "final_direction",
            "final_confidence",
            "final_bias",
        ):
            with self.subTest(forbidden=forbidden):
                payload = _valid_minimal_payload()
                payload[forbidden] = "anything"
                errors = validate_review_result(payload)
                self.assertIn(
                    f"forbidden field: {forbidden} at top-level",
                    errors,
                )


# ---------------------------------------------------------------------------
# 34. Forbidden trading / hard / forced fields rejected
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
        ):
            with self.subTest(forbidden=forbidden):
                payload = _valid_minimal_payload()
                payload[forbidden] = "anything"
                errors = validate_review_result(payload)
                self.assertIn(
                    f"forbidden field: {forbidden} at top-level",
                    errors,
                )


# ---------------------------------------------------------------------------
# 35. Forbidden review-specific mutation hook fields rejected
# ---------------------------------------------------------------------------

class ForbiddenReviewMutationHookFieldsTests(unittest.TestCase):
    def test_forbidden_review_mutation_hooks_at_top_level(self) -> None:
        for forbidden in (
            "current_prediction_mutated",
            "briefing_mutated_confidence",
            "memory_forced_decision",
        ):
            with self.subTest(forbidden=forbidden):
                payload = _valid_minimal_payload()
                payload[forbidden] = "anything"
                errors = validate_review_result(payload)
                self.assertIn(
                    f"forbidden field: {forbidden} at top-level",
                    errors,
                )


# ---------------------------------------------------------------------------
# 36. Validator does not mutate input
# ---------------------------------------------------------------------------

class NonMutationTests(unittest.TestCase):
    def test_valid_payload_unchanged(self) -> None:
        payload = _valid_minimal_payload()
        snapshot = copy.deepcopy(payload)
        validate_review_result(payload)
        self.assertEqual(payload, snapshot)

    def test_invalid_payload_unchanged(self) -> None:
        payload = _valid_minimal_payload()
        payload.pop("correctness")
        snapshot = copy.deepcopy(payload)
        errors = validate_review_result(payload)
        self.assertNotEqual(errors, [])
        self.assertEqual(payload, snapshot)

    def test_pure_function_repeatable_output(self) -> None:
        payload = _valid_minimal_payload()
        first = validate_review_result(payload)
        second = validate_review_result(payload)
        self.assertEqual(first, second)


# ---------------------------------------------------------------------------
# 37. Module import boundary
# ---------------------------------------------------------------------------

class ImportBoundaryTests(unittest.TestCase):
    """``services.review_result_contract`` must remain a pure shape
    validator with zero coupling to any business / orchestrator / UI / DB
    module."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = _read("services/review_result_contract.py")

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
            "from services.review_orchestrator",
            "import services.review_orchestrator",
            "from services.review_store",
            "import services.review_store",
            "from services.review_agent",
            "import services.review_agent",
            "from services.review_center",
            "import services.review_center",
            "from services.review_analyzer",
            "import services.review_analyzer",
            "from services.review_classifier",
            "import services.review_classifier",
            "from services.review_comparator",
            "import services.review_comparator",
            "from services.outcome_capture",
            "import services.outcome_capture",
            "from services.memory_store",
            "import services.memory_store",
            "from services.memory_feedback",
            "import services.memory_feedback",
            "from services.projection_memory_briefing",
            "import services.projection_memory_briefing",
            "from services.pre_prediction_briefing",
            "import services.pre_prediction_briefing",
            "from services.exclusion_reliability_review",
            "import services.exclusion_reliability_review",
            "from services.anti_false_exclusion_audit",
            "import services.anti_false_exclusion_audit",
            "from services.projection_review_closed_loop",
            "import services.projection_review_closed_loop",
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
        )
        for f in forbidden:
            self.assertNotIn(
                f,
                self.source,
                msg=f"services.review_result_contract must not contain `{f}`",
            )

    def test_no_io_or_llm_calls(self) -> None:
        for f in ("open(", "Path(", "requests.", "urllib", "http.client",
                  "openai", "OpenAI", "anthropic", "Anthropic"):
            self.assertNotIn(
                f,
                self.source,
                msg=f"services.review_result_contract must not contain `{f}`",
            )


# ---------------------------------------------------------------------------
# Sanity check on module reference
# ---------------------------------------------------------------------------

class ModuleReferenceTests(unittest.TestCase):
    def test_validate_function_lives_in_module(self) -> None:
        self.assertEqual(
            validate_review_result.__module__,
            "services.review_result_contract",
        )
        self.assertIs(
            rrc_mod.validate_review_result,
            validate_review_result,
        )


if __name__ == "__main__":
    unittest.main()
