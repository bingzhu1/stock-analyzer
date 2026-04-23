# -*- coding: utf-8 -*-
"""
tests/test_review_orchestrator.py

Unit tests for services/review_orchestrator.py.
All external I/O (DB reads, yfinance) is mocked — no network, no real DB.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.review_orchestrator import run_review_for_prediction

# ─────────────────────────────────────────────────────────────────────────────
# Synthetic fixtures
# ─────────────────────────────────────────────────────────────────────────────

_SYMBOL = "AVGO"
_DATE = "2026-04-21"
_PID = "test-prediction-uuid-001"

_PREDICT_RESULT = {
    "symbol": _SYMBOL,
    "final_bias": "bullish",
    "final_confidence": "medium",
    "open_tendency": "gap_up_bias",
    "close_tendency": "close_strong",
    "pred_open": "高开",
    "pred_path": "高开高走",
    "pred_close": "收涨",
    "prediction_summary": "Bullish bias with medium confidence.",
    "notes": "Unit test",
    "supporting_factors": ["scan_bias=bullish"],
    "conflicting_factors": [],
    "primary_projection": {
        "status": "computed",
        "source": "avgo_recent_20_scan_context",
        "symbol": _SYMBOL,
        "peer_inputs_used": False,
        "final_bias": "bullish",
        "final_confidence": "medium",
        "open_tendency": "gap_up_bias",
        "close_tendency": "close_strong",
        "pred_open": "高开",
        "pred_path": "高开高走",
        "pred_close": "收涨",
        "signals": ["avgo_gap_state=gap_up"],
    },
    "peer_adjustment": {
        "status": "computed",
        "source": "peer_relative_strength",
        "peer_symbols": ["NVDA", "SOXX", "QQQ"],
        "adjustment_direction": "reinforce",
        "confirm_count": 2,
        "oppose_count": 0,
        "adjusted_bias": "bullish",
        "adjusted_confidence": "medium",
        "adjustments": [
            {"peer": "NVDA", "vote": "confirm"},
            {"peer": "SOXX", "vote": "confirm"},
            {"peer": "QQQ", "vote": "mixed"},
        ],
    },
    "final_projection": {
        "status": "computed",
        "source": "primary_projection_plus_peer_adjustment",
        "symbol": _SYMBOL,
        "final_bias": "bullish",
        "final_confidence": "medium",
        "open_tendency": "gap_up_bias",
        "close_tendency": "close_strong",
        "pred_open": "高开",
        "pred_path": "高开高走",
        "pred_close": "收涨",
        "prediction_summary": "Bullish bias with medium confidence.",
        "supporting_factors": ["primary_bias=bullish", "peer_adjustment=reinforce"],
        "conflicting_factors": [],
    },
}

_PREDICTION_ROW = {
    "id": _PID,
    "symbol": _SYMBOL,
    "prediction_for_date": _DATE,
    "analysis_date": "2026-04-20",
    "final_bias": "bullish",
    "final_confidence": "medium",
    "status": "saved",
    "snapshot_id": "—",
    "predict_result_json": json.dumps(_PREDICT_RESULT),
    "scan_result_json": None,
    "research_result_json": None,
}

_OUTCOME_ROW = {
    "id": "test-outcome-uuid-001",
    "prediction_id": _PID,
    "prediction_for_date": _DATE,
    "actual_open": 172.0,
    "actual_high": 175.0,
    "actual_low": 171.5,
    "actual_close": 174.0,
    "actual_prev_close": 171.0,
    "actual_open_change": (172.0 - 171.0) / 171.0,
    "actual_close_change": (174.0 - 171.0) / 171.0,
    "direction_correct": 1,
    "scenario_match": None,
}

_PATCH_GET_LATEST = "services.review_orchestrator.get_latest_prediction_for_target_date"
_PATCH_GET_OUTCOME = "services.review_orchestrator.get_outcome_for_prediction"
_PATCH_CAPTURE = "services.review_orchestrator.capture_outcome"
_PATCH_SAVE_REVIEW = "services.review_orchestrator.save_review_record"

_FAKE_REVIEW_ID = "review-uuid-fake-001"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _run(
    prediction=_PREDICTION_ROW,
    outcome=_OUTCOME_ROW,
    capture_raises=None,
) -> dict:
    """Run orchestrator with configurable mock return values."""
    with patch(_PATCH_GET_LATEST, return_value=prediction), \
         patch(_PATCH_GET_OUTCOME, return_value=outcome), \
         patch(_PATCH_CAPTURE) as mock_cap, \
         patch(_PATCH_SAVE_REVIEW, return_value=_FAKE_REVIEW_ID):
        if capture_raises:
            mock_cap.side_effect = capture_raises
        return run_review_for_prediction(_SYMBOL, _DATE)


# ─────────────────────────────────────────────────────────────────────────────
# Happy path
# ─────────────────────────────────────────────────────────────────────────────

class HappyPathTests(unittest.TestCase):

    def setUp(self) -> None:
        self.result = _run()

    def test_status_ok(self) -> None:
        self.assertEqual(self.result["status"], "ok")

    def test_symbol_passed_through(self) -> None:
        self.assertEqual(self.result["symbol"], _SYMBOL)

    def test_prediction_for_date_passed_through(self) -> None:
        self.assertEqual(self.result["prediction_for_date"], _DATE)

    def test_prediction_id_present(self) -> None:
        self.assertEqual(self.result["prediction_id"], _PID)

    def test_comparison_key_present(self) -> None:
        self.assertIn("comparison", self.result)
        self.assertIsInstance(self.result["comparison"], dict)

    def test_error_info_key_present(self) -> None:
        self.assertIn("error_info", self.result)
        self.assertIsInstance(self.result["error_info"], dict)

    def test_review_summary_key_present(self) -> None:
        self.assertIn("review_summary", self.result)
        self.assertIsInstance(self.result["review_summary"], str)
        self.assertGreater(len(self.result["review_summary"]), 0)

    def test_no_error_key_on_success(self) -> None:
        self.assertNotIn("error", self.result)

    def test_review_id_present_on_success(self) -> None:
        self.assertIn("review_id", self.result)
        self.assertEqual(self.result["review_id"], _FAKE_REVIEW_ID)

    def test_review_save_error_absent_on_success(self) -> None:
        self.assertNotIn("review_save_error", self.result)

    def test_capture_not_called_when_outcome_exists(self) -> None:
        with patch(_PATCH_GET_LATEST, return_value=_PREDICTION_ROW), \
             patch(_PATCH_GET_OUTCOME, return_value=_OUTCOME_ROW), \
             patch(_PATCH_CAPTURE) as mock_cap:
            run_review_for_prediction(_SYMBOL, _DATE)
        mock_cap.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# Version 2 review payload schema
# ─────────────────────────────────────────────────────────────────────────────

class ReviewV2SchemaTests(unittest.TestCase):

    def setUp(self) -> None:
        self.result = _run()

    def _v2_keys(self) -> set[str]:
        return {
            "meta",
            "primary_projection",
            "peer_adjustment",
            "final_projection",
            "historical_probability",
            "actual_outcome",
            "review_result",
            "rule_extraction",
        }

    def test_v2_top_level_blocks_present(self) -> None:
        self.assertTrue(self._v2_keys().issubset(self.result.keys()))

    def test_v2_top_level_blocks_are_dicts(self) -> None:
        for key in self._v2_keys():
            self.assertIsInstance(self.result[key], dict)

    def test_meta_schema_version_two(self) -> None:
        self.assertEqual(self.result["meta"]["schema_version"], 2)

    def test_meta_has_review_id_after_save(self) -> None:
        self.assertEqual(self.result["meta"]["review_id"], _FAKE_REVIEW_ID)

    def test_final_projection_uses_reviewed_prediction_shape(self) -> None:
        final_projection = self.result["final_projection"]
        self.assertEqual(final_projection["symbol"], _SYMBOL)
        self.assertEqual(final_projection["prediction_for_date"], _DATE)
        self.assertIn("pred_open", final_projection)
        self.assertIn("pred_path", final_projection)
        self.assertIn("pred_close", final_projection)

    def test_task10b_projection_blocks_are_computed(self) -> None:
        self.assertEqual(self.result["primary_projection"]["status"], "computed")
        self.assertEqual(self.result["primary_projection"]["peer_inputs_used"], False)
        self.assertEqual(self.result["peer_adjustment"]["status"], "computed")
        self.assertEqual(self.result["peer_adjustment"]["adjustment_direction"], "reinforce")
        self.assertEqual(self.result["final_projection"]["status"], "computed")
        self.assertEqual(self.result["historical_probability"]["status"], "reserved")
        self.assertEqual(self.result["rule_extraction"]["status"], "reserved")

    def test_review_result_contains_surface_and_mechanism_slots(self) -> None:
        review_result = self.result["review_result"]
        self.assertIn("surface_errors", review_result)
        self.assertIn("mechanism_errors", review_result)
        self.assertEqual(review_result["mechanism_errors"]["status"], "reserved")

    def test_actual_outcome_block_contains_derived_labels(self) -> None:
        actual = self.result["actual_outcome"]
        self.assertIn("actual_open_type", actual)
        self.assertIn("actual_path", actual)
        self.assertIn("actual_close_type", actual)

    def test_legacy_fields_remain_present(self) -> None:
        for key in ("comparison", "error_info", "review_summary"):
            self.assertIn(key, self.result)


# ─────────────────────────────────────────────────────────────────────────────
# Comparison and classification wired correctly
# ─────────────────────────────────────────────────────────────────────────────

class ComparisonWiringTests(unittest.TestCase):

    def setUp(self) -> None:
        self.result = _run()

    def test_comparison_has_pred_open(self) -> None:
        self.assertIn("pred_open", self.result["comparison"])

    def test_comparison_has_overall_score(self) -> None:
        self.assertIn("overall_score", self.result["comparison"])

    def test_error_info_has_error_types(self) -> None:
        self.assertIn("error_types", self.result["error_info"])

    def test_error_info_has_primary_error(self) -> None:
        self.assertIn("primary_error", self.result["error_info"])

    def test_error_info_has_reason_guesses(self) -> None:
        self.assertIn("reason_guesses", self.result["error_info"])

    def test_review_summary_contains_symbol(self) -> None:
        self.assertIn(_SYMBOL, self.result["review_summary"])

    def test_review_summary_contains_date(self) -> None:
        self.assertIn(_DATE, self.result["review_summary"])


# ─────────────────────────────────────────────────────────────────────────────
# No prediction found
# ─────────────────────────────────────────────────────────────────────────────

class NoPredictionTests(unittest.TestCase):

    def setUp(self) -> None:
        self.result = _run(prediction=None, outcome=_OUTCOME_ROW)

    def test_status_no_prediction(self) -> None:
        self.assertEqual(self.result["status"], "no_prediction")

    def test_error_message_present(self) -> None:
        self.assertIn("error", self.result)
        self.assertIsInstance(self.result["error"], str)
        self.assertGreater(len(self.result["error"]), 0)

    def test_no_comparison_key(self) -> None:
        self.assertNotIn("comparison", self.result)

    def test_prediction_id_is_none(self) -> None:
        self.assertIsNone(self.result["prediction_id"])


# ─────────────────────────────────────────────────────────────────────────────
# No outcome — auto-capture succeeds
# ─────────────────────────────────────────────────────────────────────────────

class AutoCaptureSuccessTests(unittest.TestCase):

    def test_capture_called_when_no_outcome(self) -> None:
        # First call returns None (not captured yet), second returns the row
        with patch(_PATCH_GET_LATEST, return_value=_PREDICTION_ROW), \
             patch(_PATCH_GET_OUTCOME, side_effect=[None, _OUTCOME_ROW]), \
             patch(_PATCH_CAPTURE) as mock_cap:
            result = run_review_for_prediction(_SYMBOL, _DATE)
        mock_cap.assert_called_once_with(_PID)
        self.assertEqual(result["status"], "ok")

    def test_status_ok_after_auto_capture(self) -> None:
        with patch(_PATCH_GET_LATEST, return_value=_PREDICTION_ROW), \
             patch(_PATCH_GET_OUTCOME, side_effect=[None, _OUTCOME_ROW]), \
             patch(_PATCH_CAPTURE):
            result = run_review_for_prediction(_SYMBOL, _DATE)
        self.assertEqual(result["status"], "ok")


# ─────────────────────────────────────────────────────────────────────────────
# No outcome — auto-capture fails (non-trading day, network error)
# ─────────────────────────────────────────────────────────────────────────────

class AutoCaptureFailureTests(unittest.TestCase):

    def test_status_no_outcome_on_value_error(self) -> None:
        result = _run(
            outcome=None,
            capture_raises=ValueError("not a trading day"),
        )
        self.assertEqual(result["status"], "no_outcome")

    def test_error_message_from_capture_exception(self) -> None:
        result = _run(
            outcome=None,
            capture_raises=ValueError("not a trading day"),
        )
        self.assertIn("trading day", result["error"])

    def test_status_error_on_unexpected_exception(self) -> None:
        result = _run(
            outcome=None,
            capture_raises=RuntimeError("yfinance timeout"),
        )
        self.assertEqual(result["status"], "error")

    def test_prediction_id_present_in_failure_payload(self) -> None:
        result = _run(
            outcome=None,
            capture_raises=ValueError("no data"),
        )
        self.assertEqual(result["prediction_id"], _PID)

    def test_no_comparison_key_on_no_outcome(self) -> None:
        result = _run(outcome=None, capture_raises=ValueError("no data"))
        self.assertNotIn("comparison", result)


# ─────────────────────────────────────────────────────────────────────────────
# Prediction lookup exception
# ─────────────────────────────────────────────────────────────────────────────

class PredictionLookupErrorTests(unittest.TestCase):

    def test_status_error_on_db_exception(self) -> None:
        with patch(_PATCH_GET_LATEST, side_effect=RuntimeError("db corrupt")):
            result = run_review_for_prediction(_SYMBOL, _DATE)
        self.assertEqual(result["status"], "error")
        self.assertIn("error", result)

    def test_does_not_raise(self) -> None:
        with patch(_PATCH_GET_LATEST, side_effect=Exception("unexpected")):
            result = run_review_for_prediction(_SYMBOL, _DATE)
        self.assertIsNotNone(result)


# ─────────────────────────────────────────────────────────────────────────────
# Payload fields always present regardless of status
# ─────────────────────────────────────────────────────────────────────────────

class PayloadFieldConsistencyTests(unittest.TestCase):

    def _required_keys(self) -> set[str]:
        return {"status", "symbol", "prediction_for_date", "prediction_id"}

    def test_ok_has_required_keys(self) -> None:
        r = _run()
        self.assertTrue(self._required_keys().issubset(r.keys()))

    def test_no_prediction_has_required_keys(self) -> None:
        r = _run(prediction=None, outcome=None)
        self.assertTrue(self._required_keys().issubset(r.keys()))

    def test_no_outcome_has_required_keys(self) -> None:
        r = _run(outcome=None, capture_raises=ValueError("no data"))
        self.assertTrue(self._required_keys().issubset(r.keys()))

    def test_symbol_always_present(self) -> None:
        for pred, out in [(None, None), (_PREDICTION_ROW, None)]:
            with self.subTest(pred=pred, out=out):
                r = _run(prediction=pred, outcome=out,
                         capture_raises=ValueError("x") if out is None and pred else None)
                self.assertEqual(r["symbol"], _SYMBOL)


# ─────────────────────────────────────────────────────────────────────────────
# Review persistence — save_review_record called on success
# ─────────────────────────────────────────────────────────────────────────────

class ReviewPersistenceTests(unittest.TestCase):

    def test_save_review_record_called_on_success(self) -> None:
        with patch(_PATCH_GET_LATEST, return_value=_PREDICTION_ROW), \
             patch(_PATCH_GET_OUTCOME, return_value=_OUTCOME_ROW), \
             patch(_PATCH_CAPTURE), \
             patch(_PATCH_SAVE_REVIEW, return_value=_FAKE_REVIEW_ID) as mock_save:
            run_review_for_prediction(_SYMBOL, _DATE)
        mock_save.assert_called_once()

    def test_saved_payload_contains_v2_blocks(self) -> None:
        with patch(_PATCH_GET_LATEST, return_value=_PREDICTION_ROW), \
             patch(_PATCH_GET_OUTCOME, return_value=_OUTCOME_ROW), \
             patch(_PATCH_CAPTURE), \
             patch(_PATCH_SAVE_REVIEW, return_value=_FAKE_REVIEW_ID) as mock_save:
            run_review_for_prediction(_SYMBOL, _DATE)
        saved_payload = mock_save.call_args.args[0]
        for key in (
            "meta",
            "primary_projection",
            "peer_adjustment",
            "final_projection",
            "historical_probability",
            "actual_outcome",
            "review_result",
            "rule_extraction",
        ):
            self.assertIn(key, saved_payload)

    def test_save_review_record_not_called_when_no_prediction(self) -> None:
        with patch(_PATCH_GET_LATEST, return_value=None), \
             patch(_PATCH_GET_OUTCOME, return_value=_OUTCOME_ROW), \
             patch(_PATCH_CAPTURE), \
             patch(_PATCH_SAVE_REVIEW) as mock_save:
            run_review_for_prediction(_SYMBOL, _DATE)
        mock_save.assert_not_called()

    def test_save_failure_does_not_raise(self) -> None:
        with patch(_PATCH_GET_LATEST, return_value=_PREDICTION_ROW), \
             patch(_PATCH_GET_OUTCOME, return_value=_OUTCOME_ROW), \
             patch(_PATCH_CAPTURE), \
             patch(_PATCH_SAVE_REVIEW, side_effect=RuntimeError("disk full")):
            result = run_review_for_prediction(_SYMBOL, _DATE)
        self.assertEqual(result["status"], "ok")

    def test_save_failure_sets_review_save_error(self) -> None:
        with patch(_PATCH_GET_LATEST, return_value=_PREDICTION_ROW), \
             patch(_PATCH_GET_OUTCOME, return_value=_OUTCOME_ROW), \
             patch(_PATCH_CAPTURE), \
             patch(_PATCH_SAVE_REVIEW, side_effect=RuntimeError("disk full")):
            result = run_review_for_prediction(_SYMBOL, _DATE)
        self.assertIn("review_save_error", result)
        self.assertIn("disk full", result["review_save_error"])

    def test_save_failure_review_id_absent(self) -> None:
        with patch(_PATCH_GET_LATEST, return_value=_PREDICTION_ROW), \
             patch(_PATCH_GET_OUTCOME, return_value=_OUTCOME_ROW), \
             patch(_PATCH_CAPTURE), \
             patch(_PATCH_SAVE_REVIEW, side_effect=RuntimeError("disk full")):
            result = run_review_for_prediction(_SYMBOL, _DATE)
        self.assertNotIn("review_id", result)


if __name__ == "__main__":
    unittest.main()
