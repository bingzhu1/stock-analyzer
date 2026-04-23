from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.command_parser import (
    DEFAULT_WINDOW,
    FIELD_MAP,
    SYMBOL_MAP,
    ParsedTask,
    parse_command,
)


# ─────────────────────────────────────────────────────────────────────────────
# Task-type detection
# ─────────────────────────────────────────────────────────────────────────────

class TaskTypeDetectionTests(unittest.TestCase):

    def test_query_data_via_调出(self) -> None:
        result = parse_command("调出博通最近20天数据")
        self.assertEqual(result.task_type, "query_data")
        self.assertIsNone(result.parse_error)

    def test_query_data_via_查询(self) -> None:
        result = parse_command("查询英伟达最近15天收盘价")
        self.assertEqual(result.task_type, "query_data")

    def test_compare_data_via_比较(self) -> None:
        result = parse_command("比较博通和英伟达最近20天最高价走势")
        self.assertEqual(result.task_type, "compare_data")
        self.assertIsNone(result.parse_error)

    def test_compare_data_via_对比(self) -> None:
        result = parse_command("对比博通和费城最近20天收盘方向")
        self.assertEqual(result.task_type, "compare_data")

    def test_run_projection_via_推演(self) -> None:
        result = parse_command("推演博通下一个交易日走势")
        self.assertEqual(result.task_type, "run_projection")
        self.assertIsNone(result.parse_error)

    def test_run_projection_via_预测(self) -> None:
        result = parse_command("根据博通20天数据预测明天走势")
        self.assertEqual(result.task_type, "run_projection")

    def test_run_review_via_复盘(self) -> None:
        result = parse_command("复盘昨天")
        self.assertEqual(result.task_type, "run_review")
        self.assertIsNone(result.parse_error)

    def test_run_review_full_phrase(self) -> None:
        result = parse_command("一键复盘最近一次推演")
        self.assertEqual(result.task_type, "run_review")

    def test_unknown_task_returns_parse_error(self) -> None:
        result = parse_command("帮我查一下今天天气")
        self.assertEqual(result.task_type, "unknown")
        self.assertIsNotNone(result.parse_error)

    def test_review_takes_priority_over_projection_keywords(self) -> None:
        # "复盘" in same sentence as "推演" — review wins (higher priority)
        result = parse_command("复盘最近一次推演结果")
        self.assertEqual(result.task_type, "run_review")


# ─────────────────────────────────────────────────────────────────────────────
# Symbol extraction
# ─────────────────────────────────────────────────────────────────────────────

class SymbolExtractionTests(unittest.TestCase):

    def test_博通_maps_to_AVGO(self) -> None:
        result = parse_command("调出博通最近20天数据")
        self.assertIn("AVGO", result.symbols)

    def test_英伟达_maps_to_NVDA(self) -> None:
        result = parse_command("调出英伟达最近30天最高价")
        self.assertIn("NVDA", result.symbols)

    def test_费城半导体_maps_to_SOXX(self) -> None:
        result = parse_command("比较博通和费城半导体最近20天收盘方向")
        self.assertIn("SOXX", result.symbols)

    def test_费城_maps_to_SOXX(self) -> None:
        result = parse_command("比较博通和费城最近20天收盘价")
        self.assertIn("SOXX", result.symbols)
        # SOXX should only appear once even if both aliases present
        self.assertEqual(result.symbols.count("SOXX"), 1)

    def test_纳指_maps_to_QQQ(self) -> None:
        result = parse_command("调出纳指最近15天数据")
        self.assertIn("QQQ", result.symbols)

    def test_纳斯达克_maps_to_QQQ(self) -> None:
        result = parse_command("调出纳斯达克最近15天数据")
        self.assertIn("QQQ", result.symbols)

    def test_two_symbols_in_compare(self) -> None:
        result = parse_command("比较博通和英伟达最近20天最高价走势")
        self.assertIn("AVGO", result.symbols)
        self.assertIn("NVDA", result.symbols)

    def test_no_duplicate_symbols(self) -> None:
        # Same symbol mentioned twice should appear only once
        result = parse_command("比较博通和博通最近20天")
        self.assertEqual(result.symbols.count("AVGO"), 1)

    def test_missing_symbol_in_query_sets_parse_error(self) -> None:
        result = parse_command("调出最近20天数据")
        self.assertIsNotNone(result.parse_error)
        self.assertEqual(result.task_type, "query_data")

    def test_missing_symbol_in_compare_sets_parse_error(self) -> None:
        result = parse_command("比较最近20天最高价走势")
        self.assertIsNotNone(result.parse_error)


# ─────────────────────────────────────────────────────────────────────────────
# Field extraction
# ─────────────────────────────────────────────────────────────────────────────

class FieldExtractionTests(unittest.TestCase):

    def test_最高价_maps_to_High(self) -> None:
        result = parse_command("调出博通最近20天最高价")
        self.assertIn("High", result.fields)

    def test_收盘价_maps_to_Close(self) -> None:
        result = parse_command("调出博通最近20天收盘价")
        self.assertIn("Close", result.fields)

    def test_成交量_maps_to_Volume(self) -> None:
        result = parse_command("调出博通最近15天收盘价和成交量")
        self.assertIn("Volume", result.fields)
        self.assertIn("Close", result.fields)

    def test_位置标签_maps_to_PosLabel_not_Pos30(self) -> None:
        # "位置标签" must match PosLabel, not Pos30, even though "位置" is a substring
        result = parse_command("调出博通最近20天位置标签")
        self.assertIn("PosLabel", result.fields)
        self.assertNotIn("Pos30", result.fields)

    def test_位置_maps_to_Pos30(self) -> None:
        result = parse_command("调出博通最近20天位置")
        self.assertIn("Pos30", result.fields)

    def test_动能_maps_to_StageLabel(self) -> None:
        result = parse_command("调出博通最近20天动能")
        self.assertIn("StageLabel", result.fields)

    def test_no_duplicate_fields(self) -> None:
        # Even if 最高价 appears twice, High should only appear once
        result = parse_command("调出博通最近20天最高价和最高价")
        self.assertEqual(result.fields.count("High"), 1)

    def test_no_fields_is_acceptable(self) -> None:
        result = parse_command("调出博通最近20天数据")
        # "数据" alone doesn't map to any field — fields list may be empty
        self.assertIsInstance(result.fields, list)


# ─────────────────────────────────────────────────────────────────────────────
# Time-window extraction
# ─────────────────────────────────────────────────────────────────────────────

class WindowExtractionTests(unittest.TestCase):

    def test_最近15天(self) -> None:
        result = parse_command("调出博通最近15天数据")
        self.assertEqual(result.window, 15)

    def test_最近20天(self) -> None:
        result = parse_command("调出博通最近20天数据")
        self.assertEqual(result.window, 20)

    def test_最近30天(self) -> None:
        result = parse_command("调出博通最近30天数据")
        self.assertEqual(result.window, 30)

    def test_最近60天(self) -> None:
        result = parse_command("调出博通最近60天数据")
        self.assertEqual(result.window, 60)

    def test_明天_returns_minus_one(self) -> None:
        result = parse_command("推演博通明天走势")
        self.assertEqual(result.window, -1)

    def test_下一个交易日_returns_minus_one(self) -> None:
        result = parse_command("推演博通下一个交易日走势")
        self.assertEqual(result.window, -1)

    def test_no_window_defaults_to_20(self) -> None:
        result = parse_command("调出博通数据")
        self.assertEqual(result.window, DEFAULT_WINDOW)

    def test_arbitrary_N天_is_parsed(self) -> None:
        result = parse_command("调出博通最近45天数据")
        self.assertEqual(result.window, 45)


# ─────────────────────────────────────────────────────────────────────────────
# Edge cases and error handling
# ─────────────────────────────────────────────────────────────────────────────

class EdgeCaseTests(unittest.TestCase):

    def test_empty_string_returns_parse_error(self) -> None:
        result = parse_command("")
        self.assertEqual(result.task_type, "unknown")
        self.assertIsNotNone(result.parse_error)

    def test_whitespace_only_returns_parse_error(self) -> None:
        result = parse_command("   ")
        self.assertIsNotNone(result.parse_error)

    def test_parse_command_never_raises(self) -> None:
        for text in ("???", "hello world", "", "1234567890", "复盘"):
            try:
                result = parse_command(text)
                self.assertIsInstance(result, ParsedTask)
            except Exception as exc:
                self.fail(f"parse_command({text!r}) raised {exc}")

    def test_raw_text_is_preserved(self) -> None:
        text = "调出博通最近20天数据"
        result = parse_command(text)
        self.assertEqual(result.raw_text, text)

    def test_raw_text_is_stripped(self) -> None:
        result = parse_command("  调出博通最近20天数据  ")
        self.assertEqual(result.raw_text, "调出博通最近20天数据")

    def test_run_review_no_symbol_needed(self) -> None:
        # run_review should not require a symbol to parse cleanly
        result = parse_command("复盘昨天")
        self.assertIsNone(result.parse_error)

    def test_run_projection_no_symbol_no_error(self) -> None:
        # run_projection doesn't require a symbol match to succeed
        result = parse_command("推演下一个交易日走势")
        self.assertIsNone(result.parse_error)

    def test_result_fields_are_lists(self) -> None:
        result = parse_command("调出博通最近20天数据")
        self.assertIsInstance(result.symbols, list)
        self.assertIsInstance(result.fields, list)

    def test_task_type_is_valid_value(self) -> None:
        from services.command_parser import VALID_TASK_TYPES
        for text in [
            "调出博通最近20天",
            "比较博通和英伟达",
            "推演博通下一个交易日",
            "复盘昨天",
            "完全无关的话",
        ]:
            result = parse_command(text)
            self.assertIn(result.task_type, VALID_TASK_TYPES, msg=f"input: {text!r}")


# ─────────────────────────────────────────────────────────────────────────────
# Task 023 — natural language sentence coverage
# ─────────────────────────────────────────────────────────────────────────────

class NaturalLanguageSentenceTests(unittest.TestCase):
    """
    Verify that the 7 target sentences from Task 023 parse correctly.
    Each test maps one sentence to its expected (task_type, symbols, fields, window).
    """

    # Sentence 1: "把博通、英伟达、费城、纳指最近20天数据并排"
    def test_s1_parallel_multi_symbol_query(self) -> None:
        result = parse_command("把博通、英伟达、费城、纳指最近20天数据并排")
        self.assertEqual(result.task_type, "query_data")
        self.assertIsNone(result.parse_error)
        for sym in ("AVGO", "NVDA", "SOXX", "QQQ"):
            self.assertIn(sym, result.symbols)
        self.assertEqual(result.window, 20)

    # Sentence 2: "只看博通最近20天"
    def test_s2_只看_single_symbol(self) -> None:
        result = parse_command("只看博通最近20天")
        self.assertEqual(result.task_type, "query_data")
        self.assertIsNone(result.parse_error)
        self.assertIn("AVGO", result.symbols)
        self.assertEqual(result.window, 20)

    # Sentence 3: "只看英伟达最近20天最高价"
    def test_s3_只看_with_field(self) -> None:
        result = parse_command("只看英伟达最近20天最高价")
        self.assertEqual(result.task_type, "query_data")
        self.assertIsNone(result.parse_error)
        self.assertIn("NVDA", result.symbols)
        self.assertIn("High", result.fields)
        self.assertEqual(result.window, 20)

    # Sentence 4: "调出博通最近20天收盘价和成交量"
    def test_s4_multi_field_query(self) -> None:
        result = parse_command("调出博通最近20天收盘价和成交量")
        self.assertEqual(result.task_type, "query_data")
        self.assertIsNone(result.parse_error)
        self.assertIn("AVGO", result.symbols)
        self.assertIn("Close", result.fields)
        self.assertIn("Volume", result.fields)
        self.assertEqual(result.window, 20)

    # Sentence 5: "比较英伟达和博通最近20天最高价走势"
    def test_s5_compare_two_symbols_with_field(self) -> None:
        result = parse_command("比较英伟达和博通最近20天最高价走势")
        self.assertEqual(result.task_type, "compare_data")
        self.assertIsNone(result.parse_error)
        self.assertIn("NVDA", result.symbols)
        self.assertIn("AVGO", result.symbols)
        self.assertIn("High", result.fields)
        self.assertEqual(result.window, 20)

    # Sentence 6: "比较英伟达和博通最近20天最高价走势，一致里博通高位、中位、低位各多少天"
    def test_s6_compare_with_stat_request(self) -> None:
        result = parse_command(
            "比较英伟达和博通最近20天最高价走势，一致里博通高位、中位、低位各多少天"
        )
        self.assertEqual(result.task_type, "compare_data")
        self.assertIsNone(result.parse_error)
        self.assertIn("NVDA", result.symbols)
        self.assertIn("AVGO", result.symbols)
        self.assertIn("High", result.fields)
        self.assertEqual(result.window, 20)
        self.assertIsNotNone(result.stat_request)
        self.assertEqual(result.stat_request["type"], "distribution_by_label")
        self.assertEqual(result.stat_request["symbol"], "AVGO")
        self.assertEqual(result.stat_request["field"], "PosLabel")

    # Sentence 7: "根据博通20天数据推演下一个交易日走势"
    def test_s7_projection_with_lookback_phrase(self) -> None:
        result = parse_command("根据博通20天数据推演下一个交易日走势")
        self.assertEqual(result.task_type, "run_projection")
        self.assertIsNone(result.parse_error)
        self.assertIn("AVGO", result.symbols)
        # "下一个交易日" takes priority → window = -1
        self.assertEqual(result.window, -1)


class StatRequestExtractionTests(unittest.TestCase):
    """Unit tests for _extract_stat_request via parse_command()."""

    def test_no_stat_request_for_simple_query(self) -> None:
        result = parse_command("调出博通最近20天数据")
        self.assertIsNone(result.stat_request)

    def test_no_stat_request_for_simple_compare(self) -> None:
        result = parse_command("比较博通和英伟达最近20天收盘价")
        self.assertIsNone(result.stat_request)

    def test_no_stat_request_for_projection(self) -> None:
        result = parse_command("推演博通下一个交易日走势")
        self.assertIsNone(result.stat_request)

    def test_distribution_by_label_detected(self) -> None:
        result = parse_command("比较博通和英伟达最近20天最高价，高位、中位、低位各多少天")
        self.assertIsNotNone(result.stat_request)
        self.assertEqual(result.stat_request["type"], "distribution_by_label")
        self.assertEqual(result.stat_request["field"], "PosLabel")

    def test_distribution_symbol_inferred_from_nearby_label(self) -> None:
        # "博通高位" → AVGO should be the distribution symbol
        result = parse_command(
            "比较英伟达和博通最近20天收盘价走势，一致里博通高位、中位、低位各多少天"
        )
        self.assertIsNotNone(result.stat_request)
        self.assertEqual(result.stat_request["symbol"], "AVGO")

    def test_match_rate_request(self) -> None:
        result = parse_command("比较博通和英伟达最近20天收盘价一致率")
        self.assertIsNotNone(result.stat_request)
        self.assertEqual(result.stat_request["type"], "match_rate")

    def test_matched_count_request(self) -> None:
        result = parse_command("比较博通和英伟达最近20天一致天数")
        self.assertIsNotNone(result.stat_request)
        self.assertEqual(result.stat_request["type"], "matched_count")

    def test_mismatched_count_request(self) -> None:
        result = parse_command("比较博通和英伟达最近20天不一致天数")
        self.assertIsNotNone(result.stat_request)
        self.assertEqual(result.stat_request["type"], "mismatched_count")

    def test_stat_request_is_dict_or_none(self) -> None:
        for text in [
            "调出博通最近20天",
            "比较博通和英伟达最近20天最高价走势，一致里博通高位各多少天",
        ]:
            result = parse_command(text)
            self.assertTrue(
                result.stat_request is None or isinstance(result.stat_request, dict),
                msg=f"stat_request should be dict or None for: {text!r}",
            )


class WindowExtensionTests(unittest.TestCase):
    """Tests for the bare 'N天' (without 最近) window fallback."""

    def test_bare_n_tian_extracted(self) -> None:
        result = parse_command("只看博通20天")
        self.assertEqual(result.window, 20)

    def test_bare_n_tian_30(self) -> None:
        result = parse_command("只看博通30天最高价")
        self.assertEqual(result.window, 30)

    def test_最近_prefix_still_takes_priority(self) -> None:
        # "最近20天" is a fixed pattern and should still resolve correctly
        result = parse_command("调出博通最近20天数据")
        self.assertEqual(result.window, 20)

    def test_small_n_does_not_match(self) -> None:
        # "3天" (N < 5) should not be extracted; falls back to DEFAULT_WINDOW
        result = parse_command("只看博通3天")
        self.assertEqual(result.window, DEFAULT_WINDOW)

    def test_下一个交易日_still_overrides_bare_n_tian(self) -> None:
        # "下一个交易日" in _WINDOW_PATTERNS fires before the bare fallback
        result = parse_command("根据博通20天数据推演下一个交易日走势")
        self.assertEqual(result.window, -1)


class NewQueryKeywordTests(unittest.TestCase):
    """Tests for the new query-intent keywords: 只看, 并排, 查看."""

    def test_只看_triggers_query(self) -> None:
        result = parse_command("只看博通最近20天")
        self.assertEqual(result.task_type, "query_data")

    def test_并排_triggers_query(self) -> None:
        result = parse_command("博通和英伟达最近20天数据并排")
        self.assertEqual(result.task_type, "query_data")

    def test_查看_triggers_query(self) -> None:
        result = parse_command("查看博通最近20天最高价")
        self.assertEqual(result.task_type, "query_data")
        self.assertIsNone(result.parse_error)

    def test_只看_with_no_symbol_sets_error(self) -> None:
        # query intent detected but no symbol → error
        result = parse_command("只看最近20天数据")
        self.assertEqual(result.task_type, "query_data")
        self.assertIsNotNone(result.parse_error)

    def test_compare_keyword_still_wins_over_只看(self) -> None:
        # Priority: review > projection > compare > query
        # This sentence has both 比较 (compare) — compare should win
        result = parse_command("比较博通和英伟达只看最高价")
        self.assertEqual(result.task_type, "compare_data")


class AIExplanationIntentTests(unittest.TestCase):
    def test_ai_explain_projection_intent(self) -> None:
        result = parse_command("用 AI 解释这次推演")
        self.assertEqual(result.task_type, "ai_explanation")
        self.assertIsNone(result.parse_error)
        self.assertEqual(result.ai_request, {"focus": "projection"})

    def test_ai_explain_direction_intent(self) -> None:
        result = parse_command("用 AI 解释为什么偏空")
        self.assertEqual(result.task_type, "ai_explanation")
        self.assertEqual(result.ai_request, {"focus": "direction", "direction": "偏空"})

    def test_ai_summarize_compare_intent(self) -> None:
        result = parse_command("用 AI 总结这次比较结果")
        self.assertEqual(result.task_type, "ai_explanation")
        self.assertEqual(result.ai_request, {"focus": "compare"})

    def test_ai_explain_risk_intent(self) -> None:
        result = parse_command("用 AI 解释这次风险提醒")
        self.assertEqual(result.task_type, "ai_explanation")
        self.assertEqual(result.ai_request, {"focus": "risk"})

    def test_ai_intent_takes_priority_over_projection_keyword(self) -> None:
        result = parse_command("用 AI 解释这次推演，不要重新预测")
        self.assertEqual(result.task_type, "ai_explanation")


if __name__ == "__main__":
    unittest.main()
