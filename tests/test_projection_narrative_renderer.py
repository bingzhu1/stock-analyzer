from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.projection_narrative_renderer import build_projection_narrative


def _v2_result(**overrides) -> dict:
    base = {
        "kind": "projection_v2_report",
        "symbol": "AVGO",
        "target_date": "2026-04-21",
        "ready": True,
        "preflight": {
            "kind": "projection_rule_preflight",
            "ready": True,
            "matched_rules": [
                {
                    "rule_id": "r-1",
                    "category": "false_confidence",
                    "severity": "high",
                    "message": "高置信度场景需复核。",
                }
            ],
            "rule_warnings": ["历史提醒：高置信度场景需复核。"],
            "summary": "命中 1 条历史规则提醒。",
            "warnings": [],
        },
        "primary_analysis": {
            "kind": "primary_20day_analysis",
            "ready": True,
            "direction": "偏多",
            "confidence": "medium",
            "position_label": "高位",
            "stage_label": "延续",
            "volume_state": "正常",
            "summary": "最近20天主分析偏多。",
            "basis": ["最近5日收益为 +3.00%。", "主分析方向信号归纳为偏多。"],
            "warnings": [],
        },
        "peer_adjustment": {
            "kind": "peer_adjustment",
            "ready": True,
            "confirmation_level": "confirmed",
            "adjustment": "reinforce_bullish",
            "adjusted_direction": "偏多",
            "adjusted_confidence": "high",
            "summary": "peers 支持主分析偏多。",
            "basis": ["NVDA / SOXX / QQQ 同步确认。"],
            "warnings": [],
        },
        "historical_probability": {
            "kind": "historical_probability",
            "ready": True,
            "sample_count": 8,
            "sample_quality": "enough",
            "historical_bias": "supports_bullish",
            "impact": "support",
            "summary": "历史概率层完成：样本 8，支持偏多。",
            "combined_probability": {
                "up_rate": 0.625,
                "down_rate": 0.375,
                "gap_up_rate": 0.5,
                "strong_close_rate": 0.7,
                "method": "blended",
            },
            "warnings": [],
        },
        "final_decision": {
            "kind": "final_decision",
            "ready": True,
            "final_direction": "偏多",
            "final_confidence": "medium",
            "risk_level": "medium",
            "summary": "最终结论：方向偏多，置信度medium，风险medium。",
            "decision_factors": ["主分析偏多。", "历史概率支持偏多。"],
            "warnings": [],
            "layer_contributions": {
                "primary": "主分析给出偏多，作为主判断来源。",
                "peer": "peer 修正强化主分析方向。",
                "historical": "历史概率层支持当前方向。",
                "preflight": "preflight 命中 1 条提醒。 命中 1 条历史规则：下调置信度。",
            },
            "why_not_more_bullish_or_bearish": "peers 未提供额外强化。 历史规则约束：命中 1 条历史规则：下调置信度。",
            "preflight_influence": {
                "matched_rule_count": 1,
                "applied_effects": ["lower_confidence"],
                "summary": "命中 1 条历史规则：下调置信度。",
            },
        },
        "warnings": [],
        "trace": [],
        "step_status": {
            "preflight": "success",
            "primary_analysis": "success",
            "peer_adjustment": "success",
            "historical_probability": "success",
            "final_decision": "success",
        },
    }
    for key, value in overrides.items():
        base[key] = value
    return base


class ProjectionNarrativeRendererTests(unittest.TestCase):
    def test_happy_path_returns_full_narrative_shape(self) -> None:
        result = build_projection_narrative(projection_v2_raw=_v2_result())

        self.assertEqual(result["kind"], "projection_narrative")
        self.assertTrue(result["ready"])
        self.assertEqual(result["symbol"], "AVGO")
        for key in (
            "step1_conclusion",
            "step2_peer_adjustment",
            "final_judgment",
            "open_tendency",
            "intraday_structure",
            "close_tendency",
            "one_line_summary",
        ):
            self.assertTrue(result[key])
        self.assertTrue(result["key_watchpoints"]["stronger_case"])
        self.assertTrue(result["key_watchpoints"]["weaker_case"])

    def test_primary_missing_keeps_readable_degraded_step1(self) -> None:
        result = build_projection_narrative(
            projection_v2_raw=_v2_result(
                ready=False,
                primary_analysis={
                    "kind": "primary_20day_analysis",
                    "ready": False,
                    "direction": "unknown",
                    "confidence": "unknown",
                    "summary": "主分析不可用，最近20天窗口不足。",
                    "basis": [],
                    "warnings": ["primary_analysis 数据不足。"],
                },
                final_decision={
                    "kind": "final_decision",
                    "ready": False,
                    "final_direction": "unknown",
                    "final_confidence": "unknown",
                    "risk_level": "high",
                    "summary": "最终结论不可用：主分析不可用。",
                    "warnings": ["final_decision 不可用。"],
                    "why_not_more_bullish_or_bearish": "主分析不可用。",
                    "preflight_influence": {
                        "matched_rule_count": 0,
                        "applied_effects": [],
                        "summary": "未命中会影响最终结论的历史规则。",
                    },
                },
            )
        )

        self.assertFalse(result["ready"])
        self.assertIn("主分析不可用", result["step1_conclusion"])
        self.assertTrue(result["final_judgment"])
        self.assertTrue(result["one_line_summary"])

    def test_peer_missing_mentions_unconfirmed_without_fabricating_support(self) -> None:
        result = build_projection_narrative(
            projection_v2_raw=_v2_result(
                peer_adjustment={
                    "kind": "peer_adjustment",
                    "ready": False,
                    "confirmation_level": "missing",
                    "adjustment": "missing",
                    "adjusted_direction": "偏多",
                    "adjusted_confidence": "medium",
                    "summary": "未获 peers 确认。",
                    "basis": [],
                    "warnings": ["peer_adjustment 缺少 NVDA / SOXX / QQQ 对照数据。"],
                }
            )
        )

        text = result["step2_peer_adjustment"]
        self.assertIn("未获 peers 确认", text)
        self.assertNotIn("托底", text)
        self.assertNotIn("同步确认", text)

    def test_historical_insufficient_is_visible_in_judgment_and_warnings(self) -> None:
        result = build_projection_narrative(
            projection_v2_raw=_v2_result(
                historical_probability={
                    "kind": "historical_probability",
                    "ready": False,
                    "sample_count": 2,
                    "sample_quality": "insufficient",
                    "historical_bias": "insufficient",
                    "impact": "missing",
                    "summary": "历史样本不足：当前仅 2 个样本。",
                    "combined_probability": {
                        "up_rate": None,
                        "down_rate": None,
                        "gap_up_rate": None,
                        "strong_close_rate": None,
                        "method": "fallback",
                    },
                    "warnings": ["historical_probability 样本或信号不足：sample_count=2。"],
                }
            )
        )

        self.assertIn("历史样本不足", result["final_judgment"])
        self.assertTrue(any("历史样本不足" in item for item in result["warnings"]))

    def test_preflight_influence_is_visible_in_narrative(self) -> None:
        result = build_projection_narrative(projection_v2_raw=_v2_result())

        self.assertIn("历史规则提醒", result["final_judgment"])
        self.assertIn("下调置信度", result["final_judgment"])
        self.assertTrue(
            any("历史规则提醒仍在生效" in item for item in result["key_watchpoints"]["weaker_case"])
        )

    def test_raw_preflight_fallback_stays_visible_when_final_is_degraded(self) -> None:
        result = build_projection_narrative(
            projection_v2_raw=_v2_result(
                ready=False,
                primary_analysis={
                    "kind": "primary_20day_analysis",
                    "ready": False,
                    "direction": "unknown",
                    "confidence": "unknown",
                    "summary": "主分析不可用。",
                    "basis": [],
                    "warnings": ["primary_analysis 数据不足。"],
                },
                preflight={
                    "kind": "projection_rule_preflight",
                    "ready": True,
                    "matched_rules": [
                        {
                            "rule_id": "r-9",
                            "category": "wrong_direction",
                            "severity": "high",
                            "message": "历史上类似场景容易误判方向。",
                        }
                    ],
                    "rule_warnings": ["历史提醒：类似场景容易误判方向。"],
                    "summary": "命中 1 条历史规则提醒。",
                    "warnings": [],
                },
                final_decision={
                    "kind": "final_decision",
                    "ready": False,
                    "final_direction": "unknown",
                    "final_confidence": "unknown",
                    "risk_level": "high",
                    "summary": "最终结论不可用：主分析不可用。",
                    "warnings": ["final_decision 不可用。"],
                    "why_not_more_bullish_or_bearish": "主分析不可用。",
                    "preflight_influence": {
                        "matched_rule_count": 0,
                        "applied_effects": [],
                        "summary": "未命中会影响最终结论的历史规则。",
                    },
                },
            )
        )

        self.assertIn("历史规则提醒", result["final_judgment"])
        self.assertIn("命中 1 条历史规则提醒", result["final_judgment"])
        self.assertTrue(
            any("历史规则提醒仍在生效" in item for item in result["key_watchpoints"]["weaker_case"])
        )

    def test_bullish_supported_case_stays_bullish_not_bearish(self) -> None:
        result = build_projection_narrative(
            projection_v2_raw=_v2_result(
                final_decision={
                    "kind": "final_decision",
                    "ready": True,
                    "final_direction": "偏多",
                    "final_confidence": "high",
                    "risk_level": "low",
                    "summary": "最终结论：方向偏多，置信度high，风险low。",
                    "warnings": [],
                    "why_not_more_bullish_or_bearish": "MVP 决策层不做更激进加权。",
                    "preflight_influence": {
                        "matched_rule_count": 0,
                        "applied_effects": [],
                        "summary": "未命中会影响最终结论的历史规则。",
                    },
                },
                preflight={
                    "kind": "projection_rule_preflight",
                    "ready": True,
                    "matched_rules": [],
                    "rule_warnings": [],
                    "summary": "当前未接入历史规则或未命中规则。",
                    "warnings": [],
                },
            )
        )

        text = " ".join(
            [
                result["step1_conclusion"],
                result["step2_peer_adjustment"],
                result["final_judgment"],
                result["one_line_summary"],
            ]
        )
        self.assertIn("偏多", text)
        self.assertNotIn("延续偏弱", text)
        self.assertNotIn("强反转", text)

    def test_bearish_high_risk_case_does_not_claim_strong_reversal(self) -> None:
        result = build_projection_narrative(
            projection_v2_raw=_v2_result(
                primary_analysis={
                    "kind": "primary_20day_analysis",
                    "ready": True,
                    "direction": "偏空",
                    "confidence": "medium",
                    "position_label": "低位",
                    "stage_label": "衰竭风险",
                    "volume_state": "放量",
                    "summary": "最近20天主分析偏空。",
                    "basis": ["主分析方向信号归纳为偏空。"],
                    "warnings": [],
                },
                peer_adjustment={
                    "kind": "peer_adjustment",
                    "ready": True,
                    "confirmation_level": "weak",
                    "adjustment": "downgrade",
                    "adjusted_direction": "偏空",
                    "adjusted_confidence": "low",
                    "summary": "peers 未充分确认主分析方向，peer_adjustment 已下调置信度。",
                    "basis": ["peer votes: confirm=0, oppose=2, mixed=1, neutral=0."],
                    "warnings": [],
                },
                historical_probability={
                    "kind": "historical_probability",
                    "ready": False,
                    "sample_count": 1,
                    "sample_quality": "insufficient",
                    "historical_bias": "insufficient",
                    "impact": "missing",
                    "summary": "历史样本不足。",
                    "combined_probability": {"strong_close_rate": None, "method": "fallback"},
                    "warnings": ["历史样本不足。"],
                },
                final_decision={
                    "kind": "final_decision",
                    "ready": True,
                    "final_direction": "偏空",
                    "final_confidence": "low",
                    "risk_level": "high",
                    "summary": "最终结论：方向偏空，置信度low，风险high。",
                    "warnings": ["final_decision 未获历史样本支持。"],
                    "why_not_more_bullish_or_bearish": "同业未确认或偏弱；历史样本不足或不可形成可靠倾向。",
                    "preflight_influence": {
                        "matched_rule_count": 1,
                        "applied_effects": ["raise_risk"],
                        "summary": "命中 1 条历史规则：提高风险等级。",
                    },
                },
                ready=False,
            )
        )

        text = " ".join([result["final_judgment"], result["one_line_summary"]])
        self.assertIn("偏弱", text)
        self.assertNotIn("强反转", text)
        self.assertNotIn("偏多延续", text)

    def test_ready_false_keeps_full_shape(self) -> None:
        result = build_projection_narrative(
            projection_v2_raw=_v2_result(
                ready=False,
                final_decision={
                    "kind": "final_decision",
                    "ready": False,
                    "final_direction": "unknown",
                    "final_confidence": "unknown",
                    "risk_level": "high",
                    "summary": "最终结论不可用：主分析不可用。",
                    "warnings": ["final_decision 不可用。"],
                    "why_not_more_bullish_or_bearish": "主分析不可用。",
                    "preflight_influence": {
                        "matched_rule_count": 0,
                        "applied_effects": [],
                        "summary": "未命中会影响最终结论的历史规则。",
                    },
                },
            )
        )

        self.assertFalse(result["ready"])
        self.assertEqual(
            sorted(result.keys()),
            sorted(
                [
                    "kind",
                    "symbol",
                    "ready",
                    "step1_conclusion",
                    "step2_peer_adjustment",
                    "final_judgment",
                    "open_tendency",
                    "intraday_structure",
                    "close_tendency",
                    "key_watchpoints",
                    "one_line_summary",
                    "warnings",
                ]
            ),
        )
        self.assertTrue(result["one_line_summary"])


if __name__ == "__main__":
    unittest.main()
