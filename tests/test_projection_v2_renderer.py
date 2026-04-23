from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.command_bar import _build_projection_response_card
from ui.projection_v2_renderer import build_projection_v2_display


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
                    "message": "高置信度场景需复核。",
                }
            ],
            "rule_warnings": ["历史提醒：高置信度场景需复核。"],
            "rule_adjustments": ["复核主方向。"],
            "summary": "命中 1 条历史规则提醒。",
            "warnings": [],
            "source_counts": {"memory_items": 1, "review_items": 0, "matched_rule_count": 1},
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
            "code_match": {
                "sample_count": 4,
                "up_rate": 0.75,
                "down_rate": 0.25,
                "summary": "同编码样本 4 个，上涨率 75.0%。",
            },
            "window_similarity": {
                "sample_count": 4,
                "up_rate": 0.5,
                "down_rate": 0.5,
                "avg_similarity": 0.88,
                "summary": "相似窗口样本 4 个，平均相似度 88.0%。",
            },
            "combined_probability": {
                "up_rate": 0.625,
                "down_rate": 0.375,
                "gap_up_rate": 0.5,
                "strong_close_rate": 0.5,
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
        "trace": [
            {"step": "preflight", "status": "success", "message": "命中 1 条历史规则提醒。"},
            {"step": "primary_analysis", "status": "success", "message": "主分析完成。"},
            {"step": "peer_adjustment", "status": "success", "message": "peer 调整完成。"},
            {"step": "historical_probability", "status": "success", "message": "历史概率完成。"},
            {"step": "final_decision", "status": "success", "message": "最终决策完成。"},
        ],
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


class ProjectionV2RendererTests(unittest.TestCase):
    def test_happy_path_renders_final_and_step_zero_to_four_sections(self) -> None:
        rendered = build_projection_v2_display(_v2_result())
        conclusion = "\n".join(rendered["conclusion"])
        evidence = "\n".join(rendered["evidence"])

        self.assertIn("最终方向：偏多", conclusion)
        self.assertIn("最终置信度：medium", conclusion)
        self.assertIn("风险等级：medium", conclusion)
        self.assertIn("Step 0 历史规则前置", evidence)
        self.assertIn("Step 1 最近20天主分析", evidence)
        self.assertIn("Step 2 peers 修正", evidence)
        self.assertIn("Step 3 历史概率层", evidence)
        self.assertIn("Step 4 最终结论", evidence)
        self.assertIn("规则影响：命中 1 条历史规则：下调置信度。", evidence)
        self.assertIn("combined_probability：method=blended", evidence)
        self.assertIn("trace：final_decision / success", evidence)

    def test_degraded_path_remains_readable_for_primary_peer_and_historical(self) -> None:
        degraded = _v2_result(
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
            },
            historical_probability={
                "kind": "historical_probability",
                "ready": False,
                "sample_count": 2,
                "sample_quality": "insufficient",
                "historical_bias": "insufficient",
                "impact": "missing",
                "summary": "历史样本不足：当前仅 2 个样本，不能形成可靠概率层。",
                "code_match": {"sample_count": 2, "summary": "同编码样本 2 个，样本仍偏少。"},
                "window_similarity": {"sample_count": 0, "summary": "相似窗口层缺少 feature_history，已降级。"},
                "combined_probability": {
                    "up_rate": None,
                    "down_rate": None,
                    "gap_up_rate": None,
                    "strong_close_rate": None,
                    "method": "fallback",
                },
                "warnings": ["historical_probability 样本或信号不足：sample_count=2。"],
            },
            final_decision={
                "kind": "final_decision",
                "ready": False,
                "final_direction": "unknown",
                "final_confidence": "unknown",
                "risk_level": "high",
                "summary": "最终结论不可用：主分析不可用，不能伪造完整结论。",
                "decision_factors": ["主分析不可用。"],
                "warnings": ["final_decision 未获历史样本支持。"],
                "layer_contributions": {
                    "primary": "主分析不可用，是阻断项。",
                    "peer": "未获 peers 确认。",
                    "historical": "未获得历史概率支持。",
                    "preflight": "preflight 未命中规则或未接入可用提醒。",
                },
                "why_not_more_bullish_or_bearish": "主分析不可用，不能判断是否更偏多或更偏空。",
                "preflight_influence": {
                    "matched_rule_count": 0,
                    "applied_effects": [],
                    "summary": "未命中会影响最终结论的历史规则。",
                },
            },
            warnings=["projection_v2 主链路已降级。"],
        )

        rendered = build_projection_v2_display(degraded)
        text = "\n".join(rendered["conclusion"] + rendered["evidence"] + rendered["warnings"])

        self.assertIn("主分析不可用", text)
        self.assertIn("未获 peers 确认", text)
        self.assertIn("历史样本不足", text)
        self.assertIn("combined_probability：method=fallback", text)
        self.assertTrue(rendered["warnings"])

    def test_command_bar_prefers_v2_raw_over_compat_projection_report(self) -> None:
        result = {
            "ready": True,
            "projection_v2_raw": _v2_result(),
            "projection_report": {
                "kind": "final_projection_report",
                "direction": "中性",
                "open_tendency": "平开",
                "close_tendency": "震荡",
                "confidence": "low",
                "basis_summary": ["旧 compat 层内容。"],
                "risk_reminders": ["旧 compat 提醒。"],
            },
        }

        card = _build_projection_response_card(result)
        conclusion = "\n".join(card["conclusion"])
        evidence = "\n".join(card["evidence"])

        self.assertIn("最终方向：偏多", conclusion)
        self.assertIn("Step 0 历史规则前置", evidence)
        self.assertNotIn("明日方向：中性", conclusion)
        self.assertNotIn("旧 compat 层内容。", evidence)

    def test_command_bar_falls_back_to_compat_when_v2_raw_missing(self) -> None:
        result = {
            "ready": True,
            "projection_report": {
                "kind": "final_projection_report",
                "direction": "中性",
                "open_tendency": "平开",
                "close_tendency": "震荡",
                "confidence": "low",
                "basis_summary": ["compat 依据。"],
                "risk_reminders": ["compat 风险提醒。"],
            },
        }

        card = _build_projection_response_card(result)
        conclusion = "\n".join(card["conclusion"])
        evidence = "\n".join(card["evidence"])

        self.assertIn("明日方向：中性", conclusion)
        self.assertIn("compat 依据。", evidence)


if __name__ == "__main__":
    unittest.main()
