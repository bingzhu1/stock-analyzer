from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.exclusion_layer import run_exclusion_layer


class ExclusionLayerTests(unittest.TestCase):
    def test_excludes_tomorrow_big_up(self) -> None:
        result = run_exclusion_layer({
            "symbol": "AVGO",
            "pos20": 88.0,
            "vol_ratio20": 0.78,
            "upper_shadow_ratio": 0.42,
            "lower_shadow_ratio": 0.10,
            "ret1": 2.3,
            "ret3": 5.2,
            "ret5": 8.4,
            "nvda_ret1": 0.1,
            "soxx_ret1": -0.2,
            "qqq_ret1": 0.2,
        })

        self.assertTrue(result["excluded"])
        self.assertEqual(result["action"], "exclude")
        self.assertEqual(result["triggered_rule"], "exclude_big_up")
        self.assertIn("明天不太可能大涨", result["summary"])
        self.assertEqual(result["peer_alignment"]["up_support"], "unsupported")
        self.assertEqual(result["feature_snapshot"]["pos20"], 88.0)
        self.assertTrue(any("高位" in reason or "peers" in reason for reason in result["reasons"]))

    def test_excludes_tomorrow_big_down(self) -> None:
        result = run_exclusion_layer({
            "symbol": "AVGO",
            "pos20": 12.0,
            "vol_ratio20": 1.35,
            "upper_shadow_ratio": 0.08,
            "lower_shadow_ratio": 0.41,
            "ret1": 0.9,
            "ret3": 1.8,
            "ret5": 3.0,
            "nvda_ret1": -0.1,
            "soxx_ret1": 0.2,
            "qqq_ret1": 0.0,
        })

        self.assertTrue(result["excluded"])
        self.assertEqual(result["action"], "exclude")
        self.assertEqual(result["triggered_rule"], "exclude_big_down")
        self.assertIn("明天不太可能大跌", result["summary"])
        self.assertEqual(result["peer_alignment"]["down_support"], "unsupported")
        self.assertEqual(result["feature_snapshot"]["vol_ratio20"], 1.35)
        self.assertTrue(any("低位" in reason or "下影" in reason for reason in result["reasons"]))

    def test_neutral_case_is_allowed(self) -> None:
        result = run_exclusion_layer({
            "symbol": "AVGO",
            "pos20": 52.0,
            "vol_ratio20": 1.02,
            "upper_shadow_ratio": 0.16,
            "lower_shadow_ratio": 0.14,
            "ret1": 0.3,
            "ret3": 0.7,
            "ret5": 1.1,
            "nvda_ret1": 1.2,
            "soxx_ret1": -1.1,
            "qqq_ret1": 0.4,
        })

        self.assertFalse(result["excluded"])
        self.assertEqual(result["action"], "allow")
        self.assertIsNone(result["triggered_rule"])
        self.assertIn("主流程可继续推演", result["summary"])
        self.assertEqual(result["feature_snapshot"]["ret5"], 1.1)


if __name__ == "__main__":
    unittest.main()
