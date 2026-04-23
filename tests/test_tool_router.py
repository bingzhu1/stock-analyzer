"""Tests for services/tool_router.py — Task 033 multi-step tool router MVP."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.tool_router import (
    STATUS_FAILED,
    STATUS_PLANNED,
    STATUS_SKIPPED,
    STATUS_SUCCESS,
    route_plan,
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _fake_loader(symbol: str, window: int = 20, fields=None) -> pd.DataFrame:
    """Return a minimal fake DataFrame with Volume and Close columns."""
    n = window + 1
    data = {
        "Date":   [f"2026-01-{i+1:02d}" for i in range(n)],
        "Volume": [float(1_000_000 + i * 10_000) for i in range(n)],
        "Close":  [float(700 + i) for i in range(n)],
    }
    df = pd.DataFrame(data)
    if fields:
        cols = ["Date"] + [f for f in fields if f in df.columns]
        return df[cols]
    return df


def _fake_aligned_loader(symbols, window=20, fields=None) -> pd.DataFrame:
    """Return a fake aligned DataFrame with prefixed columns."""
    n = window
    dates = [f"2026-01-{i+1:02d}" for i in range(n)]
    result = pd.DataFrame({"Date": dates})
    for sym in symbols:
        result[f"{sym}_Close"] = [float(700 + i) for i in range(n)]
        result[f"{sym}_Volume"] = [float(1_000_000 + i * 5_000) for i in range(n)]
    return result


def _fake_projection_runner(symbol="AVGO", lookback_days=20) -> dict:
    return {
        "ready": True,
        "projection_report": {
            "kind": "final_projection_report",
            "direction": "偏多",
            "confidence": "medium",
        },
        "advisory": {"matched_count": 3, "caution_level": "low", "reminder_lines": []},
        "request": {"symbol": symbol},
    }


def _query_plan(symbol="AVGO", field="Volume", lookback=20) -> dict:
    return {
        "kind": "intent_plan",
        "raw_text": f"查询 {symbol}",
        "supported": True,
        "primary_intent": "query",
        "steps": [
            {"type": "query", "symbols": [symbol], "fields": [field], "lookback_days": lookback}
        ],
        "ai_followups": [],
        "warnings": [],
    }


def _compare_plan(symbols=("AVGO", "NVDA"), lookback=20, missing=False) -> dict:
    return {
        "kind": "intent_plan",
        "raw_text": "compare",
        "supported": not missing,
        "primary_intent": "compare",
        "steps": [
            {
                "type": "compare",
                "symbols": list(symbols),
                "fields": ["Close"],
                "lookback_days": lookback,
                "missing_second_symbol": missing,
            }
        ],
        "ai_followups": [],
        "warnings": ["比较指令只识别到一个标的，请补充第二个标的。"] if missing else [],
    }


def _projection_plan(symbol="AVGO", lookback=20, with_ai=False, ai_type="ai_explain_risk") -> dict:
    ai_followups = []
    if with_ai:
        ai_followups = [{"type": ai_type, "available": True, "requires_openai_api_key": False}]
    return {
        "kind": "intent_plan",
        "raw_text": "projection plan",
        "supported": True,
        "primary_intent": "projection",
        "steps": [
            {"type": "projection", "symbols": [symbol], "lookback_days": lookback}
        ],
        "ai_followups": ai_followups,
        "warnings": [],
    }


def _stats_plan(symbol="AVGO", field="Volume", lookback=20) -> dict:
    return {
        "kind": "intent_plan",
        "raw_text": "stats plan",
        "supported": True,
        "primary_intent": "stats",
        "steps": [
            {
                "type": "stats",
                "symbol": symbol,
                "field": field,
                "lookback_days": lookback,
                "operation": "today_vs_average",
            }
        ],
        "ai_followups": [],
        "warnings": [],
    }


def _unsupported_plan() -> dict:
    return {
        "kind": "intent_plan",
        "raw_text": "午饭",
        "supported": False,
        "primary_intent": "unsupported",
        "steps": [],
        "ai_followups": [],
        "warnings": ["暂未识别到计划。"],
    }


# ── tests ─────────────────────────────────────────────────────────────────────

class UnsupportedPlanTests(unittest.TestCase):
    def test_unsupported_plan_returns_no_steps(self) -> None:
        result = route_plan(_unsupported_plan())
        self.assertEqual(result["steps_executed"], [])
        self.assertIsNone(result["primary_result"])

    def test_unsupported_plan_preserves_warnings(self) -> None:
        result = route_plan(_unsupported_plan())
        self.assertTrue(result["warnings"])

    def test_result_has_required_keys(self) -> None:
        result = route_plan(_unsupported_plan())
        for key in ("plan", "steps_executed", "primary_result", "aux_results", "session_ctx", "warnings"):
            self.assertIn(key, result)


class QueryStepTests(unittest.TestCase):
    def test_query_single_step_success(self) -> None:
        result = route_plan(_query_plan(), _loader=_fake_loader)
        self.assertEqual(len(result["steps_executed"]), 1)
        step = result["steps_executed"][0]
        self.assertEqual(step["status"], STATUS_SUCCESS)
        self.assertEqual(step["type"], "query")

    def test_query_result_in_primary(self) -> None:
        result = route_plan(_query_plan(), _loader=_fake_loader)
        self.assertIsNotNone(result["primary_result"])
        self.assertEqual(result["primary_result"]["type"], "query")

    def test_query_result_in_session_ctx(self) -> None:
        result = route_plan(_query_plan(), _loader=_fake_loader)
        self.assertIsNotNone(result["session_ctx"].get("latest_query_result"))

    def test_query_loader_failure_is_failed_status(self) -> None:
        def bad_loader(*a, **kw):
            raise FileNotFoundError("no csv")

        result = route_plan(_query_plan(), _loader=bad_loader)
        step = result["steps_executed"][0]
        self.assertEqual(step["status"], STATUS_FAILED)
        self.assertIn("查询失败", step.get("error", ""))

    def test_query_no_symbols_is_failed(self) -> None:
        plan = _query_plan()
        plan["steps"][0]["symbols"] = []
        result = route_plan(plan, _loader=_fake_loader)
        step = result["steps_executed"][0]
        self.assertEqual(step["status"], STATUS_FAILED)


class CompareStepTests(unittest.TestCase):
    def test_compare_two_symbols_success(self) -> None:
        result = route_plan(
            _compare_plan(["AVGO", "NVDA"]),
            _aligned_loader=_fake_aligned_loader,
        )
        step = result["steps_executed"][0]
        self.assertEqual(step["status"], STATUS_SUCCESS)

    def test_compare_result_in_session_ctx(self) -> None:
        result = route_plan(
            _compare_plan(["AVGO", "NVDA"]),
            _aligned_loader=_fake_aligned_loader,
        )
        self.assertIsNotNone(result["session_ctx"].get("latest_compare_result"))

    def test_compare_missing_second_symbol_is_skipped(self) -> None:
        plan = _compare_plan(["AVGO"], missing=True)
        # Force supported=True so we reach step execution
        plan["supported"] = True
        result = route_plan(plan, _aligned_loader=_fake_aligned_loader)
        step = result["steps_executed"][0]
        self.assertEqual(step["status"], STATUS_SKIPPED)
        self.assertIn("第二标的", step.get("warning", ""))

    def test_compare_missing_second_symbol_no_execution(self) -> None:
        plan = _compare_plan(["AVGO"], missing=True)
        plan["supported"] = True
        result = route_plan(plan, _aligned_loader=_fake_aligned_loader)
        self.assertIsNone(result["session_ctx"].get("latest_compare_result"))


class ProjectionStepTests(unittest.TestCase):
    def test_projection_success(self) -> None:
        result = route_plan(_projection_plan(), _projection_runner=_fake_projection_runner)
        step = result["steps_executed"][0]
        self.assertEqual(step["status"], STATUS_SUCCESS)
        self.assertEqual(result["primary_result"]["type"], "projection")

    def test_projection_result_in_session_ctx(self) -> None:
        result = route_plan(_projection_plan(), _projection_runner=_fake_projection_runner)
        self.assertIsNotNone(result["session_ctx"].get("latest_projection_result"))

    def test_projection_failure_is_failed_status(self) -> None:
        def bad_runner(**kw):
            raise RuntimeError("db unavailable")

        result = route_plan(_projection_plan(), _projection_runner=bad_runner)
        step = result["steps_executed"][0]
        self.assertEqual(step["status"], STATUS_FAILED)
        self.assertIn("推演执行失败", step.get("error", ""))


class StatsStepTests(unittest.TestCase):
    def test_stats_today_vs_average_success(self) -> None:
        result = route_plan(_stats_plan(), _loader=_fake_loader)
        step = result["steps_executed"][0]
        self.assertEqual(step["status"], STATUS_SUCCESS)
        self.assertEqual(result["primary_result"]["type"], "stats")

    def test_stats_result_shape(self) -> None:
        result = route_plan(_stats_plan(), _loader=_fake_loader)
        data = result["primary_result"]["data"]
        for key in ("symbol", "field", "today_value", "average_value", "absolute_diff", "pct_diff", "raw_table"):
            self.assertIn(key, data)
        self.assertIn("Date", data["raw_table"].columns)
        self.assertIn("Volume", data["raw_table"].columns)

    def test_stats_today_vs_average_in_session_ctx(self) -> None:
        result = route_plan(_stats_plan(), _loader=_fake_loader)
        self.assertIsNotNone(result["session_ctx"].get("latest_stats_result"))

    def test_stats_unsupported_operation_is_planned_only(self) -> None:
        plan = _stats_plan()
        plan["steps"][0]["operation"] = "custom_op"
        result = route_plan(plan, _loader=_fake_loader)
        step = result["steps_executed"][0]
        self.assertEqual(step["status"], STATUS_PLANNED)

    def test_stats_loader_failure_is_failed(self) -> None:
        def bad_loader(*a, **kw):
            raise FileNotFoundError("no csv")

        result = route_plan(_stats_plan(), _loader=bad_loader)
        step = result["steps_executed"][0]
        self.assertEqual(step["status"], STATUS_FAILED)


class AIFollowupTests(unittest.TestCase):
    def test_ai_followup_skipped_without_openai_key(self) -> None:
        plan = _projection_plan(with_ai=True, ai_type="ai_explain_risk")
        plan["ai_followups"][0]["available"] = False

        result = route_plan(plan, _projection_runner=_fake_projection_runner)
        # projection step + ai step
        self.assertEqual(len(result["steps_executed"]), 2)
        ai_step = result["steps_executed"][1]
        self.assertEqual(ai_step["status"], STATUS_SKIPPED)

    def test_ai_followup_succeeds_with_mock_builder(self) -> None:
        plan = _projection_plan(with_ai=True, ai_type="ai_explain_risk")
        plan["ai_followups"][0]["available"] = True

        fake_risk_builder = lambda payload: "风险解释文本"

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            result = route_plan(
                plan,
                _projection_runner=_fake_projection_runner,
                _risk_ai_builder=fake_risk_builder,
            )
        ai_step = result["steps_executed"][1]
        self.assertEqual(ai_step["status"], STATUS_SUCCESS)
        self.assertEqual(result["session_ctx"].get("latest_ai_explanation"), "风险解释文本")
        self.assertEqual(result["aux_results"].get("ai_explanation"), "风险解释文本")

    def test_ai_followup_skipped_when_no_projection_context(self) -> None:
        plan = _projection_plan(with_ai=True, ai_type="ai_explain_projection")
        plan["ai_followups"][0]["available"] = True
        # Provide empty session_ctx so there's no prior projection result
        # and the projection step itself fails
        def bad_runner(**kw):
            raise RuntimeError("no data")

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            result = route_plan(plan, _projection_runner=bad_runner)

        ai_step = result["steps_executed"][1]
        self.assertEqual(ai_step["status"], STATUS_SKIPPED)
        self.assertIn("未找到", ai_step.get("error", ""))

    def test_ai_explain_compare_without_context_skipped(self) -> None:
        plan = {
            "kind": "intent_plan",
            "raw_text": "explain compare",
            "supported": True,
            "primary_intent": "compare",
            "steps": [
                {
                    "type": "compare",
                    "symbols": ["AVGO", "NVDA"],
                    "fields": ["Close"],
                    "lookback_days": 20,
                }
            ],
            "ai_followups": [
                {"type": "ai_explain_compare", "available": True}
            ],
            "warnings": [],
        }
        # Compare fails → AI has no context
        def bad_aligned(*a, **kw):
            raise RuntimeError("no data")

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            result = route_plan(plan, _aligned_loader=bad_aligned)

        ai_step = result["steps_executed"][1]
        self.assertEqual(ai_step["status"], STATUS_SKIPPED)
        self.assertIn("未找到", ai_step.get("error", ""))


class SessionContextTests(unittest.TestCase):
    def test_session_ctx_accumulates_across_steps(self) -> None:
        """Multi-step plan: both projection and compare populate session_ctx."""
        plan = {
            "kind": "intent_plan",
            "raw_text": "projection + compare",
            "supported": True,
            "primary_intent": "projection",
            "steps": [
                {"type": "projection", "symbols": ["AVGO"], "lookback_days": 20},
                {
                    "type": "compare",
                    "symbols": ["AVGO", "NVDA"],
                    "fields": ["Close"],
                    "lookback_days": 20,
                    "optional": True,
                },
            ],
            "ai_followups": [],
            "warnings": [],
        }
        result = route_plan(
            plan,
            _projection_runner=_fake_projection_runner,
            _aligned_loader=_fake_aligned_loader,
        )
        ctx = result["session_ctx"]
        self.assertIsNotNone(ctx.get("latest_projection_result"))
        self.assertIsNotNone(ctx.get("latest_compare_result"))

    def test_prior_ctx_carries_into_ai_followup(self) -> None:
        """AI follow-up can use a projection result from prior session_ctx."""
        plan = _projection_plan(with_ai=True, ai_type="ai_explain_projection")
        plan["steps"] = []  # No projection step in this plan
        plan["ai_followups"][0]["available"] = True

        prior_ctx = {
            "latest_projection_result": _fake_projection_runner(),
        }
        called = []

        def fake_proj_builder(payload):
            called.append(payload)
            return "推演解释"

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            result = route_plan(
                plan,
                session_ctx=prior_ctx,
                _proj_ai_builder=fake_proj_builder,
            )
        self.assertTrue(called)
        ai_step = result["steps_executed"][0]
        self.assertEqual(ai_step["status"], STATUS_SUCCESS)

    def test_optional_step_failure_does_not_propagate_warning(self) -> None:
        """Optional step failures should not add to top-level warnings."""
        plan = {
            "kind": "intent_plan",
            "raw_text": "projection + optional compare",
            "supported": True,
            "primary_intent": "projection",
            "steps": [
                {"type": "projection", "symbols": ["AVGO"], "lookback_days": 20},
                {
                    "type": "compare",
                    "symbols": ["AVGO", "NVDA"],
                    "fields": ["Close"],
                    "lookback_days": 20,
                    "optional": True,
                },
            ],
            "ai_followups": [],
            "warnings": [],
        }

        def bad_aligned(*a, **kw):
            raise RuntimeError("no data")

        result = route_plan(
            plan,
            _projection_runner=_fake_projection_runner,
            _aligned_loader=bad_aligned,
        )
        compare_step = result["steps_executed"][1]
        self.assertEqual(compare_step["status"], STATUS_SKIPPED)
        # Optional failures should not appear in top-level warnings
        self.assertFalse(any("数据对比失败" in w for w in result["warnings"]))


if __name__ == "__main__":
    unittest.main()
