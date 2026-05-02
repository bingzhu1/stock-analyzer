"""Tests for services/contract_payload_inspector.py (Step 1G)."""
from __future__ import annotations

import copy
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import services.prediction_store as ps
from services.contract_payload_inspector import inspect_latest_contract_payload
from services.projection_output_contract import CONTRACT_SECTIONS


def _make_predict_result(
    bias: str = "bullish", confidence: str = "medium"
) -> dict:
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


class _IsolatedStoreTestCase(unittest.TestCase):
    """Common setUp/tearDown: every test gets a fresh tmp DB."""

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        ps.DB_PATH = Path(self._tmpdir.name) / "test.db"
        ps.init_db()

    def tearDown(self) -> None:
        self._tmpdir.cleanup()


class InspectorEmptyDBTests(_IsolatedStoreTestCase):
    def test_no_records_returns_no_records_status(self) -> None:
        result = inspect_latest_contract_payload()
        self.assertEqual(result["status"], "no_records")
        # No id/symbol/date — there's no record to identify.
        self.assertNotIn("prediction_id", result)


class InspectorMissingPayloadTests(_IsolatedStoreTestCase):
    def test_explicit_none_contract_payload_yields_missing_status(self) -> None:
        # Save with explicit None to opt-out of the side-path.
        pid = ps.save_prediction(
            "AVGO", "2026-04-11", None, None, _make_predict_result(),
            contract_payload=None,
        )
        result = inspect_latest_contract_payload()
        self.assertEqual(result["status"], "missing_contract_payload")
        self.assertEqual(result["prediction_id"], pid)
        self.assertEqual(result["symbol"], "AVGO")
        self.assertEqual(result["prediction_for_date"], "2026-04-11")


class InspectorInvalidJSONTests(_IsolatedStoreTestCase):
    def test_corrupt_json_in_column_returns_invalid_json_status(self) -> None:
        # Save a row with explicit None first, then corrupt the column directly
        # via SQL to simulate a row written by an out-of-date writer.
        pid = ps.save_prediction(
            "AVGO", "2026-04-11", None, None, _make_predict_result(),
            contract_payload=None,
        )
        with ps._get_conn() as conn:
            conn.execute(
                "UPDATE prediction_log SET contract_payload_json = ? WHERE id = ?",
                ("{not valid json", pid),
            )
        result = inspect_latest_contract_payload()
        self.assertEqual(result["status"], "invalid_json")
        self.assertEqual(result["prediction_id"], pid)
        self.assertIn("error", result)


class InspectorValidationFailedTests(_IsolatedStoreTestCase):
    def test_non_contract_shaped_payload_returns_validation_failed(self) -> None:
        # Pass an explicit dict that is JSON-valid but not contract-shaped.
        bogus = {"only_one_section": "not contract"}
        pid = ps.save_prediction(
            "AVGO", "2026-04-11", None, None, _make_predict_result(),
            contract_payload=bogus,
        )
        result = inspect_latest_contract_payload()
        self.assertEqual(result["status"], "validation_failed")
        self.assertEqual(result["prediction_id"], pid)
        self.assertTrue(result["validation_errors"])
        self.assertIsInstance(result["validation_errors"], list)
        self.assertIsInstance(result["sections_present"], list)


class InspectorOkPathTests(_IsolatedStoreTestCase):
    def test_side_path_auto_generated_payload_returns_ok(self) -> None:
        # Don't pass contract_payload — Step 1F side-path will auto-build.
        pid = ps.save_prediction(
            "AVGO", "2026-04-11", None, None, _make_predict_result()
        )
        result = inspect_latest_contract_payload()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["prediction_id"], pid)
        self.assertEqual(result["symbol"], "AVGO")
        self.assertEqual(result["prediction_for_date"], "2026-04-11")
        self.assertEqual(result["validation_errors"], [])

    def test_ok_result_lists_all_eight_sections_present(self) -> None:
        ps.save_prediction("AVGO", "2026-04-11", None, None, _make_predict_result())
        result = inspect_latest_contract_payload()
        self.assertEqual(set(result["sections_present"]), set(CONTRACT_SECTIONS))
        self.assertEqual(len(result["sections_present"]), 8)

    def test_ok_summary_has_one_string_per_section(self) -> None:
        ps.save_prediction("AVGO", "2026-04-11", None, None, _make_predict_result())
        result = inspect_latest_contract_payload()
        self.assertIn("summary", result)
        summary = result["summary"]
        self.assertEqual(set(summary.keys()), set(CONTRACT_SECTIONS))
        for section, value in summary.items():
            self.assertIsInstance(value, str, msg=f"summary[{section}] is not str")
            self.assertTrue(value.strip(), msg=f"summary[{section}] is empty")


class InspectorReadOnlyTests(_IsolatedStoreTestCase):
    def test_inspector_does_not_mutate_db(self) -> None:
        pid = ps.save_prediction(
            "AVGO", "2026-04-11", None, None, _make_predict_result()
        )
        before = ps.get_prediction(pid)
        assert before is not None
        before_snapshot = copy.deepcopy(before)

        # Inspect multiple times — each call must leave the row identical.
        inspect_latest_contract_payload()
        inspect_latest_contract_payload()

        after = ps.get_prediction(pid)
        self.assertEqual(after, before_snapshot)

    def test_inspector_does_not_change_row_count(self) -> None:
        ps.save_prediction("AVGO", "2026-04-11", None, None, _make_predict_result())
        with ps._get_conn() as conn:
            before = conn.execute("SELECT COUNT(*) FROM prediction_log").fetchone()[0]
        inspect_latest_contract_payload()
        with ps._get_conn() as conn:
            after = conn.execute("SELECT COUNT(*) FROM prediction_log").fetchone()[0]
        self.assertEqual(before, after)


class InspectorLatestRowSelectionTests(_IsolatedStoreTestCase):
    def test_inspector_picks_most_recently_created_row(self) -> None:
        ps.save_prediction("AVGO", "2026-04-09", None, None, _make_predict_result())
        ps.save_prediction("AVGO", "2026-04-11", None, None, _make_predict_result())
        latest_pid = ps.save_prediction(
            "AVGO", "2026-04-10", None, None, _make_predict_result()
        )
        # The 3rd save is the most recently created, even though its
        # prediction_for_date is older than the 2nd.
        result = inspect_latest_contract_payload()
        self.assertEqual(result["prediction_id"], latest_pid)
        self.assertEqual(result["prediction_for_date"], "2026-04-10")


class InspectorErrorPathTests(unittest.TestCase):
    def test_unreadable_db_path_returns_error_status(self) -> None:
        # Point inspector at a directory (not a file) so sqlite3.connect
        # succeeds but the SELECT fails. Returned status must be "error" —
        # never raise.
        with tempfile.TemporaryDirectory() as tmpdir:
            result = inspect_latest_contract_payload(db_path=tmpdir)
        self.assertEqual(result["status"], "error")
        self.assertIn("error", result)
        self.assertTrue(result["error"].startswith("db_read_failed"))


class InspectorDbPathArgumentTests(_IsolatedStoreTestCase):
    def test_explicit_db_path_overrides_module_default(self) -> None:
        ps.save_prediction("AVGO", "2026-04-11", None, None, _make_predict_result())
        explicit = ps.DB_PATH
        # Switch ps.DB_PATH to a fresh path so the default would be empty.
        with tempfile.TemporaryDirectory() as other_tmpdir:
            ps.DB_PATH = Path(other_tmpdir) / "other.db"
            ps.init_db()
            # Explicit arg uses the original DB (which has data).
            result = inspect_latest_contract_payload(db_path=str(explicit))
        self.assertEqual(result["status"], "ok")


if __name__ == "__main__":
    unittest.main()
