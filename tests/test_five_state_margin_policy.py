"""Tests for services/five_state_margin_policy.py."""

import copy
import unittest

from services.five_state_margin_policy import apply_five_state_margin_policy


class LowMarginTests(unittest.TestCase):
    def test_zhen_dang_045_vs_xiao_zhang_042_is_low_margin(self) -> None:
        result = apply_five_state_margin_policy({
            "大涨": 0.05,
            "小涨": 0.42,
            "震荡": 0.45,
            "小跌": 0.04,
            "大跌": 0.04,
        })
        self.assertEqual(result["margin_band"], "low_margin")
        self.assertEqual(result["primary_state"], "震荡")
        self.assertEqual(result["secondary_state"], "小涨")
        self.assertAlmostEqual(result["top1_margin"], 0.03)

    def test_display_state_is_zhen_dang_xiao_zhang_dispute(self) -> None:
        result = apply_five_state_margin_policy({
            "大涨": 0.05,
            "小涨": 0.42,
            "震荡": 0.45,
            "小跌": 0.04,
            "大跌": 0.04,
        })
        self.assertEqual(result["display_state"], "震荡/小涨分歧")

    def test_top2_states_preserved(self) -> None:
        result = apply_five_state_margin_policy({
            "大涨": 0.05,
            "小涨": 0.42,
            "震荡": 0.45,
            "小跌": 0.04,
            "大跌": 0.04,
        })
        self.assertEqual(result["top2_states"], ["震荡", "小涨"])

    def test_bias_duo_with_close_zhen_dang_xiao_zhang_sets_conflict(self) -> None:
        result = apply_five_state_margin_policy(
            {
                "大涨": 0.05,
                "小涨": 0.42,
                "震荡": 0.45,
                "小跌": 0.04,
                "大跌": 0.04,
            },
            final_direction="偏多",
        )
        self.assertTrue(result["state_conflict"])
        self.assertIn("方向偏多但五状态 top1 为震荡", result["policy_note"])


class MarginBandTests(unittest.TestCase):
    def test_margin_007_is_watch_margin(self) -> None:
        result = apply_five_state_margin_policy({
            "大涨": 0.04,
            "小涨": 0.35,
            "震荡": 0.42,
            "小跌": 0.10,
            "大跌": 0.09,
        })
        self.assertEqual(result["margin_band"], "watch_margin")
        self.assertEqual(result["display_state"], "震荡为主，小涨接近")

    def test_margin_012_is_clear_top1(self) -> None:
        result = apply_five_state_margin_policy({
            "大涨": 0.03,
            "小涨": 0.28,
            "震荡": 0.40,
            "小跌": 0.17,
            "大跌": 0.12,
        })
        self.assertEqual(result["margin_band"], "clear_top1")
        self.assertEqual(result["display_state"], "震荡")


class InvalidInputTests(unittest.TestCase):
    def test_malformed_distribution_returns_unknown(self) -> None:
        result = apply_five_state_margin_policy("bad")  # type: ignore[arg-type]
        self.assertEqual(result["margin_band"], "unknown")
        self.assertEqual(result["display_state"], "unknown")
        self.assertFalse(result["state_conflict"])

    def test_missing_state_probabilities_handled_safely(self) -> None:
        result = apply_five_state_margin_policy({
            "大涨": 0.1,
            "小涨": 0.2,
            "震荡": 0.3,
        })
        self.assertEqual(result["margin_band"], "unknown")
        self.assertEqual(result["display_state"], "unknown")
        self.assertIn("缺少", result["policy_note"])


class DeterminismTests(unittest.TestCase):
    def test_tie_handled_deterministically(self) -> None:
        result = apply_five_state_margin_policy({
            "大涨": 0.03,
            "小涨": 0.45,
            "震荡": 0.45,
            "小跌": 0.04,
            "大跌": 0.03,
        })
        self.assertEqual(result["primary_state"], "小涨")
        self.assertEqual(result["secondary_state"], "震荡")
        self.assertEqual(result["margin_band"], "low_margin")

    def test_original_distribution_not_mutated(self) -> None:
        distribution = {
            "大涨": 0.05,
            "小涨": 0.42,
            "震荡": 0.45,
            "小跌": 0.04,
            "大跌": 0.04,
        }
        baseline = copy.deepcopy(distribution)
        apply_five_state_margin_policy(distribution, final_direction="偏多")
        self.assertEqual(distribution, baseline)


class ConflictAndNotesTests(unittest.TestCase):
    def test_clear_top1_agreeing_direction_has_no_conflict(self) -> None:
        result = apply_five_state_margin_policy(
            {
                "大涨": 0.08,
                "小涨": 0.52,
                "震荡": 0.25,
                "小跌": 0.10,
                "大跌": 0.05,
            },
            final_direction="偏多",
        )
        self.assertEqual(result["margin_band"], "clear_top1")
        self.assertFalse(result["state_conflict"])
        self.assertEqual(result["display_state"], "小涨")

    def test_policy_note_is_non_empty(self) -> None:
        result = apply_five_state_margin_policy({
            "大涨": 0.05,
            "小涨": 0.42,
            "震荡": 0.45,
            "小跌": 0.04,
            "大跌": 0.04,
        })
        self.assertTrue(result["policy_note"])
        self.assertIsInstance(result["policy_note"], str)


if __name__ == "__main__":
    unittest.main()
