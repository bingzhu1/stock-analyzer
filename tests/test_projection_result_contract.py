"""Boundary + contract tests for ``services.projection_result_contract``
(Step 18C / PR-PROJ-1).

Spec source of truth:

- `tasks/record_1_0_architecture_reset_canonical_principles.md` §8 (Branch 3)
- `tasks/record_07a_projection_system_contract.md` §3 / §9
- `tasks/record_17g_projection_layer_rebuild_plan.md` §8 / §14
- `tasks/record_18a_first_layer_based_implementation_batch_selection.md` §13

PR-PROJ-1 is a **pure addition** — a new schema constant + validator with
zero changes to any existing business code. This suite verifies:

1.  valid minimal payload returns ``[]``
2.  non-dict payload returns error (no raise)
3.  wrong ``schema_version`` returns ``invalid value:``
4.  each missing top-level section returns ``missing section:``
5.  ``kind`` must equal ``"projection"``
6.  ``symbol`` must be a non-empty string
7.  ``ready`` must be a bool
8.  ``most_likely_state`` must be a valid state, or None when ready=False
9.  ``ranked_states`` must be a list
10. invalid state in ``ranked_states`` returns error
11. ``state_probabilities`` must be a dict
12. invalid state key in ``state_probabilities`` returns error
13. ``state_probabilities`` value outside ``[0, 1]`` returns error
14. ``state_probabilities`` sum not close to 1 returns ``warning:``
15. missing ``non_mutation_confirmations`` required keys returns error
16. ``non_mutation_confirmations`` required values must be ``True``
17. forbidden exclusion / confidence / final sections at top level rejected
18. forbidden trading / hard / forced fields at top level rejected
19. legacy final fields (``final_direction`` / ``final_confidence`` /
    ``final_bias`` / ``final_projection`` etc.) rejected
20. validator does not mutate input payload
21. module import boundary: the validator does **not** import any
    business / orchestrator / UI / DB module
22. ``PROJECTION_RESULT_SECTIONS`` matches the expected fixed order
23. ``PROJECTION_RESULT_SCHEMA_VERSION`` equals ``"projection_result.v1"``
24. ``VALID_STATES`` equals the 5-state vocabulary in fixed order

The validator must never raise (returns errors as a list).
"""

from __future__ import annotations

import copy
import unittest
from pathlib import Path

import services.projection_result_contract as prc_mod
from services.projection_result_contract import (
    FORBIDDEN_FIELDS,
    PROJECTION_RESULT_KIND,
    PROJECTION_RESULT_SCHEMA_VERSION,
    PROJECTION_RESULT_SECTIONS,
    VALID_STATES,
    validate_projection_result,
)


_REPO_ROOT = Path(__file__).resolve().parent.parent


def _read(rel: str) -> str:
    return (_REPO_ROOT / rel).read_text(encoding="utf-8")


def _valid_minimal_payload() -> dict:
    """Build a payload that satisfies every PR-PROJ-1 shape rule."""
    return {
        "schema_version": PROJECTION_RESULT_SCHEMA_VERSION,
        "kind": PROJECTION_RESULT_KIND,
        "symbol": "AVGO",
        "ready": True,
        "most_likely_state": "小涨",
        "ranked_states": ["小涨", "震荡", "大涨", "小跌", "大跌"],
        "state_probabilities": {
            "大涨": 0.10,
            "小涨": 0.40,
            "震荡": 0.30,
            "小跌": 0.15,
            "大跌": 0.05,
        },
        "evidence": [],
        "rationale": [],
        "raw_score": None,
        "warnings": [],
        "feature_snapshot_ref": None,
        "historical_match_summary": {},
        "peer_alignment_summary": {},
        "non_mutation_confirmations": {
            "projection_did_not_read_exclusion": True,
            "projection_did_not_read_confidence": True,
            "projection_did_not_read_final_report": True,
            "projection_did_not_read_future_outcome": True,
        },
    }


# ---------------------------------------------------------------------------
# 0. Constants (test items 22 + 23 + 24)
# ---------------------------------------------------------------------------

class ProjectionResultConstantsTests(unittest.TestCase):
    def test_schema_version_is_v1(self) -> None:
        self.assertEqual(PROJECTION_RESULT_SCHEMA_VERSION, "projection_result.v1")

    def test_fifteen_top_level_sections_in_fixed_order(self) -> None:
        self.assertEqual(
            PROJECTION_RESULT_SECTIONS,
            (
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
            ),
        )

    def test_kind_is_projection(self) -> None:
        self.assertEqual(PROJECTION_RESULT_KIND, "projection")

    def test_valid_states_are_five_state_vocabulary(self) -> None:
        self.assertEqual(VALID_STATES, ("大涨", "小涨", "震荡", "小跌", "大跌"))

    def test_forbidden_fields_includes_exclusion_and_downstream(self) -> None:
        for required in (
            "most_unlikely_state",
            "ranked_unlikely_states",
            "excluded_states",
            "triggered_rules",
            "false_exclusion_risk",
            "exclusion_result",
            "confidence_result",
            "final_report",
            "review_result",
            "evaluation_result",
        ):
            self.assertIn(
                required, FORBIDDEN_FIELDS,
                msg=f"FORBIDDEN_FIELDS must include {required!r}",
            )

    def test_forbidden_fields_includes_legacy_bridge_keys(self) -> None:
        for required in (
            "final_direction",
            "final_confidence",
            "final_bias",
            "final_projection",
            "primary_projection",
            "peer_adjustment",
            "path_risk",
            "predicted_top1",
            "predicted_top2",
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
        errors = validate_projection_result(_valid_minimal_payload())
        self.assertEqual(errors, [], msg=f"unexpected errors: {errors}")

    def test_ready_false_with_none_most_likely_state_is_valid(self) -> None:
        payload = _valid_minimal_payload()
        payload["ready"] = False
        payload["most_likely_state"] = None
        errors = validate_projection_result(payload)
        self.assertEqual(errors, [], msg=f"unexpected errors: {errors}")


# ---------------------------------------------------------------------------
# 2. Non-dict payload returns error (no raise)
# ---------------------------------------------------------------------------

class NonDictPayloadTests(unittest.TestCase):
    def test_none_payload(self) -> None:
        errors = validate_projection_result(None)
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("invalid type: payload expected dict"))

    def test_list_payload(self) -> None:
        errors = validate_projection_result([])
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("invalid type: payload expected dict"))

    def test_str_payload(self) -> None:
        errors = validate_projection_result("not a dict")
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("invalid type: payload expected dict"))

    def test_int_payload(self) -> None:
        errors = validate_projection_result(42)
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("invalid type: payload expected dict"))

    def test_non_dict_input_does_not_raise(self) -> None:
        for value in (None, 42, "x", [], (), 1.5, object()):
            with self.subTest(value=value):
                result = validate_projection_result(value)
                self.assertIsInstance(result, list)


# ---------------------------------------------------------------------------
# 3. Wrong schema_version
# ---------------------------------------------------------------------------

class SchemaVersionTests(unittest.TestCase):
    def test_wrong_schema_version_returns_invalid_value_error(self) -> None:
        payload = _valid_minimal_payload()
        payload["schema_version"] = "projection_result.v2"
        errors = validate_projection_result(payload)
        matches = [e for e in errors if e.startswith("invalid value: schema_version")]
        self.assertEqual(
            len(matches), 1,
            msg=f"expected one schema_version error; got {matches} (all: {errors})",
        )


# ---------------------------------------------------------------------------
# 4. Missing top-level section
# ---------------------------------------------------------------------------

class MissingTopLevelSectionTests(unittest.TestCase):
    def test_each_missing_section_yields_missing_section_error(self) -> None:
        for section in PROJECTION_RESULT_SECTIONS:
            with self.subTest(section=section):
                payload = _valid_minimal_payload()
                payload.pop(section)
                errors = validate_projection_result(payload)
                self.assertIn(
                    f"missing section: {section}",
                    errors,
                    msg=f"validator did not catch missing {section}; got {errors}",
                )


# ---------------------------------------------------------------------------
# 5. kind must equal "projection"
# ---------------------------------------------------------------------------

class KindTests(unittest.TestCase):
    def test_wrong_kind_returns_invalid_value_error(self) -> None:
        for bad in ("main_projection_layer", "projection_v2", "exclusion", "", None, 42):
            with self.subTest(kind=bad):
                payload = _valid_minimal_payload()
                payload["kind"] = bad
                errors = validate_projection_result(payload)
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
                errors = validate_projection_result(payload)
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
                errors = validate_projection_result(payload)
                matches = [e for e in errors if e.startswith("invalid type: ready")]
                self.assertEqual(
                    len(matches), 1,
                    msg=f"expected one ready type error for {bad!r}; got {matches}",
                )


# ---------------------------------------------------------------------------
# 8. most_likely_state must be valid state (or None when ready=False)
# ---------------------------------------------------------------------------

class MostLikelyStateTests(unittest.TestCase):
    def test_most_likely_state_must_be_valid(self) -> None:
        for bad in ("BIG_UP", "neutral", "横盘", "", 42):
            with self.subTest(state=bad):
                payload = _valid_minimal_payload()
                payload["most_likely_state"] = bad
                errors = validate_projection_result(payload)
                matches = [
                    e for e in errors
                    if e.startswith("invalid value: most_likely_state expected")
                ]
                self.assertEqual(
                    len(matches), 1,
                    msg=f"expected one most_likely_state error for {bad!r}; got {matches}",
                )

    def test_most_likely_state_none_when_ready_true_is_error(self) -> None:
        payload = _valid_minimal_payload()
        payload["ready"] = True
        payload["most_likely_state"] = None
        errors = validate_projection_result(payload)
        self.assertIn(
            "invalid value: most_likely_state may be None only when ready=False",
            errors,
        )

    def test_most_likely_state_none_when_ready_false_is_ok(self) -> None:
        payload = _valid_minimal_payload()
        payload["ready"] = False
        payload["most_likely_state"] = None
        errors = validate_projection_result(payload)
        bad = [
            e for e in errors
            if e.startswith("invalid value: most_likely_state")
        ]
        self.assertEqual(bad, [])

    def test_each_valid_state_is_accepted(self) -> None:
        for state in VALID_STATES:
            with self.subTest(state=state):
                payload = _valid_minimal_payload()
                payload["most_likely_state"] = state
                errors = validate_projection_result(payload)
                bad = [
                    e for e in errors
                    if e.startswith("invalid value: most_likely_state")
                ]
                self.assertEqual(bad, [], msg=f"errors for {state!r}: {errors}")


# ---------------------------------------------------------------------------
# 9. ranked_states must be list
# ---------------------------------------------------------------------------

class RankedStatesTypeTests(unittest.TestCase):
    def test_ranked_states_must_be_list(self) -> None:
        for bad in ({}, "list", 42, None):
            with self.subTest(ranked_states=bad):
                payload = _valid_minimal_payload()
                payload["ranked_states"] = bad
                errors = validate_projection_result(payload)
                matches = [
                    e for e in errors
                    if e.startswith("invalid type: ranked_states")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 10. ranked_states invalid state returns error
# ---------------------------------------------------------------------------

class RankedStatesValueTests(unittest.TestCase):
    def test_ranked_states_invalid_state_returns_error(self) -> None:
        payload = _valid_minimal_payload()
        payload["ranked_states"] = ["小涨", "BAD", "震荡"]
        errors = validate_projection_result(payload)
        self.assertTrue(
            any(
                e.startswith("invalid value: ranked_states[1] expected")
                for e in errors
            ),
            msg=f"expected ranked_states[1] error; got {errors}",
        )

    def test_empty_ranked_states_is_allowed(self) -> None:
        payload = _valid_minimal_payload()
        payload["ranked_states"] = []
        errors = validate_projection_result(payload)
        self.assertEqual(errors, [])


# ---------------------------------------------------------------------------
# 11. state_probabilities must be dict
# ---------------------------------------------------------------------------

class StateProbabilitiesTypeTests(unittest.TestCase):
    def test_state_probabilities_must_be_dict(self) -> None:
        for bad in ([], "dict", 42, None):
            with self.subTest(state_probabilities=bad):
                payload = _valid_minimal_payload()
                payload["state_probabilities"] = bad
                errors = validate_projection_result(payload)
                matches = [
                    e for e in errors
                    if e.startswith("invalid type: state_probabilities")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 12. state_probabilities invalid state key returns error
# ---------------------------------------------------------------------------

class StateProbabilitiesKeyTests(unittest.TestCase):
    def test_state_probabilities_invalid_key_returns_error(self) -> None:
        payload = _valid_minimal_payload()
        payload["state_probabilities"] = {
            "大涨": 0.20,
            "横盘": 0.30,  # invalid
            "震荡": 0.50,
        }
        errors = validate_projection_result(payload)
        self.assertTrue(
            any(
                e.startswith(
                    "invalid value: state_probabilities key '横盘'"
                )
                for e in errors
            ),
            msg=f"expected state_probabilities key error; got {errors}",
        )


# ---------------------------------------------------------------------------
# 13. state_probabilities value outside [0, 1] returns error
# ---------------------------------------------------------------------------

class StateProbabilitiesValueRangeTests(unittest.TestCase):
    def test_negative_value_returns_error(self) -> None:
        payload = _valid_minimal_payload()
        payload["state_probabilities"] = {
            "大涨": -0.1,
            "小涨": 0.40,
            "震荡": 0.30,
            "小跌": 0.20,
            "大跌": 0.20,
        }
        errors = validate_projection_result(payload)
        matches = [
            e for e in errors
            if e.startswith("invalid value: state_probabilities['大涨']")
        ]
        self.assertEqual(len(matches), 1)

    def test_value_above_one_returns_error(self) -> None:
        payload = _valid_minimal_payload()
        payload["state_probabilities"] = {
            "大涨": 1.5,
            "小涨": -0.0,
            "震荡": 0.0,
            "小跌": 0.0,
            "大跌": 0.0,
        }
        errors = validate_projection_result(payload)
        matches = [
            e for e in errors
            if e.startswith("invalid value: state_probabilities['大涨']")
        ]
        self.assertEqual(len(matches), 1)

    def test_non_numeric_value_returns_type_error(self) -> None:
        payload = _valid_minimal_payload()
        payload["state_probabilities"] = {
            "大涨": "0.40",
            "小涨": 0.40,
            "震荡": 0.20,
            "小跌": 0.0,
            "大跌": 0.0,
        }
        errors = validate_projection_result(payload)
        self.assertTrue(
            any(
                e.startswith("invalid type: state_probabilities['大涨']")
                for e in errors
            ),
            msg=f"expected type error for non-numeric value; got {errors}",
        )

    def test_bool_value_rejected_as_non_numeric(self) -> None:
        # Guard against ``bool`` being accepted via Python's ``isinstance(True, int)``.
        payload = _valid_minimal_payload()
        payload["state_probabilities"] = {
            "大涨": True,
            "小涨": 0.40,
            "震荡": 0.20,
            "小跌": 0.0,
            "大跌": 0.0,
        }
        errors = validate_projection_result(payload)
        self.assertTrue(
            any(
                e.startswith("invalid type: state_probabilities['大涨']")
                for e in errors
            ),
            msg=f"expected type error for bool value; got {errors}",
        )


# ---------------------------------------------------------------------------
# 14. state_probabilities sum not close to 1 returns warning
# ---------------------------------------------------------------------------

class StateProbabilitiesSumTests(unittest.TestCase):
    def test_far_from_one_emits_warning(self) -> None:
        payload = _valid_minimal_payload()
        payload["state_probabilities"] = {
            "大涨": 0.10,
            "小涨": 0.10,
            "震荡": 0.10,
            "小跌": 0.10,
            "大跌": 0.10,
        }
        errors = validate_projection_result(payload)
        warnings = [
            e for e in errors
            if e.startswith("warning: state_probabilities sum")
        ]
        self.assertEqual(len(warnings), 1)

    def test_close_to_one_does_not_emit_warning(self) -> None:
        payload = _valid_minimal_payload()
        payload["state_probabilities"] = {
            "大涨": 0.20,
            "小涨": 0.20,
            "震荡": 0.20,
            "小跌": 0.20,
            "大跌": 0.20,
        }
        errors = validate_projection_result(payload)
        warnings = [e for e in errors if e.startswith("warning:")]
        self.assertEqual(warnings, [])

    def test_validator_does_not_normalize_probabilities(self) -> None:
        # The validator emits an advisory but does NOT touch the values.
        payload = _valid_minimal_payload()
        payload["state_probabilities"] = {
            "大涨": 0.10,
            "小涨": 0.10,
            "震荡": 0.10,
            "小跌": 0.10,
            "大跌": 0.10,
        }
        snapshot = copy.deepcopy(payload["state_probabilities"])
        validate_projection_result(payload)
        self.assertEqual(payload["state_probabilities"], snapshot)


# ---------------------------------------------------------------------------
# 15. Missing non_mutation_confirmations required keys returns error
# ---------------------------------------------------------------------------

class MissingNonMutationConfirmationKeysTests(unittest.TestCase):
    def test_each_missing_key_yields_missing_field_error(self) -> None:
        for key in (
            "projection_did_not_read_exclusion",
            "projection_did_not_read_confidence",
            "projection_did_not_read_final_report",
            "projection_did_not_read_future_outcome",
        ):
            with self.subTest(key=key):
                payload = _valid_minimal_payload()
                payload["non_mutation_confirmations"].pop(key)
                errors = validate_projection_result(payload)
                self.assertIn(
                    f"missing field: non_mutation_confirmations.{key}",
                    errors,
                )


# ---------------------------------------------------------------------------
# 16. non_mutation_confirmations required values must be True
# ---------------------------------------------------------------------------

class NonMutationConfirmationValueTests(unittest.TestCase):
    def test_each_required_key_must_be_true(self) -> None:
        for key in (
            "projection_did_not_read_exclusion",
            "projection_did_not_read_confidence",
            "projection_did_not_read_final_report",
            "projection_did_not_read_future_outcome",
        ):
            for bad in (False, None, 0, 1, "true", []):
                with self.subTest(key=key, value=bad):
                    payload = _valid_minimal_payload()
                    payload["non_mutation_confirmations"][key] = bad
                    errors = validate_projection_result(payload)
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
# 17. Forbidden exclusion / confidence / final sections at top level rejected
# ---------------------------------------------------------------------------

class ForbiddenDownstreamSectionsTests(unittest.TestCase):
    def test_forbidden_downstream_sections_at_top_level(self) -> None:
        for forbidden in (
            "exclusion_result",
            "confidence_result",
            "final_report",
            "review_result",
            "evaluation_result",
            "most_unlikely_state",
            "ranked_unlikely_states",
            "excluded_states",
            "triggered_rules",
            "false_exclusion_risk",
        ):
            with self.subTest(forbidden=forbidden):
                payload = _valid_minimal_payload()
                payload[forbidden] = "anything"
                errors = validate_projection_result(payload)
                self.assertIn(
                    f"forbidden field: {forbidden} at top-level",
                    errors,
                    msg=f"validator did not flag {forbidden}; got {errors}",
                )


# ---------------------------------------------------------------------------
# 18. Forbidden trading / hard / forced fields at top level rejected
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
                errors = validate_projection_result(payload)
                self.assertIn(
                    f"forbidden field: {forbidden} at top-level",
                    errors,
                    msg=f"validator did not flag {forbidden}; got {errors}",
                )


# ---------------------------------------------------------------------------
# 19. Legacy final / bridge fields rejected
# ---------------------------------------------------------------------------

class ForbiddenLegacyBridgeFieldsTests(unittest.TestCase):
    def test_forbidden_legacy_bridge_fields_at_top_level(self) -> None:
        for forbidden in (
            "final_direction",
            "final_confidence",
            "final_bias",
            "final_projection",
            "primary_projection",
            "peer_adjustment",
            "path_risk",
            "predicted_top1",
            "predicted_top2",
        ):
            with self.subTest(forbidden=forbidden):
                payload = _valid_minimal_payload()
                payload[forbidden] = "anything"
                errors = validate_projection_result(payload)
                self.assertIn(
                    f"forbidden field: {forbidden} at top-level",
                    errors,
                    msg=f"validator did not flag {forbidden}; got {errors}",
                )


# ---------------------------------------------------------------------------
# 20. Validator does not mutate input
# ---------------------------------------------------------------------------

class NonMutationTests(unittest.TestCase):
    def test_valid_payload_unchanged(self) -> None:
        payload = _valid_minimal_payload()
        snapshot = copy.deepcopy(payload)
        validate_projection_result(payload)
        self.assertEqual(payload, snapshot)

    def test_invalid_payload_unchanged(self) -> None:
        payload = _valid_minimal_payload()
        payload.pop("most_likely_state")
        snapshot = copy.deepcopy(payload)
        errors = validate_projection_result(payload)
        self.assertNotEqual(errors, [])
        self.assertEqual(payload, snapshot)

    def test_pure_function_repeatable_output(self) -> None:
        payload = _valid_minimal_payload()
        first = validate_projection_result(payload)
        second = validate_projection_result(payload)
        self.assertEqual(first, second)


# ---------------------------------------------------------------------------
# 21. Module import boundary
# ---------------------------------------------------------------------------

class ImportBoundaryTests(unittest.TestCase):
    """``services.projection_result_contract`` must remain a pure shape
    validator with zero coupling to any business / orchestrator / UI / DB
    module."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = _read("services/projection_result_contract.py")

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
            "from services.main_projection_layer",
            "import services.main_projection_layer",
            "from services.exclusion_layer",
            "import services.exclusion_layer",
            "from services.confidence_evaluator",
            "import services.confidence_evaluator",
            "from services.final_decision",
            "import services.final_decision",
            "from services.consistency_layer",
            "import services.consistency_layer",
            "from services.review_orchestrator",
            "import services.review_orchestrator",
            "from services.historical_probability",
            "import services.historical_probability",
            "from services.predict_summary",
            "import services.predict_summary",
            "from services.ai_summary",
            "import services.ai_summary",
            "from services.feature_payload_contract",
            "import services.feature_payload_contract",
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
                msg=f"services.projection_result_contract must not contain `{f}`",
            )

    def test_no_io_or_llm_calls(self) -> None:
        for f in ("open(", "Path(", "requests.", "urllib", "http.client",
                  "openai", "OpenAI", "anthropic", "Anthropic"):
            self.assertNotIn(
                f,
                self.source,
                msg=f"services.projection_result_contract must not contain `{f}`",
            )


# ---------------------------------------------------------------------------
# Sanity check on module reference
# ---------------------------------------------------------------------------

class ModuleReferenceTests(unittest.TestCase):
    def test_validate_function_lives_in_module(self) -> None:
        self.assertEqual(
            validate_projection_result.__module__,
            "services.projection_result_contract",
        )
        self.assertIs(
            prc_mod.validate_projection_result,
            validate_projection_result,
        )


if __name__ == "__main__":
    unittest.main()
