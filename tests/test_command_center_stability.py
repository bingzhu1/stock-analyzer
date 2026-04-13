"""Stability tests for the command center (ui/command_bar.py).

Covers:
- Exception guard in run_projection_command()
- Session-state result persistence across re-renders
- Input-change staleness clearing
- Empty / whitespace input safe handling
- Repeated parse of the same command
- Non-projection commands not touching the entrypoint
"""
from __future__ import annotations

import sys
import textwrap
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.command_parser import ParsedTask, parse_command
from ui.command_bar import (
    _PROJECTION_ERROR_NO_SYMBOL,
    _SS_LAST_INPUT,
    _SS_PARSED,
    _SS_PROJ_ERROR,
    _SS_PROJ_RESULT,
    run_projection_command,
)

try:
    import pandas  # noqa: F401
    from streamlit.testing.v1 import AppTest
except ModuleNotFoundError:
    AppTest = None


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _projection_task(symbol: str = "AVGO") -> ParsedTask:
    return ParsedTask(
        task_type="run_projection",
        symbols=[symbol],
        fields=[],
        window=-1,
        raw_text=f"推演{symbol}下一个交易日走势",
    )


def _query_task() -> ParsedTask:
    return ParsedTask(
        task_type="query_data",
        symbols=["AVGO"],
        fields=["Close"],
        window=20,
        raw_text="调出博通最近20天收盘价",
    )


def _script() -> str:
    """Minimal embedded script for AppTest."""
    return textwrap.dedent(
        f"""
        import sys
        sys.path.insert(0, {str(ROOT)!r})

        import streamlit as st
        from ui.command_bar import render_command_bar

        render_command_bar()
        """
    )


# ─────────────────────────────────────────────────────────────────────────────
# Exception guard tests (no Streamlit required)
# ─────────────────────────────────────────────────────────────────────────────

class ExceptionGuardTests(unittest.TestCase):
    """run_projection_command() must never raise; failures become error strings."""

    def test_entrypoint_exception_returns_error_string(self) -> None:
        task = _projection_task()
        with patch("ui.command_bar.run_projection_entrypoint", side_effect=RuntimeError("db unavailable")):
            result, error = run_projection_command(task)
        self.assertIsNone(result)
        self.assertIsNotNone(error)
        self.assertIn("推演执行失败", error)

    def test_entrypoint_exception_message_included(self) -> None:
        task = _projection_task()
        with patch("ui.command_bar.run_projection_entrypoint", side_effect=ValueError("bad symbol")):
            _, error = run_projection_command(task)
        self.assertIn("bad symbol", error)

    def test_entrypoint_success_returns_dict(self) -> None:
        task = _projection_task()
        fake_result = {"ready": True, "advisory": {"matched_count": 2, "caution_level": "low", "reminder_lines": []}}
        with patch("ui.command_bar.run_projection_entrypoint", return_value=fake_result):
            result, error = run_projection_command(task)
        self.assertEqual(result, fake_result)
        self.assertIsNone(error)

    def test_non_projection_task_never_calls_entrypoint(self) -> None:
        task = _query_task()
        with patch("ui.command_bar.run_projection_entrypoint") as mock_ep:
            result, error = run_projection_command(task)
        mock_ep.assert_not_called()
        self.assertIsNone(result)
        self.assertIsNone(error)

    def test_missing_symbol_never_calls_entrypoint(self) -> None:
        task = ParsedTask(
            task_type="run_projection",
            symbols=[],
            fields=[],
            window=-1,
            raw_text="推演下一个交易日走势",
        )
        with patch("ui.command_bar.run_projection_entrypoint") as mock_ep:
            result, error = run_projection_command(task)
        mock_ep.assert_not_called()
        self.assertIsNone(result)
        self.assertEqual(error, _PROJECTION_ERROR_NO_SYMBOL)

    def test_never_raises_on_any_exception_type(self) -> None:
        task = _projection_task()
        for exc_class in (RuntimeError, ValueError, KeyError, AttributeError, Exception):
            with patch("ui.command_bar.run_projection_entrypoint", side_effect=exc_class("boom")):
                try:
                    run_projection_command(task)
                except Exception as e:
                    self.fail(f"run_projection_command raised {type(e).__name__} for {exc_class.__name__}")


# ─────────────────────────────────────────────────────────────────────────────
# Session-state constant exports
# ─────────────────────────────────────────────────────────────────────────────

class SessionStateKeyTests(unittest.TestCase):
    """Session-state key constants must be importable strings."""

    def test_session_state_keys_are_strings(self) -> None:
        for key in (_SS_PARSED, _SS_PROJ_RESULT, _SS_PROJ_ERROR, _SS_LAST_INPUT):
            self.assertIsInstance(key, str)

    def test_session_state_keys_are_unique(self) -> None:
        keys = [_SS_PARSED, _SS_PROJ_RESULT, _SS_PROJ_ERROR, _SS_LAST_INPUT]
        self.assertEqual(len(keys), len(set(keys)))


# ─────────────────────────────────────────────────────────────────────────────
# AppTest stability tests (requires streamlit + pandas)
# ─────────────────────────────────────────────────────────────────────────────

@unittest.skipIf(AppTest is None, "streamlit AppTest or pandas is not installed")
class CommandBarStabilityAppTests(unittest.TestCase):

    def _get_button(self, at, key: str):
        for btn in at.button:
            if btn.key == key:
                return btn
        raise AssertionError(f"Button {key!r} not found")

    def test_repeated_parse_same_input_no_error(self) -> None:
        """Clicking parse multiple times on the same input must not crash."""
        at = AppTest.from_string(_script()).run()
        at.text_input(key="cn_command_input").input("调出博通最近20天数据")
        # First click
        at = self._get_button(at, "cn_parse_btn").click().run()
        self.assertFalse(at.exception, msg=f"1st click: {at.exception}")
        # Second click (same input)
        at = self._get_button(at, "cn_parse_btn").click().run()
        self.assertFalse(at.exception, msg=f"2nd click: {at.exception}")

    def test_empty_input_repeated_clicks_no_error(self) -> None:
        """Clicking parse repeatedly with empty input must not crash."""
        at = AppTest.from_string(_script()).run()
        for i in range(3):
            at = self._get_button(at, "cn_parse_btn").click().run()
            self.assertFalse(at.exception, msg=f"Click {i+1}: {at.exception}")

    def test_parse_then_clear_then_parse_no_error(self) -> None:
        """Changing input after a successful parse then re-parsing must not crash."""
        at = AppTest.from_string(_script()).run()
        at.text_input(key="cn_command_input").input("调出博通最近20天数据")
        at = self._get_button(at, "cn_parse_btn").click().run()
        self.assertFalse(at.exception)
        # Change input
        at.text_input(key="cn_command_input").input("比较博通和英伟达最近20天最高价走势")
        at = self._get_button(at, "cn_parse_btn").click().run()
        self.assertFalse(at.exception, msg=f"After input change: {at.exception}")

    def test_unknown_command_no_exception(self) -> None:
        """An unknown command must show an error widget, not throw an exception."""
        at = AppTest.from_string(_script()).run()
        at.text_input(key="cn_command_input").input("这是无法识别的指令xyz")
        at = self._get_button(at, "cn_parse_btn").click().run()
        self.assertFalse(at.exception)
        error_texts = [e.value for e in at.error]
        self.assertTrue(any("解析错误" in t for t in error_texts))

    def test_whitespace_only_input_no_exception(self) -> None:
        """Whitespace-only input must show a warning, not crash."""
        at = AppTest.from_string(_script()).run()
        at.text_input(key="cn_command_input").input("   ")
        at = self._get_button(at, "cn_parse_btn").click().run()
        self.assertFalse(at.exception)
        warning_texts = [w.value for w in at.warning]
        self.assertTrue(any("请先输入指令" in t for t in warning_texts))

    def test_rerender_after_success_no_exception(self) -> None:
        """A re-render (simulated by a second .run()) after a successful parse must not crash."""
        at = AppTest.from_string(_script()).run()
        at.text_input(key="cn_command_input").input("调出博通最近20天数据")
        at = self._get_button(at, "cn_parse_btn").click().run()
        self.assertFalse(at.exception)
        # Simulate re-render (no interaction)
        at = at.run()
        self.assertFalse(at.exception, msg=f"Re-render: {at.exception}")


if __name__ == "__main__":
    unittest.main()
