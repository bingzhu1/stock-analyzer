"""Tests for services/data_query.py"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.data_query import (
    ALL_SUPPORTED_FIELDS,
    SUPPORTED_SYMBOLS,
    load_symbol_data,
)


# ── test DataFrame factory ────────────────────────────────────────────────────

def _make_raw(n: int = 60) -> pd.DataFrame:
    """Minimal coded-CSV-like DataFrame with enough rows for rolling windows."""
    dates = pd.date_range("2023-01-01", periods=n, freq="B")
    base = 100.0
    return pd.DataFrame({
        "Date":       [d.strftime("%Y-%m-%d") for d in dates],
        "Open":       [base + i * 0.5            for i in range(n)],
        "High":       [base + i * 0.5 + 2.0      for i in range(n)],
        "Low":        [base + i * 0.5 - 1.5      for i in range(n)],
        "Close":      [base + i * 0.5 + 0.3      for i in range(n)],
        "Volume":     [1_000_000 + i * 5_000      for i in range(n)],
        "PrevClose":  [base + (i - 1) * 0.5 + 0.3 for i in range(n)],
        "MA20_Volume":[900_000.0                  for _ in range(n)],
        "O_gap":      [0.001                      for _ in range(n)],
        "H_up":       [0.02                       for _ in range(n)],
        "L_down":     [0.015                      for _ in range(n)],
        "C_move":     [0.003                      for _ in range(n)],
        "V_ratio":    [1.1                        for _ in range(n)],
        "O_code":     [3] * n,
        "H_code":     [2] * n,
        "L_code":     [2] * n,
        "C_code":     [3] * n,
        "V_code":     [3] * n,
        "Code":       ["32233"] * n,
    })


def _reader(df: pd.DataFrame):
    """Return a reader callable that always returns ``df``."""
    return lambda _path: df


# ── symbol / file validation ──────────────────────────────────────────────────

class SymbolValidationTests(unittest.TestCase):

    def test_unsupported_symbol_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            load_symbol_data("TSLA", _reader=_reader(_make_raw()))

    def test_symbol_case_insensitive(self) -> None:
        df = load_symbol_data("avgo", window=5, _reader=_reader(_make_raw()))
        self.assertFalse(df.empty)

    def test_supported_symbols_constant(self) -> None:
        self.assertIn("AVGO", SUPPORTED_SYMBOLS)
        self.assertIn("NVDA", SUPPORTED_SYMBOLS)
        self.assertIn("SOXX", SUPPORTED_SYMBOLS)
        self.assertIn("QQQ",  SUPPORTED_SYMBOLS)


# ── window slicing ────────────────────────────────────────────────────────────

class WindowSlicingTests(unittest.TestCase):

    def test_window_limits_rows(self) -> None:
        df = load_symbol_data("AVGO", window=10, _reader=_reader(_make_raw(60)))
        self.assertEqual(len(df), 10)

    def test_window_zero_returns_all_rows(self) -> None:
        raw = _make_raw(60)
        df = load_symbol_data("AVGO", window=0, _reader=_reader(raw))
        self.assertEqual(len(df), 60)

    def test_date_column_always_present(self) -> None:
        df = load_symbol_data("AVGO", window=5, _reader=_reader(_make_raw()))
        self.assertIn("Date", df.columns)

    def test_rows_are_most_recent(self) -> None:
        raw = _make_raw(60)
        df = load_symbol_data("AVGO", window=5, _reader=_reader(raw))
        self.assertEqual(df["Date"].iloc[-1], raw["Date"].iloc[-1])


# ── field selection ───────────────────────────────────────────────────────────

class FieldSelectionTests(unittest.TestCase):

    def test_default_returns_ohlcv(self) -> None:
        df = load_symbol_data("AVGO", window=5, _reader=_reader(_make_raw()))
        for col in ("Open", "High", "Low", "Close", "Volume"):
            self.assertIn(col, df.columns)

    def test_requested_field_returned(self) -> None:
        df = load_symbol_data("AVGO", window=5, fields=["High"], _reader=_reader(_make_raw()))
        self.assertIn("High", df.columns)

    def test_unknown_field_raises(self) -> None:
        with self.assertRaises(ValueError):
            load_symbol_data("AVGO", fields=["NonExistentField"], _reader=_reader(_make_raw()))

    def test_all_supported_fields_constant(self) -> None:
        self.assertIn("Ret5", ALL_SUPPORTED_FIELDS)
        self.assertIn("Pos30", ALL_SUPPORTED_FIELDS)
        self.assertIn("PosLabel", ALL_SUPPORTED_FIELDS)
        self.assertIn("StageLabel", ALL_SUPPORTED_FIELDS)
        self.assertIn("Code", ALL_SUPPORTED_FIELDS)


# ── derived field computation ─────────────────────────────────────────────────

class DerivedFieldTests(unittest.TestCase):

    def _load(self, field: str) -> pd.DataFrame:
        return load_symbol_data(
            "AVGO", window=10, fields=[field],
            _reader=_reader(_make_raw(60)),
        )

    def test_ret5_present_and_numeric(self) -> None:
        df = self._load("Ret5")
        self.assertIn("Ret5", df.columns)
        self.assertTrue(pd.api.types.is_numeric_dtype(df["Ret5"]))

    def test_ret3_present_and_numeric(self) -> None:
        df = self._load("Ret3")
        self.assertIn("Ret3", df.columns)
        self.assertTrue(pd.api.types.is_numeric_dtype(df["Ret3"]))

    def test_pos30_in_0_100_range(self) -> None:
        df = self._load("Pos30")
        valid = df["Pos30"].dropna()
        self.assertTrue((valid >= 0).all() and (valid <= 100).all())

    def test_poslabel_categorical_values(self) -> None:
        df = self._load("PosLabel")
        allowed = {"低位", "中位", "高位", "—"}
        self.assertTrue(df["PosLabel"].dropna().isin(allowed).all())

    def test_stagelabel_categorical_values(self) -> None:
        df = self._load("StageLabel")
        allowed = {"衰竭风险", "分歧", "加速", "启动", "整理", "延续", "—"}
        self.assertTrue(df["StageLabel"].dropna().isin(allowed).all())

    def test_code_column_preserved(self) -> None:
        df = self._load("Code")
        self.assertIn("Code", df.columns)


if __name__ == "__main__":
    unittest.main()
