from __future__ import annotations

import sys
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.projection_three_systems_renderer import (
    build_confidence_evaluator,
    build_negative_system,
    build_projection_three_systems,
    build_record_02_projection_system,
)


_TOP_LEVEL_KEYS = {
    "kind",
    "symbol",
    "ready",
    "negative_system",
    "record_02_projection_system",
    "confidence_evaluator",
}

_NEGATIVE_KEYS = {
    "conclusion",
    "excluded_states",
    "strength",
    "evidence",
    "invalidating_conditions",
    "risk_notes",
}

_RECORD_02_KEYS = {
    "current_structure",
    "main_projection",
    "five_state_top1",
    "five_state_projection",
    "final_direction",
    "five_state_display_state",
    "five_state_margin_band",
    "five_state_top2_states",
    "five_state_top1_margin",
    "five_state_secondary_state",
    "five_state_secondary_probability",
    "five_state_state_conflict",
    "five_state_policy_note",
    "five_state_display_summary",
    "open_path_close_projection",
    "historical_sample_summary",
    "peer_market_confirmation",
    "key_price_levels",
    "risk_notes",
    "final_summary",
}

_CONFIDENCE_KEYS = {
    "negative_system_confidence",
    "projection_system_confidence",
    "overall_confidence",
    "conflicts",
    "reliability_warnings",
}


def _v2_happy() -> dict:
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
            "position_label": "高位",
            "stage_label": "延续",
            "volume_state": "正常",
            "summary": "最近20天主分析偏多。",
            "warnings": [],
        },
        "peer_adjustment": {
            "kind": "peer_adjustment",
            "ready": True,
            "confirmation_level": "confirmed",
            "adjustment": "reinforce_bullish",
            "summary": "peers 支持主分析偏多。",
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
            "combined_probability": {"strong_close_rate": 0.7, "method": "blended"},
            "warnings": [],
        },
        "final_decision": {
            "kind": "final_decision",
            "ready": True,
            "final_direction": "偏多",
            "final_confidence": "medium",
            "risk_level": "medium",
            "summary": "最终结论：方向偏多，置信度medium，风险medium。",
            "warnings": [],
            "layer_contributions": {
                "primary": "主分析给出偏多。",
                "peer": "peer 修正强化主分析方向。",
                "historical": "历史概率层支持当前方向。",
                "preflight": "preflight 未命中规则。",
            },
            "why_not_more_bullish_or_bearish": "MVP 决策层不做更激进加权。",
        },
        "exclusion_result": {
            "excluded": False,
            "action": "allow",
            "triggered_rule": None,
            "summary": "排除层未形成足够强的极端排除证据。",
            "reasons": [],
            "peer_alignment": {
                "alignment": "neutral",
                "up_support": "partial",
                "down_support": "unsupported",
                "available_peer_count": 3,
            },
            "feature_snapshot": {
                "pos20": 65.0,
                "vol_ratio20": 1.05,
                "upper_shadow_ratio": 0.20,
                "lower_shadow_ratio": 0.15,
                "ret1": 0.5,
                "ret3": 1.2,
                "ret5": 2.0,
            },
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
            "consistency_score": 0.9,
            "conflict_reasons": [],
            "summary": "一致性良好。",
        },
        "step_status": {
            "preflight": "success",
            "primary_analysis": "success",
            "peer_adjustment": "success",
            "historical_probability": "success",
            "final_decision": "success",
        },
        "warnings": [],
    }


def _v2_excluded_big_up() -> dict:
    base = _v2_happy()
    base["exclusion_result"] = {
        "excluded": True,
        "action": "exclude",
        "triggered_rule": "exclude_big_up",
        "summary": "排除层判断：明天不太可能大涨。",
        "reasons": [
            "pos20=88.0，位置偏高。",
            "vol_ratio20=0.85，量能偏缩。",
            "upper_shadow_ratio=0.42，上影偏长。",
            "ret3 短期透支。",
            "peers 不支持上行。",
        ],
        "peer_alignment": {
            "alignment": "neutral",
            "up_support": "unsupported",
            "down_support": "partial",
            "available_peer_count": 3,
        },
        "feature_snapshot": {
            "pos20": 88.0,
            "vol_ratio20": 0.85,
            "upper_shadow_ratio": 0.42,
            "lower_shadow_ratio": 0.10,
            "ret1": 1.5,
            "ret3": 5.0,
            "ret5": 7.5,
        },
    }
    base["main_projection"] = {
        "kind": "main_projection_layer",
        "ready": True,
        "predicted_top1": {"state": "震荡", "probability": 0.40},
        "predicted_top2": {"state": "小跌", "probability": 0.25},
        "state_probabilities": {
            "大涨": 0.0,
            "小涨": 0.20,
            "震荡": 0.40,
            "小跌": 0.25,
            "大跌": 0.15,
        },
        "warnings": [],
    }
    return base


class NegativeSystemTests(unittest.TestCase):
    def test_shape_keys(self) -> None:
        result = build_negative_system(_v2_happy())
        self.assertEqual(set(result.keys()), _NEGATIVE_KEYS)

    def test_not_excluded_returns_empty_states_and_none_strength(self) -> None:
        result = build_negative_system(_v2_happy())
        self.assertEqual(result["excluded_states"], [])
        self.assertEqual(result["strength"], "none")
        self.assertTrue(result["conclusion"])
        self.assertIn("未形成", result["conclusion"])

    def test_excluded_big_up_marks_state_and_strength(self) -> None:
        result = build_negative_system(_v2_excluded_big_up())
        self.assertEqual(result["excluded_states"], ["大涨"])
        self.assertEqual(result["strength"], "high")
        self.assertIn("大涨", result["conclusion"])
        self.assertTrue(result["evidence"])
        self.assertTrue(result["invalidating_conditions"])

    def test_missing_exclusion_returns_safe_shape(self) -> None:
        result = build_negative_system({})
        self.assertEqual(set(result.keys()), _NEGATIVE_KEYS)
        self.assertEqual(result["excluded_states"], [])
        self.assertIn(result["strength"], {"none", "low"})


class Record02ProjectionSystemTests(unittest.TestCase):
    def test_shape_keys(self) -> None:
        result = build_record_02_projection_system(_v2_happy())
        self.assertEqual(set(result.keys()), _RECORD_02_KEYS)
        self.assertEqual(
            set(result["open_path_close_projection"].keys()),
            {"open", "intraday", "close"},
        )

    def test_happy_includes_distribution(self) -> None:
        result = build_record_02_projection_system(_v2_happy())
        self.assertIn("小涨", result["five_state_projection"])
        self.assertGreater(result["five_state_projection"]["小涨"], 0)
        self.assertIn("偏多", result["main_projection"])
        self.assertIn("偏多", result["current_structure"])

    def test_primary_failed_keeps_shape_and_uses_safe_text(self) -> None:
        v2 = _v2_happy()
        v2["primary_analysis"] = {
            "kind": "primary_20day_analysis",
            "ready": False,
            "direction": "unknown",
            "confidence": "unknown",
            "summary": "主分析不可用。",
        }
        v2["final_decision"] = {
            "kind": "final_decision",
            "ready": False,
            "final_direction": "unknown",
            "final_confidence": "unknown",
            "risk_level": "high",
            "summary": "最终结论不可用：主分析不可用。",
            "warnings": ["final_decision 不可用。"],
        }
        v2["main_projection"] = {
            "kind": "main_projection_layer",
            "ready": False,
            "predicted_top1": {"state": None, "probability": None},
            "state_probabilities": {},
            "warnings": ["主推演层不可用。"],
        }
        result = build_record_02_projection_system(v2)
        self.assertEqual(set(result.keys()), _RECORD_02_KEYS)
        self.assertEqual(result["five_state_projection"], {})
        self.assertIn("不可用", result["main_projection"])
        self.assertIn("不可用", result["current_structure"])
        self.assertIn("暂不明确", result["open_path_close_projection"]["open"])


class ConfidenceEvaluatorTests(unittest.TestCase):
    def test_shape_keys(self) -> None:
        result = build_confidence_evaluator(_v2_happy())
        self.assertEqual(set(result.keys()), _CONFIDENCE_KEYS)
        for sub in ("negative_system_confidence", "projection_system_confidence"):
            self.assertEqual(
                set(result[sub].keys()),
                {"score", "level", "reasoning", "risks"},
            )
        self.assertEqual(
            set(result["overall_confidence"].keys()),
            {"score", "level", "reasoning"},
        )

    def test_happy_levels_match_score_mapping(self) -> None:
        result = build_confidence_evaluator(_v2_happy())
        # final_confidence=medium -> projection level medium -> score 0.6
        self.assertEqual(result["projection_system_confidence"]["level"], "medium")
        self.assertEqual(result["projection_system_confidence"]["score"], 0.6)
        # exclusion not triggered, all features present -> negative high
        self.assertEqual(result["negative_system_confidence"]["level"], "high")
        self.assertEqual(result["negative_system_confidence"]["score"], 0.9)
        # overall = min(high, medium) = medium
        self.assertEqual(result["overall_confidence"]["level"], "medium")
        self.assertEqual(result["overall_confidence"]["score"], 0.6)
        self.assertEqual(result["conflicts"], [])

    def test_excluded_big_up_negative_high_confidence(self) -> None:
        result = build_confidence_evaluator(_v2_excluded_big_up())
        self.assertEqual(result["negative_system_confidence"]["level"], "high")

    def test_consistency_conflict_downgrades_overall(self) -> None:
        v2 = _v2_happy()
        v2["consistency"]["conflict_reasons"] = ["主推演与历史方向不一致。"]
        v2["consistency"]["consistency_flag"] = "conflict"
        result = build_confidence_evaluator(v2)
        self.assertTrue(result["conflicts"])
        self.assertIn(result["overall_confidence"]["level"], {"low", "unknown"})

    def test_final_unready_yields_unknown_projection_level(self) -> None:
        v2 = _v2_happy()
        v2["final_decision"]["ready"] = False
        v2["final_decision"]["final_confidence"] = "unknown"
        result = build_confidence_evaluator(v2)
        self.assertEqual(result["projection_system_confidence"]["level"], "unknown")
        self.assertIsNone(result["projection_system_confidence"]["score"])


class BuildProjectionThreeSystemsTests(unittest.TestCase):
    def test_top_level_shape(self) -> None:
        result = build_projection_three_systems(_v2_happy())
        self.assertEqual(set(result.keys()), _TOP_LEVEL_KEYS)
        self.assertEqual(result["kind"], "projection_three_systems")
        self.assertEqual(result["symbol"], "AVGO")
        self.assertTrue(result["ready"])

    def test_empty_v2_returns_safe_shape(self) -> None:
        for empty in (None, {}, "not-a-dict"):
            result = build_projection_three_systems(empty)
            self.assertEqual(set(result.keys()), _TOP_LEVEL_KEYS)
            self.assertFalse(result["ready"])
            self.assertEqual(set(result["negative_system"].keys()), _NEGATIVE_KEYS)
            self.assertEqual(set(result["record_02_projection_system"].keys()), _RECORD_02_KEYS)
            self.assertEqual(set(result["confidence_evaluator"].keys()), _CONFIDENCE_KEYS)
            self.assertTrue(result["confidence_evaluator"]["reliability_warnings"])

    def test_does_not_mutate_input(self) -> None:
        v2 = _v2_happy()
        before = deepcopy(v2)
        build_projection_three_systems(v2)
        self.assertEqual(v2, before)

    def test_symbol_override_and_uppercase(self) -> None:
        v2 = _v2_happy()
        del v2["symbol"]
        result = build_projection_three_systems(v2, symbol="msft")
        self.assertEqual(result["symbol"], "MSFT")

    def test_excluded_top1_conflict_recorded(self) -> None:
        v2 = _v2_happy()
        v2["exclusion_result"] = {
            "excluded": True,
            "action": "exclude",
            "triggered_rule": "exclude_big_up",
            "summary": "排除大涨。",
            "reasons": ["a", "b", "c"],
            "peer_alignment": {"alignment": "neutral", "available_peer_count": 3},
            "feature_snapshot": {
                "pos20": 88.0,
                "vol_ratio20": 0.8,
                "upper_shadow_ratio": 0.4,
                "lower_shadow_ratio": 0.1,
                "ret1": 1.0,
                "ret3": 4.0,
                "ret5": 7.5,
            },
        }
        v2["main_projection"]["predicted_top1"] = {"state": "大涨", "probability": 0.50}
        result = build_projection_three_systems(v2)
        self.assertTrue(
            any("大涨" in conflict for conflict in result["confidence_evaluator"]["conflicts"]),
            msg=result["confidence_evaluator"]["conflicts"],
        )


if __name__ == "__main__":
    unittest.main()
