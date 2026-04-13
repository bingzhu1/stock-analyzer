"""Tests for services/multi_symbol_view.py"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.multi_symbol_view import build_aligned_view


# ── test loader factory ───────────────────────────────────────────────────────

def _make_df(n: int = 40, start: str = "2023-01-01", close_start: float = 100.0) -> pd.DataFrame:
    dates = pd.date_range(start, periods=n, freq="B")
    return pd.DataFrame({
        "Date":   [d.strftime("%Y-%m-%d") for d in dates],
        "Open":   [close_start + i * 0.3 for i in range(n)],
        "High":   [close_start + i * 0.3 + 1.0 for i in range(n)],
        "Low":    [close_start + i * 0.3 - 0.5 for i in range(n)],
        "Close":  [close_start + i * 0.3 + 0.1 for i in range(n)],
        "Volume": [500_000 + i * 1_000 for i in range(n)],
    })


def _make_loader(data_map: dict[str, pd.DataFrame]):
    """Return a loader that serves DataFrames from data_map, ignoring window/fields."""
    def _loader(symbol: str, window: int = 0, fields=None, **_kwargs) -> pd.DataFrame:
        sym = symbol.upper()
        df = data_map[sym].copy()
        if window > 0:
            df = df.tail(window).reset_index(drop=True)
        return df
    return _loader


# ── tests ─────────────────────────────────────────────────────────────────────

class MultiSymbolViewTests(unittest.TestCase):

    def setUp(self) -> None:
        self.avgo = _make_df(40, close_start=100.0)
        self.nvda = _make_df(40, close_start=400.0)

    def _loader(self, symbol: str, window: int = 0, fields=None, **kwargs) -> pd.DataFrame:
        mapping = {"AVGO": self.avgo, "NVDA": self.nvda}
        df = mapping[symbol.upper()].copy()
        if window > 0:
            df = df.tail(window).reset_index(drop=True)
        return df

    def test_empty_symbols_returns_empty_df(self) -> None:
        df = build_aligned_view([], window=10, _loader=self._loader)
        self.assertTrue(df.empty)

    def test_single_symbol_returns_data(self) -> None:
        df = build_aligned_view(["AVGO"], window=10, _loader=self._loader)
        self.assertEqual(len(df), 10)
        self.assertIn("AVGO_Close", df.columns)

    def test_two_symbols_aligned_on_date(self) -> None:
        df = build_aligned_view(["AVGO", "NVDA"], window=10, _loader=self._loader)
        self.assertIn("AVGO_Close", df.columns)
        self.assertIn("NVDA_Close", df.columns)

    def test_date_column_not_prefixed(self) -> None:
        df = build_aligned_view(["AVGO", "NVDA"], window=5, _loader=self._loader)
        self.assertIn("Date", df.columns)
        self.assertNotIn("AVGO_Date", df.columns)
        self.assertNotIn("NVDA_Date", df.columns)

    def test_window_limits_rows(self) -> None:
        df = build_aligned_view(["AVGO", "NVDA"], window=15, _loader=self._loader)
        self.assertEqual(len(df), 15)

    def test_duplicate_symbols_deduplicated(self) -> None:
        df = build_aligned_view(["AVGO", "AVGO"], window=5, _loader=self._loader)
        # Deduplication means only one set of AVGO columns
        avgo_cols = [c for c in df.columns if c.startswith("AVGO_")]
        close_cols = [c for c in avgo_cols if "Close" in c]
        self.assertEqual(len(close_cols), 1)

    def test_inner_join_drops_non_overlapping_dates(self) -> None:
        avgo_short = _make_df(20, start="2023-01-01")
        nvda_late  = _make_df(20, start="2023-02-15")  # different start

        loader = _make_loader({"AVGO": avgo_short, "NVDA": nvda_late})
        df = build_aligned_view(["AVGO", "NVDA"], window=0, _loader=loader)
        # Only overlapping dates should remain
        avgo_dates = set(avgo_short["Date"])
        nvda_dates = set(nvda_late["Date"])
        expected_overlap = avgo_dates & nvda_dates
        self.assertEqual(len(df), len(expected_overlap))


if __name__ == "__main__":
    unittest.main()
