"""Tests for services/ai_task_parser.py

Covers:
  - _validate_schema: structural checks (intent whitelist, required keys)
  - parse_task: JSON parsing, fence stripping, safe degradation
  - Year inference schema passthrough (semantic validation is in plan_normalizer)
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.ai_task_parser import SUPPORTED_INTENTS, _validate_schema, parse_task


# ── helpers ────────────────────────────────────────────────────────────────────

def _minimal_schema(**overrides) -> dict:
    base = {
        "intent": "query",
        "symbols": ["AVGO"],
        "time_range": {
            "type": "relative",
            "lookback_days": 20,
            "inferred": False,
            "confidence": 0.95,
            "raw_text": "最近20天",
        },
        "fields": ["Open", "High", "Low", "Close", "Volume"],
        "transforms": [],
        "constraints": [],
        "user_goal": "查询 AVGO 最近20天数据",
        "explanation": "用户想查看最近20天的博通数据",
        "confidence": 0.92,
    }
    base.update(overrides)
    return base


def _absolute_schema(*, inferred: bool = False, confidence: float = 0.9) -> dict:
    return _minimal_schema(
        intent="query",
        time_range={
            "type": "absolute",
            "start_date": "2026-02-05",
            "end_date": "2026-02-25",
            "inferred": inferred,
            "confidence": confidence,
            "raw_text": "2月5号至2月25号",
        },
    )


def _mock_generate(schema: dict):
    def _gen(*, input_text, instructions, **_kw):
        return json.dumps(schema, ensure_ascii=False)
    return _gen


# ── _validate_schema ───────────────────────────────────────────────────────────

class ValidateSchemaTests(unittest.TestCase):

    def test_valid_query_schema(self):
        self.assertIsNotNone(_validate_schema(_minimal_schema()))

    def test_valid_compare_schema(self):
        s = _minimal_schema(intent="compare", symbols=["AVGO", "NVDA"])
        self.assertIsNotNone(_validate_schema(s))

    def test_invalid_intent_returns_none(self):
        self.assertIsNone(_validate_schema(_minimal_schema(intent="buy_stock")))

    def test_not_a_dict_returns_none(self):
        self.assertIsNone(_validate_schema([]))  # type: ignore[arg-type]

    def test_symbols_not_list_returns_none(self):
        s = _minimal_schema()
        s["symbols"] = "AVGO"
        self.assertIsNone(_validate_schema(s))

    def test_time_range_not_dict_returns_none(self):
        s = _minimal_schema()
        s["time_range"] = "最近20天"
        self.assertIsNone(_validate_schema(s))

    def test_unknown_time_range_type_returns_none(self):
        s = _minimal_schema()
        s["time_range"] = {"type": "yesterday"}
        self.assertIsNone(_validate_schema(s))

    def test_fields_not_list_returns_none(self):
        s = _minimal_schema()
        s["fields"] = "Close"
        self.assertIsNone(_validate_schema(s))

    def test_all_supported_intents_pass(self):
        for intent in SUPPORTED_INTENTS:
            with self.subTest(intent=intent):
                s = _minimal_schema(intent=intent)
                self.assertIsNotNone(_validate_schema(s))

    def test_absolute_time_range_valid(self):
        self.assertIsNotNone(_validate_schema(_absolute_schema()))

    def test_absolute_inferred_valid(self):
        self.assertIsNotNone(_validate_schema(_absolute_schema(inferred=True, confidence=0.9)))

    def test_confidence_numeric_passes(self):
        s = _minimal_schema(confidence=0.5)
        self.assertIsNotNone(_validate_schema(s))

    def test_confidence_non_numeric_returns_none(self):
        s = _minimal_schema(confidence="high")
        self.assertIsNone(_validate_schema(s))


# ── parse_task ─────────────────────────────────────────────────────────────────

class ParseTaskTests(unittest.TestCase):

    def test_valid_response_returns_schema(self):
        schema = _minimal_schema()
        result = parse_task("调出博通最近20天", _today="2026-04-20", _generate=_mock_generate(schema))
        self.assertIsNotNone(result)
        self.assertEqual(result["intent"], "query")
        self.assertEqual(result["symbols"], ["AVGO"])

    def test_absolute_with_inferred_year_passes_through(self):
        schema = _absolute_schema(inferred=True, confidence=0.9)
        result = parse_task("2月5号至2月25号", _today="2026-04-20", _generate=_mock_generate(schema))
        self.assertIsNotNone(result)
        tr = result["time_range"]
        self.assertEqual(tr["type"], "absolute")
        self.assertTrue(tr["inferred"])
        self.assertAlmostEqual(tr["confidence"], 0.9)
        self.assertEqual(tr["start_date"], "2026-02-05")

    def test_json_parse_error_returns_none(self):
        def _bad_gen(*, input_text, instructions, **_kw):
            return "not json at all"
        result = parse_task("test", _generate=_bad_gen)
        self.assertIsNone(result)

    def test_markdown_fences_stripped(self):
        schema = _minimal_schema()
        json_str = json.dumps(schema, ensure_ascii=False)

        def _fenced_gen(*, input_text, instructions, **_kw):
            return f"```json\n{json_str}\n```"

        result = parse_task("test", _generate=_fenced_gen)
        self.assertIsNotNone(result)
        self.assertEqual(result["intent"], "query")

    def test_api_error_returns_none(self):
        from services.openai_client import OpenAIClientError

        def _error_gen(*, input_text, instructions, **_kw):
            raise OpenAIClientError("timeout")

        result = parse_task("test", _generate=_error_gen)
        self.assertIsNone(result)

    def test_unexpected_exception_returns_none(self):
        def _crash_gen(*, input_text, instructions, **_kw):
            raise RuntimeError("network is gone")

        result = parse_task("test", _generate=_crash_gen)
        self.assertIsNone(result)

    def test_unsupported_intent_in_response_returns_none(self):
        bad = _minimal_schema(intent="buy_stock")
        result = parse_task("test", _generate=_mock_generate(bad))
        self.assertIsNone(result)

    def test_next_trading_day_intent_passes(self):
        schema = _minimal_schema(
            intent="projection",
            time_range={"type": "next_trading_day", "inferred": False, "confidence": 1.0, "raw_text": "明天"},
        )
        result = parse_task("推演博通明天", _generate=_mock_generate(schema))
        self.assertIsNotNone(result)
        self.assertEqual(result["intent"], "projection")
        self.assertEqual(result["time_range"]["type"], "next_trading_day")

    def test_compare_intent_with_two_symbols(self):
        schema = _minimal_schema(intent="compare", symbols=["AVGO", "NVDA"])
        result = parse_task("比较博通和英伟达", _generate=_mock_generate(schema))
        self.assertIsNotNone(result)
        self.assertEqual(result["intent"], "compare")
        self.assertEqual(result["symbols"], ["AVGO", "NVDA"])


if __name__ == "__main__":
    unittest.main()
