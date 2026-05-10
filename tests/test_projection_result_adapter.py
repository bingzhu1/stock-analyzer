"""Tests for ``services.projection_result_adapter`` (Step 18L /
PR-PROJ-2, Plan A).

Spec source of truth:

- `tasks/record_1_0_architecture_reset_canonical_principles.md` §8 (Branch 3)
- `tasks/record_07a_projection_system_contract.md` §3 / §9
- `tasks/record_17g_projection_layer_rebuild_plan.md` §8 / §13
- `tasks/record_18a_first_layer_based_implementation_batch_selection.md` §13
- `tasks/record_18j_second_layer_based_implementation_batch_selection.md` §6 / §13

PR-PROJ-2 Plan A is a **pure addition** — a new translator that wires
PR-PROJ-1 (``projection_result.v1`` validator) into a real callable
shape. It is not yet called by any active path, and does not modify
``services.main_projection_layer`` (Plan B was rejected because legacy
output's ``predicted_top1`` / ``predicted_top2`` fields are forbidden at
top level by the validator). This suite verifies:

1.  ``build_projection_result_from_legacy`` returns dict with
    ``"payload"`` and ``"validation_errors"`` keys
2.  valid legacy projection produces a valid ``projection_result.v1``
    payload (``validation_errors == []``)
3.  output payload passes ``validate_projection_result`` (round-trip)
4.  ``most_likely_state`` maps from legacy ``predicted_top1.state``
5.  ``ranked_states`` uses sorted ``state_probabilities`` when present
6.  ``ranked_states`` falls back to ``[predicted_top1.state,
    predicted_top2.state]`` when no probabilities
7.  ``ranked_states`` falls back to ``[most_likely_state]`` when only
    top1 exists
8.  ``ranked_states == []`` when nothing is available
9.  ``state_probabilities`` defaults to ``{}`` when legacy has no dict
10. invalid state in legacy produces ``validation_errors``
11. ``symbol`` is required and passed through
12. ``feature_snapshot_ref`` is deep-copied and preserved
13. ``evidence`` / ``rationale`` / ``warnings`` are passed through
    conservatively
14. ``historical_match_summary`` defaults to ``{}``
15. ``peer_alignment_summary`` defaults to ``{}`` (or legacy
    ``peer_alignment`` if present)
16. ``non_mutation_confirmations`` 4 keys all True
17. adapter does not mutate ``legacy_projection``
18. adapter deep-copies mutable fields
19. adapter does not add forbidden upstream fields at top level
20. adapter does not add trading / hard / forced fields at top level
21. import boundary: the adapter does not import main_projection_layer /
    exclusion_layer / confidence_evaluator / final_decision / predict /
    app / ui / orchestrator / DB
"""

from __future__ import annotations

import copy
import unittest
from pathlib import Path

import services.projection_result_adapter as adapter_mod
from services.projection_result_adapter import (
    build_projection_result_from_legacy,
)
from services.projection_result_contract import (
    PROJECTION_RESULT_KIND,
    PROJECTION_RESULT_SCHEMA_VERSION,
    PROJECTION_RESULT_SECTIONS,
    VALID_STATES,
    validate_projection_result,
)


_REPO_ROOT = Path(__file__).resolve().parent.parent


def _read(rel: str) -> str:
    return (_REPO_ROOT / rel).read_text(encoding="utf-8")


def _legacy_full_projection() -> dict:
    """A representative legacy main_projection_layer output (ready=True
    full distribution path)."""
    return {
        "kind": "main_projection_layer",
        "symbol": "AVGO",
        "ready": True,
        "predicted_top1": {"state": "小涨", "probability": 0.40},
        "predicted_top2": {"state": "震荡", "probability": 0.30},
        "state_probabilities": {
            "大涨": 0.10,
            "小涨": 0.40,
            "震荡": 0.30,
            "小跌": 0.15,
            "大跌": 0.05,
        },
        "rationale": ["主推演层已基于当前20日特征生成五状态分布。"],
        "warnings": [],
        "peer_alignment": {
            "alignment": "neutral",
            "available_peer_count": 3,
            "peer_returns": {"NVDA": 0.5, "SOXX": 0.3, "QQQ": 0.2},
        },
        "feature_snapshot": {
            "pos20": 50.0,
            "vol_ratio20": 1.05,
        },
    }


def _legacy_fallback_projection() -> dict:
    """A representative legacy main_projection_layer fallback output
    (ready=False, neutral distribution)."""
    return {
        "kind": "main_projection_layer",
        "symbol": "AVGO",
        "ready": False,
        "predicted_top1": {"state": "震荡", "probability": 0.40},
        "predicted_top2": {"state": "小涨", "probability": 0.20},
        "state_probabilities": {
            "大涨": 0.10,
            "小涨": 0.20,
            "震荡": 0.40,
            "小跌": 0.20,
            "大跌": 0.10,
        },
        "rationale": ["当前20日特征不足，主推演层已回退到保守中性分布。"],
        "warnings": ["主推演层可用特征不足，已安全降级为中性分布。"],
        "peer_alignment": {},
        "feature_snapshot": {},
    }


# ---------------------------------------------------------------------------
# 1. Returns dict with payload and validation_errors keys
# ---------------------------------------------------------------------------

class ReturnShapeTests(unittest.TestCase):
    def test_return_is_dict(self) -> None:
        result = build_projection_result_from_legacy(
            _legacy_full_projection(), symbol="AVGO"
        )
        self.assertIsInstance(result, dict)

    def test_return_has_payload_and_validation_errors(self) -> None:
        result = build_projection_result_from_legacy(
            _legacy_full_projection(), symbol="AVGO"
        )
        self.assertIn("payload", result)
        self.assertIn("validation_errors", result)
        self.assertIsInstance(result["validation_errors"], list)


# ---------------------------------------------------------------------------
# 2. Valid legacy projection produces valid payload (validation_errors == [])
# ---------------------------------------------------------------------------

class ValidLegacyProjectionTests(unittest.TestCase):
    def test_full_projection_validates_clean(self) -> None:
        result = build_projection_result_from_legacy(
            _legacy_full_projection(), symbol="AVGO"
        )
        self.assertEqual(
            result["validation_errors"], [],
            msg=f"unexpected errors: {result['validation_errors']}",
        )

    def test_fallback_projection_validates_clean(self) -> None:
        result = build_projection_result_from_legacy(
            _legacy_fallback_projection(), symbol="AVGO"
        )
        self.assertEqual(
            result["validation_errors"], [],
            msg=f"unexpected errors: {result['validation_errors']}",
        )

    def test_payload_schema_version_is_v1(self) -> None:
        result = build_projection_result_from_legacy(
            _legacy_full_projection(), symbol="AVGO"
        )
        self.assertEqual(
            result["payload"]["schema_version"],
            PROJECTION_RESULT_SCHEMA_VERSION,
        )
        self.assertEqual(
            result["payload"]["schema_version"], "projection_result.v1"
        )

    def test_payload_kind_is_projection(self) -> None:
        result = build_projection_result_from_legacy(
            _legacy_full_projection(), symbol="AVGO"
        )
        self.assertEqual(result["payload"]["kind"], PROJECTION_RESULT_KIND)
        self.assertEqual(result["payload"]["kind"], "projection")

    def test_payload_has_all_fifteen_top_level_sections(self) -> None:
        result = build_projection_result_from_legacy(
            _legacy_full_projection(), symbol="AVGO"
        )
        for section in PROJECTION_RESULT_SECTIONS:
            with self.subTest(section=section):
                self.assertIn(section, result["payload"])


# ---------------------------------------------------------------------------
# 3. Output payload passes validate_projection_result (round-trip)
# ---------------------------------------------------------------------------

class ValidatorRoundTripTests(unittest.TestCase):
    def test_assembled_payload_passes_validator(self) -> None:
        result = build_projection_result_from_legacy(
            _legacy_full_projection(), symbol="AVGO"
        )
        direct = validate_projection_result(result["payload"])
        self.assertEqual(direct, result["validation_errors"])
        self.assertEqual(direct, [])


# ---------------------------------------------------------------------------
# 4. most_likely_state maps from predicted_top1.state
# ---------------------------------------------------------------------------

class MostLikelyStateMappingTests(unittest.TestCase):
    def test_most_likely_state_from_predicted_top1(self) -> None:
        legacy = _legacy_full_projection()
        legacy["predicted_top1"] = {"state": "大涨", "probability": 0.55}
        result = build_projection_result_from_legacy(legacy, symbol="AVGO")
        self.assertEqual(result["payload"]["most_likely_state"], "大涨")

    def test_invalid_top1_state_yields_none(self) -> None:
        legacy = _legacy_full_projection()
        legacy["predicted_top1"] = {"state": "BIG_UP", "probability": 0.55}
        legacy["state_probabilities"] = {}
        legacy["ready"] = False
        result = build_projection_result_from_legacy(legacy, symbol="AVGO")
        self.assertIsNone(result["payload"]["most_likely_state"])

    def test_missing_top1_yields_none(self) -> None:
        legacy = _legacy_full_projection()
        legacy.pop("predicted_top1")
        legacy["state_probabilities"] = {}
        legacy["ready"] = False
        result = build_projection_result_from_legacy(legacy, symbol="AVGO")
        self.assertIsNone(result["payload"]["most_likely_state"])


# ---------------------------------------------------------------------------
# 5. ranked_states uses sorted state_probabilities
# ---------------------------------------------------------------------------

class RankedStatesFromProbabilitiesTests(unittest.TestCase):
    def test_ranked_states_sorted_by_probability_desc(self) -> None:
        legacy = _legacy_full_projection()
        legacy["state_probabilities"] = {
            "大涨": 0.10,
            "小涨": 0.40,
            "震荡": 0.30,
            "小跌": 0.15,
            "大跌": 0.05,
        }
        result = build_projection_result_from_legacy(legacy, symbol="AVGO")
        self.assertEqual(
            result["payload"]["ranked_states"],
            ["小涨", "震荡", "小跌", "大涨", "大跌"],
        )

    def test_ranked_states_filters_invalid_keys(self) -> None:
        legacy = _legacy_full_projection()
        legacy["state_probabilities"] = {
            "大涨": 0.10,
            "小涨": 0.40,
            "横盘": 0.30,  # invalid; filtered out
            "小跌": 0.15,
            "大跌": 0.05,
        }
        result = build_projection_result_from_legacy(legacy, symbol="AVGO")
        # ranked excludes invalid '横盘'
        self.assertEqual(
            result["payload"]["ranked_states"],
            ["小涨", "小跌", "大涨", "大跌"],
        )

    def test_ranked_states_stable_tiebreak_by_canonical_order(self) -> None:
        legacy = _legacy_full_projection()
        legacy["state_probabilities"] = {
            "大涨": 0.20,
            "小涨": 0.20,
            "震荡": 0.20,
            "小跌": 0.20,
            "大跌": 0.20,
        }
        result = build_projection_result_from_legacy(legacy, symbol="AVGO")
        # All equal → tie-break by VALID_STATES order
        self.assertEqual(result["payload"]["ranked_states"], list(VALID_STATES))


# ---------------------------------------------------------------------------
# 6. ranked_states falls back to predicted_top1+top2 pair
# ---------------------------------------------------------------------------

class RankedStatesFromTopPairTests(unittest.TestCase):
    def test_ranked_states_uses_top1_top2_when_no_probabilities(self) -> None:
        legacy = _legacy_full_projection()
        legacy["state_probabilities"] = {}  # empty
        legacy["predicted_top1"] = {"state": "小涨"}
        legacy["predicted_top2"] = {"state": "大涨"}
        result = build_projection_result_from_legacy(legacy, symbol="AVGO")
        self.assertEqual(
            result["payload"]["ranked_states"], ["小涨", "大涨"]
        )

    def test_ranked_states_dedupes_top1_top2_when_same(self) -> None:
        legacy = _legacy_full_projection()
        legacy["state_probabilities"] = {}
        legacy["predicted_top1"] = {"state": "小涨"}
        legacy["predicted_top2"] = {"state": "小涨"}
        result = build_projection_result_from_legacy(legacy, symbol="AVGO")
        self.assertEqual(result["payload"]["ranked_states"], ["小涨"])


# ---------------------------------------------------------------------------
# 7. ranked_states falls back to [most_likely_state] when only top1
# ---------------------------------------------------------------------------

class RankedStatesFallbackToTop1OnlyTests(unittest.TestCase):
    def test_ranked_states_uses_top1_only_when_no_top2(self) -> None:
        legacy = _legacy_full_projection()
        legacy["state_probabilities"] = {}
        legacy["predicted_top1"] = {"state": "震荡"}
        legacy.pop("predicted_top2")
        result = build_projection_result_from_legacy(legacy, symbol="AVGO")
        self.assertEqual(result["payload"]["ranked_states"], ["震荡"])


# ---------------------------------------------------------------------------
# 8. ranked_states == [] when nothing is available
# ---------------------------------------------------------------------------

class RankedStatesEmptyTests(unittest.TestCase):
    def test_ranked_states_empty_when_nothing_available(self) -> None:
        legacy = {
            "kind": "main_projection_layer",
            "symbol": "AVGO",
            "ready": False,
            "state_probabilities": {},
            "rationale": [],
            "warnings": [],
        }
        result = build_projection_result_from_legacy(legacy, symbol="AVGO")
        self.assertEqual(result["payload"]["ranked_states"], [])


# ---------------------------------------------------------------------------
# 9. state_probabilities defaults to {} when legacy has no dict
# ---------------------------------------------------------------------------

class StateProbabilitiesDefaultTests(unittest.TestCase):
    def test_missing_state_probabilities_defaults_to_empty_dict(self) -> None:
        legacy = _legacy_full_projection()
        legacy.pop("state_probabilities")
        result = build_projection_result_from_legacy(legacy, symbol="AVGO")
        self.assertEqual(result["payload"]["state_probabilities"], {})

    def test_non_dict_state_probabilities_defaults_to_empty_dict(self) -> None:
        legacy = _legacy_full_projection()
        legacy["state_probabilities"] = "not a dict"
        result = build_projection_result_from_legacy(legacy, symbol="AVGO")
        self.assertEqual(result["payload"]["state_probabilities"], {})


# ---------------------------------------------------------------------------
# 10. Invalid state in legacy produces validation_errors
# ---------------------------------------------------------------------------

class InvalidLegacyStateTests(unittest.TestCase):
    def test_invalid_top1_with_ready_true_produces_validation_error(self) -> None:
        legacy = _legacy_full_projection()
        legacy["predicted_top1"] = {"state": "BIG_UP"}  # invalid
        legacy["state_probabilities"] = {}
        legacy["ready"] = True  # ready=True with most_likely_state=None → error
        result = build_projection_result_from_legacy(legacy, symbol="AVGO")
        self.assertTrue(
            any(
                "most_likely_state may be None only when ready=False" in e
                for e in result["validation_errors"]
            ),
            msg=f"expected None+ready=True error; got {result['validation_errors']}",
        )

    def test_invalid_state_probability_value_produces_validation_error(self) -> None:
        legacy = _legacy_full_projection()
        legacy["state_probabilities"]["大涨"] = 1.5  # outside [0, 1]
        result = build_projection_result_from_legacy(legacy, symbol="AVGO")
        self.assertTrue(
            any(
                e.startswith("invalid value: state_probabilities['大涨']")
                for e in result["validation_errors"]
            ),
            msg=f"expected state_probabilities range error; got {result['validation_errors']}",
        )


# ---------------------------------------------------------------------------
# 11. symbol is required and passed through
# ---------------------------------------------------------------------------

class SymbolPassThroughTests(unittest.TestCase):
    def test_symbol_appears_at_top_level(self) -> None:
        result = build_projection_result_from_legacy(
            _legacy_full_projection(), symbol="NVDA"
        )
        self.assertEqual(result["payload"]["symbol"], "NVDA")

    def test_legacy_symbol_does_not_override_caller_symbol(self) -> None:
        legacy = _legacy_full_projection()
        legacy["symbol"] = "OTHER"
        result = build_projection_result_from_legacy(legacy, symbol="AVGO")
        self.assertEqual(result["payload"]["symbol"], "AVGO")


# ---------------------------------------------------------------------------
# 12. feature_snapshot_ref is deep-copied / preserved
# ---------------------------------------------------------------------------

class FeatureSnapshotRefTests(unittest.TestCase):
    def test_feature_snapshot_ref_string_preserved(self) -> None:
        result = build_projection_result_from_legacy(
            _legacy_full_projection(),
            symbol="AVGO",
            feature_snapshot_ref="ref://snapshot/abc",
        )
        self.assertEqual(
            result["payload"]["feature_snapshot_ref"], "ref://snapshot/abc"
        )

    def test_feature_snapshot_ref_dict_deep_copied(self) -> None:
        ref = {"path": "snapshot.csv", "checksum": "abc123"}
        result = build_projection_result_from_legacy(
            _legacy_full_projection(),
            symbol="AVGO",
            feature_snapshot_ref=ref,
        )
        self.assertEqual(result["payload"]["feature_snapshot_ref"], ref)
        # mutate returned dict; original unchanged
        result["payload"]["feature_snapshot_ref"]["path"] = "MUTATED"
        self.assertEqual(ref["path"], "snapshot.csv")

    def test_feature_snapshot_ref_default_none(self) -> None:
        result = build_projection_result_from_legacy(
            _legacy_full_projection(), symbol="AVGO"
        )
        self.assertIsNone(result["payload"]["feature_snapshot_ref"])


# ---------------------------------------------------------------------------
# 13. evidence / rationale / warnings passed through conservatively
# ---------------------------------------------------------------------------

class EvidenceRationaleWarningsPassThroughTests(unittest.TestCase):
    def test_rationale_passed_through(self) -> None:
        legacy = _legacy_full_projection()
        legacy["rationale"] = ["原因 1", "原因 2"]
        result = build_projection_result_from_legacy(legacy, symbol="AVGO")
        self.assertEqual(
            result["payload"]["rationale"], ["原因 1", "原因 2"]
        )

    def test_warnings_passed_through(self) -> None:
        legacy = _legacy_full_projection()
        legacy["warnings"] = ["警告 A"]
        result = build_projection_result_from_legacy(legacy, symbol="AVGO")
        self.assertEqual(result["payload"]["warnings"], ["警告 A"])

    def test_evidence_falls_back_to_key_observations(self) -> None:
        legacy = _legacy_full_projection()
        legacy.pop("rationale", None)
        legacy["key_observations"] = {"momentum": "rising"}
        result = build_projection_result_from_legacy(legacy, symbol="AVGO")
        self.assertEqual(
            result["payload"]["evidence"], {"momentum": "rising"}
        )

    def test_evidence_default_empty_dict(self) -> None:
        legacy = _legacy_full_projection()
        result = build_projection_result_from_legacy(legacy, symbol="AVGO")
        self.assertEqual(result["payload"]["evidence"], {})

    def test_rationale_default_empty_list(self) -> None:
        legacy = _legacy_full_projection()
        legacy.pop("rationale", None)
        result = build_projection_result_from_legacy(legacy, symbol="AVGO")
        self.assertEqual(result["payload"]["rationale"], [])

    def test_warnings_default_empty_list(self) -> None:
        legacy = _legacy_full_projection()
        legacy.pop("warnings", None)
        result = build_projection_result_from_legacy(legacy, symbol="AVGO")
        self.assertEqual(result["payload"]["warnings"], [])

    def test_raw_score_passed_through_when_int(self) -> None:
        legacy = _legacy_full_projection()
        legacy["raw_score"] = 0.42
        result = build_projection_result_from_legacy(legacy, symbol="AVGO")
        self.assertEqual(result["payload"]["raw_score"], 0.42)

    def test_raw_score_falls_back_to_score(self) -> None:
        legacy = _legacy_full_projection()
        legacy["score"] = 1
        result = build_projection_result_from_legacy(legacy, symbol="AVGO")
        self.assertEqual(result["payload"]["raw_score"], 1)

    def test_raw_score_default_none(self) -> None:
        legacy = _legacy_full_projection()
        result = build_projection_result_from_legacy(legacy, symbol="AVGO")
        self.assertIsNone(result["payload"]["raw_score"])

    def test_raw_score_bool_rejected(self) -> None:
        legacy = _legacy_full_projection()
        legacy["raw_score"] = True  # bool not allowed
        result = build_projection_result_from_legacy(legacy, symbol="AVGO")
        self.assertIsNone(result["payload"]["raw_score"])


# ---------------------------------------------------------------------------
# 14. historical_match_summary defaults to {}
# ---------------------------------------------------------------------------

class HistoricalMatchSummaryTests(unittest.TestCase):
    def test_historical_match_summary_default_empty_dict(self) -> None:
        legacy = _legacy_full_projection()
        result = build_projection_result_from_legacy(legacy, symbol="AVGO")
        self.assertEqual(result["payload"]["historical_match_summary"], {})

    def test_historical_match_summary_passed_through(self) -> None:
        legacy = _legacy_full_projection()
        legacy["historical_match_summary"] = {"top_match_count": 5}
        result = build_projection_result_from_legacy(legacy, symbol="AVGO")
        self.assertEqual(
            result["payload"]["historical_match_summary"],
            {"top_match_count": 5},
        )


# ---------------------------------------------------------------------------
# 15. peer_alignment_summary defaults to {} (or legacy peer_alignment)
# ---------------------------------------------------------------------------

class PeerAlignmentSummaryTests(unittest.TestCase):
    def test_peer_alignment_summary_uses_legacy_peer_alignment_dict(self) -> None:
        legacy = _legacy_full_projection()
        # legacy.peer_alignment is non-empty; should flow through
        result = build_projection_result_from_legacy(legacy, symbol="AVGO")
        self.assertEqual(
            result["payload"]["peer_alignment_summary"],
            legacy["peer_alignment"],
        )

    def test_peer_alignment_summary_default_empty_dict(self) -> None:
        legacy = {
            "kind": "main_projection_layer",
            "symbol": "AVGO",
            "ready": False,
            "state_probabilities": {},
            "warnings": [],
        }
        result = build_projection_result_from_legacy(legacy, symbol="AVGO")
        self.assertEqual(result["payload"]["peer_alignment_summary"], {})

    def test_peer_alignment_summary_explicit_takes_priority(self) -> None:
        legacy = _legacy_full_projection()
        legacy["peer_alignment_summary"] = {"alignment": "explicit"}
        result = build_projection_result_from_legacy(legacy, symbol="AVGO")
        self.assertEqual(
            result["payload"]["peer_alignment_summary"],
            {"alignment": "explicit"},
        )


# ---------------------------------------------------------------------------
# 16. non_mutation_confirmations 4 keys all True
# ---------------------------------------------------------------------------

class NonMutationConfirmationsTests(unittest.TestCase):
    def test_all_four_required_keys_are_true(self) -> None:
        result = build_projection_result_from_legacy(
            _legacy_full_projection(), symbol="AVGO"
        )
        nmc = result["payload"]["non_mutation_confirmations"]
        for key in (
            "projection_did_not_read_exclusion",
            "projection_did_not_read_confidence",
            "projection_did_not_read_final_report",
            "projection_did_not_read_future_outcome",
        ):
            with self.subTest(key=key):
                self.assertIs(nmc[key], True)

    def test_non_mutation_dict_is_isolated_per_call(self) -> None:
        # Mutating one call's nmc must not leak to subsequent calls.
        result_1 = build_projection_result_from_legacy(
            _legacy_full_projection(), symbol="AVGO"
        )
        result_1["payload"]["non_mutation_confirmations"][
            "projection_did_not_read_exclusion"
        ] = False
        result_2 = build_projection_result_from_legacy(
            _legacy_full_projection(), symbol="AVGO"
        )
        self.assertIs(
            result_2["payload"]["non_mutation_confirmations"][
                "projection_did_not_read_exclusion"
            ],
            True,
        )


# ---------------------------------------------------------------------------
# 17. Adapter does not mutate legacy_projection
# ---------------------------------------------------------------------------

class NoMutationOfLegacyInputTests(unittest.TestCase):
    def test_legacy_unchanged_after_call(self) -> None:
        legacy = _legacy_full_projection()
        snapshot = copy.deepcopy(legacy)
        build_projection_result_from_legacy(legacy, symbol="AVGO")
        self.assertEqual(legacy, snapshot)

    def test_legacy_unchanged_after_call_with_feature_snapshot_ref(self) -> None:
        legacy = _legacy_full_projection()
        snapshot = copy.deepcopy(legacy)
        build_projection_result_from_legacy(
            legacy,
            symbol="AVGO",
            feature_snapshot_ref={"some": "ref"},
        )
        self.assertEqual(legacy, snapshot)


# ---------------------------------------------------------------------------
# 18. Adapter deep-copies mutable fields
# ---------------------------------------------------------------------------

class DeepCopyTests(unittest.TestCase):
    def test_mutating_returned_payload_does_not_affect_legacy(self) -> None:
        legacy = _legacy_full_projection()
        result = build_projection_result_from_legacy(legacy, symbol="AVGO")
        result["payload"]["state_probabilities"]["大涨"] = 999.0
        result["payload"]["rationale"].append("MUTATED")
        result["payload"]["warnings"].append("MUTATED")
        result["payload"]["peer_alignment_summary"]["alignment"] = "MUTATED"

        self.assertEqual(legacy["state_probabilities"]["大涨"], 0.10)
        self.assertEqual(
            legacy["rationale"],
            ["主推演层已基于当前20日特征生成五状态分布。"],
        )
        self.assertEqual(legacy["warnings"], [])
        self.assertEqual(legacy["peer_alignment"]["alignment"], "neutral")

    def test_state_probabilities_object_identity_isolated(self) -> None:
        legacy = _legacy_full_projection()
        result = build_projection_result_from_legacy(legacy, symbol="AVGO")
        self.assertIsNot(
            result["payload"]["state_probabilities"],
            legacy["state_probabilities"],
        )


# ---------------------------------------------------------------------------
# 19. Adapter does not add forbidden upstream fields at top level
# ---------------------------------------------------------------------------

class NoForbiddenUpstreamFieldsTests(unittest.TestCase):
    def test_no_exclusion_or_confidence_or_final_at_top_level(self) -> None:
        result = build_projection_result_from_legacy(
            _legacy_full_projection(), symbol="AVGO"
        )
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
                self.assertNotIn(forbidden, result["payload"])

    def test_legacy_top_level_forbidden_fields_passed_through_to_validator(
        self,
    ) -> None:
        # If the legacy dict carries (incorrectly) a forbidden top-level
        # field, the adapter does not propagate it to the standard
        # payload — the new payload is a fresh dict assembled from a
        # known set of keys, so legacy stowaways cannot leak.
        legacy = _legacy_full_projection()
        legacy["exclusion_result"] = {"injected": True}
        legacy["final_direction"] = "偏多"
        result = build_projection_result_from_legacy(legacy, symbol="AVGO")
        self.assertNotIn("exclusion_result", result["payload"])
        self.assertNotIn("final_direction", result["payload"])
        self.assertEqual(result["validation_errors"], [])

    def test_predicted_top1_top2_not_in_standard_payload(self) -> None:
        # 18A §13 Option A: legacy interim alias predicted_top1/top2
        # forbidden at top level. Adapter strips them.
        result = build_projection_result_from_legacy(
            _legacy_full_projection(), symbol="AVGO"
        )
        self.assertNotIn("predicted_top1", result["payload"])
        self.assertNotIn("predicted_top2", result["payload"])


# ---------------------------------------------------------------------------
# 20. Adapter does not add trading / hard / forced fields at top level
# ---------------------------------------------------------------------------

class NoForbiddenTradingForcedFieldsTests(unittest.TestCase):
    def test_no_trading_or_forced_at_top_level(self) -> None:
        result = build_projection_result_from_legacy(
            _legacy_full_projection(), symbol="AVGO"
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
# 21. Module import boundary
# ---------------------------------------------------------------------------

class ImportBoundaryTests(unittest.TestCase):
    """``services.projection_result_adapter`` must remain a pure
    translator with zero coupling to active projection / exclusion /
    confidence / final / review / evaluation / orchestrator / UI / DB
    modules. The only allowed cross-module references are
    ``services.projection_result_contract`` + stdlib (typing / copy).
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = _read("services/projection_result_adapter.py")

    def test_no_main_projection_layer_import(self) -> None:
        for f in (
            "from services.main_projection_layer",
            "import services.main_projection_layer",
        ):
            self.assertNotIn(
                f, self.source,
                msg=f"adapter must not contain `{f}`",
            )

    def test_no_exclusion_or_confidence_or_final_imports(self) -> None:
        forbidden = (
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
            build_projection_result_from_legacy.__module__,
            "services.projection_result_adapter",
        )
        self.assertIs(
            adapter_mod.build_projection_result_from_legacy,
            build_projection_result_from_legacy,
        )


if __name__ == "__main__":
    unittest.main()
