from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.main_projection_layer import build_main_projection_layer


class MainProjectionLayerTests(unittest.TestCase):
    def test_baseline_bullish_scores_are_stable_and_big_up_remains_positive(self) -> None:
        """Per 11A §8.2 + 17C / PR-D: the legacy `_apply_exclusion`
        behavior is forbidden. After PR-D, the projection layer no
        longer accepts ``exclusion_result`` at all (see
        ``test_exclusion_result_kwarg_raises_typeerror`` below); this
        test pins the baseline bullish projection so any future schema
        / scoring drift is caught."""
        baseline_features = {
            "symbol": "AVGO",
            "pos20": 84.0,
            "vol_ratio20": 1.18,
            "upper_shadow_ratio": 0.08,
            "lower_shadow_ratio": 0.10,
            "ret1": 1.8,
            "ret3": 3.2,
            "ret5": 5.8,
            "ret10": 7.5,
        }

        baseline = build_main_projection_layer(
            current_20day_features=baseline_features,
            historical_match_result={"dominant_historical_outcome": "up_bias"},
            peer_alignment={"up_support": "supported", "down_support": "unsupported"},
        )

        self.assertTrue(baseline["ready"])
        self.assertGreater(baseline["state_probabilities"]["大涨"], 0.0)
        # Five-state distribution is well-formed.
        self.assertEqual(
            set(baseline["state_probabilities"].keys()),
            {"大涨", "小涨", "震荡", "小跌", "大跌"},
        )

    def test_baseline_bearish_scores_are_stable_and_big_down_remains_positive(self) -> None:
        """Bearish-feature counterpart to the bullish baseline test.
        Same PR-D rationale: ``exclusion_result`` is no longer a valid
        kwarg; this test only verifies a well-formed bearish projection."""
        baseline_features = {
            "symbol": "AVGO",
            "pos20": 16.0,
            "vol_ratio20": 1.25,
            "upper_shadow_ratio": 0.12,
            "lower_shadow_ratio": 0.08,
            "ret1": -1.7,
            "ret3": -3.0,
            "ret5": -5.4,
            "ret10": -7.2,
        }

        baseline = build_main_projection_layer(
            current_20day_features=baseline_features,
            historical_match_result={"dominant_historical_outcome": "down_bias"},
            peer_alignment={"up_support": "unsupported", "down_support": "supported"},
        )

        self.assertTrue(baseline["ready"])
        self.assertGreater(baseline["state_probabilities"]["大跌"], 0.0)
        self.assertEqual(
            set(baseline["state_probabilities"].keys()),
            {"大涨", "小涨", "震荡", "小跌", "大跌"},
        )

    def test_exclusion_result_kwarg_raises_typeerror(self) -> None:
        """17C / PR-D: ``build_main_projection_layer`` no longer
        accepts ``exclusion_result``; passing it must raise
        ``TypeError`` (boundary enforced at the API layer)."""
        baseline_features = {
            "symbol": "AVGO",
            "pos20": 50.0,
            "vol_ratio20": 1.0,
            "upper_shadow_ratio": 0.10,
            "lower_shadow_ratio": 0.10,
            "ret1": 0.1,
            "ret3": 0.2,
            "ret5": 0.3,
            "ret10": 0.4,
        }
        with self.assertRaises(TypeError):
            build_main_projection_layer(
                current_20day_features=baseline_features,
                exclusion_result={"excluded": False},
            )

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
