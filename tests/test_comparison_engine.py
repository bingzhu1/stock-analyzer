"""Tests for services/comparison_engine.py"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.comparison_engine import compare_field, is_categorical_field


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_aligned(avgo_close, nvda_close, n: int = 10) -> pd.DataFrame:
    dates = pd.date_range("2023-01-01", periods=n, freq="B")
    return pd.DataFrame({
        "Date":       [d.strftime("%Y-%m-%d") for d in dates],
        "AVGO_Close": avgo_close,
        "NVDA_Close": nvda_close,
    })


def _same_direction_df(n: int = 10) -> pd.DataFrame:
    """Both symbols move up every day."""
    base_a = [100.0 + i * 1.0 for i in range(n)]
    base_b = [200.0 + i * 2.0 for i in range(n)]
    return _make_aligned(base_a, base_b, n)


def _opposite_direction_df(n: int = 10) -> pd.DataFrame:
    """AVGO up, NVDA down every day."""
    base_a = [100.0 + i * 1.0 for i in range(n)]
    base_b = [200.0 - i * 2.0 for i in range(n)]
    return _make_aligned(base_a, base_b, n)


# ── is_categorical_field ──────────────────────────────────────────────────────

class IsCategoricalFieldTests(unittest.TestCase):

    def test_poslabel_is_categorical(self) -> None:
        self.assertTrue(is_categorical_field("PosLabel"))

    def test_stagelabel_is_categorical(self) -> None:
        self.assertTrue(is_categorical_field("StageLabel"))

    def test_code_is_categorical(self) -> None:
        self.assertTrue(is_categorical_field("Code"))

    def test_close_is_not_categorical(self) -> None:
        self.assertFalse(is_categorical_field("Close"))

    def test_pos30_is_not_categorical(self) -> None:
        self.assertFalse(is_categorical_field("Pos30"))


# ── numeric field comparison ──────────────────────────────────────────────────

class NumericComparisonTests(unittest.TestCase):

    def test_returns_required_columns(self) -> None:
        aligned = _same_direction_df()
        result = compare_field(aligned, "Close", "AVGO", "NVDA")
        for col in ("Date", "AVGO_Close", "NVDA_Close", "dir_AVGO", "dir_NVDA", "match"):
            self.assertIn(col, result.columns)

    def test_same_direction_produces_matches(self) -> None:
        aligned = _same_direction_df(10)
        result = compare_field(aligned, "Close", "AVGO", "NVDA")
        # First row has NaN pct_change → "—" direction → no match
        # Remaining 9 rows should all be "up" for both → match=True
        self.assertTrue(result["match"].iloc[1:].all())

    def test_opposite_direction_produces_mismatches(self) -> None:
        aligned = _opposite_direction_df(10)
        result = compare_field(aligned, "Close", "AVGO", "NVDA")
        # Skip first row (NaN pct_change)
        self.assertFalse(result["match"].iloc[1:].any())

    def test_first_row_direction_is_dash(self) -> None:
        aligned = _same_direction_df(5)
        result = compare_field(aligned, "Close", "AVGO", "NVDA")
        self.assertEqual(result["dir_AVGO"].iloc[0], "—")
        self.assertEqual(result["dir_NVDA"].iloc[0], "—")

    def test_missing_column_raises_value_error(self) -> None:
        aligned = _same_direction_df(5)
        with self.assertRaises(ValueError):
            compare_field(aligned, "Volume", "AVGO", "NVDA")  # Volume column absent


# ── categorical field comparison ──────────────────────────────────────────────

class CategoricalComparisonTests(unittest.TestCase):

    def _make_cat_aligned(self, labels_a, labels_b) -> pd.DataFrame:
        n = len(labels_a)
        dates = pd.date_range("2023-01-01", periods=n, freq="B")
        return pd.DataFrame({
            "Date":            [d.strftime("%Y-%m-%d") for d in dates],
            "AVGO_PosLabel":   labels_a,
            "NVDA_PosLabel":   labels_b,
        })

    def test_equal_labels_match(self) -> None:
        aligned = self._make_cat_aligned(["低位"] * 5, ["低位"] * 5)
        result = compare_field(aligned, "PosLabel", "AVGO", "NVDA")
        self.assertTrue(result["match"].all())

    def test_different_labels_no_match(self) -> None:
        aligned = self._make_cat_aligned(["低位"] * 5, ["高位"] * 5)
        result = compare_field(aligned, "PosLabel", "AVGO", "NVDA")
        self.assertFalse(result["match"].any())

    def test_categorical_result_has_no_direction_columns(self) -> None:
        aligned = self._make_cat_aligned(["中位"] * 3, ["中位"] * 3)
        result = compare_field(aligned, "PosLabel", "AVGO", "NVDA")
        self.assertNotIn("dir_AVGO", result.columns)
        self.assertNotIn("dir_NVDA", result.columns)


if __name__ == "__main__":
    unittest.main()
