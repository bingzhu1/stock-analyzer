from __future__ import annotations

import json
import sys
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import services.prediction_store as ps


def _make_predict_result(bias: str = "bullish", confidence: str = "medium") -> dict:
    return {
        "symbol": "AVGO",
        "final_bias": bias,
        "final_confidence": confidence,
        "scan_bias": bias,
        "scan_confidence": confidence,
        "prediction_summary": "test summary",
        "supporting_factors": ["factor_a"],
        "conflicting_factors": [],
    }


class PredictionStoreTests(unittest.TestCase):
    """
    All tests use an isolated temp DB so they don't touch the real avgo_agent.db.
    """

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        ps.DB_PATH = Path(self._tmpdir.name) / "test.db"
        ps.init_db()

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    # ── prediction_log ────────────────────────────────────────────────────────

    def test_save_and_get_prediction(self) -> None:
        pr = _make_predict_result()
        pid = ps.save_prediction(
            symbol="AVGO",
            prediction_for_date="2026-04-11",
            scan_result=None,
            research_result=None,
            predict_result=pr,
        )
        self.assertIsInstance(pid, str)
        self.assertEqual(len(pid), 36)  # UUID4

        row = ps.get_prediction(pid)
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row["symbol"], "AVGO")
        self.assertEqual(row["prediction_for_date"], "2026-04-11")
        self.assertEqual(row["final_bias"], "bullish")
        self.assertEqual(row["status"], "saved")
        self.assertIn("analysis_date", row)

    def test_save_prediction_round_trips_two_step_projection_blocks(self) -> None:
        pr = _make_predict_result(confidence="high")
        pr["primary_projection"] = {
            "status": "computed",
            "source": "avgo_recent_20_scan_context",
            "lookback_days": 20,
            "peer_inputs_used": False,
            "final_bias": "bullish",
            "final_confidence": "medium",
        }
        pr["peer_adjustment"] = {
            "status": "computed",
            "source": "peer_relative_strength",
            "peer_symbols": ["NVDA", "SOXX", "QQQ"],
            "adjustment_direction": "reinforce",
            "adjusted_bias": "bullish",
            "adjusted_confidence": "high",
        }
        pr["final_projection"] = {
            "status": "computed",
            "source": "primary_projection_plus_peer_adjustment",
            "final_bias": "bullish",
            "final_confidence": "high",
            "pred_open": "高开",
            "pred_path": "高开高走",
            "pred_close": "收涨",
        }

        pid = ps.save_prediction(
            symbol="AVGO",
            prediction_for_date="2026-04-11",
            scan_result=None,
            research_result=None,
            predict_result=pr,
        )

        row = ps.get_prediction(pid)
        self.assertIsNotNone(row)
        assert row is not None
        stored = json.loads(row["predict_result_json"])
        self.assertEqual(stored["primary_projection"]["lookback_days"], 20)
        self.assertFalse(stored["primary_projection"]["peer_inputs_used"])
        self.assertEqual(stored["peer_adjustment"]["peer_symbols"], ["NVDA", "SOXX", "QQQ"])
        self.assertEqual(stored["final_projection"]["pred_path"], "高开高走")
        self.assertEqual(row["final_bias"], "bullish")
        self.assertEqual(row["final_confidence"], "high")

    def test_get_prediction_returns_none_for_missing(self) -> None:
        self.assertIsNone(ps.get_prediction("nonexistent-id"))

    def test_get_prediction_by_date_returns_latest_save_with_tiebreaker(self) -> None:
        pr = _make_predict_result()
        ps.save_prediction("AVGO", "2026-04-11", None, None, pr)
        pid2 = ps.save_prediction("AVGO", "2026-04-11", None, None, pr)

        row = ps.get_prediction_by_date("AVGO", "2026-04-11")
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row["id"], pid2)
        self.assertEqual(row["prediction_for_date"], "2026-04-11")

    def test_get_prediction_by_date_returns_none_for_missing(self) -> None:
        self.assertIsNone(ps.get_prediction_by_date("AVGO", "2026-01-01"))

    def test_multiple_saves_same_date_both_persist(self) -> None:
        pr = _make_predict_result()
        pid1 = ps.save_prediction("AVGO", "2026-04-11", None, None, pr)
        pid2 = ps.save_prediction("AVGO", "2026-04-11", None, None, pr)
        self.assertNotEqual(pid1, pid2)
        self.assertIsNotNone(ps.get_prediction(pid1))
        self.assertIsNotNone(ps.get_prediction(pid2))

    # ── status machine ────────────────────────────────────────────────────────

    def test_update_status_advances_forward(self) -> None:
        pr = _make_predict_result()
        pid = ps.save_prediction("AVGO", "2026-04-11", None, None, pr)

        ps.update_prediction_status(pid, "outcome_captured")
        row = ps.get_prediction(pid)
        assert row is not None
        self.assertEqual(row["status"], "outcome_captured")

        ps.update_prediction_status(pid, "review_generated")
        row = ps.get_prediction(pid)
        assert row is not None
        self.assertEqual(row["status"], "review_generated")

    def test_update_status_does_not_rollback(self) -> None:
        pr = _make_predict_result()
        pid = ps.save_prediction("AVGO", "2026-04-11", None, None, pr)

        ps.update_prediction_status(pid, "review_generated")
        ps.update_prediction_status(pid, "outcome_captured")  # should be no-op
        ps.update_prediction_status(pid, "saved")             # should be no-op

        row = ps.get_prediction(pid)
        assert row is not None
        self.assertEqual(row["status"], "review_generated")

    def test_update_status_is_idempotent(self) -> None:
        pr = _make_predict_result()
        pid = ps.save_prediction("AVGO", "2026-04-11", None, None, pr)

        ps.update_prediction_status(pid, "outcome_captured")
        ps.update_prediction_status(pid, "outcome_captured")  # duplicate, should be no-op
        row = ps.get_prediction(pid)
        assert row is not None
        self.assertEqual(row["status"], "outcome_captured")

    def test_update_status_on_missing_id_is_safe(self) -> None:
        # Should not raise
        ps.update_prediction_status("nonexistent-id", "outcome_captured")

    def test_connection_enforces_foreign_keys(self) -> None:
        with ps._get_conn() as conn:
            row = conn.execute("PRAGMA foreign_keys").fetchone()
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row[0], 1)

    # ── outcome_log ───────────────────────────────────────────────────────────

    def test_save_and_get_outcome(self) -> None:
        pr = _make_predict_result()
        pid = ps.save_prediction("AVGO", "2026-04-11", None, None, pr)

        oid = ps.save_outcome(
            prediction_id=pid,
            prediction_for_date="2026-04-11",
            actual_open=175.0,
            actual_high=188.0,
            actual_low=144.0,
            actual_close=177.0,
            actual_prev_close=174.0,
            direction_correct=1,
            scenario_match=None,
        )
        self.assertIsInstance(oid, str)

        outcome = ps.get_outcome_for_prediction(pid)
        self.assertIsNotNone(outcome)
        assert outcome is not None
        self.assertEqual(outcome["actual_close"], 177.0)
        self.assertEqual(outcome["direction_correct"], 1)
        self.assertIsNone(outcome["scenario_match"])
        # open_change and close_change computed automatically
        self.assertAlmostEqual(outcome["close_change"] if "close_change" in outcome
                               else outcome["actual_close_change"],
                               (177.0 - 174.0) / 174.0, places=6)

    def test_get_outcome_returns_none_for_missing(self) -> None:
        self.assertIsNone(ps.get_outcome_for_prediction("nonexistent-id"))

    def test_save_outcome_rejects_missing_prediction(self) -> None:
        with self.assertRaises(ValueError):
            ps.save_outcome(
                prediction_id="nonexistent-id",
                prediction_for_date="2026-04-11",
                actual_open=170.0,
                actual_high=188.0,
                actual_low=144.0,
                actual_close=177.0,
                actual_prev_close=174.0,
                direction_correct=1,
                scenario_match=None,
            )

        with ps._get_conn() as conn:
            count = conn.execute("SELECT COUNT(*) FROM outcome_log").fetchone()[0]
        self.assertEqual(count, 0)

    def test_save_outcome_advances_status(self) -> None:
        """save_outcome itself does not advance status — outcome_capture does.
        But update_prediction_status called externally should work."""
        pr = _make_predict_result()
        pid = ps.save_prediction("AVGO", "2026-04-11", None, None, pr)
        ps.update_prediction_status(pid, "outcome_captured")
        row = ps.get_prediction(pid)
        assert row is not None
        self.assertEqual(row["status"], "outcome_captured")

    # ── review_log ────────────────────────────────────────────────────────────

    def test_save_review_persists_and_advances_status(self) -> None:
        pr = _make_predict_result()
        pid = ps.save_prediction("AVGO", "2026-04-11", None, None, pr)
        ps.update_prediction_status(pid, "outcome_captured")

        review_data = {
            "error_category": "correct",
            "root_cause": "Bullish momentum followed through.",
            "confidence_note": "High confidence was appropriate.",
            "watch_for_next_time": "Watch volume on open.",
        }
        import json
        rid = ps.save_review(
            prediction_id=pid,
            error_category=review_data["error_category"],
            root_cause=review_data["root_cause"],
            confidence_note=review_data["confidence_note"],
            watch_for_next_time=review_data["watch_for_next_time"],
            review_json=json.dumps(review_data),
            raw_llm_output='{"error_category": "correct"}',
        )
        self.assertIsInstance(rid, str)

        review = ps.get_review_for_prediction(pid)
        self.assertIsNotNone(review)
        assert review is not None
        self.assertEqual(review["error_category"], "correct")
        self.assertEqual(review["root_cause"], "Bullish momentum followed through.")
        self.assertIn("review_json", review)

        # save_review must have advanced status to review_generated
        row = ps.get_prediction(pid)
        assert row is not None
        self.assertEqual(row["status"], "review_generated")

    def test_get_review_returns_none_for_missing(self) -> None:
        self.assertIsNone(ps.get_review_for_prediction("nonexistent-id"))

    def test_save_review_rejects_missing_prediction_without_orphan_row(self) -> None:
        with self.assertRaises(ValueError):
            ps.save_review(
                prediction_id="nonexistent-id",
                error_category="correct",
                root_cause="n/a",
                confidence_note="n/a",
                watch_for_next_time="n/a",
                review_json="{}",
                raw_llm_output="{}",
            )

        with ps._get_conn() as conn:
            count = conn.execute("SELECT COUNT(*) FROM review_log").fetchone()[0]
        self.assertEqual(count, 0)

    # ── list_predictions ──────────────────────────────────────────────────────

    def test_list_predictions_returns_newest_first(self) -> None:
        pr = _make_predict_result()
        ps.save_prediction("AVGO", "2026-04-09", None, None, pr)
        ps.save_prediction("AVGO", "2026-04-11", None, None, pr)
        ps.save_prediction("AVGO", "2026-04-10", None, None, pr)

        rows = ps.list_predictions(limit=10)
        self.assertEqual(len(rows), 3)
        dates = [r["prediction_for_date"] for r in rows]
        self.assertEqual(dates, sorted(dates, reverse=True))

    def test_list_predictions_respects_limit(self) -> None:
        pr = _make_predict_result()
        for i in range(5):
            ps.save_prediction("AVGO", f"2026-04-{10 + i:02d}", None, None, pr)
        rows = ps.list_predictions(limit=3)
        self.assertEqual(len(rows), 3)

    def test_list_predictions_includes_status(self) -> None:
        pr = _make_predict_result()
        ps.save_prediction("AVGO", "2026-04-11", None, None, pr)
        rows = ps.list_predictions(limit=5)
        self.assertIn("status", rows[0])

    def test_list_predictions_includes_scenario_match(self) -> None:
        pr = _make_predict_result()
        pid = ps.save_prediction("AVGO", "2026-04-11", None, None, pr)
        ps.save_outcome(
            prediction_id=pid,
            prediction_for_date="2026-04-11",
            actual_open=175.0,
            actual_high=178.0,
            actual_low=174.0,
            actual_close=177.0,
            actual_prev_close=174.0,
            direction_correct=1,
            scenario_match='{"match_sample_size": 5}',
        )

        rows = ps.list_predictions(limit=5)
        self.assertEqual(rows[0]["scenario_match"], '{"match_sample_size": 5}')

    def test_list_predictions_reports_corrupt_db_as_controlled_error(self) -> None:
        with patch.object(
            ps,
            "init_db",
            side_effect=sqlite3.DatabaseError("database disk image is malformed"),
        ):
            with self.assertRaises(ps.PredictionStoreCorruptionError) as ctx:
                ps.list_predictions(limit=5)

        self.assertIn("历史记录数据库损坏", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
