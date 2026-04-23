from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.consistency_layer import build_consistency_layer


def _projection(top1: str, top2: str = "震荡") -> dict:
    probabilities = {
        "大涨": 0.10,
        "小涨": 0.20,
        "震荡": 0.30,
        "小跌": 0.20,
        "大跌": 0.20,
    }
    probabilities[top1] = 0.42
    probabilities[top2] = 0.24
    return {
        "symbol": "AVGO",
        "predicted_top1": {"state": top1, "probability": probabilities[top1]},
        "predicted_top2": {"state": top2, "probability": probabilities[top2]},
        "state_probabilities": probabilities,
        "rationale": ["主推演层已生成五状态分布。"],
    }


class ConsistencyLayerTests(unittest.TestCase):
    def test_exclusion_and_main_projection_conflict_is_marked(self) -> None:
        result = build_consistency_layer(
            exclusion_result={
                "excluded": True,
                "triggered_rule": "exclude_big_up",
                "peer_alignment": {
                    "up_support": "supported",
                    "down_support": "unsupported",
                },
            },
            main_projection_result=_projection("大涨", "小涨"),
            peer_alignment={
                "up_support": "supported",
                "down_support": "unsupported",
            },
            historical_match_result={
                "dominant_historical_outcome": "up_bias",
            },
        )

        self.assertTrue(result["ready"])
        self.assertEqual(result["consistency_flag"], "conflict")
        self.assertLess(result["consistency_score"], 0.7)
        self.assertTrue(any("排除层已排除大涨" in item for item in result["conflict_reasons"]))

    def test_peer_and_main_projection_conflict_is_marked(self) -> None:
        result = build_consistency_layer(
            exclusion_result={"excluded": False},
            main_projection_result=_projection("小涨", "震荡"),
            peer_alignment={
                "up_support": "unsupported",
                "down_support": "supported",
            },
            historical_match_result={
                "dominant_historical_outcome": "up_bias",
            },
        )

        self.assertTrue(result["ready"])
        self.assertEqual(result["consistency_flag"], "mixed")
        self.assertTrue(any("peers 对上行给出 unsupported" in item for item in result["conflict_reasons"]))

    def test_history_and_main_projection_conflict_is_marked(self) -> None:
        result = build_consistency_layer(
            exclusion_result={"excluded": False},
            main_projection_result=_projection("小跌", "震荡"),
            peer_alignment={
                "up_support": "unsupported",
                "down_support": "supported",
            },
            historical_match_result={
                "dominant_historical_outcome": "up_bias",
            },
        )

        self.assertTrue(result["ready"])
        self.assertEqual(result["consistency_flag"], "mixed")
        self.assertTrue(any("历史匹配结果明显偏 bullish" in item for item in result["conflict_reasons"]))

    def test_fully_consistent_case_returns_consistent_flag(self) -> None:
        result = build_consistency_layer(
            exclusion_result={"excluded": False},
            main_projection_result=_projection("小涨", "震荡"),
            peer_alignment={
                "up_support": "supported",
                "down_support": "unsupported",
            },
            historical_match_result={
                "dominant_historical_outcome": "up_bias",
            },
        )

        self.assertTrue(result["ready"])
        self.assertEqual(result["consistency_flag"], "consistent")
        self.assertEqual(result["conflict_reasons"], [])
        self.assertIn("整体一致", result["summary"])


if __name__ == "__main__":
    unittest.main()
