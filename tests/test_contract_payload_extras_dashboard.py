"""Tests for services/contract_payload_extras_dashboard.py (Step 2E-2)."""
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
from services.contract_payload_extras_dashboard import (
    DISTRIBUTION_PATHS,
    summarize_contract_extras_dashboard,
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


class _IsolatedStoreTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        ps.DB_PATH = Path(self._tmpdir.name) / "test.db"
        ps.init_db()

    def tearDown(self) -> None:
        self._tmpdir.cleanup()


# ── 1. no records ───────────────────────────────────────────────────────────

class DashboardNoRecordsTests(_IsolatedStoreTestCase):
    def test_no_predictions_returns_no_records_status(self) -> None:
        result = summarize_contract_extras_dashboard()
        self.assertEqual(result["status"], "no_records")
        self.assertEqual(result["records_scanned"], 0)
        self.assertEqual(result["valid_payloads"], 0)
        self.assertEqual(result["invalid_payloads"], 0)
        self.assertEqual(result["skipped_records"], [])
        self.assertEqual(result["requested_limit"], 20)
        self.assertEqual(result["symbol_filter"], "AVGO")
        self.assertNotIn("latest_snapshot", result)
        self.assertNotIn("extras_distributions", result)


# ── 2. all invalid → no_valid_payloads ─────────────────────────────────────

class DashboardAllInvalidTests(_IsolatedStoreTestCase):
    def test_all_invalid_returns_no_valid_payloads(self) -> None:
        # missing contract_payload + invalid validation payload
        ps.save_prediction(
            "AVGO", "2026-04-09", None, None, _predict_result(),
            contract_payload=None,
        )
        ps.save_prediction(
            "AVGO", "2026-04-10", None, None, _predict_result(),
            contract_payload={"only_one_section": "bogus"},
        )
        result = summarize_contract_extras_dashboard()
        self.assertEqual(result["status"], "no_valid_payloads")
        self.assertEqual(result["valid_payloads"], 0)
        self.assertEqual(result["invalid_payloads"], 2)
        reasons = [s["reason"] for s in result["skipped_records"]]
        self.assertIn("missing_contract_payload", reasons)
        self.assertIn("validation_failed", reasons)
        self.assertNotIn("latest_snapshot", result)

    def test_invalid_json_is_skipped_with_invalid_json_reason(self) -> None:
        bogus_pid = ps.save_prediction(
            "AVGO", "2026-04-11", None, None, _predict_result(),
            contract_payload=None,
        )
        with ps._get_conn() as conn:
            conn.execute(
                "UPDATE prediction_log SET contract_payload_json = ? WHERE id = ?",
                ("{not valid json", bogus_pid),
            )
        result = summarize_contract_extras_dashboard()
        reasons = [s["reason"] for s in result["skipped_records"]]
        self.assertIn("invalid_json", reasons)


# ── 3. status ok and shape ──────────────────────────────────────────────────

class DashboardOkStatusTests(_IsolatedStoreTestCase):
    def test_one_valid_prediction_returns_ok_with_full_shape(self) -> None:
        ps.save_prediction(
            "AVGO", "2026-04-11", None, None, _predict_result()
        )
        result = summarize_contract_extras_dashboard()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["valid_payloads"], 1)
        self.assertIn("latest_snapshot", result)
        self.assertIn("extras_distributions", result)


# ── 4. latest_snapshot picks the most recent valid payload ─────────────────

class DashboardLatestSnapshotTests(_IsolatedStoreTestCase):
    def test_latest_snapshot_is_most_recent_valid_payload(self) -> None:
        # Save two valid predictions; second is most recent.
        ps.save_prediction(
            "AVGO", "2026-04-10", None, None, _predict_result(bias="bearish",
                                                              pred_open="低开",
                                                              pred_path="低开低走",
                                                              pred_close="收跌"),
        )
        latest_pid = ps.save_prediction(
            "AVGO", "2026-04-11", None, None,
            _predict_result(bias="bullish", confidence="high"),
        )
        result = summarize_contract_extras_dashboard()
        snapshot = result["latest_snapshot"]
        self.assertEqual(snapshot["prediction_id"], latest_pid)
        self.assertEqual(snapshot["prediction_for_date"], "2026-04-11")
        self.assertEqual(snapshot["final_direction"], "偏多")
        self.assertEqual(snapshot["confidence_level"], "high")
        self.assertEqual(snapshot["trade_action"], "no_trade")
        # extras blocks present (Step 2C-2 / 2C-3b / 2D-2 self-published).
        self.assertIsInstance(snapshot["exclusion_system_extras"], dict)
        self.assertIsInstance(snapshot["confidence_system_extras"], dict)
        self.assertIsInstance(snapshot["simulated_trade_extras"], dict)

    def test_latest_snapshot_skips_invalid_to_pick_next(self) -> None:
        # Most-recent row is invalid; snapshot should fall back to older valid.
        valid_pid = ps.save_prediction(
            "AVGO", "2026-04-10", None, None, _predict_result()
        )
        ps.save_prediction(
            "AVGO", "2026-04-11", None, None, _predict_result(),
            contract_payload=None,  # most recent is invalid (missing)
        )
        result = summarize_contract_extras_dashboard()
        # invalid 1, valid 1
        self.assertEqual(result["valid_payloads"], 1)
        self.assertEqual(result["invalid_payloads"], 1)
        self.assertEqual(result["latest_snapshot"]["prediction_id"], valid_pid)


# ── 5. extras_distributions reflects predict_result extras ─────────────────

class DashboardDistributionsTests(_IsolatedStoreTestCase):
    def test_soft_signal_distribution_reflects_payloads(self) -> None:
        # 3 AVGO predictions, all peers stronger → soft_signal "none"
        for _ in range(3):
            ps.save_prediction(
                "AVGO", "2026-04-11", None, None, _predict_result(),
            )
        result = summarize_contract_extras_dashboard()
        excl_soft = result["extras_distributions"]["exclusion_system.extras.soft_signal"]
        # adapter built extras from the empty conflicting_factors → "none"
        self.assertEqual(excl_soft.get("none"), 3)
        self.assertNotIn("MISSING", excl_soft)

    def test_path_risk_level_distribution_passes_through(self) -> None:
        # path_risk in predict_result is "low" by default in our fixture
        # (it's not set; adapter falls back to "unknown")
        for _ in range(2):
            ps.save_prediction(
                "AVGO", "2026-04-11", None, None, _predict_result(),
            )
        excl_path = (
            summarize_contract_extras_dashboard()
            ["extras_distributions"]["exclusion_system.extras.path_risk_level"]
        )
        # _predict_result fixture doesn't set path_risk → adapter → "unknown"
        self.assertEqual(excl_path.get("unknown"), 2)

    def test_confidence_raw_distribution_reflects_final_confidence(self) -> None:
        ps.save_prediction("AVGO", "2026-04-11", None, None,
                            _predict_result(confidence="high"))
        ps.save_prediction("AVGO", "2026-04-11", None, None,
                            _predict_result(confidence="medium"))
        ps.save_prediction("AVGO", "2026-04-11", None, None,
                            _predict_result(confidence="medium"))
        # confidence_system.extras.final_confidence mirrors predict.final_confidence
        result = summarize_contract_extras_dashboard()
        bucket = result["extras_distributions"]["confidence_system.extras.final_confidence"]
        self.assertEqual(bucket.get("high"), 1)
        self.assertEqual(bucket.get("medium"), 2)

    def test_simulated_trade_bool_fields_use_string_keys(self) -> None:
        # trade_engine_enabled is constant False; has_key_price_levels is False
        # because adapter never produces non-empty key_price_levels today.
        for _ in range(4):
            ps.save_prediction(
                "AVGO", "2026-04-11", None, None, _predict_result(),
            )
        dist = summarize_contract_extras_dashboard()["extras_distributions"]
        self.assertEqual(
            dist["simulated_trade.extras.trade_engine_enabled"], {"False": 4}
        )
        self.assertEqual(
            dist["simulated_trade.extras.has_key_price_levels"], {"False": 4}
        )

    def test_distribution_paths_constant_covers_three_sections(self) -> None:
        sections = {section for section, _ in DISTRIBUTION_PATHS}
        self.assertEqual(
            sections,
            {"exclusion_system", "confidence_system", "simulated_trade"},
        )


# ── 6. defensive: missing extras → "MISSING" bucket (not skipped) ───────────

class DashboardMissingExtrasTests(_IsolatedStoreTestCase):
    def _save_valid_payload_without_extras(self, prediction_for_date: str) -> str:
        """Manually craft a contract-valid payload that lacks `extras` blocks
        (i.e. an "older" payload from before Step 2C-2 / 2C-3b / 2D-2).

        Use ``contract_payload=`` to bypass the auto side-path.
        """
        no_extras_payload = {
            "current_structure": {
                "symbol": "AVGO",
                "analysis_date": "2099-01-01",
                "prediction_for_date": prediction_for_date,
                "data_window_days": 20,
                "current_price": 100.0,
                "previous_close": 99.0,
                "volume": 1_000_000,
                "turnover": 100_000_000.0,
                "structure_label": "bullish",
                "short_summary": "<placeholder>",
            },
            "avgo_primary_projection": {
                "primary_direction": "偏多",
                "open_projection": "高开",
                "intraday_path_projection": "高走",
                "close_projection": "收涨",
                "five_state_projection": "小涨",
                "historical_sample_count": 0,
                "key_evidence": ["a"],
                "primary_confidence_raw": "medium",
            },
            "peer_confirmation_adjustment": {
                "peer_symbols": ["NVDA", "SOXX", "QQQ"],
                "nvda_signal": "neutral",
                "soxx_signal": "neutral",
                "qqq_signal": "neutral",
                "peer_alignment": "insufficient",
                "peer_adjustment": "hold",
                "adjusted_direction": "偏多",
                "adjustment_reason": "<placeholder>",
            },
            "exclusion_system": {
                # NOTE: deliberately no "extras" block.
                "exclusion_level": "none",
                "exclusion_sources": [],
                "exclusion_reasons": [],
                "forced_exclusion": False,
                "anti_false_exclusion_triggered": False,
            },
            "confidence_system": {
                # NOTE: deliberately no "extras" block.
                "historical_score": 0.0,
                "structure_score": 0.0,
                "peer_score": 0.0,
                "exclusion_penalty": 0.0,
                "event_score": None,
                "total_confidence": 0.50,
                "confidence_level": "medium",
                "confidence_reason": "<placeholder>",
            },
            "final_projection": {
                "final_direction": "偏多",
                "final_open_projection": "高开",
                "final_intraday_path": "高走",
                "final_close_projection": "收涨",
                "final_five_state": "小涨",
                "probability_bucket": "55–70%",
                "key_price_levels": {},
                "final_one_sentence": "<placeholder>",
            },
            "simulated_trade": {
                # NOTE: deliberately no "extras" block.
                "trade_action": "no_trade",
                "trade_direction": "none",
                "entry_condition": "",
                "stop_loss_condition": "",
                "take_profit_condition": "",
                "suggested_position_size": "0%",
                "no_trade_reason": "<old payload>",
            },
            "review_payload": {
                "prediction_id": "",
                "predicted_open_type": "高开",
                "predicted_path_type": "高走",
                "predicted_close_type": "收涨",
                "predicted_five_state": "小涨",
                "predicted_confidence": "medium",
                "review_ready_fields": [],
            },
        }
        return ps.save_prediction(
            "AVGO", prediction_for_date, None, None, _predict_result(),
            contract_payload=no_extras_payload,
        )

    def test_missing_extras_block_counts_as_missing_not_invalid(self) -> None:
        self._save_valid_payload_without_extras("2026-04-11")
        result = summarize_contract_extras_dashboard()
        # Old payload is *valid* (no validation_failed); just lacks extras.
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["valid_payloads"], 1)
        self.assertEqual(result["invalid_payloads"], 0)
        self.assertEqual(result["skipped_records"], [])

        dist = result["extras_distributions"]
        self.assertEqual(
            dist["exclusion_system.extras.soft_signal"], {"MISSING": 1}
        )
        self.assertEqual(
            dist["confidence_system.extras.final_confidence"], {"MISSING": 1}
        )
        self.assertEqual(
            dist["simulated_trade.extras.trade_engine_enabled"], {"MISSING": 1}
        )

    def test_latest_snapshot_extras_blocks_are_none_for_old_payload(self) -> None:
        self._save_valid_payload_without_extras("2026-04-11")
        snapshot = summarize_contract_extras_dashboard()["latest_snapshot"]
        self.assertIsNone(snapshot["exclusion_system_extras"])
        self.assertIsNone(snapshot["confidence_system_extras"])
        self.assertIsNone(snapshot["simulated_trade_extras"])
        # decision-summary fields still present.
        self.assertEqual(snapshot["final_direction"], "偏多")
        self.assertEqual(snapshot["trade_action"], "no_trade")

    def test_explicit_none_extras_field_counts_as_null(self) -> None:
        # Build a payload that has extras dict but with primary_score_raw=None.
        # The adapter naturally produces None when primary_projection.score is
        # not a float; we craft this case via a custom contract_payload.
        payload = {
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
                "extras": {
                    "soft_signal": "none", "path_risk_level": None,
                    "peer_path_risk_direction": None,
                    "conflicting_factors_count": 0,
                },
            },
            "confidence_system": {
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
                "no_trade_reason": "<placeholder>",
            },
            "review_payload": {
                "prediction_id": "", "predicted_open_type": "高开",
                "predicted_path_type": "高走", "predicted_close_type": "收涨",
                "predicted_five_state": "小涨", "predicted_confidence": "medium",
                "review_ready_fields": [],
            },
        }
        ps.save_prediction(
            "AVGO", "2026-04-11", None, None, _predict_result(),
            contract_payload=payload,
        )
        dist = summarize_contract_extras_dashboard()["extras_distributions"]
        # path_risk_level explicitly None → "NULL" bucket
        self.assertEqual(
            dist["exclusion_system.extras.path_risk_level"], {"NULL": 1}
        )


# ── 7. limit / symbol parameter handling ────────────────────────────────────

class DashboardLimitTests(_IsolatedStoreTestCase):
    def test_limit_truncates_records_scanned(self) -> None:
        for _ in range(30):
            ps.save_prediction("AVGO", "2026-04-11", None, None, _predict_result())
        result = summarize_contract_extras_dashboard(limit=10)
        self.assertEqual(result["requested_limit"], 10)
        self.assertEqual(result["records_scanned"], 10)

    def test_zero_limit_falls_back_to_default_20(self) -> None:
        for _ in range(25):
            ps.save_prediction("AVGO", "2026-04-11", None, None, _predict_result())
        result = summarize_contract_extras_dashboard(limit=0)
        self.assertEqual(result["requested_limit"], 20)

    def test_negative_limit_falls_back_to_default_20(self) -> None:
        for _ in range(5):
            ps.save_prediction("AVGO", "2026-04-11", None, None, _predict_result())
        result = summarize_contract_extras_dashboard(limit=-5)
        self.assertEqual(result["requested_limit"], 20)

    def test_non_int_limit_falls_back_to_default_20(self) -> None:
        ps.save_prediction("AVGO", "2026-04-11", None, None, _predict_result())
        result = summarize_contract_extras_dashboard(limit="abc")  # type: ignore[arg-type]
        self.assertEqual(result["requested_limit"], 20)

    def test_bool_limit_falls_back_to_default_20(self) -> None:
        ps.save_prediction("AVGO", "2026-04-11", None, None, _predict_result())
        result = summarize_contract_extras_dashboard(limit=True)  # type: ignore[arg-type]
        self.assertEqual(result["requested_limit"], 20)


class DashboardSymbolFilterTests(_IsolatedStoreTestCase):
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
        result = summarize_contract_extras_dashboard()
        self.assertEqual(result["symbol_filter"], "AVGO")
        self.assertEqual(result["records_scanned"], 3)

    def test_symbol_all_includes_every_symbol(self) -> None:
        self._seed_mixed()
        result = summarize_contract_extras_dashboard(symbol="ALL")
        self.assertEqual(result["symbol_filter"], "ALL")
        self.assertEqual(result["records_scanned"], 5)

    def test_symbol_none_is_treated_as_all(self) -> None:
        self._seed_mixed()
        result = summarize_contract_extras_dashboard(symbol=None)
        self.assertEqual(result["symbol_filter"], "ALL")
        self.assertEqual(result["records_scanned"], 5)

    def test_empty_symbol_falls_back_to_avgo(self) -> None:
        self._seed_mixed()
        result = summarize_contract_extras_dashboard(symbol="")
        self.assertEqual(result["symbol_filter"], "AVGO")
        self.assertEqual(result["records_scanned"], 3)

    def test_lowercase_and_whitespace_symbol_normalize(self) -> None:
        self._seed_mixed()
        result = summarize_contract_extras_dashboard(symbol="  nvda  ")
        self.assertEqual(result["symbol_filter"], "NVDA")
        self.assertEqual(result["records_scanned"], 2)

    def test_unknown_symbol_yields_no_records(self) -> None:
        self._seed_mixed()
        result = summarize_contract_extras_dashboard(symbol="TSLA")
        self.assertEqual(result["status"], "no_records")
        self.assertEqual(result["symbol_filter"], "TSLA")


# ── 8. read-only ───────────────────────────────────────────────────────────

class DashboardReadOnlyTests(_IsolatedStoreTestCase):
    def test_dashboard_does_not_mutate_db(self) -> None:
        for _ in range(3):
            ps.save_prediction("AVGO", "2026-04-11", None, None, _predict_result())
        with ps._get_conn() as conn:
            count_before = conn.execute(
                "SELECT COUNT(*) FROM prediction_log"
            ).fetchone()[0]
            rows_before = [
                dict(r) for r in conn.execute("SELECT * FROM prediction_log")
            ]

        summarize_contract_extras_dashboard()
        summarize_contract_extras_dashboard(limit=5)
        summarize_contract_extras_dashboard(symbol="ALL")

        with ps._get_conn() as conn:
            count_after = conn.execute(
                "SELECT COUNT(*) FROM prediction_log"
            ).fetchone()[0]
            rows_after = [
                dict(r) for r in conn.execute("SELECT * FROM prediction_log")
            ]
        self.assertEqual(count_before, count_after)
        self.assertEqual(rows_before, rows_after)


# ── 9. error path ──────────────────────────────────────────────────────────

class DashboardErrorPathTests(unittest.TestCase):
    def test_unreadable_db_path_returns_error_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            # Pass the directory itself as the db path → sqlite3.connect fails.
            result = summarize_contract_extras_dashboard(db_path=tmpdir)
        self.assertEqual(result["status"], "error")
        self.assertTrue(result["error"].startswith("db_read_failed"))


# ── 10. CLI ────────────────────────────────────────────────────────────────

class DashboardScriptArgTests(_IsolatedStoreTestCase):
    def _run(self, *extra: str) -> dict:
        script = ROOT / "scripts" / "dashboard_contract_extras.py"
        proc = subprocess.run(
            [sys.executable, str(script), "--db", str(ps.DB_PATH), *extra],
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(proc.stdout)

    def test_script_default_symbol_is_avgo(self) -> None:
        ps.save_prediction("AVGO", "2026-04-11", None, None, _predict_result())
        ps.save_prediction("NVDA", "2026-04-11", None, None,
                            _predict_result(symbol="NVDA"))
        result = self._run()
        self.assertEqual(result["symbol_filter"], "AVGO")
        self.assertEqual(result["records_scanned"], 1)

    def test_script_accepts_symbol_all(self) -> None:
        ps.save_prediction("AVGO", "2026-04-11", None, None, _predict_result())
        ps.save_prediction("NVDA", "2026-04-11", None, None,
                            _predict_result(symbol="NVDA"))
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
