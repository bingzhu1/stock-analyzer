"""Tests for services/stats_engine.py"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.stats_engine import compute_match_stats, distribution_by_label, position_distribution


# ── helpers ───────────────────────────────────────────────────────────────────

def _df(matches: list[bool], labels: list[str] | None = None) -> pd.DataFrame:
    d = {"match": matches}
    if labels is not None:
        d["label"] = labels
    return pd.DataFrame(d)


# ── compute_match_stats ───────────────────────────────────────────────────────

class ComputeMatchStatsTests(unittest.TestCase):

    def test_all_matched(self) -> None:
        stats = compute_match_stats(_df([True, True, True]))
        self.assertEqual(stats["total"],      3)
        self.assertEqual(stats["matched"],    3)
        self.assertEqual(stats["mismatched"], 0)
        self.assertAlmostEqual(stats["match_rate"], 100.0)

    def test_none_matched(self) -> None:
        stats = compute_match_stats(_df([False, False, False]))
        self.assertEqual(stats["matched"],    0)
        self.assertEqual(stats["mismatched"], 3)
        self.assertAlmostEqual(stats["match_rate"], 0.0)

    def test_partial_match_rate(self) -> None:
        stats = compute_match_stats(_df([True, False, True, False]))
        self.assertAlmostEqual(stats["match_rate"], 50.0)

    def test_empty_df_returns_zeros(self) -> None:
        stats = compute_match_stats(pd.DataFrame())
        self.assertEqual(stats["total"],      0)
        self.assertEqual(stats["matched"],    0)
        self.assertEqual(stats["mismatched"], 0)
        self.assertAlmostEqual(stats["match_rate"], 0.0)

    def test_missing_match_column_returns_zeros(self) -> None:
        df = pd.DataFrame({"other": [1, 2, 3]})
        stats = compute_match_stats(df)
        self.assertEqual(stats["total"], 0)

    def test_match_rate_rounded_to_one_dp(self) -> None:
        # 1 match out of 3 = 33.3%
        stats = compute_match_stats(_df([True, False, False]))
        self.assertEqual(stats["match_rate"], round(1 / 3 * 100, 1))

    def test_result_keys_present(self) -> None:
        stats = compute_match_stats(_df([True]))
        for key in ("total", "matched", "mismatched", "match_rate"):
            self.assertIn(key, stats)


# ── distribution_by_label ─────────────────────────────────────────────────────

class DistributionByLabelTests(unittest.TestCase):

    def test_by_label_groups_correctly(self) -> None:
        df = _df(
            [True, True, False, False, True],
            labels=["低位", "低位", "高位", "高位", "中位"],
        )
        result = distribution_by_label(df, "label")
        self.assertIn("低位", result)
        self.assertEqual(result["低位"]["matched"], 2)
        self.assertEqual(result["高位"]["matched"], 0)
        self.assertEqual(result["中位"]["matched"], 1)

    def test_missing_label_col_returns_empty_dict(self) -> None:
        df = _df([True, False])
        result = distribution_by_label(df, "nonexistent_col")
        self.assertEqual(result, {})

    def test_missing_match_col_returns_empty_dict(self) -> None:
        df = pd.DataFrame({"label": ["a", "b"]})
        result = distribution_by_label(df, "label")
        self.assertEqual(result, {})


# ── position_distribution ─────────────────────────────────────────────────────

class PositionDistributionTests(unittest.TestCase):

    def _make_data(
        self,
        dates: list[str],
        matches: list[bool],
        pos_labels: list[str] | None = None,
        pos30: list[int | float] | None = None,
        symbol: str = "AVGO",
    ):
        comp = pd.DataFrame({"Date": dates, "match": matches})
        aligned_data: dict = {"Date": dates}
        if pos_labels is not None:
            aligned_data[f"{symbol}_PosLabel"] = pos_labels
        if pos30 is not None:
            aligned_data[f"{symbol}_Pos30"] = pos30
        return comp, pd.DataFrame(aligned_data)

    def test_pos_label_used_when_available(self) -> None:
        dates   = ["2023-01-02", "2023-01-03", "2023-01-04", "2023-01-05"]
        matches = [True,         True,          True,          False]
        labels  = ["高位",       "中位",         "低位",        "高位"]
        comp, aligned = self._make_data(dates, matches, pos_labels=labels)
        result = position_distribution(comp, aligned, "AVGO")
        self.assertEqual(result["label_source"], "PosLabel")
        self.assertEqual(result["高位"], 1)
        self.assertEqual(result["中位"], 1)
        self.assertEqual(result["低位"], 1)
        self.assertEqual(result["total_matched"], 3)

    def test_pos30_fallback_when_no_poslabel(self) -> None:
        dates   = ["2023-01-02", "2023-01-03", "2023-01-04"]
        matches = [True,         True,          True]
        p30     = [70,           50,            20]   # → 高位, 中位, 低位
        comp, aligned = self._make_data(dates, matches, pos30=p30)
        result = position_distribution(comp, aligned, "AVGO")
        self.assertEqual(result["label_source"], "Pos30")
        self.assertEqual(result["高位"], 1)
        self.assertEqual(result["中位"], 1)
        self.assertEqual(result["低位"], 1)
        self.assertEqual(result["total_matched"], 3)

    def test_pos30_boundary_values(self) -> None:
        # 67 → 高位 (boundary), 33 → 低位 (boundary), 34 → 中位, 66 → 中位
        dates   = ["2023-01-02", "2023-01-03", "2023-01-04", "2023-01-05"]
        matches = [True,         True,          True,          True]
        p30     = [67,           33,            34,            66]
        comp, aligned = self._make_data(dates, matches, pos30=p30)
        result = position_distribution(comp, aligned, "AVGO")
        self.assertEqual(result["高位"], 1)
        self.assertEqual(result["低位"], 1)
        self.assertEqual(result["中位"], 2)

    def test_no_position_columns_returns_none_source(self) -> None:
        comp    = pd.DataFrame({"Date": ["2023-01-02"], "match": [True]})
        aligned = pd.DataFrame({"Date": ["2023-01-02"], "AVGO_Close": [100.0]})
        result  = position_distribution(comp, aligned, "AVGO")
        self.assertEqual(result["label_source"], "none")
        self.assertEqual(result["total_matched"], 0)

    def test_invariant_high_plus_mid_plus_low_equals_total(self) -> None:
        dates   = ["2023-01-0" + str(i) for i in range(2, 7)]
        matches = [True, True, True, True, False]
        labels  = ["高位", "高位", "中位", "低位", "高位"]
        comp, aligned = self._make_data(dates, matches, pos_labels=labels)
        result = position_distribution(comp, aligned, "AVGO")
        self.assertEqual(
            result["高位"] + result["中位"] + result["低位"],
            result["total_matched"],
        )

    def test_empty_comparison_df_returns_empty(self) -> None:
        result = position_distribution(pd.DataFrame(), pd.DataFrame(), "AVGO")
        self.assertEqual(result["total_matched"], 0)
        self.assertEqual(result["label_source"], "none")

    def test_no_matched_rows_returns_zero_counts(self) -> None:
        dates   = ["2023-01-02", "2023-01-03"]
        matches = [False, False]
        labels  = ["高位", "中位"]
        comp, aligned = self._make_data(dates, matches, pos_labels=labels)
        result = position_distribution(comp, aligned, "AVGO")
        self.assertEqual(result["高位"], 0)
        self.assertEqual(result["中位"], 0)
        self.assertEqual(result["低位"], 0)
        self.assertEqual(result["total_matched"], 0)

    def test_unmatched_rows_excluded_from_count(self) -> None:
        dates   = ["2023-01-02", "2023-01-03", "2023-01-04"]
        matches = [True,         False,          True]
        labels  = ["高位",       "低位",          "中位"]  # False row has "低位"
        comp, aligned = self._make_data(dates, matches, pos_labels=labels)
        result = position_distribution(comp, aligned, "AVGO")
        self.assertEqual(result["高位"], 1)
        self.assertEqual(result["中位"], 1)
        self.assertEqual(result["低位"], 0)   # "低位" row was unmatched
        self.assertEqual(result["total_matched"], 2)

    def test_result_keys_present(self) -> None:
        dates   = ["2023-01-02"]
        matches = [True]
        labels  = ["高位"]
        comp, aligned = self._make_data(dates, matches, pos_labels=labels)
        result = position_distribution(comp, aligned, "AVGO")
        for key in ("高位", "中位", "低位", "total_matched", "label_source"):
            self.assertIn(key, result)


if __name__ == "__main__":
    unittest.main()
