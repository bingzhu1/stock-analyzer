"""Contract enforcement tests for Step 12C-B (RISK-3 stage B).

These tests pin the wire-up of ``services.confidence_evaluator`` into the
final report path:

1. ``run_projection_v2`` surfaces a ``confidence_result`` field at the top
   of its unified payload, with ``schema_version ==
   "confidence_system_result.v1"``.
2. ``build_home_terminal_orchestrator_result`` does the same.
3. ``build_final_decision`` consumes the wired ``confidence_result`` so
   ``final_confidence`` strictly equals
   ``confidence_result.combined_confidence.level``.
4. ``confidence_result`` does NOT mutate ``main_projection`` or
   ``exclusion_result`` (snapshot equality before/after).
5. The renderer's ``confidence_evaluator`` block, when given a
   ``confidence_result`` in ``v2_raw``, surfaces its level instead of
   self-computing.
6. When ``confidence_result`` is missing, ``final_confidence`` stays
   ``"unknown"`` (12B contract preserved).
7. The wired ``confidence_result`` does not contain trading / hard /
   forced / required / promotion fields.

Design contracts: 06 / 07C / 07D / 11C / 11H.
"""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


_FORBIDDEN_FIELDS = (
    "trading_action",
    "buy",
    "sell",
    "hold",
    "simulated_trade",
    "no_trade",
    "hard_exclusion",
    "forced_exclusion",
    "required_decision",
    "production_promotion",
    "_PROTECTION_LAYER_CONNECTED",
    "final_report_mutation",
    "modified_projection",
    "modified_exclusion",
)


def _coded_df_20() -> pd.DataFrame:
    rows = []
    closes = [
        100.0, 100.8, 101.2, 101.6, 102.1,
        102.8, 103.0, 103.6, 104.1, 104.8,
        105.2, 105.9, 106.3, 106.9, 107.1,
        107.8, 108.2, 108.9, 109.4, 110.2,
    ]
    for idx, close in enumerate(closes, start=1):
        rows.append({
            "Date": f"2026-04-{idx:02d}",
            "Open": close - 0.6,
            "High": close + 1.2,
            "Low": close - 1.0,
            "Close": close,
            "Volume": 1000 + idx * 20,
        })
    return pd.DataFrame(rows)


def _peer_df(move: float) -> pd.DataFrame:
    return pd.DataFrame({"Date": ["2026-04-20"], "C_move": [move / 100.0]})


def _legacy_v2_payload() -> dict:
    return {
        "symbol": "AVGO",
        "request": {"symbol": "AVGO", "lookback_days": 20},
        "advisory": {
            "matched_count": 1,
            "caution_level": "low",
            "reminder_lines": ["历史提醒：等待确认。"],
            "ready": True,
        },
        "projection_report": {
            "kind": "final_projection_report",
            "target_date": "2026-04-21",
            "direction": "偏多",
            "open_tendency": "平开",
            "close_tendency": "偏强",
            "confidence": "medium",
            "basis_summary": ["主分析依据。"],
            "risk_reminders": ["风险提醒。"],
            "report_text": "明日基准判断：偏多。",
            "readable_summary": {
                "baseline_judgment": {"risk_level": "中"},
            },
        },
        "predict_result": {"final_bias": "bullish", "final_confidence": "medium"},
        "scan_result": {
            "confirmation_state": "confirmed",
            "relative_strength_5d_summary": {
                "vs_nvda": "stronger",
                "vs_soxx": "neutral",
                "vs_qqq": "stronger",
            },
            "relative_strength_same_day_summary": {
                "vs_nvda": "stronger",
                "vs_soxx": "neutral",
                "vs_qqq": "neutral",
            },
            "historical_match_summary": {
                "exact_match_count": 2,
                "near_match_count": 4,
                "dominant_historical_outcome": "up_bias",
            },
        },
        "ready": True,
    }


def _primary_result() -> dict:
    return {
        "kind": "primary_20day_analysis",
        "symbol": "AVGO",
        "lookback_days": 20,
        "target_date": "2026-04-21",
        "ready": True,
        "direction": "偏多",
        "confidence": "medium",
        "position_label": "高位",
        "stage_label": "延续",
        "volume_state": "正常",
        "summary": "AVGO 最近20天主分析：方向偏多。",
        "basis": ["最近5日收益为 +3.00%。"],
        "warnings": [],
        "features": {
            "latest_close": 120.0,
            "ret_5d": 3.0,
            "ret_10d": 5.0,
            "pos_20d": 80.0,
            "high_20d": 121.0,
            "low_20d": 100.0,
            "vol_ratio_5d": 1.0,
            "days_used": 20,
        },
    }


def _empty_preflight(**_):
    return {
        "kind": "projection_rule_preflight",
        "symbol": "AVGO",
        "target_date": None,
        "lookback_days": 20,
        "ready": True,
        "matched_rules": [],
        "rule_warnings": [],
        "rule_adjustments": [],
        "summary": "未命中历史规则。",
        "warnings": [],
        "source_counts": {"memory_items": 0, "review_items": 0, "matched_rule_count": 0},
    }


class V2OrchestratorWiringTests(unittest.TestCase):
    def test_projection_orchestrator_v2_wires_confidence_result(self) -> None:
        from services.projection_orchestrator_v2 import run_projection_v2

        payload = _legacy_v2_payload()

        def _runner(**_):
            return payload

        def _primary(**_):
            return _primary_result()

        result = run_projection_v2(
            target_date="2026-04-21",
            _projection_runner=_runner,
            _primary_analysis_builder=_primary,
            _rule_preflight_builder=_empty_preflight,
        )

        self.assertIn("confidence_result", result, msg=result.keys())
        cr = result["confidence_result"]
        self.assertEqual(cr["schema_version"], "confidence_system_result.v1")
        self.assertEqual(cr["system_name"], "confidence_system")
        self.assertEqual(cr["target_date"], "2026-04-21")
        # No forbidden fields anywhere on confidence_result.
        for forbidden in _FORBIDDEN_FIELDS:
            self.assertNotIn(forbidden, cr)

    def test_projection_v2_final_decision_reads_confidence_result_only(self) -> None:
        """When confidence_result.combined_confidence.level resolves to
        unknown (calibration not wired), the aggregator's final_confidence
        must stay unknown. This pins that final_decision does NOT recompute
        from peer/historical."""
        from services.projection_orchestrator_v2 import run_projection_v2

        result = run_projection_v2(
            target_date="2026-04-21",
            _projection_runner=lambda **_: _legacy_v2_payload(),
            _primary_analysis_builder=lambda **_: _primary_result(),
            _rule_preflight_builder=_empty_preflight,
        )
        self.assertEqual(
            result["final_decision"]["final_confidence"],
            result["confidence_result"]["combined_confidence"]["level"],
        )

    def test_projection_v2_confidence_result_does_not_mutate_projection_or_exclusion(self) -> None:
        from services.projection_orchestrator_v2 import run_projection_v2

        result = run_projection_v2(
            target_date="2026-04-21",
            _projection_runner=lambda **_: _legacy_v2_payload(),
            _primary_analysis_builder=lambda **_: _primary_result(),
            _rule_preflight_builder=_empty_preflight,
        )
        main_before = copy.deepcopy(result["main_projection"])
        excl_before = copy.deepcopy(result["exclusion_result"])

        # Re-run with the same fixtures and compare; deterministic builders
        # should produce identical projection / exclusion sections.
        result2 = run_projection_v2(
            target_date="2026-04-21",
            _projection_runner=lambda **_: _legacy_v2_payload(),
            _primary_analysis_builder=lambda **_: _primary_result(),
            _rule_preflight_builder=_empty_preflight,
        )
        self.assertEqual(result2["main_projection"], main_before)
        self.assertEqual(result2["exclusion_result"], excl_before)

        # confidence_result has the read-only audit confirmations.
        confirmations = result["confidence_result"]["non_mutation_confirmations"]
        self.assertIs(confirmations["projection_result_mutated"], False)
        self.assertIs(confirmations["exclusion_result_mutated"], False)


class HomeTerminalWiringTests(unittest.TestCase):
    def test_home_terminal_orchestrator_wires_confidence_result(self) -> None:
        from services.home_terminal_orchestrator import (
            build_home_terminal_orchestrator_result,
        )

        payload = build_home_terminal_orchestrator_result(
            scan_result={
                "historical_match_summary": {
                    "exact_match_count": 2,
                    "near_match_count": 3,
                    "dominant_historical_outcome": "up_bias",
                }
            },
            target_date_str="2026-04-20",
            coded_df=_coded_df_20(),
            target_row=_coded_df_20().iloc[-1],
            target_ctx={"ret3": 1.9, "ret5": 3.8},
            peer_loader=lambda symbol: {
                "NVDA": _peer_df(1.1),
                "SOXX": _peer_df(0.7),
                "QQQ": _peer_df(0.4),
            }.get(symbol),
            persist_log=False,
        )

        self.assertIn("confidence_result", payload)
        cr = payload["confidence_result"]
        self.assertEqual(cr["schema_version"], "confidence_system_result.v1")
        self.assertEqual(cr["system_name"], "confidence_system")
        self.assertEqual(cr["target_date"], "2026-04-20")
        for forbidden in _FORBIDDEN_FIELDS:
            self.assertNotIn(forbidden, cr)


class FinalDecisionReadsConfidenceTests(unittest.TestCase):
    def test_missing_confidence_result_still_unknown(self) -> None:
        """If the caller omits confidence_result, final_decision stays
        unknown — preserves 12B contract under 12C-B wiring."""
        from services.final_decision import build_final_decision

        result = build_final_decision(
            primary_analysis={
                "ready": True,
                "direction": "偏多",
                "confidence": "high",
            },
            peer_adjustment={"ready": True, "adjustment": "reinforce_bullish"},
            historical_probability={"ready": True, "impact": "support"},
            preflight={},
        )
        self.assertEqual(result["final_confidence"], "unknown")

    def test_wired_confidence_result_drives_final_confidence(self) -> None:
        from services.final_decision import build_final_decision

        for level in ("low", "medium", "high"):
            result = build_final_decision(
                primary_analysis={
                    "ready": True,
                    "direction": "偏多",
                    "confidence": "high",
                },
                peer_adjustment={"ready": True, "adjustment": "reinforce_bullish"},
                historical_probability={"ready": True, "impact": "support"},
                preflight={},
                confidence_result={
                    "ready": True,
                    "schema_version": "confidence_system_result.v1",
                    "combined_confidence": {"level": level},
                    "agreement_status": "aligned",
                    "conflict_level": "none",
                },
            )
            self.assertEqual(result["final_confidence"], level)

    def test_final_decision_does_not_recompute_confidence_after_wire(self) -> None:
        """Even when peer/historical/preflight push for higher confidence,
        the aggregator must not override the confidence_result."""
        from services.final_decision import build_final_decision

        result = build_final_decision(
            primary_analysis={
                "ready": True,
                "direction": "偏多",
                "confidence": "high",
            },
            peer_adjustment={"ready": True, "adjustment": "reinforce_bullish"},
            historical_probability={"ready": True, "impact": "support"},
            preflight={"matched_rules": [{"severity": "high", "rule_id": "x"}]},
            confidence_result={
                "ready": True,
                "schema_version": "confidence_system_result.v1",
                "combined_confidence": {"level": "low"},
            },
        )
        self.assertEqual(result["final_confidence"], "low")


class RendererReadsConfidenceTests(unittest.TestCase):
    def _v2_with_confidence_result(self, level: str) -> dict:
        return {
            "kind": "projection_v2_report",
            "symbol": "AVGO",
            "ready": True,
            "preflight": {"kind": "projection_rule_preflight", "ready": True, "matched_rules": []},
            "primary_analysis": {
                "kind": "primary_20day_analysis",
                "ready": True,
                "direction": "偏多",
                "confidence": "medium",
                "summary": "AVGO 主分析。",
                "warnings": [],
            },
            "peer_adjustment": {
                "kind": "peer_adjustment",
                "ready": True,
                "confirmation_level": "confirmed",
                "adjustment": "reinforce_bullish",
                "summary": "peers ok.",
                "warnings": [],
            },
            "historical_probability": {
                "kind": "historical_probability",
                "ready": True,
                "sample_count": 8,
                "sample_quality": "enough",
                "historical_bias": "supports_bullish",
                "impact": "support",
                "summary": "hist ok.",
                "warnings": [],
            },
            "final_decision": {
                "kind": "final_decision",
                "ready": True,
                "final_direction": "偏多",
                "final_confidence": level,
                "risk_level": "unknown",
                "summary": "ok",
                "warnings": [],
                "layer_contributions": {
                    "primary": "p",
                    "peer": "pe",
                    "historical": "h",
                    "preflight": "pf",
                },
                "why_not_more_bullish_or_bearish": "",
            },
            "exclusion_result": {
                "excluded": False,
                "action": "allow",
                "triggered_rule": None,
                "summary": "no exclusion",
                "reasons": [],
                "peer_alignment": {"alignment": "neutral", "available_peer_count": 3},
                "feature_snapshot": {},
            },
            "main_projection": {
                "kind": "main_projection_layer",
                "ready": True,
                "predicted_top1": {"state": "小涨", "probability": 0.36},
                "predicted_top2": {"state": "震荡", "probability": 0.28},
                "state_probabilities": {
                    "大涨": 0.10,
                    "小涨": 0.36,
                    "震荡": 0.28,
                    "小跌": 0.18,
                    "大跌": 0.08,
                },
                "warnings": [],
            },
            "consistency": {
                "consistency_flag": "consistent",
                "consistency_score": 1.0,
                "conflict_reasons": [],
                "summary": "ok",
            },
            "confidence_result": {
                "schema_version": "confidence_system_result.v1",
                "system_name": "confidence_system",
                "ready": True,
                "projection_confidence": {
                    "level": level,
                    "score": None,
                    "reasoning": [],
                },
                "exclusion_confidence": {
                    "level": level,
                    "score": None,
                    "reasoning": [],
                },
                "agreement_status": "aligned",
                "conflict_level": "none",
                "combined_confidence": {
                    "level": level,
                    "score": None,
                    "reasoning": [],
                },
            },
        }

    def test_renderer_displays_confidence_result_without_recomputing(self) -> None:
        from services.projection_three_systems_renderer import (
            build_confidence_evaluator,
        )

        for level in ("low", "medium", "high"):
            v2 = self._v2_with_confidence_result(level)
            result = build_confidence_evaluator(v2)
            self.assertEqual(
                result["overall_confidence"]["level"],
                level,
                msg=f"renderer must read overall level from confidence_result for {level=}",
            )
            self.assertEqual(
                result["projection_system_confidence"]["level"],
                level,
            )
            self.assertEqual(
                result["negative_system_confidence"]["level"],
                level,
            )

    def test_renderer_does_not_mutate_main_projection_or_exclusion(self) -> None:
        from services.projection_three_systems_renderer import (
            build_projection_three_systems,
        )

        v2 = self._v2_with_confidence_result("medium")
        v2_snapshot = copy.deepcopy(v2)
        build_projection_three_systems(v2)
        self.assertEqual(v2["main_projection"], v2_snapshot["main_projection"])
        self.assertEqual(v2["exclusion_result"], v2_snapshot["exclusion_result"])
        self.assertEqual(v2["confidence_result"], v2_snapshot["confidence_result"])


if __name__ == "__main__":
    unittest.main()
