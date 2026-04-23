from __future__ import annotations

from pathlib import Path
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]

try:
    import pandas  # noqa: F401
    from streamlit.testing.v1 import AppTest
except ModuleNotFoundError:
    AppTest = None


def _script() -> str:
    return textwrap.dedent(
        f"""
        import sys
        sys.path.insert(0, {str(ROOT)!r})

        import streamlit as st
        from ui import predict_tab

        st.session_state.setdefault("target_date_str", "2026-04-11")
        st.session_state.setdefault("snapshot_id", "snap-test")
        st.session_state.setdefault("fake_save_counter", 0)
        st.session_state.setdefault("fake_saved_payloads", {{}})
        st.session_state.setdefault("fake_outcomes", {{}})
        st.session_state.setdefault("fake_reviews", {{}})

        def fake_run_predict(scan_result, research_result):
            return {{
                "symbol": "AVGO",
                "predict_timestamp": "2026-04-10T09:00:00",
                "final_bias": "bullish",
                "final_confidence": "medium",
                "open_tendency": "up",
                "close_tendency": "up",
                "scan_bias": "bullish",
                "scan_confidence": "medium",
                "research_bias_adjustment": "confirms_bias",
                "prediction_summary": "Test prediction summary",
                "supporting_factors": ["momentum"],
                "conflicting_factors": [],
                "notes": "Test notes",
            }}

        def fake_render_predict_result(predict_result):
            st.write("predict result rendered")

        def fake_save_prediction(symbol, prediction_for_date, scan_result,
                                 research_result, predict_result, snapshot_id):
            st.session_state["fake_save_counter"] += 1
            pid = f"pid-{{st.session_state['fake_save_counter']}}"
            st.session_state["fake_saved_payloads"][pid] = {{
                "symbol": symbol,
                "prediction_for_date": prediction_for_date,
                "snapshot_id": snapshot_id,
            }}
            return pid

        def fake_get_outcome_for_prediction(prediction_id):
            return st.session_state["fake_outcomes"].get(prediction_id)

        def fake_capture_outcome(prediction_id):
            outcome = {{
                "id": f"outcome-{{prediction_id}}",
                "direction_correct": 1,
                "actual_close_change": 0.0234,
                "actual_close": 177.0,
                "scenario_match": None,
            }}
            st.session_state["fake_outcomes"][prediction_id] = outcome
            return outcome

        def fake_get_review_for_prediction(prediction_id):
            return st.session_state["fake_reviews"].get(prediction_id)

        def fake_generate_review(prediction_id):
            review = {{
                "id": f"review-{{prediction_id}}",
                "error_category": "correct",
                "root_cause": "The bullish setup followed through.",
                "confidence_note": "Confidence was appropriate.",
                "watch_for_next_time": "Watch follow-through volume.",
                "raw_llm_output": "",
            }}
            st.session_state["fake_reviews"][prediction_id] = review
            return review

        predict_tab.run_predict = fake_run_predict
        predict_tab.render_predict_result = fake_render_predict_result
        predict_tab.save_prediction = fake_save_prediction
        predict_tab.get_outcome_for_prediction = fake_get_outcome_for_prediction
        predict_tab.capture_outcome = fake_capture_outcome
        predict_tab.get_review_for_prediction = fake_get_review_for_prediction
        predict_tab.generate_review = fake_generate_review

        scan_result = {{"scan_bias": "bullish", "scan_confidence": "medium"}}
        research_result = {{"research_bias_adjustment": "confirms_bias"}}
        predict_tab.render_predict_tab(scan_result, research_result)
        """
    )


def _button_by_key(at, key: str):
    for button in at.button:
        if button.key == key:
            return button
    raise AssertionError(f"Button with key {key!r} not found")


def _markdown_text(at) -> str:
    return "\n".join(item.value for item in at.markdown)


def _caption_text(at) -> str:
    return "\n".join(item.value for item in at.caption)


@unittest.skipIf(AppTest is None, "streamlit AppTest or pandas is not installed")
class ResearchLoopAppTests(unittest.TestCase):
    def test_button_preconditions_and_three_step_flow(self) -> None:
        at = AppTest.from_string(_script()).run()

        self.assertFalse(_button_by_key(at, "btn_save_prediction").disabled)
        self.assertTrue(_button_by_key(at, "btn_capture_outcome_locked").disabled)
        self.assertTrue(_button_by_key(at, "btn_generate_review_locked1").disabled)
        self.assertIn("Complete Step 1 first.", _caption_text(at))

        at = _button_by_key(at, "btn_save_prediction").click().run()
        self.assertEqual(at.session_state["saved_prediction_id"], "pid-1")
        self.assertEqual(at.session_state["saved_prediction_date"], "2026-04-11")
        self.assertIn("pid-1", at.session_state["fake_saved_payloads"])
        self.assertFalse(_button_by_key(at, "btn_save_new_version").disabled)
        self.assertFalse(_button_by_key(at, "btn_capture_outcome").disabled)
        self.assertTrue(_button_by_key(at, "btn_generate_review_locked2").disabled)
        self.assertIn("Complete Step 2 first.", _caption_text(at))

        at = _button_by_key(at, "btn_capture_outcome").click().run()
        self.assertIn("pid-1", at.session_state["fake_outcomes"])
        self.assertIn("CORRECT", "\n".join(item.value for item in at.success))
        self.assertFalse(_button_by_key(at, "btn_generate_review").disabled)

        at = _button_by_key(at, "btn_generate_review").click().run()
        self.assertIn("pid-1", at.session_state["fake_reviews"])
        self.assertIn("CORRECT", _markdown_text(at))
        self.assertIn("Root cause:", _markdown_text(at))

    def test_save_new_version_resets_session_prediction_id(self) -> None:
        at = AppTest.from_string(_script()).run()

        at = _button_by_key(at, "btn_save_prediction").click().run()
        self.assertEqual(at.session_state["saved_prediction_id"], "pid-1")

        at = _button_by_key(at, "btn_save_new_version").click().run()
        self.assertEqual(at.session_state["saved_prediction_id"], "pid-2")
        self.assertEqual(at.session_state["saved_prediction_date"], "2026-04-11")
        self.assertIn("pid-1", at.session_state["fake_saved_payloads"])
        self.assertIn("pid-2", at.session_state["fake_saved_payloads"])
        self.assertFalse(_button_by_key(at, "btn_capture_outcome").disabled)
        self.assertTrue(_button_by_key(at, "btn_generate_review_locked2").disabled)


if __name__ == "__main__":
    unittest.main()
