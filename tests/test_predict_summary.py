from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.predict_summary import build_predict_readable_summary


class PredictReadableSummaryTests(unittest.TestCase):
    def test_builds_required_summary_blocks(self) -> None:
        predict_result = {
            "final_bias": "bullish",
            "final_confidence": "high",
            "open_tendency": "gap_up_bias",
            "close_tendency": "close_strong",
            "prediction_summary": "Prediction is bullish.",
            "supporting_factors": ["scan_bias=bullish", "scan_confidence=high"],
            "conflicting_factors": ["scan_confirmation=diverging"],
        }
        scan_result = {
            "confirmation_state": "diverging",
            "avgo_gap_state": "gap_up",
            "avgo_price_state": "bullish",
            "avgo_volume_state": "expanding",
            "historical_match_summary": {
                "exact_match_count": 3,
                "near_match_count": 5,
                "dominant_historical_outcome": "mixed",
            },
            "relative_strength_5d_summary": {"vs_nvda": "stronger"},
            "relative_strength_same_day_summary": {"vs_soxx": "weaker"},
        }

        summary = build_predict_readable_summary(
            predict_result,
            scan_result=scan_result,
            advisory={"reminder_lines": ["Prior memory reminder."]},
            lookback_days=20,
        )

        self.assertEqual(summary["kind"], "predict_readable_summary")
        self.assertEqual(summary["baseline_judgment"]["direction"], "偏多")
        self.assertEqual(summary["baseline_judgment"]["strength"], "强")
        self.assertEqual(summary["baseline_judgment"]["risk_level"], "高")
        self.assertEqual(summary["open_projection"]["tendency"], "高开")
        self.assertIn("防高开低走", summary["open_projection"]["text"])
        self.assertEqual(summary["close_projection"]["tendency"], "偏强")
        self.assertTrue(any("历史匹配" in line for line in summary["rationale"]))
        self.assertTrue(any("同业对照" in line for line in summary["rationale"]))
        self.assertTrue(any("最近 20 天" in line for line in summary["rationale"]))
        self.assertTrue(any("Prior memory reminder." in line for line in summary["risk_reminders"]))
        summary_text = summary["summary_text"]
        self.assertNotIn("mixed", summary_text)
        self.assertNotIn("stronger", summary_text)
        self.assertNotIn("gap_up", summary_text)
        self.assertNotIn("Prediction is", summary_text)
        self.assertIn("明日基准判断", summary["summary_text"])
        self.assertIn("为什么这样判断", summary["summary_text"])
        self.assertIn("风险提醒", summary["summary_text"])

    def test_missing_fields_degrade_safely(self) -> None:
        summary = build_predict_readable_summary({})

        self.assertEqual(summary["baseline_judgment"]["direction"], "中性")
        self.assertEqual(summary["baseline_judgment"]["strength"], "弱")
        self.assertEqual(summary["baseline_judgment"]["risk_level"], "高")
        self.assertEqual(summary["open_projection"]["tendency"], "平开")
        self.assertEqual(summary["close_projection"]["tendency"], "震荡")
        self.assertTrue(summary["rationale"])
        self.assertTrue(summary["risk_reminders"])

    def test_external_confirmation_missing_adds_risk_reminder(self) -> None:
        summary = build_predict_readable_summary(
            {"final_bias": "bullish", "final_confidence": "high"},
            scan_result={
                "confirmation_state": "mixed",
                "relative_strength_5d_summary": {
                    "vs_nvda": "unavailable",
                    "vs_soxx": "unavailable",
                    "vs_qqq": "unavailable",
                },
            },
        )

        self.assertEqual(summary["baseline_judgment"]["risk_level"], "高")
        self.assertTrue(any("外部确认不足" in line for line in summary["risk_reminders"]))

    def test_ai_polish_is_optional_and_secondary(self) -> None:
        summary = build_predict_readable_summary(
            {"final_bias": "bearish", "final_confidence": "medium"},
            ai_polish="自然中文润色段落。",
        )

        self.assertEqual(summary["baseline_judgment"]["direction"], "偏空")
        self.assertEqual(summary["ai_polish"], "自然中文润色段落。")


class FakeStreamlit:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def markdown(self, text: str, **_: object) -> None:
        self.messages.append(text)

    def write(self, text: object) -> None:
        self.messages.append(str(text))

    def caption(self, text: str) -> None:
        self.messages.append(text)

    def metric(self, label: str, value: object) -> None:
        self.messages.append(f"{label}: {value}")

    def columns(self, count: int) -> list["FakeStreamlit"]:
        return [self for _ in range(count)]


class PredictReadableSummaryRenderTests(unittest.TestCase):
    def test_predict_summary_render_outputs_required_headings(self) -> None:
        from ui import predict_tab

        fake_st = FakeStreamlit()
        old_st = predict_tab.st
        try:
            predict_tab.st = fake_st
            predict_tab.render_readable_predict_summary(build_predict_readable_summary({}))
        finally:
            predict_tab.st = old_st

        text = "\n".join(fake_st.messages)
        self.assertIn("明日基准判断", text)
        self.assertIn("开盘推演", text)
        self.assertIn("收盘推演", text)
        self.assertIn("为什么这样判断", text)
        self.assertIn("风险提醒", text)


if __name__ == "__main__":
    unittest.main()
