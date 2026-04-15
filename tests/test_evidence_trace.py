from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.evidence_trace import build_projection_evidence_trace


class EvidenceTraceTests(unittest.TestCase):
    def _payload(self) -> dict:
        return {
            "predict_result": {
                "final_bias": "bullish",
                "final_confidence": "low",
                "open_tendency": "flat_bias",
                "close_tendency": "close_strong",
                "supporting_factors": ["scan_bias=bullish", "scan_confidence=low"],
                "conflicting_factors": ["scan_confirmation=diverging"],
            },
            "scan_result": {
                "avgo_gap_state": "flat",
                "avgo_intraday_state": "high_go",
                "avgo_volume_state": "shrinking",
                "avgo_price_state": "bullish",
                "confirmation_state": "diverging",
                "historical_match_summary": {
                    "exact_match_count": 17,
                    "near_match_count": 26,
                    "dominant_historical_outcome": "mixed",
                },
                "relative_strength_5d_summary": {
                    "vs_nvda": "weaker",
                    "vs_soxx": "stronger",
                    "vs_qqq": "neutral",
                },
            },
            "projection_report": {
                "direction": "中性",
                "open_tendency": "平开",
                "close_tendency": "偏强",
                "confidence": "low",
                "risk_reminders": ["历史分布混杂"],
            },
            "advisory": {"reminder_lines": ["memory reminder"]},
        }

    def test_builds_required_trace_blocks_from_projection_payload(self) -> None:
        trace = build_projection_evidence_trace(self._payload())

        self.assertEqual(trace["kind"], "projection_evidence_trace")
        for key in (
            "tool_trace",
            "key_observations",
            "decision_steps",
            "final_conclusion",
            "verification_points",
        ):
            self.assertIn(key, trace)

        self.assertIn("scan", trace["tool_trace"])
        self.assertIn("historical_match", trace["tool_trace"])
        self.assertIn("peer_confirmation", trace["tool_trace"])
        self.assertIn("predict_summary", trace["tool_trace"])
        self.assertIn("projection_report", trace["tool_trace"])
        self.assertEqual(
            trace["final_conclusion"],
            {
                "direction": "中性",
                "open_tendency": "平开",
                "close_tendency": "偏强",
                "confidence": "low",
            },
        )
        self.assertTrue(any("完全匹配 17" in line for line in trace["key_observations"]))
        self.assertTrue(any("同业" in line for line in trace["key_observations"]))
        self.assertTrue(all("观察：" in line and "结论影响：" in line for line in trace["decision_steps"]))
        self.assertTrue(any("NVDA / SOXX / QQQ" in line for line in trace["verification_points"]))

    def test_missing_fields_degrade_safely(self) -> None:
        trace = build_projection_evidence_trace({})

        self.assertEqual(trace["tool_trace"], ["fallback_projection_trace"])
        self.assertEqual(trace["final_conclusion"]["direction"], "中性")
        self.assertEqual(trace["final_conclusion"]["open_tendency"], "平开")
        self.assertEqual(trace["final_conclusion"]["close_tendency"], "震荡")
        self.assertEqual(trace["final_conclusion"]["confidence"], "low")
        self.assertTrue(trace["key_observations"])
        self.assertTrue(trace["decision_steps"])
        self.assertTrue(trace["verification_points"])

    def test_final_conclusion_uses_projection_report_over_predict_result(self) -> None:
        payload = self._payload()
        payload["predict_result"]["final_bias"] = "bearish"
        trace = build_projection_evidence_trace(payload)

        self.assertEqual(trace["final_conclusion"]["direction"], "中性")
        self.assertEqual(trace["final_conclusion"]["open_tendency"], "平开")
        self.assertEqual(trace["final_conclusion"]["close_tendency"], "偏强")

    def test_empty_advisory_shell_does_not_mark_memory_feedback(self) -> None:
        payload = self._payload()
        payload["advisory"] = {
            "matched_count": 0,
            "caution_level": "none",
            "reminder_lines": [],
            "advisory_block": {
                "matched_count": 0,
                "reminder_lines": [],
            },
        }

        trace = build_projection_evidence_trace(payload)

        self.assertNotIn("memory_feedback", trace["tool_trace"])

    def test_missing_peer_rs_values_do_not_render_literal_none(self) -> None:
        payload = self._payload()
        payload["scan_result"]["confirmation_state"] = None
        payload["scan_result"]["relative_strength_5d_summary"] = {
            "vs_nvda": None,
            "vs_soxx": "unavailable",
            "vs_qqq": "",
        }
        payload["scan_result"]["relative_strength_same_day_summary"] = {
            "vs_nvda": None,
        }

        trace = build_projection_evidence_trace(payload)
        text = "\n".join(trace["key_observations"] + trace["decision_steps"])

        self.assertNotIn("None", text)
        self.assertNotIn("literal None", text)
        self.assertIn("暂无可用同业对照", text)


class FakeStreamlit:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def markdown(self, text: str, **_: object) -> None:
        self.messages.append(text)

    def caption(self, text: str) -> None:
        self.messages.append(text)

    def metric(self, label: str, value: object) -> None:
        self.messages.append(f"{label}: {value}")

    def columns(self, count: int) -> list["FakeStreamlit"]:
        return [self for _ in range(count)]


class EvidenceTraceRenderTests(unittest.TestCase):
    def test_predict_page_renders_required_evidence_trace_blocks(self) -> None:
        from ui import predict_tab

        fake_st = FakeStreamlit()
        old_st = predict_tab.st
        try:
            predict_tab.st = fake_st
            predict_tab.render_evidence_trace(build_projection_evidence_trace({}))
        finally:
            predict_tab.st = old_st

        text = "\n".join(fake_st.messages)
        self.assertIn("tool_trace", text)
        self.assertIn("key_observations", text)
        self.assertIn("decision_steps", text)
        self.assertIn("final_conclusion", text)
        self.assertIn("verification_points", text)


if __name__ == "__main__":
    unittest.main()
