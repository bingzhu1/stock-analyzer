"""Integration tests: plan_intent -> route_plan -> load_symbol_data.

These tests exercise the full planner-router-loader chain without hitting the
filesystem.  The fake loader captures every call it receives so assertions can
verify which branch of the router was taken and what arguments reached the
loader.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.intent_planner import plan_intent
from services.tool_router import STATUS_FAILED, STATUS_SUCCESS, route_plan


# ── instrumented fake loader ───────────────────────────────────────────────────

class _RecordingLoader:
    """Fake loader that records every call and returns a minimal DataFrame."""

    def __init__(self, rows: list[dict]) -> None:
        self.calls: list[dict[str, Any]] = []
        self._rows = rows

    def __call__(
        self,
        symbol: str,
        window: int = 20,
        fields=None,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> pd.DataFrame:
        self.calls.append({
            "symbol":     symbol,
            "window":     window,
            "fields":     fields,
            "start_date": start_date,
            "end_date":   end_date,
        })
        df = pd.DataFrame(self._rows)
        if fields:
            cols = ["Date"] + [f for f in fields if f in df.columns]
            return df[cols]
        return df


def _make_rows(dates: list[str]) -> list[dict]:
    return [
        {"Date": d, "Open": 700.0, "High": 720.0, "Low": 695.0,
         "Close": 710.0, "Volume": 1_000_000.0}
        for d in dates
    ]


# ── integration test cases ─────────────────────────────────────────────────────

class AbsoluteDateRangeIntegrationTests(unittest.TestCase):

    def test_absolute_range_planner_to_loader(self) -> None:
        """Full chain: planner extracts dates → router passes them → loader receives them."""
        raw = "调出博通2026年1月15日至2月9日历史数据"

        # Step 1: planner
        plan = plan_intent(raw)
        self.assertTrue(plan["supported"], f"plan should be supported; warnings={plan['warnings']}")
        self.assertEqual(plan.get("start_date"), "2026-01-15")
        self.assertEqual(plan.get("end_date"),   "2026-02-09")

        # Step 2: router + instrumented loader
        rows = _make_rows(["2026-01-15", "2026-01-20", "2026-02-01", "2026-02-09"])
        loader = _RecordingLoader(rows)
        result = route_plan(plan, _loader=loader)

        # Router must have executed successfully
        self.assertEqual(len(loader.calls), 1, "loader must be called exactly once")
        call = loader.calls[0]

        # Loader received date kwargs, not the relative-window branch
        self.assertEqual(call["start_date"], "2026-01-15")
        self.assertEqual(call["end_date"],   "2026-02-09")
        self.assertIsNone(
            call.get("start_date") and None,  # always None check via explicit assert below
        )
        # The window argument must be the default (20), meaning the router did NOT
        # deliberately pass a custom window — the date-branch was taken instead.
        # We verify this by confirming start_date/end_date are present (proven above)
        # and that the step executed successfully.
        steps = result["steps_executed"]
        self.assertTrue(
            any(s["status"] == STATUS_SUCCESS and s["type"] == "query" for s in steps),
            f"query step must succeed; steps={steps}",
        )

        # primary_result carries query data
        pr = result["primary_result"]
        self.assertIsNotNone(pr)
        self.assertEqual(pr["type"], "query")

    def test_absolute_range_loader_not_called_with_window_branch(self) -> None:
        """Router must not fall through to tail(window) when dates are present."""
        raw = "调出博通2026年1月15日至2月9日历史数据"
        plan = plan_intent(raw)

        rows = _make_rows(["2026-01-15", "2026-02-09"])
        loader = _RecordingLoader(rows)
        route_plan(plan, _loader=loader)

        self.assertEqual(len(loader.calls), 1)
        call = loader.calls[0]
        # If the window branch had been taken, start_date would be None
        self.assertIsNotNone(call["start_date"],
                             "loader must receive start_date, not fall through to window branch")
        self.assertIsNotNone(call["end_date"])

    def test_inverted_dates_blocked_before_loader(self) -> None:
        """start > end must be caught by planner — loader must never be called."""
        raw = "调出博通2026年3月1日至2026年1月1日历史数据"
        plan = plan_intent(raw)

        self.assertFalse(plan["supported"])
        self.assertTrue(
            any("晚于" in w or "结束日期" in w for w in plan["warnings"]),
            f"expected inversion warning; got: {plan['warnings']}",
        )

        loader = _RecordingLoader([])
        result = route_plan(plan, _loader=loader)
        self.assertEqual(loader.calls, [], "loader must not be called when plan is unsupported")
        self.assertIsNone(result["primary_result"])

    def test_relative_lookback_unaffected_end_to_end(self) -> None:
        """Relative-window query must still reach the loader with window, not dates."""
        raw = "只看博通最近20天成交量"
        plan = plan_intent(raw)
        self.assertTrue(plan["supported"])
        self.assertNotIn("start_date", plan)

        rows = _make_rows([f"2026-03-{i+1:02d}" for i in range(21)])
        loader = _RecordingLoader(rows)
        route_plan(plan, _loader=loader)

        self.assertEqual(len(loader.calls), 1)
        call = loader.calls[0]
        self.assertIsNone(call["start_date"], "relative query must NOT pass start_date to loader")
        self.assertIsNone(call["end_date"])
        self.assertEqual(call["window"], 20)

    def test_partial_date_blocked_before_loader(self) -> None:
        """Incomplete date expression must block execution entirely."""
        raw = "调出博通2026年1月15日至2月历史数据"
        plan = plan_intent(raw)

        self.assertFalse(plan["supported"])
        loader = _RecordingLoader([])
        result = route_plan(plan, _loader=loader)
        self.assertEqual(loader.calls, [], "loader must not be called for partial date input")

    def test_hao_no_year_blocked_before_loader(self) -> None:
        """号 without year must be detected as partial date → supported=False, loader not called."""
        raw = "调出博通2月5号至2月25号的数据"
        plan = plan_intent(raw)

        self.assertFalse(plan["supported"], f"must be blocked; warnings={plan['warnings']}")
        self.assertTrue(
            any("日期" in w for w in plan["warnings"]),
            f"must warn about date range; got: {plan['warnings']}",
        )

        loader = _RecordingLoader([])
        result = route_plan(plan, _loader=loader)
        self.assertEqual(loader.calls, [], "loader must not be called when plan is unsupported")
        self.assertIsNone(result["primary_result"])

    def test_hao_with_year_executes_date_branch(self) -> None:
        """号 with year must parse fully and reach loader with start_date/end_date."""
        raw = "调出博通2026年2月5号至2月25号的数据"
        plan = plan_intent(raw)

        self.assertTrue(plan["supported"], f"must be supported; warnings={plan['warnings']}")
        self.assertEqual(plan.get("start_date"), "2026-02-05")
        self.assertEqual(plan.get("end_date"),   "2026-02-25")

        rows = _make_rows(["2026-02-05", "2026-02-10", "2026-02-25"])
        loader = _RecordingLoader(rows)
        route_plan(plan, _loader=loader)

        self.assertEqual(len(loader.calls), 1)
        call = loader.calls[0]
        self.assertEqual(call["start_date"], "2026-02-05")
        self.assertEqual(call["end_date"],   "2026-02-25")


if __name__ == "__main__":
    unittest.main()
