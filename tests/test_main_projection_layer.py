from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.main_projection_layer import build_main_projection_layer


class MainProjectionLayerTests(unittest.TestCase):
    def test_exclusion_of_big_up_prevents_big_up_top1(self) -> None:
        result = build_main_projection_layer(
            current_20day_features={
                "symbol": "AVGO",
                "pos20": 84.0,
                "vol_ratio20": 1.18,
                "upper_shadow_ratio": 0.08,
                "lower_shadow_ratio": 0.10,
                "ret1": 1.8,
                "ret3": 3.2,
                "ret5": 5.8,
                "ret10": 7.5,
            },
            exclusion_result={
                "excluded": True,
                "triggered_rule": "exclude_big_up",
                "peer_alignment": {
                    "up_support": "supported",
                    "down_support": "unsupported",
                },
            },
            historical_match_result={
                "dominant_historical_outcome": "up_bias",
            },
            peer_alignment={
                "up_support": "supported",
                "down_support": "unsupported",
            },
        )

        self.assertTrue(result["ready"])
        self.assertNotEqual(result["predicted_top1"]["state"], "大涨")
        self.assertEqual(result["predicted_top1"]["state"], "小涨")
        self.assertEqual(result["state_probabilities"]["大涨"], 0.0)
        self.assertTrue(any("禁止将大涨排为 Top1" in item for item in result["rationale"]))

    def test_exclusion_of_big_down_prevents_big_down_top1(self) -> None:
        result = build_main_projection_layer(
            current_20day_features={
                "symbol": "AVGO",
                "pos20": 16.0,
                "vol_ratio20": 1.25,
                "upper_shadow_ratio": 0.12,
                "lower_shadow_ratio": 0.08,
                "ret1": -1.7,
                "ret3": -3.0,
                "ret5": -5.4,
                "ret10": -7.2,
            },
            exclusion_result={
                "excluded": True,
                "triggered_rule": "exclude_big_down",
                "peer_alignment": {
                    "up_support": "unsupported",
                    "down_support": "supported",
                },
            },
            historical_match_result={
                "dominant_historical_outcome": "down_bias",
            },
            peer_alignment={
                "up_support": "unsupported",
                "down_support": "supported",
            },
        )

        self.assertTrue(result["ready"])
        self.assertNotEqual(result["predicted_top1"]["state"], "大跌")
        self.assertEqual(result["predicted_top1"]["state"], "小跌")
        self.assertEqual(result["state_probabilities"]["大跌"], 0.0)
        self.assertTrue(any("禁止将大跌排为 Top1" in item for item in result["rationale"]))

    def test_neutral_case_returns_stable_distribution_and_top2(self) -> None:
        result = build_main_projection_layer(
            current_20day_features={
                "symbol": "AVGO",
                "pos20": 51.0,
                "vol_ratio20": 0.98,
                "upper_shadow_ratio": 0.15,
                "lower_shadow_ratio": 0.16,
                "ret1": 0.1,
                "ret3": 0.4,
                "ret5": 0.8,
                "ret10": 1.0,
            },
            exclusion_result={"excluded": False},
            historical_match_result={},
            peer_alignment={
                "up_support": "partial",
                "down_support": "partial",
            },
        )

        self.assertTrue(result["ready"])
        self.assertEqual(result["predicted_top1"]["state"], "震荡")
        self.assertIn(result["predicted_top2"]["state"], {"小涨", "小跌"})
        self.assertEqual(set(result["state_probabilities"].keys()), {"大涨", "小涨", "震荡", "小跌", "大跌"})
        self.assertAlmostEqual(sum(result["state_probabilities"].values()), 1.0, places=4)
        self.assertTrue(result["rationale"])


if __name__ == "__main__":
    unittest.main()
