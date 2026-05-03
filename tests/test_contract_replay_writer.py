"""Tests for services/contract_replay_writer.py (Step 2F-4c-2).

dry_run=True (default) still NEVER calls run_predict / save_prediction /
save_outcome. dry_run=False walks each (D, D+1) pair, runs predict on a
historical scan derived from coded_data, and writes a prediction_log
row + outcome_log row via save_prediction / save_outcome (with
analysis_date_override=D, captured_at_override=D+1T16:00:00).

These tests use isolated tmp DBs and synthetic CSVs; nothing touches the
real coded_data/ directory, the real DB, or yfinance.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import services.prediction_store as ps
from services import contract_replay_writer as crw
from services.contract_replay_writer import run_contract_replay


def _business_day_dates(n: int, start: date = date(2024, 1, 2)) -> list[str]:
    """Generate n business-day ISO dates starting at ``start``."""
    out: list[str] = []
    d = start - timedelta(days=1)
    while len(out) < n:
        d += timedelta(days=1)
        if d.weekday() < 5:  # Mon-Fri
            out.append(d.isoformat())
    return out


def _write_realistic_csv(
    dir_path: Path,
    symbol: str,
    n_days: int = 35,
    *,
    bias_up: bool = True,
) -> Path:
    """Write a coded CSV with full per-row OHLCV + O_gap / C_move / V_ratio.

    The columns mirror the real coded_data/<SYMBOL>_coded.csv subset that
    ``_build_historical_scan_at`` and ``_read_outcome_row`` consume. With
    ``bias_up=True`` close is rising linearly so the scan trend is
    bullish; ``bias_up=False`` flips for variety.
    """
    dates = _business_day_dates(n_days)
    rows = ["Date,Open,High,Low,Close,Volume,PrevClose,O_gap,C_move,V_ratio"]
    prev_close: float | None = None
    step = 0.5 if bias_up else -0.3
    for i, dt in enumerate(dates):
        close = 100.0 + i * step
        open_ = close - 0.25
        high = close + 0.6
        low = close - 0.7
        vol = 1_000_000 + i * 1_000
        if prev_close is None:
            o_gap = 0.0
            c_move = 0.0
            prev_close_str = ""
        else:
            o_gap = (open_ - prev_close) / prev_close
            c_move = (close - prev_close) / prev_close
            prev_close_str = f"{prev_close:.6f}"
        v_ratio = 1.2
        rows.append(
            f"{dt},{open_:.6f},{high:.6f},{low:.6f},{close:.6f},"
            f"{vol},{prev_close_str},{o_gap:.6f},{c_move:.6f},{v_ratio}"
        )
        prev_close = close

    csv_path = dir_path / f"{symbol}_coded.csv"
    csv_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return csv_path


def _write_minimal_csv(
    dir_path: Path, symbol: str, dates: list[str]
) -> Path:
    """Tiny CSV with just Date / Open / Close (no O_gap etc.).

    Used for planner-only tests where run_predict is never called.
    """
    csv_path = dir_path / f"{symbol}_coded.csv"
    lines = ["Date,Open,High,Low,Close,Volume"] + [
        f"{d},100,101,99,100.5,1000000" for d in dates
    ]
    csv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return csv_path


class _IsolatedDB(unittest.TestCase):
    """Mixin: monkeypatch ps.DB_PATH to a tmp DB and run init_db."""

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._tmp_path = Path(self._tmpdir.name)
        self._old_db_path = ps.DB_PATH
        ps.DB_PATH = self._tmp_path / "test.db"
        ps.init_db()

    def tearDown(self) -> None:
        ps.DB_PATH = self._old_db_path
        self._tmpdir.cleanup()


# ── 1. dry_run is the default and is read-only ──────────────────────────────

class WriterDryRunDefaultTests(_IsolatedDB):
    def test_dry_run_default_is_true(self) -> None:
        _write_minimal_csv(self._tmp_path, "AVGO", ["2024-01-02", "2024-01-03"])
        result = run_contract_replay(coded_data_dir=self._tmp_path)
        self.assertIs(result["dry_run"], True)
        self.assertEqual(result["status"], "ok")

    def test_dry_run_returns_candidate_pairs_from_planner(self) -> None:
        _write_minimal_csv(
            self._tmp_path, "AVGO",
            ["2024-01-02", "2024-01-03", "2024-01-04"],
        )
        result = run_contract_replay(coded_data_dir=self._tmp_path)
        self.assertEqual(result["candidate_pair_count"], 2)
        self.assertEqual(result["would_write_count"], 2)
        self.assertEqual(result["written_prediction_count"], 0)
        self.assertEqual(result["written_outcome_count"], 0)
        self.assertEqual(result["written_records"], [])

    def test_dry_run_notes_explain_no_writes_happened(self) -> None:
        _write_minimal_csv(self._tmp_path, "AVGO", ["2024-01-02", "2024-01-03"])
        result = run_contract_replay(coded_data_dir=self._tmp_path)
        joined = " | ".join(result["notes"])
        self.assertIn("dry_run=True", joined)
        self.assertIn("no prediction", joined)


# ── 2. dry_run does NOT call run_predict / save_prediction / save_outcome ──

class WriterDryRunDoesNotInvokeWritePathTests(_IsolatedDB):
    """The dry-run path must never reach the real write functions."""

    def _csv(self) -> None:
        _write_minimal_csv(
            self._tmp_path, "AVGO",
            ["2024-01-02", "2024-01-03", "2024-01-04"],
        )

    def test_dry_run_does_not_call_run_predict(self) -> None:
        self._csv()
        with patch("services.contract_replay_writer.run_predict") as m:
            run_contract_replay(coded_data_dir=self._tmp_path, dry_run=True)
        self.assertEqual(m.call_count, 0)

    def test_dry_run_does_not_call_save_prediction(self) -> None:
        self._csv()
        with patch("services.contract_replay_writer.save_prediction") as m:
            run_contract_replay(coded_data_dir=self._tmp_path, dry_run=True)
        self.assertEqual(m.call_count, 0)

    def test_dry_run_does_not_call_save_outcome(self) -> None:
        self._csv()
        with patch("services.contract_replay_writer.save_outcome") as m:
            run_contract_replay(coded_data_dir=self._tmp_path, dry_run=True)
        self.assertEqual(m.call_count, 0)


# ── 3. planner failure modes pass through ──────────────────────────────────

class WriterPlannerPassthroughTests(_IsolatedDB):
    def test_planner_missing_data_passes_through(self) -> None:
        nonexistent = self._tmp_path / "no_dir_here"
        result = run_contract_replay(coded_data_dir=nonexistent)
        self.assertEqual(result["status"], "missing_data")
        self.assertEqual(result["candidate_pair_count"], 0)
        self.assertEqual(result["written_prediction_count"], 0)

    def test_planner_insufficient_data_passes_through(self) -> None:
        _write_minimal_csv(self._tmp_path, "AVGO", ["2024-01-02"])
        result = run_contract_replay(coded_data_dir=self._tmp_path)
        self.assertEqual(result["status"], "insufficient_data")
        self.assertEqual(result["candidate_pair_count"], 0)

    def test_planner_error_passes_through(self) -> None:
        _write_minimal_csv(
            self._tmp_path, "AVGO", ["2024-01-02", "2024-01-03"],
        )
        result = run_contract_replay(
            coded_data_dir=self._tmp_path, start_date="not-a-date",
        )
        self.assertEqual(result["status"], "error")


# ── 4. limit handling (writer hard cap is 30) ─────────────────────────────

class WriterLimitTests(_IsolatedDB):
    def _seed_many(self, n: int) -> None:
        dates = _business_day_dates(n)
        _write_minimal_csv(self._tmp_path, "AVGO", dates)

    def test_default_limit_is_30(self) -> None:
        self._seed_many(60)
        result = run_contract_replay(coded_data_dir=self._tmp_path)
        self.assertEqual(result["requested_limit"], 30)
        self.assertEqual(result["candidate_pair_count"], 30)

    def test_limit_clamped_at_hard_cap_30(self) -> None:
        self._seed_many(100)
        result = run_contract_replay(
            coded_data_dir=self._tmp_path, limit=200,
        )
        self.assertEqual(result["requested_limit"], 30)
        self.assertEqual(result["candidate_pair_count"], 30)

    def test_limit_at_cap_passes_through(self) -> None:
        self._seed_many(60)
        result = run_contract_replay(
            coded_data_dir=self._tmp_path, limit=30,
        )
        self.assertEqual(result["requested_limit"], 30)
        self.assertEqual(result["candidate_pair_count"], 30)

    def test_zero_limit_falls_back_to_default(self) -> None:
        self._seed_many(10)
        result = run_contract_replay(coded_data_dir=self._tmp_path, limit=0)
        self.assertEqual(result["requested_limit"], 30)

    def test_non_int_limit_falls_back_to_default(self) -> None:
        self._seed_many(10)
        result = run_contract_replay(
            coded_data_dir=self._tmp_path, limit="abc",  # type: ignore[arg-type]
        )
        self.assertEqual(result["requested_limit"], 30)

    def test_bool_limit_falls_back_to_default(self) -> None:
        self._seed_many(10)
        result = run_contract_replay(
            coded_data_dir=self._tmp_path, limit=True,  # type: ignore[arg-type]
        )
        self.assertEqual(result["requested_limit"], 30)


# ── 5. dry_run=False writes via save_prediction + save_outcome ─────────────

class WriterRealWriteTests(_IsolatedDB):
    """Integration: real run_predict + real save_prediction + real save_outcome."""

    def _seed_realistic(self, n_days: int = 35) -> None:
        _write_realistic_csv(
            self._tmp_path, "AVGO", n_days=n_days, bias_up=True,
        )

    # Helper: a CSV with 35 business days starting 2024-01-02 means
    # the 20th day = 2024-01-29 (the first as_of_date with 20 rows of
    # history). Pairs starting on/after 2024-01-29 are writable.
    _WRITABLE_START = "2024-01-29"

    def _run_writable(self, *, limit: int = 3) -> dict:
        """Run the writer over the writable portion of the seeded CSV."""
        return run_contract_replay(
            coded_data_dir=self._tmp_path,
            start_date=self._WRITABLE_START,
            dry_run=False,
            limit=limit,
        )

    def test_write_mode_status_is_ok_or_partial(self) -> None:
        self._seed_realistic()
        result = self._run_writable(limit=5)
        self.assertIs(result["dry_run"], False)
        self.assertIn(result["status"], {"ok", "partial"})
        self.assertGreaterEqual(result["written_prediction_count"], 1)
        self.assertGreaterEqual(result["written_outcome_count"], 1)
        self.assertEqual(
            result["written_prediction_count"],
            result["written_outcome_count"],
        )

    def test_write_mode_invokes_run_predict(self) -> None:
        self._seed_realistic()
        original = crw.run_predict
        with patch(
            "services.contract_replay_writer.run_predict",
            wraps=original,
        ) as m:
            self._run_writable(limit=3)
        self.assertGreaterEqual(m.call_count, 1)

    def test_write_mode_writes_prediction_log_row(self) -> None:
        self._seed_realistic()
        result = self._run_writable(limit=3)
        self.assertGreaterEqual(len(result["written_records"]), 1)
        first_pid = result["written_records"][0]["prediction_id"]
        row = ps.get_prediction(first_pid)
        self.assertIsNotNone(row)
        assert row is not None
        # contract_payload_json auto-generated by Step 1E side-path.
        self.assertIsNotNone(row["contract_payload_json"])

    def test_write_mode_writes_outcome_log_row(self) -> None:
        self._seed_realistic()
        result = self._run_writable(limit=3)
        first_pid = result["written_records"][0]["prediction_id"]
        outcome = ps.get_outcome_for_prediction(first_pid)
        self.assertIsNotNone(outcome)

    def test_prediction_analysis_date_equals_as_of_date(self) -> None:
        self._seed_realistic()
        result = self._run_writable(limit=3)
        for rec in result["written_records"]:
            row = ps.get_prediction(rec["prediction_id"])
            assert row is not None
            self.assertEqual(row["analysis_date"], rec["as_of_date"])
            self.assertEqual(row["analysis_date"], rec["analysis_date"])

    def test_outcome_captured_at_equals_d_plus_1_t16(self) -> None:
        self._seed_realistic()
        result = self._run_writable(limit=3)
        for rec in result["written_records"]:
            outcome = ps.get_outcome_for_prediction(rec["prediction_id"])
            assert outcome is not None
            expected = f"{rec['prediction_for_date']}T16:00:00"
            self.assertEqual(outcome["captured_at"], expected)
            self.assertEqual(rec["captured_at"], expected)

    def test_snapshot_id_encodes_replay_symbol_d(self) -> None:
        self._seed_realistic()
        result = self._run_writable(limit=3)
        for rec in result["written_records"]:
            row = ps.get_prediction(rec["prediction_id"])
            assert row is not None
            self.assertEqual(
                row["snapshot_id"], f"replay_AVGO_{rec['as_of_date']}",
            )

    def test_direction_correct_uses_compute_helper(self) -> None:
        self._seed_realistic()
        from services.outcome_capture import _compute_direction_correct as real
        with patch(
            "services.contract_replay_writer._compute_direction_correct",
            wraps=real,
        ) as m:
            result = self._run_writable(limit=3)
        self.assertGreaterEqual(m.call_count, len(result["written_records"]))
        for rec in result["written_records"]:
            self.assertIn(rec["direction_correct"], (0, 1, None))


# ── 6. skipping pairs (no half-writes) ─────────────────────────────────────

class WriterSkipBehaviorTests(_IsolatedDB):
    def test_pairs_with_insufficient_history_are_skipped(self) -> None:
        # 25-day CSV: pairs whose as_of_date has < 20 rows of history must
        # be skipped. With 25 days starting 2024-01-02, the 1st pair has
        # 1 row of history (only 2024-01-02 ≤ 2024-01-02). The 20th pair
        # has 20 rows → first writable.
        _write_realistic_csv(self._tmp_path, "AVGO", n_days=25)
        result = run_contract_replay(
            coded_data_dir=self._tmp_path, dry_run=False, limit=10,
        )
        # First several pairs should be skipped insufficient_history.
        self.assertGreaterEqual(len(result["skipped_pairs"]), 1)
        skipped_reasons = {s["reason"] for s in result["skipped_pairs"]}
        self.assertIn("insufficient_history", skipped_reasons)

    def test_skipped_pair_does_not_write_prediction(self) -> None:
        _write_realistic_csv(self._tmp_path, "AVGO", n_days=25)
        result = run_contract_replay(
            coded_data_dir=self._tmp_path, dry_run=False, limit=10,
        )
        # written_prediction_count must equal written_records length;
        # skipped pairs must NOT have prediction_id field.
        self.assertEqual(
            result["written_prediction_count"], len(result["written_records"])
        )
        for s in result["skipped_pairs"]:
            self.assertNotIn("prediction_id", s)

    def test_partial_status_when_some_skip_some_write(self) -> None:
        _write_realistic_csv(self._tmp_path, "AVGO", n_days=25)
        result = run_contract_replay(
            coded_data_dir=self._tmp_path, dry_run=False, limit=10,
        )
        if result["written_prediction_count"] > 0 and result["skipped_pairs"]:
            self.assertEqual(result["status"], "partial")

    def test_pair_with_unparseable_outcome_row_is_skipped(self) -> None:
        # Build a 35-day CSV. Day 21 = 2024-01-30. Pair (Day 20→Day 21)
        # = (2024-01-29 → 2024-01-30) is the first writable pair.
        # Corrupt Day 21's Open so that pair's outcome read fails.
        _write_realistic_csv(self._tmp_path, "AVGO", n_days=35)
        csv_path = self._tmp_path / "AVGO_coded.csv"
        lines = csv_path.read_text(encoding="utf-8").splitlines()
        # Header is line 0; data rows 1..35 → Day 21 is at index 21.
        target_idx = 21
        parts = lines[target_idx].split(",")
        parts[1] = "not-a-number"  # Open column
        lines[target_idx] = ",".join(parts)
        csv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        result = run_contract_replay(
            coded_data_dir=self._tmp_path,
            start_date="2024-01-29",  # Land in the writable range
            dry_run=False,
            limit=3,
        )
        no_outcome_skips = [
            s for s in result["skipped_pairs"]
            if s["reason"] == "no_outcome_data"
        ]
        self.assertGreaterEqual(len(no_outcome_skips), 1)


# ── 7. db_path isolation ───────────────────────────────────────────────────

class WriterDbPathIsolationTests(unittest.TestCase):
    """Without _IsolatedDB mixin: this test verifies that passing
    ``db_path`` overrides ``ps.DB_PATH`` for the duration of writes and
    restores it afterwards."""

    def test_explicit_db_path_isolates_writes(self) -> None:
        with tempfile.TemporaryDirectory() as csv_dir, \
             tempfile.TemporaryDirectory() as db_dir:
            csv_path = Path(csv_dir)
            db_path = Path(db_dir) / "isolated.db"
            _write_realistic_csv(csv_path, "AVGO", n_days=35)

            old_default = ps.DB_PATH
            try:
                # Point default to a different (also tmp) DB so we can
                # confirm writes go to the explicit db_path, not default.
                with tempfile.TemporaryDirectory() as alt_dir:
                    ps.DB_PATH = Path(alt_dir) / "default.db"
                    ps.init_db()  # init the default tmp

                    # Pre-seed the explicit DB so it has the right schema.
                    saved = ps.DB_PATH
                    ps.DB_PATH = db_path
                    ps.init_db()
                    ps.DB_PATH = saved

                    # Sanity: default DB starts empty.
                    with ps._get_conn() as conn:
                        n_default_before = conn.execute(
                            "SELECT COUNT(*) FROM prediction_log"
                        ).fetchone()[0]

                    result = run_contract_replay(
                        coded_data_dir=csv_path,
                        start_date="2024-01-29",  # writable range
                        dry_run=False,
                        limit=3,
                        db_path=db_path,
                    )
                    self.assertGreaterEqual(
                        result["written_prediction_count"], 1,
                    )

                    # After write: default DB unchanged.
                    with ps._get_conn() as conn:
                        n_default_after = conn.execute(
                            "SELECT COUNT(*) FROM prediction_log"
                        ).fetchone()[0]
                    self.assertEqual(n_default_before, n_default_after)

                    # Explicit DB now has rows.
                    saved = ps.DB_PATH
                    ps.DB_PATH = db_path
                    try:
                        with ps._get_conn() as conn:
                            n_explicit = conn.execute(
                                "SELECT COUNT(*) FROM prediction_log"
                            ).fetchone()[0]
                        self.assertGreaterEqual(n_explicit, 1)
                    finally:
                        ps.DB_PATH = saved
            finally:
                ps.DB_PATH = old_default


# ── 8. dependency hygiene ─────────────────────────────────────────────────

class WriterHygieneTests(unittest.TestCase):
    def test_writer_module_does_not_import_yfinance(self) -> None:
        source = Path(crw.__file__).read_text(encoding="utf-8")
        self.assertNotIn("import yfinance", source)
        self.assertNotIn("from yfinance", source)
        self.assertNotIn("yf.Ticker", source)

    def test_writer_module_does_not_import_requests(self) -> None:
        source = Path(crw.__file__).read_text(encoding="utf-8")
        self.assertNotIn("import requests", source)
        self.assertNotIn("from requests", source)


# ── 9. CLI ────────────────────────────────────────────────────────────────

class WriterScriptTests(_IsolatedDB):
    def _run(self, csv_dir: Path, *extra: str) -> dict:
        script = ROOT / "scripts" / "run_contract_replay.py"
        proc = subprocess.run(
            [sys.executable, str(script),
             "--coded-data-dir", str(csv_dir), *extra],
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(proc.stdout)

    def test_cli_default_is_dry_run_no_write(self) -> None:
        _write_minimal_csv(
            self._tmp_path, "AVGO", ["2024-01-02", "2024-01-03"],
        )
        result = self._run(self._tmp_path)
        self.assertIs(result["dry_run"], True)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["written_prediction_count"], 0)

    def test_cli_write_flag_actually_writes(self) -> None:
        # Use a separate tmp DB; pass via --db so CLI subprocess writes
        # to our isolated location.
        with tempfile.TemporaryDirectory() as csv_dir, \
             tempfile.TemporaryDirectory() as db_dir:
            csv_path = Path(csv_dir)
            db_path = Path(db_dir) / "cli_test.db"
            _write_realistic_csv(csv_path, "AVGO", n_days=35)
            # Pre-init the DB schema in this tmp location.
            saved = ps.DB_PATH
            ps.DB_PATH = db_path
            ps.init_db()
            ps.DB_PATH = saved

            script = ROOT / "scripts" / "run_contract_replay.py"
            proc = subprocess.run(
                [sys.executable, str(script),
                 "--coded-data-dir", str(csv_path),
                 "--db", str(db_path),
                 "--start", "2024-01-29",  # land in writable range
                 "--limit", "3",
                 "--write"],
                capture_output=True, text=True, check=True,
            )
            result = json.loads(proc.stdout)
            self.assertIs(result["dry_run"], False)
            self.assertIn(result["status"], {"ok", "partial"})
            self.assertGreaterEqual(result["written_prediction_count"], 1)


if __name__ == "__main__":
    unittest.main()
