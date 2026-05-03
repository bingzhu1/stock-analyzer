"""Tests for services/contract_calibration_inputs.py (Step 2F-2)."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import services.prediction_store as ps
from services.contract_calibration_inputs import (
    _MIN_RECOMMENDED_PAIRS,
    summarize_confidence_calibration_inputs,
)


def _predict_result(
    symbol: str = "AVGO",
    bias: str = "bullish",
    confidence: str = "medium",
    pred_open: str = "高开",
    pred_path: str = "高开高走",
    pred_close: str = "收涨",
) -> dict:
    return {
        "symbol": symbol,
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


def _save_outcome(pid: str, direction_correct: int | None, pred_date: str = "2026-04-11") -> str:
    return ps.save_outcome(
        prediction_id=pid,
        prediction_for_date=pred_date,
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


# ── 1. no records ──────────────────────────────────────────────────────────

class CalibNoRecordsTests(_IsolatedStoreTestCase):
    def test_no_predictions_returns_no_records_status(self) -> None:
        result = summarize_confidence_calibration_inputs()
        self.assertEqual(result["status"], "no_records")
        self.assertEqual(result["records_scanned"], 0)
        self.assertEqual(result["valid_payloads"], 0)
        self.assertEqual(result["records_with_confidence_extras"], 0)
        self.assertEqual(result["paired_outcomes"], 0)
        self.assertEqual(result["pending_outcomes"], 0)
        self.assertEqual(result["skipped_records"], [])
        self.assertEqual(result["records"], [])
        self.assertEqual(result["requested_limit"], 50)
        self.assertEqual(result["symbol_filter"], "AVGO")
        self.assertNotIn("data_gap_report", result)


# ── 2. all invalid → no_valid_payloads ─────────────────────────────────────

class CalibAllInvalidTests(_IsolatedStoreTestCase):
    def test_all_missing_or_invalid_returns_no_valid_payloads(self) -> None:
        ps.save_prediction(
            "AVGO", "2026-04-09", None, None, _predict_result(),
            contract_payload=None,
        )
        ps.save_prediction(
            "AVGO", "2026-04-10", None, None, _predict_result(),
            contract_payload={"only_one_section": "bogus"},
        )
        result = summarize_confidence_calibration_inputs()
        self.assertEqual(result["status"], "no_valid_payloads")
        self.assertEqual(result["valid_payloads"], 0)
        self.assertEqual(result["invalid_payloads"], 2)
        reasons = {s["reason"] for s in result["skipped_records"]}
        self.assertIn("missing_contract_payload", reasons)
        self.assertIn("validation_failed", reasons)

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
        result = summarize_confidence_calibration_inputs()
        reasons = [s["reason"] for s in result["skipped_records"]]
        self.assertIn("invalid_json", reasons)


# ── 3. valid contract payload (with / without confidence extras) ──────────

class CalibRecordShapeTests(_IsolatedStoreTestCase):
    def test_valid_payload_with_modern_extras_yields_full_record(self) -> None:
        # save_prediction's auto-side-path in the current adapter writes
        # confidence extras (Step 2C-3b is on main).
        pid = ps.save_prediction(
            "AVGO", "2026-04-11", None, None, _predict_result(confidence="high"),
        )
        result = summarize_confidence_calibration_inputs()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["valid_payloads"], 1)
        self.assertEqual(result["records_with_confidence_extras"], 1)
        rec = result["records"][0]
        self.assertEqual(rec["prediction_id"], pid)
        self.assertEqual(rec["prediction_for_date"], "2026-04-11")
        self.assertEqual(rec["symbol"], "AVGO")
        self.assertTrue(rec["has_confidence_extras"])
        # primary_score_raw is a number (real or None depending on payload)
        self.assertTrue(
            rec["primary_score_raw"] is None
            or isinstance(rec["primary_score_raw"], (int, float))
        )
        self.assertEqual(rec["final_confidence"], "high")
        self.assertEqual(rec["direction_correct"], "pending")  # no outcome saved

    def test_valid_payload_without_extras_keeps_record_with_flag(self) -> None:
        # Manually craft a contract-valid payload that LACKS confidence_system.extras
        # (i.e. an older payload from before Step 2C-3b).
        no_extras_payload = self._minimal_valid_payload_without_confidence_extras()
        ps.save_prediction(
            "AVGO", "2026-04-11", None, None, _predict_result(),
            contract_payload=no_extras_payload,
        )
        result = summarize_confidence_calibration_inputs()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["valid_payloads"], 1)
        self.assertEqual(result["records_with_confidence_extras"], 0)
        rec = result["records"][0]
        self.assertFalse(rec["has_confidence_extras"])
        self.assertIsNone(rec["primary_score_raw"])
        self.assertIsNone(rec["primary_confidence_raw"])
        self.assertIsNone(rec["peer_confirm_count"])
        self.assertIsNone(rec["soft_signal"])

    @staticmethod
    def _minimal_valid_payload_without_confidence_extras() -> dict:
        return {
            "current_structure": {
                "symbol": "AVGO", "analysis_date": "2099-01-01",
                "prediction_for_date": "2026-04-11", "data_window_days": 20,
                "current_price": 100.0, "previous_close": 99.0,
                "volume": 1_000_000, "turnover": 1.0e8,
                "structure_label": "bullish", "short_summary": "",
            },
            "avgo_primary_projection": {
                "primary_direction": "偏多", "open_projection": "高开",
                "intraday_path_projection": "高走", "close_projection": "收涨",
                "five_state_projection": "小涨", "historical_sample_count": 0,
                "key_evidence": [], "primary_confidence_raw": "medium",
            },
            "peer_confirmation_adjustment": {
                "peer_symbols": ["NVDA", "SOXX", "QQQ"],
                "nvda_signal": "neutral", "soxx_signal": "neutral",
                "qqq_signal": "neutral", "peer_alignment": "insufficient",
                "peer_adjustment": "hold", "adjusted_direction": "偏多",
                "adjustment_reason": "",
            },
            "exclusion_system": {
                "exclusion_level": "none", "exclusion_sources": [],
                "exclusion_reasons": [], "forced_exclusion": False,
                "anti_false_exclusion_triggered": False,
            },
            "confidence_system": {
                # NO extras — this is the "old payload" case.
                "historical_score": 0.0, "structure_score": 0.0,
                "peer_score": 0.0, "exclusion_penalty": 0.0,
                "event_score": None, "total_confidence": 0.5,
                "confidence_level": "medium", "confidence_reason": "",
            },
            "final_projection": {
                "final_direction": "偏多", "final_open_projection": "高开",
                "final_intraday_path": "高走", "final_close_projection": "收涨",
                "final_five_state": "小涨", "probability_bucket": "55–70%",
                "key_price_levels": {}, "final_one_sentence": "",
            },
            "simulated_trade": {
                "trade_action": "no_trade", "trade_direction": "none",
                "entry_condition": "", "stop_loss_condition": "",
                "take_profit_condition": "", "suggested_position_size": "0%",
                "no_trade_reason": "<old payload>",
            },
            "review_payload": {
                "prediction_id": "", "predicted_open_type": "高开",
                "predicted_path_type": "高走", "predicted_close_type": "收涨",
                "predicted_five_state": "小涨", "predicted_confidence": "medium",
                "review_ready_fields": [],
            },
        }


# ── 4. outcome direction_correct labelling ─────────────────────────────────

class CalibOutcomeLabellingTests(_IsolatedStoreTestCase):
    def test_outcome_pending_yields_pending_label(self) -> None:
        ps.save_prediction("AVGO", "2026-04-11", None, None, _predict_result())
        result = summarize_confidence_calibration_inputs()
        self.assertEqual(result["records"][0]["direction_correct"], "pending")
        self.assertEqual(result["pending_outcomes"], 1)
        self.assertEqual(result["paired_outcomes"], 0)

    def test_outcome_correct_increments_correct_count(self) -> None:
        pid = ps.save_prediction("AVGO", "2026-04-11", None, None, _predict_result())
        _save_outcome(pid, 1)
        result = summarize_confidence_calibration_inputs()
        self.assertEqual(result["records"][0]["direction_correct"], "correct")
        self.assertEqual(result["paired_outcomes"], 1)
        self.assertEqual(result["pending_outcomes"], 0)

    def test_outcome_wrong_increments_wrong_count(self) -> None:
        pid = ps.save_prediction("AVGO", "2026-04-11", None, None, _predict_result())
        _save_outcome(pid, 0)
        result = summarize_confidence_calibration_inputs()
        self.assertEqual(result["records"][0]["direction_correct"], "wrong")
        self.assertEqual(result["paired_outcomes"], 1)


# ── 5. confidence_level_summary buckets and accuracy ──────────────────────

class CalibConfidenceLevelSummaryTests(_IsolatedStoreTestCase):
    def test_accuracy_uses_correct_over_correct_plus_wrong(self) -> None:
        # 3 medium-confidence: 2 correct, 1 wrong → accuracy = 2/3
        for dc in (1, 1, 0):
            pid = ps.save_prediction(
                "AVGO", "2026-04-11", None, None,
                _predict_result(confidence="medium"),
            )
            _save_outcome(pid, dc)
        result = summarize_confidence_calibration_inputs()
        bucket = result["confidence_level_summary"]["medium"]
        self.assertEqual(bucket["samples"], 3)
        self.assertEqual(bucket["correct"], 2)
        self.assertEqual(bucket["wrong"], 1)
        self.assertEqual(bucket["pending"], 0)
        self.assertAlmostEqual(bucket["accuracy"], 2 / 3, places=6)

    def test_pending_excluded_from_accuracy_denominator(self) -> None:
        # 2 medium correct, 0 wrong, 5 pending → accuracy = 1.0
        pids = [
            ps.save_prediction(
                "AVGO", "2026-04-11", None, None,
                _predict_result(confidence="medium"),
            )
            for _ in range(7)
        ]
        _save_outcome(pids[0], 1)
        _save_outcome(pids[1], 1)
        result = summarize_confidence_calibration_inputs()
        bucket = result["confidence_level_summary"]["medium"]
        self.assertEqual(bucket["pending"], 5)
        self.assertEqual(bucket["accuracy"], 1.0)

    def test_zero_resolved_yields_accuracy_none(self) -> None:
        for _ in range(3):
            ps.save_prediction(
                "AVGO", "2026-04-11", None, None,
                _predict_result(confidence="low"),
            )
        result = summarize_confidence_calibration_inputs()
        bucket = result["confidence_level_summary"]["low"]
        self.assertEqual(bucket["correct"], 0)
        self.assertEqual(bucket["wrong"], 0)
        self.assertIsNone(bucket["accuracy"])


# ── 6. primary_score_raw_summary ───────────────────────────────────────────

class CalibPrimaryScoreSummaryTests(_IsolatedStoreTestCase):
    def test_min_max_mean_over_real_numbers(self) -> None:
        # 3 contract-valid payloads carrying explicit numeric
        # ``confidence_system.extras.primary_score_raw`` values: 1.0, 2.0,
        # 3.0. The minimal _predict_result() fixture has no
        # primary_projection sub-dict, so the adapter would emit
        # primary_score_raw=None; we bypass the auto side-path with a
        # custom contract_payload to control the value precisely.
        from copy import deepcopy
        for score in (1.0, 2.0, 3.0):
            payload = deepcopy(
                CalibRecordShapeTests._minimal_valid_payload_without_confidence_extras()
            )
            payload["confidence_system"]["extras"] = {
                "primary_score_raw": score,
                "primary_confidence_raw": "medium",
                "peer_confirm_count": 0,
                "peer_oppose_count": 0,
                "peer_adjusted_confidence": "medium",
                "final_confidence": "medium",
                "probability_bucket": "55–70%",
                "conflicting_factors_count": 0,
                "path_risk_level": "unknown",
                "soft_signal": "none",
            }
            ps.save_prediction(
                "AVGO", "2026-04-11", None, None, _predict_result(),
                contract_payload=payload,
            )
        summary = summarize_confidence_calibration_inputs()["primary_score_raw_summary"]
        self.assertEqual(summary["count"], 3)
        self.assertEqual(summary["min"], 1.0)
        self.assertEqual(summary["max"], 3.0)
        self.assertAlmostEqual(summary["mean"], 2.0, places=6)

    def test_no_real_numbers_yields_zero_count(self) -> None:
        # Save a payload whose extras has primary_score_raw=None.
        no_score_payload = self._payload_with_explicit_none_score()
        ps.save_prediction(
            "AVGO", "2026-04-11", None, None, _predict_result(),
            contract_payload=no_score_payload,
        )
        result = summarize_confidence_calibration_inputs()
        summary = result["primary_score_raw_summary"]
        self.assertEqual(summary["count"], 0)
        self.assertIsNone(summary["min"])
        self.assertIsNone(summary["max"])
        self.assertIsNone(summary["mean"])

    @staticmethod
    def _payload_with_explicit_none_score() -> dict:
        # Re-uses the no-extras fixture and patches confidence_system.extras
        # with primary_score_raw = None.
        from copy import deepcopy
        base = CalibRecordShapeTests._minimal_valid_payload_without_confidence_extras()
        payload = deepcopy(base)
        payload["confidence_system"]["extras"] = {
            "primary_score_raw": None,
            "primary_confidence_raw": "medium",
            "peer_confirm_count": 0,
            "peer_oppose_count": 0,
            "peer_adjusted_confidence": "medium",
            "final_confidence": "medium",
            "probability_bucket": "55–70%",
            "conflicting_factors_count": 0,
            "path_risk_level": "unknown",
            "soft_signal": "none",
        }
        return payload


# ── 7. data_gap_report ──────────────────────────────────────────────────────

class CalibDataGapReportTests(_IsolatedStoreTestCase):
    def test_zero_pairs_flags_no_paired_outcomes(self) -> None:
        ps.save_prediction("AVGO", "2026-04-11", None, None, _predict_result())
        result = summarize_confidence_calibration_inputs()
        gap = result["data_gap_report"]
        self.assertEqual(gap["contract_outcome_pairs"], 0)
        self.assertEqual(gap["minimum_recommended_pairs"], _MIN_RECOMMENDED_PAIRS)
        self.assertFalse(gap["calibration_ready"])
        self.assertIn(
            "no paired outcomes for valid contract payloads",
            gap["missing_dimensions"],
        )

    def test_few_pairs_below_threshold_flags_insufficient_pairs(self) -> None:
        # 1 paired pair: not zero, but well below 90.
        pid = ps.save_prediction("AVGO", "2026-04-11", None, None, _predict_result())
        _save_outcome(pid, 1)
        gap = summarize_confidence_calibration_inputs()["data_gap_report"]
        self.assertEqual(gap["contract_outcome_pairs"], 1)
        self.assertFalse(gap["calibration_ready"])
        self.assertTrue(
            any("insufficient pairs" in s for s in gap["missing_dimensions"]),
        )

    def test_single_confidence_level_flags_coverage_gap(self) -> None:
        # All medium → high+low missing → coverage gap flagged.
        for _ in range(3):
            pid = ps.save_prediction(
                "AVGO", "2026-04-11", None, None,
                _predict_result(confidence="medium"),
            )
            _save_outcome(pid, 1)
        gap = summarize_confidence_calibration_inputs()["data_gap_report"]
        self.assertIn(
            "insufficient high/medium/low coverage", gap["missing_dimensions"]
        )

    def test_single_peer_confirm_count_flags_peer_gap(self) -> None:
        # All 3 records have the same peer_confirm_count (whatever the
        # live adapter produces) → coverage gap flagged.
        for _ in range(3):
            pid = ps.save_prediction(
                "AVGO", "2026-04-11", None, None, _predict_result(),
            )
            _save_outcome(pid, 1)
        gap = summarize_confidence_calibration_inputs()["data_gap_report"]
        self.assertIn(
            "insufficient peer_confirm_count coverage", gap["missing_dimensions"]
        )

    def test_single_soft_signal_flags_signal_gap(self) -> None:
        for _ in range(3):
            pid = ps.save_prediction(
                "AVGO", "2026-04-11", None, None, _predict_result(),
            )
            _save_outcome(pid, 1)
        gap = summarize_confidence_calibration_inputs()["data_gap_report"]
        self.assertIn(
            "insufficient soft_signal coverage", gap["missing_dimensions"]
        )


# ── 8. limit handling ─────────────────────────────────────────────────────

class CalibLimitTests(_IsolatedStoreTestCase):
    def test_limit_truncates_records_scanned(self) -> None:
        for _ in range(60):
            ps.save_prediction("AVGO", "2026-04-11", None, None, _predict_result())
        result = summarize_confidence_calibration_inputs(limit=10)
        self.assertEqual(result["requested_limit"], 10)
        self.assertEqual(result["records_scanned"], 10)

    def test_zero_limit_falls_back_to_default_50(self) -> None:
        for _ in range(55):
            ps.save_prediction("AVGO", "2026-04-11", None, None, _predict_result())
        result = summarize_confidence_calibration_inputs(limit=0)
        self.assertEqual(result["requested_limit"], 50)

    def test_negative_limit_falls_back_to_default(self) -> None:
        ps.save_prediction("AVGO", "2026-04-11", None, None, _predict_result())
        result = summarize_confidence_calibration_inputs(limit=-1)
        self.assertEqual(result["requested_limit"], 50)

    def test_non_int_limit_falls_back_to_default(self) -> None:
        ps.save_prediction("AVGO", "2026-04-11", None, None, _predict_result())
        result = summarize_confidence_calibration_inputs(limit="abc")  # type: ignore[arg-type]
        self.assertEqual(result["requested_limit"], 50)

    def test_bool_limit_falls_back_to_default(self) -> None:
        ps.save_prediction("AVGO", "2026-04-11", None, None, _predict_result())
        result = summarize_confidence_calibration_inputs(limit=True)  # type: ignore[arg-type]
        self.assertEqual(result["requested_limit"], 50)


# ── 9. symbol filter ──────────────────────────────────────────────────────

class CalibSymbolFilterTests(_IsolatedStoreTestCase):
    def _seed_mixed(self) -> None:
        for _ in range(3):
            ps.save_prediction(
                "AVGO", "2026-04-11", None, None,
                _predict_result(symbol="AVGO"),
            )
        for _ in range(2):
            ps.save_prediction(
                "NVDA", "2026-04-11", None, None,
                _predict_result(symbol="NVDA"),
            )

    def test_default_symbol_filter_is_avgo(self) -> None:
        self._seed_mixed()
        result = summarize_confidence_calibration_inputs()
        self.assertEqual(result["symbol_filter"], "AVGO")
        self.assertEqual(result["records_scanned"], 3)

    def test_symbol_all_includes_every_symbol(self) -> None:
        self._seed_mixed()
        result = summarize_confidence_calibration_inputs(symbol="ALL")
        self.assertEqual(result["symbol_filter"], "ALL")
        self.assertEqual(result["records_scanned"], 5)

    def test_symbol_nvda_only_counts_nvda(self) -> None:
        self._seed_mixed()
        result = summarize_confidence_calibration_inputs(symbol="NVDA")
        self.assertEqual(result["symbol_filter"], "NVDA")
        self.assertEqual(result["records_scanned"], 2)


# ── 10. read-only ─────────────────────────────────────────────────────────

class CalibReadOnlyTests(_IsolatedStoreTestCase):
    def test_does_not_mutate_db(self) -> None:
        for _ in range(3):
            pid = ps.save_prediction(
                "AVGO", "2026-04-11", None, None, _predict_result(),
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

        summarize_confidence_calibration_inputs()
        summarize_confidence_calibration_inputs(limit=5)
        summarize_confidence_calibration_inputs(symbol="ALL")

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
        self.assertEqual(count_pred_before, count_pred_after)
        self.assertEqual(count_outcome_before, count_outcome_after)
        self.assertEqual(rows_before, rows_after)


# ── 11. error path ────────────────────────────────────────────────────────

class CalibErrorPathTests(unittest.TestCase):
    def test_unreadable_db_path_returns_error_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = summarize_confidence_calibration_inputs(db_path=tmpdir)
        self.assertEqual(result["status"], "error")
        self.assertTrue(result["error"].startswith("db_read_failed"))


# ── 12. CLI ───────────────────────────────────────────────────────────────

class CalibScriptArgTests(_IsolatedStoreTestCase):
    def _run(self, *extra: str) -> dict:
        script = ROOT / "scripts" / "summarize_confidence_calibration_inputs.py"
        proc = subprocess.run(
            [sys.executable, str(script), "--db", str(ps.DB_PATH), *extra],
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(proc.stdout)

    def test_script_default_symbol_is_avgo(self) -> None:
        ps.save_prediction("AVGO", "2026-04-11", None, None, _predict_result())
        ps.save_prediction(
            "NVDA", "2026-04-11", None, None, _predict_result(symbol="NVDA"),
        )
        result = self._run()
        self.assertEqual(result["symbol_filter"], "AVGO")
        self.assertEqual(result["records_scanned"], 1)

    def test_script_accepts_symbol_all(self) -> None:
        ps.save_prediction("AVGO", "2026-04-11", None, None, _predict_result())
        ps.save_prediction(
            "NVDA", "2026-04-11", None, None, _predict_result(symbol="NVDA"),
        )
        result = self._run("--symbol", "ALL")
        self.assertEqual(result["symbol_filter"], "ALL")
        self.assertEqual(result["records_scanned"], 2)

    def test_script_accepts_explicit_limit(self) -> None:
        for _ in range(8):
            ps.save_prediction("AVGO", "2026-04-11", None, None, _predict_result())
        result = self._run("--limit", "3")
        self.assertEqual(result["requested_limit"], 3)
        self.assertEqual(result["records_scanned"], 3)


if __name__ == "__main__":
    unittest.main()
