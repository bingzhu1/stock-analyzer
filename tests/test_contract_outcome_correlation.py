"""Tests for services/contract_outcome_correlation.py (Step 1J)."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import services.prediction_store as ps
from services.contract_outcome_correlation import (
    GROUP_PATHS,
    correlate_outcomes_with_contract,
)


def _predict_result(
    bias: str = "bullish",
    confidence: str = "medium",
    pred_open: str = "高开",
    pred_path: str = "高开高走",
    pred_close: str = "收涨",
) -> dict:
    return {
        "symbol": "AVGO",
        "final_bias": bias,
        "final_confidence": confidence,
        "scan_bias": bias,
        "scan_confidence": confidence,
        "pred_open": pred_open,
        "pred_path": pred_path,
        "pred_close": pred_close,
        "prediction_summary": "<placeholder>",
        "supporting_factors": ["factor_a"],
        "conflicting_factors": [],
    }


def _save_outcome(pid: str, direction_correct: int | None) -> str:
    return ps.save_outcome(
        prediction_id=pid,
        prediction_for_date="2026-04-11",
        actual_open=100.0,
        actual_high=101.0,
        actual_low=99.0,
        actual_close=100.5,
        actual_prev_close=100.0,
        direction_correct=direction_correct,
    )


class _IsolatedStoreTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        ps.DB_PATH = Path(self._tmpdir.name) / "test.db"
        ps.init_db()

    def tearDown(self) -> None:
        self._tmpdir.cleanup()


# ── 1. no predictions ────────────────────────────────────────────────────────

class CorrelationNoRecordsTests(_IsolatedStoreTestCase):
    def test_no_predictions_returns_no_records_status(self) -> None:
        result = correlate_outcomes_with_contract()
        self.assertEqual(result["status"], "no_records")
        self.assertEqual(result["predictions_scanned"], 0)
        self.assertEqual(result["requested_limit"], 30)


# ── 2. all invalid → no_valid_contracts ──────────────────────────────────────

class CorrelationAllInvalidTests(_IsolatedStoreTestCase):
    def test_all_contracts_missing_or_invalid_returns_no_valid_contracts(self) -> None:
        ps.save_prediction(
            "AVGO", "2026-04-09", None, None, _predict_result(),
            contract_payload=None,
        )
        ps.save_prediction(
            "AVGO", "2026-04-10", None, None, _predict_result(),
            contract_payload={"only_one_section": "bogus"},
        )
        result = correlate_outcomes_with_contract()
        self.assertEqual(result["status"], "no_valid_contracts")
        self.assertEqual(result["valid_contracts"], 0)
        self.assertEqual(result["invalid_contracts"], 2)
        self.assertEqual(len(result["skipped_records"]), 2)


# ── 3. valid contracts but no outcomes → ok + pending ────────────────────────

class CorrelationAllPendingTests(_IsolatedStoreTestCase):
    def test_valid_contracts_without_outcomes_yield_ok_with_pending_only(self) -> None:
        for _ in range(3):
            ps.save_prediction("AVGO", "2026-04-11", None, None, _predict_result())
        result = correlate_outcomes_with_contract()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["valid_contracts"], 3)
        self.assertEqual(result["paired_outcomes"], 0)
        self.assertEqual(result["pending_outcomes"], 3)
        bullish = result["group_accuracy"]["final_projection.final_direction"]["偏多"]
        self.assertEqual(bullish["samples"], 3)
        self.assertEqual(bullish["correct"], 0)
        self.assertEqual(bullish["wrong"], 0)
        self.assertEqual(bullish["pending"], 3)
        self.assertIsNone(bullish["accuracy"])


# ── 4. correct / wrong outcomes drive accuracy ───────────────────────────────

class CorrelationAccuracyMathTests(_IsolatedStoreTestCase):
    def test_mix_of_correct_wrong_pending_yields_correct_accuracy(self) -> None:
        # 5 bullish predictions: 3 correct, 1 wrong, 1 pending
        pids = []
        for _ in range(5):
            pid = ps.save_prediction(
                "AVGO", "2026-04-11", None, None, _predict_result()
            )
            pids.append(pid)
        _save_outcome(pids[0], 1)
        _save_outcome(pids[1], 1)
        _save_outcome(pids[2], 1)
        _save_outcome(pids[3], 0)
        # pids[4] left without outcome → pending

        result = correlate_outcomes_with_contract()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["paired_outcomes"], 4)
        self.assertEqual(result["pending_outcomes"], 1)

        bullish = result["group_accuracy"]["final_projection.final_direction"]["偏多"]
        self.assertEqual(bullish["samples"], 5)
        self.assertEqual(bullish["correct"], 3)
        self.assertEqual(bullish["wrong"], 1)
        self.assertEqual(bullish["pending"], 1)
        self.assertAlmostEqual(bullish["accuracy"], 3 / 4, places=6)

    def test_zero_correct_zero_wrong_yields_accuracy_none(self) -> None:
        # All pending → accuracy should be None.
        for _ in range(3):
            ps.save_prediction("AVGO", "2026-04-11", None, None, _predict_result())
        result = correlate_outcomes_with_contract()
        bullish = result["group_accuracy"]["final_projection.final_direction"]["偏多"]
        self.assertEqual(bullish["correct"], 0)
        self.assertEqual(bullish["wrong"], 0)
        self.assertIsNone(bullish["accuracy"])

    def test_pending_excluded_from_accuracy_denominator(self) -> None:
        # 2 correct, 0 wrong, 8 pending → accuracy must be 1.0, not 2/10.
        pids = []
        for _ in range(10):
            pids.append(
                ps.save_prediction("AVGO", "2026-04-11", None, None, _predict_result())
            )
        _save_outcome(pids[0], 1)
        _save_outcome(pids[1], 1)
        result = correlate_outcomes_with_contract()
        bullish = result["group_accuracy"]["final_projection.final_direction"]["偏多"]
        self.assertEqual(bullish["pending"], 8)
        self.assertEqual(bullish["accuracy"], 1.0)


# ── 5. grouping by each path ─────────────────────────────────────────────────

class CorrelationGroupingTests(_IsolatedStoreTestCase):
    def test_groups_by_final_direction(self) -> None:
        # 3 bullish (all correct), 2 bearish (all wrong)
        for _ in range(3):
            pid = ps.save_prediction(
                "AVGO", "2026-04-11", None, None,
                _predict_result(bias="bullish", pred_close="收涨"),
            )
            _save_outcome(pid, 1)
        for _ in range(2):
            pid = ps.save_prediction(
                "AVGO", "2026-04-11", None, None,
                _predict_result(bias="bearish", pred_close="收跌",
                                 pred_open="低开", pred_path="低开低走"),
            )
            _save_outcome(pid, 0)
        result = correlate_outcomes_with_contract()
        groups = result["group_accuracy"]["final_projection.final_direction"]
        self.assertIn("偏多", groups)
        self.assertIn("偏空", groups)
        self.assertEqual(groups["偏多"]["correct"], 3)
        self.assertEqual(groups["偏多"]["accuracy"], 1.0)
        self.assertEqual(groups["偏空"]["wrong"], 2)
        self.assertEqual(groups["偏空"]["accuracy"], 0.0)

    def test_groups_by_confidence_level(self) -> None:
        # 4 medium (3 correct, 1 wrong), 2 high (1 correct, 1 wrong)
        med_pids = [
            ps.save_prediction(
                "AVGO", "2026-04-11", None, None,
                _predict_result(confidence="medium"),
            )
            for _ in range(4)
        ]
        for pid, dc in zip(med_pids, [1, 1, 1, 0]):
            _save_outcome(pid, dc)
        high_pids = [
            ps.save_prediction(
                "AVGO", "2026-04-11", None, None,
                _predict_result(confidence="high"),
            )
            for _ in range(2)
        ]
        for pid, dc in zip(high_pids, [1, 0]):
            _save_outcome(pid, dc)

        result = correlate_outcomes_with_contract()
        groups = result["group_accuracy"]["confidence_system.confidence_level"]
        self.assertEqual(groups["medium"]["samples"], 4)
        self.assertAlmostEqual(groups["medium"]["accuracy"], 3 / 4, places=6)
        self.assertEqual(groups["high"]["samples"], 2)
        self.assertEqual(groups["high"]["accuracy"], 0.5)

    def test_groups_by_five_state(self) -> None:
        # 2 小涨 (1 correct, 1 wrong), 1 小跌 (1 correct), 1 震荡 (pending)
        pid = ps.save_prediction(
            "AVGO", "2026-04-11", None, None,
            _predict_result(bias="bullish", pred_close="收涨"),
        )
        _save_outcome(pid, 1)
        pid = ps.save_prediction(
            "AVGO", "2026-04-11", None, None,
            _predict_result(bias="bullish", pred_close="收涨"),
        )
        _save_outcome(pid, 0)
        pid = ps.save_prediction(
            "AVGO", "2026-04-11", None, None,
            _predict_result(bias="bearish", pred_close="收跌",
                             pred_open="低开", pred_path="低开低走"),
        )
        _save_outcome(pid, 1)
        # 震荡 → bias=neutral OR mixed close. Easiest path: bullish bias but
        # pred_close="收跌" → adapter picks 震荡 (no 偏多+收跌 mapping).
        ps.save_prediction(
            "AVGO", "2026-04-11", None, None,
            _predict_result(bias="bullish", pred_close="收跌"),
        )

        result = correlate_outcomes_with_contract()
        groups = result["group_accuracy"]["final_projection.final_five_state"]
        self.assertEqual(groups["小涨"]["correct"], 1)
        self.assertEqual(groups["小涨"]["wrong"], 1)
        self.assertEqual(groups["小涨"]["accuracy"], 0.5)
        self.assertEqual(groups["小跌"]["correct"], 1)
        self.assertEqual(groups["小跌"]["accuracy"], 1.0)
        self.assertEqual(groups["震荡"]["pending"], 1)
        self.assertIsNone(groups["震荡"]["accuracy"])


# ── 9-11. skipped reasons ────────────────────────────────────────────────────

class CorrelationSkippedReasonsTests(_IsolatedStoreTestCase):
    def test_missing_contract_payload_is_skipped(self) -> None:
        ps.save_prediction(
            "AVGO", "2026-04-11", None, None, _predict_result(),
            contract_payload=None,
        )
        ps.save_prediction("AVGO", "2026-04-11", None, None, _predict_result())
        result = correlate_outcomes_with_contract()
        reasons = [s["reason"] for s in result["skipped_records"]]
        self.assertIn("missing_contract_payload", reasons)
        self.assertEqual(result["valid_contracts"], 1)

    def test_invalid_json_is_skipped(self) -> None:
        bogus_pid = ps.save_prediction(
            "AVGO", "2026-04-11", None, None, _predict_result(),
            contract_payload=None,
        )
        with ps._get_conn() as conn:
            conn.execute(
                "UPDATE prediction_log SET contract_payload_json = ? WHERE id = ?",
                ("{not valid json", bogus_pid),
            )
        ps.save_prediction("AVGO", "2026-04-11", None, None, _predict_result())
        result = correlate_outcomes_with_contract()
        reasons = [s["reason"] for s in result["skipped_records"]]
        self.assertIn("invalid_json", reasons)
        self.assertEqual(result["valid_contracts"], 1)

    def test_validation_failed_is_skipped(self) -> None:
        ps.save_prediction(
            "AVGO", "2026-04-11", None, None, _predict_result(),
            contract_payload={"only_one_section": "bogus"},
        )
        ps.save_prediction("AVGO", "2026-04-11", None, None, _predict_result())
        result = correlate_outcomes_with_contract()
        reasons = [s["reason"] for s in result["skipped_records"]]
        self.assertIn("validation_failed", reasons)
        self.assertEqual(result["valid_contracts"], 1)


# ── 12-13. limit handling ────────────────────────────────────────────────────

class CorrelationLimitTests(_IsolatedStoreTestCase):
    def test_limit_truncates_predictions_scanned(self) -> None:
        for _ in range(40):
            ps.save_prediction("AVGO", "2026-04-11", None, None, _predict_result())
        result = correlate_outcomes_with_contract(limit=10)
        self.assertEqual(result["requested_limit"], 10)
        self.assertEqual(result["predictions_scanned"], 10)

    def test_zero_limit_falls_back_to_default_30(self) -> None:
        for _ in range(35):
            ps.save_prediction("AVGO", "2026-04-11", None, None, _predict_result())
        result = correlate_outcomes_with_contract(limit=0)
        self.assertEqual(result["requested_limit"], 30)
        self.assertEqual(result["predictions_scanned"], 30)

    def test_negative_limit_falls_back_to_default_30(self) -> None:
        for _ in range(35):
            ps.save_prediction("AVGO", "2026-04-11", None, None, _predict_result())
        result = correlate_outcomes_with_contract(limit=-5)
        self.assertEqual(result["requested_limit"], 30)

    def test_non_int_limit_falls_back_to_default_30(self) -> None:
        for _ in range(2):
            ps.save_prediction("AVGO", "2026-04-11", None, None, _predict_result())
        result = correlate_outcomes_with_contract(limit="abc")  # type: ignore[arg-type]
        self.assertEqual(result["requested_limit"], 30)

    def test_bool_limit_falls_back_to_default_30(self) -> None:
        for _ in range(2):
            ps.save_prediction("AVGO", "2026-04-11", None, None, _predict_result())
        result = correlate_outcomes_with_contract(limit=True)  # type: ignore[arg-type]
        self.assertEqual(result["requested_limit"], 30)


# ── 14. read-only ───────────────────────────────────────────────────────────

class CorrelationReadOnlyTests(_IsolatedStoreTestCase):
    def test_correlate_does_not_mutate_db(self) -> None:
        for _ in range(3):
            pid = ps.save_prediction(
                "AVGO", "2026-04-11", None, None, _predict_result()
            )
            _save_outcome(pid, 1)
        with ps._get_conn() as conn:
            count_pred_before = conn.execute(
                "SELECT COUNT(*) FROM prediction_log"
            ).fetchone()[0]
            count_outcome_before = conn.execute(
                "SELECT COUNT(*) FROM outcome_log"
            ).fetchone()[0]
            rows_before = [
                dict(r) for r in conn.execute("SELECT * FROM prediction_log")
            ]
            outcomes_before = [
                dict(r) for r in conn.execute("SELECT * FROM outcome_log")
            ]

        correlate_outcomes_with_contract()
        correlate_outcomes_with_contract(limit=5)
        correlate_outcomes_with_contract(limit=100)

        with ps._get_conn() as conn:
            count_pred_after = conn.execute(
                "SELECT COUNT(*) FROM prediction_log"
            ).fetchone()[0]
            count_outcome_after = conn.execute(
                "SELECT COUNT(*) FROM outcome_log"
            ).fetchone()[0]
            rows_after = [
                dict(r) for r in conn.execute("SELECT * FROM prediction_log")
            ]
            outcomes_after = [
                dict(r) for r in conn.execute("SELECT * FROM outcome_log")
            ]
        self.assertEqual(count_pred_before, count_pred_after)
        self.assertEqual(count_outcome_before, count_outcome_after)
        self.assertEqual(rows_before, rows_after)
        self.assertEqual(outcomes_before, outcomes_after)


# ── 15. DB error path ────────────────────────────────────────────────────────

class CorrelationErrorPathTests(unittest.TestCase):
    def test_unreadable_db_path_returns_error_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = correlate_outcomes_with_contract(db_path=tmpdir)
        self.assertEqual(result["status"], "error")
        self.assertTrue(result["error"].startswith("db_read_failed"))


# ── 16. correlated subquery picks the latest outcome per prediction ──────────

class CorrelationLatestOutcomeTests(_IsolatedStoreTestCase):
    def test_only_most_recent_outcome_per_prediction_is_used(self) -> None:
        # Save one prediction; capture two outcomes for it (re-capture scenario).
        # The latest outcome (direction_correct=0) must override the first (=1).
        pid = ps.save_prediction(
            "AVGO", "2026-04-11", None, None, _predict_result()
        )
        _save_outcome(pid, 1)
        _save_outcome(pid, 0)  # latest by captured_at + rowid
        result = correlate_outcomes_with_contract()
        bullish = result["group_accuracy"]["final_projection.final_direction"]["偏多"]
        self.assertEqual(bullish["correct"], 0)
        self.assertEqual(bullish["wrong"], 1)
        self.assertEqual(bullish["pending"], 0)


# ── 17. GROUP_PATHS sanity ───────────────────────────────────────────────────

class CorrelationGroupPathsContractTests(unittest.TestCase):
    def test_group_paths_match_user_specified_set(self) -> None:
        self.assertEqual(
            set(GROUP_PATHS),
            {
                ("final_projection", "final_direction"),
                ("confidence_system", "confidence_level"),
                ("final_projection", "final_five_state"),
            },
        )
        self.assertEqual(len(GROUP_PATHS), 3)


if __name__ == "__main__":
    unittest.main()
