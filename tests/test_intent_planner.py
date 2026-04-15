from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.intent_planner import plan_intent


class IntentPlannerTests(unittest.TestCase):
    # ── existing regression tests ─────────────────────────────────────────────

    def test_freeform_projection_plan(self) -> None:
        plan = plan_intent("帮我看看博通明天怎么样")

        self.assertTrue(plan["supported"])
        self.assertEqual(plan["primary_intent"], "projection")
        self.assertEqual(plan["symbols"], ["AVGO"])
        self.assertEqual(plan["lookback_days"], 20)
        self.assertEqual(plan["steps"][0]["type"], "projection")
        self.assertEqual(plan["steps"][0]["symbols"], ["AVGO"])
        self.assertTrue(any(step["type"] == "compare" and step.get("optional") for step in plan["steps"]))

    def test_freeform_compare_then_projection_plan(self) -> None:
        plan = plan_intent("比较一下博通和英伟达最近20天强弱，再告诉我明天怎么看")

        self.assertTrue(plan["supported"])
        self.assertEqual(plan["primary_intent"], "compare")
        self.assertEqual(plan["steps"][0]["type"], "compare")
        # Extraction order depends on token length, not text position; use set check.
        self.assertCountEqual(plan["steps"][0]["symbols"], ["AVGO", "NVDA"])
        self.assertEqual(plan["steps"][0]["lookback_days"], 20)
        self.assertEqual(plan["steps"][1]["type"], "projection")
        self.assertIn(plan["steps"][1]["symbols"][0], ["AVGO", "NVDA"])

    def test_freeform_query_plan(self) -> None:
        plan = plan_intent("只看博通最近20天成交量")

        self.assertTrue(plan["supported"])
        self.assertEqual(plan["primary_intent"], "query")
        self.assertEqual(plan["steps"][0]["type"], "query")
        self.assertEqual(plan["steps"][0]["symbols"], ["AVGO"])
        self.assertEqual(plan["steps"][0]["fields"], ["Volume"])
        self.assertEqual(plan["steps"][0]["lookback_days"], 20)

    def test_projection_with_ai_risk_followup_marks_unavailable_without_key(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            plan = plan_intent("先做推演，再用 AI 解释风险")

        self.assertTrue(plan["supported"])
        self.assertEqual(plan["primary_intent"], "projection")
        self.assertEqual(plan["steps"][0]["type"], "projection")
        self.assertEqual(plan["ai_followups"][0]["type"], "ai_explain_risk")
        self.assertFalse(plan["ai_followups"][0]["available"])
        self.assertTrue(plan["ai_followups"][0]["requires_openai_api_key"])

    def test_projection_with_ai_followup_marks_available_with_key(self) -> None:
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True):
            plan = plan_intent("先做推演，再用 AI 解释风险")

        self.assertTrue(plan["ai_followups"][0]["available"])
        self.assertFalse(plan["ai_followups"][0]["requires_openai_api_key"])

    def test_unsupported_input_degrades_safely(self) -> None:
        plan = plan_intent("今天午饭吃什么")

        self.assertFalse(plan["supported"])
        self.assertEqual(plan["primary_intent"], "unsupported")
        self.assertEqual(plan["steps"], [])
        self.assertTrue(plan["warnings"])

    # ── Task 032: stats today_vs_average ──────────────────────────────────────

    def test_stats_today_vs_average_volume(self) -> None:
        """博通今天 vs 近20天平均成交量 → stats, not projection/compare."""
        plan = plan_intent("博通今天和最近20天平均成交量比怎么样")

        self.assertTrue(plan["supported"])
        self.assertEqual(plan["primary_intent"], "stats")
        step = plan["steps"][0]
        self.assertEqual(step["type"], "stats")
        self.assertEqual(step["symbol"], "AVGO")
        self.assertEqual(step["field"], "Volume")
        self.assertEqual(step["lookback_days"], 20)
        self.assertEqual(step["operation"], "today_vs_average")

    def test_stats_today_vs_average_not_projection(self) -> None:
        """Input with '今天' + average signal must NOT be classified as projection."""
        plan = plan_intent("博通今天成交量比最近20天均量高多少")

        self.assertEqual(plan["primary_intent"], "stats")
        self.assertNotEqual(plan["primary_intent"], "projection")
        self.assertNotEqual(plan["primary_intent"], "compare")
        self.assertTrue(plan["supported"])
        self.assertEqual(plan["steps"][0]["operation"], "today_vs_average")

    def test_stats_today_vs_average_close(self) -> None:
        """'今天' + '平均收盘价' → stats with Close field."""
        plan = plan_intent("博通今天收盘价和最近20天平均收盘价对比")

        self.assertEqual(plan["primary_intent"], "stats")
        step = plan["steps"][0]
        self.assertEqual(step["type"], "stats")
        self.assertEqual(step["symbol"], "AVGO")
        self.assertEqual(step["field"], "Close")
        self.assertEqual(step["operation"], "today_vs_average")

    # ── Task 032: compare single-symbol must not auto-add NVDA ───────────────

    def test_compare_single_symbol_no_auto_nvda(self) -> None:
        """Single-symbol compare input must not auto-append NVDA."""
        plan = plan_intent("比较博通最近20天最高价走势")

        self.assertFalse(plan["supported"])
        self.assertEqual(plan["primary_intent"], "compare")
        step_symbols = plan["steps"][0]["symbols"]
        self.assertNotIn("NVDA", step_symbols)
        self.assertEqual(step_symbols, ["AVGO"])
        self.assertTrue(plan["steps"][0].get("missing_second_symbol"))

    def test_compare_single_symbol_has_friendly_warning(self) -> None:
        """Single-symbol compare should surface a human-readable warning."""
        plan = plan_intent("比较博通走势")

        self.assertFalse(plan["supported"])
        self.assertTrue(any("第二个标的" in w for w in plan["warnings"]))

    def test_compare_two_symbols_supported(self) -> None:
        """Two-symbol compare must remain supported and not add missing_second_symbol."""
        plan = plan_intent("比较博通和英伟达最近20天强弱")

        self.assertTrue(plan["supported"])
        self.assertEqual(plan["primary_intent"], "compare")
        step = plan["steps"][0]
        self.assertIn("AVGO", step["symbols"])
        self.assertIn("NVDA", step["symbols"])
        self.assertFalse(step.get("missing_second_symbol", False))

    # ── Task 032: unsupported graceful fallback ───────────────────────────────

    def test_empty_input_degrades_safely(self) -> None:
        plan = plan_intent("")

        self.assertFalse(plan["supported"])
        self.assertEqual(plan["primary_intent"], "unsupported")
        self.assertEqual(plan["steps"], [])

    def test_unsupported_has_kind_field(self) -> None:
        plan = plan_intent("随便说说")

        self.assertEqual(plan["kind"], "intent_plan")
        self.assertFalse(plan["supported"])


if __name__ == "__main__":
    unittest.main()
