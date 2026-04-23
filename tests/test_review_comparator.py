# -*- coding: utf-8 -*-
"""
tests/test_review_comparator.py

Unit tests for services/review_comparator.py.
All tests use synthetic dicts — no DB, no network.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.review_comparator import compare_prediction_vs_actual, extract_prediction_structure


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

def _make_prediction_raw(
    *,
    bias: str = "bullish",
    confidence: str = "medium",
    open_tendency: str = "gap_up_bias",
    close_tendency: str = "close_strong",
) -> dict:
    """Shape 3: raw prediction_log row — predict_result_json is a JSON string."""
    pr = {
        "final_bias": bias,
        "open_tendency": open_tendency,
        "close_tendency": close_tendency,
        "prediction_summary": "Test",
        "notes": "Unit test",
        "supporting_factors": [],
        "conflicting_factors": [],
    }
    return {
        "symbol": "AVGO",
        "prediction_for_date": "2026-04-21",
        "final_bias": bias,
        "final_confidence": confidence,
        "predict_result_json": json.dumps(pr),
    }


def _make_prediction_premapped(
    *,
    bias: str = "bullish",
    confidence: str = "medium",
    pred_open: str | None = "高开",
    pred_path: str | None = "高开高走",
    pred_close: str | None = "收涨",
) -> dict:
    """Shape 1: top-level Chinese labels already set."""
    d: dict = {
        "symbol": "AVGO",
        "prediction_for_date": "2026-04-21",
        "final_bias": bias,
        "final_confidence": confidence,
    }
    if pred_open is not None:
        d["pred_open"] = pred_open
    if pred_path is not None:
        d["pred_path"] = pred_path
    if pred_close is not None:
        d["pred_close"] = pred_close
    return d


def _make_prediction_nested(
    *,
    bias: str = "bullish",
    pred_open: str = "高开",
    pred_path: str = "高开高走",
    pred_close: str = "收涨",
    use_json_string: bool = False,
) -> dict:
    """Shape 2: fields nested under 'predict_result' (dict or JSON string)."""
    nested: dict = {
        "pred_open": pred_open,
        "pred_path": pred_path,
        "pred_close": pred_close,
    }
    return {
        "symbol": "AVGO",
        "prediction_for_date": "2026-04-21",
        "final_bias": bias,
        "final_confidence": "medium",
        "predict_result": json.dumps(nested) if use_json_string else nested,
    }


def _make_prediction_nested_tendency(
    *,
    open_tendency: str = "gap_up_bias",
    close_tendency: str = "close_strong",
) -> dict:
    """Shape 2b: nested predict_result with tendency keys (not pre-mapped)."""
    return {
        "symbol": "AVGO",
        "prediction_for_date": "2026-04-21",
        "final_bias": "bullish",
        "final_confidence": "medium",
        "predict_result": {
            "open_tendency": open_tendency,
            "close_tendency": close_tendency,
        },
    }


def _make_actual_premapped(
    *,
    actual_open_type: str = "高开",
    actual_path: str = "高开高走",
    actual_close_type: str = "收涨",
    direction_correct: int | None = 1,
    close_change: float = 0.018,
) -> dict:
    return {
        "actual_open_type": actual_open_type,
        "actual_path": actual_path,
        "actual_close_type": actual_close_type,
        "direction_correct": direction_correct,
        "actual_close_change": close_change,
    }


# ─────────────────────────────────────────────────────────────────────────────
# extract_prediction_structure
# ─────────────────────────────────────────────────────────────────────────────

class ExtractPredictionStructureTests(unittest.TestCase):

    def test_shape1_top_level_labels(self) -> None:
        pred = _make_prediction_premapped(pred_open="低开", pred_path="低开低走",
                                          pred_close="收跌")
        s = extract_prediction_structure(pred)
        self.assertEqual(s["pred_open"], "低开")
        self.assertEqual(s["pred_path"], "低开低走")
        self.assertEqual(s["pred_close"], "收跌")

    def test_shape2_nested_dict(self) -> None:
        pred = _make_prediction_nested(pred_open="高开", pred_path="高开高走",
                                       pred_close="收涨")
        s = extract_prediction_structure(pred)
        self.assertEqual(s["pred_open"], "高开")
        self.assertEqual(s["pred_path"], "高开高走")
        self.assertEqual(s["pred_close"], "收涨")

    def test_shape2_nested_json_string(self) -> None:
        pred = _make_prediction_nested(pred_open="平开", pred_path="平开走高",
                                       pred_close="收涨", use_json_string=True)
        s = extract_prediction_structure(pred)
        self.assertEqual(s["pred_open"], "平开")
        self.assertEqual(s["pred_path"], "平开走高")
        self.assertEqual(s["pred_close"], "收涨")

    def test_shape2_nested_tendency_keys(self) -> None:
        pred = _make_prediction_nested_tendency(open_tendency="gap_up_bias",
                                                close_tendency="close_strong")
        s = extract_prediction_structure(pred)
        self.assertEqual(s["pred_open"], "高开")
        self.assertEqual(s["pred_close"], "收涨")
        self.assertEqual(s["pred_path"], "高开高走")  # derived

    def test_shape3_predict_result_json_string(self) -> None:
        pred = _make_prediction_raw(open_tendency="gap_down_bias",
                                    close_tendency="close_weak")
        s = extract_prediction_structure(pred)
        self.assertEqual(s["pred_open"], "低开")
        self.assertEqual(s["pred_close"], "收跌")
        self.assertEqual(s["pred_path"], "低开低走")

    def test_top_level_wins_over_nested(self) -> None:
        pred = _make_prediction_nested(pred_open="低开", pred_path="低开低走",
                                       pred_close="收跌")
        pred["pred_open"] = "高开"  # top-level should win
        s = extract_prediction_structure(pred)
        self.assertEqual(s["pred_open"], "高开")

    def test_missing_fields_return_none(self) -> None:
        s = extract_prediction_structure({})
        self.assertIsNone(s["pred_open"])
        self.assertIsNone(s["pred_path"])
        self.assertIsNone(s["pred_close"])

    def test_corrupt_predict_result_json_returns_none(self) -> None:
        pred = {"predict_result_json": "{{not-valid-json"}
        s = extract_prediction_structure(pred)
        self.assertIsNone(s["pred_open"])

    def test_pred_path_derived_when_only_open_close_present(self) -> None:
        pred = {"pred_open": "平开", "pred_close": "收跌"}
        s = extract_prediction_structure(pred)
        self.assertEqual(s["pred_path"], "平开走低")


# ─────────────────────────────────────────────────────────────────────────────
# Required test cases (spec §Tests)
# ─────────────────────────────────────────────────────────────────────────────

class AllCorrectTests(unittest.TestCase):
    """1. All three dimensions correct."""

    def setUp(self) -> None:
        self.result = compare_prediction_vs_actual(
            _make_prediction_premapped(pred_open="高开", pred_path="高开高走",
                                       pred_close="收涨"),
            _make_actual_premapped(actual_open_type="高开", actual_path="高开高走",
                                   actual_close_type="收涨", direction_correct=1,
                                   close_change=0.018),
        )

    def test_all_correct_flags_true(self) -> None:
        self.assertTrue(self.result["open_correct"])
        self.assertTrue(self.result["path_correct"])
        self.assertTrue(self.result["close_correct"])

    def test_correct_count_3(self) -> None:
        self.assertEqual(self.result["correct_count"], 3)

    def test_total_count_always_3(self) -> None:
        self.assertEqual(self.result["total_count"], 3)

    def test_overall_score_1(self) -> None:
        self.assertAlmostEqual(self.result["overall_score"], 1.0)

    def test_no_missing_fields(self) -> None:
        self.assertEqual(self.result["_missing_fields"], [])


class AllWrongTests(unittest.TestCase):
    """2. All three dimensions wrong — exact spec example."""

    def setUp(self) -> None:
        self.result = compare_prediction_vs_actual(
            _make_prediction_premapped(pred_open="高开", pred_path="高开高走",
                                       pred_close="收涨"),
            _make_actual_premapped(actual_open_type="低开", actual_path="低开低走",
                                   actual_close_type="收跌", direction_correct=0,
                                   close_change=-0.02),
        )

    def test_all_correct_flags_false(self) -> None:
        self.assertFalse(self.result["open_correct"])
        self.assertFalse(self.result["path_correct"])
        self.assertFalse(self.result["close_correct"])

    def test_correct_count_0(self) -> None:
        self.assertEqual(self.result["correct_count"], 0)

    def test_total_count_3(self) -> None:
        self.assertEqual(self.result["total_count"], 3)

    def test_overall_score_0(self) -> None:
        self.assertAlmostEqual(self.result["overall_score"], 0.0)

    def test_spec_exact_output_shape(self) -> None:
        r = self.result
        self.assertEqual(r["symbol"], "AVGO")
        self.assertEqual(r["pred_open"], "高开")
        self.assertEqual(r["pred_path"], "高开高走")
        self.assertEqual(r["pred_close"], "收涨")
        self.assertEqual(r["actual_open_type"], "低开")
        self.assertEqual(r["actual_path"], "低开低走")
        self.assertEqual(r["actual_close_type"], "收跌")


class PartiallyCorrectTests(unittest.TestCase):
    """3. Partially correct — only open matched."""

    def setUp(self) -> None:
        self.result = compare_prediction_vs_actual(
            _make_prediction_premapped(pred_open="高开", pred_path="高开高走",
                                       pred_close="收涨"),
            _make_actual_premapped(actual_open_type="高开", actual_path="低开低走",
                                   actual_close_type="收跌", direction_correct=0,
                                   close_change=-0.02),
        )

    def test_open_correct_only(self) -> None:
        self.assertTrue(self.result["open_correct"])
        self.assertFalse(self.result["path_correct"])
        self.assertFalse(self.result["close_correct"])

    def test_correct_count_1(self) -> None:
        self.assertEqual(self.result["correct_count"], 1)

    def test_total_count_3(self) -> None:
        self.assertEqual(self.result["total_count"], 3)

    def test_overall_score_one_third(self) -> None:
        self.assertAlmostEqual(self.result["overall_score"], 1 / 3)

    def test_two_of_three_correct(self) -> None:
        r = compare_prediction_vs_actual(
            _make_prediction_premapped(pred_open="高开", pred_path="高开高走",
                                       pred_close="收涨"),
            _make_actual_premapped(actual_open_type="高开", actual_path="高开高走",
                                   actual_close_type="收跌"),
        )
        self.assertEqual(r["correct_count"], 2)
        self.assertAlmostEqual(r["overall_score"], 2 / 3)


class MissingPredictionFieldsTests(unittest.TestCase):
    """4. Missing prediction fields — must not crash; must report them."""

    def test_entirely_empty_prediction_does_not_crash(self) -> None:
        r = compare_prediction_vs_actual({}, _make_actual_premapped())
        self.assertIsNotNone(r)

    def test_missing_fields_listed_in_diagnostic(self) -> None:
        r = compare_prediction_vs_actual({}, _make_actual_premapped())
        self.assertIn("pred_open", r["_missing_fields"])
        self.assertIn("pred_path", r["_missing_fields"])
        self.assertIn("pred_close", r["_missing_fields"])

    def test_missing_fields_give_none_correct_flags(self) -> None:
        r = compare_prediction_vs_actual({}, _make_actual_premapped())
        self.assertIsNone(r["open_correct"])
        self.assertIsNone(r["path_correct"])
        self.assertIsNone(r["close_correct"])

    def test_missing_fields_score_zero(self) -> None:
        r = compare_prediction_vs_actual({}, _make_actual_premapped())
        self.assertEqual(r["correct_count"], 0)
        self.assertEqual(r["total_count"], 3)
        self.assertAlmostEqual(r["overall_score"], 0.0)

    def test_partial_missing_fields_reported(self) -> None:
        # Only pred_close is missing
        pred = {"symbol": "AVGO", "prediction_for_date": "2026-04-21",
                "final_bias": "bullish", "final_confidence": "medium",
                "pred_open": "高开", "pred_path": "高开高走"}
        r = compare_prediction_vs_actual(pred, _make_actual_premapped())
        self.assertIn("pred_close", r["_missing_fields"])
        self.assertNotIn("pred_open", r["_missing_fields"])
        self.assertNotIn("pred_path", r["_missing_fields"])

    def test_corrupt_json_does_not_crash(self) -> None:
        pred = _make_prediction_raw()
        pred["predict_result_json"] = "{{not-json"
        r = compare_prediction_vs_actual(pred, _make_actual_premapped())
        self.assertIsNotNone(r)
        self.assertIn("pred_open", r["_missing_fields"])

    def test_none_values_not_fabricated(self) -> None:
        r = compare_prediction_vs_actual({}, {})
        self.assertIsNone(r["pred_open"])
        self.assertIsNone(r["pred_path"])
        self.assertIsNone(r["pred_close"])
        self.assertIsNone(r["actual_open_type"])
        self.assertIsNone(r["actual_path"])
        self.assertIsNone(r["actual_close_type"])


class NestedPredictResultTests(unittest.TestCase):
    """5. Prediction fields nested inside predict_result."""

    def test_nested_dict_with_chinese_labels(self) -> None:
        pred = _make_prediction_nested(pred_open="低开", pred_path="低开高走",
                                       pred_close="收涨")
        r = compare_prediction_vs_actual(
            pred,
            _make_actual_premapped(actual_open_type="低开", actual_path="低开高走",
                                   actual_close_type="收涨"),
        )
        self.assertEqual(r["pred_open"], "低开")
        self.assertEqual(r["pred_path"], "低开高走")
        self.assertEqual(r["pred_close"], "收涨")
        self.assertEqual(r["correct_count"], 3)

    def test_nested_json_string_with_chinese_labels(self) -> None:
        pred = _make_prediction_nested(pred_open="平开", pred_path="平开震荡",
                                       pred_close="平收", use_json_string=True)
        r = compare_prediction_vs_actual(
            pred,
            _make_actual_premapped(actual_open_type="平开", actual_path="平开震荡",
                                   actual_close_type="平收"),
        )
        self.assertEqual(r["pred_open"], "平开")
        self.assertEqual(r["correct_count"], 3)

    def test_nested_tendency_keys_mapped_correctly(self) -> None:
        pred = _make_prediction_nested_tendency(open_tendency="gap_down_bias",
                                                close_tendency="close_weak")
        r = compare_prediction_vs_actual(
            pred,
            _make_actual_premapped(actual_open_type="低开", actual_path="低开低走",
                                   actual_close_type="收跌"),
        )
        self.assertEqual(r["pred_open"], "低开")
        self.assertEqual(r["pred_close"], "收跌")
        self.assertEqual(r["pred_path"], "低开低走")
        self.assertEqual(r["correct_count"], 3)

    def test_top_level_wins_over_nested(self) -> None:
        pred = _make_prediction_nested(pred_open="低开", pred_path="低开低走",
                                       pred_close="收跌")
        pred["pred_open"] = "高开"  # top-level overrides nested
        r = compare_prediction_vs_actual(pred, _make_actual_premapped(actual_open_type="高开"))
        self.assertEqual(r["pred_open"], "高开")
        self.assertTrue(r["open_correct"])


# ─────────────────────────────────────────────────────────────────────────────
# Scoring rule: overall_score = correct_count / 3 always
# ─────────────────────────────────────────────────────────────────────────────

class ScoringRuleTests(unittest.TestCase):

    def test_total_count_always_3_even_with_none_flags(self) -> None:
        # pred_open is None → open_correct is None, but total_count stays 3
        pred = _make_prediction_premapped(pred_path="高开高走", pred_close="收涨")
        pred.pop("pred_open", None)
        r = compare_prediction_vs_actual(
            pred,
            _make_actual_premapped(actual_path="高开高走", actual_close_type="收涨"),
        )
        self.assertIsNone(r["open_correct"])
        self.assertEqual(r["total_count"], 3)
        self.assertEqual(r["correct_count"], 2)
        self.assertAlmostEqual(r["overall_score"], 2 / 3)

    def test_overall_score_always_divides_by_3_not_total(self) -> None:
        # 1 out of 3 correct — score must be 1/3, not 1/1
        r = compare_prediction_vs_actual(
            _make_prediction_premapped(pred_open="高开", pred_path="高开低走",
                                       pred_close="收跌"),
            _make_actual_premapped(actual_open_type="高开", actual_path="低开低走",
                                   actual_close_type="收涨"),
        )
        self.assertAlmostEqual(r["overall_score"], 1 / 3)
        self.assertEqual(r["total_count"], 3)


# ─────────────────────────────────────────────────────────────────────────────
# Output schema
# ─────────────────────────────────────────────────────────────────────────────

class OutputSchemaTests(unittest.TestCase):

    def _result(self) -> dict:
        return compare_prediction_vs_actual(
            _make_prediction_raw(), _make_actual_premapped()
        )

    def test_required_spec_keys_present(self) -> None:
        r = self._result()
        required = {
            "symbol", "prediction_for_date",
            "pred_open", "pred_path", "pred_close",
            "actual_open_type", "actual_path", "actual_close_type",
            "open_correct", "path_correct", "close_correct",
            "correct_count", "total_count", "overall_score",
        }
        self.assertTrue(required.issubset(r.keys()))

    def test_diagnostic_key_present(self) -> None:
        self.assertIn("_missing_fields", self._result())

    def test_metadata_keys_present(self) -> None:
        r = self._result()
        for key in ("final_bias", "final_confidence", "direction_match",
                    "error_category", "summary"):
            self.assertIn(key, r)

    def test_summary_contains_score_percentage(self) -> None:
        r = compare_prediction_vs_actual(
            _make_prediction_premapped(pred_open="高开", pred_path="高开高走",
                                       pred_close="收涨"),
            _make_actual_premapped(),
        )
        self.assertIn("100%", r["summary"])

    def test_summary_contains_bias(self) -> None:
        r = compare_prediction_vs_actual(
            _make_prediction_raw(bias="bearish"),
            _make_actual_premapped(direction_correct=0, close_change=0.02),
        )
        self.assertIn("BEARISH", r["summary"])


# ─────────────────────────────────────────────────────────────────────────────
# Actual input shapes
# ─────────────────────────────────────────────────────────────────────────────

class ActualInputShapeTests(unittest.TestCase):

    def test_premapped_actual_open_type_key(self) -> None:
        r = compare_prediction_vs_actual(
            _make_prediction_raw(),
            _make_actual_premapped(actual_open_type="低开"),
        )
        self.assertEqual(r["actual_open_type"], "低开")

    def test_open_label_key_accepted(self) -> None:
        actual = {"open_label": "低开", "path_label": "低开低走", "close_label": "收跌",
                  "actual_close_change": -0.02, "direction_correct": 0}
        r = compare_prediction_vs_actual(_make_prediction_raw(), actual)
        self.assertEqual(r["actual_open_type"], "低开")

    def test_ohlcv_derived(self) -> None:
        actual = {"actual_prev_close": 170.0, "actual_open": 168.0, "actual_close": 167.0,
                  "actual_close_change": -0.018, "direction_correct": 0}
        r = compare_prediction_vs_actual(_make_prediction_raw(), actual)
        self.assertEqual(r["actual_open_type"], "低开")
        self.assertEqual(r["actual_close_type"], "收跌")

    def test_premapped_wins_over_open_label(self) -> None:
        actual = {"actual_open_type": "平开", "open_label": "高开",
                  "actual_path": "平开震荡", "actual_close_type": "平收"}
        r = compare_prediction_vs_actual(_make_prediction_raw(), actual)
        self.assertEqual(r["actual_open_type"], "平开")


# ─────────────────────────────────────────────────────────────────────────────
# Direction + error category
# ─────────────────────────────────────────────────────────────────────────────

class DirectionAndCategoryTests(unittest.TestCase):

    def test_error_category_correct(self) -> None:
        r = compare_prediction_vs_actual(
            _make_prediction_raw(bias="bullish"),
            _make_actual_premapped(direction_correct=1, close_change=0.015),
        )
        self.assertEqual(r["error_category"], "correct")

    def test_error_category_wrong_direction(self) -> None:
        r = compare_prediction_vs_actual(
            _make_prediction_raw(bias="bullish"),
            _make_actual_premapped(direction_correct=0, close_change=-0.015),
        )
        self.assertEqual(r["error_category"], "wrong_direction")

    def test_direction_derived_from_close_change(self) -> None:
        actual = {"actual_close_change": 0.02}
        r = compare_prediction_vs_actual(_make_prediction_raw(bias="bullish"), actual)
        self.assertEqual(r["direction_match"], 1)


if __name__ == "__main__":
    unittest.main()
