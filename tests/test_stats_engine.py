"""Tests for services/stats_engine.py"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.stats_engine import compute_match_stats, distribution_by_label


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


if __name__ == "__main__":
    unittest.main()
