# -*- coding: utf-8 -*-
"""
tests/test_review_classifier.py

Unit tests for services/review_classifier.py.
All tests use synthetic dicts — no DB, no network.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.review_classifier import build_review_summary, classify_review_errors


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

def _comparison(
    *,
    symbol: str = "AVGO",
    prediction_for_date: str = "2026-04-21",
    bias: str = "bullish",
    confidence: str = "medium",
    direction_match: int | None = 1,
    pred_open: str | None = "高开",
    actual_open_type: str | None = "高开",
    open_correct: bool | None = True,
    pred_path: str | None = "高开高走",
    actual_path: str | None = "高开高走",
    path_correct: bool | None = True,
    pred_close: str | None = "收涨",
    actual_close_type: str | None = "收涨",
    close_correct: bool | None = True,
    correct_count: int = 3,
    total_count: int = 3,
    overall_score: float = 1.0,
    error_category: str = "correct",
) -> dict:
    return {
        "symbol": symbol,
        "prediction_for_date": prediction_for_date,
        "final_bias": bias,
        "final_confidence": confidence,
        "direction_match": direction_match,
        "pred_open": pred_open,
        "actual_open_type": actual_open_type,
        "open_correct": open_correct,
        "pred_path": pred_path,
        "actual_path": actual_path,
        "path_correct": path_correct,
        "pred_close": pred_close,
        "actual_close_type": actual_close_type,
        "close_correct": close_correct,
        "correct_count": correct_count,
        "total_count": total_count,
        "overall_score": overall_score,
        "error_category": error_category,
    }


def _all_correct() -> dict:
    return _comparison()


def _all_wrong() -> dict:
    return _comparison(
        direction_match=0,
        actual_open_type="低开", open_correct=False,
        actual_path="低开低走", path_correct=False,
        actual_close_type="收跌", close_correct=False,
        correct_count=0, overall_score=0.0,
        error_category="wrong_direction",
    )


def _partial(correct_count: int = 1) -> dict:
    return _comparison(
        direction_match=0,
        open_correct=True,
        actual_path="低开低走", path_correct=False,
        actual_close_type="收跌", close_correct=False,
        correct_count=correct_count,
        overall_score=correct_count / 3,
        error_category="wrong_direction",
    )


def _with_unclear() -> dict:
    return _comparison(
        pred_open=None, actual_open_type="高开", open_correct=None,
        correct_count=2, overall_score=2 / 3,
        error_category="correct",
    )


# ─────────────────────────────────────────────────────────────────────────────
# classify_review_errors — output schema
# ─────────────────────────────────────────────────────────────────────────────

class ClassifyOutputSchemaTests(unittest.TestCase):

    def _classify(self, comp: dict | None = None) -> dict:
        return classify_review_errors(comp or _all_correct())

    def test_required_keys_present(self) -> None:
        r = self._classify()
        for key in ("error_category", "error_dimensions", "correct_dimensions",
                    "unclear_dimensions", "dimension_detail",
                    "overall_score", "correct_count", "total_count"):
            self.assertIn(key, r)

    def test_dimension_detail_has_three_dims(self) -> None:
        r = self._classify()
        self.assertIn("open", r["dimension_detail"])
        self.assertIn("path", r["dimension_detail"])
        self.assertIn("close", r["dimension_detail"])

    def test_dimension_detail_has_predicted_actual_correct_keys(self) -> None:
        d = self._classify()["dimension_detail"]["open"]
        self.assertIn("predicted", d)
        self.assertIn("actual", d)
        self.assertIn("correct", d)

    def test_overall_score_is_float(self) -> None:
        self.assertIsInstance(self._classify()["overall_score"], float)

    def test_correct_count_is_int(self) -> None:
        self.assertIsInstance(self._classify()["correct_count"], int)

    def test_total_count_is_int(self) -> None:
        self.assertIsInstance(self._classify()["total_count"], int)


# ─────────────────────────────────────────────────────────────────────────────
# classify_review_errors — dimension bucketing
# ─────────────────────────────────────────────────────────────────────────────

class ClassifyDimensionBucketingTests(unittest.TestCase):

    def test_all_correct_dims(self) -> None:
        r = classify_review_errors(_all_correct())
        self.assertEqual(sorted(r["correct_dimensions"]), ["close", "open", "path"])
        self.assertEqual(r["error_dimensions"], [])
        self.assertEqual(r["unclear_dimensions"], [])

    def test_all_wrong_dims(self) -> None:
        r = classify_review_errors(_all_wrong())
        self.assertEqual(sorted(r["error_dimensions"]), ["close", "open", "path"])
        self.assertEqual(r["correct_dimensions"], [])
        self.assertEqual(r["unclear_dimensions"], [])

    def test_partial_correct_dims(self) -> None:
        r = classify_review_errors(_partial())
        self.assertIn("open", r["correct_dimensions"])
        self.assertIn("path", r["error_dimensions"])
        self.assertIn("close", r["error_dimensions"])

    def test_unclear_dim_when_flag_is_none(self) -> None:
        r = classify_review_errors(_with_unclear())
        self.assertIn("open", r["unclear_dimensions"])
        self.assertNotIn("open", r["error_dimensions"])
        self.assertNotIn("open", r["correct_dimensions"])

    def test_mixed_all_three_buckets(self) -> None:
        comp = _comparison(
            open_correct=True,
            path_correct=False,
            close_correct=None,
            correct_count=1, overall_score=1 / 3,
        )
        r = classify_review_errors(comp)
        self.assertIn("open", r["correct_dimensions"])
        self.assertIn("path", r["error_dimensions"])
        self.assertIn("close", r["unclear_dimensions"])


# ─────────────────────────────────────────────────────────────────────────────
# classify_review_errors — score passthrough
# ─────────────────────────────────────────────────────────────────────────────

class ClassifyScorePassthroughTests(unittest.TestCase):

    def test_perfect_score_passed_through(self) -> None:
        r = classify_review_errors(_all_correct())
        self.assertAlmostEqual(r["overall_score"], 1.0)
        self.assertEqual(r["correct_count"], 3)
        self.assertEqual(r["total_count"], 3)

    def test_zero_score_passed_through(self) -> None:
        r = classify_review_errors(_all_wrong())
        self.assertAlmostEqual(r["overall_score"], 0.0)
        self.assertEqual(r["correct_count"], 0)

    def test_partial_score_passed_through(self) -> None:
        r = classify_review_errors(_partial(correct_count=1))
        self.assertAlmostEqual(r["overall_score"], 1 / 3)
        self.assertEqual(r["correct_count"], 1)


# ─────────────────────────────────────────────────────────────────────────────
# classify_review_errors — error category
# ─────────────────────────────────────────────────────────────────────────────

class ClassifyErrorCategoryTests(unittest.TestCase):

    def test_correct_category(self) -> None:
        r = classify_review_errors(_all_correct())
        self.assertEqual(r["error_category"], "correct")

    def test_wrong_direction_category(self) -> None:
        r = classify_review_errors(_all_wrong())
        self.assertEqual(r["error_category"], "wrong_direction")

    def test_unknown_category_normalized_to_insufficient_data(self) -> None:
        comp = _comparison(error_category="totally-invalid-value")
        r = classify_review_errors(comp)
        self.assertEqual(r["error_category"], "insufficient_data")

    def test_empty_category_normalized(self) -> None:
        comp = _comparison(error_category="")
        r = classify_review_errors(comp)
        self.assertEqual(r["error_category"], "insufficient_data")


# ─────────────────────────────────────────────────────────────────────────────
# classify_review_errors — dimension_detail values
# ─────────────────────────────────────────────────────────────────────────────

class ClassifyDimensionDetailTests(unittest.TestCase):

    def test_predicted_values_present(self) -> None:
        r = classify_review_errors(_all_correct())
        self.assertEqual(r["dimension_detail"]["open"]["predicted"], "高开")
        self.assertEqual(r["dimension_detail"]["path"]["predicted"], "高开高走")
        self.assertEqual(r["dimension_detail"]["close"]["predicted"], "收涨")

    def test_actual_values_present(self) -> None:
        r = classify_review_errors(_all_wrong())
        self.assertEqual(r["dimension_detail"]["open"]["actual"], "低开")
        self.assertEqual(r["dimension_detail"]["path"]["actual"], "低开低走")
        self.assertEqual(r["dimension_detail"]["close"]["actual"], "收跌")

    def test_correct_flags_in_detail(self) -> None:
        r = classify_review_errors(_all_correct())
        self.assertTrue(r["dimension_detail"]["open"]["correct"])
        self.assertTrue(r["dimension_detail"]["path"]["correct"])
        self.assertTrue(r["dimension_detail"]["close"]["correct"])

    def test_none_predicted_preserved_in_detail(self) -> None:
        r = classify_review_errors(_with_unclear())
        self.assertIsNone(r["dimension_detail"]["open"]["predicted"])
        self.assertIsNone(r["dimension_detail"]["open"]["correct"])


# ─────────────────────────────────────────────────────────────────────────────
# classify_review_errors — edge cases
# ─────────────────────────────────────────────────────────────────────────────

class ClassifyEdgeCaseTests(unittest.TestCase):

    def test_empty_comparison_does_not_crash(self) -> None:
        r = classify_review_errors({})
        self.assertIsNotNone(r)
        self.assertEqual(r["correct_count"], 0)

    def test_all_none_flags_go_to_unclear(self) -> None:
        comp = _comparison(open_correct=None, path_correct=None, close_correct=None,
                           correct_count=0, overall_score=0.0)
        r = classify_review_errors(comp)
        self.assertEqual(sorted(r["unclear_dimensions"]), ["close", "open", "path"])
        self.assertEqual(r["error_dimensions"], [])
        self.assertEqual(r["correct_dimensions"], [])


# ─────────────────────────────────────────────────────────────────────────────
# build_review_summary — output
# ─────────────────────────────────────────────────────────────────────────────

class BuildReviewSummaryTests(unittest.TestCase):

    def _summary(self, comp: dict | None = None,
                 error_info: dict | None = None) -> str:
        c = comp or _all_correct()
        e = error_info or classify_review_errors(c)
        return build_review_summary(c, e)

    def test_returns_nonempty_string(self) -> None:
        self.assertIsInstance(self._summary(), str)
        self.assertGreater(len(self._summary()), 0)

    def test_contains_symbol(self) -> None:
        self.assertIn("AVGO", self._summary())

    def test_contains_prediction_date(self) -> None:
        self.assertIn("2026-04-21", self._summary())

    def test_contains_bias_uppercase(self) -> None:
        self.assertIn("BULLISH", self._summary())

    def test_contains_score_fraction(self) -> None:
        self.assertIn("3/3", self._summary())

    def test_all_wrong_shows_0_score(self) -> None:
        comp = _all_wrong()
        s = build_review_summary(comp, classify_review_errors(comp))
        self.assertIn("0/3", s)

    def test_partial_shows_1_score(self) -> None:
        comp = _partial()
        s = build_review_summary(comp, classify_review_errors(comp))
        self.assertIn("1/3", s)

    def test_contains_error_category_label(self) -> None:
        comp = _all_correct()
        s = build_review_summary(comp, classify_review_errors(comp))
        self.assertIn("correct", s)

    def test_wrong_direction_label_in_summary(self) -> None:
        comp = _all_wrong()
        s = build_review_summary(comp, classify_review_errors(comp))
        self.assertIn("wrong_direction", s)

    def test_contains_dimension_lines(self) -> None:
        s = self._summary()
        self.assertIn("开盘", s)
        self.assertIn("路径", s)
        self.assertIn("收盘", s)

    def test_correct_dimension_marked_with_checkmark(self) -> None:
        s = self._summary(_all_correct())
        self.assertIn("✓", s)

    def test_wrong_dimension_marked_with_cross(self) -> None:
        comp = _all_wrong()
        s = build_review_summary(comp, classify_review_errors(comp))
        self.assertIn("✗", s)

    def test_unclear_dimension_marked_with_question(self) -> None:
        comp = _with_unclear()
        s = build_review_summary(comp, classify_review_errors(comp))
        self.assertIn("?", s)

    def test_direction_correct_label(self) -> None:
        s = self._summary()
        self.assertIn("方向正确", s)

    def test_direction_wrong_label(self) -> None:
        comp = _all_wrong()
        s = build_review_summary(comp, classify_review_errors(comp))
        self.assertIn("方向错误", s)

    def test_error_dimensions_reported_via_primary_error(self) -> None:
        comp = _all_wrong()
        s = build_review_summary(comp, classify_review_errors(comp))
        # error dimensions are now surfaced through 主要问题 + reason_guesses
        self.assertIn("主要问题", s)

    def test_correct_dimensions_reported_in_summary(self) -> None:
        comp = _partial()
        s = build_review_summary(comp, classify_review_errors(comp))
        self.assertIn("正确维度", s)

    def test_empty_inputs_do_not_crash(self) -> None:
        s = build_review_summary({}, classify_review_errors({}))
        self.assertIsInstance(s, str)


# ─────────────────────────────────────────────────────────────────────────────
# classify_review_errors — error_types (spec field)
# ─────────────────────────────────────────────────────────────────────────────

class ErrorTypesTests(unittest.TestCase):

    def test_all_wrong_gives_three_error_types(self) -> None:
        r = classify_review_errors(_all_wrong())
        self.assertEqual(r["error_types"], ["开盘判断错误", "路径判断错误", "收盘判断错误"])

    def test_all_correct_gives_empty_error_types(self) -> None:
        r = classify_review_errors(_all_correct())
        self.assertEqual(r["error_types"], [])

    def test_partial_wrong_gives_subset(self) -> None:
        comp = _comparison(open_correct=True, path_correct=False, close_correct=False,
                           correct_count=1, overall_score=1/3,
                           error_category="wrong_direction")
        r = classify_review_errors(comp)
        self.assertNotIn("开盘判断错误", r["error_types"])
        self.assertIn("路径判断错误", r["error_types"])
        self.assertIn("收盘判断错误", r["error_types"])

    def test_unclear_dims_not_in_error_types(self) -> None:
        r = classify_review_errors(_with_unclear())
        # open is unclear, not wrong → must not appear in error_types
        self.assertNotIn("开盘判断错误", r["error_types"])

    def test_error_types_is_list_of_strings(self) -> None:
        r = classify_review_errors(_all_wrong())
        self.assertIsInstance(r["error_types"], list)
        for item in r["error_types"]:
            self.assertIsInstance(item, str)


# ─────────────────────────────────────────────────────────────────────────────
# classify_review_errors — primary_error (spec field)
# ─────────────────────────────────────────────────────────────────────────────

class PrimaryErrorTests(unittest.TestCase):

    def test_all_wrong_primary_is_path(self) -> None:
        # path takes priority when all three are wrong (spec example)
        r = classify_review_errors(_all_wrong())
        self.assertEqual(r["primary_error"], "路径判断错误")

    def test_all_correct_primary_is_none(self) -> None:
        r = classify_review_errors(_all_correct())
        self.assertIsNone(r["primary_error"])

    def test_only_open_wrong_primary_is_open(self) -> None:
        comp = _comparison(open_correct=False, path_correct=True, close_correct=True,
                           correct_count=2, overall_score=2/3,
                           error_category="wrong_direction")
        r = classify_review_errors(comp)
        self.assertEqual(r["primary_error"], "开盘判断错误")

    def test_path_and_close_wrong_primary_is_path(self) -> None:
        comp = _comparison(open_correct=True, path_correct=False, close_correct=False,
                           correct_count=1, overall_score=1/3,
                           error_category="wrong_direction")
        r = classify_review_errors(comp)
        self.assertEqual(r["primary_error"], "路径判断错误")

    def test_open_before_close_in_priority(self) -> None:
        # open wrong + close wrong, path correct → open wins over close (spec priority)
        comp = _comparison(open_correct=False, path_correct=True, close_correct=False,
                           correct_count=1, overall_score=1/3,
                           error_category="wrong_direction")
        r = classify_review_errors(comp)
        self.assertEqual(r["primary_error"], "开盘判断错误")

    def test_only_close_wrong_primary_is_close(self) -> None:
        comp = _comparison(open_correct=True, path_correct=True, close_correct=False,
                           correct_count=2, overall_score=2/3,
                           error_category="wrong_direction")
        r = classify_review_errors(comp)
        self.assertEqual(r["primary_error"], "收盘判断错误")

    def test_all_unclear_primary_is_none(self) -> None:
        comp = _comparison(open_correct=None, path_correct=None, close_correct=None,
                           correct_count=0, overall_score=0.0)
        r = classify_review_errors(comp)
        self.assertIsNone(r["primary_error"])


# ─────────────────────────────────────────────────────────────────────────────
# classify_review_errors — reason_guesses (spec field)
# ─────────────────────────────────────────────────────────────────────────────

class ReasonGuessesTests(unittest.TestCase):

    def test_all_wrong_gives_three_reasons(self) -> None:
        r = classify_review_errors(_all_wrong())
        self.assertEqual(len(r["reason_guesses"]), 3)
        self.assertIn("预测开盘方向与实际不一致", r["reason_guesses"])
        self.assertIn("预测路径与实际结构不一致", r["reason_guesses"])
        self.assertIn("预测收盘方向与实际不一致", r["reason_guesses"])

    def test_all_correct_gives_empty_reasons(self) -> None:
        r = classify_review_errors(_all_correct())
        self.assertEqual(r["reason_guesses"], [])

    def test_unclear_dims_get_unclear_reason(self) -> None:
        r = classify_review_errors(_with_unclear())
        # open is unclear → its reason should mention 信号不明确
        unclear_reasons = [g for g in r["reason_guesses"] if "不明确" in g]
        self.assertTrue(len(unclear_reasons) >= 1)

    def test_wrong_reasons_listed_before_unclear_reasons(self) -> None:
        comp = _comparison(open_correct=False, path_correct=None, close_correct=True,
                           correct_count=1, overall_score=1/3)
        r = classify_review_errors(comp)
        reasons = r["reason_guesses"]
        wrong_idx = next((i for i, g in enumerate(reasons) if "不一致" in g), -1)
        unclear_idx = next((i for i, g in enumerate(reasons) if "不明确" in g), -1)
        if wrong_idx >= 0 and unclear_idx >= 0:
            self.assertLess(wrong_idx, unclear_idx)

    def test_reason_guesses_is_list_of_strings(self) -> None:
        r = classify_review_errors(_all_wrong())
        self.assertIsInstance(r["reason_guesses"], list)
        for item in r["reason_guesses"]:
            self.assertIsInstance(item, str)


# ─────────────────────────────────────────────────────────────────────────────
# build_review_summary — primary_error and reason_guesses in output
# ─────────────────────────────────────────────────────────────────────────────

class SummaryPrimaryErrorTests(unittest.TestCase):

    def test_primary_error_in_summary_when_wrong(self) -> None:
        comp = _all_wrong()
        s = build_review_summary(comp, classify_review_errors(comp))
        self.assertIn("路径判断错误", s)

    def test_reason_guesses_in_summary(self) -> None:
        comp = _all_wrong()
        s = build_review_summary(comp, classify_review_errors(comp))
        self.assertIn("预测路径与实际结构不一致", s)

    def test_primary_error_absent_when_all_correct(self) -> None:
        comp = _all_correct()
        s = build_review_summary(comp, classify_review_errors(comp))
        self.assertNotIn("主要问题", s)

    def test_unclear_reason_in_summary(self) -> None:
        comp = _with_unclear()
        s = build_review_summary(comp, classify_review_errors(comp))
        self.assertIn("不明确", s)


if __name__ == "__main__":
    unittest.main()
