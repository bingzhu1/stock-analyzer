from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.command_parser import ParsedTask, parse_command
from ui.command_bar import run_projection_command


class CommandProjectionWiringTests(unittest.TestCase):
    def test_run_projection_command_calls_entrypoint_with_first_symbol(self) -> None:
        parsed = parse_command("推演博通下一个交易日走势")
        expected = {
            "symbol": "AVGO",
            "request": {"symbol": "AVGO"},
            "advisory": {"matched_count": 0},
            "ready": True,
        }

        with patch("ui.command_bar.run_projection_entrypoint", return_value=expected) as mocked:
            result, error = run_projection_command(parsed)

        self.assertIsNone(error)
        self.assertEqual(result, expected)
        mocked.assert_called_once_with(symbol="AVGO")

    def test_projection_without_symbol_fails_safely(self) -> None:
        parsed = parse_command("推演下一个交易日走势")

        with patch("ui.command_bar.run_projection_entrypoint") as mocked:
            result, error = run_projection_command(parsed)

        self.assertIsNone(result)
        self.assertIsNotNone(error)
        assert error is not None
        self.assertIn("需要指定标的", error)
        mocked.assert_not_called()

    def test_non_projection_command_is_not_executed(self) -> None:
        parsed = parse_command("调出博通最近20天数据")

        with patch("ui.command_bar.run_projection_entrypoint") as mocked:
            result, error = run_projection_command(parsed)

        self.assertIsNone(result)
        self.assertIsNone(error)
        mocked.assert_not_called()

    def test_parse_error_command_is_not_projection_execution(self) -> None:
        parsed = ParsedTask(
            task_type="unknown",
            symbols=[],
            fields=[],
            window=20,
            raw_text="帮我查天气",
            parse_error="无法识别指令类型",
        )

        with patch("ui.command_bar.run_projection_entrypoint") as mocked:
            result, error = run_projection_command(parsed)

        self.assertIsNone(result)
        self.assertIsNone(error)
        mocked.assert_not_called()


if __name__ == "__main__":
    unittest.main()
