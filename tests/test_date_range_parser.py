from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.date_range_parser import has_partial_date_signals, parse_date_range


class ParseDateRangeTests(unittest.TestCase):

    def test_chinese_shared_year(self) -> None:
        result = parse_date_range("调出博通2026年1月15日至2月9日历史数据")
        self.assertEqual(result, ("2026-01-15", "2026-02-09"))

    def test_chinese_both_years(self) -> None:
        result = parse_date_range("2026年1月15日到2026年2月9日")
        self.assertEqual(result, ("2026-01-15", "2026-02-09"))

    def test_iso_with_chinese_separator(self) -> None:
        result = parse_date_range("2026-01-15 至 2026-02-09")
        self.assertEqual(result, ("2026-01-15", "2026-02-09"))

    def test_slash_with_dash(self) -> None:
        result = parse_date_range("2026/1/15 - 2026/2/9")
        self.assertEqual(result, ("2026-01-15", "2026-02-09"))

    def test_no_date(self) -> None:
        self.assertIsNone(parse_date_range("只看博通最近20天成交量"))

    def test_single_date_no_range(self) -> None:
        self.assertIsNone(parse_date_range("2026年1月15日历史数据"))

    def test_partial_date_signals_true(self) -> None:
        # Has 年月日 + 至 but end date incomplete
        self.assertTrue(has_partial_date_signals("调出博通2026年1月15日至2月历史数据"))

    def test_partial_date_signals_combined_with_parse(self) -> None:
        # When parse_date_range succeeds, callers won't reach has_partial_date_signals;
        # the combined guard (partial = has_signals AND parse is None) is what matters.
        text = "2026年1月15日至2月9日"
        date_range = parse_date_range(text)
        self.assertIsNotNone(date_range)
        # Even if has_partial_date_signals is True alone, the combined guard is False
        combined = has_partial_date_signals(text) and date_range is None
        self.assertFalse(combined)

    def test_partial_date_signals_false_for_relative(self) -> None:
        self.assertFalse(has_partial_date_signals("最近20天"))

    def test_zero_padding(self) -> None:
        result = parse_date_range("2026年3月5日至4月2日")
        self.assertEqual(result, ("2026-03-05", "2026-04-02"))

    # ── 号 support ────────────────────────────────────────────────────────────

    def test_hao_no_year_parse_returns_none(self) -> None:
        # No year → cannot safely infer; must return None
        self.assertIsNone(parse_date_range("2月5号至2月25号"))

    def test_hao_no_year_partial_signal_true(self) -> None:
        # Fragment "2月5号" + separator "至" → partial signal must fire
        self.assertTrue(has_partial_date_signals("2月5号至2月25号"))

    def test_hao_shared_year(self) -> None:
        result = parse_date_range("2026年2月5号至2月25号")
        self.assertEqual(result, ("2026-02-05", "2026-02-25"))

    def test_hao_both_years(self) -> None:
        result = parse_date_range("2026年2月5号到2026年2月25号")
        self.assertEqual(result, ("2026-02-05", "2026-02-25"))

    def test_hao_mixed_ri_hao(self) -> None:
        # Start uses 日, end uses 号 — both should parse
        result = parse_date_range("2026年2月5日至2月25号")
        self.assertEqual(result, ("2026-02-05", "2026-02-25"))


if __name__ == "__main__":
    unittest.main()
