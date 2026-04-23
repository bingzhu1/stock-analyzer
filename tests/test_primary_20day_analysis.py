from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.primary_20day_analysis import build_primary_20day_analysis
from services.projection_orchestrator_v2 import run_projection_v2


def _frame(closes: list[float], *, volumes: list[float] | None = None, stage: str | None = None) -> pd.DataFrame:
    volumes = volumes or [100.0 for _ in closes]
    rows = []
    for idx, close in enumerate(closes):
        rows.append({
            "Date": f"2026-01-{idx + 1:02d}",
            "Open": close - 0.5,
            "High": close + 1.0,
            "Low": close - 1.0,
            "Close": close,
            "Volume": volumes[idx],
            "StageLabel": stage or "整理",
        })
    return pd.DataFrame(rows)


def _legacy_payload() -> dict:
    return {
        "advisory": {"matched_count": 0, "caution_level": "none", "reminder_lines": []},
        "projection_report": {"kind": "final_projection_report", "target_date": "2026-01-20"},
        "scan_result": {
            "confirmation_state": "mixed",
            "relative_strength_5d_summary": {"vs_nvda": "neutral"},
            "historical_match_summary": {
                "exact_match_count": 1,
                "near_match_count": 1,
                "dominant_historical_outcome": "mixed",
            },
        },
    }


class Primary20DayAnalysisTests(unittest.TestCase):
    def test_happy_path_returns_fixed_shape(self) -> None:
        result = build_primary_20day_analysis(data=_frame([100 + i for i in range(20)], stage="延续"))

        self.assertEqual(result["kind"], "primary_20day_analysis")
        self.assertEqual(result["symbol"], "AVGO")
        self.assertTrue(result["ready"])
        self.assertIn(result["direction"], {"偏多", "偏空", "中性"})
        self.assertIn(result["confidence"], {"high", "medium", "low"})
        self.assertTrue(result["summary"])
        self.assertGreaterEqual(len(result["basis"]), 3)
        for key in ("latest_close", "ret_5d", "ret_10d", "pos_20d", "high_20d", "low_20d", "vol_ratio_5d", "days_used"):
            self.assertIn(key, result["features"])
        self.assertEqual(result["features"]["days_used"], 20)

    def test_bullish_like_case_outputs_bullish(self) -> None:
        result = build_primary_20day_analysis(
            data=_frame([100 + i for i in range(20)], volumes=[100.0] * 15 + [130.0] * 5, stage="延续")
        )

        self.assertEqual(result["direction"], "偏多")
        self.assertTrue(result["basis"])

    def test_bearish_like_case_outputs_bearish(self) -> None:
        result = build_primary_20day_analysis(
            data=_frame([120 - i for i in range(20)], volumes=[120.0] * 20, stage="衰竭风险")
        )

        self.assertEqual(result["direction"], "偏空")

    def test_mixed_case_outputs_neutral(self) -> None:
        closes = [100.0, 101.0, 100.5, 99.8, 100.2, 100.1, 99.9, 100.0, 100.2, 99.9,
                  100.1, 100.0, 99.8, 100.2, 100.1, 99.9, 100.0, 100.1, 99.9, 100.0]

        result = build_primary_20day_analysis(data=_frame(closes, stage="整理"))

        self.assertEqual(result["direction"], "中性")
        self.assertEqual(result["confidence"], "low")

    def test_insufficient_days_does_not_crash_and_warns(self) -> None:
        result = build_primary_20day_analysis(data=_frame([100 + i for i in range(8)]))

        self.assertTrue(result["ready"])
        self.assertEqual(result["features"]["days_used"], 8)
        self.assertTrue(any("样本不足" in warning for warning in result["warnings"]))

    def test_empty_data_degrades_without_fake_analysis(self) -> None:
        result = build_primary_20day_analysis(data=pd.DataFrame())

        self.assertFalse(result["ready"])
        self.assertEqual(result["direction"], "unknown")
        self.assertEqual(result["confidence"], "unknown")
        self.assertEqual(result["features"]["days_used"], 0)
        self.assertTrue(result["warnings"])
        self.assertIn("不可用", result["summary"])

    def test_missing_key_field_degrades_with_stable_shape(self) -> None:
        result = build_primary_20day_analysis(data=pd.DataFrame({
            "Date": ["2026-01-01"],
            "Close": [100.0],
            "Volume": [100.0],
        }))

        self.assertFalse(result["ready"])
        self.assertEqual(result["direction"], "unknown")
        self.assertTrue(any("缺少关键字段" in warning for warning in result["warnings"]))
        self.assertIn("high_20d", result["features"])

    def test_non_numeric_required_fields_degrade_without_fake_neutral_analysis(self) -> None:
        result = build_primary_20day_analysis(data=pd.DataFrame({
            "Date": [f"2026-01-{idx + 1:02d}" for idx in range(20)],
            "High": ["unavailable"] * 20,
            "Low": ["unavailable"] * 20,
            "Close": ["unavailable"] * 20,
            "Volume": ["unavailable"] * 20,
        }))

        self.assertFalse(result["ready"])
        self.assertEqual(result["direction"], "unknown")
        self.assertTrue(result["warnings"])
        self.assertIn("不可用", result["summary"])
        self.assertNotIn("方向中性", result["summary"])
        self.assertEqual(result["features"]["days_used"], 20)

    def test_projection_v2_primary_analysis_uses_primary_layer_output(self) -> None:
        primary = build_primary_20day_analysis(data=_frame([100 + i for i in range(20)], stage="延续"))

        def runner(**_: object) -> dict:
            return _legacy_payload()

        def primary_builder(**_: object) -> dict:
            return primary

        result = run_projection_v2(
            _projection_runner=runner,
            _primary_analysis_builder=primary_builder,
        )

        self.assertEqual(result["step_status"]["primary_analysis"], "success")
        self.assertEqual(result["primary_analysis"]["kind"], "primary_20day_analysis")
        self.assertEqual(result["primary_analysis"]["features"]["days_used"], 20)
        self.assertEqual(result["final_decision"]["direction"], primary["direction"])


if __name__ == "__main__":
    unittest.main()
