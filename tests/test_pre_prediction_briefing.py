# -*- coding: utf-8 -*-
"""
tests/test_pre_prediction_briefing.py

Unit tests for services/pre_prediction_briefing.py.
All I/O is mocked — no DB, no network.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.pre_prediction_briefing import build_pre_prediction_briefing

_PATCH_SUMMARIZE = "services.pre_prediction_briefing.summarize_review_history"
_PATCH_SCENARIO  = "services.pre_prediction_briefing.summarize_review_history_by_open_scenario"
_PATCH_RULES     = "services.pre_prediction_briefing.extract_review_rules"

# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

_EMPTY_SUMMARY = {
    "symbol": "AVGO",
    "record_count": 0,
    "overall_accuracy": 0.0,
    "dimension_accuracy": {"open": None, "path": None, "close": None},
    "dimension_sample_count": {"open": 0, "path": 0, "close": 0},
    "weakest_dimension": None,
    "strongest_dimension": None,
    "error_category_counts": {},
    "primary_error_counts": {},
    "most_common_error_category": None,
    "most_common_primary_error": None,
}

_GOOD_SUMMARY = {
    "symbol": "AVGO",
    "record_count": 10,
    "overall_accuracy": 0.8,
    "dimension_accuracy": {"open": 0.9, "path": 0.8, "close": 0.7},
    "dimension_sample_count": {"open": 10, "path": 10, "close": 10},
    "weakest_dimension": "close",
    "strongest_dimension": "open",
    "error_category_counts": {"correct": 8, "wrong_direction": 2},
    "primary_error_counts": {"收盘判断错误": 2},
    "most_common_error_category": "correct",
    "most_common_primary_error": "收盘判断错误",
}

_WEAK_SUMMARY = {
    "symbol": "AVGO",
    "record_count": 8,
    "overall_accuracy": 0.45,
    "dimension_accuracy": {"open": 0.75, "path": 0.25, "close": 0.80},
    "dimension_sample_count": {"open": 8, "path": 8, "close": 8},
    "weakest_dimension": "path",
    "strongest_dimension": "close",
    "error_category_counts": {"wrong_direction": 6, "correct": 2},
    "primary_error_counts": {"路径判断错误": 5, "开盘判断错误": 1},
    "most_common_error_category": "wrong_direction",
    "most_common_primary_error": "路径判断错误",
}

_MOCK_ALL_RULES = ["整体命中率 80%（基于10条）", "最弱维度：收盘", "最常见误差：correct"]
_MOCK_WEAK_RULES = ["⚠ 路径判断准确率仅 25%", "历史最常见误判：路径判断错误", "整体命中率 45%"]

_HIGH_OPEN_SUMMARY = {
    "symbol": "AVGO",
    "record_count": 4,
    "overall_accuracy": 0.35,
    "dimension_accuracy": {"open": 0.75, "path": 0.25, "close": 0.75},
    "dimension_sample_count": {"open": 4, "path": 4, "close": 4},
    "weakest_dimension": "path",
    "strongest_dimension": "open",
    "error_category_counts": {"wrong_direction": 3, "correct": 1},
    "primary_error_counts": {"路径判断错误": 3},
    "most_common_error_category": "wrong_direction",
    "most_common_primary_error": "路径判断错误",
    "scenario_type": "pred_open",
    "scenario_value": "高开",
}

_SCENARIO_SUMMARY = {
    "symbol": "AVGO",
    "record_count": 10,
    "scenario_type": "pred_open",
    "scenario_values": ["高开", "低开", "平开"],
    "scenario_record_count": {"高开": 4, "低开": 0, "平开": 0},
    "available_scenarios": ["高开"],
    "unknown_count": 6,
    "scenarios": {
        "高开": _HIGH_OPEN_SUMMARY,
        "低开": dict(_EMPTY_SUMMARY, scenario_type="pred_open", scenario_value="低开"),
        "平开": dict(_EMPTY_SUMMARY, scenario_type="pred_open", scenario_value="平开"),
    },
}


def _run(
    summary=_GOOD_SUMMARY,
    all_rules=_MOCK_ALL_RULES,
    max_rules=3,
    pred_open=None,
    scenario_summary=_SCENARIO_SUMMARY,
) -> dict:
    with patch(_PATCH_SUMMARIZE, return_value=summary), \
         patch(_PATCH_SCENARIO, return_value=scenario_summary), \
         patch(_PATCH_RULES, return_value=all_rules):
        return build_pre_prediction_briefing("AVGO", limit=30, max_rules=max_rules, pred_open=pred_open)


# ─────────────────────────────────────────────────────────────────────────────
# Return schema
# ─────────────────────────────────────────────────────────────────────────────

class SchemaTests(unittest.TestCase):

    def setUp(self) -> None:
        self.result = _run()

    def _required_keys(self) -> set:
        return {
            "symbol", "record_count", "has_data", "overall_accuracy",
            "caution_level", "weakest_dimension", "weakest_dimension_cn",
            "weakest_accuracy", "most_common_primary_error",
            "top_rules", "all_rules", "rule_scope", "pred_open",
            "selected_open_scenario", "scenario_has_data", "scenario_summary",
            "scenario_rules", "scenario_top_rules", "advisory_only",
        }

    def test_required_keys_present(self) -> None:
        self.assertTrue(self._required_keys().issubset(self.result.keys()))

    def test_advisory_only_always_true(self) -> None:
        self.assertIs(self.result["advisory_only"], True)

    def test_top_rules_is_list(self) -> None:
        self.assertIsInstance(self.result["top_rules"], list)

    def test_all_rules_is_list(self) -> None:
        self.assertIsInstance(self.result["all_rules"], list)

    def test_caution_level_is_string(self) -> None:
        self.assertIsInstance(self.result["caution_level"], str)

    def test_symbol_passed_through(self) -> None:
        self.assertEqual(self.result["symbol"], "AVGO")

    def test_record_count_passed_through(self) -> None:
        self.assertEqual(self.result["record_count"], 10)


# ─────────────────────────────────────────────────────────────────────────────
# Empty history
# ─────────────────────────────────────────────────────────────────────────────

class EmptyHistoryTests(unittest.TestCase):

    def setUp(self) -> None:
        self.result = _run(summary=_EMPTY_SUMMARY, all_rules=[])

    def test_has_data_false(self) -> None:
        self.assertFalse(self.result["has_data"])

    def test_caution_level_none(self) -> None:
        self.assertEqual(self.result["caution_level"], "none")

    def test_weakest_dimension_none(self) -> None:
        self.assertIsNone(self.result["weakest_dimension"])

    def test_weakest_accuracy_none(self) -> None:
        self.assertIsNone(self.result["weakest_accuracy"])

    def test_most_common_primary_error_none(self) -> None:
        self.assertIsNone(self.result["most_common_primary_error"])

    def test_top_rules_nonempty_even_without_data(self) -> None:
        self.assertGreater(len(self.result["top_rules"]), 0)

    def test_top_rules_contains_no_data_message(self) -> None:
        combined = " ".join(self.result["top_rules"])
        self.assertIn("暂无", combined)


# ─────────────────────────────────────────────────────────────────────────────
# Good accuracy — caution_level = "low"
# ─────────────────────────────────────────────────────────────────────────────

class GoodAccuracyTests(unittest.TestCase):

    def setUp(self) -> None:
        self.result = _run(summary=_GOOD_SUMMARY)

    def test_has_data_true(self) -> None:
        self.assertTrue(self.result["has_data"])

    def test_caution_level_low(self) -> None:
        # overall 80%, weakest 70% — both above thresholds → "low"
        self.assertEqual(self.result["caution_level"], "low")

    def test_overall_accuracy_passed_through(self) -> None:
        self.assertAlmostEqual(self.result["overall_accuracy"], 0.8)

    def test_weakest_dimension_close(self) -> None:
        self.assertEqual(self.result["weakest_dimension"], "close")

    def test_weakest_dimension_cn_is_chinese(self) -> None:
        self.assertEqual(self.result["weakest_dimension_cn"], "收盘")

    def test_weakest_accuracy_passed_through(self) -> None:
        self.assertAlmostEqual(self.result["weakest_accuracy"], 0.7)

    def test_all_rules_matches_mock(self) -> None:
        self.assertEqual(self.result["all_rules"], _MOCK_ALL_RULES)


# ─────────────────────────────────────────────────────────────────────────────
# Weak accuracy — caution_level = "medium" or "high"
# ─────────────────────────────────────────────────────────────────────────────

class WeakAccuracyTests(unittest.TestCase):

    def setUp(self) -> None:
        self.result = _run(summary=_WEAK_SUMMARY, all_rules=_MOCK_WEAK_RULES)

    def test_caution_level_medium_or_high(self) -> None:
        self.assertIn(self.result["caution_level"], ("medium", "high"))

    def test_weakest_dimension_path(self) -> None:
        self.assertEqual(self.result["weakest_dimension"], "path")

    def test_weakest_dimension_cn_lu(self) -> None:
        self.assertEqual(self.result["weakest_dimension_cn"], "路径")

    def test_weakest_accuracy_low(self) -> None:
        self.assertLess(self.result["weakest_accuracy"], 0.5)

    def test_top_rules_includes_weak_dim_warning(self) -> None:
        combined = " ".join(self.result["top_rules"])
        self.assertIn("路径", combined)

    def test_top_rules_includes_primary_error(self) -> None:
        combined = " ".join(self.result["top_rules"])
        self.assertIn("路径判断错误", combined)

    def test_most_common_primary_error_is_path(self) -> None:
        self.assertEqual(self.result["most_common_primary_error"], "路径判断错误")


# ─────────────────────────────────────────────────────────────────────────────
# Open scenario briefing
# ─────────────────────────────────────────────────────────────────────────────

class OpenScenarioBriefingTests(unittest.TestCase):

    def test_without_pred_open_uses_global_scope(self) -> None:
        result = _run(summary=_GOOD_SUMMARY, pred_open=None)
        self.assertEqual(result["rule_scope"], "global")
        self.assertFalse(result["scenario_has_data"])
        self.assertEqual(result["record_count"], 10)
        self.assertEqual(result["global_record_count"], 10)

    def test_pred_open_with_history_uses_scenario_scope(self) -> None:
        result = _run(summary=_GOOD_SUMMARY, pred_open="高开")
        self.assertEqual(result["rule_scope"], "open_scenario")
        self.assertEqual(result["selected_open_scenario"], "高开")
        self.assertTrue(result["scenario_has_data"])
        self.assertEqual(result["record_count"], 4)
        self.assertEqual(result["global_record_count"], 10)

    def test_scenario_top_rules_name_open_scenario(self) -> None:
        result = _run(summary=_GOOD_SUMMARY, pred_open="高开")
        combined = " ".join(result["top_rules"])
        self.assertIn("高开场景", combined)
        self.assertIn("路径", combined)

    def test_unknown_pred_open_falls_back_to_global(self) -> None:
        result = _run(summary=_GOOD_SUMMARY, pred_open="跳空")
        self.assertEqual(result["rule_scope"], "global")
        self.assertEqual(result["selected_open_scenario"], None)
        self.assertEqual(result["record_count"], 10)
        self.assertEqual(result["scenario_top_rules"], [])

    def test_known_pred_open_without_history_falls_back_to_global(self) -> None:
        result = _run(summary=_GOOD_SUMMARY, pred_open="低开")
        self.assertEqual(result["rule_scope"], "global")
        self.assertEqual(result["selected_open_scenario"], "低开")
        self.assertFalse(result["scenario_has_data"])
        self.assertEqual(result["record_count"], 10)


# ─────────────────────────────────────────────────────────────────────────────
# max_rules respected
# ─────────────────────────────────────────────────────────────────────────────

class MaxRulesTests(unittest.TestCase):

    def test_top_rules_capped_at_max_rules(self) -> None:
        result = _run(summary=_WEAK_SUMMARY, max_rules=1)
        self.assertLessEqual(len(result["top_rules"]), 1)

    def test_top_rules_zero_max_returns_empty(self) -> None:
        result = _run(summary=_WEAK_SUMMARY, max_rules=0)
        self.assertEqual(result["top_rules"], [])

    def test_top_rules_large_max_does_not_exceed_available(self) -> None:
        result = _run(summary=_WEAK_SUMMARY, max_rules=100)
        # There are only a finite number of rules buildable from the summary
        self.assertIsInstance(result["top_rules"], list)


# ─────────────────────────────────────────────────────────────────────────────
# caution_level thresholds
# ─────────────────────────────────────────────────────────────────────────────

class CautionLevelTests(unittest.TestCase):

    def _summary_with(self, overall, weakest_acc) -> dict:
        base = dict(_WEAK_SUMMARY)
        base["overall_accuracy"] = overall
        da = {"open": 0.8, "path": weakest_acc, "close": 0.8}
        base["dimension_accuracy"] = da
        base["record_count"] = 5
        return base

    def test_high_caution_when_overall_below_34(self) -> None:
        result = _run(summary=self._summary_with(0.30, 0.50))
        self.assertEqual(result["caution_level"], "high")

    def test_high_caution_when_dim_below_34(self) -> None:
        result = _run(summary=self._summary_with(0.70, 0.30))
        self.assertEqual(result["caution_level"], "high")

    def test_medium_caution_when_overall_between_34_and_67(self) -> None:
        result = _run(summary=self._summary_with(0.50, 0.60))
        self.assertEqual(result["caution_level"], "medium")

    def test_medium_caution_when_dim_below_50(self) -> None:
        result = _run(summary=self._summary_with(0.80, 0.40))
        self.assertEqual(result["caution_level"], "medium")

    def test_low_caution_when_all_good(self) -> None:
        result = _run(summary=self._summary_with(0.80, 0.70))
        self.assertEqual(result["caution_level"], "low")


# ─────────────────────────────────────────────────────────────────────────────
# Dependency calls wired correctly
# ─────────────────────────────────────────────────────────────────────────────

class WiringTests(unittest.TestCase):

    def test_summarize_called_with_symbol_and_limit(self) -> None:
        with patch(_PATCH_SUMMARIZE, return_value=_EMPTY_SUMMARY) as mock_s, \
             patch(_PATCH_SCENARIO, return_value=_SCENARIO_SUMMARY), \
             patch(_PATCH_RULES, return_value=[]):
            build_pre_prediction_briefing("NVDA", limit=15)
        mock_s.assert_called_once_with(symbol="NVDA", limit=15)

    def test_scenario_summarize_called_with_symbol_and_limit(self) -> None:
        with patch(_PATCH_SUMMARIZE, return_value=_EMPTY_SUMMARY), \
             patch(_PATCH_SCENARIO, return_value=_SCENARIO_SUMMARY) as mock_scenario, \
             patch(_PATCH_RULES, return_value=[]):
            build_pre_prediction_briefing("NVDA", limit=15)
        mock_scenario.assert_called_once_with(symbol="NVDA", limit=15)

    def test_extract_rules_called_with_summary(self) -> None:
        with patch(_PATCH_SUMMARIZE, return_value=_GOOD_SUMMARY), \
             patch(_PATCH_SCENARIO, return_value=_SCENARIO_SUMMARY), \
             patch(_PATCH_RULES, return_value=_MOCK_ALL_RULES) as mock_r:
            build_pre_prediction_briefing("AVGO")
        mock_r.assert_called_once_with(_GOOD_SUMMARY)

    def test_extract_rules_called_for_selected_scenario(self) -> None:
        with patch(_PATCH_SUMMARIZE, return_value=_GOOD_SUMMARY), \
             patch(_PATCH_SCENARIO, return_value=_SCENARIO_SUMMARY), \
             patch(_PATCH_RULES, return_value=_MOCK_ALL_RULES) as mock_r:
            build_pre_prediction_briefing("AVGO", pred_open="高开")
        self.assertEqual(mock_r.call_count, 2)
        self.assertEqual(mock_r.call_args_list[0].args[0], _GOOD_SUMMARY)
        self.assertEqual(mock_r.call_args_list[1].args[0], _HIGH_OPEN_SUMMARY)

    def test_does_not_raise_on_any_summary(self) -> None:
        for summary in [_EMPTY_SUMMARY, _GOOD_SUMMARY, _WEAK_SUMMARY]:
            with patch(_PATCH_SUMMARIZE, return_value=summary), \
                 patch(_PATCH_SCENARIO, return_value=_SCENARIO_SUMMARY), \
                 patch(_PATCH_RULES, return_value=[]):
                result = build_pre_prediction_briefing("AVGO")
            self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main()
