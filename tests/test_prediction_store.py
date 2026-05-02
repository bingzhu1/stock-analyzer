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


class ContractPayloadStoreTests(unittest.TestCase):
    """Step 1E: prediction_log carries an optional contract_payload_json column."""

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        ps.DB_PATH = Path(self._tmpdir.name) / "test.db"
        ps.init_db()

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    # ── 1. backward compat: legacy callers don't pass contract_payload ────────

    def test_legacy_save_without_contract_payload_auto_generates(self) -> None:
        """Step 1F: legacy callers (no ``contract_payload`` kwarg) get a
        contract_payload_json auto-populated by the side-path. The save
        succeeds, legacy fields are intact, and the JSON parses back to a
        full 8-section contract dict."""
        from services.projection_output_contract import CONTRACT_SECTIONS

        pid = ps.save_prediction(
            "AVGO", "2026-04-11", None, None, _make_predict_result()
        )
        row = ps.get_prediction(pid)
        assert row is not None
        # Side-path wrote the column.
        self.assertIsNotNone(row["contract_payload_json"])
        payload = json.loads(row["contract_payload_json"])
        self.assertEqual(set(payload.keys()), set(CONTRACT_SECTIONS))
        # Legacy fields untouched.
        self.assertEqual(row["final_bias"], "bullish")
        self.assertEqual(row["status"], "saved")
        self.assertEqual(row["symbol"], "AVGO")

    # ── 2. valid payload round-trips ──────────────────────────────────────────

    def test_valid_contract_payload_round_trips(self) -> None:
        contract_payload = {
            "current_structure": {
                "symbol": "AVGO",
                "analysis_date": "2026-04-09",
            },
            "review_payload": {"prediction_id": "pid-placeholder"},
        }
        pid = ps.save_prediction(
            "AVGO",
            "2026-04-11",
            None,
            None,
            _make_predict_result(),
            contract_payload=contract_payload,
        )
        row = ps.get_prediction(pid)
        assert row is not None
        self.assertIsNotNone(row["contract_payload_json"])
        decoded = json.loads(row["contract_payload_json"])
        self.assertEqual(decoded, contract_payload)

    def test_save_prediction_record_passes_through_contract_payload(self) -> None:
        record = {
            "symbol": "AVGO",
            "prediction_for_date": "2026-04-11",
            "predict_result": _make_predict_result(),
            "contract_payload": {"current_structure": {"symbol": "AVGO"}},
        }
        pid = ps.save_prediction_record(record)
        row = ps.get_prediction(pid)
        assert row is not None
        decoded = json.loads(row["contract_payload_json"])
        self.assertEqual(decoded, record["contract_payload"])

    # ── 3. invalid payload does not break the save ────────────────────────────

    def test_invalid_contract_payload_does_not_break_save(self) -> None:
        # The store does not validate; it just persists. Even contract-illegal
        # payloads must not crash save_prediction or corrupt the legacy row.
        bogus = {"only_one_section": "this is not contract-shaped"}
        pid = ps.save_prediction(
            "AVGO",
            "2026-04-11",
            None,
            None,
            _make_predict_result(),
            contract_payload=bogus,
        )
        row = ps.get_prediction(pid)
        assert row is not None
        self.assertEqual(row["final_bias"], "bullish")  # legacy fields intact
        self.assertEqual(json.loads(row["contract_payload_json"]), bogus)

    def test_explicit_none_contract_payload_stores_null(self) -> None:
        pid = ps.save_prediction(
            "AVGO",
            "2026-04-11",
            None,
            None,
            _make_predict_result(),
            contract_payload=None,
        )
        row = ps.get_prediction(pid)
        assert row is not None
        self.assertIsNone(row["contract_payload_json"])

    # ── 4. legacy DBs (pre-Step-1E schema) get migrated on init_db() ──────────

    def test_old_db_without_contract_payload_column_is_migrated(self) -> None:
        # Simulate an old DB by dropping the column-aware schema and creating
        # a minimal legacy table that lacks contract_payload_json.
        with ps._get_conn() as conn:
            conn.execute("DROP TABLE prediction_log")
            conn.execute(
                """
                CREATE TABLE prediction_log (
                    id                   TEXT PRIMARY KEY,
                    symbol               TEXT NOT NULL,
                    analysis_date        TEXT NOT NULL,
                    prediction_for_date  TEXT NOT NULL,
                    created_at           TEXT NOT NULL,
                    final_bias           TEXT NOT NULL,
                    final_confidence     TEXT NOT NULL,
                    status               TEXT NOT NULL DEFAULT 'saved',
                    scan_result_json     TEXT,
                    research_result_json TEXT,
                    predict_result_json  TEXT NOT NULL,
                    snapshot_id          TEXT
                )
                """
            )
            # Sanity: column genuinely absent before migration.
            cols_before = {r["name"] for r in conn.execute("PRAGMA table_info(prediction_log)")}
            self.assertNotIn("contract_payload_json", cols_before)

        # init_db must add the column without dropping data.
        ps.init_db()

        with ps._get_conn() as conn:
            cols_after = {r["name"] for r in conn.execute("PRAGMA table_info(prediction_log)")}
        self.assertIn("contract_payload_json", cols_after)

        # And it must be idempotent — second call is a no-op.
        ps.init_db()

        # New saves with contract_payload work end-to-end on the migrated table.
        pid = ps.save_prediction(
            "AVGO",
            "2026-04-11",
            None,
            None,
            _make_predict_result(),
            contract_payload={"current_structure": {"symbol": "AVGO"}},
        )
        row = ps.get_prediction(pid)
        assert row is not None
        self.assertEqual(
            json.loads(row["contract_payload_json"]),
            {"current_structure": {"symbol": "AVGO"}},
        )

    def test_legacy_row_with_null_contract_payload_reads_back_cleanly(self) -> None:
        # Insert a row directly via SQL, leaving contract_payload_json NULL,
        # to mimic a row written before Step 1E.
        legacy_pid = "legacy-id-0000"
        with ps._get_conn() as conn:
            conn.execute(
                """INSERT INTO prediction_log
                   (id, symbol, analysis_date, prediction_for_date, created_at,
                    final_bias, final_confidence, status,
                    scan_result_json, research_result_json, predict_result_json,
                    snapshot_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    legacy_pid, "AVGO", "2026-04-09", "2026-04-11",
                    "2026-04-09T00:00:00",
                    "bullish", "medium", "saved",
                    None, None, json.dumps(_make_predict_result()),
                    "—",
                ),
            )

        row = ps.get_prediction(legacy_pid)
        assert row is not None
        self.assertEqual(row["id"], legacy_pid)
        self.assertIsNone(row["contract_payload_json"])
        # list_predictions and get_prediction_by_date also must not crash.
        rows = ps.list_predictions(limit=10)
        self.assertEqual(len(rows), 1)
        self.assertEqual(
            ps.get_prediction_by_date("AVGO", "2026-04-11")["id"],  # type: ignore[index]
            legacy_pid,
        )


class ContractSavePathSideEffectTests(unittest.TestCase):
    """Step 1F: prediction_store.save_prediction wraps a side-path that
    auto-builds and validates a Projection Output Contract payload."""

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        ps.DB_PATH = Path(self._tmpdir.name) / "test.db"
        ps.init_db()

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    # ── 1. happy path: side-path writes a valid contract payload ──────────────

    def test_side_path_writes_contract_payload_that_passes_validator(self) -> None:
        from services.projection_output_contract import (
            CONTRACT_SECTIONS,
            validate_projection_output,
        )

        pid = ps.save_prediction(
            "AVGO", "2026-04-11", None, None, _make_predict_result()
        )
        row = ps.get_prediction(pid)
        assert row is not None
        self.assertIsNotNone(row["contract_payload_json"])
        payload = json.loads(row["contract_payload_json"])
        # Round-trips cleanly through json AND passes the contract validator.
        self.assertEqual(set(payload.keys()), set(CONTRACT_SECTIONS))
        self.assertEqual(validate_projection_output(payload), [])

    def test_save_prediction_record_auto_generates_when_contract_omitted(self) -> None:
        from services.projection_output_contract import CONTRACT_SECTIONS

        record = {
            "symbol": "AVGO",
            "prediction_for_date": "2026-04-11",
            "predict_result": _make_predict_result(),
            # NOTE: no "contract_payload" key — auto-gen path triggers.
        }
        pid = ps.save_prediction_record(record)
        row = ps.get_prediction(pid)
        assert row is not None
        payload = json.loads(row["contract_payload_json"])
        self.assertEqual(set(payload.keys()), set(CONTRACT_SECTIONS))

    # ── 2. opt-out: explicit None still stores NULL (no auto-gen) ─────────────

    def test_explicit_none_disables_auto_gen(self) -> None:
        # Disambiguates "caller did not pass" (auto-gen) from "caller
        # explicitly passed None" (store NULL, no side-path).
        pid = ps.save_prediction(
            "AVGO", "2026-04-11", None, None, _make_predict_result(),
            contract_payload=None,
        )
        row = ps.get_prediction(pid)
        assert row is not None
        self.assertIsNone(row["contract_payload_json"])

    def test_save_prediction_record_explicit_none_disables_auto_gen(self) -> None:
        record = {
            "symbol": "AVGO",
            "prediction_for_date": "2026-04-11",
            "predict_result": _make_predict_result(),
            "contract_payload": None,  # explicit opt-out
        }
        pid = ps.save_prediction_record(record)
        row = ps.get_prediction(pid)
        assert row is not None
        self.assertIsNone(row["contract_payload_json"])

    # ── 3. failure isolation: adapter / validator faults don't break save ─────

    def test_adapter_failure_falls_back_to_null_without_breaking_save(self) -> None:
        with patch.object(
            ps,
            "_try_build_contract_payload",
            side_effect=RuntimeError("adapter exploded"),
        ):
            # Even if helper itself raises (it shouldn't, but defense in depth):
            # the save flow must propagate the exception only from helper, not
            # from the legacy save. Here we test the contract that _try_build
            # is responsible for swallowing — so simulate via direct failure
            # of adapter inside its own try/except block.
            with self.assertRaises(RuntimeError):
                ps.save_prediction(
                    "AVGO", "2026-04-11", None, None, _make_predict_result()
                )
        # Confirm the contract: when _try_build is well-behaved (returns None on
        # any inner failure), save must succeed and store NULL.
        with patch.object(ps, "_try_build_contract_payload", return_value=None):
            pid = ps.save_prediction(
                "AVGO", "2026-04-11", None, None, _make_predict_result()
            )
        row = ps.get_prediction(pid)
        assert row is not None
        self.assertIsNone(row["contract_payload_json"])
        self.assertEqual(row["final_bias"], "bullish")  # legacy save still wrote

    def test_inner_adapter_exception_is_swallowed_by_helper(self) -> None:
        # Simulate the realistic failure path: adapter raises inside the
        # helper. The helper must catch it and return None; save proceeds.
        with patch(
            "services.projection_output_adapter.adapt_projection_output",
            side_effect=RuntimeError("boom"),
        ):
            pid = ps.save_prediction(
                "AVGO", "2026-04-11", None, None, _make_predict_result()
            )
        row = ps.get_prediction(pid)
        assert row is not None
        self.assertIsNone(row["contract_payload_json"])
        self.assertEqual(row["final_bias"], "bullish")

    def test_validation_failure_falls_back_to_null(self) -> None:
        # Adapter returns OK, but validator returns a non-empty error list.
        # Helper drops the payload (returns None); save proceeds with NULL.
        with patch(
            "services.projection_output_contract.validate_projection_output",
            return_value=["invalid value: exclusion_system.exclusion_level"],
        ):
            pid = ps.save_prediction(
                "AVGO", "2026-04-11", None, None, _make_predict_result()
            )
        row = ps.get_prediction(pid)
        assert row is not None
        self.assertIsNone(row["contract_payload_json"])
        self.assertEqual(row["final_bias"], "bullish")

    # ── 4. legacy callers / fields are not affected ───────────────────────────

    def test_predict_result_json_is_unchanged_by_side_path(self) -> None:
        pr = _make_predict_result()
        original = json.loads(json.dumps(pr))  # snapshot
        pid = ps.save_prediction("AVGO", "2026-04-11", None, None, pr)
        row = ps.get_prediction(pid)
        assert row is not None
        stored = json.loads(row["predict_result_json"])
        self.assertEqual(stored, original)
        # And the in-memory dict must not have been mutated either.
        self.assertEqual(pr, original)

    def test_explicit_dict_contract_payload_skips_auto_gen(self) -> None:
        # Explicit dict is stored verbatim — side-path is bypassed entirely.
        custom = {"my_custom": "payload", "not_contract_shaped": True}
        pid = ps.save_prediction(
            "AVGO", "2026-04-11", None, None, _make_predict_result(),
            contract_payload=custom,
        )
        row = ps.get_prediction(pid)
        assert row is not None
        self.assertEqual(json.loads(row["contract_payload_json"]), custom)


if __name__ == "__main__":
    unittest.main()
