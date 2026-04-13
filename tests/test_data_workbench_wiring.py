"""Tests for the data workbench command wiring in ui/command_bar.py.

Covers run_query_command and run_compare_command — the two new execution
paths added in Task 022.  All tests mock the data layer to avoid file I/O.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.command_parser import ParsedTask
from ui.command_bar import run_compare_command, run_query_command


# ── helpers ───────────────────────────────────────────────────────────────────

def _task(task_type, symbols=None, fields=None, window=20) -> ParsedTask:
    return ParsedTask(
        task_type=task_type,
        symbols=symbols or [],
        fields=fields or [],
        window=window,
        raw_text="test",
    )


def _make_df(n: int = 20, close_start: float = 100.0) -> pd.DataFrame:
    dates = pd.date_range("2023-01-01", periods=n, freq="B")
    return pd.DataFrame({
        "Date":   [d.strftime("%Y-%m-%d") for d in dates],
        "Open":   [close_start + i * 0.3 for i in range(n)],
        "High":   [close_start + i * 0.3 + 1.0 for i in range(n)],
        "Low":    [close_start + i * 0.3 - 0.5 for i in range(n)],
        "Close":  [close_start + i * 0.3 + 0.1 for i in range(n)],
        "Volume": [500_000 + i * 1_000 for i in range(n)],
    })


def _fake_loader(symbol: str, window: int = 0, fields=None, **_kwargs) -> pd.DataFrame:
    close_map = {"AVGO": 100.0, "NVDA": 400.0, "SOXX": 50.0, "QQQ": 380.0}
    n = window if window > 0 else 40
    return _make_df(n, close_start=close_map.get(symbol.upper(), 100.0))


# ── run_query_command ─────────────────────────────────────────────────────────

class RunQueryCommandTests(unittest.TestCase):

    def test_wrong_task_type_returns_none(self) -> None:
        result, error = run_query_command(_task("compare_data", ["AVGO"]))
        self.assertIsNone(result)
        self.assertIsNone(error)

    def test_no_symbols_returns_error(self) -> None:
        result, error = run_query_command(_task("query_data", []))
        self.assertIsNone(result)
        self.assertIsNotNone(error)
        self.assertIn("标的", error)

    def test_single_symbol_returns_list_of_one(self) -> None:
        result, error = run_query_command(
            _task("query_data", ["AVGO"]),
            _loader=_fake_loader,
        )
        self.assertIsNone(error)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        sym, df = result[0]
        self.assertEqual(sym, "AVGO")
        self.assertIsInstance(df, pd.DataFrame)

    def test_two_symbols_returns_list_of_two(self) -> None:
        result, error = run_query_command(
            _task("query_data", ["AVGO", "NVDA"]),
            _loader=_fake_loader,
        )
        self.assertIsNone(error)
        self.assertEqual(len(result), 2)
        symbols = [sym for sym, _ in result]
        self.assertIn("AVGO", symbols)
        self.assertIn("NVDA", symbols)

    def test_loader_exception_returns_error_string(self) -> None:
        def _bad_loader(*args, **kwargs):
            raise RuntimeError("disk error")

        result, error = run_query_command(
            _task("query_data", ["AVGO"]),
            _loader=_bad_loader,
        )
        self.assertIsNone(result)
        self.assertIsNotNone(error)
        self.assertIn("数据查询失败", error)

    def test_never_raises(self) -> None:
        def _explode(*args, **kwargs):
            raise Exception("boom")

        try:
            run_query_command(_task("query_data", ["AVGO"]), _loader=_explode)
        except Exception as exc:
            self.fail(f"run_query_command raised: {exc}")

    def test_window_passed_to_loader(self) -> None:
        calls = []

        def _recording_loader(symbol, window=0, **kwargs):
            calls.append(window)
            return _fake_loader(symbol, window=window)

        run_query_command(
            _task("query_data", ["AVGO"], window=15),
            _loader=_recording_loader,
        )
        self.assertEqual(calls[0], 15)


# ── run_compare_command ───────────────────────────────────────────────────────

class RunCompareCommandTests(unittest.TestCase):

    def test_wrong_task_type_returns_none(self) -> None:
        result, error = run_compare_command(_task("query_data", ["AVGO", "NVDA"]))
        self.assertIsNone(result)
        self.assertIsNone(error)

    def test_single_symbol_returns_error(self) -> None:
        result, error = run_compare_command(
            _task("compare_data", ["AVGO"]),
            _loader=_fake_loader,
        )
        self.assertIsNone(result)
        self.assertIsNotNone(error)
        self.assertIn("两个标的", error)

    def test_two_symbols_returns_result_dict(self) -> None:
        result, error = run_compare_command(
            _task("compare_data", ["AVGO", "NVDA"]),
            _loader=_fake_loader,
        )
        self.assertIsNone(error)
        self.assertIsNotNone(result)
        for key in ("aligned_df", "comparison_df", "stats", "field", "symbols"):
            self.assertIn(key, result)

    def test_result_contains_valid_stats(self) -> None:
        result, _ = run_compare_command(
            _task("compare_data", ["AVGO", "NVDA"]),
            _loader=_fake_loader,
        )
        stats = result["stats"]
        self.assertIn("total", stats)
        self.assertIn("matched", stats)
        self.assertIn("match_rate", stats)
        self.assertGreaterEqual(stats["total"], 0)

    def test_loader_exception_returns_error_string(self) -> None:
        def _bad_loader(*args, **kwargs):
            raise RuntimeError("network error")

        result, error = run_compare_command(
            _task("compare_data", ["AVGO", "NVDA"]),
            _loader=_bad_loader,
        )
        self.assertIsNone(result)
        self.assertIsNotNone(error)
        self.assertIn("数据对比失败", error)

    def test_never_raises(self) -> None:
        def _explode(*args, **kwargs):
            raise Exception("boom")

        try:
            run_compare_command(_task("compare_data", ["AVGO", "NVDA"]), _loader=_explode)
        except Exception as exc:
            self.fail(f"run_compare_command raised: {exc}")

    def test_default_comparison_field_is_close(self) -> None:
        result, _ = run_compare_command(
            _task("compare_data", ["AVGO", "NVDA"], fields=[]),
            _loader=_fake_loader,
        )
        self.assertEqual(result["field"], "Close")

    def test_explicit_field_used(self) -> None:
        result, _ = run_compare_command(
            _task("compare_data", ["AVGO", "NVDA"], fields=["High"]),
            _loader=_fake_loader,
        )
        self.assertEqual(result["field"], "High")


if __name__ == "__main__":
    unittest.main()
