"""Boundary + contract tests for ``services.final_report_result_contract``
(Step 18F / PR-FINAL-1).

Spec source of truth:

- `tasks/record_1_0_architecture_reset_canonical_principles.md` §8 (Branch 6)
- `tasks/record_07d_final_report_aggregator_contract.md` §3 / §9 / §11
- `tasks/record_17j_final_report_layer_rebuild_plan.md` §9 / §11 / §15
- `tasks/record_18a_first_layer_based_implementation_batch_selection.md` §13

PR-FINAL-1 is a **pure addition** — a new schema constant + validator
with zero changes to any existing business code. This suite verifies:

1.  valid minimal payload returns ``[]``
2.  non-dict payload returns error (no raise)
3.  wrong ``schema_version`` returns ``invalid value:``
4.  each missing top-level section returns ``missing section:``
5.  ``kind`` must equal ``"final_report"``
6.  ``symbol`` must be a non-empty string
7.  ``ready`` must be a bool
8.  ``summary`` must be str or list
9.  ``key_points`` must be a list
10. ``risks`` must be a list
11. ``evidence_summary`` must be dict / list / str
12. ``projection_summary`` must be a dict
13. ``exclusion_summary`` must be a dict
14. ``confidence_summary`` must be a dict
15. ``conflict_summary`` must be dict / list / str
16. ``warning_cards`` must be a list
17. ``warning_cards`` dict item missing ``type`` / ``message`` returns warning
18. ``decision_factors`` must be list or dict
19. ``why_not_more`` must be list or str
20. ``layer_contributions`` must be a dict
21. ``source_attribution`` must be dict or list
22. ``raw_section_refs`` must be dict or list
23. ``risk_disclosure`` must be str or list
24. missing ``non_mutation_confirmations`` required keys returns error
25. ``non_mutation_confirmations`` required values must be ``True``
26. forbidden upstream raw sections rejected
27. forbidden projection verdict fields rejected
28. forbidden exclusion verdict fields rejected
29. forbidden confidence verdict fields rejected
30. forbidden review / evaluation result fields rejected
31. forbidden legacy final fields rejected
32. forbidden trading / hard / forced fields rejected
33. validator does not mutate input payload
34. module import boundary
35. ``FINAL_REPORT_RESULT_SECTIONS`` matches the expected fixed order
36. ``FINAL_REPORT_RESULT_SCHEMA_VERSION`` equals ``"final_report_result.v1"``
37. ``FINAL_REPORT_RESULT_KIND`` equals ``"final_report"``

The validator must never raise (returns errors as a list).
"""

from __future__ import annotations

import copy
import unittest
from pathlib import Path

import services.final_report_result_contract as frc_mod
from services.final_report_result_contract import (
    FINAL_REPORT_RESULT_KIND,
    FINAL_REPORT_RESULT_SCHEMA_VERSION,
    FINAL_REPORT_RESULT_SECTIONS,
    FORBIDDEN_FIELDS,
    validate_final_report_result,
)


_REPO_ROOT = Path(__file__).resolve().parent.parent


def _read(rel: str) -> str:
    return (_REPO_ROOT / rel).read_text(encoding="utf-8")


def _valid_minimal_payload() -> dict:
    """Build a payload that satisfies every PR-FINAL-1 shape rule."""
    return {
        "schema_version": FINAL_REPORT_RESULT_SCHEMA_VERSION,
        "kind": FINAL_REPORT_RESULT_KIND,
        "symbol": "AVGO",
        "ready": True,
        "summary": "minimal",
        "key_points": [],
        "risks": [],
        "evidence_summary": [],
        "projection_summary": {},
        "exclusion_summary": {},
        "confidence_summary": {},
        "conflict_summary": {},
        "warning_cards": [],
        "decision_factors": [],
        "why_not_more": [],
        "layer_contributions": {},
        "source_attribution": [],
        "raw_section_refs": {},
        "risk_disclosure": [],
        "non_mutation_confirmations": {
            "final_report_did_not_mutate_feature_payload": True,
            "final_report_did_not_mutate_projection_result": True,
            "final_report_did_not_mutate_exclusion_result": True,
            "final_report_did_not_mutate_confidence_result": True,
            "final_report_did_not_read_future_outcome": True,
        },
    }


# ---------------------------------------------------------------------------
# 0. Constants (test items 35-37)
# ---------------------------------------------------------------------------

class FinalReportResultConstantsTests(unittest.TestCase):
    def test_schema_version_is_v1(self) -> None:
        self.assertEqual(
            FINAL_REPORT_RESULT_SCHEMA_VERSION, "final_report_result.v1"
        )

    def test_kind_is_final_report(self) -> None:
        self.assertEqual(FINAL_REPORT_RESULT_KIND, "final_report")

    def test_twenty_top_level_sections_in_fixed_order(self) -> None:
        self.assertEqual(
            FINAL_REPORT_RESULT_SECTIONS,
            (
                "schema_version",
                "kind",
                "symbol",
                "ready",
                "summary",
                "key_points",
                "risks",
                "evidence_summary",
                "projection_summary",
                "exclusion_summary",
                "confidence_summary",
                "conflict_summary",
                "warning_cards",
                "decision_factors",
                "why_not_more",
                "layer_contributions",
                "source_attribution",
                "raw_section_refs",
                "risk_disclosure",
                "non_mutation_confirmations",
            ),
        )

    def test_forbidden_fields_includes_upstream_raw_sections(self) -> None:
        for required in (
            "feature_payload",
            "projection_result",
            "exclusion_result",
            "confidence_result",
            "review_result",
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
            self.assertIn(
                required, FORBIDDEN_FIELDS,
                msg=f"FORBIDDEN_FIELDS must include {required!r}",
            )

    def test_forbidden_fields_includes_exclusion_verdict_keys(self) -> None:
        for required in (
            "most_unlikely_state",
            "ranked_unlikely_states",
            "excluded_states",
            "triggered_rules",
            "triggered_rule",
            "false_exclusion_risk",
        ):
            self.assertIn(
                required, FORBIDDEN_FIELDS,
                msg=f"FORBIDDEN_FIELDS must include {required!r}",
            )

    def test_forbidden_fields_includes_confidence_verdict_keys(self) -> None:
        for required in (
            "agreement_status",
            "conflict_level",
            "combined_confidence",
            "projection_confidence",
            "exclusion_confidence",
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
        errors = validate_final_report_result(_valid_minimal_payload())
        self.assertEqual(errors, [], msg=f"unexpected errors: {errors}")

    def test_summary_str_is_ok(self) -> None:
        payload = _valid_minimal_payload()
        payload["summary"] = "AVGO 一句话总结"
        errors = validate_final_report_result(payload)
        self.assertEqual(errors, [])

    def test_warning_cards_with_complete_dict_is_ok(self) -> None:
        payload = _valid_minimal_payload()
        payload["warning_cards"] = [
            {"type": "big_up_contradiction", "message": "潜在矛盾"},
            {"type": "big_down_tail", "message": "尾部风险"},
        ]
        errors = validate_final_report_result(payload)
        self.assertEqual(errors, [])


# ---------------------------------------------------------------------------
# 2. Non-dict payload returns error (no raise)
# ---------------------------------------------------------------------------

class NonDictPayloadTests(unittest.TestCase):
    def test_none_payload(self) -> None:
        errors = validate_final_report_result(None)
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("invalid type: payload expected dict"))

    def test_list_payload(self) -> None:
        errors = validate_final_report_result([])
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("invalid type: payload expected dict"))

    def test_str_payload(self) -> None:
        errors = validate_final_report_result("not a dict")
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("invalid type: payload expected dict"))

    def test_int_payload(self) -> None:
        errors = validate_final_report_result(42)
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("invalid type: payload expected dict"))

    def test_non_dict_input_does_not_raise(self) -> None:
        for value in (None, 42, "x", [], (), 1.5, object()):
            with self.subTest(value=value):
                result = validate_final_report_result(value)
                self.assertIsInstance(result, list)


# ---------------------------------------------------------------------------
# 3. Wrong schema_version
# ---------------------------------------------------------------------------

class SchemaVersionTests(unittest.TestCase):
    def test_wrong_schema_version_returns_invalid_value_error(self) -> None:
        payload = _valid_minimal_payload()
        payload["schema_version"] = "final_report_aggregator_result.v1"
        errors = validate_final_report_result(payload)
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
        for section in FINAL_REPORT_RESULT_SECTIONS:
            with self.subTest(section=section):
                payload = _valid_minimal_payload()
                payload.pop(section)
                errors = validate_final_report_result(payload)
                self.assertIn(
                    f"missing section: {section}",
                    errors,
                    msg=f"validator did not catch missing {section}; got {errors}",
                )


# ---------------------------------------------------------------------------
# 5. kind must equal "final_report"
# ---------------------------------------------------------------------------

class KindTests(unittest.TestCase):
    def test_wrong_kind_returns_invalid_value_error(self) -> None:
        for bad in ("final_decision", "final_report_aggregator", "summary",
                    "", None, 42):
            with self.subTest(kind=bad):
                payload = _valid_minimal_payload()
                payload["kind"] = bad
                errors = validate_final_report_result(payload)
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
                errors = validate_final_report_result(payload)
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
                errors = validate_final_report_result(payload)
                matches = [e for e in errors if e.startswith("invalid type: ready")]
                self.assertEqual(
                    len(matches), 1,
                    msg=f"expected one ready type error for {bad!r}; got {matches}",
                )


# ---------------------------------------------------------------------------
# 8. summary must be str or list
# ---------------------------------------------------------------------------

class SummaryTypeTests(unittest.TestCase):
    def test_summary_must_be_str_or_list(self) -> None:
        for bad in ({}, 42, None, True):
            with self.subTest(summary=bad):
                payload = _valid_minimal_payload()
                payload["summary"] = bad
                errors = validate_final_report_result(payload)
                matches = [e for e in errors if e.startswith("invalid type: summary")]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 9. key_points must be list
# ---------------------------------------------------------------------------

class KeyPointsTypeTests(unittest.TestCase):
    def test_key_points_must_be_list(self) -> None:
        for bad in ({}, "list", 42, None):
            with self.subTest(key_points=bad):
                payload = _valid_minimal_payload()
                payload["key_points"] = bad
                errors = validate_final_report_result(payload)
                matches = [
                    e for e in errors if e.startswith("invalid type: key_points")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 10. risks must be list
# ---------------------------------------------------------------------------

class RisksTypeTests(unittest.TestCase):
    def test_risks_must_be_list(self) -> None:
        for bad in ({}, "list", 42, None):
            with self.subTest(risks=bad):
                payload = _valid_minimal_payload()
                payload["risks"] = bad
                errors = validate_final_report_result(payload)
                matches = [e for e in errors if e.startswith("invalid type: risks")]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 11. evidence_summary must be dict / list / str
# ---------------------------------------------------------------------------

class EvidenceSummaryTypeTests(unittest.TestCase):
    def test_evidence_summary_must_be_dict_list_or_str(self) -> None:
        for bad in (42, None, True):
            with self.subTest(evidence_summary=bad):
                payload = _valid_minimal_payload()
                payload["evidence_summary"] = bad
                errors = validate_final_report_result(payload)
                matches = [
                    e for e in errors if e.startswith("invalid type: evidence_summary")
                ]
                self.assertEqual(len(matches), 1)

    def test_evidence_summary_dict_str_list_all_ok(self) -> None:
        for ok in ({}, "summary", []):
            with self.subTest(evidence_summary=ok):
                payload = _valid_minimal_payload()
                payload["evidence_summary"] = ok
                errors = validate_final_report_result(payload)
                bad = [e for e in errors if e.startswith("invalid type: evidence_summary")]
                self.assertEqual(bad, [])


# ---------------------------------------------------------------------------
# 12 / 13 / 14. *_summary must be dict (projection / exclusion / confidence)
# ---------------------------------------------------------------------------

class SummarySectionTypeTests(unittest.TestCase):
    def test_each_dict_summary_section_must_be_dict(self) -> None:
        for section_name in (
            "projection_summary",
            "exclusion_summary",
            "confidence_summary",
        ):
            for bad in ([], "string", 42, None):
                with self.subTest(section=section_name, value=bad):
                    payload = _valid_minimal_payload()
                    payload[section_name] = bad
                    errors = validate_final_report_result(payload)
                    matches = [
                        e for e in errors
                        if e.startswith(f"invalid type: {section_name}")
                    ]
                    self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 15. conflict_summary must be dict / list / str
# ---------------------------------------------------------------------------

class ConflictSummaryTypeTests(unittest.TestCase):
    def test_conflict_summary_must_be_dict_list_or_str(self) -> None:
        for bad in (42, None, True):
            with self.subTest(conflict_summary=bad):
                payload = _valid_minimal_payload()
                payload["conflict_summary"] = bad
                errors = validate_final_report_result(payload)
                matches = [
                    e for e in errors
                    if e.startswith("invalid type: conflict_summary")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 16. warning_cards must be list
# ---------------------------------------------------------------------------

class WarningCardsTypeTests(unittest.TestCase):
    def test_warning_cards_must_be_list(self) -> None:
        for bad in ({}, "list", 42, None):
            with self.subTest(warning_cards=bad):
                payload = _valid_minimal_payload()
                payload["warning_cards"] = bad
                errors = validate_final_report_result(payload)
                matches = [
                    e for e in errors
                    if e.startswith("invalid type: warning_cards")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 17. warning_cards dict missing type/message returns warning
# ---------------------------------------------------------------------------

class WarningCardsAdvisoryTests(unittest.TestCase):
    def test_warning_cards_missing_type_emits_warning(self) -> None:
        payload = _valid_minimal_payload()
        payload["warning_cards"] = [{"message": "no type"}]
        errors = validate_final_report_result(payload)
        warnings = [
            e for e in errors
            if e.startswith("warning: warning_cards[0] dict missing 'type'")
        ]
        self.assertEqual(len(warnings), 1)

    def test_warning_cards_missing_message_emits_warning(self) -> None:
        payload = _valid_minimal_payload()
        payload["warning_cards"] = [{"type": "big_up"}]
        errors = validate_final_report_result(payload)
        warnings = [
            e for e in errors
            if e.startswith("warning: warning_cards[0] dict missing 'message'")
        ]
        self.assertEqual(len(warnings), 1)

    def test_warning_cards_missing_both_emits_two_warnings(self) -> None:
        payload = _valid_minimal_payload()
        payload["warning_cards"] = [{"other": "x"}]
        errors = validate_final_report_result(payload)
        warnings = [e for e in errors if e.startswith("warning: warning_cards[0]")]
        self.assertEqual(len(warnings), 2)

    def test_warning_cards_complete_dict_no_warning(self) -> None:
        payload = _valid_minimal_payload()
        payload["warning_cards"] = [
            {"type": "big_up_contradiction", "message": "潜在矛盾"}
        ]
        errors = validate_final_report_result(payload)
        warnings = [e for e in errors if e.startswith("warning: warning_cards")]
        self.assertEqual(warnings, [])

    def test_warning_cards_non_dict_item_does_not_emit_advisory(self) -> None:
        # Producers may emit string-only warning entries; the advisory only
        # applies to dict items.
        payload = _valid_minimal_payload()
        payload["warning_cards"] = ["plain text warning"]
        errors = validate_final_report_result(payload)
        warnings = [e for e in errors if e.startswith("warning: warning_cards")]
        self.assertEqual(warnings, [])

    def test_validator_does_not_auto_correct_warning_cards(self) -> None:
        payload = _valid_minimal_payload()
        payload["warning_cards"] = [{"other": "x"}]
        snapshot = copy.deepcopy(payload["warning_cards"])
        validate_final_report_result(payload)
        self.assertEqual(payload["warning_cards"], snapshot)


# ---------------------------------------------------------------------------
# 18. decision_factors must be list or dict
# ---------------------------------------------------------------------------

class DecisionFactorsTypeTests(unittest.TestCase):
    def test_decision_factors_must_be_list_or_dict(self) -> None:
        for bad in ("string", 42, None, True):
            with self.subTest(decision_factors=bad):
                payload = _valid_minimal_payload()
                payload["decision_factors"] = bad
                errors = validate_final_report_result(payload)
                matches = [
                    e for e in errors
                    if e.startswith("invalid type: decision_factors")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 19. why_not_more must be list or str
# ---------------------------------------------------------------------------

class WhyNotMoreTypeTests(unittest.TestCase):
    def test_why_not_more_must_be_list_or_str(self) -> None:
        for bad in ({}, 42, None, True):
            with self.subTest(why_not_more=bad):
                payload = _valid_minimal_payload()
                payload["why_not_more"] = bad
                errors = validate_final_report_result(payload)
                matches = [
                    e for e in errors
                    if e.startswith("invalid type: why_not_more")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 20. layer_contributions must be dict
# ---------------------------------------------------------------------------

class LayerContributionsTypeTests(unittest.TestCase):
    def test_layer_contributions_must_be_dict(self) -> None:
        for bad in ([], "string", 42, None):
            with self.subTest(layer_contributions=bad):
                payload = _valid_minimal_payload()
                payload["layer_contributions"] = bad
                errors = validate_final_report_result(payload)
                matches = [
                    e for e in errors
                    if e.startswith("invalid type: layer_contributions")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 21. source_attribution must be dict or list
# ---------------------------------------------------------------------------

class SourceAttributionTypeTests(unittest.TestCase):
    def test_source_attribution_must_be_dict_or_list(self) -> None:
        for bad in ("string", 42, None, True):
            with self.subTest(source_attribution=bad):
                payload = _valid_minimal_payload()
                payload["source_attribution"] = bad
                errors = validate_final_report_result(payload)
                matches = [
                    e for e in errors
                    if e.startswith("invalid type: source_attribution")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 22. raw_section_refs must be dict or list
# ---------------------------------------------------------------------------

class RawSectionRefsTypeTests(unittest.TestCase):
    def test_raw_section_refs_must_be_dict_or_list(self) -> None:
        for bad in ("string", 42, None, True):
            with self.subTest(raw_section_refs=bad):
                payload = _valid_minimal_payload()
                payload["raw_section_refs"] = bad
                errors = validate_final_report_result(payload)
                matches = [
                    e for e in errors
                    if e.startswith("invalid type: raw_section_refs")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 23. risk_disclosure must be str or list
# ---------------------------------------------------------------------------

class RiskDisclosureTypeTests(unittest.TestCase):
    def test_risk_disclosure_must_be_str_or_list(self) -> None:
        for bad in ({}, 42, None, True):
            with self.subTest(risk_disclosure=bad):
                payload = _valid_minimal_payload()
                payload["risk_disclosure"] = bad
                errors = validate_final_report_result(payload)
                matches = [
                    e for e in errors
                    if e.startswith("invalid type: risk_disclosure")
                ]
                self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 24. Missing non_mutation_confirmations required keys
# ---------------------------------------------------------------------------

class MissingNonMutationConfirmationKeysTests(unittest.TestCase):
    def test_each_missing_key_yields_missing_field_error(self) -> None:
        for key in (
            "final_report_did_not_mutate_feature_payload",
            "final_report_did_not_mutate_projection_result",
            "final_report_did_not_mutate_exclusion_result",
            "final_report_did_not_mutate_confidence_result",
            "final_report_did_not_read_future_outcome",
        ):
            with self.subTest(key=key):
                payload = _valid_minimal_payload()
                payload["non_mutation_confirmations"].pop(key)
                errors = validate_final_report_result(payload)
                self.assertIn(
                    f"missing field: non_mutation_confirmations.{key}",
                    errors,
                )


# ---------------------------------------------------------------------------
# 25. non_mutation_confirmations required values must be True
# ---------------------------------------------------------------------------

class NonMutationConfirmationValueTests(unittest.TestCase):
    def test_each_required_key_must_be_true(self) -> None:
        for key in (
            "final_report_did_not_mutate_feature_payload",
            "final_report_did_not_mutate_projection_result",
            "final_report_did_not_mutate_exclusion_result",
            "final_report_did_not_mutate_confidence_result",
            "final_report_did_not_read_future_outcome",
        ):
            for bad in (False, None, 0, 1, "true", []):
                with self.subTest(key=key, value=bad):
                    payload = _valid_minimal_payload()
                    payload["non_mutation_confirmations"][key] = bad
                    errors = validate_final_report_result(payload)
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
# 26. Forbidden upstream raw sections rejected
# ---------------------------------------------------------------------------

class ForbiddenUpstreamSectionsTests(unittest.TestCase):
    def test_forbidden_upstream_raw_sections_at_top_level(self) -> None:
        for forbidden in (
            "feature_payload",
            "projection_result",
            "exclusion_result",
            "confidence_result",
        ):
            with self.subTest(forbidden=forbidden):
                payload = _valid_minimal_payload()
                payload[forbidden] = {}
                errors = validate_final_report_result(payload)
                self.assertIn(
                    f"forbidden field: {forbidden} at top-level",
                    errors,
                )


# ---------------------------------------------------------------------------
# 27. Forbidden projection verdict fields rejected
# ---------------------------------------------------------------------------

class ForbiddenProjectionVerdictFieldsTests(unittest.TestCase):
    def test_forbidden_projection_verdict_at_top_level(self) -> None:
        for forbidden in (
            "most_likely_state",
            "ranked_states",
            "state_probabilities",
            "predicted_top1",
            "predicted_top2",
        ):
            with self.subTest(forbidden=forbidden):
                payload = _valid_minimal_payload()
                payload[forbidden] = "anything"
                errors = validate_final_report_result(payload)
                self.assertIn(
                    f"forbidden field: {forbidden} at top-level",
                    errors,
                )


# ---------------------------------------------------------------------------
# 28. Forbidden exclusion verdict fields rejected
# ---------------------------------------------------------------------------

class ForbiddenExclusionVerdictFieldsTests(unittest.TestCase):
    def test_forbidden_exclusion_verdict_at_top_level(self) -> None:
        for forbidden in (
            "most_unlikely_state",
            "ranked_unlikely_states",
            "excluded_states",
            "triggered_rules",
            "triggered_rule",
            "false_exclusion_risk",
        ):
            with self.subTest(forbidden=forbidden):
                payload = _valid_minimal_payload()
                payload[forbidden] = "anything"
                errors = validate_final_report_result(payload)
                self.assertIn(
                    f"forbidden field: {forbidden} at top-level",
                    errors,
                )


# ---------------------------------------------------------------------------
# 29. Forbidden confidence verdict fields rejected
# ---------------------------------------------------------------------------

class ForbiddenConfidenceVerdictFieldsTests(unittest.TestCase):
    def test_forbidden_confidence_verdict_at_top_level(self) -> None:
        for forbidden in (
            "agreement_status",
            "conflict_level",
            "combined_confidence",
            "projection_confidence",
            "exclusion_confidence",
        ):
            with self.subTest(forbidden=forbidden):
                payload = _valid_minimal_payload()
                payload[forbidden] = "anything"
                errors = validate_final_report_result(payload)
                self.assertIn(
                    f"forbidden field: {forbidden} at top-level",
                    errors,
                )


# ---------------------------------------------------------------------------
# 30. Forbidden review / evaluation result fields rejected
# ---------------------------------------------------------------------------

class ForbiddenReviewEvalFieldsTests(unittest.TestCase):
    def test_forbidden_review_eval_at_top_level(self) -> None:
        for forbidden in ("review_result", "evaluation_result"):
            with self.subTest(forbidden=forbidden):
                payload = _valid_minimal_payload()
                payload[forbidden] = "anything"
                errors = validate_final_report_result(payload)
                self.assertIn(
                    f"forbidden field: {forbidden} at top-level",
                    errors,
                )


# ---------------------------------------------------------------------------
# 31. Forbidden legacy final fields rejected
# ---------------------------------------------------------------------------

class ForbiddenLegacyFinalFieldsTests(unittest.TestCase):
    def test_forbidden_legacy_final_fields_at_top_level(self) -> None:
        for forbidden in (
            "final_direction",
            "final_confidence",
            "final_bias",
            "final_projection",
            "primary_projection",
            "peer_adjustment",
            "path_risk",
        ):
            with self.subTest(forbidden=forbidden):
                payload = _valid_minimal_payload()
                payload[forbidden] = "anything"
                errors = validate_final_report_result(payload)
                self.assertIn(
                    f"forbidden field: {forbidden} at top-level",
                    errors,
                )


# ---------------------------------------------------------------------------
# 32. Forbidden trading / hard / forced fields rejected
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
                errors = validate_final_report_result(payload)
                self.assertIn(
                    f"forbidden field: {forbidden} at top-level",
                    errors,
                )


# ---------------------------------------------------------------------------
# 33. Validator does not mutate input
# ---------------------------------------------------------------------------

class NonMutationTests(unittest.TestCase):
    def test_valid_payload_unchanged(self) -> None:
        payload = _valid_minimal_payload()
        snapshot = copy.deepcopy(payload)
        validate_final_report_result(payload)
        self.assertEqual(payload, snapshot)

    def test_invalid_payload_unchanged(self) -> None:
        payload = _valid_minimal_payload()
        payload.pop("warning_cards")
        snapshot = copy.deepcopy(payload)
        errors = validate_final_report_result(payload)
        self.assertNotEqual(errors, [])
        self.assertEqual(payload, snapshot)

    def test_pure_function_repeatable_output(self) -> None:
        payload = _valid_minimal_payload()
        first = validate_final_report_result(payload)
        second = validate_final_report_result(payload)
        self.assertEqual(first, second)


# ---------------------------------------------------------------------------
# 34. Module import boundary
# ---------------------------------------------------------------------------

class ImportBoundaryTests(unittest.TestCase):
    """``services.final_report_result_contract`` must remain a pure shape
    validator with zero coupling to any business / orchestrator / UI / DB
    module."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = _read("services/final_report_result_contract.py")

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
            "from services.final_decision",
            "import services.final_decision",
            "from services.consistency_layer",
            "import services.consistency_layer",
            "from services.projection_chain_contract",
            "import services.projection_chain_contract",
            "from services.predict_summary",
            "import services.predict_summary",
            "from services.ai_summary",
            "import services.ai_summary",
            "from services.main_projection_layer",
            "import services.main_projection_layer",
            "from services.exclusion_layer",
            "import services.exclusion_layer",
            "from services.peer_alignment",
            "import services.peer_alignment",
            "from services.confidence_evaluator",
            "import services.confidence_evaluator",
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
                msg=f"services.final_report_result_contract must not contain `{f}`",
            )

    def test_no_io_or_llm_calls(self) -> None:
        for f in ("open(", "Path(", "requests.", "urllib", "http.client",
                  "openai", "OpenAI", "anthropic", "Anthropic"):
            self.assertNotIn(
                f,
                self.source,
                msg=f"services.final_report_result_contract must not contain `{f}`",
            )


# ---------------------------------------------------------------------------
# Sanity check on module reference
# ---------------------------------------------------------------------------

class ModuleReferenceTests(unittest.TestCase):
    def test_validate_function_lives_in_module(self) -> None:
        self.assertEqual(
            validate_final_report_result.__module__,
            "services.final_report_result_contract",
        )
        self.assertIs(
            frc_mod.validate_final_report_result,
            validate_final_report_result,
        )


if __name__ == "__main__":
    unittest.main()
