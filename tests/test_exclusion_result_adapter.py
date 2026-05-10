"""Tests for ``services.exclusion_result_adapter`` (Step 18M /
PR-EXCL-2, Plan A adapter-only).

Spec source of truth:

- `tasks/record_1_0_architecture_reset_canonical_principles.md` §8 (Branch 4)
- `tasks/record_07b_exclusion_system_contract.md` §3 / §9
- `tasks/record_17h_exclusion_layer_rebuild_plan.md` §8 / §10 / §14
- `tasks/record_18a_first_layer_based_implementation_batch_selection.md` §13
- `tasks/record_18j_second_layer_based_implementation_batch_selection.md` §6 / §13

PR-EXCL-2 Plan A is a **pure addition** — a new translator that wires
PR-EXCL-1 (``exclusion_result.v1`` validator) into a real callable
shape. It does not modify ``services.exclusion_layer`` (the legacy
output emits ``triggered_rule`` (singular) which the validator forbids
at top level — direct alias is impossible). This suite verifies:

1.  ``build_exclusion_result_from_legacy`` returns dict with
    ``"payload"`` and ``"validation_errors"`` keys
2.  valid legacy exclusion produces a valid ``exclusion_result.v1``
    payload (``validation_errors == []``)
3.  output payload passes ``validate_exclusion_result`` (round-trip)
4.  ``most_unlikely_state`` maps from legacy ``most_unlikely_state``
5.  ``most_unlikely_state`` falls back from ``triggered_rule`` mapping
6.  ``most_unlikely_state`` falls back from ``excluded_states`` first
    valid entry
7.  ``most_unlikely_state`` falls back from ``exclude_big_up`` /
    ``exclude_big_down`` flags
8.  ``ranked_unlikely_states`` uses legacy ``ranked_unlikely_states``
    when present
9.  ``ranked_unlikely_states`` falls back to ``excluded_states``
10. ``ranked_unlikely_states`` falls back to ``[most_unlikely_state]``
11. ``ranked_unlikely_states == []`` when nothing is available
12. ``excluded_states`` maps from legacy ``excluded_states`` list
13. ``excluded_states`` maps from ``excluded`` string when valid
14. ``excluded_states`` maps from ``exclude_big_up`` /
    ``exclude_big_down`` flags
15. ``excluded_states`` order-preserving deduplicates
16. ``triggered_rules`` maps from legacy ``triggered_rules`` list
17. ``triggered_rules`` maps from legacy ``triggered_rule`` single
    string
18. ``triggered_rules == []`` when legacy is None or missing
19. ``state_impossibility_scores`` defaults to ``{}``
20. ``state_impossibility_scores`` invalid value flows to
    ``validation_errors``
21. ``false_exclusion_risk`` valid enum passes through
22. ``false_exclusion_risk`` invalid / missing defaults to
    ``"unknown"``
23. ``symbol`` is required and passed through (legacy.symbol does not
    override caller)
24. ``feature_snapshot_ref`` is deep-copied / preserved
25. ``evidence`` / ``rationale`` / ``warnings`` are passed through
    conservatively
26. ``peer_alignment_summary`` falls back from legacy
    ``peer_alignment``
27. ``non_mutation_confirmations`` 4 keys all True
28. adapter does not mutate ``legacy_exclusion``
29. adapter deep-copies mutable fields
30. adapter does not leak ``projection_result`` / ``confidence_result``
    / ``final_report`` to top level
31. adapter does not add trading / hard / forced fields at top level
32. legacy ``triggered_rule`` (single) does not appear in standard
    payload top level
33. import boundary
"""

from __future__ import annotations

import copy
import unittest
from pathlib import Path

import services.exclusion_result_adapter as adapter_mod
from services.exclusion_result_adapter import (
    build_exclusion_result_from_legacy,
)
from services.exclusion_result_contract import (
    EXCLUSION_RESULT_KIND,
    EXCLUSION_RESULT_SCHEMA_VERSION,
    EXCLUSION_RESULT_SECTIONS,
    VALID_STATES,
    validate_exclusion_result,
)


_REPO_ROOT = Path(__file__).resolve().parent.parent


def _read(rel: str) -> str:
    return (_REPO_ROOT / rel).read_text(encoding="utf-8")


def _legacy_exclude_big_up() -> dict:
    """Legacy run_exclusion_layer output for the exclude_big_up branch."""
    return {
        "excluded": True,
        "action": "exclude",
        "triggered_rule": "exclude_big_up",
        "summary": "排除层判断：明天不太可能大涨。",
        "reasons": ["pos20=85，处于偏高区域，明日大涨概率下降。"],
        "peer_alignment": {
            "alignment": "neutral",
            "up_support": "unsupported",
        },
        "feature_snapshot": {"pos20": 85.0},
    }


def _legacy_exclude_big_down() -> dict:
    """Legacy run_exclusion_layer output for the exclude_big_down branch."""
    return {
        "excluded": True,
        "action": "exclude",
        "triggered_rule": "exclude_big_down",
        "summary": "排除层判断：明天不太可能大跌。",
        "reasons": ["pos20=15，处于偏低区域，明日大跌概率下降。"],
        "peer_alignment": {
            "alignment": "neutral",
            "down_support": "unsupported",
        },
        "feature_snapshot": {"pos20": 15.0},
    }


def _legacy_allow() -> dict:
    """Legacy run_exclusion_layer output for the allow branch (no
    extreme constraint)."""
    return {
        "excluded": False,
        "action": "allow",
        "triggered_rule": None,
        "summary": "排除层未形成足够强的极端排除证据，主流程可继续推演。",
        "reasons": ["当前特征未形成对明日大涨或大跌的强排除约束。"],
        "peer_alignment": {},
        "feature_snapshot": {},
    }


# ---------------------------------------------------------------------------
# 1. Returns dict with payload and validation_errors
# ---------------------------------------------------------------------------

class ReturnShapeTests(unittest.TestCase):
    def test_return_is_dict(self) -> None:
        result = build_exclusion_result_from_legacy(
            _legacy_exclude_big_up(), symbol="AVGO"
        )
        self.assertIsInstance(result, dict)

    def test_return_has_payload_and_validation_errors(self) -> None:
        result = build_exclusion_result_from_legacy(
            _legacy_exclude_big_up(), symbol="AVGO"
        )
        self.assertIn("payload", result)
        self.assertIn("validation_errors", result)
        self.assertIsInstance(result["validation_errors"], list)


# ---------------------------------------------------------------------------
# 2. Valid legacy produces valid payload
# ---------------------------------------------------------------------------

class ValidLegacyExclusionTests(unittest.TestCase):
    def test_exclude_big_up_validates_clean(self) -> None:
        result = build_exclusion_result_from_legacy(
            _legacy_exclude_big_up(), symbol="AVGO"
        )
        self.assertEqual(
            result["validation_errors"], [],
            msg=f"unexpected errors: {result['validation_errors']}",
        )

    def test_exclude_big_down_validates_clean(self) -> None:
        result = build_exclusion_result_from_legacy(
            _legacy_exclude_big_down(), symbol="AVGO"
        )
        self.assertEqual(
            result["validation_errors"], [],
            msg=f"unexpected errors: {result['validation_errors']}",
        )

    def test_payload_schema_version_and_kind(self) -> None:
        result = build_exclusion_result_from_legacy(
            _legacy_exclude_big_up(), symbol="AVGO"
        )
        self.assertEqual(
            result["payload"]["schema_version"],
            EXCLUSION_RESULT_SCHEMA_VERSION,
        )
        self.assertEqual(result["payload"]["kind"], EXCLUSION_RESULT_KIND)
        self.assertEqual(result["payload"]["kind"], "exclusion")

    def test_payload_has_all_sixteen_top_level_sections(self) -> None:
        result = build_exclusion_result_from_legacy(
            _legacy_exclude_big_up(), symbol="AVGO"
        )
        for section in EXCLUSION_RESULT_SECTIONS:
            with self.subTest(section=section):
                self.assertIn(section, result["payload"])


# ---------------------------------------------------------------------------
# 3. Validator round-trip
# ---------------------------------------------------------------------------

class ValidatorRoundTripTests(unittest.TestCase):
    def test_assembled_payload_passes_validator(self) -> None:
        result = build_exclusion_result_from_legacy(
            _legacy_exclude_big_up(), symbol="AVGO"
        )
        direct = validate_exclusion_result(result["payload"])
        self.assertEqual(direct, result["validation_errors"])
        self.assertEqual(direct, [])


# ---------------------------------------------------------------------------
# 4. most_unlikely_state from explicit legacy field
# ---------------------------------------------------------------------------

class MostUnlikelyStateExplicitTests(unittest.TestCase):
    def test_most_unlikely_state_from_legacy_field(self) -> None:
        legacy = _legacy_exclude_big_up()
        legacy["most_unlikely_state"] = "小跌"
        result = build_exclusion_result_from_legacy(legacy, symbol="AVGO")
        self.assertEqual(result["payload"]["most_unlikely_state"], "小跌")


# ---------------------------------------------------------------------------
# 5. most_unlikely_state from triggered_rule mapping
# ---------------------------------------------------------------------------

class MostUnlikelyStateFromTriggeredRuleTests(unittest.TestCase):
    def test_exclude_big_up_maps_to_dazhang(self) -> None:
        result = build_exclusion_result_from_legacy(
            _legacy_exclude_big_up(), symbol="AVGO"
        )
        self.assertEqual(result["payload"]["most_unlikely_state"], "大涨")

    def test_exclude_big_down_maps_to_dadie(self) -> None:
        result = build_exclusion_result_from_legacy(
            _legacy_exclude_big_down(), symbol="AVGO"
        )
        self.assertEqual(result["payload"]["most_unlikely_state"], "大跌")

    def test_unrecognised_triggered_rule_yields_no_mapping(self) -> None:
        legacy = _legacy_allow()
        legacy["triggered_rule"] = "exclude_unknown_rule"
        legacy["ready"] = False  # avoid validator complaint
        result = build_exclusion_result_from_legacy(legacy, symbol="AVGO")
        self.assertIsNone(result["payload"]["most_unlikely_state"])


# ---------------------------------------------------------------------------
# 6. most_unlikely_state from excluded_states first valid entry
# ---------------------------------------------------------------------------

class MostUnlikelyStateFromExcludedStatesTests(unittest.TestCase):
    def test_excluded_states_first_valid_state_used(self) -> None:
        legacy = _legacy_allow()
        legacy["triggered_rule"] = None
        legacy["excluded_states"] = ["INVALID", "震荡"]
        result = build_exclusion_result_from_legacy(legacy, symbol="AVGO")
        self.assertEqual(result["payload"]["most_unlikely_state"], "震荡")


# ---------------------------------------------------------------------------
# 7. most_unlikely_state from exclude_big_up / exclude_big_down flags
# ---------------------------------------------------------------------------

class MostUnlikelyStateFromFlagsTests(unittest.TestCase):
    def test_exclude_big_up_flag_maps_to_dazhang(self) -> None:
        legacy = _legacy_allow()
        legacy["triggered_rule"] = None
        legacy["exclude_big_up"] = True
        result = build_exclusion_result_from_legacy(legacy, symbol="AVGO")
        self.assertEqual(result["payload"]["most_unlikely_state"], "大涨")

    def test_exclude_big_down_flag_maps_to_dadie(self) -> None:
        legacy = _legacy_allow()
        legacy["triggered_rule"] = None
        legacy["exclude_big_down"] = True
        result = build_exclusion_result_from_legacy(legacy, symbol="AVGO")
        self.assertEqual(result["payload"]["most_unlikely_state"], "大跌")


# ---------------------------------------------------------------------------
# 8. ranked_unlikely_states uses explicit legacy when present
# ---------------------------------------------------------------------------

class RankedUnlikelyStatesExplicitTests(unittest.TestCase):
    def test_legacy_ranked_unlikely_states_used_when_present(self) -> None:
        legacy = _legacy_exclude_big_up()
        legacy["ranked_unlikely_states"] = ["大跌", "小跌", "INVALID"]
        result = build_exclusion_result_from_legacy(legacy, symbol="AVGO")
        # invalid filtered, valid passed through
        self.assertEqual(
            result["payload"]["ranked_unlikely_states"], ["大跌", "小跌"]
        )


# ---------------------------------------------------------------------------
# 9. ranked_unlikely_states falls back to excluded_states
# ---------------------------------------------------------------------------

class RankedUnlikelyStatesFromExcludedStatesTests(unittest.TestCase):
    def test_excluded_states_used_when_no_ranked(self) -> None:
        legacy = _legacy_allow()
        legacy["triggered_rule"] = None
        legacy["excluded_states"] = ["小跌", "大跌"]
        result = build_exclusion_result_from_legacy(legacy, symbol="AVGO")
        self.assertEqual(
            result["payload"]["ranked_unlikely_states"], ["小跌", "大跌"]
        )


# ---------------------------------------------------------------------------
# 10. ranked_unlikely_states falls back to [most_unlikely_state]
# ---------------------------------------------------------------------------

class RankedUnlikelyStatesFromMostUnlikelyTests(unittest.TestCase):
    def test_ranked_unlikely_states_uses_most_unlikely_when_only_top1(
        self,
    ) -> None:
        # exclude_big_up legacy has only triggered_rule → "大涨"; no
        # excluded_states / ranked.
        result = build_exclusion_result_from_legacy(
            _legacy_exclude_big_up(), symbol="AVGO"
        )
        self.assertEqual(
            result["payload"]["ranked_unlikely_states"], ["大涨"]
        )


# ---------------------------------------------------------------------------
# 11. ranked_unlikely_states empty when nothing available
# ---------------------------------------------------------------------------

class RankedUnlikelyStatesEmptyTests(unittest.TestCase):
    def test_ranked_empty_when_everything_missing(self) -> None:
        legacy = _legacy_allow()
        legacy["ready"] = False
        result = build_exclusion_result_from_legacy(legacy, symbol="AVGO")
        self.assertEqual(result["payload"]["ranked_unlikely_states"], [])


# ---------------------------------------------------------------------------
# 12. excluded_states from legacy excluded_states list
# ---------------------------------------------------------------------------

class ExcludedStatesFromListTests(unittest.TestCase):
    def test_excluded_states_filtered_to_valid_states(self) -> None:
        legacy = _legacy_allow()
        legacy["triggered_rule"] = None
        legacy["excluded_states"] = ["小跌", "INVALID", "大跌"]
        result = build_exclusion_result_from_legacy(legacy, symbol="AVGO")
        self.assertEqual(
            result["payload"]["excluded_states"], ["小跌", "大跌"]
        )


# ---------------------------------------------------------------------------
# 13. excluded_states from `excluded` string when valid
# ---------------------------------------------------------------------------

class ExcludedStatesFromExcludedStringTests(unittest.TestCase):
    def test_excluded_string_valid_state_picked_up(self) -> None:
        legacy = _legacy_allow()
        legacy["triggered_rule"] = None
        legacy["excluded"] = "大跌"  # alt-shape: str rather than bool
        result = build_exclusion_result_from_legacy(legacy, symbol="AVGO")
        self.assertIn("大跌", result["payload"]["excluded_states"])

    def test_excluded_bool_does_not_pollute_excluded_states(self) -> None:
        # The native run_exclusion_layer output has excluded=True (bool)
        # at top-level. Adapter must not interpret that as a valid state.
        result = build_exclusion_result_from_legacy(
            _legacy_exclude_big_up(), symbol="AVGO"
        )
        # excluded_states should only contain "大涨" (from triggered_rule
        # mapping), not "True" or anything string-coerced from the bool.
        self.assertEqual(result["payload"]["excluded_states"], ["大涨"])


# ---------------------------------------------------------------------------
# 14. excluded_states from exclude_big_up / exclude_big_down flags
# ---------------------------------------------------------------------------

class ExcludedStatesFromFlagsTests(unittest.TestCase):
    def test_exclude_big_up_flag_adds_dazhang(self) -> None:
        legacy = _legacy_allow()
        legacy["triggered_rule"] = None
        legacy["exclude_big_up"] = True
        result = build_exclusion_result_from_legacy(legacy, symbol="AVGO")
        self.assertIn("大涨", result["payload"]["excluded_states"])

    def test_exclude_big_down_flag_adds_dadie(self) -> None:
        legacy = _legacy_allow()
        legacy["triggered_rule"] = None
        legacy["exclude_big_down"] = True
        result = build_exclusion_result_from_legacy(legacy, symbol="AVGO")
        self.assertIn("大跌", result["payload"]["excluded_states"])


# ---------------------------------------------------------------------------
# 15. excluded_states order-preserving deduplicates
# ---------------------------------------------------------------------------

class ExcludedStatesDedupeTests(unittest.TestCase):
    def test_duplicate_states_collapsed_keeping_first_occurrence(self) -> None:
        legacy = _legacy_allow()
        legacy["triggered_rule"] = "exclude_big_up"  # → 大涨
        legacy["excluded_states"] = ["大涨", "小跌", "大涨"]  # duplicate
        legacy["exclude_big_up"] = True  # would also add 大涨
        result = build_exclusion_result_from_legacy(legacy, symbol="AVGO")
        self.assertEqual(
            result["payload"]["excluded_states"], ["大涨", "小跌"]
        )


# ---------------------------------------------------------------------------
# 16. triggered_rules from legacy triggered_rules list
# ---------------------------------------------------------------------------

class TriggeredRulesFromListTests(unittest.TestCase):
    def test_legacy_triggered_rules_list_passed_through(self) -> None:
        legacy = _legacy_exclude_big_up()
        legacy["triggered_rules"] = ["exclude_big_up", "extreme_overextended"]
        result = build_exclusion_result_from_legacy(legacy, symbol="AVGO")
        self.assertEqual(
            result["payload"]["triggered_rules"],
            ["exclude_big_up", "extreme_overextended"],
        )

    def test_legacy_triggered_rules_filters_non_string_and_empty(self) -> None:
        legacy = _legacy_exclude_big_up()
        legacy["triggered_rules"] = [
            "exclude_big_up",
            "",  # empty string filtered
            42,  # non-string filtered
            None,  # None filtered
            "another_rule",
        ]
        result = build_exclusion_result_from_legacy(legacy, symbol="AVGO")
        self.assertEqual(
            result["payload"]["triggered_rules"],
            ["exclude_big_up", "another_rule"],
        )


# ---------------------------------------------------------------------------
# 17. triggered_rules from triggered_rule single string
# ---------------------------------------------------------------------------

class TriggeredRulesFromSingleStringTests(unittest.TestCase):
    def test_single_triggered_rule_lifted_into_list(self) -> None:
        # _legacy_exclude_big_up has triggered_rule="exclude_big_up"
        # but no triggered_rules list.
        result = build_exclusion_result_from_legacy(
            _legacy_exclude_big_up(), symbol="AVGO"
        )
        self.assertEqual(
            result["payload"]["triggered_rules"], ["exclude_big_up"]
        )


# ---------------------------------------------------------------------------
# 18. triggered_rules == [] when None / missing
# ---------------------------------------------------------------------------

class TriggeredRulesEmptyTests(unittest.TestCase):
    def test_triggered_rules_empty_when_legacy_none(self) -> None:
        legacy = _legacy_allow()
        legacy["ready"] = False
        result = build_exclusion_result_from_legacy(legacy, symbol="AVGO")
        self.assertEqual(result["payload"]["triggered_rules"], [])

    def test_triggered_rules_empty_when_missing(self) -> None:
        legacy = _legacy_allow()
        legacy.pop("triggered_rule")
        legacy["ready"] = False
        result = build_exclusion_result_from_legacy(legacy, symbol="AVGO")
        self.assertEqual(result["payload"]["triggered_rules"], [])


# ---------------------------------------------------------------------------
# 19. state_impossibility_scores defaults to {}
# ---------------------------------------------------------------------------

class StateImpossibilityScoresDefaultTests(unittest.TestCase):
    def test_missing_state_impossibility_scores_defaults_to_empty(self) -> None:
        result = build_exclusion_result_from_legacy(
            _legacy_exclude_big_up(), symbol="AVGO"
        )
        self.assertEqual(result["payload"]["state_impossibility_scores"], {})

    def test_non_dict_state_impossibility_scores_defaults_to_empty(self) -> None:
        legacy = _legacy_exclude_big_up()
        legacy["state_impossibility_scores"] = "not a dict"
        result = build_exclusion_result_from_legacy(legacy, symbol="AVGO")
        self.assertEqual(result["payload"]["state_impossibility_scores"], {})


# ---------------------------------------------------------------------------
# 20. state_impossibility_scores invalid value → validation_errors
# ---------------------------------------------------------------------------

class StateImpossibilityScoresValidationTests(unittest.TestCase):
    def test_out_of_range_value_surfaces_in_validation_errors(self) -> None:
        legacy = _legacy_exclude_big_up()
        legacy["state_impossibility_scores"] = {"大涨": 1.5}
        result = build_exclusion_result_from_legacy(legacy, symbol="AVGO")
        self.assertTrue(
            any(
                e.startswith(
                    "invalid value: state_impossibility_scores['大涨']"
                )
                for e in result["validation_errors"]
            ),
            msg=f"expected range error; got {result['validation_errors']}",
        )


# ---------------------------------------------------------------------------
# 21. false_exclusion_risk valid enum passes through
# ---------------------------------------------------------------------------

class FalseExclusionRiskValidEnumTests(unittest.TestCase):
    def test_valid_low_passes_through(self) -> None:
        legacy = _legacy_exclude_big_up()
        legacy["false_exclusion_risk"] = "low"
        result = build_exclusion_result_from_legacy(legacy, symbol="AVGO")
        self.assertEqual(result["payload"]["false_exclusion_risk"], "low")

    def test_valid_medium_passes_through(self) -> None:
        legacy = _legacy_exclude_big_up()
        legacy["false_exclusion_risk"] = "medium"
        result = build_exclusion_result_from_legacy(legacy, symbol="AVGO")
        self.assertEqual(result["payload"]["false_exclusion_risk"], "medium")

    def test_valid_high_passes_through(self) -> None:
        legacy = _legacy_exclude_big_up()
        legacy["false_exclusion_risk"] = "high"
        result = build_exclusion_result_from_legacy(legacy, symbol="AVGO")
        self.assertEqual(result["payload"]["false_exclusion_risk"], "high")


# ---------------------------------------------------------------------------
# 22. false_exclusion_risk invalid / missing defaults to "unknown"
# ---------------------------------------------------------------------------

class FalseExclusionRiskFallbackTests(unittest.TestCase):
    def test_missing_defaults_to_unknown(self) -> None:
        result = build_exclusion_result_from_legacy(
            _legacy_exclude_big_up(), symbol="AVGO"
        )
        self.assertEqual(
            result["payload"]["false_exclusion_risk"], "unknown"
        )

    def test_invalid_value_defaults_to_unknown(self) -> None:
        legacy = _legacy_exclude_big_up()
        legacy["false_exclusion_risk"] = "EXTREME"
        result = build_exclusion_result_from_legacy(legacy, symbol="AVGO")
        self.assertEqual(
            result["payload"]["false_exclusion_risk"], "unknown"
        )


# ---------------------------------------------------------------------------
# 23. symbol passed through; legacy.symbol does not override
# ---------------------------------------------------------------------------

class SymbolPassThroughTests(unittest.TestCase):
    def test_caller_symbol_used(self) -> None:
        result = build_exclusion_result_from_legacy(
            _legacy_exclude_big_up(), symbol="NVDA"
        )
        self.assertEqual(result["payload"]["symbol"], "NVDA")

    def test_legacy_symbol_does_not_override_caller(self) -> None:
        legacy = _legacy_exclude_big_up()
        legacy["symbol"] = "OTHER"
        result = build_exclusion_result_from_legacy(legacy, symbol="AVGO")
        self.assertEqual(result["payload"]["symbol"], "AVGO")


# ---------------------------------------------------------------------------
# 24. feature_snapshot_ref deep-copied / preserved
# ---------------------------------------------------------------------------

class FeatureSnapshotRefTests(unittest.TestCase):
    def test_string_ref_preserved(self) -> None:
        result = build_exclusion_result_from_legacy(
            _legacy_exclude_big_up(),
            symbol="AVGO",
            feature_snapshot_ref="ref://snapshot/abc",
        )
        self.assertEqual(
            result["payload"]["feature_snapshot_ref"], "ref://snapshot/abc"
        )

    def test_dict_ref_deep_copied(self) -> None:
        ref = {"path": "snapshot.csv"}
        result = build_exclusion_result_from_legacy(
            _legacy_exclude_big_up(),
            symbol="AVGO",
            feature_snapshot_ref=ref,
        )
        self.assertEqual(
            result["payload"]["feature_snapshot_ref"], ref
        )
        result["payload"]["feature_snapshot_ref"]["path"] = "MUTATED"
        self.assertEqual(ref["path"], "snapshot.csv")

    def test_default_none(self) -> None:
        result = build_exclusion_result_from_legacy(
            _legacy_exclude_big_up(), symbol="AVGO"
        )
        self.assertIsNone(result["payload"]["feature_snapshot_ref"])


# ---------------------------------------------------------------------------
# 25. evidence / rationale / warnings passthrough
# ---------------------------------------------------------------------------

class EvidenceRationaleWarningsPassThroughTests(unittest.TestCase):
    def test_rationale_falls_back_from_summary(self) -> None:
        # _legacy_exclude_big_up has summary str; no rationale/reason/explanation.
        result = build_exclusion_result_from_legacy(
            _legacy_exclude_big_up(), symbol="AVGO"
        )
        self.assertEqual(
            result["payload"]["rationale"],
            "排除层判断：明天不太可能大涨。",
        )

    def test_explicit_rationale_takes_priority(self) -> None:
        legacy = _legacy_exclude_big_up()
        legacy["rationale"] = ["显式 rationale"]
        result = build_exclusion_result_from_legacy(legacy, symbol="AVGO")
        self.assertEqual(result["payload"]["rationale"], ["显式 rationale"])

    def test_evidence_default_empty_dict(self) -> None:
        result = build_exclusion_result_from_legacy(
            _legacy_exclude_big_up(), symbol="AVGO"
        )
        self.assertEqual(result["payload"]["evidence"], {})

    def test_evidence_falls_back_from_key_observations(self) -> None:
        legacy = _legacy_exclude_big_up()
        legacy["key_observations"] = ["pos20 high"]
        result = build_exclusion_result_from_legacy(legacy, symbol="AVGO")
        self.assertEqual(
            result["payload"]["evidence"], ["pos20 high"]
        )

    def test_warnings_passed_through(self) -> None:
        legacy = _legacy_exclude_big_up()
        legacy["warnings"] = ["warn 1"]
        result = build_exclusion_result_from_legacy(legacy, symbol="AVGO")
        self.assertEqual(result["payload"]["warnings"], ["warn 1"])

    def test_warnings_default_empty_list(self) -> None:
        # _legacy_exclude_big_up has no warnings key
        result = build_exclusion_result_from_legacy(
            _legacy_exclude_big_up(), symbol="AVGO"
        )
        self.assertEqual(result["payload"]["warnings"], [])


# ---------------------------------------------------------------------------
# 26. peer_alignment_summary falls back from legacy peer_alignment
# ---------------------------------------------------------------------------

class PeerAlignmentSummaryTests(unittest.TestCase):
    def test_legacy_peer_alignment_used_when_no_explicit_summary(self) -> None:
        result = build_exclusion_result_from_legacy(
            _legacy_exclude_big_up(), symbol="AVGO"
        )
        self.assertEqual(
            result["payload"]["peer_alignment_summary"],
            _legacy_exclude_big_up()["peer_alignment"],
        )

    def test_explicit_peer_alignment_summary_takes_priority(self) -> None:
        legacy = _legacy_exclude_big_up()
        legacy["peer_alignment_summary"] = {"alignment": "explicit"}
        result = build_exclusion_result_from_legacy(legacy, symbol="AVGO")
        self.assertEqual(
            result["payload"]["peer_alignment_summary"],
            {"alignment": "explicit"},
        )

    def test_default_empty_dict(self) -> None:
        legacy = _legacy_allow()
        legacy.pop("peer_alignment", None)
        legacy["ready"] = False
        result = build_exclusion_result_from_legacy(legacy, symbol="AVGO")
        self.assertEqual(result["payload"]["peer_alignment_summary"], {})


# ---------------------------------------------------------------------------
# 27. non_mutation_confirmations all True
# ---------------------------------------------------------------------------

class NonMutationConfirmationsTests(unittest.TestCase):
    def test_all_four_required_keys_are_true(self) -> None:
        result = build_exclusion_result_from_legacy(
            _legacy_exclude_big_up(), symbol="AVGO"
        )
        nmc = result["payload"]["non_mutation_confirmations"]
        for key in (
            "exclusion_did_not_read_projection",
            "exclusion_did_not_read_confidence",
            "exclusion_did_not_read_final_report",
            "exclusion_did_not_read_future_outcome",
        ):
            with self.subTest(key=key):
                self.assertIs(nmc[key], True)

    def test_non_mutation_dict_isolated_per_call(self) -> None:
        result_1 = build_exclusion_result_from_legacy(
            _legacy_exclude_big_up(), symbol="AVGO"
        )
        result_1["payload"]["non_mutation_confirmations"][
            "exclusion_did_not_read_projection"
        ] = False
        result_2 = build_exclusion_result_from_legacy(
            _legacy_exclude_big_up(), symbol="AVGO"
        )
        self.assertIs(
            result_2["payload"]["non_mutation_confirmations"][
                "exclusion_did_not_read_projection"
            ],
            True,
        )


# ---------------------------------------------------------------------------
# 28. Adapter does not mutate legacy_exclusion
# ---------------------------------------------------------------------------

class NoMutationOfLegacyInputTests(unittest.TestCase):
    def test_legacy_unchanged_after_call(self) -> None:
        legacy = _legacy_exclude_big_up()
        snapshot = copy.deepcopy(legacy)
        build_exclusion_result_from_legacy(legacy, symbol="AVGO")
        self.assertEqual(legacy, snapshot)

    def test_legacy_unchanged_with_dict_feature_snapshot_ref(self) -> None:
        legacy = _legacy_exclude_big_up()
        snapshot = copy.deepcopy(legacy)
        build_exclusion_result_from_legacy(
            legacy, symbol="AVGO", feature_snapshot_ref={"some": "ref"}
        )
        self.assertEqual(legacy, snapshot)


# ---------------------------------------------------------------------------
# 29. Adapter deep-copies mutable fields
# ---------------------------------------------------------------------------

class DeepCopyTests(unittest.TestCase):
    def test_mutating_returned_payload_does_not_affect_legacy(self) -> None:
        legacy = _legacy_exclude_big_up()
        result = build_exclusion_result_from_legacy(legacy, symbol="AVGO")
        result["payload"]["peer_alignment_summary"]["alignment"] = "MUTATED"
        result["payload"]["evidence"] = "MUTATED"  # rebinding, not mutation
        result["payload"]["warnings"].append("MUTATED")
        self.assertEqual(legacy["peer_alignment"]["alignment"], "neutral")
        self.assertNotIn("MUTATED", legacy.get("warnings", []))

    def test_state_impossibility_scores_deep_copied(self) -> None:
        legacy = _legacy_exclude_big_up()
        legacy["state_impossibility_scores"] = {"大涨": 0.8}
        result = build_exclusion_result_from_legacy(legacy, symbol="AVGO")
        result["payload"]["state_impossibility_scores"]["大涨"] = 0.0
        self.assertEqual(legacy["state_impossibility_scores"]["大涨"], 0.8)


# ---------------------------------------------------------------------------
# 30. No upstream forbidden sections at top level
# ---------------------------------------------------------------------------

class NoForbiddenUpstreamFieldsTests(unittest.TestCase):
    def test_no_projection_or_confidence_or_final_at_top_level(self) -> None:
        result = build_exclusion_result_from_legacy(
            _legacy_exclude_big_up(), symbol="AVGO"
        )
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
                self.assertNotIn(forbidden, result["payload"])

    def test_legacy_top_level_forbidden_fields_do_not_leak(self) -> None:
        legacy = _legacy_exclude_big_up()
        legacy["projection_result"] = {"injected": True}
        legacy["final_direction"] = "偏多"
        result = build_exclusion_result_from_legacy(legacy, symbol="AVGO")
        self.assertNotIn("projection_result", result["payload"])
        self.assertNotIn("final_direction", result["payload"])
        self.assertEqual(result["validation_errors"], [])


# ---------------------------------------------------------------------------
# 31. No trading / hard / forced fields
# ---------------------------------------------------------------------------

class NoForbiddenTradingForcedFieldsTests(unittest.TestCase):
    def test_no_trading_or_forced_at_top_level(self) -> None:
        result = build_exclusion_result_from_legacy(
            _legacy_exclude_big_up(), symbol="AVGO"
        )
        for forbidden in (
            "trading_action",
            "order",
            "position_action",
            "execution",
            "buy",
            "sell",
            "hold",
            "hard",
            "forced",
            "required",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, result["payload"])


# ---------------------------------------------------------------------------
# 32. legacy triggered_rule single does not appear in standard payload
# ---------------------------------------------------------------------------

class NoLegacyTriggeredRuleSingleAtTopLevelTests(unittest.TestCase):
    def test_standard_payload_has_only_triggered_rules_plural(self) -> None:
        # 18A §13 / 17H §11 forbids legacy ``triggered_rule`` at top level.
        # Adapter must not propagate it to standard payload.
        legacy = _legacy_exclude_big_up()
        # legacy already has triggered_rule="exclude_big_up"
        result = build_exclusion_result_from_legacy(legacy, symbol="AVGO")
        self.assertNotIn("triggered_rule", result["payload"])
        # but triggered_rules (plural) IS there
        self.assertIn("triggered_rules", result["payload"])


# ---------------------------------------------------------------------------
# 33. Module import boundary
# ---------------------------------------------------------------------------

class ImportBoundaryTests(unittest.TestCase):
    """``services.exclusion_result_adapter`` must remain a pure
    translator with zero coupling to active exclusion / projection /
    confidence / final / review / evaluation / orchestrator / UI / DB
    modules. The only allowed cross-module references are
    ``services.exclusion_result_contract`` + stdlib (typing / copy).
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = _read("services/exclusion_result_adapter.py")

    def test_no_exclusion_layer_or_peer_alignment_imports(self) -> None:
        for f in (
            "from services.exclusion_layer",
            "import services.exclusion_layer",
            "from services.peer_alignment",
            "import services.peer_alignment",
        ):
            self.assertNotIn(
                f, self.source,
                msg=f"adapter must not contain `{f}`",
            )

    def test_no_main_projection_or_confidence_or_final_imports(self) -> None:
        forbidden = (
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
        )
        for f in forbidden:
            self.assertNotIn(
                f, self.source,
                msg=f"adapter must not contain `{f}`",
            )

    def test_no_orchestrator_imports(self) -> None:
        forbidden = (
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
        )
        for f in forbidden:
            self.assertNotIn(
                f, self.source,
                msg=f"adapter must not contain `{f}`",
            )

    def test_no_predict_app_ui_imports(self) -> None:
        forbidden = (
            "import predict",
            "from predict",
            "import app",
            "from app",
            "import ui",
            "from ui",
            "import streamlit",
            "from streamlit",
        )
        for f in forbidden:
            self.assertNotIn(
                f, self.source,
                msg=f"adapter must not contain `{f}`",
            )

    def test_no_db_or_yfinance_imports(self) -> None:
        for f in (
            "import sqlite3",
            "from sqlite3",
            "import yfinance",
            "from yfinance",
            "import pandas",
            "from pandas",
        ):
            self.assertNotIn(
                f, self.source,
                msg=f"adapter must not contain `{f}`",
            )

    def test_no_io_or_llm_calls(self) -> None:
        for f in ("open(", "Path(", "requests.", "urllib", "http.client",
                  "openai", "OpenAI", "anthropic", "Anthropic"):
            self.assertNotIn(
                f, self.source,
                msg=f"adapter must not contain `{f}`",
            )


# ---------------------------------------------------------------------------
# Sanity check on module reference
# ---------------------------------------------------------------------------

class ModuleReferenceTests(unittest.TestCase):
    def test_function_lives_in_module(self) -> None:
        self.assertEqual(
            build_exclusion_result_from_legacy.__module__,
            "services.exclusion_result_adapter",
        )
        self.assertIs(
            adapter_mod.build_exclusion_result_from_legacy,
            build_exclusion_result_from_legacy,
        )


if __name__ == "__main__":
    unittest.main()
