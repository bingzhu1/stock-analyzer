from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.historical_probability import build_historical_probability


def _primary(direction: str = "偏多", confidence: str = "medium", ready: bool = True) -> dict:
    return {
        "kind": "primary_20day_analysis",
        "symbol": "AVGO",
        "ready": ready,
        "direction": direction,
        "confidence": confidence,
        "summary": f"主分析方向{direction}。",
        "basis": ["主分析依据。"],
    }


def _summary(
    *,
    exact: int = 4,
    near: int = 6,
    dominant: str = "up_bias",
    **extra: object,
) -> dict:
    result = {
        "exact_match_count": exact,
        "near_match_count": near,
        "dominant_historical_outcome": dominant,
        "top_context_score": 0.82,
    }
    result.update(extra)
    return result


def _coded_history_bullish() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Date": pd.to_datetime(
                [
                    "2026-01-01",
                    "2026-01-02",
                    "2026-01-03",
                    "2026-01-04",
                    "2026-01-05",
                    "2026-01-06",
                    "2026-01-07",
                    "2026-01-08",
                ]
            ),
            "Code": ["A", "B", "A", "B", "A", "B", "C", "A"],
            "O_gap": [0.0, 0.01, 0.0, -0.01, 0.0, 0.02, 0.0, 0.0],
            "C_move": [0.0, 0.02, 0.0, -0.02, 0.0, 0.015, 0.0, 0.0],
        }
    )


def _coded_history_insufficient() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Date": pd.to_datetime(
                ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04"]
            ),
            "Code": ["A", "B", "C", "A"],
            "O_gap": [0.0, 0.01, 0.0, 0.0],
            "C_move": [0.0, 0.02, 0.0, 0.0],
        }
    )


def _coded_history_with_future_sample() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Date": pd.to_datetime(
                [
                    "2026-01-01",
                    "2026-01-02",
                    "2026-01-03",
                    "2026-01-04",
                    "2026-01-05",
                    "2026-01-06",
                    "2026-01-07",
                    "2026-01-08",
                ]
            ),
            "Code": ["A", "B", "A", "B", "C", "A", "A", "B"],
            "O_gap": [0.0, 0.01, 0.0, -0.01, 0.0, 0.0, 0.0, 0.03],
            "C_move": [0.0, 0.02, 0.0, -0.02, 0.0, 0.0, 0.0, 0.03],
        }
    )


def _feature_history_bullish() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Date": pd.to_datetime(
                [
                    "2026-02-01",
                    "2026-02-02",
                    "2026-02-03",
                    "2026-02-04",
                    "2026-02-05",
                    "2026-02-06",
                    "2026-02-07",
                    "2026-02-08",
                    "2026-02-09",
                    "2026-02-10",
                    "2026-02-11",
                ]
            ),
            "feat_a": [10.0, 20.0, 900.0, 11.0, 21.0, 800.0, 9.0, 19.0, 850.0, 10.5, 20.5],
            "feat_b": [100.0, 200.0, 900.0, 101.0, 201.0, 800.0, 99.0, 199.0, 850.0, 100.5, 200.5],
            "O_gap": [0.0, 0.0, 0.01, 0.0, 0.0, -0.01, 0.0, 0.0, 0.02, 0.0, 0.0],
            "C_move": [0.0, 0.0, 0.02, 0.0, 0.0, -0.02, 0.0, 0.0, 0.03, 0.0, 0.0],
        }
    )


def _feature_history_bearish() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Date": pd.to_datetime(
                [
                    "2026-02-01",
                    "2026-02-02",
                    "2026-02-03",
                    "2026-02-04",
                    "2026-02-05",
                    "2026-02-06",
                    "2026-02-07",
                    "2026-02-08",
                    "2026-02-09",
                    "2026-02-10",
                    "2026-02-11",
                ]
            ),
            "feat_a": [10.0, 20.0, 900.0, 11.0, 21.0, 800.0, 9.0, 19.0, 850.0, 10.5, 20.5],
            "feat_b": [100.0, 200.0, 900.0, 101.0, 201.0, 800.0, 99.0, 199.0, 850.0, 100.5, 200.5],
            "O_gap": [0.0, 0.0, -0.01, 0.0, 0.0, -0.02, 0.0, 0.0, 0.01, 0.0, 0.0],
            "C_move": [0.0, 0.0, -0.02, 0.0, 0.0, -0.03, 0.0, 0.0, 0.01, 0.0, 0.0],
        }
    )


def _feature_history_insufficient() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Date": pd.to_datetime(
                [
                    "2026-02-01",
                    "2026-02-02",
                    "2026-02-03",
                    "2026-02-04",
                    "2026-02-05",
                    "2026-02-06",
                ]
            ),
            "feat_a": [10.0, 20.0, 900.0, 11.0, 21.0, 22.0],
            "feat_b": [100.0, 200.0, 900.0, 101.0, 201.0, 202.0],
            "O_gap": [0.0, 0.0, 0.01, 0.0, 0.0, 0.0],
            "C_move": [0.0, 0.0, 0.02, 0.0, 0.0, 0.0],
        }
    )


class HistoricalProbabilityTests(unittest.TestCase):
    def test_same_code_happy_path_builds_real_code_probability(self) -> None:
        result = build_historical_probability(
            primary_analysis=_primary("偏多"),
            coded_history=_coded_history_bullish(),
            as_of_date="2026-01-08",
        )

        self.assertTrue(result["ready"])
        self.assertEqual(result["combined_probability"]["method"], "code_only")
        self.assertEqual(result["code_match"]["sample_count"], 3)
        self.assertAlmostEqual(result["code_match"]["up_rate"], 0.6667, places=4)
        self.assertAlmostEqual(result["code_match"]["down_rate"], 0.3333, places=4)
        self.assertEqual(result["historical_bias"], "supports_bullish")
        self.assertEqual(result["impact"], "support")
        self.assertIn("同编码样本 3 个", result["code_match"]["summary"])

    def test_same_code_insufficient_does_not_fake_support(self) -> None:
        result = build_historical_probability(
            primary_analysis=_primary("偏多"),
            coded_history=_coded_history_insufficient(),
            as_of_date="2026-01-04",
        )

        self.assertFalse(result["ready"])
        self.assertEqual(result["combined_probability"]["method"], "fallback")
        self.assertEqual(result["code_match"]["sample_count"], 1)
        self.assertEqual(result["sample_quality"], "insufficient")
        self.assertEqual(result["historical_bias"], "insufficient")
        self.assertEqual(result["impact"], "missing")
        self.assertNotIn("支持当前主分析方向", result["summary"])

    def test_similar_window_happy_path_builds_window_probability(self) -> None:
        result = build_historical_probability(
            primary_analysis=_primary("偏多"),
            feature_history=_feature_history_bullish(),
            context_features={"window_days": 2, "top_k": 3},
            as_of_date="2026-02-11",
        )

        self.assertTrue(result["ready"])
        self.assertEqual(result["combined_probability"]["method"], "window_only")
        self.assertEqual(result["window_similarity"]["sample_count"], 3)
        self.assertAlmostEqual(result["window_similarity"]["up_rate"], 0.6667, places=4)
        self.assertAlmostEqual(result["window_similarity"]["down_rate"], 0.3333, places=4)
        self.assertIsNotNone(result["window_similarity"]["avg_similarity"])
        self.assertIn("平均相似度", result["window_similarity"]["summary"])

    def test_feature_history_missing_degrades_cleanly(self) -> None:
        result = build_historical_probability(
            primary_analysis=_primary("偏多"),
            feature_history=None,
            context_features={"window_days": 2},
        )

        self.assertFalse(result["ready"])
        self.assertEqual(result["window_similarity"]["sample_count"], 0)
        self.assertTrue(any("window_similarity" in warning for warning in result["warnings"]))

    def test_code_only_path_sets_combined_method(self) -> None:
        result = build_historical_probability(
            primary_analysis=_primary("偏多"),
            coded_history=_coded_history_bullish(),
            as_of_date="2026-01-08",
        )

        self.assertEqual(result["combined_probability"]["method"], "code_only")
        self.assertAlmostEqual(result["up_rate"], 0.6667, places=4)
        self.assertAlmostEqual(result["down_rate"], 0.3333, places=4)

    def test_window_only_path_sets_combined_method(self) -> None:
        result = build_historical_probability(
            primary_analysis=_primary("偏空"),
            feature_history=_feature_history_bearish(),
            context_features={"window_days": 2, "top_k": 3},
            as_of_date="2026-02-11",
        )

        self.assertTrue(result["ready"])
        self.assertEqual(result["combined_probability"]["method"], "window_only")
        self.assertAlmostEqual(result["up_rate"], 0.3333, places=4)
        self.assertAlmostEqual(result["down_rate"], 0.6667, places=4)
        self.assertEqual(result["historical_bias"], "supports_bearish")
        self.assertEqual(result["impact"], "support")

    def test_blended_path_weights_code_and_window_samples(self) -> None:
        result = build_historical_probability(
            primary_analysis=_primary("偏多"),
            coded_history=_coded_history_bullish(),
            feature_history=_feature_history_bearish(),
            context_features={"window_days": 2, "top_k": 3},
            as_of_date="2026-02-11",
        )

        self.assertTrue(result["ready"])
        self.assertEqual(result["combined_probability"]["method"], "blended")
        self.assertEqual(result["sample_count"], 6)
        self.assertAlmostEqual(result["up_rate"], 0.5, places=4)
        self.assertAlmostEqual(result["down_rate"], 0.5, places=4)
        self.assertEqual(result["historical_bias"], "mixed")
        self.assertEqual(result["impact"], "caution")

    def test_two_insufficient_layers_do_not_blend_into_ready_support(self) -> None:
        result = build_historical_probability(
            primary_analysis=_primary("偏多"),
            coded_history=_coded_history_with_future_sample(),
            feature_history=_feature_history_insufficient(),
            context_features={"window_days": 2, "top_k": 2},
            as_of_date="2026-02-06",
        )

        self.assertFalse(result["ready"])
        self.assertEqual(result["code_match"]["sample_count"], 2)
        self.assertEqual(result["window_similarity"]["sample_count"], 2)
        self.assertEqual(result["combined_probability"]["method"], "fallback")
        self.assertEqual(result["sample_quality"], "insufficient")
        self.assertEqual(result["historical_bias"], "insufficient")
        self.assertNotEqual(result["impact"], "support")
        self.assertIn("样本不足", result["summary"])
        self.assertTrue(any("样本不足" in warning or "样本仍偏少" in warning for warning in result["warnings"]))

    def test_both_missing_returns_null_combined_probability(self) -> None:
        result = build_historical_probability(
            primary_analysis=_primary("偏多"),
            historical_summary=None,
            coded_history=None,
            feature_history=None,
        )

        self.assertFalse(result["ready"])
        self.assertEqual(result["combined_probability"]["method"], "fallback")
        self.assertIsNone(result["combined_probability"]["up_rate"])
        self.assertIsNone(result["combined_probability"]["down_rate"])
        self.assertEqual(result["historical_bias"], "missing")
        self.assertTrue(result["warnings"])

    def test_as_of_date_cutoff_prevents_future_leak(self) -> None:
        result = build_historical_probability(
            primary_analysis=_primary("偏多"),
            coded_history=_coded_history_with_future_sample(),
            as_of_date="2026-01-06",
        )

        self.assertFalse(result["ready"])
        self.assertEqual(result["code_match"]["sample_count"], 2)
        self.assertAlmostEqual(result["code_match"]["up_rate"], 0.5, places=4)
        self.assertAlmostEqual(result["code_match"]["down_rate"], 0.5, places=4)
        self.assertEqual(result["historical_bias"], "insufficient")

    def test_fallback_summary_path_preserves_task_041_contract(self) -> None:
        result = build_historical_probability(
            primary_analysis=_primary("偏多"),
            historical_summary=_summary(dominant="up_bias", up_rate=0.62, down_rate=0.38),
        )

        self.assertTrue(result["ready"])
        self.assertEqual(result["combined_probability"]["method"], "fallback")
        self.assertEqual(result["sample_count"], 10)
        self.assertEqual(result["sample_quality"], "enough")
        self.assertAlmostEqual(result["up_rate"], 0.62, places=4)
        self.assertAlmostEqual(result["down_rate"], 0.38, places=4)
        self.assertEqual(result["historical_bias"], "supports_bullish")
        self.assertEqual(result["impact"], "support")

    def test_semantic_consistency_for_mixed_and_missing(self) -> None:
        mixed = build_historical_probability(
            primary_analysis=_primary("偏多"),
            coded_history=_coded_history_bullish(),
            feature_history=_feature_history_bearish(),
            context_features={"window_days": 2, "top_k": 3},
            as_of_date="2026-02-11",
        )
        missing = build_historical_probability(
            primary_analysis=_primary("偏多"),
            historical_summary=None,
        )

        self.assertEqual(mixed["historical_bias"], "mixed")
        self.assertEqual(mixed["impact"], "caution")
        self.assertIn("caution", mixed["summary"])
        self.assertEqual(missing["historical_bias"], "missing")
        self.assertEqual(missing["impact"], "missing")
        self.assertTrue(missing["warnings"])

    def test_primary_missing_still_degrades_without_fake_support(self) -> None:
        result = build_historical_probability(
            primary_analysis=_primary("unknown", "unknown", ready=False),
            coded_history=_coded_history_bullish(),
            as_of_date="2026-01-08",
        )

        self.assertFalse(result["ready"])
        self.assertEqual(result["historical_bias"], "missing")
        self.assertEqual(result["impact"], "missing")
        self.assertIn("主分析不可用", result["summary"])


if __name__ == "__main__":
    unittest.main()
