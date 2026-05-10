"""Boundary + contract tests for ``services.exclusion_result_contract``
(Step 18D / PR-EXCL-1).

Spec source of truth:

- `tasks/record_1_0_architecture_reset_canonical_principles.md` §8 (Branch 4)
- `tasks/record_07b_exclusion_system_contract.md` §3 / §9
- `tasks/record_17h_exclusion_layer_rebuild_plan.md` §8 / §10 / §14
- `tasks/record_18a_first_layer_based_implementation_batch_selection.md` §13

PR-EXCL-1 is a **pure addition** — a new schema constant + validator with
zero changes to any existing business code. This suite verifies:

1.  valid minimal payload returns ``[]``
2.  non-dict payload returns error (no raise)
3.  wrong ``schema_version`` returns ``invalid value:``
4.  each missing top-level section returns ``missing section:``
5.  ``kind`` must equal ``"exclusion"``
6.  ``symbol`` must be a non-empty string
7.  ``ready`` must be a bool
8.  ``most_unlikely_state`` must be a valid state (or None when ready=False)
9.  ``most_unlikely_state == None`` with ready=True returns error
10. ``ranked_unlikely_states`` must be a list
11. invalid state in ``ranked_unlikely_states`` returns error
12. ``state_impossibility_scores`` must be a dict
13. invalid state key in ``state_impossibility_scores`` returns error
14. ``state_impossibility_scores`` value outside ``[0, 1]`` returns error
15. ``excluded_states`` must be a list
16. invalid state in ``excluded_states`` returns error
17. ``triggered_rules`` must be a list
18. ``triggered_rules`` item must be a non-empty string
19. ``false_exclusion_risk`` must be a valid enum
20. ``evidence`` must be a dict or list
21. ``rationale`` must be a str or list
22. ``warnings`` must be a list
23. missing ``non_mutation_confirmations`` required keys returns error
24. ``non_mutation_confirmations`` required values must be ``True``
25. forbidden projection / confidence / final sections at top level rejected
26. legacy ``triggered_rule`` (single) at top level rejected
27. forbidden trading / hard / forced fields at top level rejected
28. legacy final / confidence fields rejected
29. validator does not mutate input payload
30. module import boundary: the validator does **not** import any
    business / orchestrator / UI / DB module
31. ``EXCLUSION_RESULT_SECTIONS`` matches the expected fixed order
32. ``EXCLUSION_RESULT_SCHEMA_VERSION`` equals ``"exclusion_result.v1"``
33. ``EXCLUSION_RESULT_KIND`` equals ``"exclusion"``
34. ``VALID_STATES`` equals the 5-state vocabulary in fixed order
35. ``VALID_FALSE_EXCLUSION_RISK`` equals ``("low", "medium", "high", "unknown")``

The validator must never raise (returns errors as a list).
"""

from __future__ import annotations

import copy
import unittest
from pathlib import Path

import services.exclusion_result_contract as erc_mod
from services.exclusion_result_contract import (
    EXCLUSION_RESULT_KIND,
    EXCLUSION_RESULT_SCHEMA_VERSION,
    EXCLUSION_RESULT_SECTIONS,
    FORBIDDEN_FIELDS,
    VALID_FALSE_EXCLUSION_RISK,
    VALID_STATES,
    validate_exclusion_result,
)


_REPO_ROOT = Path(__file__).resolve().parent.parent


def _read(rel: str) -> str:
    return (_REPO_ROOT / rel).read_text(encoding="utf-8")


def _valid_minimal_payload() -> dict:
    """Build a payload that satisfies every PR-EXCL-1 shape rule."""
    return {
        "schema_version": EXCLUSION_RESULT_SCHEMA_VERSION,
        "kind": EXCLUSION_RESULT_KIND,
        "symbol": "AVGO",
        "ready": True,
        "most_unlikely_state": "大跌",
        "ranked_unlikely_states": ["大跌", "小跌", "震荡", "小涨", "大涨"],
        "state_impossibility_scores": {
            "大涨": 0.10,
            "小涨": 0.20,
            "震荡": 0.30,
            "小跌": 0.50,
            "大跌": 0.80,
        },
        "excluded_states": ["大跌"],
        "triggered_rules": ["exclude_big_down"],
        "false_exclusion_risk": "low",
        "evidence": [],
        "rationale": [],
        "warnings": [],
        "feature_snapshot_ref": None,
        "peer_alignment_summary": {},
        "non_mutation_confirmations": {
            "exclusion_did_not_read_projection": True,
            "exclusion_did_not_read_confidence": True,
            "exclusion_did_not_read_final_report": True,
            "exclusion_did_not_read_future_outcome": True,
        },
    }


# ---------------------------------------------------------------------------
# 0. Constants (test items 31 + 32 + 33 + 34 + 35)
# ---------------------------------------------------------------------------

class ExclusionResultConstantsTests(unittest.TestCase):
    def test_schema_version_is_v1(self) -> None:
        self.assertEqual(EXCLUSION_RESULT_SCHEMA_VERSION, "exclusion_result.v1")

    def test_kind_is_exclusion(self) -> None:
        self.assertEqual(EXCLUSION_RESULT_KIND, "exclusion")

    def test_sixteen_top_level_sections_in_fixed_order(self) -> None:
        self.assertEqual(
            EXCLUSION_RESULT_SECTIONS,
            (
                "schema_version",
                "kind",
                "symbol",
                "ready",
                "most_unlikely_state",
                "ranked_unlikely_states",
                "state_impossibility_scores",
                "excluded_states",
                "triggered_rules",
                "false_exclusion_risk",
                "evidence",
                "rationale",
                "warnings",
                "feature_snapshot_ref",
                "peer_alignment_summary",
                "non_mutation_confirmations",
            ),
        )

    def test_valid_states_are_five_state_vocabulary(self) -> None:
        self.assertEqual(VALID_STATES, ("大涨", "小涨", "震荡", "小跌", "大跌"))

    def test_valid_false_exclusion_risk_enum(self) -> None:
        self.assertEqual(
            VALID_FALSE_EXCLUSION_RISK, ("low", "medium", "high", "unknown")
        )

    def test_forbidden_fields_includes_projection_and_downstream(self) -> None:
        for required in (
            "most_likely_state",
            "ranked_states",
            "state_probabilities",
            "predicted_top1",
            "predicted_top2",
            "projection_result",
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
            "combined_confidence",
            "agreement_status",
            "conflict_level",
            "final_bias",
            "final_projection",
            "primary_projection",
            "triggered_rule",  # legacy single alias
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
        errors = validate_exclusion_result(_valid_minimal_payload())
        self.assertEqual(errors, [], msg=f"unexpected errors: {errors}")

    def test_ready_false_with_none_most_unlikely_state_is_valid(self) -> None:
        payload = _valid_minimal_payload()
        payload["ready"] = False
        payload["most_unlikely_state"] = None
        payload["excluded_states"] = []
        payload["triggered_rules"] = []
        errors = validate_exclusion_result(payload)
        self.assertEqual(errors, [], msg=f"unexpected errors: {errors}")

    def test_each_valid_false_exclusion_risk_is_accepted(self) -> None:
        for risk in VALID_FALSE_EXCLUSION_RISK:
            with self.subTest(false_exclusion_risk=risk):
                payload = _valid_minimal_payload()
                payload["false_exclusion_risk"] = risk
                errors = validate_exclusion_result(payload)
                self.assertEqual(
                    errors, [], msg=f"unexpected errors for {risk}: {errors}"
                )


# ---------------------------------------------------------------------------
# 2. Non-dict payload returns error (no raise)
# ---------------------------------------------------------------------------

class NonDictPayloadTests(unittest.TestCase):
    def test_none_payload(self) -> None:
        errors = validate_exclusion_result(None)
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("invalid type: payload expected dict"))

    def test_list_payload(self) -> None:
        errors = validate_exclusion_result([])
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("invalid type: payload expected dict"))

    def test_str_payload(self) -> None:
        errors = validate_exclusion_result("not a dict")
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("invalid type: payload expected dict"))

    def test_int_payload(self) -> None:
        errors = validate_exclusion_result(42)
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("invalid type: payload expected dict"))

    def test_non_dict_input_does_not_raise(self) -> None:
        for value in (None, 42, "x", [], (), 1.5, object()):
            with self.subTest(value=value):
                result = validate_exclusion_result(value)
                self.assertIsInstance(result, list)


# ---------------------------------------------------------------------------
# 3. Wrong schema_version
# ---------------------------------------------------------------------------

class SchemaVersionTests(unittest.TestCase):
    def test_wrong_schema_version_returns_invalid_value_error(self) -> None:
        payload = _valid_minimal_payload()
        payload["schema_version"] = "exclusion_result.v2"
        errors = validate_exclusion_result(payload)
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
        for section in EXCLUSION_RESULT_SECTIONS:
            with self.subTest(section=section):
                payload = _valid_minimal_payload()
                payload.pop(section)
                errors = validate_exclusion_result(payload)
                self.assertIn(
                    f"missing section: {section}",
                    errors,
                    msg=f"validator did not catch missing {section}; got {errors}",
                )


# ---------------------------------------------------------------------------
# 5. kind must equal "exclusion"
# ---------------------------------------------------------------------------

class KindTests(unittest.TestCase):
    def test_wrong_kind_returns_invalid_value_error(self) -> None:
        for bad in ("exclusion_layer", "projection", "anti_false_exclusion", "", None, 42):
            with self.subTest(kind=bad):
                payload = _valid_minimal_payload()
                payload["kind"] = bad
                errors = validate_exclusion_result(payload)
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
                errors = validate_exclusion_result(payload)
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
                errors = validate_exclusion_result(payload)
                matches = [e for e in errors if e.startswith("invalid type: ready")]
                self.assertEqual(
                    len(matches), 1,
                    msg=f"expected one ready type error for {bad!r}; got {matches}",
                )


# ---------------------------------------------------------------------------
# 8. most_unlikely_state must be valid state (or None when ready=False)
# ---------------------------------------------------------------------------

class MostUnlikelyStateTests(unittest.TestCase):
    def test_most_unlikely_state_must_be_valid(self) -> None:
        for bad in ("BIG_UP", "neutral", "横盘", "", 42):
            with self.subTest(state=bad):
                payload = _valid_minimal_payload()
                payload["most_unlikely_state"] = bad
                errors = validate_exclusion_result(payload)
                matches = [
                    e for e in errors
                    if e.startswith("invalid value: most_unlikely_state expected")
                ]
                self.assertEqual(
                    len(matches), 1,
                    msg=f"expected one most_unlikely_state error for {bad!r}; got {matches}",
                )

    def test_most_unlikely_state_none_when_ready_true_is_error(self) -> None:
        payload = _valid_minimal_payload()
        payload["ready"] = True
        payload["most_unlikely_state"] = None
        errors = validate_exclusion_result(payload)
        self.assertIn(
            "invalid value: most_unlikely_state may be None only when ready=False",
            errors,
        )

    def test_most_unlikely_state_none_when_ready_false_is_ok(self) -> None:
        payload = _valid_minimal_payload()
        payload["ready"] = False
        payload["most_unlikely_state"] = None
        payload["excluded_states"] = []
        payload["triggered_rules"] = []
        errors = validate_exclusion_result(payload)
        bad = [
            e for e in errors
            if e.startswith("invalid value: most_unlikely_state")
        ]
        self.assertEqual(bad, [])

    def test_each_valid_state_is_accepted(self) -> None:
        for state in VALID_STATES:
            with self.subTest(state=state):
                payload = _valid_minimal_payload()
                payload["most_unlikely_state"] = state
                payload["excluded_states"] = [state]
                errors = validate_exclusion_result(payload)
                bad = [
                    e for e in errors
                    if e.startswith("invalid value: most_unlikely_state")
                ]
                self.assertEqual(bad, [], msg=f"errors for {state!r}: {errors}")


# ---------------------------------------------------------------------------
# 10. ranked_unlikely_states must be list
# ---------------------------------------------------------------------------

class RankedUnlikelyStatesTypeTests(unittest.TestCase):
    def test_ranked_unlikely_states_must_be_list(self) -> None:
        for bad in ({}, "list", 42, None):
            with self.subTest(ranked_unlikely_states=bad):
                payload = _valid_minimal_payload()
                payload["ranked_unlikely_states"] = bad
                errors = validate_exclusion_result(payload)
                matches = [
                    e for e in errors
                    if e.startswith("invalid type: ranked_unlikely_states")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 11. ranked_unlikely_states invalid state returns error
# ---------------------------------------------------------------------------

class RankedUnlikelyStatesValueTests(unittest.TestCase):
    def test_ranked_unlikely_states_invalid_state_returns_error(self) -> None:
        payload = _valid_minimal_payload()
        payload["ranked_unlikely_states"] = ["大跌", "BAD", "小跌"]
        errors = validate_exclusion_result(payload)
        self.assertTrue(
            any(
                e.startswith("invalid value: ranked_unlikely_states[1] expected")
                for e in errors
            ),
            msg=f"expected ranked_unlikely_states[1] error; got {errors}",
        )

    def test_empty_ranked_unlikely_states_is_allowed(self) -> None:
        payload = _valid_minimal_payload()
        payload["ranked_unlikely_states"] = []
        errors = validate_exclusion_result(payload)
        self.assertEqual(errors, [])


# ---------------------------------------------------------------------------
# 12. state_impossibility_scores must be dict
# ---------------------------------------------------------------------------

class StateImpossibilityScoresTypeTests(unittest.TestCase):
    def test_state_impossibility_scores_must_be_dict(self) -> None:
        for bad in ([], "dict", 42, None):
            with self.subTest(state_impossibility_scores=bad):
                payload = _valid_minimal_payload()
                payload["state_impossibility_scores"] = bad
                errors = validate_exclusion_result(payload)
                matches = [
                    e for e in errors
                    if e.startswith("invalid type: state_impossibility_scores")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 13. state_impossibility_scores invalid state key returns error
# ---------------------------------------------------------------------------

class StateImpossibilityScoresKeyTests(unittest.TestCase):
    def test_state_impossibility_scores_invalid_key_returns_error(self) -> None:
        payload = _valid_minimal_payload()
        payload["state_impossibility_scores"] = {
            "大涨": 0.20,
            "横盘": 0.30,
            "震荡": 0.10,
        }
        errors = validate_exclusion_result(payload)
        self.assertTrue(
            any(
                e.startswith(
                    "invalid value: state_impossibility_scores key '横盘'"
                )
                for e in errors
            ),
            msg=f"expected state_impossibility_scores key error; got {errors}",
        )


# ---------------------------------------------------------------------------
# 14. state_impossibility_scores value outside [0, 1] returns error
# ---------------------------------------------------------------------------

class StateImpossibilityScoresValueRangeTests(unittest.TestCase):
    def test_negative_value_returns_error(self) -> None:
        payload = _valid_minimal_payload()
        payload["state_impossibility_scores"] = {
            "大涨": -0.1,
            "小涨": 0.1,
            "震荡": 0.2,
            "小跌": 0.2,
            "大跌": 0.7,
        }
        errors = validate_exclusion_result(payload)
        matches = [
            e for e in errors
            if e.startswith("invalid value: state_impossibility_scores['大涨']")
        ]
        self.assertEqual(len(matches), 1)

    def test_value_above_one_returns_error(self) -> None:
        payload = _valid_minimal_payload()
        payload["state_impossibility_scores"] = {
            "大涨": 1.5,
            "小涨": 0.0,
            "震荡": 0.0,
            "小跌": 0.0,
            "大跌": 0.0,
        }
        errors = validate_exclusion_result(payload)
        matches = [
            e for e in errors
            if e.startswith("invalid value: state_impossibility_scores['大涨']")
        ]
        self.assertEqual(len(matches), 1)

    def test_non_numeric_value_returns_type_error(self) -> None:
        payload = _valid_minimal_payload()
        payload["state_impossibility_scores"] = {
            "大涨": "0.40",
            "小涨": 0.0,
            "震荡": 0.0,
            "小跌": 0.0,
            "大跌": 0.0,
        }
        errors = validate_exclusion_result(payload)
        self.assertTrue(
            any(
                e.startswith("invalid type: state_impossibility_scores['大涨']")
                for e in errors
            ),
            msg=f"expected type error for non-numeric value; got {errors}",
        )

    def test_bool_value_rejected_as_non_numeric(self) -> None:
        payload = _valid_minimal_payload()
        payload["state_impossibility_scores"] = {
            "大涨": True,
            "小涨": 0.0,
            "震荡": 0.0,
            "小跌": 0.0,
            "大跌": 0.0,
        }
        errors = validate_exclusion_result(payload)
        self.assertTrue(
            any(
                e.startswith("invalid type: state_impossibility_scores['大涨']")
                for e in errors
            ),
            msg=f"expected type error for bool value; got {errors}",
        )

    def test_no_sum_warning_emitted(self) -> None:
        # Impossibility scores are NOT a probability distribution — the
        # validator must not emit a sum-near-1 advisory. (17H §8.3 / §10)
        payload = _valid_minimal_payload()
        payload["state_impossibility_scores"] = {
            "大涨": 0.10,
            "小涨": 0.10,
            "震荡": 0.10,
            "小跌": 0.10,
            "大跌": 0.10,
        }
        errors = validate_exclusion_result(payload)
        sum_warnings = [e for e in errors if e.startswith("warning:")]
        self.assertEqual(sum_warnings, [])


# ---------------------------------------------------------------------------
# 15. excluded_states must be list
# ---------------------------------------------------------------------------

class ExcludedStatesTypeTests(unittest.TestCase):
    def test_excluded_states_must_be_list(self) -> None:
        for bad in ({}, "list", 42, None):
            with self.subTest(excluded_states=bad):
                payload = _valid_minimal_payload()
                payload["excluded_states"] = bad
                errors = validate_exclusion_result(payload)
                matches = [
                    e for e in errors
                    if e.startswith("invalid type: excluded_states")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 16. excluded_states invalid state returns error
# ---------------------------------------------------------------------------

class ExcludedStatesValueTests(unittest.TestCase):
    def test_excluded_states_invalid_state_returns_error(self) -> None:
        payload = _valid_minimal_payload()
        payload["excluded_states"] = ["大跌", "BAD"]
        errors = validate_exclusion_result(payload)
        self.assertTrue(
            any(
                e.startswith("invalid value: excluded_states[1] expected")
                for e in errors
            ),
            msg=f"expected excluded_states[1] error; got {errors}",
        )

    def test_empty_excluded_states_is_allowed(self) -> None:
        payload = _valid_minimal_payload()
        payload["excluded_states"] = []
        errors = validate_exclusion_result(payload)
        self.assertEqual(errors, [])


# ---------------------------------------------------------------------------
# 17. triggered_rules must be list
# ---------------------------------------------------------------------------

class TriggeredRulesTypeTests(unittest.TestCase):
    def test_triggered_rules_must_be_list(self) -> None:
        for bad in ({}, "list", 42, None):
            with self.subTest(triggered_rules=bad):
                payload = _valid_minimal_payload()
                payload["triggered_rules"] = bad
                errors = validate_exclusion_result(payload)
                matches = [
                    e for e in errors
                    if e.startswith("invalid type: triggered_rules")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 18. triggered_rules item must be non-empty string
# ---------------------------------------------------------------------------

class TriggeredRulesValueTests(unittest.TestCase):
    def test_triggered_rules_empty_string_returns_error(self) -> None:
        payload = _valid_minimal_payload()
        payload["triggered_rules"] = ["exclude_big_down", ""]
        errors = validate_exclusion_result(payload)
        self.assertTrue(
            any(
                e.startswith("invalid value: triggered_rules[1] expected")
                for e in errors
            )
        )

    def test_triggered_rules_non_string_returns_error(self) -> None:
        payload = _valid_minimal_payload()
        payload["triggered_rules"] = ["exclude_big_down", 42, None]
        errors = validate_exclusion_result(payload)
        for index in (1, 2):
            self.assertTrue(
                any(
                    e.startswith(f"invalid value: triggered_rules[{index}]")
                    for e in errors
                ),
                msg=f"expected triggered_rules[{index}] error; got {errors}",
            )

    def test_empty_triggered_rules_is_allowed(self) -> None:
        # 17H §8 — when action="allow", triggered_rules may be []. Keep
        # most_unlikely_state non-None / ready=True for this case (an
        # operator-side quirk; producer may choose either combination).
        payload = _valid_minimal_payload()
        payload["triggered_rules"] = []
        payload["excluded_states"] = []
        errors = validate_exclusion_result(payload)
        bad = [
            e for e in errors
            if e.startswith("invalid value: triggered_rules")
            or e.startswith("invalid type: triggered_rules")
        ]
        self.assertEqual(bad, [])


# ---------------------------------------------------------------------------
# 19. false_exclusion_risk must be valid enum
# ---------------------------------------------------------------------------

class FalseExclusionRiskTests(unittest.TestCase):
    def test_invalid_false_exclusion_risk_returns_error(self) -> None:
        for bad in ("LOW", "extreme", "", None, 42, True):
            with self.subTest(false_exclusion_risk=bad):
                payload = _valid_minimal_payload()
                payload["false_exclusion_risk"] = bad
                errors = validate_exclusion_result(payload)
                matches = [
                    e for e in errors
                    if e.startswith("invalid value: false_exclusion_risk")
                ]
                self.assertEqual(
                    len(matches), 1,
                    msg=f"expected one false_exclusion_risk error for {bad!r}; got {matches}",
                )


# ---------------------------------------------------------------------------
# 20. evidence must be dict or list
# ---------------------------------------------------------------------------

class EvidenceTypeTests(unittest.TestCase):
    def test_evidence_must_be_dict_or_list(self) -> None:
        for bad in ("string", 42, None, True):
            with self.subTest(evidence=bad):
                payload = _valid_minimal_payload()
                payload["evidence"] = bad
                errors = validate_exclusion_result(payload)
                matches = [
                    e for e in errors
                    if e.startswith("invalid type: evidence")
                ]
                self.assertEqual(len(matches), 1)

    def test_evidence_dict_is_ok(self) -> None:
        payload = _valid_minimal_payload()
        payload["evidence"] = {"rare_event": "bullish gap"}
        errors = validate_exclusion_result(payload)
        bad = [e for e in errors if e.startswith("invalid type: evidence")]
        self.assertEqual(bad, [])


# ---------------------------------------------------------------------------
# 21. rationale must be str or list
# ---------------------------------------------------------------------------

class RationaleTypeTests(unittest.TestCase):
    def test_rationale_must_be_str_or_list(self) -> None:
        for bad in ({}, 42, None, True):
            with self.subTest(rationale=bad):
                payload = _valid_minimal_payload()
                payload["rationale"] = bad
                errors = validate_exclusion_result(payload)
                matches = [
                    e for e in errors
                    if e.startswith("invalid type: rationale")
                ]
                self.assertEqual(len(matches), 1)

    def test_rationale_str_is_ok(self) -> None:
        payload = _valid_minimal_payload()
        payload["rationale"] = "tail risk dampened by peer alignment"
        errors = validate_exclusion_result(payload)
        bad = [e for e in errors if e.startswith("invalid type: rationale")]
        self.assertEqual(bad, [])


# ---------------------------------------------------------------------------
# 22. warnings must be list
# ---------------------------------------------------------------------------

class WarningsTypeTests(unittest.TestCase):
    def test_warnings_must_be_list(self) -> None:
        for bad in ({}, "list", 42, None):
            with self.subTest(warnings=bad):
                payload = _valid_minimal_payload()
                payload["warnings"] = bad
                errors = validate_exclusion_result(payload)
                matches = [
                    e for e in errors
                    if e.startswith("invalid type: warnings")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 23. Missing non_mutation_confirmations required keys returns error
# ---------------------------------------------------------------------------

class MissingNonMutationConfirmationKeysTests(unittest.TestCase):
    def test_each_missing_key_yields_missing_field_error(self) -> None:
        for key in (
            "exclusion_did_not_read_projection",
            "exclusion_did_not_read_confidence",
            "exclusion_did_not_read_final_report",
            "exclusion_did_not_read_future_outcome",
        ):
            with self.subTest(key=key):
                payload = _valid_minimal_payload()
                payload["non_mutation_confirmations"].pop(key)
                errors = validate_exclusion_result(payload)
                self.assertIn(
                    f"missing field: non_mutation_confirmations.{key}",
                    errors,
                )


# ---------------------------------------------------------------------------
# 24. non_mutation_confirmations required values must be True
# ---------------------------------------------------------------------------

class NonMutationConfirmationValueTests(unittest.TestCase):
    def test_each_required_key_must_be_true(self) -> None:
        for key in (
            "exclusion_did_not_read_projection",
            "exclusion_did_not_read_confidence",
            "exclusion_did_not_read_final_report",
            "exclusion_did_not_read_future_outcome",
        ):
            for bad in (False, None, 0, 1, "true", []):
                with self.subTest(key=key, value=bad):
                    payload = _valid_minimal_payload()
                    payload["non_mutation_confirmations"][key] = bad
                    errors = validate_exclusion_result(payload)
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
# 25. Forbidden projection / confidence / final sections at top level rejected
# ---------------------------------------------------------------------------

class ForbiddenDownstreamSectionsTests(unittest.TestCase):
    def test_forbidden_projection_and_downstream_at_top_level(self) -> None:
        for forbidden in (
            "projection_result",
            "confidence_result",
            "final_report",
            "review_result",
            "evaluation_result",
            "most_likely_state",
            "ranked_states",
            "state_probabilities",
            "predicted_top1",
            "predicted_top2",
        ):
            with self.subTest(forbidden=forbidden):
                payload = _valid_minimal_payload()
                payload[forbidden] = "anything"
                errors = validate_exclusion_result(payload)
                self.assertIn(
                    f"forbidden field: {forbidden} at top-level",
                    errors,
                    msg=f"validator did not flag {forbidden}; got {errors}",
                )


# ---------------------------------------------------------------------------
# 26. Legacy triggered_rule (single) at top level rejected
# ---------------------------------------------------------------------------

class ForbiddenLegacyTriggeredRuleTests(unittest.TestCase):
    def test_legacy_triggered_rule_at_top_level_is_rejected(self) -> None:
        payload = _valid_minimal_payload()
        payload["triggered_rule"] = "exclude_big_down"
        errors = validate_exclusion_result(payload)
        self.assertIn(
            "forbidden field: triggered_rule at top-level",
            errors,
            msg=f"validator did not flag legacy triggered_rule; got {errors}",
        )


# ---------------------------------------------------------------------------
# 27. Forbidden trading / hard / forced fields at top level rejected
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
                errors = validate_exclusion_result(payload)
                self.assertIn(
                    f"forbidden field: {forbidden} at top-level",
                    errors,
                    msg=f"validator did not flag {forbidden}; got {errors}",
                )


# ---------------------------------------------------------------------------
# 28. Legacy final / confidence fields rejected
# ---------------------------------------------------------------------------

class ForbiddenLegacyFinalConfidenceFieldsTests(unittest.TestCase):
    def test_forbidden_legacy_final_and_confidence_fields(self) -> None:
        for forbidden in (
            "final_direction",
            "final_confidence",
            "combined_confidence",
            "agreement_status",
            "conflict_level",
            "final_bias",
            "final_projection",
            "primary_projection",
        ):
            with self.subTest(forbidden=forbidden):
                payload = _valid_minimal_payload()
                payload[forbidden] = "anything"
                errors = validate_exclusion_result(payload)
                self.assertIn(
                    f"forbidden field: {forbidden} at top-level",
                    errors,
                    msg=f"validator did not flag {forbidden}; got {errors}",
                )


# ---------------------------------------------------------------------------
# 29. Validator does not mutate input
# ---------------------------------------------------------------------------

class NonMutationTests(unittest.TestCase):
    def test_valid_payload_unchanged(self) -> None:
        payload = _valid_minimal_payload()
        snapshot = copy.deepcopy(payload)
        validate_exclusion_result(payload)
        self.assertEqual(payload, snapshot)

    def test_invalid_payload_unchanged(self) -> None:
        payload = _valid_minimal_payload()
        payload.pop("most_unlikely_state")
        snapshot = copy.deepcopy(payload)
        errors = validate_exclusion_result(payload)
        self.assertNotEqual(errors, [])
        self.assertEqual(payload, snapshot)

    def test_pure_function_repeatable_output(self) -> None:
        payload = _valid_minimal_payload()
        first = validate_exclusion_result(payload)
        second = validate_exclusion_result(payload)
        self.assertEqual(first, second)


# ---------------------------------------------------------------------------
# 30. Module import boundary
# ---------------------------------------------------------------------------

class ImportBoundaryTests(unittest.TestCase):
    """``services.exclusion_result_contract`` must remain a pure shape
    validator with zero coupling to any business / orchestrator / UI / DB
    module."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = _read("services/exclusion_result_contract.py")

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
            "from services.exclusion_layer",
            "import services.exclusion_layer",
            "from services.peer_alignment",
            "import services.peer_alignment",
            "from services.main_projection_layer",
            "import services.main_projection_layer",
            "from services.confidence_evaluator",
            "import services.confidence_evaluator",
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
                msg=f"services.exclusion_result_contract must not contain `{f}`",
            )

    def test_no_io_or_llm_calls(self) -> None:
        for f in ("open(", "Path(", "requests.", "urllib", "http.client",
                  "openai", "OpenAI", "anthropic", "Anthropic"):
            self.assertNotIn(
                f,
                self.source,
                msg=f"services.exclusion_result_contract must not contain `{f}`",
            )


# ---------------------------------------------------------------------------
# Sanity check on module reference
# ---------------------------------------------------------------------------

class ModuleReferenceTests(unittest.TestCase):
    def test_validate_function_lives_in_module(self) -> None:
        self.assertEqual(
            validate_exclusion_result.__module__,
            "services.exclusion_result_contract",
        )
        self.assertIs(
            erc_mod.validate_exclusion_result,
            validate_exclusion_result,
        )


if __name__ == "__main__":
    unittest.main()
