from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.projection_three_systems_renderer import (  # noqa: E402
    build_confidence_evaluator,
    build_negative_system,
    build_record_02_projection_system,
)


def _v2_low_margin() -> dict:
    return {
        "kind": "projection_v2_report",
        "symbol": "AVGO",
        "ready": True,
        "primary_analysis": {
            "ready": True,
            "direction": "偏多",
            "position_label": "中位",
            "stage_label": "整理",
            "volume_state": "正常",
            "summary": "主分析偏多。",
            "warnings": [],
        },
        "peer_adjustment": {
            "ready": True,
            "confirmation_level": "confirmed",
            "adjustment": "reinforce_bullish",
            "summary": "peers 支持偏多。",
            "warnings": [],
        },
        "historical_probability": {
            "ready": True,
            "sample_count": 18,
            "sample_quality": "enough",
            "historical_bias": "supports_bullish",
            "summary": "历史样本偏多。",
            "warnings": [],
        },
        "final_decision": {
            "ready": True,
            "final_direction": "偏多",
            "final_confidence": "medium",
            "risk_level": "medium",
            "summary": "最终结论：方向偏多。",
            "warnings": [],
            "layer_contributions": {
                "primary": "主分析偏多。",
                "peer": "peer 支持偏多。",
                "historical": "历史概率偏多。",
            },
            "why_not_more_bullish_or_bearish": "保留震荡扰动。",
        },
        "exclusion_result": {
            "excluded": False,
            "action": "allow",
            "triggered_rule": None,
            "summary": "排除层未触发。",
            "reasons": [],
            "peer_alignment": {
                "alignment": "neutral",
                "available_peer_count": 3,
            },
            "feature_snapshot": {
                "pos20": 65.0,
                "vol_ratio20": 1.05,
                "upper_shadow_ratio": 0.2,
                "lower_shadow_ratio": 0.1,
                "ret1": 0.4,
                "ret3": 1.1,
                "ret5": 1.8,
            },
        },
        "main_projection": {
            "ready": True,
            "predicted_top1": {"state": "震荡", "probability": 0.45},
            "predicted_top2": {"state": "小涨", "probability": 0.42},
            "state_probabilities": {
                "大涨": 0.00,
                "小涨": 0.42,
                "震荡": 0.45,
                "小跌": 0.11,
                "大跌": 0.02,
            },
            "warnings": [],
        },
        "consistency": {
            "consistency_flag": "consistent",
            "summary": "一致性良好。",
            "conflict_reasons": [],
        },
        "step_status": {
            "primary_analysis": "success",
            "peer_adjustment": "success",
            "historical_probability": "success",
            "final_decision": "success",
        },
    }


class LowMarginDisplaySummaryTests(unittest.TestCase):
    def test_low_margin_summary_includes_display_state(self) -> None:
        result = build_record_02_projection_system(_v2_low_margin())
        self.assertIn("震荡/小涨分歧", result["five_state_display_summary"])

    def test_summary_mentions_original_top1(self) -> None:
        result = build_record_02_projection_system(_v2_low_margin())
        self.assertIn("原始 top1 为震荡", result["five_state_display_summary"])

    def test_summary_mentions_split_context(self) -> None:
        result = build_record_02_projection_system(_v2_low_margin())
        summary = result["five_state_display_summary"]
        self.assertTrue("小涨" in summary and ("接近" in summary or "分歧" in summary))

    def test_summary_mentions_final_direction_bias_duo(self) -> None:
        result = build_record_02_projection_system(_v2_low_margin())
        self.assertIn("final_direction=偏多", result["five_state_display_summary"])

    def test_summary_does_not_reduce_to_only_zhen_dang(self) -> None:
        result = build_record_02_projection_system(_v2_low_margin())
        summary = result["five_state_display_summary"]
        self.assertNotEqual(summary, "五状态：震荡")
        self.assertIn("微弱优势", summary)


class ClearTop1DisplaySummaryTests(unittest.TestCase):
    def test_clear_top1_case_can_just_show_primary_state(self) -> None:
        v2 = _v2_low_margin()
        v2["final_decision"]["final_direction"] = "震荡"
        v2["main_projection"]["predicted_top1"] = {"state": "震荡", "probability": 0.55}
        v2["main_projection"]["predicted_top2"] = {"state": "小涨", "probability": 0.20}
        v2["main_projection"]["state_probabilities"] = {
            "大涨": 0.01,
            "小涨": 0.20,
            "震荡": 0.55,
            "小跌": 0.18,
            "大跌": 0.06,
        }
        result = build_record_02_projection_system(v2)
        summary = result["five_state_display_summary"]
        self.assertIn("当前展示为震荡", summary)
        self.assertNotIn("分歧", summary)


class StabilityTests(unittest.TestCase):
    def test_original_five_state_top1_remains_unchanged(self) -> None:
        result = build_record_02_projection_system(_v2_low_margin())
        self.assertEqual(result["five_state_top1"], "震荡")

    def test_original_final_direction_remains_unchanged(self) -> None:
        result = build_record_02_projection_system(_v2_low_margin())
        self.assertEqual(result["final_direction"], "偏多")

    def test_negative_system_unchanged(self) -> None:
        result = build_negative_system(_v2_low_margin())
        self.assertEqual(result["excluded_states"], [])
        self.assertEqual(result["strength"], "none")

    def test_confidence_evaluator_unchanged(self) -> None:
        result = build_confidence_evaluator(_v2_low_margin())
        self.assertEqual(result["projection_system_confidence"]["level"], "medium")
        self.assertEqual(result["overall_confidence"]["level"], "medium")

    def test_all_existing_record_02_fields_still_present(self) -> None:
        result = build_record_02_projection_system(_v2_low_margin())
        for key in (
            "five_state_top1",
            "five_state_projection",
            "final_direction",
            "main_projection",
            "final_summary",
        ):
            self.assertIn(key, result)

    def test_unknown_margin_case_degrades_safely(self) -> None:
        v2 = _v2_low_margin()
        v2["main_projection"]["state_probabilities"] = {"震荡": "bad", "小涨": 0.42}
        result = build_record_02_projection_system(v2)
        self.assertEqual(result["five_state_display_state"], "unknown")
        self.assertIn("暂不可用", result["five_state_display_summary"])
        self.assertEqual(result["five_state_margin_band"], "unknown")


if __name__ == "__main__":
    unittest.main()
