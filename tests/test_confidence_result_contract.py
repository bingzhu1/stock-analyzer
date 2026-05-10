"""Boundary + contract tests for ``services.confidence_result_contract``
(Step 18E / PR-CONF-1).

Spec source of truth:

- `tasks/record_1_0_architecture_reset_canonical_principles.md` §8 (Branch 5)
- `tasks/record_07c_confidence_system_contract.md` §3 / §9 / §11
- `tasks/record_17i_confidence_layer_rebuild_plan.md` §8 / §11 / §13
- `tasks/record_18a_first_layer_based_implementation_batch_selection.md` §13

PR-CONF-1 is a **pure addition** — a new schema constant + validator with
zero changes to any existing business code. This suite verifies:

1.  valid minimal payload returns ``[]``
2.  non-dict payload returns error (no raise)
3.  wrong ``schema_version`` returns ``invalid value:``
4.  each missing top-level section returns ``missing section:``
5.  ``kind`` must equal ``"confidence"``
6.  ``symbol`` must be a non-empty string
7.  ``ready`` must be a bool
8.  ``projection_confidence`` must be a dict
9.  ``exclusion_confidence`` must be a dict
10. ``combined_confidence`` must be a dict
11. each confidence block missing required keys returns error
12. confidence ``level`` must be a valid enum
13. confidence ``score`` outside [0, 1] returns error
14. confidence ``score`` may be None
15. ``level == 'unknown'`` with non-None score returns warning
16. confidence block ``reasoning`` must be str or list
17. ``agreement_status`` must be a valid enum
18. ``conflict_level`` must be a valid enum
19. ``confidence_factors`` must be list or dict
20. ``calibration_status`` must be a valid enum
21. ``calibration_notes`` must be list or str
22. top-level ``reasoning`` must be str or list
23. ``warnings`` must be a list
24. ``raw_evidence_refs`` must be a list
25. missing ``non_mutation_confirmations`` required keys returns error
26. ``non_mutation_confirmations`` required values must be ``True``
27. forbidden projection fields rejected
28. forbidden exclusion fields rejected
29. forbidden final / review / evaluation fields rejected
30. forbidden trading / hard / forced fields rejected
31. validator does not mutate input payload
32. module import boundary
33. ``CONFIDENCE_RESULT_SECTIONS`` matches the expected fixed order
34. ``CONFIDENCE_RESULT_SCHEMA_VERSION`` equals ``"confidence_result.v1"``
35. ``CONFIDENCE_RESULT_KIND`` equals ``"confidence"``
36. enum constants equal expected values

The validator must never raise (returns errors as a list).
"""

from __future__ import annotations

import copy
import unittest
from pathlib import Path

import services.confidence_result_contract as crc_mod
from services.confidence_result_contract import (
    CONFIDENCE_RESULT_KIND,
    CONFIDENCE_RESULT_SCHEMA_VERSION,
    CONFIDENCE_RESULT_SECTIONS,
    FORBIDDEN_FIELDS,
    VALID_AGREEMENT_STATUS,
    VALID_CALIBRATION_STATUS,
    VALID_CONFIDENCE_LEVELS,
    VALID_CONFLICT_LEVELS,
    validate_confidence_result,
)


_REPO_ROOT = Path(__file__).resolve().parent.parent


def _read(rel: str) -> str:
    return (_REPO_ROOT / rel).read_text(encoding="utf-8")


def _confidence_block(level: str = "medium", score: float | None = 0.6) -> dict:
    return {"level": level, "score": score, "reasoning": []}


def _valid_minimal_payload() -> dict:
    """Build a payload that satisfies every PR-CONF-1 shape rule."""
    return {
        "schema_version": CONFIDENCE_RESULT_SCHEMA_VERSION,
        "kind": CONFIDENCE_RESULT_KIND,
        "symbol": "AVGO",
        "ready": True,
        "projection_confidence": _confidence_block("medium", 0.6),
        "exclusion_confidence": _confidence_block("medium", 0.6),
        "agreement_status": "aligned",
        "conflict_level": "none",
        "combined_confidence": _confidence_block("medium", 0.6),
        "confidence_factors": [],
        "calibration_status": "not_ready",
        "calibration_notes": [],
        "reasoning": [],
        "warnings": [],
        "raw_evidence_refs": [],
        "non_mutation_confirmations": {
            "confidence_did_not_mutate_projection_result": True,
            "confidence_did_not_mutate_exclusion_result": True,
            "confidence_did_not_mutate_feature_payload": True,
            "confidence_did_not_generate_projection": True,
            "confidence_did_not_generate_exclusion": True,
        },
    }


# ---------------------------------------------------------------------------
# 0. Constants (test items 33-36)
# ---------------------------------------------------------------------------

class ConfidenceResultConstantsTests(unittest.TestCase):
    def test_schema_version_is_v1(self) -> None:
        self.assertEqual(CONFIDENCE_RESULT_SCHEMA_VERSION, "confidence_result.v1")

    def test_kind_is_confidence(self) -> None:
        self.assertEqual(CONFIDENCE_RESULT_KIND, "confidence")

    def test_sixteen_top_level_sections_in_fixed_order(self) -> None:
        self.assertEqual(
            CONFIDENCE_RESULT_SECTIONS,
            (
                "schema_version",
                "kind",
                "symbol",
                "ready",
                "projection_confidence",
                "exclusion_confidence",
                "agreement_status",
                "conflict_level",
                "combined_confidence",
                "confidence_factors",
                "calibration_status",
                "calibration_notes",
                "reasoning",
                "warnings",
                "raw_evidence_refs",
                "non_mutation_confirmations",
            ),
        )

    def test_valid_confidence_levels(self) -> None:
        self.assertEqual(
            VALID_CONFIDENCE_LEVELS, ("high", "medium", "low", "unknown")
        )

    def test_valid_agreement_status(self) -> None:
        self.assertEqual(
            VALID_AGREEMENT_STATUS,
            ("aligned", "partial_conflict", "strong_conflict", "unknown"),
        )

    def test_valid_conflict_levels(self) -> None:
        self.assertEqual(
            VALID_CONFLICT_LEVELS,
            ("none", "low", "medium", "high", "unknown"),
        )

    def test_valid_calibration_status(self) -> None:
        self.assertEqual(
            VALID_CALIBRATION_STATUS,
            ("ready", "not_ready", "partial", "unknown"),
        )

    def test_forbidden_fields_includes_projection_keys(self) -> None:
        for required in (
            "most_likely_state",
            "ranked_states",
            "state_probabilities",
            "predicted_top1",
            "predicted_top2",
            "projection_result",
        ):
            self.assertIn(
                required, FORBIDDEN_FIELDS,
                msg=f"FORBIDDEN_FIELDS must include {required!r}",
            )

    def test_forbidden_fields_includes_exclusion_keys(self) -> None:
        for required in (
            "most_unlikely_state",
            "ranked_unlikely_states",
            "excluded_states",
            "triggered_rules",
            "triggered_rule",
            "exclusion_result",
            "false_exclusion_risk",
        ):
            self.assertIn(
                required, FORBIDDEN_FIELDS,
                msg=f"FORBIDDEN_FIELDS must include {required!r}",
            )

    def test_forbidden_fields_includes_final_review_eval_keys(self) -> None:
        for required in (
            "final_report",
            "review_result",
            "evaluation_result",
            "final_direction",
            "final_confidence",
            "final_bias",
            "final_projection",
            "primary_projection",
        ):
            self.assertIn(
                required, FORBIDDEN_FIELDS,
                msg=f"FORBIDDEN_FIELDS must include {required!r}",
            )

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
            self.assertIn(
                required, FORBIDDEN_FIELDS,
                msg=f"FORBIDDEN_FIELDS must include {required!r}",
            )


# ---------------------------------------------------------------------------
# 1. Valid minimal payload returns []
# ---------------------------------------------------------------------------

class ValidMinimalPayloadTests(unittest.TestCase):
    def test_valid_minimal_payload_returns_empty_list(self) -> None:
        errors = validate_confidence_result(_valid_minimal_payload())
        self.assertEqual(errors, [], msg=f"unexpected errors: {errors}")

    def test_each_valid_confidence_level_is_accepted(self) -> None:
        for level in ("high", "medium", "low"):
            with self.subTest(level=level):
                payload = _valid_minimal_payload()
                payload["projection_confidence"] = _confidence_block(level, 0.6)
                payload["exclusion_confidence"] = _confidence_block(level, 0.6)
                payload["combined_confidence"] = _confidence_block(level, 0.6)
                errors = validate_confidence_result(payload)
                self.assertEqual(errors, [], msg=f"errors for {level}: {errors}")

    def test_unknown_level_with_none_score_is_valid(self) -> None:
        payload = _valid_minimal_payload()
        payload["projection_confidence"] = _confidence_block("unknown", None)
        payload["exclusion_confidence"] = _confidence_block("unknown", None)
        payload["combined_confidence"] = _confidence_block("unknown", None)
        payload["agreement_status"] = "unknown"
        payload["conflict_level"] = "unknown"
        payload["calibration_status"] = "unknown"
        errors = validate_confidence_result(payload)
        self.assertEqual(errors, [])

    def test_each_valid_agreement_status_is_accepted(self) -> None:
        for status in VALID_AGREEMENT_STATUS:
            with self.subTest(agreement_status=status):
                payload = _valid_minimal_payload()
                payload["agreement_status"] = status
                errors = validate_confidence_result(payload)
                bad = [
                    e for e in errors
                    if e.startswith("invalid value: agreement_status")
                ]
                self.assertEqual(bad, [])

    def test_each_valid_conflict_level_is_accepted(self) -> None:
        for level in VALID_CONFLICT_LEVELS:
            with self.subTest(conflict_level=level):
                payload = _valid_minimal_payload()
                payload["conflict_level"] = level
                errors = validate_confidence_result(payload)
                bad = [
                    e for e in errors
                    if e.startswith("invalid value: conflict_level")
                ]
                self.assertEqual(bad, [])

    def test_each_valid_calibration_status_is_accepted(self) -> None:
        for status in VALID_CALIBRATION_STATUS:
            with self.subTest(calibration_status=status):
                payload = _valid_minimal_payload()
                payload["calibration_status"] = status
                errors = validate_confidence_result(payload)
                bad = [
                    e for e in errors
                    if e.startswith("invalid value: calibration_status")
                ]
                self.assertEqual(bad, [])


# ---------------------------------------------------------------------------
# 2. Non-dict payload returns error (no raise)
# ---------------------------------------------------------------------------

class NonDictPayloadTests(unittest.TestCase):
    def test_none_payload(self) -> None:
        errors = validate_confidence_result(None)
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("invalid type: payload expected dict"))

    def test_list_payload(self) -> None:
        errors = validate_confidence_result([])
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("invalid type: payload expected dict"))

    def test_str_payload(self) -> None:
        errors = validate_confidence_result("not a dict")
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("invalid type: payload expected dict"))

    def test_int_payload(self) -> None:
        errors = validate_confidence_result(42)
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("invalid type: payload expected dict"))

    def test_non_dict_input_does_not_raise(self) -> None:
        for value in (None, 42, "x", [], (), 1.5, object()):
            with self.subTest(value=value):
                result = validate_confidence_result(value)
                self.assertIsInstance(result, list)


# ---------------------------------------------------------------------------
# 3. Wrong schema_version
# ---------------------------------------------------------------------------

class SchemaVersionTests(unittest.TestCase):
    def test_wrong_schema_version_returns_invalid_value_error(self) -> None:
        payload = _valid_minimal_payload()
        payload["schema_version"] = "confidence_system_result.v1"
        errors = validate_confidence_result(payload)
        matches = [e for e in errors if e.startswith("invalid value: schema_version")]
        self.assertEqual(
            len(matches), 1,
            msg=f"expected one schema_version error; got {matches}",
        )


# ---------------------------------------------------------------------------
# 4. Missing top-level section
# ---------------------------------------------------------------------------

class MissingTopLevelSectionTests(unittest.TestCase):
    def test_each_missing_section_yields_missing_section_error(self) -> None:
        for section in CONFIDENCE_RESULT_SECTIONS:
            with self.subTest(section=section):
                payload = _valid_minimal_payload()
                payload.pop(section)
                errors = validate_confidence_result(payload)
                self.assertIn(
                    f"missing section: {section}",
                    errors,
                    msg=f"validator did not catch missing {section}; got {errors}",
                )


# ---------------------------------------------------------------------------
# 5. kind must equal "confidence"
# ---------------------------------------------------------------------------

class KindTests(unittest.TestCase):
    def test_wrong_kind_returns_invalid_value_error(self) -> None:
        for bad in ("confidence_evaluator", "projection", "exclusion", "", None, 42):
            with self.subTest(kind=bad):
                payload = _valid_minimal_payload()
                payload["kind"] = bad
                errors = validate_confidence_result(payload)
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
                errors = validate_confidence_result(payload)
                matches = [e for e in errors if e.startswith("invalid value: symbol")]
                self.assertEqual(
                    len(matches), 1,
                    msg=f"expected one symbol error for {bad!r}; got {matches}",
                )


# ---------------------------------------------------------------------------
# 7. ready must be bool
# ---------------------------------------------------------------------------

class ReadyTests(unittest.TestCase):
    def test_ready_must_be_bool(self) -> None:
        for bad in (None, 0, 1, "True", "False", []):
            with self.subTest(ready=bad):
                payload = _valid_minimal_payload()
                payload["ready"] = bad
                errors = validate_confidence_result(payload)
                matches = [e for e in errors if e.startswith("invalid type: ready")]
                self.assertEqual(
                    len(matches), 1,
                    msg=f"expected one ready type error for {bad!r}; got {matches}",
                )


# ---------------------------------------------------------------------------
# 8 / 9 / 10. confidence blocks must be dict
# ---------------------------------------------------------------------------

class ConfidenceBlockTypeTests(unittest.TestCase):
    def test_each_confidence_block_must_be_dict(self) -> None:
        for block_name in (
            "projection_confidence",
            "exclusion_confidence",
            "combined_confidence",
        ):
            for bad in ([], "string", 42, None):
                with self.subTest(block=block_name, value=bad):
                    payload = _valid_minimal_payload()
                    payload[block_name] = bad
                    errors = validate_confidence_result(payload)
                    matches = [
                        e for e in errors
                        if e.startswith(f"invalid type: {block_name}")
                    ]
                    self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 11. each confidence block missing required keys returns error
# ---------------------------------------------------------------------------

class ConfidenceBlockMissingFieldsTests(unittest.TestCase):
    def test_each_block_each_missing_key_yields_missing_field_error(self) -> None:
        for block_name in (
            "projection_confidence",
            "exclusion_confidence",
            "combined_confidence",
        ):
            for field in ("level", "score", "reasoning"):
                with self.subTest(block=block_name, field=field):
                    payload = _valid_minimal_payload()
                    payload[block_name].pop(field)
                    errors = validate_confidence_result(payload)
                    self.assertIn(
                        f"missing field: {block_name}.{field}",
                        errors,
                    )


# ---------------------------------------------------------------------------
# 12. confidence level must be valid enum
# ---------------------------------------------------------------------------

class ConfidenceBlockLevelEnumTests(unittest.TestCase):
    def test_invalid_level_returns_error(self) -> None:
        for block_name in (
            "projection_confidence",
            "exclusion_confidence",
            "combined_confidence",
        ):
            for bad in ("HIGH", "very_low", "extreme", "", None, 42):
                with self.subTest(block=block_name, level=bad):
                    payload = _valid_minimal_payload()
                    payload[block_name] = {
                        "level": bad,
                        "score": 0.6,
                        "reasoning": [],
                    }
                    errors = validate_confidence_result(payload)
                    matches = [
                        e for e in errors
                        if e.startswith(f"invalid value: {block_name}.level")
                    ]
                    self.assertEqual(
                        len(matches), 1,
                        msg=f"expected one level error for {block_name}={bad!r}; got {matches}",
                    )


# ---------------------------------------------------------------------------
# 13. confidence score outside [0, 1] returns error
# ---------------------------------------------------------------------------

class ConfidenceBlockScoreRangeTests(unittest.TestCase):
    def test_negative_score_returns_error(self) -> None:
        for block_name in (
            "projection_confidence",
            "exclusion_confidence",
            "combined_confidence",
        ):
            with self.subTest(block=block_name):
                payload = _valid_minimal_payload()
                payload[block_name] = _confidence_block("medium", -0.1)
                errors = validate_confidence_result(payload)
                matches = [
                    e for e in errors
                    if e.startswith(f"invalid value: {block_name}.score")
                ]
                self.assertEqual(len(matches), 1)

    def test_score_above_one_returns_error(self) -> None:
        for block_name in (
            "projection_confidence",
            "exclusion_confidence",
            "combined_confidence",
        ):
            with self.subTest(block=block_name):
                payload = _valid_minimal_payload()
                payload[block_name] = _confidence_block("medium", 1.5)
                errors = validate_confidence_result(payload)
                matches = [
                    e for e in errors
                    if e.startswith(f"invalid value: {block_name}.score")
                ]
                self.assertEqual(len(matches), 1)

    def test_non_numeric_score_returns_type_error(self) -> None:
        for block_name in (
            "projection_confidence",
            "exclusion_confidence",
            "combined_confidence",
        ):
            with self.subTest(block=block_name):
                payload = _valid_minimal_payload()
                payload[block_name] = _confidence_block("medium", "0.6")
                errors = validate_confidence_result(payload)
                matches = [
                    e for e in errors
                    if e.startswith(f"invalid type: {block_name}.score")
                ]
                self.assertEqual(len(matches), 1)

    def test_bool_score_rejected_as_non_numeric(self) -> None:
        # Guard against ``bool`` being accepted via ``isinstance(True, int)``.
        for block_name in (
            "projection_confidence",
            "exclusion_confidence",
            "combined_confidence",
        ):
            with self.subTest(block=block_name):
                payload = _valid_minimal_payload()
                payload[block_name] = _confidence_block("medium", True)
                errors = validate_confidence_result(payload)
                matches = [
                    e for e in errors
                    if e.startswith(f"invalid type: {block_name}.score")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 14. confidence score may be None
# ---------------------------------------------------------------------------

class ConfidenceBlockScoreNoneTests(unittest.TestCase):
    def test_none_score_with_valid_level_is_ok(self) -> None:
        # Level != "unknown" with score=None should not be a type error.
        # (Producers may emit None for fields they cannot derive yet.)
        payload = _valid_minimal_payload()
        payload["projection_confidence"] = _confidence_block("medium", None)
        errors = validate_confidence_result(payload)
        bad = [
            e for e in errors
            if e.startswith("invalid type: projection_confidence.score")
            or e.startswith("invalid value: projection_confidence.score")
        ]
        self.assertEqual(bad, [])


# ---------------------------------------------------------------------------
# 15. level == "unknown" with non-None score returns warning
# ---------------------------------------------------------------------------

class UnknownLevelScoreAdvisoryTests(unittest.TestCase):
    def test_unknown_level_with_score_emits_warning(self) -> None:
        for block_name in (
            "projection_confidence",
            "exclusion_confidence",
            "combined_confidence",
        ):
            with self.subTest(block=block_name):
                payload = _valid_minimal_payload()
                payload[block_name] = _confidence_block("unknown", 0.5)
                errors = validate_confidence_result(payload)
                warnings = [
                    e for e in errors
                    if e.startswith(f"warning: {block_name}.score")
                ]
                self.assertEqual(len(warnings), 1)

    def test_unknown_level_with_none_score_does_not_warn(self) -> None:
        for block_name in (
            "projection_confidence",
            "exclusion_confidence",
            "combined_confidence",
        ):
            with self.subTest(block=block_name):
                payload = _valid_minimal_payload()
                payload[block_name] = _confidence_block("unknown", None)
                errors = validate_confidence_result(payload)
                warnings = [
                    e for e in errors
                    if e.startswith(f"warning: {block_name}.score")
                ]
                self.assertEqual(warnings, [])

    def test_validator_does_not_auto_correct(self) -> None:
        # The advisory must not normalize the score back to None.
        payload = _valid_minimal_payload()
        payload["projection_confidence"] = _confidence_block("unknown", 0.5)
        snapshot = copy.deepcopy(payload["projection_confidence"])
        validate_confidence_result(payload)
        self.assertEqual(payload["projection_confidence"], snapshot)


# ---------------------------------------------------------------------------
# 16. confidence block reasoning must be str or list
# ---------------------------------------------------------------------------

class ConfidenceBlockReasoningTypeTests(unittest.TestCase):
    def test_reasoning_must_be_str_or_list(self) -> None:
        for block_name in (
            "projection_confidence",
            "exclusion_confidence",
            "combined_confidence",
        ):
            for bad in ({}, 42, None, True):
                with self.subTest(block=block_name, value=bad):
                    payload = _valid_minimal_payload()
                    payload[block_name] = {
                        "level": "medium",
                        "score": 0.6,
                        "reasoning": bad,
                    }
                    errors = validate_confidence_result(payload)
                    matches = [
                        e for e in errors
                        if e.startswith(f"invalid type: {block_name}.reasoning")
                    ]
                    self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 17. agreement_status must be valid enum
# ---------------------------------------------------------------------------

class AgreementStatusTests(unittest.TestCase):
    def test_invalid_agreement_status_returns_error(self) -> None:
        for bad in ("ALIGNED", "agreed", "", None, 42):
            with self.subTest(agreement_status=bad):
                payload = _valid_minimal_payload()
                payload["agreement_status"] = bad
                errors = validate_confidence_result(payload)
                matches = [
                    e for e in errors
                    if e.startswith("invalid value: agreement_status")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 18. conflict_level must be valid enum
# ---------------------------------------------------------------------------

class ConflictLevelTests(unittest.TestCase):
    def test_invalid_conflict_level_returns_error(self) -> None:
        for bad in ("LOW", "extreme", "", None, 42):
            with self.subTest(conflict_level=bad):
                payload = _valid_minimal_payload()
                payload["conflict_level"] = bad
                errors = validate_confidence_result(payload)
                matches = [
                    e for e in errors
                    if e.startswith("invalid value: conflict_level")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 19. confidence_factors must be list or dict
# ---------------------------------------------------------------------------

class ConfidenceFactorsTypeTests(unittest.TestCase):
    def test_confidence_factors_must_be_list_or_dict(self) -> None:
        for bad in ("string", 42, None, True):
            with self.subTest(confidence_factors=bad):
                payload = _valid_minimal_payload()
                payload["confidence_factors"] = bad
                errors = validate_confidence_result(payload)
                matches = [
                    e for e in errors
                    if e.startswith("invalid type: confidence_factors")
                ]
                self.assertEqual(len(matches), 1)

    def test_confidence_factors_dict_is_ok(self) -> None:
        payload = _valid_minimal_payload()
        payload["confidence_factors"] = {"sample_size": "high"}
        errors = validate_confidence_result(payload)
        bad = [e for e in errors if e.startswith("invalid type: confidence_factors")]
        self.assertEqual(bad, [])


# ---------------------------------------------------------------------------
# 20. calibration_status must be valid enum
# ---------------------------------------------------------------------------

class CalibrationStatusTests(unittest.TestCase):
    def test_invalid_calibration_status_returns_error(self) -> None:
        for bad in ("READY", "calibrated", "", None, 42):
            with self.subTest(calibration_status=bad):
                payload = _valid_minimal_payload()
                payload["calibration_status"] = bad
                errors = validate_confidence_result(payload)
                matches = [
                    e for e in errors
                    if e.startswith("invalid value: calibration_status")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 21. calibration_notes must be list or str
# ---------------------------------------------------------------------------

class CalibrationNotesTypeTests(unittest.TestCase):
    def test_calibration_notes_must_be_list_or_str(self) -> None:
        for bad in ({}, 42, None, True):
            with self.subTest(calibration_notes=bad):
                payload = _valid_minimal_payload()
                payload["calibration_notes"] = bad
                errors = validate_confidence_result(payload)
                matches = [
                    e for e in errors
                    if e.startswith("invalid type: calibration_notes")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 22. top-level reasoning must be str or list
# ---------------------------------------------------------------------------

class TopLevelReasoningTypeTests(unittest.TestCase):
    def test_top_level_reasoning_must_be_str_or_list(self) -> None:
        for bad in ({}, 42, None, True):
            with self.subTest(reasoning=bad):
                payload = _valid_minimal_payload()
                payload["reasoning"] = bad
                errors = validate_confidence_result(payload)
                matches = [
                    e for e in errors
                    if e.startswith("invalid type: reasoning")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 23. warnings must be list
# ---------------------------------------------------------------------------

class WarningsTypeTests(unittest.TestCase):
    def test_warnings_must_be_list(self) -> None:
        for bad in ({}, "list", 42, None):
            with self.subTest(warnings=bad):
                payload = _valid_minimal_payload()
                payload["warnings"] = bad
                errors = validate_confidence_result(payload)
                matches = [
                    e for e in errors
                    if e.startswith("invalid type: warnings")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 24. raw_evidence_refs must be list
# ---------------------------------------------------------------------------

class RawEvidenceRefsTypeTests(unittest.TestCase):
    def test_raw_evidence_refs_must_be_list(self) -> None:
        for bad in ({}, "list", 42, None):
            with self.subTest(raw_evidence_refs=bad):
                payload = _valid_minimal_payload()
                payload["raw_evidence_refs"] = bad
                errors = validate_confidence_result(payload)
                matches = [
                    e for e in errors
                    if e.startswith("invalid type: raw_evidence_refs")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 25. Missing non_mutation_confirmations required keys returns error
# ---------------------------------------------------------------------------

class MissingNonMutationConfirmationKeysTests(unittest.TestCase):
    def test_each_missing_key_yields_missing_field_error(self) -> None:
        for key in (
            "confidence_did_not_mutate_projection_result",
            "confidence_did_not_mutate_exclusion_result",
            "confidence_did_not_mutate_feature_payload",
            "confidence_did_not_generate_projection",
            "confidence_did_not_generate_exclusion",
        ):
            with self.subTest(key=key):
                payload = _valid_minimal_payload()
                payload["non_mutation_confirmations"].pop(key)
                errors = validate_confidence_result(payload)
                self.assertIn(
                    f"missing field: non_mutation_confirmations.{key}",
                    errors,
                )


# ---------------------------------------------------------------------------
# 26. non_mutation_confirmations required values must be True
# ---------------------------------------------------------------------------

class NonMutationConfirmationValueTests(unittest.TestCase):
    def test_each_required_key_must_be_true(self) -> None:
        for key in (
            "confidence_did_not_mutate_projection_result",
            "confidence_did_not_mutate_exclusion_result",
            "confidence_did_not_mutate_feature_payload",
            "confidence_did_not_generate_projection",
            "confidence_did_not_generate_exclusion",
        ):
            for bad in (False, None, 0, 1, "true", []):
                with self.subTest(key=key, value=bad):
                    payload = _valid_minimal_payload()
                    payload["non_mutation_confirmations"][key] = bad
                    errors = validate_confidence_result(payload)
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
# 27. Forbidden projection fields rejected
# ---------------------------------------------------------------------------

class ForbiddenProjectionFieldsTests(unittest.TestCase):
    def test_forbidden_projection_fields_at_top_level(self) -> None:
        for forbidden in (
            "most_likely_state",
            "ranked_states",
            "state_probabilities",
            "predicted_top1",
            "predicted_top2",
            "projection_result",
        ):
            with self.subTest(forbidden=forbidden):
                payload = _valid_minimal_payload()
                payload[forbidden] = "anything"
                errors = validate_confidence_result(payload)
                self.assertIn(
                    f"forbidden field: {forbidden} at top-level",
                    errors,
                )


# ---------------------------------------------------------------------------
# 28. Forbidden exclusion fields rejected
# ---------------------------------------------------------------------------

class ForbiddenExclusionFieldsTests(unittest.TestCase):
    def test_forbidden_exclusion_fields_at_top_level(self) -> None:
        for forbidden in (
            "most_unlikely_state",
            "ranked_unlikely_states",
            "excluded_states",
            "triggered_rules",
            "triggered_rule",
            "exclusion_result",
            "false_exclusion_risk",
        ):
            with self.subTest(forbidden=forbidden):
                payload = _valid_minimal_payload()
                payload[forbidden] = "anything"
                errors = validate_confidence_result(payload)
                self.assertIn(
                    f"forbidden field: {forbidden} at top-level",
                    errors,
                )


# ---------------------------------------------------------------------------
# 29. Forbidden final / review / evaluation fields rejected
# ---------------------------------------------------------------------------

class ForbiddenFinalReviewEvalFieldsTests(unittest.TestCase):
    def test_forbidden_final_review_eval_fields_at_top_level(self) -> None:
        for forbidden in (
            "final_report",
            "review_result",
            "evaluation_result",
            "final_direction",
            "final_confidence",
            "final_bias",
            "final_projection",
            "primary_projection",
        ):
            with self.subTest(forbidden=forbidden):
                payload = _valid_minimal_payload()
                payload[forbidden] = "anything"
                errors = validate_confidence_result(payload)
                self.assertIn(
                    f"forbidden field: {forbidden} at top-level",
                    errors,
                )


# ---------------------------------------------------------------------------
# 30. Forbidden trading / hard / forced fields rejected
# ---------------------------------------------------------------------------

class ForbiddenTradingForcedFieldsTests(unittest.TestCase):
    def test_forbidden_trading_and_forced_at_top_level(self) -> None:
        for forbidden in (
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
            with self.subTest(forbidden=forbidden):
                payload = _valid_minimal_payload()
                payload[forbidden] = "anything"
                errors = validate_confidence_result(payload)
                self.assertIn(
                    f"forbidden field: {forbidden} at top-level",
                    errors,
                )


# ---------------------------------------------------------------------------
# 31. Validator does not mutate input
# ---------------------------------------------------------------------------

class NonMutationTests(unittest.TestCase):
    def test_valid_payload_unchanged(self) -> None:
        payload = _valid_minimal_payload()
        snapshot = copy.deepcopy(payload)
        validate_confidence_result(payload)
        self.assertEqual(payload, snapshot)

    def test_invalid_payload_unchanged(self) -> None:
        payload = _valid_minimal_payload()
        payload.pop("agreement_status")
        snapshot = copy.deepcopy(payload)
        errors = validate_confidence_result(payload)
        self.assertNotEqual(errors, [])
        self.assertEqual(payload, snapshot)

    def test_pure_function_repeatable_output(self) -> None:
        payload = _valid_minimal_payload()
        first = validate_confidence_result(payload)
        second = validate_confidence_result(payload)
        self.assertEqual(first, second)


# ---------------------------------------------------------------------------
# 32. Module import boundary
# ---------------------------------------------------------------------------

class ImportBoundaryTests(unittest.TestCase):
    """``services.confidence_result_contract`` must remain a pure shape
    validator with zero coupling to any business / orchestrator / UI / DB
    module."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = _read("services/confidence_result_contract.py")

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
            "from services.confidence_evaluator",
            "import services.confidence_evaluator",
            "from services.main_projection_layer",
            "import services.main_projection_layer",
            "from services.exclusion_layer",
            "import services.exclusion_layer",
            "from services.peer_alignment",
            "import services.peer_alignment",
            "from services.final_decision",
            "import services.final_decision",
            "from services.consistency_layer",
            "import services.consistency_layer",
            "from services.review_orchestrator",
            "import services.review_orchestrator",
            "from services.predict_summary",
            "import services.predict_summary",
            "from services.ai_summary",
            "import services.ai_summary",
            "from services.feature_payload_contract",
            "import services.feature_payload_contract",
            "from services.projection_result_contract",
            "import services.projection_result_contract",
            "from services.exclusion_result_contract",
            "import services.exclusion_result_contract",
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
                msg=f"services.confidence_result_contract must not contain `{f}`",
            )

    def test_no_io_or_llm_calls(self) -> None:
        for f in ("open(", "Path(", "requests.", "urllib", "http.client",
                  "openai", "OpenAI", "anthropic", "Anthropic"):
            self.assertNotIn(
                f,
                self.source,
                msg=f"services.confidence_result_contract must not contain `{f}`",
            )


# ---------------------------------------------------------------------------
# Sanity check on module reference
# ---------------------------------------------------------------------------

class ModuleReferenceTests(unittest.TestCase):
    def test_validate_function_lives_in_module(self) -> None:
        self.assertEqual(
            validate_confidence_result.__module__,
            "services.confidence_result_contract",
        )
        self.assertIs(
            crc_mod.validate_confidence_result,
            validate_confidence_result,
        )


if __name__ == "__main__":
    unittest.main()
