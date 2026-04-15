"""Tests for services/ai_intent_parser.py

Covers:
  - _needs_ai_fallback trigger conditions
  - _call_ai_parser JSON parsing and error handling
  - parse_with_ai_fallback integration (OpenAI mocked)
  - Safe degradation on API failure / bad JSON / unsupported intent
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.ai_intent_parser import (
    OHLCV_FIELDS,
    _call_ai_parser,
    _needs_ai_fallback,
    parse_with_ai_fallback,
)
from services.command_parser import DEFAULT_WINDOW, ParsedTask, parse_command


# ── helpers ────────────────────────────────────────────────────────────────────

def _mk_plan(
    *,
    supported: bool = True,
    primary: str = "query",
    fields: list | None = None,
    symbols: list | None = None,
    steps: list | None = None,
    warnings: list | None = None,
) -> dict:
    return {
        "kind": "intent_plan",
        "raw_text": "",
        "supported": supported,
        "primary_intent": primary,
        "fields": fields or [],
        "symbols": symbols or [],
        "steps": steps or [],
        "ai_followups": [],
        "warnings": warnings or [],
    }


def _mk_parsed(
    *,
    task_type: str = "query_data",
    symbols: list | None = None,
    fields: list | None = None,
    window: int = DEFAULT_WINDOW,
    raw_text: str = "",
    parse_error: str | None = None,
) -> ParsedTask:
    return ParsedTask(
        task_type=task_type,
        symbols=symbols or [],
        fields=fields or [],
        window=window,
        raw_text=raw_text,
        parse_error=parse_error,
    )


def _ohlcv_ai_json(**overrides) -> str:
    base = {
        "intent": "query",
        "symbols": ["AVGO"],
        "lookback_days": 20,
        "fields": ["Open", "High", "Low", "Close", "Volume"],
        "operation": None,
        "ai_followups": [],
        "confidence": "high",
        "ambiguity_reason": None,
    }
    base.update(overrides)
    return json.dumps(base)


# ── _needs_ai_fallback ─────────────────────────────────────────────────────────

class TestNeedsAiFallback(unittest.TestCase):

    def test_ohlcv_signal_no_fields_triggers(self):
        text = "调出博通近20天的所有数据"
        parsed = _mk_parsed(task_type="query_data", fields=[])
        plan = _mk_plan(supported=True, primary="query")
        self.assertTrue(_needs_ai_fallback(parsed, plan, text))

    def test_ohlcv_english_keyword_triggers(self):
        text = "调出博通近20天 OHLCV 数据"
        parsed = _mk_parsed(task_type="query_data", fields=[])
        plan = _mk_plan(supported=True, primary="query")
        self.assertTrue(_needs_ai_fallback(parsed, plan, text))

    def test_ohlcv_lowercase_triggers(self):
        text = "调出博通近20天 ohlcv 数据"
        parsed = _mk_parsed(task_type="query_data", fields=[])
        plan = _mk_plan(supported=True, primary="query")
        self.assertTrue(_needs_ai_fallback(parsed, plan, text))

    def test_ohlcv_with_fields_already_resolved_no_trigger(self):
        # If rule parse already resolved fields, AI not needed
        text = "调出博通近20天的所有数据"
        parsed = _mk_parsed(task_type="query_data", fields=["Close"])
        plan = _mk_plan(supported=True, primary="query")
        self.assertFalse(_needs_ai_fallback(parsed, plan, text))

    def test_unsupported_plan_and_unknown_parse_triggers(self):
        text = "帮我来个什么随机操作"
        parsed = _mk_parsed(task_type="unknown", fields=[], parse_error="无法识别")
        plan = _mk_plan(supported=False, primary="unsupported")
        self.assertTrue(_needs_ai_fallback(parsed, plan, text))

    def test_unsupported_plan_but_known_parse_no_trigger(self):
        # Rule parse identified intent even though planner couldn't
        text = "推演博通明天"
        parsed = _mk_parsed(task_type="run_projection")
        plan = _mk_plan(supported=False, primary="unsupported")
        self.assertFalse(_needs_ai_fallback(parsed, plan, text))

    def test_stats_correctly_identified_no_trigger(self):
        # plan correctly identifies stats, AI not needed
        text = "博通今天和最近20天平均成交量比怎么样"
        parsed = parse_command(text)
        from services.intent_planner import plan_intent
        plan = plan_intent(text)
        self.assertFalse(_needs_ai_fallback(parsed, plan, text))

    def test_compare_correctly_identified_no_trigger(self):
        text = "比较一下博通和英伟达最近20天强弱"
        parsed = parse_command(text)
        from services.intent_planner import plan_intent
        plan = plan_intent(text)
        self.assertFalse(_needs_ai_fallback(parsed, plan, text))

    def test_projection_correctly_identified_no_trigger(self):
        text = "帮我看看博通明天怎么样"
        parsed = parse_command(text)
        from services.intent_planner import plan_intent
        plan = plan_intent(text)
        self.assertFalse(_needs_ai_fallback(parsed, plan, text))

    def test_ai_explain_correctly_identified_no_trigger(self):
        text = "用 AI 解释这次推演"
        parsed = parse_command(text)
        from services.intent_planner import plan_intent
        plan = plan_intent(text)
        self.assertFalse(_needs_ai_fallback(parsed, plan, text))


# ── _call_ai_parser ────────────────────────────────────────────────────────────

class TestCallAiParser(unittest.TestCase):

    @patch("services.ai_intent_parser.generate_text", return_value=_ohlcv_ai_json())
    def test_valid_json_returned(self, _mock):
        result = _call_ai_parser("调出博通近20天的所有数据")
        self.assertIsNotNone(result)
        self.assertEqual(result["intent"], "query")
        self.assertIn("Open", result["fields"])

    @patch("services.ai_intent_parser.generate_text", return_value="not json at all")
    def test_bad_json_returns_none(self, _mock):
        result = _call_ai_parser("test")
        self.assertIsNone(result)

    @patch("services.ai_intent_parser.generate_text",
           return_value='{"intent": "bogus_intent", "symbols": ["AVGO"]}')
    def test_unsupported_intent_returns_none(self, _mock):
        result = _call_ai_parser("test")
        self.assertIsNone(result)

    @patch("services.ai_intent_parser.generate_text",
           side_effect=Exception("network error"))
    def test_exception_returns_none(self, _mock):
        result = _call_ai_parser("test")
        self.assertIsNone(result)

    @patch("services.ai_intent_parser.generate_text",
           return_value="```json\n" + _ohlcv_ai_json() + "\n```")
    def test_markdown_fenced_json_parsed(self, _mock):
        result = _call_ai_parser("test")
        self.assertIsNotNone(result)
        self.assertEqual(result["intent"], "query")

    @patch("services.ai_intent_parser.generate_text",
           return_value=_ohlcv_ai_json(intent="stats", operation="today_vs_average",
                                       fields=["Volume"]))
    def test_stats_intent_accepted(self, _mock):
        result = _call_ai_parser("博通今天成交量 vs 均值")
        self.assertIsNotNone(result)
        self.assertEqual(result["intent"], "stats")


# ── parse_with_ai_fallback — OHLCV resolution ─────────────────────────────────

class TestParseWithAiFallbackOHLCV(unittest.TestCase):

    @patch("services.ai_intent_parser.generate_text", return_value=_ohlcv_ai_json())
    def test_all_data_resolves_to_ohlcv(self, _mock):
        """'所有数据' should trigger AI and resolve to OHLCV fields."""
        parsed, plan, ai_used = parse_with_ai_fallback("调出博通近20天的所有数据")
        self.assertTrue(ai_used)
        self.assertEqual(set(parsed.fields), set(OHLCV_FIELDS))
        self.assertEqual(parsed.task_type, "query_data")
        self.assertEqual(plan.get("planner"), "rule+ai_fallback")

    @patch("services.ai_intent_parser.generate_text", return_value=_ohlcv_ai_json())
    def test_ohlcv_keyword_resolves_to_ohlcv(self, _mock):
        """'OHLCV' keyword should trigger AI and resolve to OHLCV fields."""
        parsed, plan, ai_used = parse_with_ai_fallback("调出博通近20天 OHLCV 数据")
        self.assertTrue(ai_used)
        self.assertEqual(set(parsed.fields), set(OHLCV_FIELDS))
        self.assertEqual(plan.get("planner"), "rule+ai_fallback")

    @patch("services.ai_intent_parser.generate_text", return_value=_ohlcv_ai_json())
    def test_symbols_preserved_from_rule_parse(self, _mock):
        """Symbols resolved by rule parser should not be overridden by AI."""
        parsed, plan, ai_used = parse_with_ai_fallback("调出博通近20天的所有数据")
        self.assertIn("AVGO", parsed.symbols)

    @patch("services.ai_intent_parser.generate_text", return_value=_ohlcv_ai_json())
    def test_plan_query_step_fields_updated(self, _mock):
        """Plan query step fields should be updated to OHLCV."""
        _, plan, ai_used = parse_with_ai_fallback("调出博通近20天的所有数据")
        self.assertTrue(ai_used)
        query_steps = [s for s in plan.get("steps", []) if s.get("type") == "query"]
        if query_steps:
            self.assertEqual(set(query_steps[0]["fields"]), set(OHLCV_FIELDS))


# ── parse_with_ai_fallback — no AI needed ─────────────────────────────────────

class TestParseWithAiFallbackNoAI(unittest.TestCase):

    def _assert_no_ai(self, text: str):
        """Assert AI is NOT called for well-handled inputs."""
        with patch("services.ai_intent_parser.generate_text") as mock_gen:
            _, _, ai_used = parse_with_ai_fallback(text)
            self.assertFalse(ai_used, f"AI triggered unexpectedly for: {text!r}")
            mock_gen.assert_not_called()

    def test_stats_volume_no_ai(self):
        self._assert_no_ai("博通今天和最近20天平均成交量比怎么样")

    def test_stats_close_no_ai(self):
        self._assert_no_ai("博通今天收盘价和最近20天平均收盘价对比")

    def test_compare_no_ai(self):
        self._assert_no_ai("比较一下博通和英伟达最近20天强弱")

    def test_projection_no_ai(self):
        self._assert_no_ai("帮我看看博通明天怎么样")

    def test_ai_explain_no_ai(self):
        self._assert_no_ai("用 AI 解释这次推演")


# ── parse_with_ai_fallback — safe degradation ─────────────────────────────────

class TestParseWithAiFallbackDegradation(unittest.TestCase):

    @patch("services.ai_intent_parser.generate_text",
           side_effect=Exception("no API key"))
    def test_api_failure_degrades_safely(self, _mock):
        """On API failure, rule parse result is returned unchanged."""
        parsed, plan, ai_used = parse_with_ai_fallback("调出博通近20天的所有数据")
        self.assertFalse(ai_used)
        self.assertEqual(parsed.task_type, "query_data")
        self.assertIsNone(plan.get("planner"))

    @patch("services.ai_intent_parser.generate_text",
           return_value="not valid json at all")
    def test_bad_json_degrades_safely(self, _mock):
        parsed, plan, ai_used = parse_with_ai_fallback("调出博通近20天的所有数据")
        self.assertFalse(ai_used)
        self.assertEqual(parsed.task_type, "query_data")

    @patch("services.ai_intent_parser.generate_text",
           return_value='{"intent": "unsupported_intent", "symbols": ["AVGO"]}')
    def test_unsupported_intent_degrades_safely(self, _mock):
        parsed, plan, ai_used = parse_with_ai_fallback("调出博通近20天的所有数据")
        self.assertFalse(ai_used)
        self.assertIsNone(plan.get("planner"))

    @patch("services.ai_intent_parser.generate_text",
           return_value="null")
    def test_null_json_degrades_safely(self, _mock):
        parsed, plan, ai_used = parse_with_ai_fallback("调出博通近20天的所有数据")
        self.assertFalse(ai_used)

    @patch("services.ai_intent_parser.generate_text",
           return_value=_ohlcv_ai_json(lookback_days="twenty"))
    def test_string_lookback_days_degrades_safely(self, _mock):
        parsed, plan, ai_used = parse_with_ai_fallback("调出博通近20天的所有数据")
        self.assertFalse(ai_used)
        self.assertEqual(parsed.task_type, "query_data")
        self.assertEqual(parsed.window, 20)
        self.assertIsNone(plan.get("planner"))

    @patch("services.ai_intent_parser.generate_text",
           return_value=_ohlcv_ai_json(fields="Close"))
    def test_string_fields_degrades_without_character_split(self, _mock):
        parsed, plan, ai_used = parse_with_ai_fallback("调出博通近20天的所有数据")
        self.assertFalse(ai_used)
        self.assertEqual(parsed.fields, [])
        self.assertNotEqual(parsed.fields, ["C", "l", "o", "s", "e"])
        self.assertIsNone(plan.get("planner"))

    @patch("services.ai_intent_parser.generate_text",
           return_value=_ohlcv_ai_json(symbols="AVGO"))
    def test_string_symbols_degrades_safely(self, _mock):
        parsed, plan, ai_used = parse_with_ai_fallback("调出博通近20天的所有数据")
        self.assertFalse(ai_used)
        self.assertEqual(parsed.symbols, ["AVGO"])
        self.assertIsNone(plan.get("planner"))

    @patch("services.ai_intent_parser.generate_text",
           return_value='{"intent": "query"}')
    def test_missing_required_fields_degrades_safely(self, _mock):
        parsed, plan, ai_used = parse_with_ai_fallback("调出博通近20天的所有数据")
        self.assertFalse(ai_used)
        self.assertEqual(parsed.fields, [])
        self.assertIsNone(plan.get("planner"))

    @patch("services.ai_intent_parser.generate_text",
           return_value=_ohlcv_ai_json(operation="rolling_average"))
    def test_unsupported_operation_degrades_safely(self, _mock):
        parsed, plan, ai_used = parse_with_ai_fallback("调出博通近20天的所有数据")
        self.assertFalse(ai_used)
        self.assertEqual(parsed.task_type, "query_data")

    @patch("services.ai_intent_parser.generate_text",
           return_value=_ohlcv_ai_json(confidence="certain"))
    def test_unsupported_confidence_degrades_safely(self, _mock):
        parsed, plan, ai_used = parse_with_ai_fallback("调出博通近20天的所有数据")
        self.assertFalse(ai_used)
        self.assertEqual(parsed.task_type, "query_data")


# ── integration: full 7 validation cases ─────────────────────────────────────

class TestValidationCases(unittest.TestCase):
    """
    Validates the 7 required test cases from tasks/037_ai_intent_parser_fallback_mvp.md.
    OpenAI is mocked for cases 1-2; real rule/plan handles cases 3-7.
    """

    @patch("services.ai_intent_parser.generate_text", return_value=_ohlcv_ai_json())
    def test_case_1_all_data_ohlcv(self, _mock):
        """调出博通近20天的所有数据 → query + OHLCV"""
        parsed, plan, ai_used = parse_with_ai_fallback("调出博通近20天的所有数据")
        self.assertTrue(ai_used)
        self.assertEqual(parsed.task_type, "query_data")
        self.assertEqual(set(parsed.fields), set(OHLCV_FIELDS))

    @patch("services.ai_intent_parser.generate_text", return_value=_ohlcv_ai_json())
    def test_case_2_ohlcv_keyword(self, _mock):
        """调出博通近20天 OHLCV 数据 → query + OHLCV"""
        parsed, plan, ai_used = parse_with_ai_fallback("调出博通近20天 OHLCV 数据")
        self.assertTrue(ai_used)
        self.assertEqual(parsed.task_type, "query_data")
        self.assertEqual(set(parsed.fields), set(OHLCV_FIELDS))

    def test_case_3_stats_volume(self):
        """博通今天和最近20天平均成交量比怎么样 → stats + today_vs_average + Volume"""
        parsed, plan, ai_used = parse_with_ai_fallback("博通今天和最近20天平均成交量比怎么样")
        self.assertFalse(ai_used)
        self.assertEqual(plan.get("primary_intent"), "stats")
        stats_steps = [s for s in plan.get("steps", []) if s.get("type") == "stats"]
        self.assertTrue(len(stats_steps) > 0)
        self.assertEqual(stats_steps[0].get("operation"), "today_vs_average")
        self.assertEqual(stats_steps[0].get("field"), "Volume")

    def test_case_4_stats_close(self):
        """博通今天收盘价和最近20天平均收盘价对比 → stats + today_vs_average + Close"""
        parsed, plan, ai_used = parse_with_ai_fallback("博通今天收盘价和最近20天平均收盘价对比")
        self.assertFalse(ai_used)
        self.assertEqual(plan.get("primary_intent"), "stats")
        stats_steps = [s for s in plan.get("steps", []) if s.get("type") == "stats"]
        self.assertTrue(len(stats_steps) > 0)
        self.assertEqual(stats_steps[0].get("field"), "Close")

    def test_case_5_compare(self):
        """比较一下博通和英伟达最近20天强弱 → compare"""
        parsed, plan, ai_used = parse_with_ai_fallback("比较一下博通和英伟达最近20天强弱")
        self.assertFalse(ai_used)
        self.assertIn(plan.get("primary_intent"), ("compare",))
        self.assertIn("AVGO", plan.get("symbols", []))
        self.assertIn("NVDA", plan.get("symbols", []))

    def test_case_6_projection(self):
        """帮我看看博通明天怎么样 → projection"""
        parsed, plan, ai_used = parse_with_ai_fallback("帮我看看博通明天怎么样")
        self.assertFalse(ai_used)
        self.assertEqual(plan.get("primary_intent"), "projection")

    def test_case_7_ai_explain(self):
        """用 AI 解释这次推演 → ai_explain (parsed as ai_explanation)"""
        parsed, plan, ai_used = parse_with_ai_fallback("用 AI 解释这次推演")
        self.assertFalse(ai_used)
        self.assertEqual(parsed.task_type, "ai_explanation")
        self.assertEqual(plan.get("primary_intent"), "ai_explain")


if __name__ == "__main__":
    unittest.main()
