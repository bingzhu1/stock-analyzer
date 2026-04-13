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
from ui.command_bar import (
    _render_compare_result,
    _render_query_result,
    run_compare_command,
    run_query_command,
)

# ── helpers for stat_request tests ───────────────────────────────────────────

def _fake_loader_with_pos(symbol: str, window: int = 0, fields=None, **_kwargs) -> pd.DataFrame:
    """Fake loader that includes PosLabel, suitable for position_distribution tests."""
    n = window if window > 0 else 40
    dates = pd.date_range("2023-01-01", periods=n, freq="B")
    close_start = {"AVGO": 100.0, "NVDA": 400.0}.get(symbol.upper(), 100.0)
    label_cycle = ["高位", "中位", "低位"]
    return pd.DataFrame({
        "Date":     [d.strftime("%Y-%m-%d") for d in dates],
        "Close":    [close_start + i * 0.3 + 0.1 for i in range(n)],
        "PosLabel": [label_cycle[i % 3] for i in range(n)],
    })


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


def _empty_loader(symbol: str, window: int = 0, fields=None, **_kwargs) -> pd.DataFrame:
    return pd.DataFrame({"Date": [], "Close": []})


class _FakeColumn:
    def __init__(self, parent) -> None:
        self._parent = parent

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def metric(self, label, value) -> None:
        self._parent.messages.append(f"{label}: {value}")


class _FakeStreamlit:
    def __init__(self) -> None:
        self.messages: list[str] = []
        self.dataframes: list[pd.DataFrame] = []

    def info(self, text: str) -> None:
        self.messages.append(text)

    def warning(self, text: str) -> None:
        self.messages.append(text)

    def caption(self, text: str) -> None:
        self.messages.append(text)

    def metric(self, label, value) -> None:
        self.messages.append(f"{label}: {value}")

    def columns(self, count: int) -> list[_FakeColumn]:
        return [_FakeColumn(self) for _ in range(count)]

    def dataframe(self, df, **_kwargs) -> None:
        self.dataframes.append(df)


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

    def test_empty_query_result_renders_warning(self) -> None:
        from ui import command_bar

        fake_st = _FakeStreamlit()
        old_st = command_bar.st
        try:
            command_bar.st = fake_st
            _render_query_result([("AVGO", _empty_loader("AVGO"))])
        finally:
            command_bar.st = old_st

        self.assertTrue(any("查询结果为空" in msg for msg in fake_st.messages))
        self.assertEqual(fake_st.dataframes, [])


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

    def test_result_always_has_position_dist_key(self) -> None:
        result, _ = run_compare_command(
            _task("compare_data", ["AVGO", "NVDA"]),
            _loader=_fake_loader,
        )
        self.assertIn("position_dist", result)

    def test_empty_compare_result_renders_guardrail_warning(self) -> None:
        from ui import command_bar

        result, error = run_compare_command(
            _task("compare_data", ["AVGO", "NVDA"]),
            _loader=_empty_loader,
        )
        self.assertIsNone(error)
        self.assertEqual(result["stats"]["total"], 0)

        fake_st = _FakeStreamlit()
        old_st = command_bar.st
        try:
            command_bar.st = fake_st
            _render_compare_result(result)
        finally:
            command_bar.st = old_st

        text = "\n".join(fake_st.messages)
        self.assertIn("样本不足", text)
        self.assertIn("逐日对比为空", text)
        self.assertIn("对齐数据为空", text)


# ── run_compare_command + stat_request ────────────────────────────────────────

class RunCompareStatRequestTests(unittest.TestCase):

    def _task_with_stat(self, stat_req, window: int = 15) -> ParsedTask:
        return ParsedTask(
            task_type="compare_data",
            symbols=["AVGO", "NVDA"],
            fields=["Close"],
            window=window,
            raw_text="test",
            stat_request=stat_req,
        )

    def test_no_stat_request_position_dist_is_none(self) -> None:
        result, error = run_compare_command(
            _task("compare_data", ["AVGO", "NVDA"]),
            _loader=_fake_loader,
        )
        self.assertIsNone(error)
        self.assertIsNone(result["position_dist"])

    def test_stat_request_distribution_adds_position_dist(self) -> None:
        result, error = run_compare_command(
            self._task_with_stat({
                "type": "distribution_by_label",
                "symbol": "AVGO",
                "field": "PosLabel",
            }),
            _loader=_fake_loader_with_pos,
        )
        self.assertIsNone(error)
        self.assertIsNotNone(result["position_dist"])

    def test_position_dist_has_required_keys(self) -> None:
        result, _ = run_compare_command(
            self._task_with_stat({
                "type": "distribution_by_label",
                "symbol": "AVGO",
                "field": "PosLabel",
            }),
            _loader=_fake_loader_with_pos,
        )
        dist = result["position_dist"]
        for key in ("高位", "中位", "低位", "total_matched", "label_source"):
            self.assertIn(key, dist)

    def test_position_dist_invariant_high_mid_low_sum(self) -> None:
        result, _ = run_compare_command(
            self._task_with_stat({
                "type": "distribution_by_label",
                "symbol": "AVGO",
                "field": "PosLabel",
            }),
            _loader=_fake_loader_with_pos,
        )
        dist = result["position_dist"]
        self.assertEqual(
            dist["高位"] + dist["中位"] + dist["低位"],
            dist["total_matched"],
        )

    def test_stat_symbol_recorded_in_result(self) -> None:
        result, _ = run_compare_command(
            self._task_with_stat({
                "type": "distribution_by_label",
                "symbol": "AVGO",
                "field": "PosLabel",
            }),
            _loader=_fake_loader_with_pos,
        )
        self.assertEqual(result["stat_symbol"], "AVGO")

    def test_stat_request_wrong_type_no_position_dist(self) -> None:
        result, _ = run_compare_command(
            self._task_with_stat({"type": "match_rate"}),
            _loader=_fake_loader,
        )
        self.assertIsNone(result["position_dist"])

    def test_never_raises_with_stat_request(self) -> None:
        try:
            run_compare_command(
                self._task_with_stat({
                    "type": "distribution_by_label",
                    "symbol": "AVGO",
                    "field": "PosLabel",
                }),
                _loader=_fake_loader_with_pos,
            )
        except Exception as exc:
            self.fail(f"run_compare_command raised with stat_request: {exc}")


if __name__ == "__main__":
    unittest.main()
