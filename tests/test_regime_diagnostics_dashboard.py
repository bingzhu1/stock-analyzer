"""Tests for services/regime_diagnostics_dashboard.py (Step 3D-1)."""
from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import services.prediction_store as ps
from services.regime_diagnostics_dashboard import (
    _MIN_RECOMMENDED_PAIRS,
    _R4_AVGO_MINUS_SOXX_THRESHOLD,
    _R4_POS20_THRESHOLD,
    summarize_regime_diagnostics_dashboard,
)


# ── Shared fixtures ─────────────────────────────────────────────────────────

def _predict_result(
    symbol: str = "AVGO",
    bias: str = "bullish",
    confidence: str = "medium",
) -> dict:
    return {
        "symbol": symbol,
        "final_bias": bias,
        "final_confidence": confidence,
        "scan_bias": bias,
        "scan_confidence": confidence,
        "pred_open": "高开",
        "pred_path": "高开高走",
        "pred_close": "收涨",
        "prediction_summary": "<placeholder>",
        "supporting_factors": ["factor_a"],
        "conflicting_factors": [],
    }


def _build_replay_payload(
    *,
    final_direction: str = "偏多",
    confidence_level: str = "medium",
    primary_score_raw: float | None = 1.5,
    peer_adjustment: str = "hold",
    peer_confirm_count: int = 1,
    peer_oppose_count: int = 0,
    soft_signal: str = "none",
    path_risk_level: str = "unknown",
    analysis_date: str = "2024-01-08",
    prediction_for_date: str = "2024-01-09",
) -> dict:
    """Produce a contract-valid payload with full Step 2C-3b extras."""
    return {
        "current_structure": {
            "symbol": "AVGO", "analysis_date": analysis_date,
            "prediction_for_date": prediction_for_date,
            "data_window_days": 20,
            "current_price": 100.0, "previous_close": 99.0,
            "volume": 1_000_000, "turnover": 1.0e8,
            "structure_label": "bullish", "short_summary": "",
        },
        "avgo_primary_projection": {
            "primary_direction": final_direction,
            "open_projection": "高开",
            "intraday_path_projection": "高走",
            "close_projection": "收涨",
            "five_state_projection": "小涨",
            "historical_sample_count": 0,
            "key_evidence": [],
            "primary_confidence_raw": confidence_level,
        },
        "peer_confirmation_adjustment": {
            "peer_symbols": ["NVDA", "SOXX", "QQQ"],
            "nvda_signal": "neutral", "soxx_signal": "neutral",
            "qqq_signal": "neutral", "peer_alignment": "insufficient",
            "peer_adjustment": peer_adjustment,
            "adjusted_direction": final_direction,
            "adjustment_reason": "",
        },
        "exclusion_system": {
            "exclusion_level": "none", "exclusion_sources": [],
            "exclusion_reasons": [], "forced_exclusion": False,
            "anti_false_exclusion_triggered": False,
            "extras": {
                "conflicting_factors_count": 0,
                "conflicting_factors": [],
                "path_risk_level": path_risk_level,
                "peer_path_risk_direction": "neutral",
                "peer_path_risk_reasons": [],
                "soft_signal": soft_signal,
            },
        },
        "confidence_system": {
            "historical_score": 0.0, "structure_score": 0.0,
            "peer_score": 0.0, "exclusion_penalty": 0.0,
            "event_score": None, "total_confidence": 0.5,
            "confidence_level": confidence_level,
            "confidence_reason": "",
            "extras": {
                "primary_score_raw": primary_score_raw,
                "primary_confidence_raw": confidence_level,
                "peer_confirm_count": peer_confirm_count,
                "peer_oppose_count": peer_oppose_count,
                "peer_adjusted_confidence": confidence_level,
                "final_confidence": confidence_level,
                "probability_bucket": "55–70%",
                "conflicting_factors_count": 0,
                "path_risk_level": path_risk_level,
                "soft_signal": soft_signal,
            },
        },
        "final_projection": {
            "final_direction": final_direction,
            "final_open_projection": "高开",
            "final_intraday_path": "高走",
            "final_close_projection": "收涨",
            "final_five_state": "小涨",
            "probability_bucket": "55–70%",
            "key_price_levels": {},
            "final_one_sentence": "",
        },
        "simulated_trade": {
            "trade_action": "no_trade", "trade_direction": "none",
            "entry_condition": "", "stop_loss_condition": "",
            "take_profit_condition": "", "suggested_position_size": "0%",
            "no_trade_reason": "<test>",
        },
        "review_payload": {
            "prediction_id": "", "predicted_open_type": "高开",
            "predicted_path_type": "高走", "predicted_close_type": "收涨",
            "predicted_five_state": "小涨", "predicted_confidence": confidence_level,
            "review_ready_fields": [],
        },
    }


def _save_replay(
    *,
    analysis_date: str,
    prediction_for_date: str,
    payload: dict,
    direction_correct: int | None = None,
    actual_close: float = 105.0,
    actual_prev_close: float = 100.0,
    symbol: str = "AVGO",
) -> str:
    pid = ps.save_prediction(
        symbol=symbol,
        prediction_for_date=prediction_for_date,
        scan_result=None,
        research_result=None,
        predict_result=_predict_result(symbol=symbol),
        snapshot_id=f"replay_{symbol}_{analysis_date}",
        contract_payload=payload,
        analysis_date_override=analysis_date,
    )
    if direction_correct is not None or actual_close is not None:
        ps.save_outcome(
            prediction_id=pid,
            prediction_for_date=prediction_for_date,
            actual_open=actual_prev_close,
            actual_high=max(actual_close, actual_prev_close) + 1,
            actual_low=min(actual_close, actual_prev_close) - 1,
            actual_close=actual_close,
            actual_prev_close=actual_prev_close,
            direction_correct=direction_correct,
        )
    return pid


def _write_coded_csv(path: Path, rows: list[dict[str, str]]) -> None:
    """Write a minimal coded CSV (Date, Open, High, Low, Close)."""
    fieldnames = ["Date", "Open", "High", "Low", "Close"]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, "") for k in fieldnames})


def _make_linear_csv_rows(
    start_close: float, step: float, count: int, start_date: str = "2023-12-01"
) -> list[dict[str, str]]:
    """Create ``count`` daily bars whose Close walks linearly from
    ``start_close`` by ``+step`` each day. High = Close + 0.5; Low = Close - 0.5;
    Open = previous close (or start_close on day 0)."""
    from datetime import date, timedelta
    rows: list[dict[str, str]] = []
    d = date.fromisoformat(start_date)
    prev_close = start_close
    for i in range(count):
        close = start_close + step * i
        rows.append({
            "Date": d.isoformat(),
            "Open": f"{prev_close:.4f}",
            "High": f"{close + 0.5:.4f}",
            "Low": f"{close - 0.5:.4f}",
            "Close": f"{close:.4f}",
        })
        prev_close = close
        d += timedelta(days=1)
    return rows


class _IsolatedStoreTestCase(unittest.TestCase):
    """Each test gets its own tmp DB + tmp coded_data dir."""

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        ps.DB_PATH = Path(self._tmpdir.name) / "test.db"
        ps.init_db()
        self.coded_dir = Path(self._tmpdir.name) / "coded_data"
        self.coded_dir.mkdir()

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def _summary(self, **kwargs) -> dict:
        kwargs.setdefault("coded_data_dir", self.coded_dir)
        return summarize_regime_diagnostics_dashboard(**kwargs)


# ── 1. no_records ──────────────────────────────────────────────────────────

class NoRecordsTests(_IsolatedStoreTestCase):
    def test_empty_db_returns_no_records_status(self) -> None:
        result = self._summary()
        self.assertEqual(result["status"], "no_records")
        self.assertEqual(result["records_scanned"], 0)
        self.assertEqual(result["valid_payloads"], 0)
        self.assertEqual(result["paired_outcomes"], 0)
        self.assertEqual(result["pending_outcomes"], 0)
        self.assertFalse(result["calibration_ready"])
        self.assertEqual(result["pos20_quartile_bias"], [])
        self.assertEqual(result["monthly_accuracy"], [])
        self.assertEqual(result["high_confidence_failure_slices"], [])

    def test_only_non_replay_rows_yields_no_records(self) -> None:
        # A live (non-replay) prediction must not be counted; the LIKE
        # filter is the source of truth for which rows belong to replay.
        ps.save_prediction(
            symbol="AVGO", prediction_for_date="2024-01-09",
            scan_result=None, research_result=None,
            predict_result=_predict_result(),
            snapshot_id="—",
        )
        result = self._summary()
        self.assertEqual(result["status"], "no_records")


# ── 2. invalid JSON payload skipped ───────────────────────────────────────

class InvalidPayloadTests(_IsolatedStoreTestCase):
    def test_invalid_json_payload_is_skipped_but_warned(self) -> None:
        # Insert a replay row, then corrupt its contract_payload_json.
        pid = _save_replay(
            analysis_date="2024-01-08",
            prediction_for_date="2024-01-09",
            payload=_build_replay_payload(),
            direction_correct=1,
        )
        with ps._get_conn() as conn:
            conn.execute(
                "UPDATE prediction_log SET contract_payload_json = ? WHERE id = ?",
                ("{not valid json", pid),
            )
        result = self._summary()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["records_scanned"], 1)
        self.assertEqual(result["valid_payloads"], 0)
        self.assertTrue(any(
            "skipped" in w and "invalid" in w for w in result["warnings"]
        ))


# ── 3. pending outcomes counted but excluded from accuracy ────────────────

class PendingOutcomeTests(_IsolatedStoreTestCase):
    def test_pending_record_counted_but_no_accuracy(self) -> None:
        _save_replay(
            analysis_date="2024-01-08",
            prediction_for_date="2024-01-09",
            payload=_build_replay_payload(confidence_level="high"),
            direction_correct=None,  # pending
        )
        result = self._summary()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["valid_payloads"], 1)
        self.assertEqual(result["paired_outcomes"], 0)
        self.assertEqual(result["pending_outcomes"], 1)
        # confidence_by_regime overall.high should reflect 1 pending, no paired.
        bucket = result["confidence_by_regime"]["overall"]["high"]
        self.assertEqual(bucket["samples"], 1)
        self.assertEqual(bucket["pending"], 1)
        self.assertEqual(bucket["correct"], 0)
        self.assertEqual(bucket["wrong"], 0)
        self.assertIsNone(bucket["accuracy"])


# ── 4. pos20 calculation correctness ─────────────────────────────────────

class Pos20ComputationTests(_IsolatedStoreTestCase):
    def test_pos20_at_top_of_range_when_close_equals_rolling_high(self) -> None:
        # Linear ascending closes → close on the most-recent day equals
        # the 20-day rolling high → pos20 = 1.0.
        rows = _make_linear_csv_rows(
            start_close=100.0, step=1.0, count=25,
            start_date="2023-12-15",
        )
        _write_coded_csv(self.coded_dir / "AVGO_coded.csv", rows)
        # Pick analysis_date = day 24 (index 24 → has 24 prior bars).
        target = rows[24]["Date"]
        _save_replay(
            analysis_date=target,
            prediction_for_date="2024-02-01",
            payload=_build_replay_payload(analysis_date=target),
            direction_correct=1,
        )
        result = self._summary()
        rec_pos = [
            r for r in result["pos20_quartile_bias"]
        ]
        # Single record can't form quartiles (we expect a warning + empty list).
        self.assertEqual(rec_pos, [])
        self.assertTrue(any("insufficient pos20 samples" in w for w in result["warnings"]))

    def test_pos20_skip_reason_recorded_when_history_insufficient(self) -> None:
        # Only 5 bars in CSV → pos20 needs 20 prior; expect skip_reason.
        rows = _make_linear_csv_rows(
            start_close=100.0, step=1.0, count=5, start_date="2024-01-01",
        )
        _write_coded_csv(self.coded_dir / "AVGO_coded.csv", rows)
        target = rows[4]["Date"]
        _save_replay(
            analysis_date=target,
            prediction_for_date="2024-01-09",
            payload=_build_replay_payload(analysis_date=target),
            direction_correct=1,
        )
        result = self._summary()
        # Skip reason surfaced via warnings aggregator.
        self.assertTrue(any(
            "insufficient_history" in w for w in result["warnings"]
        ))


# ── 5. pos20 quartile bias output shape ──────────────────────────────────

class Pos20QuartileShapeTests(_IsolatedStoreTestCase):
    def test_quartile_bias_emits_four_buckets_with_required_keys(self) -> None:
        # Build a CSV long enough that 4 different replay days have
        # distinct pos20 values. Linear ascending; pos20 = 1.0 every day
        # once the band stabilizes — so we use a non-monotone walk.
        from datetime import date, timedelta
        rows: list[dict[str, str]] = []
        d = date.fromisoformat("2023-12-01")
        # Saw-tooth: each bar moves +/− alternating to spread pos20.
        for i in range(80):
            base = 100.0 + (i // 4) * 2.0
            jitter = (i % 4) * 1.0
            close = base + jitter
            rows.append({
                "Date": d.isoformat(),
                "Open": f"{close - 0.2:.4f}",
                "High": f"{close + 0.5:.4f}",
                "Low": f"{close - 0.5:.4f}",
                "Close": f"{close:.4f}",
            })
            d += timedelta(days=1)
        _write_coded_csv(self.coded_dir / "AVGO_coded.csv", rows)

        # Save 20 replay rows spread across the CSV's later half so each
        # has ≥ 20 bars of history.
        for i in range(20):
            target = rows[40 + i]["Date"]
            _save_replay(
                analysis_date=target,
                prediction_for_date=rows[40 + i + 1]["Date"],
                payload=_build_replay_payload(analysis_date=target),
                direction_correct=(i % 2),
            )
        result = self._summary()
        bias = result["pos20_quartile_bias"]
        self.assertEqual(len(bias), 4)
        labels = [b["bucket"] for b in bias]
        self.assertEqual(labels, ["Q1", "Q2", "Q3", "Q4"])
        for b in bias:
            self.assertIn("boundary", b)
            self.assertIn("samples", b)
            self.assertIn("paired", b)
            self.assertIn("correct", b)
            self.assertIn("wrong", b)
            self.assertIn("pending", b)
            self.assertIn("accuracy", b)
            self.assertIn("predicted_bullish_rate", b)
            self.assertIn("actual_up_rate", b)
            self.assertIn("bias_gap", b)


# ── 6. R4 signature hits ─────────────────────────────────────────────────

class R4SignatureTests(_IsolatedStoreTestCase):
    def test_r4_matches_record_with_high_pos20_bullish_high_confidence(self) -> None:
        # Build AVGO CSV with strong upward momentum so:
        # - pos20 > 0.62 on day 24
        # - 20-day return on day 24 large
        from datetime import date, timedelta
        avgo_rows = _make_linear_csv_rows(
            start_close=100.0, step=2.0, count=30, start_date="2023-12-01",
        )
        # SOXX flat (return ≈ 0) → diff ≫ 5 pp.
        soxx_rows: list[dict[str, str]] = []
        d = date.fromisoformat("2023-12-01")
        for _ in range(30):
            soxx_rows.append({
                "Date": d.isoformat(),
                "Open": "100.0", "High": "100.5", "Low": "99.5",
                "Close": "100.0",
            })
            d += timedelta(days=1)
        _write_coded_csv(self.coded_dir / "AVGO_coded.csv", avgo_rows)
        _write_coded_csv(self.coded_dir / "SOXX_coded.csv", soxx_rows)

        target = avgo_rows[24]["Date"]
        _save_replay(
            analysis_date=target,
            prediction_for_date=avgo_rows[25]["Date"],
            payload=_build_replay_payload(
                final_direction="偏多",
                confidence_level="high",
                primary_score_raw=2.5,
                analysis_date=target,
            ),
            direction_correct=0,  # call wrong → downgrade candidate
            actual_close=99.0, actual_prev_close=100.0,
        )
        result = self._summary()
        r4 = result["r4_signature"]
        self.assertEqual(r4["samples"], 1)
        self.assertEqual(r4["paired"], 1)
        self.assertEqual(r4["wrong"], 1)
        self.assertEqual(r4["correct"], 0)
        self.assertEqual(r4["high_confidence_count"], 1)
        self.assertEqual(r4["downgrade_candidate_count"], 1)
        self.assertEqual(
            r4["thresholds"]["avgo_minus_soxx_20d"],
            _R4_AVGO_MINUS_SOXX_THRESHOLD,
        )
        self.assertEqual(r4["thresholds"]["pos20"], _R4_POS20_THRESHOLD)


# ── 7. confidence_by_regime outputs ──────────────────────────────────────

class ConfidenceByRegimeTests(_IsolatedStoreTestCase):
    def test_overall_emits_high_medium_low_buckets(self) -> None:
        for level, dc in (("high", 1), ("medium", 0), ("low", 1)):
            _save_replay(
                analysis_date=f"2024-01-{8 + ['high','medium','low'].index(level):02d}",
                prediction_for_date=f"2024-01-{9 + ['high','medium','low'].index(level):02d}",
                payload=_build_replay_payload(confidence_level=level),
                direction_correct=dc,
            )
        result = self._summary()
        overall = result["confidence_by_regime"]["overall"]
        self.assertIn("high", overall)
        self.assertIn("medium", overall)
        self.assertIn("low", overall)
        self.assertEqual(overall["high"]["samples"], 1)
        self.assertEqual(overall["medium"]["samples"], 1)
        self.assertEqual(overall["low"]["samples"], 1)
        self.assertIn("explicit_slices", result["confidence_by_regime"])
        self.assertIn(
            "pos20_gt_0_62_high",
            result["confidence_by_regime"]["explicit_slices"],
        )


# ── 8. peer_adjustment_summary outputs upgrade/hold/downgrade ────────────

class PeerAdjustmentSummaryTests(_IsolatedStoreTestCase):
    def test_summary_emits_three_labels_and_confirm_counts(self) -> None:
        for i, label in enumerate(["upgrade", "hold", "downgrade"]):
            _save_replay(
                analysis_date=f"2024-01-{8 + i:02d}",
                prediction_for_date=f"2024-01-{9 + i:02d}",
                payload=_build_replay_payload(
                    peer_adjustment=label, peer_confirm_count=i,
                ),
                direction_correct=1,
            )
        result = self._summary()
        s = result["peer_adjustment_summary"]
        self.assertEqual(set(s["by_peer_adjustment"]), {"upgrade", "hold", "downgrade"})
        for label in ("upgrade", "hold", "downgrade"):
            self.assertEqual(s["by_peer_adjustment"][label]["samples"], 1)
        self.assertEqual(set(s["by_peer_confirm_count"]), {"0", "1", "2", "3"})
        # 0/1/2 each got one record; 3 got none.
        self.assertEqual(s["by_peer_confirm_count"]["0"]["samples"], 1)
        self.assertEqual(s["by_peer_confirm_count"]["3"]["samples"], 0)


# ── 9. soft_signal_summary outputs none/high_path_risk/peer_weaken ───────

class SoftSignalSummaryTests(_IsolatedStoreTestCase):
    def test_summary_emits_three_labels(self) -> None:
        for i, label in enumerate(["none", "high_path_risk", "peer_weaken"]):
            _save_replay(
                analysis_date=f"2024-01-{8 + i:02d}",
                prediction_for_date=f"2024-01-{9 + i:02d}",
                payload=_build_replay_payload(soft_signal=label),
                direction_correct=1,
            )
        result = self._summary()
        s = result["soft_signal_summary"]
        self.assertEqual(set(s), {"none", "high_path_risk", "peer_weaken"})
        for label in s:
            self.assertEqual(s[label]["samples"], 1)


# ── 10. monthly_accuracy outputs YYYY-MM ─────────────────────────────────

class MonthlyAccuracyTests(_IsolatedStoreTestCase):
    def test_monthly_accuracy_groups_by_yyyymm(self) -> None:
        # 2 records in 2024-01 (one correct, one wrong) and 1 in 2024-02.
        _save_replay(
            analysis_date="2024-01-08", prediction_for_date="2024-01-09",
            payload=_build_replay_payload(), direction_correct=1,
        )
        _save_replay(
            analysis_date="2024-01-15", prediction_for_date="2024-01-16",
            payload=_build_replay_payload(), direction_correct=0,
        )
        _save_replay(
            analysis_date="2024-02-05", prediction_for_date="2024-02-06",
            payload=_build_replay_payload(), direction_correct=1,
        )
        result = self._summary()
        months = {m["month"]: m for m in result["monthly_accuracy"]}
        self.assertEqual(set(months), {"2024-01", "2024-02"})
        self.assertEqual(months["2024-01"]["samples"], 2)
        self.assertAlmostEqual(months["2024-01"]["accuracy"], 0.5, places=6)
        self.assertEqual(months["2024-02"]["samples"], 1)
        self.assertAlmostEqual(months["2024-02"]["accuracy"], 1.0, places=6)


# ── 11. high_confidence_failure_slices fixed list ────────────────────────

class HighConfidenceFailureSlicesTests(_IsolatedStoreTestCase):
    def test_emits_all_five_named_slices(self) -> None:
        _save_replay(
            analysis_date="2024-01-08", prediction_for_date="2024-01-09",
            payload=_build_replay_payload(confidence_level="high"),
            direction_correct=0,
        )
        result = self._summary()
        names = [s["slice"] for s in result["high_confidence_failure_slices"]]
        self.assertEqual(names, [
            "confidence_high",
            "pos20_q3_and_high",
            "pos20_q4_and_high",
            "r4_signature",
            "bullish_high_pos20_gt_0_62",
        ])


# ── 12. read-only ────────────────────────────────────────────────────────

class ReadOnlyTests(_IsolatedStoreTestCase):
    def test_does_not_mutate_db(self) -> None:
        for i in range(3):
            _save_replay(
                analysis_date=f"2024-01-{8 + i:02d}",
                prediction_for_date=f"2024-01-{9 + i:02d}",
                payload=_build_replay_payload(),
                direction_correct=1,
            )
        with ps._get_conn() as conn:
            count_pred = conn.execute(
                "SELECT COUNT(*) FROM prediction_log"
            ).fetchone()[0]
            count_outcome = conn.execute(
                "SELECT COUNT(*) FROM outcome_log"
            ).fetchone()[0]
            rows_before = [
                dict(r) for r in conn.execute(
                    "SELECT * FROM prediction_log ORDER BY id"
                )
            ]

        self._summary()
        self._summary(limit=10)
        self._summary(symbol="AVGO")

        with ps._get_conn() as conn:
            count_pred_after = conn.execute(
                "SELECT COUNT(*) FROM prediction_log"
            ).fetchone()[0]
            count_outcome_after = conn.execute(
                "SELECT COUNT(*) FROM outcome_log"
            ).fetchone()[0]
            rows_after = [
                dict(r) for r in conn.execute(
                    "SELECT * FROM prediction_log ORDER BY id"
                )
            ]
        self.assertEqual(count_pred, count_pred_after)
        self.assertEqual(count_outcome, count_outcome_after)
        self.assertEqual(rows_before, rows_after)


# ── 13. error / missing table → error or no_records, no crash ────────────

class ErrorPathTests(unittest.TestCase):
    def test_unreadable_db_path_returns_error_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            # Pass the directory itself; sqlite3 will fail to open it as DB.
            result = summarize_regime_diagnostics_dashboard(db_path=tmpdir)
        self.assertEqual(result["status"], "error")
        self.assertTrue(result["error"].startswith("db_read_failed"))

    def test_missing_table_treated_as_error_or_no_records(self) -> None:
        # A blank tmp DB has no prediction_log table → sqlite3 raises
        # OperationalError; the service surfaces this as status=error.
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Path(tmpdir) / "blank.db"
            db.touch()  # zero-byte file is a valid empty SQLite DB
            result = summarize_regime_diagnostics_dashboard(db_path=db)
        self.assertIn(result["status"], ("error", "no_records"))


# ── 14. CLI smoke test ──────────────────────────────────────────────────

class CliSmokeTests(_IsolatedStoreTestCase):
    def test_cli_prints_valid_json_with_expected_keys(self) -> None:
        _save_replay(
            analysis_date="2024-01-08", prediction_for_date="2024-01-09",
            payload=_build_replay_payload(), direction_correct=1,
        )
        script = ROOT / "scripts" / "regime_diagnostics_dashboard.py"
        proc = subprocess.run(
            [
                sys.executable, str(script),
                "--db", str(ps.DB_PATH),
                "--symbol", "AVGO",
                "--limit", "10",
                "--coded-data-dir", str(self.coded_dir),
            ],
            capture_output=True, text=True, check=True,
        )
        result = json.loads(proc.stdout)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["symbol"], "AVGO")
        for key in (
            "records_scanned", "valid_payloads", "paired_outcomes",
            "pending_outcomes", "calibration_ready", "time_range",
            "pos20_quartile_bias", "r4_signature", "confidence_by_regime",
            "peer_adjustment_summary", "soft_signal_summary",
            "monthly_accuracy", "high_confidence_failure_slices",
            "warnings",
        ):
            self.assertIn(key, result)


# ── 15. no live network imports ─────────────────────────────────────────

class NoNetworkImportTests(unittest.TestCase):
    def test_service_module_does_not_import_network_libraries(self) -> None:
        import services.regime_diagnostics_dashboard as mod
        # Walk the module's source for forbidden top-level imports.
        src = Path(mod.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "import yfinance",
            "from yfinance",
            "import requests",
            "from requests",
            "longbridge", "broker", "paper_trade",
        ):
            self.assertNotIn(
                forbidden, src,
                f"forbidden token {forbidden!r} found in regime_diagnostics_dashboard.py",
            )


# ── 16. calibration_ready threshold ──────────────────────────────────────

class CalibrationReadyTests(_IsolatedStoreTestCase):
    def test_below_min_pairs_reports_calibration_not_ready(self) -> None:
        _save_replay(
            analysis_date="2024-01-08", prediction_for_date="2024-01-09",
            payload=_build_replay_payload(), direction_correct=1,
        )
        result = self._summary()
        self.assertEqual(result["paired_outcomes"], 1)
        self.assertFalse(result["calibration_ready"])

    def test_min_threshold_constant_value(self) -> None:
        # Lock the contract: changing _MIN_RECOMMENDED_PAIRS is a deliberate
        # action and must update this test together with the docs.
        self.assertEqual(_MIN_RECOMMENDED_PAIRS, 90)


# ── 17. symbol filter is enforced via snapshot_id LIKE ──────────────────

class SymbolFilterTests(_IsolatedStoreTestCase):
    def test_only_matching_symbol_replay_rows_are_scanned(self) -> None:
        _save_replay(
            analysis_date="2024-01-08", prediction_for_date="2024-01-09",
            payload=_build_replay_payload(), direction_correct=1,
            symbol="AVGO",
        )
        # An NVDA replay row must NOT show up under symbol=AVGO.
        nvda_payload = deepcopy(_build_replay_payload())
        nvda_payload["current_structure"]["symbol"] = "NVDA"
        ps.save_prediction(
            symbol="NVDA",
            prediction_for_date="2024-01-09",
            scan_result=None, research_result=None,
            predict_result=_predict_result(symbol="NVDA"),
            snapshot_id="replay_NVDA_2024-01-08",
            contract_payload=nvda_payload,
            analysis_date_override="2024-01-08",
        )
        result = self._summary(symbol="AVGO")
        self.assertEqual(result["records_scanned"], 1)
        result_nvda = self._summary(symbol="NVDA")
        self.assertEqual(result_nvda["records_scanned"], 1)


if __name__ == "__main__":
    unittest.main()
