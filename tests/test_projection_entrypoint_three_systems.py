from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.projection_entrypoint import run_projection_entrypoint


_PACKAGED_RESULT = {
    "symbol": "AVGO",
    "ready": True,
    "advisory_only": False,
    "projection_schema": "v2",
    "source_of_truth": "projection_v2_raw",
    "projection_v2_raw": {"kind": "projection_v2_report", "ready": True},
    "legacy_compat": {"projection_report": "legacy_fallback", "advisory": "legacy_fallback"},
    "projection_report": {"kind": "final_projection_report"},
    "request": {"symbol": "AVGO", "error_category": None, "limit": 5, "lookback_days": None},
    "advisory": {"matched_count": 0, "caution_level": "none", "reminder_lines": []},
    "notes": [],
}


def _v2_payload(ready: bool = True) -> dict:
    return {
        "kind": "projection_v2_report",
        "symbol": "AVGO",
        "ready": ready,
        "exclusion_result": {
            "excluded": False,
            "action": "allow",
            "triggered_rule": None,
            "reasons": [],
            "peer_alignment": {"alignment": "neutral", "available_peer_count": 3},
            "feature_snapshot": {
                "pos20": 60.0,
                "vol_ratio20": 1.0,
                "upper_shadow_ratio": 0.2,
                "lower_shadow_ratio": 0.15,
                "ret1": 0.5,
                "ret3": 1.0,
                "ret5": 1.5,
            },
        },
        "primary_analysis": {
            "kind": "primary_20day_analysis",
            "ready": ready,
            "direction": "偏多" if ready else "unknown",
            "confidence": "medium" if ready else "unknown",
            "summary": "主分析示例。",
            "warnings": [],
        },
        "peer_adjustment": {
            "kind": "peer_adjustment",
            "ready": ready,
            "adjustment": "no_change" if ready else "missing",
            "summary": "peers 无变化。",
            "warnings": [],
        },
        "historical_probability": {
            "kind": "historical_probability",
            "ready": ready,
            "sample_count": 5 if ready else 0,
            "historical_bias": "mixed" if ready else "missing",
            "impact": "no_effect" if ready else "missing",
            "summary": "历史概率层示例。",
            "warnings": [],
        },
        "final_decision": {
            "kind": "final_decision",
            "ready": ready,
            "final_direction": "偏多" if ready else "unknown",
            "final_confidence": "medium" if ready else "unknown",
            "risk_level": "medium" if ready else "high",
            "summary": "示例最终结论。",
            "layer_contributions": {},
            "warnings": [],
            "why_not_more_bullish_or_bearish": "示例约束。",
        },
        "main_projection": {
            "kind": "main_projection_layer",
            "ready": ready,
            "predicted_top1": {"state": "震荡", "probability": 0.35},
            "predicted_top2": {"state": "小涨", "probability": 0.25},
            "state_probabilities": {
                "大涨": 0.10,
                "小涨": 0.25,
                "震荡": 0.35,
                "小跌": 0.20,
                "大跌": 0.10,
            },
            "warnings": [],
        },
        "consistency": {
            "consistency_flag": "consistent",
            "conflict_reasons": [],
            "summary": "一致。",
        },
        "step_status": {
            "preflight": "success",
            "primary_analysis": "success" if ready else "failed",
            "peer_adjustment": "success",
            "historical_probability": "success",
            "final_decision": "success" if ready else "failed",
        },
        "warnings": [],
    }


class EntrypointThreeSystemsIntegrationTests(unittest.TestCase):
    def test_three_systems_field_present_alongside_narrative(self) -> None:
        with patch(
            "services.projection_entrypoint.run_projection_v2",
            return_value=_v2_payload(ready=True),
        ), patch(
            "services.projection_entrypoint.build_projection_entrypoint_result",
            return_value=dict(_PACKAGED_RESULT),
        ):
            result = run_projection_entrypoint(symbol="AVGO")

        self.assertIn("projection_narrative", result)
        self.assertIn("projection_three_systems", result)
        three = result["projection_three_systems"]
        self.assertEqual(three["kind"], "projection_three_systems")
        self.assertEqual(three["symbol"], "AVGO")
        self.assertTrue(three["ready"])
        self.assertEqual(
            set(three.keys()),
            {"kind", "symbol", "ready", "negative_system",
             "record_02_projection_system", "confidence_evaluator"},
        )

    def test_three_systems_keeps_legacy_fields_unchanged(self) -> None:
        with patch(
            "services.projection_entrypoint.run_projection_v2",
            return_value=_v2_payload(ready=True),
        ), patch(
            "services.projection_entrypoint.build_projection_entrypoint_result",
            return_value=dict(_PACKAGED_RESULT),
        ):
            result = run_projection_entrypoint(symbol="AVGO")

        self.assertEqual(result["projection_schema"], "v2")
        self.assertEqual(result["source_of_truth"], "projection_v2_raw")
        self.assertEqual(result["projection_report"]["kind"], "final_projection_report")
        self.assertEqual(result["projection_v2_raw"]["kind"], "projection_v2_report")
        self.assertEqual(result["legacy_compat"]["projection_report"], "legacy_fallback")

    def test_three_systems_degraded_when_renderer_raises(self) -> None:
        with patch(
            "services.projection_entrypoint.run_projection_v2",
            return_value=_v2_payload(ready=True),
        ), patch(
            "services.projection_entrypoint.build_projection_entrypoint_result",
            return_value=dict(_PACKAGED_RESULT),
        ), patch(
            "services.projection_entrypoint.build_projection_three_systems",
            side_effect=RuntimeError("boom"),
        ):
            result = run_projection_entrypoint(symbol="AVGO")

        three = result["projection_three_systems"]
        self.assertEqual(three["kind"], "projection_three_systems")
        self.assertFalse(three["ready"])
        self.assertEqual(three["confidence_evaluator"]["overall_confidence"]["level"], "unknown")
        self.assertTrue(
            any("Projection three-systems degraded" in note for note in result["notes"]),
            msg=result["notes"],
        )

    def test_three_systems_unready_when_v2_unready(self) -> None:
        with patch(
            "services.projection_entrypoint.run_projection_v2",
            return_value=_v2_payload(ready=False),
        ), patch(
            "services.projection_entrypoint.build_projection_entrypoint_result",
            return_value=dict(_PACKAGED_RESULT),
        ):
            result = run_projection_entrypoint(symbol="AVGO")

        three = result["projection_three_systems"]
        self.assertFalse(three["ready"])
        self.assertEqual(set(three["negative_system"].keys()),
                         {"conclusion", "excluded_states", "strength",
                          "evidence", "invalidating_conditions", "risk_notes"})


if __name__ == "__main__":
    unittest.main()
