from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import services.prediction_store as ps
from services.review_agent import (
    _build_user_prompt,
    _extract_json,
    _rule_based_fallback,
    _validate,
    generate_review,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_prediction(prediction_for_date: str = "2026-04-11", bias: str = "bullish") -> dict:
    """Return a dict shaped like a prediction_log row."""
    predict_result = {
        "symbol": "AVGO",
        "final_bias": bias,
        "final_confidence": "high",
        "scan_bias": bias,
        "research_bias_adjustment": "confirms_bias",
        "prediction_summary": "Strong momentum expected.",
        "supporting_factors": ["gap_up", "volume_surge"],
        "conflicting_factors": ["overbought_rsi"],
    }
    return {
        "symbol": "AVGO",
        "prediction_for_date": prediction_for_date,
        "final_bias": bias,
        "final_confidence": "high",
        "predict_result_json": json.dumps(predict_result),
    }


def _make_outcome(direction_correct: int | None = 1,
                  close_change: float = 0.025) -> dict:
    """Return a dict shaped like an outcome_log row."""
    return {
        "direction_correct": direction_correct,
        "actual_open_change": 0.01,
        "actual_close_change": close_change,
    }


def _saved_prediction_with_outcome(
    tmpdir: Path,
    bias: str = "bullish",
    direction_correct: int | None = 1,
    close_change: float = 0.025,
) -> str:
    """Insert prediction + outcome into the temp DB and return prediction_id."""
    pr_dict = {
        "symbol": "AVGO",
        "final_bias": bias,
        "final_confidence": "high",
        "scan_bias": bias,
        "research_bias_adjustment": "confirms_bias",
        "prediction_summary": "test",
        "supporting_factors": [],
        "conflicting_factors": [],
    }
    pid = ps.save_prediction(
        symbol="AVGO",
        prediction_for_date="2026-04-11",
        scan_result=None,
        research_result=None,
        predict_result=pr_dict,
    )
    ps.save_outcome(
        prediction_id=pid,
        prediction_for_date="2026-04-11",
        actual_open=172.0,
        actual_high=175.0,
        actual_low=171.0,
        actual_close=174.0,
        actual_prev_close=171.0,
        direction_correct=direction_correct,
        scenario_match=None,
    )
    ps.update_prediction_status(pid, "outcome_captured")
    return pid


# ─────────────────────────────────────────────────────────────────────────────
# _build_user_prompt
# ─────────────────────────────────────────────────────────────────────────────

class BuildUserPromptTests(unittest.TestCase):
    def test_date_is_not_na_when_prediction_for_date_set(self) -> None:
        prediction = _make_prediction(prediction_for_date="2026-04-11")
        outcome = _make_outcome()
        prompt = _build_user_prompt(prediction, outcome)
        self.assertIn("Date: 2026-04-11", prompt)
        self.assertNotIn("Date: N/A", prompt)

    def test_date_falls_back_to_na_when_field_missing(self) -> None:
        prediction = _make_prediction()
        del prediction["prediction_for_date"]
        outcome = _make_outcome()
        prompt = _build_user_prompt(prediction, outcome)
        self.assertIn("Date: N/A", prompt)

    def test_supporting_factors_appear_in_prompt(self) -> None:
        prediction = _make_prediction()
        outcome = _make_outcome()
        prompt = _build_user_prompt(prediction, outcome)
        self.assertIn("gap_up", prompt)
        self.assertIn("volume_surge", prompt)

    def test_direction_label_correct_when_bullish_right(self) -> None:
        prediction = _make_prediction(bias="bullish")
        outcome = _make_outcome(direction_correct=1)
        prompt = _build_user_prompt(prediction, outcome)
        self.assertIn("YES (correct)", prompt)

    def test_direction_label_wrong_direction(self) -> None:
        prediction = _make_prediction(bias="bullish")
        outcome = _make_outcome(direction_correct=0)
        prompt = _build_user_prompt(prediction, outcome)
        self.assertIn("NO (wrong)", prompt)

    def test_direction_label_neutral(self) -> None:
        prediction = _make_prediction()
        outcome = _make_outcome(direction_correct=None)
        prompt = _build_user_prompt(prediction, outcome)
        self.assertIn("N/A (neutral", prompt)

    def test_pct_formatted_correctly(self) -> None:
        prediction = _make_prediction()
        outcome = _make_outcome(close_change=0.0312)
        prompt = _build_user_prompt(prediction, outcome)
        self.assertIn("3.12", prompt)

    def test_scenario_match_values_appear_in_prompt_when_present(self) -> None:
        scenario_json = json.dumps({
            "exact_match_count": 3,
            "near_match_count": 2,
            "dominant_historical_outcome": "bullish",
            "top_context_score": 87.5,
        })
        prediction = _make_prediction()
        outcome = _make_outcome()
        outcome["scenario_match"] = scenario_json
        prompt = _build_user_prompt(prediction, outcome)
        self.assertIn("exact=3", prompt)
        self.assertIn("near=2", prompt)
        self.assertIn("dominant=bullish", prompt)
        self.assertIn("top_context_score=87.5", prompt)

    def test_scenario_match_is_na_when_absent(self) -> None:
        prediction = _make_prediction()
        outcome = _make_outcome()
        # no scenario_match key in outcome
        prompt = _build_user_prompt(prediction, outcome)
        self.assertIn("Scenario Match: N/A", prompt)

    def test_scenario_match_shows_na_fields_for_empty_dict(self) -> None:
        """Empty {} scenario_match produces N/A fields in the prompt, not an error."""
        prediction = _make_prediction()
        outcome = _make_outcome()
        outcome["scenario_match"] = "{}"
        prompt = _build_user_prompt(prediction, outcome)
        self.assertIn("exact=N/A", prompt)
        self.assertIn("near=N/A", prompt)


# ─────────────────────────────────────────────────────────────────────────────
# _extract_json
# ─────────────────────────────────────────────────────────────────────────────

class ExtractJsonTests(unittest.TestCase):
    def test_plain_json(self) -> None:
        raw = '{"error_category": "correct", "root_cause": "ok", "confidence_note": "good", "watch_for_next_time": "nothing"}'
        parsed = _extract_json(raw)
        self.assertEqual(parsed["error_category"], "correct")

    def test_strips_json_code_fence(self) -> None:
        raw = '```json\n{"error_category": "correct", "root_cause": "ok", "confidence_note": "good", "watch_for_next_time": "nothing"}\n```'
        parsed = _extract_json(raw)
        self.assertEqual(parsed["error_category"], "correct")

    def test_strips_plain_code_fence(self) -> None:
        raw = '```\n{"error_category": "wrong_direction"}\n```'
        parsed = _extract_json(raw)
        self.assertEqual(parsed["error_category"], "wrong_direction")

    def test_raises_on_invalid_json(self) -> None:
        with self.assertRaises(json.JSONDecodeError):
            _extract_json("not valid json")


# ─────────────────────────────────────────────────────────────────────────────
# _validate
# ─────────────────────────────────────────────────────────────────────────────

class ValidateTests(unittest.TestCase):
    def test_normalizes_error_category_to_taxonomy_value(self) -> None:
        parsed = {
            "error_category": "Wrong Direction",
            "root_cause": "The move went the other way.",
            "confidence_note": "Confidence was too high.",
            "watch_for_next_time": "Watch the opening move.",
        }
        validated = _validate(parsed)
        self.assertEqual(validated["error_category"], "wrong_direction")

    def test_unknown_error_category_falls_back_to_insufficient_data(self) -> None:
        parsed = {
            "error_category": "mystery_bucket",
            "root_cause": "No clear category.",
            "confidence_note": "Confidence cannot be assessed.",
            "watch_for_next_time": "Review manually.",
        }
        validated = _validate(parsed)
        self.assertEqual(validated["error_category"], "insufficient_data")


# ─────────────────────────────────────────────────────────────────────────────
# _rule_based_fallback
# ─────────────────────────────────────────────────────────────────────────────

class RuleBasedFallbackTests(unittest.TestCase):
    def _fallback(self, direction_correct: int | None,
                  close_change: float = 0.025,
                  bias: str = "bullish") -> dict:
        prediction = {"final_bias": bias, "final_confidence": "high"}
        outcome = {"direction_correct": direction_correct,
                   "actual_close_change": close_change}
        return _rule_based_fallback(prediction, outcome)

    def test_direction_correct_1_large_move_is_correct(self) -> None:
        result = self._fallback(direction_correct=1, close_change=0.025)
        self.assertEqual(result["error_category"], "correct")
        self.assertIn("correct", result["root_cause"].lower())

    def test_direction_correct_1_tiny_move_is_right_direction_wrong_magnitude(self) -> None:
        # close_change < 1% → right_direction_wrong_magnitude
        result = self._fallback(direction_correct=1, close_change=0.005)
        self.assertEqual(result["error_category"], "right_direction_wrong_magnitude")

    def test_direction_correct_0_is_wrong_direction(self) -> None:
        result = self._fallback(direction_correct=0, close_change=-0.03)
        self.assertEqual(result["error_category"], "wrong_direction")
        self.assertIn("wrong", result["root_cause"].lower())

    def test_direction_correct_none_is_insufficient_data(self) -> None:
        result = self._fallback(direction_correct=None, close_change=0.0)
        self.assertEqual(result["error_category"], "insufficient_data")

    def test_result_always_has_four_fields(self) -> None:
        for dc in (1, 0, None):
            result = self._fallback(direction_correct=dc)
            for field in ("error_category", "root_cause", "confidence_note", "watch_for_next_time"):
                self.assertIn(field, result, f"Missing {field} for direction_correct={dc}")


# ─────────────────────────────────────────────────────────────────────────────
# generate_review (integration — isolated DB, no real Anthropic calls)
# ─────────────────────────────────────────────────────────────────────────────

class GenerateReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        ps.DB_PATH = Path(self._tmpdir.name) / "test.db"
        ps.init_db()

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_raises_if_prediction_missing(self) -> None:
        with self.assertRaises(ValueError):
            generate_review("nonexistent-id")

    def test_raises_if_outcome_missing(self) -> None:
        pr = {
            "symbol": "AVGO", "final_bias": "bullish", "final_confidence": "medium",
            "prediction_summary": "test", "supporting_factors": [], "conflicting_factors": [],
        }
        pid = ps.save_prediction("AVGO", "2026-04-11", None, None, pr)
        with self.assertRaises(ValueError):
            generate_review(pid)

    def test_uses_fallback_when_no_api_key(self) -> None:
        pid = _saved_prediction_with_outcome(Path(self._tmpdir.name))
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": ""}):
            review = generate_review(pid)
        self.assertIsNotNone(review)
        self.assertIn(review["error_category"],
                      {"correct", "wrong_direction", "right_direction_wrong_magnitude",
                       "false_confidence", "insufficient_data"})
        # Rule-based fallback sets a specific watch_for_next_time message
        self.assertIn("manually", review["watch_for_next_time"].lower())

    def test_is_idempotent(self) -> None:
        pid = _saved_prediction_with_outcome(Path(self._tmpdir.name))
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": ""}):
            review1 = generate_review(pid)
            review2 = generate_review(pid)
        self.assertEqual(review1["id"], review2["id"])

    def test_advances_status_to_review_generated(self) -> None:
        pid = _saved_prediction_with_outcome(Path(self._tmpdir.name))
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": ""}):
            generate_review(pid)
        row = ps.get_prediction(pid)
        assert row is not None
        self.assertEqual(row["status"], "review_generated")

    def test_review_json_field_is_populated(self) -> None:
        pid = _saved_prediction_with_outcome(Path(self._tmpdir.name))
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": ""}):
            review = generate_review(pid)
        # review_json should be a JSON string containing error_category
        self.assertIn("error_category", review.get("review_json", ""))


if __name__ == "__main__":
    unittest.main()
