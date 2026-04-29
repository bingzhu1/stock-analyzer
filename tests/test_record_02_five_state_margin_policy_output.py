from __future__ import annotations

import sys
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.projection_three_systems_renderer import (  # noqa: E402
    build_confidence_evaluator,
    build_negative_system,
    build_record_02_projection_system,
)


_BASE_RECORD_02_KEYS = {
    "current_structure",
    "main_projection",
    "five_state_top1",
    "five_state_projection",
    "final_direction",
    "open_path_close_projection",
    "historical_sample_summary",
    "peer_market_confirmation",
    "key_price_levels",
    "risk_notes",
    "final_summary",
}

_MARGIN_POLICY_KEYS = {
    "five_state_display_state",
    "five_state_margin_band",
    "five_state_top2_states",
    "five_state_top1_margin",
    "five_state_secondary_state",
    "five_state_secondary_probability",
    "five_state_state_conflict",
    "five_state_policy_note",
}


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


class LowMarginOutputTests(unittest.TestCase):
    def test_low_margin_adds_display_state_without_overwriting_original_fields(self) -> None:
        result = build_record_02_projection_system(_v2_low_margin())
        self.assertEqual(result["five_state_top1"], "震荡")
        self.assertEqual(result["final_direction"], "偏多")
        self.assertEqual(result["five_state_display_state"], "震荡/小涨分歧")
        self.assertEqual(result["five_state_top2_states"], ["震荡", "小涨"])
        self.assertEqual(result["five_state_margin_band"], "low_margin")
        self.assertAlmostEqual(result["five_state_top1_margin"], 0.03, places=6)
        self.assertEqual(result["five_state_secondary_state"], "小涨")
        self.assertAlmostEqual(result["five_state_secondary_probability"], 0.42, places=6)
        self.assertTrue(result["five_state_state_conflict"])

    def test_existing_record_02_fields_still_present(self) -> None:
        result = build_record_02_projection_system(_v2_low_margin())
        self.assertTrue(_BASE_RECORD_02_KEYS.issubset(set(result.keys())))
        self.assertTrue(_MARGIN_POLICY_KEYS.issubset(set(result.keys())))
        self.assertEqual(result["five_state_projection"]["震荡"], 0.45)
        self.assertIn("偏多", result["main_projection"])
        self.assertIn("最终结论", result["final_summary"])


class ClearTop1Tests(unittest.TestCase):
    def test_clear_top1_uses_original_top1_as_display_state(self) -> None:
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
        self.assertEqual(result["five_state_top1"], "震荡")
        self.assertEqual(result["five_state_display_state"], "震荡")
        self.assertEqual(result["five_state_margin_band"], "clear_top1")
        self.assertFalse(result["five_state_state_conflict"])


class MalformedDistributionTests(unittest.TestCase):
    def test_malformed_distribution_returns_unknown_margin_fields_but_no_crash(self) -> None:
        v2 = _v2_low_margin()
        v2["main_projection"]["state_probabilities"] = {
            "震荡": "bad",
            "小涨": 0.42,
        }
        result = build_record_02_projection_system(v2)
        self.assertEqual(result["five_state_top1"], "震荡")
        self.assertEqual(result["five_state_projection"], {"小涨": 0.42})
        self.assertEqual(result["five_state_display_state"], "unknown")
        self.assertEqual(result["five_state_margin_band"], "unknown")
        self.assertEqual(result["five_state_top2_states"], [])
        self.assertIsNone(result["five_state_top1_margin"])
        self.assertFalse(result["five_state_state_conflict"])
        self.assertTrue(result["five_state_policy_note"])


class SiblingSystemsUnchangedTests(unittest.TestCase):
    def test_confidence_evaluator_unchanged(self) -> None:
        result = build_confidence_evaluator(_v2_low_margin())
        self.assertEqual(result["projection_system_confidence"]["level"], "medium")
        self.assertEqual(result["projection_system_confidence"]["score"], 0.6)
        # Task 110 — non-excluded normal case caps at medium (no auto-high).
        self.assertEqual(result["negative_system_confidence"]["level"], "medium")
        self.assertEqual(result["overall_confidence"]["level"], "medium")

    def test_negative_system_unchanged(self) -> None:
        result = build_negative_system(_v2_low_margin())
        self.assertEqual(result["excluded_states"], [])
        self.assertEqual(result["strength"], "none")
        self.assertIn("未触发", result["conclusion"])

    def test_renderer_does_not_mutate_input(self) -> None:
        v2 = _v2_low_margin()
        before = deepcopy(v2)
        build_record_02_projection_system(v2)
        self.assertEqual(v2, before)


if __name__ == "__main__":
    unittest.main()
