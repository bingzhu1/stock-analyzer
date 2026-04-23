# -*- coding: utf-8 -*-
"""
tests/test_review_analyzer.py

Unit tests for services/review_analyzer.py.
All review_store I/O is mocked — no DB, no file system access.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.review_analyzer import (
    summarize_review_history,
    summarize_review_history_by_open_scenario,
    extract_review_rules,
)

_PATCH_LOAD = "services.review_analyzer.load_review_records"

# ─────────────────────────────────────────────────────────────────────────────
# Synthetic fixtures
# ─────────────────────────────────────────────────────────────────────────────

def _make_row(
    open_correct=True,
    path_correct=True,
    close_correct=True,
    overall_score=1.0,
    error_category="correct",
    primary_error=None,
    pred_open="高开",
) -> dict:
    return {
        "symbol": "AVGO",
        "prediction_for_date": "2026-04-21",
        "overall_score": overall_score,
        "correct_count": sum(1 for x in [open_correct, path_correct, close_correct] if x is True),
        "total_count": 3,
        "open_correct": open_correct,
        "path_correct": path_correct,
        "close_correct": close_correct,
        "error_category": error_category,
        "primary_error": primary_error,
        "pred_open": pred_open,
        "error_types_json": [],
        "reason_guesses_json": [],
    }


_ALL_CORRECT = _make_row(True, True, True, 1.0, "correct", None)
_ALL_WRONG   = _make_row(False, False, False, 0.0, "wrong_direction", "路径判断错误")
_MIXED_1     = _make_row(True, False, True, 2/3, "wrong_direction", "路径判断错误")
_MIXED_2     = _make_row(False, True, True, 2/3, "wrong_direction", "开盘判断错误")
_UNCLEAR     = _make_row(None, None, None, 0.0, "insufficient_data", None)


def _run_summary(records, symbol="AVGO", limit=30) -> dict:
    with patch(_PATCH_LOAD, return_value=records):
        return summarize_review_history(symbol, limit)


def _run_scenario_summary(records, symbol="AVGO", limit=30) -> dict:
    with patch(_PATCH_LOAD, return_value=records):
        return summarize_review_history_by_open_scenario(symbol, limit)


# ─────────────────────────────────────────────────────────────────────────────
# Empty history
# ─────────────────────────────────────────────────────────────────────────────

class EmptyHistoryTests(unittest.TestCase):

    def setUp(self) -> None:
        self.summary = _run_summary([])

    def test_record_count_zero(self) -> None:
        self.assertEqual(self.summary["record_count"], 0)

    def test_overall_accuracy_zero(self) -> None:
        self.assertEqual(self.summary["overall_accuracy"], 0.0)

    def test_dimension_accuracy_all_none(self) -> None:
        da = self.summary["dimension_accuracy"]
        for dim in ("open", "path", "close"):
            self.assertIsNone(da[dim])

    def test_weakest_dimension_none(self) -> None:
        self.assertIsNone(self.summary["weakest_dimension"])

    def test_strongest_dimension_none(self) -> None:
        self.assertIsNone(self.summary["strongest_dimension"])

    def test_error_category_counts_empty(self) -> None:
        self.assertEqual(self.summary["error_category_counts"], {})

    def test_most_common_error_category_none(self) -> None:
        self.assertIsNone(self.summary["most_common_error_category"])

    def test_most_common_primary_error_none(self) -> None:
        self.assertIsNone(self.summary["most_common_primary_error"])


# ─────────────────────────────────────────────────────────────────────────────
# All-correct history
# ─────────────────────────────────────────────────────────────────────────────

class AllCorrectTests(unittest.TestCase):

    def setUp(self) -> None:
        self.summary = _run_summary([_ALL_CORRECT] * 5)

    def test_record_count(self) -> None:
        self.assertEqual(self.summary["record_count"], 5)

    def test_overall_accuracy_one(self) -> None:
        self.assertAlmostEqual(self.summary["overall_accuracy"], 1.0)

    def test_open_accuracy_one(self) -> None:
        self.assertAlmostEqual(self.summary["dimension_accuracy"]["open"], 1.0)

    def test_path_accuracy_one(self) -> None:
        self.assertAlmostEqual(self.summary["dimension_accuracy"]["path"], 1.0)

    def test_close_accuracy_one(self) -> None:
        self.assertAlmostEqual(self.summary["dimension_accuracy"]["close"], 1.0)

    def test_open_sample_count(self) -> None:
        self.assertEqual(self.summary["dimension_sample_count"]["open"], 5)

    def test_most_common_category_correct(self) -> None:
        self.assertEqual(self.summary["most_common_error_category"], "correct")

    def test_most_common_primary_error_none(self) -> None:
        self.assertIsNone(self.summary["most_common_primary_error"])


# ─────────────────────────────────────────────────────────────────────────────
# All-wrong history
# ─────────────────────────────────────────────────────────────────────────────

class AllWrongTests(unittest.TestCase):

    def setUp(self) -> None:
        self.summary = _run_summary([_ALL_WRONG] * 4)

    def test_overall_accuracy_zero(self) -> None:
        self.assertAlmostEqual(self.summary["overall_accuracy"], 0.0)

    def test_open_accuracy_zero(self) -> None:
        self.assertAlmostEqual(self.summary["dimension_accuracy"]["open"], 0.0)

    def test_path_accuracy_zero(self) -> None:
        self.assertAlmostEqual(self.summary["dimension_accuracy"]["path"], 0.0)

    def test_most_common_primary_error(self) -> None:
        self.assertEqual(self.summary["most_common_primary_error"], "路径判断错误")


# ─────────────────────────────────────────────────────────────────────────────
# Mixed history — dimension accuracy computed correctly
# ─────────────────────────────────────────────────────────────────────────────

class MixedAccuracyTests(unittest.TestCase):

    def setUp(self) -> None:
        # 4 rows: open=True x3 + False x1 → 75%; path=False x3 + True x1 → 25%; close=True x4 → 100%
        records = [
            _make_row(True, False, True, 2/3, "wrong_direction", "路径判断错误"),
            _make_row(True, False, True, 2/3, "wrong_direction", "路径判断错误"),
            _make_row(True, False, True, 2/3, "wrong_direction", "路径判断错误"),
            _make_row(False, True, True, 2/3, "wrong_direction", "开盘判断错误"),
        ]
        self.summary = _run_summary(records)

    def test_open_accuracy(self) -> None:
        self.assertAlmostEqual(self.summary["dimension_accuracy"]["open"], 0.75)

    def test_path_accuracy(self) -> None:
        self.assertAlmostEqual(self.summary["dimension_accuracy"]["path"], 0.25)

    def test_close_accuracy(self) -> None:
        self.assertAlmostEqual(self.summary["dimension_accuracy"]["close"], 1.0)

    def test_weakest_dimension_is_path(self) -> None:
        self.assertEqual(self.summary["weakest_dimension"], "path")

    def test_strongest_dimension_is_close(self) -> None:
        self.assertEqual(self.summary["strongest_dimension"], "close")

    def test_overall_accuracy(self) -> None:
        self.assertAlmostEqual(self.summary["overall_accuracy"], 2/3)


# ─────────────────────────────────────────────────────────────────────────────
# None-flagged dimensions excluded from sample count
# ─────────────────────────────────────────────────────────────────────────────

class NoneExclusionTests(unittest.TestCase):

    def test_none_dims_excluded_from_sample_count(self) -> None:
        summary = _run_summary([_UNCLEAR] * 3)
        for dim in ("open", "path", "close"):
            self.assertEqual(summary["dimension_sample_count"][dim], 0)

    def test_none_dims_give_none_accuracy(self) -> None:
        summary = _run_summary([_UNCLEAR] * 3)
        for dim in ("open", "path", "close"):
            self.assertIsNone(summary["dimension_accuracy"][dim])

    def test_none_dims_no_weakest(self) -> None:
        summary = _run_summary([_UNCLEAR] * 3)
        self.assertIsNone(summary["weakest_dimension"])

    def test_mixed_none_and_bool(self) -> None:
        rows = [
            _make_row(True, None, True),
            _make_row(True, None, False),
        ]
        summary = _run_summary(rows)
        self.assertEqual(summary["dimension_sample_count"]["path"], 0)
        self.assertIsNone(summary["dimension_accuracy"]["path"])
        self.assertAlmostEqual(summary["dimension_accuracy"]["open"], 1.0)
        self.assertAlmostEqual(summary["dimension_accuracy"]["close"], 0.5)


# ─────────────────────────────────────────────────────────────────────────────
# Error category and primary error counting
# ─────────────────────────────────────────────────────────────────────────────

class CategoryCountTests(unittest.TestCase):

    def setUp(self) -> None:
        records = [
            _make_row(error_category="wrong_direction", primary_error="路径判断错误"),
            _make_row(error_category="wrong_direction", primary_error="路径判断错误"),
            _make_row(error_category="correct", primary_error=None),
        ]
        self.summary = _run_summary(records)

    def test_error_category_counts(self) -> None:
        counts = self.summary["error_category_counts"]
        self.assertEqual(counts["wrong_direction"], 2)
        self.assertEqual(counts["correct"], 1)

    def test_most_common_error_category(self) -> None:
        self.assertEqual(self.summary["most_common_error_category"], "wrong_direction")

    def test_primary_error_counts(self) -> None:
        counts = self.summary["primary_error_counts"]
        self.assertEqual(counts["路径判断错误"], 2)
        self.assertNotIn("", counts)

    def test_most_common_primary_error(self) -> None:
        self.assertEqual(self.summary["most_common_primary_error"], "路径判断错误")


# ─────────────────────────────────────────────────────────────────────────────
# summarize_review_history — return schema
# ─────────────────────────────────────────────────────────────────────────────

class SummarySchemaTests(unittest.TestCase):

    def setUp(self) -> None:
        self.summary = _run_summary([_ALL_CORRECT] * 5)

    def _required_keys(self) -> set:
        return {
            "symbol", "record_count", "overall_accuracy",
            "dimension_accuracy", "dimension_sample_count",
            "weakest_dimension", "strongest_dimension",
            "error_category_counts", "primary_error_counts",
            "most_common_error_category", "most_common_primary_error",
        }

    def test_required_keys_present(self) -> None:
        self.assertTrue(self._required_keys().issubset(self.summary.keys()))

    def test_dimension_accuracy_has_three_keys(self) -> None:
        self.assertEqual(set(self.summary["dimension_accuracy"].keys()), {"open", "path", "close"})

    def test_dimension_sample_count_has_three_keys(self) -> None:
        self.assertEqual(set(self.summary["dimension_sample_count"].keys()), {"open", "path", "close"})

    def test_symbol_passed_through(self) -> None:
        self.assertEqual(self.summary["symbol"], "AVGO")

    def test_error_category_counts_is_dict(self) -> None:
        self.assertIsInstance(self.summary["error_category_counts"], dict)

    def test_primary_error_counts_is_dict(self) -> None:
        self.assertIsInstance(self.summary["primary_error_counts"], dict)


# ─────────────────────────────────────────────────────────────────────────────
# summarize_review_history_by_open_scenario
# ─────────────────────────────────────────────────────────────────────────────

class OpenScenarioSummaryTests(unittest.TestCase):

    def setUp(self) -> None:
        self.records = [
            _make_row(True, False, True, 2/3, "wrong_direction", "路径判断错误", pred_open="高开"),
            _make_row(True, True, True, 1.0, "correct", None, pred_open="高开"),
            _make_row(False, True, True, 2/3, "wrong_direction", "开盘判断错误", pred_open="低开"),
            _make_row(True, True, False, 2/3, "wrong_direction", "收盘判断错误", pred_open="平开"),
            _make_row(True, True, True, 1.0, "correct", None, pred_open="未知"),
            _make_row(True, True, True, 1.0, "correct", None, pred_open=None),
        ]
        self.summary = _run_scenario_summary(self.records)

    def test_top_level_schema(self) -> None:
        required = {
            "symbol", "record_count", "scenario_type", "scenario_values",
            "scenario_record_count", "available_scenarios", "unknown_count", "scenarios",
        }
        self.assertTrue(required.issubset(self.summary.keys()))

    def test_fixed_open_scenarios_present(self) -> None:
        self.assertEqual(set(self.summary["scenarios"].keys()), {"高开", "低开", "平开"})

    def test_record_count_includes_unknown_rows(self) -> None:
        self.assertEqual(self.summary["record_count"], 6)

    def test_unknown_pred_open_counted_separately(self) -> None:
        self.assertEqual(self.summary["unknown_count"], 2)

    def test_scenario_record_counts(self) -> None:
        self.assertEqual(self.summary["scenario_record_count"], {"高开": 2, "低开": 1, "平开": 1})

    def test_available_scenarios(self) -> None:
        self.assertEqual(self.summary["available_scenarios"], ["高开", "低开", "平开"])

    def test_high_open_group_accuracy(self) -> None:
        high = self.summary["scenarios"]["高开"]
        self.assertEqual(high["scenario_type"], "pred_open")
        self.assertEqual(high["scenario_value"], "高开")
        self.assertEqual(high["record_count"], 2)
        self.assertAlmostEqual(high["overall_accuracy"], (2/3 + 1.0) / 2)
        self.assertAlmostEqual(high["dimension_accuracy"]["path"], 0.5)

    def test_empty_scenario_bucket_kept(self) -> None:
        summary = _run_scenario_summary([
            _make_row(pred_open="高开"),
        ])
        flat = summary["scenarios"]["平开"]
        self.assertEqual(flat["record_count"], 0)
        self.assertIsNone(flat["dimension_accuracy"]["open"])

    def test_extract_rules_can_name_scenario(self) -> None:
        high = self.summary["scenarios"]["高开"]
        rules = extract_review_rules(high)
        combined = " ".join(rules)
        self.assertIn("高开场景", combined)


# ─────────────────────────────────────────────────────────────────────────────
# extract_review_rules — empty history
# ─────────────────────────────────────────────────────────────────────────────

class ExtractRulesEmptyTests(unittest.TestCase):

    def setUp(self) -> None:
        self.rules = extract_review_rules(_run_summary([]))

    def test_returns_list(self) -> None:
        self.assertIsInstance(self.rules, list)

    def test_returns_nonempty_list(self) -> None:
        self.assertGreater(len(self.rules), 0)

    def test_contains_no_history_message(self) -> None:
        combined = " ".join(self.rules)
        self.assertIn("暂无", combined)


# ─────────────────────────────────────────────────────────────────────────────
# extract_review_rules — with data
# ─────────────────────────────────────────────────────────────────────────────

class ExtractRulesDataTests(unittest.TestCase):

    def setUp(self) -> None:
        records = [
            _make_row(True, False, True, 2/3, "wrong_direction", "路径判断错误"),
            _make_row(True, False, True, 2/3, "wrong_direction", "路径判断错误"),
            _make_row(True, False, True, 2/3, "wrong_direction", "路径判断错误"),
            _make_row(False, True, True, 2/3, "wrong_direction", "开盘判断错误"),
            _make_row(True, True, True, 1.0, "correct", None),
        ]
        self.summary = _run_summary(records)
        self.rules = extract_review_rules(self.summary)

    def test_returns_list(self) -> None:
        self.assertIsInstance(self.rules, list)

    def test_at_least_one_rule(self) -> None:
        self.assertGreater(len(self.rules), 0)

    def test_overall_accuracy_rule_present(self) -> None:
        combined = " ".join(self.rules)
        self.assertIn("命中率", combined)

    def test_weakest_dimension_rule_present(self) -> None:
        combined = " ".join(self.rules)
        self.assertIn("路径", combined)

    def test_error_category_rule_present(self) -> None:
        combined = " ".join(self.rules)
        self.assertIn("wrong_direction", combined)

    def test_primary_error_rule_present(self) -> None:
        combined = " ".join(self.rules)
        self.assertIn("路径判断错误", combined)

    def test_each_rule_is_string(self) -> None:
        for rule in self.rules:
            self.assertIsInstance(rule, str)

    def test_each_rule_nonempty(self) -> None:
        for rule in self.rules:
            self.assertGreater(len(rule), 0)


# ─────────────────────────────────────────────────────────────────────────────
# extract_review_rules — small sample warning
# ─────────────────────────────────────────────────────────────────────────────

class ExtractRulesSmallSampleTests(unittest.TestCase):

    def test_small_sample_warning_present(self) -> None:
        summary = _run_summary([_ALL_CORRECT] * 2)
        rules = extract_review_rules(summary)
        combined = " ".join(rules)
        self.assertIn("样本量较少", combined)

    def test_sufficient_sample_no_small_warning(self) -> None:
        summary = _run_summary([_ALL_CORRECT] * 5)
        rules = extract_review_rules(summary)
        combined = " ".join(rules)
        self.assertNotIn("样本量较少", combined)


# ─────────────────────────────────────────────────────────────────────────────
# extract_review_rules — strong dimension
# ─────────────────────────────────────────────────────────────────────────────

class ExtractRulesStrongDimTests(unittest.TestCase):

    def test_strong_dimension_noted_when_above_threshold(self) -> None:
        # close always correct (100%), path always wrong → close is strongest
        records = [
            _make_row(True, False, True, 2/3, "wrong_direction", "路径判断错误"),
        ] * 5
        summary = _run_summary(records)
        rules = extract_review_rules(summary)
        combined = " ".join(rules)
        self.assertIn("优势维度", combined)
        self.assertIn("收盘", combined)

    def test_strongest_not_duplicated_with_weakest(self) -> None:
        # only one dim with sufficient sample — weakest == strongest
        records = [
            _make_row(True, None, None, 1/3, "correct", None),
        ] * 5
        summary = _run_summary(records)
        rules = extract_review_rules(summary)
        # "优势维度" should not appear since weakest == strongest
        combined = " ".join(rules)
        self.assertNotIn("优势维度", combined)


# ─────────────────────────────────────────────────────────────────────────────
# load_review_records called with correct args
# ─────────────────────────────────────────────────────────────────────────────

class LoadCallArgsTests(unittest.TestCase):

    def test_load_called_with_symbol_and_limit(self) -> None:
        with patch(_PATCH_LOAD, return_value=[]) as mock_load:
            summarize_review_history("NVDA", limit=10)
        mock_load.assert_called_once_with(symbol="NVDA", limit=10)

    def test_scenario_load_called_with_symbol_and_limit(self) -> None:
        with patch(_PATCH_LOAD, return_value=[]) as mock_load:
            summarize_review_history_by_open_scenario("NVDA", limit=10)
        mock_load.assert_called_once_with(symbol="NVDA", limit=10)


if __name__ == "__main__":
    unittest.main()
