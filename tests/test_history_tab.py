from __future__ import annotations

import json
import unittest
from unittest.mock import patch

try:
    from services.prediction_store import PredictionStoreCorruptionError
    from ui.history_tab import (
        _direction_label,
        _format_pct,
        _history_rows,
        _json_or_empty,
        _prediction_summary,
        render_history_tab,
    )
except ModuleNotFoundError:
    _direction_label = None
    _format_pct = None
    _history_rows = None
    _json_or_empty = None
    _prediction_summary = None
    render_history_tab = None
    PredictionStoreCorruptionError = None


class _FakeStreamlit:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    def subheader(self, message: str) -> None:
        self.messages.append(("subheader", message))

    def caption(self, message: str) -> None:
        self.messages.append(("caption", message))

    def warning(self, message: str) -> None:
        self.messages.append(("warning", message))


@unittest.skipIf(_history_rows is None, "streamlit or pandas is not installed")
class HistoryTabHelperTests(unittest.TestCase):
    def test_history_rows_include_required_columns(self) -> None:
        rows = _history_rows(
            [
                {
                    "id": "prediction-1",
                    "prediction_for_date": "2026-04-11",
                    "final_bias": "bullish",
                    "final_confidence": "medium",
                    "status": "review_generated",
                    "direction_correct": 1,
                    "actual_close_change": 0.0123,
                }
            ]
        )

        self.assertEqual(rows[0]["prediction_for_date"], "2026-04-11")
        self.assertEqual(rows[0]["final_bias"], "bullish")
        self.assertEqual(rows[0]["final_confidence"], "medium")
        self.assertEqual(rows[0]["status"], "review_generated")
        self.assertEqual(rows[0]["direction_correct"], "CORRECT")
        self.assertEqual(rows[0]["close_change"], "+1.23%")

    def test_direction_label_handles_all_known_states(self) -> None:
        self.assertEqual(_direction_label(1), "CORRECT")
        self.assertEqual(_direction_label(0), "WRONG")
        self.assertEqual(_direction_label(None), "PENDING")
        self.assertEqual(_direction_label(None, "outcome_captured"), "NEUTRAL")
        self.assertEqual(_direction_label(None, "review_generated"), "NEUTRAL")
        self.assertEqual(_direction_label("other"), "NEUTRAL")

    def test_format_pct_handles_empty_and_numeric_values(self) -> None:
        self.assertEqual(_format_pct(None), "")
        self.assertEqual(_format_pct(0.025), "+2.50%")
        self.assertEqual(_format_pct("-0.015"), "-1.50%")
        self.assertEqual(_format_pct("not-a-number"), "")

    def test_json_or_empty_returns_dict_only(self) -> None:
        self.assertEqual(_json_or_empty('{"a": 1}'), {"a": 1})
        self.assertEqual(_json_or_empty("[1, 2, 3]"), {})
        self.assertEqual(_json_or_empty("not-json"), {})
        self.assertEqual(_json_or_empty(None), {})

    def test_prediction_summary_reads_predict_json(self) -> None:
        prediction = {
            "predict_result_json": '{"prediction_summary": "A useful summary."}'
        }
        self.assertEqual(_prediction_summary(prediction), "A useful summary.")
        self.assertEqual(_prediction_summary({"predict_result_json": "{}"}), "")

    def test_history_rows_include_scenario_match_label(self) -> None:
        scenario_json = json.dumps({
            "exact_match_count": 3,
            "near_match_count": 2,
            "dominant_historical_outcome": "bullish",
        })
        rows = _history_rows([{
            "id": "p1",
            "prediction_for_date": "2026-04-11",
            "final_bias": "bullish",
            "final_confidence": "medium",
            "status": "review_generated",
            "direction_correct": 1,
            "actual_close_change": 0.01,
            "scenario_match": scenario_json,
        }])
        self.assertEqual(rows[0]["scenario_match"], "exact 3 / near 2 / bullish")

    def test_history_rows_scenario_match_blank_when_absent(self) -> None:
        rows = _history_rows([{
            "id": "p1",
            "prediction_for_date": "2026-04-11",
            "final_bias": "bearish",
            "final_confidence": "low",
            "status": "saved",
            "direction_correct": None,
            "actual_close_change": None,
        }])
        self.assertEqual(rows[0]["scenario_match"], "")

    def test_history_rows_scenario_match_blank_for_empty_dict(self) -> None:
        """Empty {} historical_match_summary produces blank scenario display, not an error."""
        rows = _history_rows([{
            "id": "p1",
            "prediction_for_date": "2026-04-11",
            "final_bias": "neutral",
            "final_confidence": "low",
            "status": "outcome_captured",
            "direction_correct": None,
            "actual_close_change": 0.001,
            "scenario_match": "{}",
        }])
        self.assertEqual(rows[0]["scenario_match"], "")

    def test_render_history_tab_handles_corrupt_prediction_store(self) -> None:
        fake_st = _FakeStreamlit()
        error = PredictionStoreCorruptionError("历史记录数据库损坏，暂时无法读取。")

        with patch("ui.history_tab.st", fake_st), patch(
            "ui.history_tab.list_predictions",
            side_effect=error,
        ):
            render_history_tab()

        self.assertIn(("warning", "历史记录数据库损坏，暂时无法读取。"), fake_st.messages)
        self.assertTrue(
            any(
                kind == "caption" and "备份 avgo_agent.db" in message
                for kind, message in fake_st.messages
            )
        )


if __name__ == "__main__":
    unittest.main()
