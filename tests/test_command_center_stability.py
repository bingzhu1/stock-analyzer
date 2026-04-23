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

import inspect
import sys
import textwrap
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.command_parser import ParsedTask, parse_command
from ui.command_bar import (
    _PROJECTION_ERROR_NO_SYMBOL,
    _RESPONSE_CARD_SECTION_HEADINGS,
    _SS_COMPARE_RESULT,
    _SS_LAST_INPUT,
    _SS_LAST_COMP_CTX,
    _SS_LAST_PROJ_CTX,
    _SS_PARSED,
    _SS_PLAN,
    _SS_PROJ_ERROR,
    _SS_PROJ_RESULT,
    _SS_ROUTER_RESULT,
    _build_compare_response_card,
    _build_projection_response_card,
    _build_query_response_card,
    _build_stats_response_card,
    _render_intent_plan,
    _render_projection_result,
    _render_response_card,
    _render_stored_result,
    _sync_router_to_session,
    run_ai_explanation_command,
    run_projection_command,
)
from services.intent_planner import plan_intent

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


class _FakeColumn:
    def __init__(self, fake_st: "_FakeStreamlit") -> None:
        self._fake_st = fake_st

    def __enter__(self) -> "_FakeStreamlit":
        return self._fake_st

    def __exit__(self, *_: object) -> None:
        return None


class _FakeContainer:
    def __enter__(self) -> "_FakeContainer":
        return self

    def __exit__(self, *_: object) -> None:
        return None


class _FakeExpander:
    def __init__(self, fake_st: "_FakeStreamlit") -> None:
        self._fake_st = fake_st

    def __enter__(self) -> "_FakeStreamlit":
        self._fake_st.in_expander += 1
        self._fake_st.max_expander_depth = max(
            self._fake_st.max_expander_depth,
            self._fake_st.in_expander,
        )
        return self._fake_st

    def __exit__(self, *_: object) -> None:
        self._fake_st.in_expander -= 1
        return None


class _FakeStreamlit:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.in_expander = 0
        self.max_expander_depth = 0
        self.session_state: dict[str, object] = {}

    def info(self, text: str) -> None:
        self.calls.append(f"info:{text}")

    def success(self, text: str) -> None:
        self.calls.append(f"success:{text}")

    def error(self, text: str) -> None:
        self.calls.append(f"error:{text}")

    def columns(self, count: int) -> list[_FakeColumn]:
        self.calls.append(f"columns:{count}")
        return [_FakeColumn(self) for _ in range(count)]

    def metric(self, label: str, value: object) -> None:
        self.calls.append(f"metric:{label}:{value}")

    def markdown(self, text: str) -> None:
        self.calls.append(f"markdown:{text}")

    def write(self, text: object) -> None:
        self.calls.append(f"write:{text}")

    def caption(self, text: str) -> None:
        self.calls.append(f"caption:{text}")

    def dataframe(self, value: object, **_: object) -> None:
        where = "expander" if self.in_expander else "main"
        self.calls.append(f"dataframe:{where}")

    def warning(self, text: str) -> None:
        self.calls.append(f"warning:{text}")

    def container(self) -> _FakeContainer:
        self.calls.append("container")
        return _FakeContainer()

    def json(self, value: object) -> None:
        self.calls.append("json")

    def expander(self, label: str, **__: object) -> _FakeExpander:
        self.calls.append(f"expander:{label}")
        return _FakeExpander(self)


def _section_headings(fake_st: _FakeStreamlit) -> list[str]:
    headings = []
    for call in fake_st.calls:
        if not call.startswith("markdown:**"):
            continue
        text = call.removeprefix("markdown:**").removesuffix("**")
        if text in _RESPONSE_CARD_SECTION_HEADINGS:
            headings.append(text)
    return headings


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
        keys = [
            _SS_PARSED,
            _SS_PROJ_RESULT,
            _SS_PROJ_ERROR,
            _SS_LAST_INPUT,
            _SS_LAST_PROJ_CTX,
            _SS_LAST_COMP_CTX,
        ]
        self.assertEqual(len(keys), len(set(keys)))


class CommandResultIsolationTests(unittest.TestCase):
    def test_sync_does_not_rehydrate_prior_compare_context_for_stats(self) -> None:
        from ui import command_bar

        fake_st = _FakeStreamlit()
        old_compare = {
            "symbols": ["NVDA", "AVGO"],
            "field": "Close",
            "stats": {"total": 20, "matched": 10, "mismatched": 10, "match_rate": 50.0},
        }
        stats_data = {
            "symbol": "AVGO",
            "field": "Close",
            "lookback_days": 20,
            "operation": "today_vs_average",
            "today_value": 730.0,
            "average_value": 720.0,
            "absolute_diff": 10.0,
            "pct_diff": 1.39,
        }
        router_result = {
            "steps_executed": [
                {"step": 1, "type": "stats", "status": "success", "result": stats_data},
            ],
            "primary_result": {"type": "stats", "data": stats_data},
            "session_ctx": {
                "latest_compare_result": old_compare,
                "latest_stats_result": stats_data,
            },
            "warnings": [],
        }

        with patch.object(command_bar, "st", fake_st):
            _sync_router_to_session(router_result)

        self.assertNotIn(_SS_COMPARE_RESULT, fake_st.session_state)
        self.assertEqual(fake_st.session_state.get(_SS_LAST_COMP_CTX), None)

    def test_router_primary_stats_wins_over_compare_parsed_type(self) -> None:
        from ui import command_bar

        fake_st = _FakeStreamlit()
        old_compare = {
            "symbols": ["NVDA", "AVGO"],
            "field": "Close",
            "stats": {"total": 20, "matched": 10, "mismatched": 10, "match_rate": 50.0},
            "comparison_df": pd.DataFrame({"Date": ["2026-01-01"], "match": [True]}),
            "aligned_df": pd.DataFrame({"Date": ["2026-01-01"], "AVGO_Close": [1.0], "NVDA_Close": [2.0]}),
        }
        stats_data = {
            "symbol": "AVGO",
            "field": "Close",
            "lookback_days": 20,
            "operation": "today_vs_average",
            "today_value": 730.0,
            "average_value": 720.0,
            "absolute_diff": 10.0,
            "pct_diff": 1.39,
            "raw_table": pd.DataFrame({"Date": ["2026-01-01"], "Close": [730.0]}),
            "raw_table_label": "最近 20 天均值样本 + 今日原始表格",
        }
        text = "博通今天收盘价和最近20天平均收盘价对比"
        fake_st.session_state.update({
            _SS_PARSED: parse_command(text),
            _SS_PLAN: plan_intent(text),
            _SS_ROUTER_RESULT: {
                "steps_executed": [
                    {"step": 1, "type": "stats", "status": "success", "result": stats_data},
                ],
                "primary_result": {"type": "stats", "data": stats_data},
                "aux_results": {},
                "session_ctx": {"latest_compare_result": old_compare, "latest_stats_result": stats_data},
                "warnings": [],
            },
            _SS_COMPARE_RESULT: old_compare,
        })

        with patch.object(command_bar, "st", fake_st):
            _render_stored_result()

        rendered = "\n".join(fake_st.calls)
        self.assertIn("AVGO 收盘价 今日值", rendered)
        self.assertIn("近 20 日均值", rendered)
        self.assertIn("最近 20 天均值样本 + 今日原始表格", rendered)
        self.assertNotIn("比较对象", rendered)
        self.assertNotIn("逐日对比", rendered)
        self.assertNotIn("对齐数据", rendered)


class AIExplanationCommandTests(unittest.TestCase):
    def test_projection_ai_explanation_requires_context(self) -> None:
        task = parse_command("用 AI 解释这次推演")
        result, error = run_ai_explanation_command(task)
        self.assertIsNone(result)
        self.assertIn("请先运行一次推演命令", error or "")

    def test_compare_ai_explanation_requires_context(self) -> None:
        task = parse_command("用 AI 总结这次比较结果")
        result, error = run_ai_explanation_command(task)
        self.assertIsNone(result)
        self.assertIn("请先运行一次比较", error or "")

    def test_projection_ai_explanation_uses_existing_projection_result(self) -> None:
        task = parse_command("用 AI 解释为什么偏多")
        projection_result = {
            "ready": True,
            "projection_report": {
                "direction": "偏多",
                "confidence": "low",
                "readable_summary": {"risk_reminders": ["样本不足"]},
            },
        }

        def fake_builder(payload):
            self.assertEqual(payload["ai_request"]["direction"], "偏多")
            self.assertEqual(payload["projection_report"]["direction"], "偏多")
            return "规则层偏多，因为..."

        result, error = run_ai_explanation_command(
            task,
            projection_result=projection_result,
            _projection_builder=fake_builder,
        )
        self.assertEqual(result, "规则层偏多，因为...")
        self.assertIsNone(error)

    def test_compare_ai_explanation_uses_existing_compare_result(self) -> None:
        task = parse_command("用 AI 总结这次比较结果")
        compare_result = {
            "symbols": ["AVGO", "NVDA"],
            "field": "Close",
            "stats": {"total": 20, "matched": 13},
            "comparison_df": None,
            "aligned_df": None,
        }

        def fake_builder(payload):
            self.assertEqual(payload["symbols"], ["AVGO", "NVDA"])
            self.assertEqual(payload["stats"]["matched"], 13)
            return "比较结果总结"

        result, error = run_ai_explanation_command(
            task,
            compare_result=compare_result,
            _compare_builder=fake_builder,
        )
        self.assertEqual(result, "比较结果总结")
        self.assertIsNone(error)

    def test_risk_ai_explanation_uses_projection_risk_context(self) -> None:
        task = parse_command("用 AI 解释这次风险提醒")
        projection_result = {
            "projection_report": {
                "direction": "中性",
                "readable_summary": {"risk_reminders": ["外部确认不足"]},
            },
        }

        def fake_builder(payload):
            self.assertIn("外部确认不足", payload["readable_summary"]["risk_reminders"])
            return "风险解释"

        result, error = run_ai_explanation_command(
            task,
            projection_result=projection_result,
            _risk_builder=fake_builder,
        )
        self.assertEqual(result, "风险解释")
        self.assertIsNone(error)


class ResponseCardRendererTests(unittest.TestCase):
    def test_required_section_headings_are_fixed(self) -> None:
        self.assertEqual(
            list(_RESPONSE_CARD_SECTION_HEADINGS),
            ["任务理解", "执行步骤", "核心结论", "依据摘要", "风险 / 提示", "原始结果"],
        )

    def test_section_order_is_fixed(self) -> None:
        from ui import command_bar

        fake_st = _FakeStreamlit()
        card = _build_stats_response_card({
            "symbol": "AVGO",
            "field": "Volume",
            "lookback_days": 20,
            "operation": "today_vs_average",
            "today_value": 100.0,
            "average_value": 90.0,
            "absolute_diff": 10.0,
            "pct_diff": 11.11,
        })

        with patch.object(command_bar, "st", fake_st):
            _render_response_card(card)

        self.assertEqual(_section_headings(fake_st), list(_RESPONSE_CARD_SECTION_HEADINGS))

    def test_projection_compare_query_stats_use_same_outer_card_structure(self) -> None:
        from ui import command_bar

        projection_card = _build_projection_response_card({
            "ready": True,
            "projection_report": {
                "kind": "final_projection_report",
                "direction": "中性",
                "open_tendency": "平开",
                "close_tendency": "震荡",
                "confidence": "low",
            },
        })
        compare_card = _build_compare_response_card({
            "symbols": ["AVGO", "NVDA"],
            "field": "Close",
            "stats": {"total": 20, "matched": 12, "mismatched": 8, "match_rate": 60.0},
        })
        query_card = _build_query_response_card([])
        stats_card = _build_stats_response_card({
            "symbol": "AVGO",
            "field": "Volume",
            "lookback_days": 20,
            "operation": "today_vs_average",
            "today_value": 100.0,
            "average_value": 90.0,
            "absolute_diff": 10.0,
            "pct_diff": 11.11,
        })

        for card in (projection_card, compare_card, query_card, stats_card):
            fake_st = _FakeStreamlit()
            with patch.object(command_bar, "st", fake_st):
                _render_response_card(card)
            self.assertEqual(_section_headings(fake_st), list(_RESPONSE_CARD_SECTION_HEADINGS))
            self.assertIn("container", fake_st.calls)
            self.assertIn("expander:展开原始结果", fake_st.calls)
            self.assertIn("json", fake_st.calls)

    def test_query_card_renders_table_outside_raw_expander(self) -> None:
        from ui import command_bar

        fake_st = _FakeStreamlit()
        df = pd.DataFrame({
            "Date": ["2026-01-01", "2026-01-02"],
            "Volume": [100.0, 110.0],
        })
        card = _build_query_response_card([("AVGO", df)])

        with patch.object(command_bar, "st", fake_st):
            _render_response_card(card)

        self.assertIn("markdown:**表格输出**", fake_st.calls)
        self.assertIn("dataframe:main", fake_st.calls)
        self.assertNotIn("dataframe:expander", fake_st.calls)

    def test_stats_card_renders_raw_table_outside_raw_expander(self) -> None:
        from ui import command_bar

        fake_st = _FakeStreamlit()
        df = pd.DataFrame({
            "Date": ["2026-01-01", "2026-01-02"],
            "Volume": [100.0, 110.0],
        })
        card = _build_stats_response_card({
            "symbol": "AVGO",
            "field": "Volume",
            "lookback_days": 20,
            "operation": "today_vs_average",
            "today_value": 110.0,
            "average_value": 100.0,
            "absolute_diff": 10.0,
            "pct_diff": 10.0,
            "raw_table": df,
        })

        with patch.object(command_bar, "st", fake_st):
            _render_response_card(card)

        self.assertIn("markdown:**表格输出**", fake_st.calls)
        self.assertIn("dataframe:main", fake_st.calls)
        self.assertNotIn("dataframe:expander", fake_st.calls)

    def test_warnings_render_in_fixed_warning_section(self) -> None:
        from ui import command_bar

        fake_st = _FakeStreamlit()
        card = _build_projection_response_card(
            {"ready": False, "advisory": {"matched_count": 0, "caution_level": "none"}},
            router_result={"warnings": ["AI 未配置，已保留规则层结果。"]},
        )

        with patch.object(command_bar, "st", fake_st):
            _render_response_card(card)

        self.assertEqual(_section_headings(fake_st), list(_RESPONSE_CARD_SECTION_HEADINGS))
        warning_section = fake_st.calls.index("markdown:**风险 / 提示**")
        raw_section = fake_st.calls.index("markdown:**原始结果**")
        warning_call = "warning:AI 未配置，已保留规则层结果。"
        self.assertIn(warning_call, fake_st.calls)
        self.assertGreater(fake_st.calls.index(warning_call), warning_section)
        self.assertLess(fake_st.calls.index(warning_call), raw_section)

    def test_raw_result_uses_single_non_nested_expander(self) -> None:
        from ui import command_bar

        fake_st = _FakeStreamlit()
        card = _build_compare_response_card({
            "symbols": ["AVGO", "NVDA"],
            "field": "Close",
            "stats": {"total": 1, "matched": 1, "mismatched": 0, "match_rate": 100.0},
        })

        with patch.object(command_bar, "st", fake_st):
            _render_response_card(card)

        self.assertEqual(fake_st.calls.count("expander:展开原始结果"), 1)
        self.assertEqual(fake_st.max_expander_depth, 1)

    def test_command_center_renderer_does_not_use_empty_placeholder(self) -> None:
        from ui import command_bar

        sources = "\n".join(
            inspect.getsource(fn)
            for fn in (
                command_bar.render_command_bar,
                command_bar._render_stored_result,
                command_bar._render_response_card,
            )
        )

        self.assertNotIn("st.empty", sources)
        self.assertNotIn(".empty(", sources)


class ProjectionRenderTests(unittest.TestCase):
    def test_final_projection_details_use_container_not_expander(self) -> None:
        from ui import command_bar

        fake_st = _FakeStreamlit()
        result = {
            "ready": True,
            "projection_report": {
                "kind": "final_projection_report",
                "direction": "中性",
                "open_tendency": "平开",
                "close_tendency": "震荡",
                "confidence": "low",
                "readable_summary": {
                    "baseline_judgment": {"text": "中性（强度：弱，风险：高，置信度：低）"},
                    "open_projection": {"text": "更可能平开。"},
                    "close_projection": {"text": "更可能震荡。"},
                    "rationale": ["结构化依据"],
                    "risk_reminders": ["样本不足"],
                },
                "evidence_trace": {
                    "tool_trace": ["scan", "predict_summary"],
                    "key_observations": ["结构观察"],
                    "decision_steps": ["观察：gap state = flat → 结论影响：开盘倾向保持为 平开。"],
                    "final_conclusion": {
                        "direction": "中性",
                        "open_tendency": "平开",
                        "close_tendency": "震荡",
                        "confidence": "low",
                    },
                    "verification_points": ["观察开盘后 30 分钟。"],
                },
            },
        }

        with patch.object(command_bar, "st", fake_st):
            _render_projection_result(result)

        self.assertEqual(_section_headings(fake_st), list(_RESPONSE_CARD_SECTION_HEADINGS))
        self.assertNotIn("markdown:**推演详情**", fake_st.calls)
        self.assertIn("container", fake_st.calls)
        self.assertIn("expander:展开原始结果", fake_st.calls)
        self.assertIn("json", fake_st.calls)
        self.assertTrue(any("tool_trace" in call for call in fake_st.calls))
        self.assertTrue(any("decision_steps" in call for call in fake_st.calls))


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
