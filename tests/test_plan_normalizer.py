"""Tests for services/plan_normalizer.py

Covers:
  - Intent → task_type mapping
  - Symbol validation and filtering
  - Field validation and filtering
  - Time range: absolute / relative / next_trading_day
  - Year inference: confidence threshold enforcement
  - Inverted date blocking
  - Step construction per intent
  - plan["supported"] and plan["warnings"] correctness
  - ParsedTask backward compat fields
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.plan_normalizer import INFERRED_CONFIDENCE_MIN, normalize
from services.command_parser import DEFAULT_WINDOW


# ── helpers ────────────────────────────────────────────────────────────────────

def _schema(
    *,
    intent: str = "query",
    symbols: list | None = None,
    fields: list | None = None,
    time_range: dict | None = None,
    user_goal: str = "test goal",
    explanation: str = "test explanation",
    confidence: float = 0.9,
) -> dict:
    return {
        "intent": intent,
        "symbols": symbols if symbols is not None else ["AVGO"],
        "fields": fields if fields is not None else ["Open", "High", "Low", "Close", "Volume"],
        "time_range": time_range or {
            "type": "relative",
            "lookback_days": 20,
            "inferred": False,
            "confidence": 1.0,
            "raw_text": "最近20天",
        },
        "transforms": [],
        "constraints": [],
        "user_goal": user_goal,
        "explanation": explanation,
        "confidence": confidence,
    }


def _abs_range(
    start: str = "2026-02-05",
    end: str = "2026-02-25",
    *,
    inferred: bool = False,
    confidence: float = 0.9,
    raw_text: str = "2月5号至2月25号",
) -> dict:
    return {
        "type": "absolute",
        "start_date": start,
        "end_date": end,
        "inferred": inferred,
        "confidence": confidence,
        "raw_text": raw_text,
    }


# ── basic intent + ParsedTask compat ──────────────────────────────────────────

class IntentMappingTests(unittest.TestCase):

    def test_query_maps_to_query_data(self):
        parsed, plan = normalize("test", _schema(intent="query"))
        self.assertEqual(parsed.task_type, "query_data")
        self.assertEqual(plan["primary_intent"], "query")

    def test_compare_maps_to_compare_data(self):
        parsed, plan = normalize("test", _schema(intent="compare", symbols=["AVGO", "NVDA"]))
        self.assertEqual(parsed.task_type, "compare_data")

    def test_filter_maps_to_query_data(self):
        parsed, plan = normalize("test", _schema(intent="filter"))
        self.assertEqual(parsed.task_type, "query_data")

    def test_projection_maps_to_run_projection(self):
        s = _schema(intent="projection", time_range={"type": "next_trading_day", "inferred": False, "confidence": 1.0, "raw_text": "明天"})
        parsed, plan = normalize("test", s)
        self.assertEqual(parsed.task_type, "run_projection")

    def test_unsupported_intent_returns_unsupported_plan(self):
        s = _schema(intent="buy_stock")
        parsed, plan = normalize("test", s)
        self.assertFalse(plan["supported"])
        self.assertEqual(plan["primary_intent"], "unsupported")
        self.assertIsNotNone(parsed.parse_error)

    def test_planner_tag_is_ai_primary(self):
        _, plan = normalize("test", _schema())
        self.assertEqual(plan["planner"], "ai_primary")


# ── symbol validation ──────────────────────────────────────────────────────────

class SymbolValidationTests(unittest.TestCase):

    def test_valid_symbols_pass_through(self):
        _, plan = normalize("test", _schema(symbols=["AVGO", "NVDA"]))
        self.assertIn("AVGO", plan["symbols"])
        self.assertIn("NVDA", plan["symbols"])

    def test_invalid_symbol_removed_with_warning(self):
        _, plan = normalize("test", _schema(symbols=["AVGO", "TSLA"]))
        self.assertNotIn("TSLA", plan["symbols"])
        self.assertTrue(any("TSLA" in w for w in plan["warnings"]))

    def test_lowercase_symbol_uppercased(self):
        _, plan = normalize("test", _schema(symbols=["avgo"]))
        self.assertIn("AVGO", plan["symbols"])

    def test_no_symbols_blocks_query(self):
        _, plan = normalize("test", _schema(intent="query", symbols=[]))
        self.assertFalse(plan["supported"])
        self.assertTrue(any("标的" in w for w in plan["warnings"]))

    def test_one_symbol_blocks_compare(self):
        _, plan = normalize("test", _schema(intent="compare", symbols=["AVGO"]))
        self.assertFalse(plan["supported"])
        self.assertTrue(any("两个标的" in w for w in plan["warnings"]))


# ── field validation ──────────────────────────────────────────────────────────

class FieldValidationTests(unittest.TestCase):

    def test_valid_fields_pass(self):
        _, plan = normalize("test", _schema(fields=["Open", "Close"]))
        self.assertIn("Open", plan["fields"])

    def test_invalid_field_removed_with_warning(self):
        _, plan = normalize("test", _schema(fields=["Close", "MarketCap"]))
        self.assertNotIn("MarketCap", plan["fields"])
        self.assertTrue(any("MarketCap" in w for w in plan["warnings"]))

    def test_derived_fields_accepted(self):
        _, plan = normalize("test", _schema(fields=["Pos30", "PosLabel", "StageLabel"]))
        self.assertIn("Pos30", plan["fields"])
        self.assertIn("PosLabel", plan["fields"])


# ── time range: relative ───────────────────────────────────────────────────────

class RelativeTimeRangeTests(unittest.TestCase):

    def test_relative_lookback_days_passed_through(self):
        s = _schema(time_range={"type": "relative", "lookback_days": 30, "inferred": False, "confidence": 1.0, "raw_text": "最近30天"})
        parsed, plan = normalize("test", s)
        self.assertEqual(plan["lookback_days"], 30)
        self.assertEqual(parsed.window, 30)

    def test_default_window_when_lookback_missing(self):
        s = _schema(time_range={"type": "relative", "inferred": False, "confidence": 1.0, "raw_text": ""})
        _, plan = normalize("test", s)
        self.assertEqual(plan["lookback_days"], DEFAULT_WINDOW)

    def test_relative_plan_has_no_dates(self):
        _, plan = normalize("test", _schema())
        self.assertNotIn("start_date", plan)
        self.assertNotIn("end_date", plan)


# ── time range: absolute ───────────────────────────────────────────────────────

class AbsoluteTimeRangeTests(unittest.TestCase):

    def test_absolute_dates_land_in_plan(self):
        s = _schema(time_range=_abs_range())
        _, plan = normalize("test", s)
        self.assertEqual(plan.get("start_date"), "2026-02-05")
        self.assertEqual(plan.get("end_date"), "2026-02-25")

    def test_absolute_dates_land_in_query_step(self):
        s = _schema(time_range=_abs_range())
        _, plan = normalize("test", s)
        step = next(s for s in plan["steps"] if s["type"] == "query")
        self.assertEqual(step.get("start_date"), "2026-02-05")
        self.assertEqual(step.get("end_date"), "2026-02-25")

    def test_absolute_plan_supported(self):
        s = _schema(time_range=_abs_range())
        _, plan = normalize("test", s)
        self.assertTrue(plan["supported"])

    def test_inverted_dates_block_plan(self):
        s = _schema(time_range=_abs_range(start="2026-03-01", end="2026-01-01"))
        _, plan = normalize("test", s)
        self.assertFalse(plan["supported"])
        self.assertTrue(any("晚于" in w for w in plan["warnings"]))
        self.assertNotIn("start_date", plan)

    def test_missing_start_date_blocks(self):
        s = _schema(time_range={"type": "absolute", "end_date": "2026-02-25", "inferred": False, "confidence": 1.0, "raw_text": ""})
        _, plan = normalize("test", s)
        self.assertFalse(plan["supported"])


# ── year inference confidence ──────────────────────────────────────────────────

class InferredDateTests(unittest.TestCase):

    def test_high_confidence_inferred_adds_warning_but_proceeds(self):
        s = _schema(time_range=_abs_range(inferred=True, confidence=0.9))
        _, plan = normalize("test", s)
        self.assertTrue(plan["supported"])
        self.assertTrue(any("推断" in w for w in plan["warnings"]))
        self.assertEqual(plan.get("start_date"), "2026-02-05")

    def test_confidence_exactly_at_threshold_proceeds(self):
        s = _schema(time_range=_abs_range(inferred=True, confidence=INFERRED_CONFIDENCE_MIN))
        _, plan = normalize("test", s)
        self.assertTrue(plan["supported"])

    def test_low_confidence_inferred_blocks(self):
        low = INFERRED_CONFIDENCE_MIN - 0.01
        s = _schema(time_range=_abs_range(inferred=True, confidence=low))
        _, plan = normalize("test", s)
        self.assertFalse(plan["supported"])
        self.assertTrue(any("置信度" in w for w in plan["warnings"]))

    def test_not_inferred_no_confidence_warning(self):
        s = _schema(time_range=_abs_range(inferred=False, confidence=0.99))
        _, plan = normalize("test", s)
        self.assertTrue(plan["supported"])
        self.assertFalse(any("推断" in w for w in plan["warnings"]))


# ── step construction ──────────────────────────────────────────────────────────

class StepConstructionTests(unittest.TestCase):

    def test_query_step_has_symbols_and_fields(self):
        _, plan = normalize("test", _schema(intent="query"))
        self.assertEqual(len(plan["steps"]), 1)
        step = plan["steps"][0]
        self.assertEqual(step["type"], "query")
        self.assertIn("AVGO", step["symbols"])

    def test_compare_step_type(self):
        s = _schema(intent="compare", symbols=["AVGO", "NVDA"])
        _, plan = normalize("test", s)
        self.assertEqual(plan["steps"][0]["type"], "compare")

    def test_projection_step_type(self):
        s = _schema(intent="projection", symbols=["AVGO"],
                    time_range={"type": "next_trading_day", "inferred": False, "confidence": 1.0, "raw_text": "明天"})
        _, plan = normalize("test", s)
        self.assertEqual(plan["steps"][0]["type"], "projection")

    def test_projection_defaults_to_avgo_when_no_symbol(self):
        s = _schema(intent="projection", symbols=[],
                    time_range={"type": "next_trading_day", "inferred": False, "confidence": 1.0, "raw_text": "明天"})
        _, plan = normalize("test", s)
        self.assertIn("AVGO", plan["steps"][0]["symbols"])


# ── AI metadata in plan ────────────────────────────────────────────────────────

class AiMetadataTests(unittest.TestCase):

    def test_user_goal_in_plan(self):
        s = _schema(user_goal="查看博通近期走势")
        _, plan = normalize("test", s)
        self.assertEqual(plan["user_goal"], "查看博通近期走势")

    def test_explanation_in_plan(self):
        s = _schema(explanation="用户想了解最近数据")
        _, plan = normalize("test", s)
        self.assertEqual(plan["explanation"], "用户想了解最近数据")

    def test_ai_confidence_in_plan(self):
        s = _schema(confidence=0.88)
        _, plan = normalize("test", s)
        self.assertAlmostEqual(plan["ai_confidence"], 0.88)

    def test_ai_schema_stored_in_plan(self):
        s = _schema()
        _, plan = normalize("test", s)
        self.assertIn("ai_schema", plan)
        self.assertEqual(plan["ai_schema"]["intent"], "query")


# ── full hao-date integration through normalizer ──────────────────────────────

class HaoDateNormalizerTests(unittest.TestCase):
    """Simulates what happens when AI correctly infers year for '2月5号至2月25号'."""

    def test_inferred_hao_date_supported_with_warning(self):
        s = _schema(time_range=_abs_range(
            start="2026-02-05", end="2026-02-25",
            inferred=True, confidence=0.9,
            raw_text="2月5号至2月25号",
        ))
        _, plan = normalize("调出博通2月5号至2月25号的数据", s)
        self.assertTrue(plan["supported"])
        self.assertEqual(plan["start_date"], "2026-02-05")
        self.assertEqual(plan["end_date"], "2026-02-25")
        self.assertTrue(any("推断" in w for w in plan["warnings"]))

    def test_low_confidence_hao_date_blocked(self):
        s = _schema(time_range=_abs_range(
            inferred=True, confidence=0.50,
            raw_text="2月5号至2月25号",
        ))
        _, plan = normalize("调出博通2月5号至2月25号的数据", s)
        self.assertFalse(plan["supported"])
        self.assertNotIn("start_date", plan)


if __name__ == "__main__":
    unittest.main()
