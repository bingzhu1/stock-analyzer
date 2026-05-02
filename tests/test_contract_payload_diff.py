"""Tests for services/contract_payload_diff.py (Step 1H)."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import services.prediction_store as ps
from services.contract_payload_diff import (
    DIFF_PATHS,
    diff_latest_contract_payloads,
)
from services.projection_output_adapter import adapt_projection_output


def _predict_result(
    bias: str = "bullish",
    confidence: str = "medium",
    pred_open: str = "高开",
    pred_path: str = "高开高走",
    pred_close: str = "收涨",
    summary: str = "<placeholder summary>",
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
        "prediction_summary": summary,
        "supporting_factors": ["factor_a"],
        "conflicting_factors": [],
    }


def _make_contract(predict_result: dict) -> dict:
    """Convenience: run the adapter to get a fully-valid contract payload."""
    return adapt_projection_output(
        scan_result=None, research_result=None, predict_result=predict_result
    )


class _IsolatedStoreTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        ps.DB_PATH = Path(self._tmpdir.name) / "test.db"
        ps.init_db()

    def tearDown(self) -> None:
        self._tmpdir.cleanup()


# ── 1. not_enough_records ─────────────────────────────────────────────────────

class DiffNotEnoughRecordsTests(_IsolatedStoreTestCase):
    def test_no_records_returns_not_enough_records(self) -> None:
        result = diff_latest_contract_payloads()
        self.assertEqual(result["status"], "not_enough_records")
        self.assertEqual(result["available_records"], 0)

    def test_one_record_returns_not_enough_records(self) -> None:
        ps.save_prediction("AVGO", "2026-04-11", None, None, _predict_result())
        result = diff_latest_contract_payloads()
        self.assertEqual(result["status"], "not_enough_records")
        self.assertEqual(result["available_records"], 1)


# ── 2. ok with no changes ─────────────────────────────────────────────────────

class DiffNoChangeTests(_IsolatedStoreTestCase):
    def test_two_identical_payloads_yield_ok_with_empty_changed_fields(self) -> None:
        # Save twice with the SAME explicit contract_payload so the diff
        # output is fully deterministic (no reliance on timing).
        contract = _make_contract(_predict_result())
        ps.save_prediction(
            "AVGO", "2026-04-10", None, None, _predict_result(),
            contract_payload=contract,
        )
        ps.save_prediction(
            "AVGO", "2026-04-11", None, None, _predict_result(),
            contract_payload=contract,
        )
        result = diff_latest_contract_payloads()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["changed_fields"], [])
        self.assertEqual(result["summary"], {})


# ── 3. ok with changes ───────────────────────────────────────────────────────

class DiffChangedFieldTests(_IsolatedStoreTestCase):
    def _save_pair(
        self, prev_predict: dict, latest_predict: dict
    ) -> tuple[str, str]:
        prev_pid = ps.save_prediction(
            "AVGO", "2026-04-10", None, None, prev_predict,
            contract_payload=_make_contract(prev_predict),
        )
        # Sleep just enough so created_at strictly orders, even on systems
        # where two saves can land in the same wall-clock second.
        latest_pid = ps.save_prediction(
            "AVGO", "2026-04-11", None, None, latest_predict,
            contract_payload=_make_contract(latest_predict),
        )
        return prev_pid, latest_pid

    def test_changed_final_direction_appears_in_changed_fields(self) -> None:
        prev_pid, latest_pid = self._save_pair(
            _predict_result(bias="bullish",  pred_close="收涨"),
            _predict_result(bias="bearish",  pred_close="收跌", pred_open="低开",
                             pred_path="低开低走"),
        )
        result = diff_latest_contract_payloads()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["latest_prediction_id"], latest_pid)
        self.assertEqual(result["previous_prediction_id"], prev_pid)
        self.assertIn("final_projection.final_direction", result["changed_fields"])
        self.assertEqual(
            result["summary"]["final_direction"],
            {"from": "偏多", "to": "偏空"},
        )

    def test_changed_confidence_level_is_detected(self) -> None:
        self._save_pair(
            _predict_result(confidence="medium"),
            _predict_result(confidence="high"),
        )
        result = diff_latest_contract_payloads()
        self.assertIn("confidence_system.confidence_level", result["changed_fields"])
        self.assertEqual(
            result["summary"]["confidence_level"],
            {"from": "medium", "to": "high"},
        )

    def test_changed_total_confidence_is_detected(self) -> None:
        self._save_pair(
            _predict_result(confidence="low"),
            _predict_result(confidence="high"),
        )
        result = diff_latest_contract_payloads()
        self.assertIn("confidence_system.total_confidence", result["changed_fields"])
        # Adapter mapping: low → 0.25, high → 0.75
        self.assertEqual(
            result["summary"]["total_confidence"],
            {"from": 0.25, "to": 0.75},
        )

    def test_changed_exclusion_level_is_detected_via_explicit_payload(self) -> None:
        # The adapter currently emits exclusion_level="none" by default; to
        # produce a "soft" prev row we override exclusion_system in the
        # explicit contract dict.
        prev_contract = _make_contract(_predict_result())
        prev_contract["exclusion_system"]["exclusion_level"] = "soft"
        latest_contract = _make_contract(_predict_result())
        # latest stays at "none"

        ps.save_prediction(
            "AVGO", "2026-04-10", None, None, _predict_result(),
            contract_payload=prev_contract,
        )
        ps.save_prediction(
            "AVGO", "2026-04-11", None, None, _predict_result(),
            contract_payload=latest_contract,
        )
        result = diff_latest_contract_payloads()
        self.assertEqual(result["status"], "ok")
        self.assertIn("exclusion_system.exclusion_level", result["changed_fields"])
        self.assertEqual(
            result["summary"]["exclusion_level"],
            {"from": "soft", "to": "none"},
        )

    def test_changed_trade_action_is_detected_via_explicit_payload(self) -> None:
        # Adapter defaults trade_action to "no_trade"; vary it via explicit
        # payloads to exercise the diff path on simulated_trade.
        prev_contract = _make_contract(_predict_result())
        latest_contract = _make_contract(_predict_result())
        latest_contract["simulated_trade"]["trade_action"] = "open"
        latest_contract["simulated_trade"]["trade_direction"] = "long"
        latest_contract["simulated_trade"]["suggested_position_size"] = "50%"

        ps.save_prediction(
            "AVGO", "2026-04-10", None, None, _predict_result(),
            contract_payload=prev_contract,
        )
        ps.save_prediction(
            "AVGO", "2026-04-11", None, None, _predict_result(),
            contract_payload=latest_contract,
        )
        result = diff_latest_contract_payloads()
        self.assertIn("simulated_trade.trade_action", result["changed_fields"])
        self.assertIn("simulated_trade.suggested_position_size", result["changed_fields"])
        self.assertEqual(
            result["summary"]["trade_action"], {"from": "no_trade", "to": "open"}
        )


# ── 4. error statuses ────────────────────────────────────────────────────────

class DiffMissingPayloadTests(_IsolatedStoreTestCase):
    def test_missing_contract_payload_on_latest_returns_missing_status(self) -> None:
        # Previous has a valid payload (auto-gen), latest opts out via None.
        ps.save_prediction("AVGO", "2026-04-10", None, None, _predict_result())
        ps.save_prediction(
            "AVGO", "2026-04-11", None, None, _predict_result(),
            contract_payload=None,
        )
        result = diff_latest_contract_payloads()
        self.assertEqual(result["status"], "missing_contract_payload")
        self.assertEqual(result["failed_side"], "latest")

    def test_missing_contract_payload_on_previous_returns_missing_status(self) -> None:
        ps.save_prediction(
            "AVGO", "2026-04-10", None, None, _predict_result(),
            contract_payload=None,
        )
        ps.save_prediction("AVGO", "2026-04-11", None, None, _predict_result())
        result = diff_latest_contract_payloads()
        self.assertEqual(result["status"], "missing_contract_payload")
        self.assertEqual(result["failed_side"], "previous")


class DiffInvalidJsonTests(_IsolatedStoreTestCase):
    def test_invalid_json_in_latest_returns_invalid_json_status(self) -> None:
        ps.save_prediction("AVGO", "2026-04-10", None, None, _predict_result())
        latest_pid = ps.save_prediction(
            "AVGO", "2026-04-11", None, None, _predict_result(),
            contract_payload=None,
        )
        # Corrupt the latest row's payload directly via SQL.
        with ps._get_conn() as conn:
            conn.execute(
                "UPDATE prediction_log SET contract_payload_json = ? WHERE id = ?",
                ("{not valid json", latest_pid),
            )
        result = diff_latest_contract_payloads()
        self.assertEqual(result["status"], "invalid_json")
        self.assertEqual(result["failed_side"], "latest")
        self.assertIn("error", result)


class DiffValidationFailedTests(_IsolatedStoreTestCase):
    def test_validation_failed_in_previous_returns_validation_failed_status(self) -> None:
        # Previous has a non-contract-shaped explicit dict that fails
        # validation; latest is fine.
        ps.save_prediction(
            "AVGO", "2026-04-10", None, None, _predict_result(),
            contract_payload={"only_one_section": "bogus"},
        )
        ps.save_prediction("AVGO", "2026-04-11", None, None, _predict_result())
        result = diff_latest_contract_payloads()
        self.assertEqual(result["status"], "validation_failed")
        self.assertEqual(result["failed_side"], "previous")
        self.assertIsInstance(result["validation_errors"], list)
        self.assertTrue(result["validation_errors"])


# ── 5. error path (DB unreadable) ────────────────────────────────────────────

class DiffErrorPathTests(unittest.TestCase):
    def test_unreadable_db_path_returns_error_status(self) -> None:
        # Pointing at a directory makes the SELECT fail. The diff tool must
        # report "error" rather than raise.
        with tempfile.TemporaryDirectory() as tmpdir:
            result = diff_latest_contract_payloads(db_path=tmpdir)
        self.assertEqual(result["status"], "error")
        self.assertTrue(result["error"].startswith("db_read_failed"))


# ── 6. read-only ────────────────────────────────────────────────────────────

class DiffReadOnlyTests(_IsolatedStoreTestCase):
    def test_diff_does_not_change_row_count_or_field_values(self) -> None:
        prev_pid = ps.save_prediction(
            "AVGO", "2026-04-10", None, None, _predict_result()
        )
        latest_pid = ps.save_prediction(
            "AVGO", "2026-04-11", None, None, _predict_result(confidence="high")
        )
        before_prev = ps.get_prediction(prev_pid)
        before_latest = ps.get_prediction(latest_pid)
        with ps._get_conn() as conn:
            count_before = conn.execute(
                "SELECT COUNT(*) FROM prediction_log"
            ).fetchone()[0]

        diff_latest_contract_payloads()
        diff_latest_contract_payloads()  # twice for good measure

        with ps._get_conn() as conn:
            count_after = conn.execute(
                "SELECT COUNT(*) FROM prediction_log"
            ).fetchone()[0]
        self.assertEqual(count_before, count_after)
        self.assertEqual(ps.get_prediction(prev_pid), before_prev)
        self.assertEqual(ps.get_prediction(latest_pid), before_latest)


# ── 7. DIFF_PATHS coverage sanity ────────────────────────────────────────────

class DiffPathsContractTests(unittest.TestCase):
    def test_diff_paths_cover_user_specified_set(self) -> None:
        expected = {
            ("final_projection", "final_direction"),
            ("final_projection", "final_five_state"),
            ("final_projection", "probability_bucket"),
            ("final_projection", "final_one_sentence"),
            ("confidence_system", "confidence_level"),
            ("confidence_system", "total_confidence"),
            ("exclusion_system", "exclusion_level"),
            ("simulated_trade", "trade_action"),
            ("simulated_trade", "trade_direction"),
            ("simulated_trade", "suggested_position_size"),
        }
        self.assertEqual(set(DIFF_PATHS), expected)
        self.assertEqual(len(DIFF_PATHS), 10)


if __name__ == "__main__":
    unittest.main()
