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
    step: float | None = None,
) -> Path:
    """Write a coded CSV with full per-row OHLCV + O_gap / C_move / V_ratio.

    The columns mirror the real coded_data/<SYMBOL>_coded.csv subset that
    ``_build_historical_scan_at`` and ``_read_outcome_row`` consume. With
    ``bias_up=True`` close is rising linearly so the scan trend is
    bullish; ``bias_up=False`` flips for variety. ``step`` overrides the
    bias_up default — pass an explicit close-per-day delta to widen the
    AVGO-vs-peer gap for relative-strength tests (Step 2F-4c-3).
    """
    dates = _business_day_dates(n_days)
    rows = ["Date,Open,High,Low,Close,Volume,PrevClose,O_gap,C_move,V_ratio"]
    prev_close: float | None = None
    if step is None:
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


# ── 10. Step 2F-4c-3: peer cutoff helper unit tests ───────────────────────


class ClassifyRelativeStrengthTests(unittest.TestCase):
    def test_unavailable_when_either_input_none(self) -> None:
        self.assertEqual(crw._classify_relative_strength(None, 0.0), "unavailable")
        self.assertEqual(crw._classify_relative_strength(0.0, None), "unavailable")
        self.assertEqual(crw._classify_relative_strength(None, None), "unavailable")

    def test_stronger_when_avgo_beats_peer_by_more_than_margin(self) -> None:
        # Default margin = 0.5 pp. AVGO 2.0%, peer 1.0% → diff 1.0 > 0.5
        self.assertEqual(
            crw._classify_relative_strength(2.0, 1.0), "stronger"
        )

    def test_weaker_when_peer_beats_avgo_by_more_than_margin(self) -> None:
        self.assertEqual(
            crw._classify_relative_strength(1.0, 2.0), "weaker"
        )

    def test_neutral_when_within_margin(self) -> None:
        # |2.4 - 2.0| = 0.4 < 0.5 → neutral
        self.assertEqual(
            crw._classify_relative_strength(2.4, 2.0), "neutral"
        )
        self.assertEqual(
            crw._classify_relative_strength(2.0, 2.4), "neutral"
        )

    def test_neutral_at_exactly_margin_boundary(self) -> None:
        # Match scanner: |diff| must STRICTLY exceed margin (>, not >=).
        self.assertEqual(
            crw._classify_relative_strength(2.5, 2.0), "neutral"
        )

    def test_custom_margin_override(self) -> None:
        # Tighter margin: same diff now classifies stronger.
        self.assertEqual(
            crw._classify_relative_strength(2.4, 2.0, margin_pp=0.3),
            "stronger",
        )


class ComputeNDayReturnAtTests(unittest.TestCase):
    @staticmethod
    def _rows(closes: list[float | None]) -> list[dict]:
        return [
            {"Date": f"2024-02-{i+1:02d}", "Close": c}
            for i, c in enumerate(closes)
        ]

    def test_normal_5d_return_in_percent(self) -> None:
        rows = self._rows([100.0, 101.0, 102.0, 103.0, 104.0, 105.0])
        # idx for 2024-02-06 is 5; close[5] / close[0] - 1 = 5%
        result = crw._compute_nday_return_at(rows, "2024-02-06", n=5)
        assert result is not None
        self.assertAlmostEqual(result, 5.0, places=6)

    def test_returns_none_when_target_idx_lt_n(self) -> None:
        rows = self._rows([100.0, 101.0, 102.0])
        # idx for 2024-02-03 is 2; need 5 prev rows → not enough
        self.assertIsNone(crw._compute_nday_return_at(rows, "2024-02-03", n=5))

    def test_returns_none_when_target_date_missing(self) -> None:
        rows = self._rows([100.0, 101.0, 102.0, 103.0, 104.0, 105.0])
        self.assertIsNone(
            crw._compute_nday_return_at(rows, "2024-02-99", n=5)
        )

    def test_returns_none_when_close_unparseable(self) -> None:
        rows = [
            {"Date": "2024-02-01", "Close": "not-a-number"},
            {"Date": "2024-02-02", "Close": 100.0},
            {"Date": "2024-02-03", "Close": 101.0},
            {"Date": "2024-02-04", "Close": 102.0},
            {"Date": "2024-02-05", "Close": 103.0},
            {"Date": "2024-02-06", "Close": 104.0},
        ]
        self.assertIsNone(
            crw._compute_nday_return_at(rows, "2024-02-06", n=5)
        )

    def test_returns_none_when_prev_close_zero(self) -> None:
        rows = self._rows([0.0, 1.0, 2.0, 3.0, 4.0, 5.0])
        self.assertIsNone(
            crw._compute_nday_return_at(rows, "2024-02-06", n=5)
        )

    def test_returns_none_for_empty_rows(self) -> None:
        self.assertIsNone(crw._compute_nday_return_at([], "2024-02-06", n=5))
        self.assertIsNone(crw._compute_nday_return_at(None, "2024-02-06", n=5))

    def test_returns_none_for_invalid_n(self) -> None:
        rows = self._rows([100.0, 101.0, 102.0])
        self.assertIsNone(
            crw._compute_nday_return_at(rows, "2024-02-03", n=0)
        )
        self.assertIsNone(
            crw._compute_nday_return_at(rows, "2024-02-03", n=-1)
        )


class ComputeSameDayMoveAtTests(unittest.TestCase):
    def test_uses_c_move_when_present(self) -> None:
        rows = [{"Date": "2024-02-01", "C_move": 0.012, "Open": 100, "Close": 105}]
        result = crw._compute_same_day_move_at(rows, "2024-02-01")
        # 0.012 × 100 = 1.2%
        assert result is not None
        self.assertAlmostEqual(result, 1.2, places=6)

    def test_falls_back_to_close_minus_open_when_c_move_missing(self) -> None:
        rows = [{"Date": "2024-02-01", "Open": 100.0, "Close": 102.0}]
        result = crw._compute_same_day_move_at(rows, "2024-02-01")
        # (102 - 100) / 100 × 100 = 2.0%
        assert result is not None
        self.assertAlmostEqual(result, 2.0, places=6)

    def test_falls_back_when_c_move_unparseable(self) -> None:
        rows = [
            {"Date": "2024-02-01", "C_move": "nan", "Open": 100.0, "Close": 99.0},
        ]
        result = crw._compute_same_day_move_at(rows, "2024-02-01")
        assert result is not None
        self.assertAlmostEqual(result, -1.0, places=6)

    def test_returns_none_when_target_date_missing(self) -> None:
        rows = [{"Date": "2024-02-01", "C_move": 0.01, "Open": 100, "Close": 101}]
        self.assertIsNone(crw._compute_same_day_move_at(rows, "2024-02-99"))

    def test_returns_none_when_c_move_missing_and_open_zero(self) -> None:
        rows = [{"Date": "2024-02-01", "Open": 0.0, "Close": 1.0}]
        self.assertIsNone(crw._compute_same_day_move_at(rows, "2024-02-01"))

    def test_returns_none_when_c_move_missing_and_open_close_unparseable(self) -> None:
        rows = [{"Date": "2024-02-01", "Open": "x", "Close": "y"}]
        self.assertIsNone(crw._compute_same_day_move_at(rows, "2024-02-01"))

    def test_returns_none_for_empty_rows(self) -> None:
        self.assertIsNone(crw._compute_same_day_move_at([], "2024-02-01"))
        self.assertIsNone(crw._compute_same_day_move_at(None, "2024-02-01"))


class ComputeRelativeStrengthSummaryAtTests(unittest.TestCase):
    @staticmethod
    def _rows(closes: list[float], c_moves: list[float] | None = None) -> list[dict]:
        rows = []
        for i, c in enumerate(closes):
            row = {"Date": f"2024-02-{i+1:02d}", "Close": c, "Open": c - 0.25}
            if c_moves is not None:
                row["C_move"] = c_moves[i]
            rows.append(row)
        return rows

    def test_keys_are_vs_lowercase_peer_names(self) -> None:
        avgo = self._rows([100, 101, 102, 103, 104, 105])
        peers = {
            "NVDA": self._rows([100, 100.1, 100.2, 100.3, 100.4, 100.5]),
            "SOXX": self._rows([100, 100.1, 100.2, 100.3, 100.4, 100.5]),
            "QQQ": self._rows([100, 100.1, 100.2, 100.3, 100.4, 100.5]),
        }
        summary = crw._compute_relative_strength_summary_at(
            "2024-02-06", avgo, peers, mode="5d"
        )
        self.assertEqual(set(summary.keys()), {"vs_nvda", "vs_soxx", "vs_qqq"})

    def test_5d_avgo_stronger_than_all_peers(self) -> None:
        avgo = self._rows([100, 101, 102, 103, 104, 110.0])  # +10%
        peers = {
            "NVDA": self._rows([100] * 6),  # 0%
            "SOXX": self._rows([100] * 6),
            "QQQ": self._rows([100] * 6),
        }
        summary = crw._compute_relative_strength_summary_at(
            "2024-02-06", avgo, peers, mode="5d"
        )
        self.assertEqual(summary["vs_nvda"], "stronger")
        self.assertEqual(summary["vs_soxx"], "stronger")
        self.assertEqual(summary["vs_qqq"], "stronger")

    def test_5d_avgo_weaker_than_all_peers(self) -> None:
        avgo = self._rows([100] * 6)
        peers = {
            "NVDA": self._rows([100, 101, 102, 103, 104, 110.0]),
            "SOXX": self._rows([100, 101, 102, 103, 104, 110.0]),
            "QQQ": self._rows([100, 101, 102, 103, 104, 110.0]),
        }
        summary = crw._compute_relative_strength_summary_at(
            "2024-02-06", avgo, peers, mode="5d"
        )
        self.assertEqual(summary["vs_nvda"], "weaker")
        self.assertEqual(summary["vs_soxx"], "weaker")
        self.assertEqual(summary["vs_qqq"], "weaker")

    def test_5d_one_peer_missing_degrades_only_that_entry(self) -> None:
        avgo = self._rows([100, 101, 102, 103, 104, 110.0])  # +10%
        peers = {
            "NVDA": self._rows([100] * 6),
            "SOXX": None,  # missing peer
            "QQQ": self._rows([100] * 6),
        }
        summary = crw._compute_relative_strength_summary_at(
            "2024-02-06", avgo, peers, mode="5d"
        )
        self.assertEqual(summary["vs_nvda"], "stronger")
        self.assertEqual(summary["vs_soxx"], "unavailable")
        self.assertEqual(summary["vs_qqq"], "stronger")

    def test_same_day_mode_reads_c_move(self) -> None:
        avgo = self._rows(
            [100, 101, 102, 103, 104, 105],
            c_moves=[0.0, 0.0, 0.0, 0.0, 0.0, 0.02],  # +2%
        )
        peers = {
            "NVDA": self._rows(
                [100, 101, 102, 103, 104, 105],
                c_moves=[0.0, 0.0, 0.0, 0.0, 0.0, 0.001],  # +0.1%
            ),
            "SOXX": self._rows(
                [100, 101, 102, 103, 104, 105],
                c_moves=[0.0, 0.0, 0.0, 0.0, 0.0, 0.001],
            ),
            "QQQ": self._rows(
                [100, 101, 102, 103, 104, 105],
                c_moves=[0.0, 0.0, 0.0, 0.0, 0.0, 0.001],
            ),
        }
        summary = crw._compute_relative_strength_summary_at(
            "2024-02-06", avgo, peers, mode="same_day"
        )
        self.assertEqual(summary["vs_nvda"], "stronger")
        self.assertEqual(summary["vs_soxx"], "stronger")
        self.assertEqual(summary["vs_qqq"], "stronger")

    def test_unknown_mode_returns_all_unavailable(self) -> None:
        summary = crw._compute_relative_strength_summary_at(
            "2024-02-06", [], {}, mode="bogus",
        )
        self.assertEqual(
            summary,
            {"vs_nvda": "unavailable", "vs_soxx": "unavailable", "vs_qqq": "unavailable"},
        )

    def test_none_peer_map_yields_all_unavailable(self) -> None:
        avgo = self._rows([100, 101, 102, 103, 104, 105])
        summary = crw._compute_relative_strength_summary_at(
            "2024-02-06", avgo, None, mode="5d"
        )
        self.assertEqual(
            summary,
            {"vs_nvda": "unavailable", "vs_soxx": "unavailable", "vs_qqq": "unavailable"},
        )

    def test_lowercase_peer_keys_also_accepted(self) -> None:
        avgo = self._rows([100, 101, 102, 103, 104, 110.0])
        peers = {
            "nvda": self._rows([100] * 6),
            "soxx": self._rows([100] * 6),
            "qqq": self._rows([100] * 6),
        }
        summary = crw._compute_relative_strength_summary_at(
            "2024-02-06", avgo, peers, mode="5d"
        )
        self.assertEqual(summary["vs_nvda"], "stronger")


# ── 11. Step 2F-4c-3: build scan now embeds three-key rs summaries ────────


class BuildHistoricalScanWithPeerCutoffTests(unittest.TestCase):
    """The scan_result returned by _build_historical_scan_at must always
    expose all three vs_* keys in both rs summaries (not empty dict).
    Backwards-compat: when peer_rows_map is None, all three keys come
    back ``"unavailable"`` (no fabricated neutrals)."""

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._tmp_path = Path(self._tmpdir.name)
        _write_realistic_csv(self._tmp_path, "AVGO", n_days=35)
        self.avgo_rows = crw._read_symbol_ohlcv("AVGO", self._tmp_path)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_scan_has_three_vs_keys_in_5d_summary_when_no_peer_map(self) -> None:
        scan = crw._build_historical_scan_at("AVGO", "2024-01-29", self.avgo_rows)
        assert scan is not None
        rs_5d = scan["relative_strength_summary"]
        self.assertEqual(set(rs_5d.keys()), {"vs_nvda", "vs_soxx", "vs_qqq"})
        # No peer rows → unavailable across the board.
        for value in rs_5d.values():
            self.assertEqual(value, "unavailable")

    def test_scan_has_three_vs_keys_in_same_day_summary_when_no_peer_map(self) -> None:
        scan = crw._build_historical_scan_at("AVGO", "2024-01-29", self.avgo_rows)
        assert scan is not None
        rs_day = scan["relative_strength_same_day_summary"]
        self.assertEqual(set(rs_day.keys()), {"vs_nvda", "vs_soxx", "vs_qqq"})

    def test_scan_rs_summaries_populated_when_peers_provided(self) -> None:
        # Generate AVGO + three peers; AVGO rises faster → all stronger.
        _write_realistic_csv(self._tmp_path, "NVDA", n_days=35, bias_up=False)
        _write_realistic_csv(self._tmp_path, "SOXX", n_days=35, bias_up=False)
        _write_realistic_csv(self._tmp_path, "QQQ", n_days=35, bias_up=False)
        peer_rows_map = {
            "NVDA": crw._read_peer_ohlcv("NVDA", self._tmp_path),
            "SOXX": crw._read_peer_ohlcv("SOXX", self._tmp_path),
            "QQQ": crw._read_peer_ohlcv("QQQ", self._tmp_path),
        }
        scan = crw._build_historical_scan_at(
            "AVGO", "2024-01-29", self.avgo_rows, peer_rows_map=peer_rows_map,
        )
        assert scan is not None
        rs_5d = scan["relative_strength_summary"]
        self.assertEqual(set(rs_5d.keys()), {"vs_nvda", "vs_soxx", "vs_qqq"})
        # AVGO bias_up=True (step +0.5), peers bias_up=False (step -0.3) →
        # AVGO 5d return clearly higher.
        self.assertEqual(rs_5d["vs_nvda"], "stronger")
        self.assertEqual(rs_5d["vs_soxx"], "stronger")
        self.assertEqual(rs_5d["vs_qqq"], "stronger")


# ── 12. Step 2F-4c-3: dry_run still does NOT read peer CSVs ────────────────


class WriterDryRunDoesNotReadPeerCsvTests(_IsolatedDB):
    """The dry-run path returns immediately after the planner; it never
    reaches _read_peer_ohlcv / _read_symbol_ohlcv for the write side."""

    def _csv(self) -> None:
        _write_minimal_csv(
            self._tmp_path, "AVGO",
            ["2024-01-02", "2024-01-03", "2024-01-04"],
        )

    def test_dry_run_does_not_call_read_peer_ohlcv(self) -> None:
        self._csv()
        with patch("services.contract_replay_writer._read_peer_ohlcv") as m:
            run_contract_replay(coded_data_dir=self._tmp_path, dry_run=True)
        self.assertEqual(m.call_count, 0)


# ── 13. Step 2F-4c-3: real-write end-to-end with peer CSVs present ────────


class WriterRealWriteWithPeerCsvTests(_IsolatedDB):
    """Generate AVGO + NVDA + SOXX + QQQ tmp CSVs, run --write, and inspect
    the contract_payload_json that landed in the tmp DB."""

    _WRITABLE_START = "2024-01-29"

    # Step 2F-4c-3 semantic note for these fixtures:
    #   ``vs_<peer>="stronger"`` means AVGO outperforms peer (AVGO step >
    #   peer step). Under bullish primary, "stronger" → confirm.
    #   ``vs_<peer>="weaker"``   means AVGO underperforms peer (peer step >
    #   AVGO step). Under bullish primary, "weaker" → oppose.

    def _seed_avgo_underperforms_peers(self) -> None:
        # AVGO mildly bullish (step 0.5 keeps primary bias bullish) but
        # peers grow much faster (step 2.5) → AVGO 5d return < peer 5d
        # return by > 0.5 pp → vs_<peer>="weaker" → bullish primary
        # treats this as "oppose" → oppose_count high.
        _write_realistic_csv(self._tmp_path, "AVGO", n_days=35, step=0.5)
        _write_realistic_csv(self._tmp_path, "NVDA", n_days=35, step=2.5)
        _write_realistic_csv(self._tmp_path, "SOXX", n_days=35, step=2.5)
        _write_realistic_csv(self._tmp_path, "QQQ", n_days=35, step=2.5)

    def _seed_avgo_outperforms_peers(self) -> None:
        # AVGO strongly bullish (step 2.5) and peers nearly flat (step
        # 0.05) → AVGO 5d return > peer 5d return by > 0.5 pp →
        # vs_<peer>="stronger" → bullish primary treats this as
        # "confirm" → confirm_count high.
        _write_realistic_csv(self._tmp_path, "AVGO", n_days=35, step=2.5)
        _write_realistic_csv(self._tmp_path, "NVDA", n_days=35, step=0.05)
        _write_realistic_csv(self._tmp_path, "SOXX", n_days=35, step=0.05)
        _write_realistic_csv(self._tmp_path, "QQQ", n_days=35, step=0.05)

    def _written_contract(self, prediction_id: str) -> dict:
        row = ps.get_prediction(prediction_id)
        assert row is not None
        payload_s = row["contract_payload_json"]
        self.assertIsNotNone(payload_s)
        return json.loads(payload_s)

    def test_peer_signals_are_not_all_unknown(self) -> None:
        self._seed_avgo_underperforms_peers()
        result = run_contract_replay(
            coded_data_dir=self._tmp_path,
            start_date=self._WRITABLE_START,
            dry_run=False,
            limit=3,
        )
        self.assertGreaterEqual(result["written_prediction_count"], 1)
        first = result["written_records"][0]
        payload = self._written_contract(first["prediction_id"])
        peer = payload["peer_confirmation_adjustment"]
        self.assertNotEqual(peer["nvda_signal"], "unknown")
        self.assertNotEqual(peer["soxx_signal"], "unknown")
        self.assertNotEqual(peer["qqq_signal"], "unknown")

    def test_peer_alignment_is_all_weaken_when_peers_outperform(self) -> None:
        self._seed_avgo_underperforms_peers()
        result = run_contract_replay(
            coded_data_dir=self._tmp_path,
            start_date=self._WRITABLE_START,
            dry_run=False,
            limit=3,
        )
        self.assertGreaterEqual(result["written_prediction_count"], 1)
        first = result["written_records"][0]
        payload = self._written_contract(first["prediction_id"])
        peer = payload["peer_confirmation_adjustment"]
        # 3 oppose under bullish primary → all_weaken; not "insufficient".
        self.assertEqual(peer["peer_alignment"], "all_weaken")

    def test_oppose_count_positive_when_peers_outperform(self) -> None:
        self._seed_avgo_underperforms_peers()
        result = run_contract_replay(
            coded_data_dir=self._tmp_path,
            start_date=self._WRITABLE_START,
            dry_run=False,
            limit=3,
        )
        first = result["written_records"][0]
        payload = self._written_contract(first["prediction_id"])
        cs_extras = payload["confidence_system"]["extras"]
        self.assertGreater(cs_extras["peer_oppose_count"], 0)

    def test_confirm_count_positive_when_avgo_outperforms(self) -> None:
        self._seed_avgo_outperforms_peers()
        result = run_contract_replay(
            coded_data_dir=self._tmp_path,
            start_date=self._WRITABLE_START,
            dry_run=False,
            limit=3,
        )
        first = result["written_records"][0]
        payload = self._written_contract(first["prediction_id"])
        cs_extras = payload["confidence_system"]["extras"]
        # AVGO outperforms peers + bullish primary → 3 confirm.
        self.assertGreater(cs_extras["peer_confirm_count"], 0)

    def test_peer_alignment_is_all_reinforce_when_avgo_outperforms(self) -> None:
        self._seed_avgo_outperforms_peers()
        result = run_contract_replay(
            coded_data_dir=self._tmp_path,
            start_date=self._WRITABLE_START,
            dry_run=False,
            limit=3,
        )
        first = result["written_records"][0]
        payload = self._written_contract(first["prediction_id"])
        peer = payload["peer_confirmation_adjustment"]
        self.assertEqual(peer["peer_alignment"], "all_reinforce")

    def test_peer_path_risk_direction_higher_when_peers_outperform(self) -> None:
        self._seed_avgo_underperforms_peers()
        result = run_contract_replay(
            coded_data_dir=self._tmp_path,
            start_date=self._WRITABLE_START,
            dry_run=False,
            limit=3,
        )
        first = result["written_records"][0]
        payload = self._written_contract(first["prediction_id"])
        es_extras = payload["exclusion_system"]["extras"]
        # 3 oppose under bullish primary → adjustment_direction "weaken"
        # → path_risk_direction "higher".
        self.assertEqual(es_extras["peer_path_risk_direction"], "higher")


# ── 14. Step 2F-4c-3: missing peer CSV degrades to unavailable ────────────


class WriterMissingPeerCsvDegradesTests(_IsolatedDB):
    """Real-write succeeds when peer CSVs are missing; signals come back
    unknown / insufficient (the 4c-2 baseline shape) without crashing."""

    def test_real_write_succeeds_with_no_peer_csvs(self) -> None:
        # Only AVGO; the three peer CSVs are absent from coded_data_dir.
        _write_realistic_csv(self._tmp_path, "AVGO", n_days=35, bias_up=True)
        result = run_contract_replay(
            coded_data_dir=self._tmp_path,
            start_date="2024-01-29",
            dry_run=False,
            limit=3,
        )
        self.assertGreaterEqual(result["written_prediction_count"], 1)
        first = result["written_records"][0]
        row = ps.get_prediction(first["prediction_id"])
        assert row is not None
        payload = json.loads(row["contract_payload_json"])
        peer = payload["peer_confirmation_adjustment"]
        self.assertEqual(peer["nvda_signal"], "unknown")
        self.assertEqual(peer["soxx_signal"], "unknown")
        self.assertEqual(peer["qqq_signal"], "unknown")
        self.assertEqual(peer["peer_alignment"], "insufficient")

    def test_one_peer_missing_does_not_break_others(self) -> None:
        # AVGO mildly bullish, two present peers grow much faster → those
        # peers vote oppose under bullish primary → signal "weaken".
        # SOXX deliberately absent → its signal degrades to "unknown".
        _write_realistic_csv(self._tmp_path, "AVGO", n_days=35, step=0.5)
        _write_realistic_csv(self._tmp_path, "NVDA", n_days=35, step=2.5)
        # SOXX deliberately absent.
        _write_realistic_csv(self._tmp_path, "QQQ", n_days=35, step=2.5)
        result = run_contract_replay(
            coded_data_dir=self._tmp_path,
            start_date="2024-01-29",
            dry_run=False,
            limit=3,
        )
        self.assertGreaterEqual(result["written_prediction_count"], 1)
        first = result["written_records"][0]
        row = ps.get_prediction(first["prediction_id"])
        assert row is not None
        payload = json.loads(row["contract_payload_json"])
        peer = payload["peer_confirmation_adjustment"]
        self.assertEqual(peer["nvda_signal"], "weaken")
        self.assertEqual(peer["soxx_signal"], "unknown")
        self.assertEqual(peer["qqq_signal"], "weaken")


# ── 15. Step 2F-4c-3: hard cap and pandas hygiene unchanged ───────────────


class WriterHardCapAndPandasHygieneTests(unittest.TestCase):
    def test_limit_hard_cap_constant_remains_30(self) -> None:
        self.assertEqual(crw._LIMIT_HARD_CAP, 30)

    def test_writer_module_does_not_import_pandas(self) -> None:
        source = Path(crw.__file__).read_text(encoding="utf-8")
        self.assertNotIn("import pandas", source)
        self.assertNotIn("from pandas", source)


# ── 16. Step 2F-4d-2-prereq-1: duplicate guard ───────────────────────────


class SnapshotIdExistsHelperTests(unittest.TestCase):
    """Direct unit tests for ``_snapshot_id_exists`` — the read-only
    SELECT-by-snapshot_id helper that gates the duplicate guard."""

    def test_returns_false_when_table_missing(self) -> None:
        # Fresh tmp DB file (created on connect, but no init_db) has no
        # prediction_log table — helper must swallow OperationalError.
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "fresh.db"
            self.assertFalse(
                crw._snapshot_id_exists("replay_AVGO_2024-01-29", db_path)
            )

    def test_returns_false_when_snapshot_id_not_in_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "init.db"
            saved = ps.DB_PATH
            ps.DB_PATH = db_path
            try:
                ps.init_db()
            finally:
                ps.DB_PATH = saved
            self.assertFalse(
                crw._snapshot_id_exists("replay_AVGO_2024-01-29", db_path)
            )

    def test_returns_true_when_snapshot_id_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "seeded.db"
            saved = ps.DB_PATH
            ps.DB_PATH = db_path
            try:
                ps.init_db()
                # Seed via save_prediction so we go through the same
                # column shape the writer would later use.
                ps.save_prediction(
                    symbol="AVGO",
                    prediction_for_date="2024-01-30",
                    scan_result={"symbol": "AVGO"},
                    research_result=None,
                    predict_result={"final_bias": "neutral"},
                    snapshot_id="replay_AVGO_2024-01-29",
                    contract_payload=None,
                )
            finally:
                ps.DB_PATH = saved
            self.assertTrue(
                crw._snapshot_id_exists("replay_AVGO_2024-01-29", db_path)
            )

    def test_falls_back_to_ps_db_path_when_arg_is_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "default.db"
            saved = ps.DB_PATH
            ps.DB_PATH = db_path
            try:
                ps.init_db()
                ps.save_prediction(
                    symbol="AVGO",
                    prediction_for_date="2024-01-30",
                    scan_result={"symbol": "AVGO"},
                    research_result=None,
                    predict_result={"final_bias": "neutral"},
                    snapshot_id="replay_AVGO_2024-01-29",
                    contract_payload=None,
                )
                # No db_path arg → uses ps.DB_PATH (currently the seeded one).
                self.assertTrue(
                    crw._snapshot_id_exists("replay_AVGO_2024-01-29")
                )
                self.assertFalse(
                    crw._snapshot_id_exists("replay_AVGO_2099-01-01")
                )
            finally:
                ps.DB_PATH = saved


class WriterDuplicateGuardSkipsTests(_IsolatedDB):
    """When a candidate pair's snapshot_id already exists, the writer
    must NOT call run_predict / save_prediction / save_outcome for that
    pair, and the pair appears in skipped_pairs with the documented reason."""

    def _seed(self, n_days: int = 35) -> None:
        _write_realistic_csv(
            self._tmp_path, "AVGO", n_days=n_days, bias_up=True,
        )

    def _preinsert(self, snapshot_id: str) -> None:
        ps.save_prediction(
            symbol="AVGO",
            prediction_for_date="2024-01-30",
            scan_result={"symbol": "AVGO"},
            research_result=None,
            predict_result={"final_bias": "neutral"},
            snapshot_id=snapshot_id,
            contract_payload=None,
        )

    def test_existing_snapshot_lands_in_skipped_pairs(self) -> None:
        self._seed()
        self._preinsert("replay_AVGO_2024-01-29")
        result = run_contract_replay(
            coded_data_dir=self._tmp_path,
            start_date="2024-01-29",
            dry_run=False,
            limit=3,
        )
        skips = [
            s for s in result["skipped_pairs"]
            if s["reason"] == "snapshot_id_already_exists"
        ]
        self.assertEqual(len(skips), 1)
        self.assertEqual(skips[0]["snapshot_id"], "replay_AVGO_2024-01-29")
        self.assertEqual(skips[0]["as_of_date"], "2024-01-29")
        # No prediction_id field on a duplicate-skip pair.
        self.assertNotIn("prediction_id", skips[0])

    def test_existing_snapshot_does_not_call_run_predict(self) -> None:
        self._seed()
        self._preinsert("replay_AVGO_2024-01-29")
        # Patch run_predict to count invocations during a 1-pair batch.
        with patch(
            "services.contract_replay_writer.run_predict"
        ) as m_predict:
            run_contract_replay(
                coded_data_dir=self._tmp_path,
                start_date="2024-01-29",
                dry_run=False,
                limit=1,  # only the duplicate pair
            )
        self.assertEqual(m_predict.call_count, 0)

    def test_existing_snapshot_does_not_call_save_prediction(self) -> None:
        self._seed()
        self._preinsert("replay_AVGO_2024-01-29")
        with patch(
            "services.contract_replay_writer.save_prediction"
        ) as m_save:
            run_contract_replay(
                coded_data_dir=self._tmp_path,
                start_date="2024-01-29",
                dry_run=False,
                limit=1,
            )
        self.assertEqual(m_save.call_count, 0)

    def test_existing_snapshot_does_not_call_save_outcome(self) -> None:
        self._seed()
        self._preinsert("replay_AVGO_2024-01-29")
        with patch(
            "services.contract_replay_writer.save_outcome"
        ) as m_save:
            run_contract_replay(
                coded_data_dir=self._tmp_path,
                start_date="2024-01-29",
                dry_run=False,
                limit=1,
            )
        self.assertEqual(m_save.call_count, 0)

    def test_no_prediction_row_added_when_all_duplicates(self) -> None:
        self._seed()
        # Pre-seed the FIRST writable pair only.
        self._preinsert("replay_AVGO_2024-01-29")
        with ps._get_conn() as conn:
            before = conn.execute(
                "SELECT COUNT(*) FROM prediction_log"
            ).fetchone()[0]
        result = run_contract_replay(
            coded_data_dir=self._tmp_path,
            start_date="2024-01-29",
            dry_run=False,
            limit=1,
        )
        with ps._get_conn() as conn:
            after = conn.execute(
                "SELECT COUNT(*) FROM prediction_log"
            ).fetchone()[0]
        self.assertEqual(after - before, 0)
        self.assertEqual(result["written_prediction_count"], 0)
        self.assertEqual(result["written_outcome_count"], 0)


class WriterDuplicateGuardNonDuplicatePathTests(_IsolatedDB):
    """When no snapshot_id pre-exists, the duplicate guard must not
    block the normal write path."""

    def test_clean_db_writes_normally(self) -> None:
        _write_realistic_csv(
            self._tmp_path, "AVGO", n_days=35, bias_up=True,
        )
        result = run_contract_replay(
            coded_data_dir=self._tmp_path,
            start_date="2024-01-29",
            dry_run=False,
            limit=3,
        )
        self.assertGreaterEqual(result["written_prediction_count"], 1)
        # No duplicate-skip reason should appear.
        dup = [
            s for s in result["skipped_pairs"]
            if s["reason"] == "snapshot_id_already_exists"
        ]
        self.assertEqual(dup, [])


class WriterDuplicateGuardPartialMixTests(_IsolatedDB):
    """Some pre-existing snapshot_ids + some new pairs → status=partial,
    duplicates skipped, fresh pairs written."""

    def test_partial_status_when_some_dup_some_write(self) -> None:
        _write_realistic_csv(
            self._tmp_path, "AVGO", n_days=35, bias_up=True,
        )
        # Pre-seed only the first writable pair.
        ps.save_prediction(
            symbol="AVGO",
            prediction_for_date="2024-01-30",
            scan_result={"symbol": "AVGO"},
            research_result=None,
            predict_result={"final_bias": "neutral"},
            snapshot_id="replay_AVGO_2024-01-29",
            contract_payload=None,
        )
        result = run_contract_replay(
            coded_data_dir=self._tmp_path,
            start_date="2024-01-29",
            dry_run=False,
            limit=3,
        )
        # Expect: 1 dup skip, 2 written.
        dup_skips = [
            s for s in result["skipped_pairs"]
            if s["reason"] == "snapshot_id_already_exists"
        ]
        self.assertEqual(len(dup_skips), 1)
        self.assertEqual(result["written_prediction_count"], 2)
        self.assertEqual(result["status"], "partial")


class WriterDuplicateGuardDryRunIsReadOnlyTests(_IsolatedDB):
    """``dry_run=True`` must not invoke the duplicate guard — the
    dry-run path stays purely planner-driven, never touches the DB."""

    def test_dry_run_does_not_call_snapshot_id_exists(self) -> None:
        _write_realistic_csv(
            self._tmp_path, "AVGO", n_days=35, bias_up=True,
        )
        with patch(
            "services.contract_replay_writer._snapshot_id_exists"
        ) as m_exists:
            run_contract_replay(
                coded_data_dir=self._tmp_path,
                start_date="2024-01-29",
                dry_run=True,
                limit=3,
            )
        self.assertEqual(m_exists.call_count, 0)


class WriterDuplicateGuardExplicitDbPathTests(unittest.TestCase):
    """When ``db_path`` is provided, the duplicate guard must read from
    THAT DB — not from ``ps.DB_PATH`` (which may be unrelated)."""

    def test_duplicate_check_routes_to_explicit_db_path(self) -> None:
        with tempfile.TemporaryDirectory() as csv_dir, \
             tempfile.TemporaryDirectory() as db_dir, \
             tempfile.TemporaryDirectory() as alt_dir:
            csv_path = Path(csv_dir)
            db_path = Path(db_dir) / "writer.db"
            alt_path = Path(alt_dir) / "default.db"

            _write_realistic_csv(csv_path, "AVGO", n_days=35, bias_up=True)

            old_default = ps.DB_PATH
            try:
                # Init both DBs so they have prediction_log schema.
                ps.DB_PATH = alt_path
                ps.init_db()

                ps.DB_PATH = db_path
                ps.init_db()
                # Pre-seed a duplicate ONLY in the explicit db_path DB.
                ps.save_prediction(
                    symbol="AVGO",
                    prediction_for_date="2024-01-30",
                    scan_result={"symbol": "AVGO"},
                    research_result=None,
                    predict_result={"final_bias": "neutral"},
                    snapshot_id="replay_AVGO_2024-01-29",
                    contract_payload=None,
                )

                # Switch ps.DB_PATH to the alt (clean) DB, then call
                # run_contract_replay with explicit db_path=writer DB.
                ps.DB_PATH = alt_path

                result = run_contract_replay(
                    coded_data_dir=csv_path,
                    start_date="2024-01-29",
                    dry_run=False,
                    limit=1,
                    db_path=db_path,
                )
                # Duplicate seeded in db_path; alt is clean. The guard
                # must consult db_path (not alt) and skip the pair.
                dup_skips = [
                    s for s in result["skipped_pairs"]
                    if s["reason"] == "snapshot_id_already_exists"
                ]
                self.assertEqual(len(dup_skips), 1)
                self.assertEqual(result["written_prediction_count"], 0)

                # alt DB must remain empty (no leakage).
                ps.DB_PATH = alt_path
                with ps._get_conn() as conn:
                    n_alt = conn.execute(
                        "SELECT COUNT(*) FROM prediction_log"
                    ).fetchone()[0]
                self.assertEqual(n_alt, 0)
            finally:
                ps.DB_PATH = old_default


class WriterDuplicateGuardCliTests(_IsolatedDB):
    """CLI smoke: ``--write`` against a DB with a pre-existing snapshot
    must report the duplicate as skipped via stdout JSON."""

    def test_cli_write_reports_duplicate_skip(self) -> None:
        with tempfile.TemporaryDirectory() as csv_dir, \
             tempfile.TemporaryDirectory() as db_dir:
            csv_path = Path(csv_dir)
            db_path = Path(db_dir) / "cli_dup.db"
            _write_realistic_csv(csv_path, "AVGO", n_days=35, bias_up=True)

            saved = ps.DB_PATH
            ps.DB_PATH = db_path
            try:
                ps.init_db()
                ps.save_prediction(
                    symbol="AVGO",
                    prediction_for_date="2024-01-30",
                    scan_result={"symbol": "AVGO"},
                    research_result=None,
                    predict_result={"final_bias": "neutral"},
                    snapshot_id="replay_AVGO_2024-01-29",
                    contract_payload=None,
                )
            finally:
                ps.DB_PATH = saved

            script = ROOT / "scripts" / "run_contract_replay.py"
            proc = subprocess.run(
                [sys.executable, str(script),
                 "--coded-data-dir", str(csv_path),
                 "--db", str(db_path),
                 "--start", "2024-01-29",
                 "--limit", "1",
                 "--write"],
                capture_output=True, text=True, check=True,
            )
            result = json.loads(proc.stdout)
            self.assertIs(result["dry_run"], False)
            dup_skips = [
                s for s in result["skipped_pairs"]
                if s["reason"] == "snapshot_id_already_exists"
            ]
            self.assertEqual(len(dup_skips), 1)
            self.assertEqual(result["written_prediction_count"], 0)
            # All-skip case → status=partial (writer's existing rule).
            self.assertEqual(result["status"], "partial")


if __name__ == "__main__":
    unittest.main()
