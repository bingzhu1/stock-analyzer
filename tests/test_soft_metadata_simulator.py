"""Tests for services/soft_metadata_simulator.py (Step 2G-5)."""
from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import services.prediction_store as ps
import services.regime_diagnostics_dashboard as dashboard
from services.soft_metadata_simulator import (
    ACTIVE_SIGNAL_NAMES,
    DEFAULT_FINAL_TEST_CUTOFF,
    HOLDOUT_STATUS,
    METRICS_SOURCE,
    SCHEMA_VERSION,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
    SEVERITY_NONE,
    _R4_AVGO_MINUS_SOXX_THRESHOLD,
    _R4_POS20_THRESHOLD,
    _classify_severity,
    build_soft_metadata_baseline,
    simulate_soft_metadata,
)


# ── shared fixtures ──────────────────────────────────────────────────────

def _build_payload(
    *,
    final_direction: str = "偏多",
    confidence_level: str = "high",
    primary_score_raw: float | None = 1.5,
    peer_adjustment: str = "hold",
    soft_signal: str = "none",
    path_risk_level: str = "unknown",
    analysis_date: str = "2024-01-08",
) -> dict:
    return {
        "current_structure": {
            "symbol": "AVGO", "analysis_date": analysis_date,
            "prediction_for_date": "2024-01-09",
            "data_window_days": 20,
            "current_price": 100.0, "previous_close": 99.0,
            "volume": 1_000_000, "turnover": 1.0e8,
            "structure_label": "bullish", "short_summary": "",
        },
        "avgo_primary_projection": {
            "primary_direction": final_direction,
            "open_projection": "高开", "intraday_path_projection": "高走",
            "close_projection": "收涨", "five_state_projection": "小涨",
            "historical_sample_count": 0, "key_evidence": [],
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
                "conflicting_factors_count": 0, "conflicting_factors": [],
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
            "confidence_level": confidence_level, "confidence_reason": "",
            "extras": {
                "primary_score_raw": primary_score_raw,
                "primary_confidence_raw": confidence_level,
                "peer_confirm_count": 1, "peer_oppose_count": 0,
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
            "key_price_levels": {}, "final_one_sentence": "",
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
            "predicted_five_state": "小涨",
            "predicted_confidence": confidence_level,
            "review_ready_fields": [],
        },
    }


def _r4_baseline_dict() -> dict:
    """A representative baseline matching the main-DB R4 numbers."""
    return {
        "metrics_source": METRICS_SOURCE,
        "metrics_window": {
            "analysis_date_min": "2023-01-03",
            "analysis_date_max": "2024-08-02",
            "paired_total": 286, "db_snapshot_id": None,
        },
        "metrics_computed_at": "2026-05-04T00:00:00",
        "r4_overextension": {
            "samples": 36, "paired": 34,
            "accuracy": 0.324, "bias_gap": 0.676,
            "false_exclusion_rate": 0.3235, "net_benefit": 0.0219,
        },
        "bullish_high_pos20_residual": {
            "samples": 47, "paired": 47,
            "accuracy": 0.489, "bias_gap": 0.511,
            "false_exclusion_rate": 0.489, "net_benefit": 0.005,
        },
        "holdout_status": "FAIL",
        "warnings": [],
    }


# ── Schema / summary tests ──────────────────────────────────────────────

class SchemaShapeTests(unittest.TestCase):
    def test_empty_payload_no_signals_max_severity_none(self) -> None:
        out = simulate_soft_metadata({})
        self.assertEqual(out["schema_version"], SCHEMA_VERSION)
        self.assertEqual(out["signals"], [])
        self.assertEqual(out["summary"]["max_severity"], SEVERITY_NONE)
        self.assertFalse(out["summary"]["hard_exclusion_allowed"])
        self.assertEqual(out["summary"]["signal_count"], 0)
        self.assertIsNone(out["summary"]["primary_signal"])

    def test_schema_version_constant(self) -> None:
        out = simulate_soft_metadata({})
        self.assertEqual(out["schema_version"], "soft_metadata.v1")
        self.assertEqual(out["metrics_source"], "regime_diagnostics_dashboard_v1")

    def test_signal_count_matches_signals_length(self) -> None:
        payload = _build_payload(
            confidence_level="high", primary_score_raw=2.5,
        )
        out = simulate_soft_metadata(
            payload,
            regime_features={"pos20": 0.81, "avgo_minus_soxx_20d": 7.3},
            baseline=_r4_baseline_dict(),
        )
        self.assertEqual(out["summary"]["signal_count"], len(out["signals"]))

    def test_severity_only_low_or_medium(self) -> None:
        payload = _build_payload(confidence_level="high")
        out = simulate_soft_metadata(
            payload,
            regime_features={"pos20": 0.81, "avgo_minus_soxx_20d": 7.3},
            baseline=_r4_baseline_dict(),
        )
        for s in out["signals"]:
            self.assertIn(s["severity"], (SEVERITY_LOW, SEVERITY_MEDIUM))
            self.assertNotIn(s["severity"], ("high", "hard"))

    def test_signals_capped_at_three(self) -> None:
        payload = _build_payload(confidence_level="high")
        out = simulate_soft_metadata(
            payload,
            regime_features={"pos20": 0.81, "avgo_minus_soxx_20d": 7.3},
            baseline=_r4_baseline_dict(),
        )
        self.assertLessEqual(len(out["signals"]), 3)

    def test_hard_exclusion_allowed_invariant_on_arbitrary_input(self) -> None:
        for kwargs in (
            {},
            {"regime_features": {"pos20": 0.99, "avgo_minus_soxx_20d": 99.0}},
            {"baseline": None},
            {"baseline": _r4_baseline_dict()},
        ):
            payload = _build_payload()
            out = simulate_soft_metadata(payload, **kwargs)
            self.assertFalse(out["summary"]["hard_exclusion_allowed"])


# ── R4 trigger tests ─────────────────────────────────────────────────────

class R4TriggerTests(unittest.TestCase):
    BASELINE = _r4_baseline_dict()
    R4_FEATURES = {"pos20": 0.81, "avgo_minus_soxx_20d": 7.3}

    def test_r4_triggers_with_high_confidence(self) -> None:
        payload = _build_payload(confidence_level="high")
        out = simulate_soft_metadata(
            payload, regime_features=self.R4_FEATURES, baseline=self.BASELINE,
        )
        names = [s["name"] for s in out["signals"]]
        self.assertEqual(names, ["r4_overextension"])

    def test_r4_does_not_trigger_when_pos20_below_threshold(self) -> None:
        payload = _build_payload(confidence_level="high")
        out = simulate_soft_metadata(
            payload,
            regime_features={"pos20": 0.50, "avgo_minus_soxx_20d": 7.3},
            baseline=self.BASELINE,
        )
        self.assertNotIn(
            "r4_overextension", [s["name"] for s in out["signals"]],
        )

    def test_r4_does_not_trigger_when_diff_below_threshold(self) -> None:
        payload = _build_payload(confidence_level="high")
        out = simulate_soft_metadata(
            payload,
            regime_features={"pos20": 0.81, "avgo_minus_soxx_20d": 3.0},
            baseline=self.BASELINE,
        )
        self.assertNotIn(
            "r4_overextension", [s["name"] for s in out["signals"]],
        )

    def test_r4_does_not_trigger_when_direction_not_bullish(self) -> None:
        payload = _build_payload(
            final_direction="偏空", confidence_level="high",
        )
        out = simulate_soft_metadata(
            payload, regime_features=self.R4_FEATURES, baseline=self.BASELINE,
        )
        self.assertEqual(out["signals"], [])

    def test_r4_or_branch_confidence_high_only(self) -> None:
        payload = _build_payload(
            confidence_level="high", primary_score_raw=0.5,
        )
        out = simulate_soft_metadata(
            payload, regime_features=self.R4_FEATURES, baseline=self.BASELINE,
        )
        self.assertEqual(
            out["signals"][0]["trigger_context"]["matched_or_branch"],
            "confidence_high",
        )

    def test_r4_or_branch_primary_score_only(self) -> None:
        payload = _build_payload(
            confidence_level="medium", primary_score_raw=2.5,
        )
        out = simulate_soft_metadata(
            payload, regime_features=self.R4_FEATURES, baseline=self.BASELINE,
        )
        self.assertEqual(
            out["signals"][0]["trigger_context"]["matched_or_branch"],
            "primary_score_raw_gt_2",
        )

    def test_r4_or_branch_both(self) -> None:
        payload = _build_payload(
            confidence_level="high", primary_score_raw=2.5,
        )
        out = simulate_soft_metadata(
            payload, regime_features=self.R4_FEATURES, baseline=self.BASELINE,
        )
        self.assertEqual(
            out["signals"][0]["trigger_context"]["matched_or_branch"],
            "both",
        )

    def test_peer_adjustment_becomes_trigger_context_subtype(self) -> None:
        for label in ("upgrade", "hold", "downgrade"):
            payload = _build_payload(
                confidence_level="high", peer_adjustment=label,
            )
            out = simulate_soft_metadata(
                payload, regime_features=self.R4_FEATURES,
                baseline=self.BASELINE,
            )
            self.assertEqual(
                out["signals"][0]["trigger_context"]["peer_subtype"], label,
            )

    def test_peer_adjustment_unknown_falls_back(self) -> None:
        payload = _build_payload(confidence_level="high")
        payload["peer_confirmation_adjustment"]["peer_adjustment"] = "weird"
        out = simulate_soft_metadata(
            payload, regime_features=self.R4_FEATURES, baseline=self.BASELINE,
        )
        self.assertEqual(
            out["signals"][0]["trigger_context"]["peer_subtype"], "unknown",
        )

    def test_hard_forbidden_fields_present(self) -> None:
        payload = _build_payload(confidence_level="high")
        out = simulate_soft_metadata(
            payload, regime_features=self.R4_FEATURES, baseline=self.BASELINE,
        )
        sig = out["signals"][0]
        self.assertEqual(
            sig["hard_forbidden_primary_reason"],
            "false_exclusion_rate_too_high",
        )
        self.assertIsInstance(sig["hard_forbidden_breakdown"], list)
        self.assertTrue(any(
            "false_exclusion_rate=" in s
            for s in sig["hard_forbidden_breakdown"]
        ))
        self.assertTrue(any(
            "net_benefit=" in s
            for s in sig["hard_forbidden_breakdown"]
        ))
        self.assertIn(
            "anti_false_exclusion_not_connected",
            sig["hard_forbidden_breakdown"],
        )
        self.assertEqual(sig["holdout_status"], HOLDOUT_STATUS)


# ── Residual trigger tests ──────────────────────────────────────────────

class ResidualTriggerTests(unittest.TestCase):
    BASELINE = _r4_baseline_dict()

    def test_residual_triggers_when_r4_does_not(self) -> None:
        payload = _build_payload(confidence_level="high")
        # pos20 high, but SOXX diff below R4 → residual instead of R4
        out = simulate_soft_metadata(
            payload,
            regime_features={"pos20": 0.81, "avgo_minus_soxx_20d": 2.0},
            baseline=self.BASELINE,
        )
        names = [s["name"] for s in out["signals"]]
        self.assertEqual(names, ["bullish_high_pos20_residual"])

    def test_residual_does_not_emit_when_r4_emits(self) -> None:
        payload = _build_payload(confidence_level="high")
        out = simulate_soft_metadata(
            payload,
            regime_features={"pos20": 0.81, "avgo_minus_soxx_20d": 7.3},
            baseline=self.BASELINE,
        )
        names = [s["name"] for s in out["signals"]]
        self.assertEqual(names, ["r4_overextension"])
        self.assertNotIn("bullish_high_pos20_residual", names)

    def test_residual_metrics_missing_from_baseline_emits_warning(self) -> None:
        baseline = deepcopy(self.BASELINE)
        baseline["bullish_high_pos20_residual"] = None  # missing
        payload = _build_payload(confidence_level="high")
        out = simulate_soft_metadata(
            payload,
            regime_features={"pos20": 0.81, "avgo_minus_soxx_20d": 2.0},
            baseline=baseline,
        )
        self.assertIn(
            "missing_baseline_metrics: bullish_high_pos20_residual",
            out["summary"]["warnings"],
        )
        self.assertEqual(out["signals"][0]["historical_metrics_in_sample"], {})


# ── Removed candidate enforcement ────────────────────────────────────────

class RemovedCandidateEnforcementTests(unittest.TestCase):
    BASELINE = _r4_baseline_dict()

    def test_peer_weaken_never_emits_signal(self) -> None:
        payload = _build_payload(
            confidence_level="medium", soft_signal="peer_weaken",
        )
        out = simulate_soft_metadata(
            payload,
            regime_features={"pos20": 0.30, "avgo_minus_soxx_20d": -1.0},
            baseline=self.BASELINE,
        )
        for s in out["signals"]:
            self.assertNotIn(s["name"], (
                "peer_weaken_metadata_only",
                "high_path_risk_metadata_only",
                "bullish_peer_upgrade_overextension",
                "peer_path_lower_bullish",
            ))

    def test_high_path_risk_never_emits_signal(self) -> None:
        payload = _build_payload(
            confidence_level="medium", soft_signal="high_path_risk",
            path_risk_level="high",
        )
        out = simulate_soft_metadata(
            payload,
            regime_features={"pos20": 0.30, "avgo_minus_soxx_20d": -1.0},
            baseline=self.BASELINE,
        )
        for s in out["signals"]:
            self.assertNotIn("path_risk", s["name"])
            self.assertNotIn("peer_weaken", s["name"])

    def test_peer_upgrade_alone_does_not_emit_top_level_signal(self) -> None:
        # No R4 trigger, no bullish_high_pos20 trigger; just peer_upgrade
        payload = _build_payload(
            confidence_level="medium", peer_adjustment="upgrade",
        )
        out = simulate_soft_metadata(
            payload,
            regime_features={"pos20": 0.30, "avgo_minus_soxx_20d": -1.0},
            baseline=self.BASELINE,
        )
        for s in out["signals"]:
            self.assertNotEqual(s["name"], "bullish_peer_upgrade_overextension")

    def test_signal_names_only_from_active_enum(self) -> None:
        for kwargs in (
            {"regime_features": {"pos20": 0.81, "avgo_minus_soxx_20d": 7.3}},
            {"regime_features": {"pos20": 0.81, "avgo_minus_soxx_20d": 2.0}},
        ):
            payload = _build_payload(confidence_level="high")
            out = simulate_soft_metadata(
                payload, baseline=self.BASELINE, **kwargs,
            )
            for s in out["signals"]:
                self.assertIn(s["name"], ACTIVE_SIGNAL_NAMES)


# ── Severity classification ──────────────────────────────────────────────

class SeverityClassificationTests(unittest.TestCase):
    def test_strict_lt_acc_boundary_is_low(self) -> None:
        # acc = 0.45 exactly, gap = 0.50 exactly → low (strict <, >)
        self.assertEqual(
            _classify_severity({"accuracy": 0.45, "bias_gap": 0.50}),
            SEVERITY_LOW,
        )

    def test_strict_gt_gap_boundary_is_low(self) -> None:
        # gap = 0.50 exactly → low (we need > 0.50 for medium)
        self.assertEqual(
            _classify_severity({"accuracy": 0.50, "bias_gap": 0.50}),
            SEVERITY_LOW,
        )

    def test_acc_below_boundary_is_medium(self) -> None:
        self.assertEqual(
            _classify_severity({"accuracy": 0.44, "bias_gap": 0.10}),
            SEVERITY_MEDIUM,
        )

    def test_gap_above_boundary_is_medium(self) -> None:
        self.assertEqual(
            _classify_severity({"accuracy": 0.50, "bias_gap": 0.51}),
            SEVERITY_MEDIUM,
        )

    def test_r4_implementation_metrics_classify_medium(self) -> None:
        # Real R4 numbers from main DB
        self.assertEqual(
            _classify_severity({"accuracy": 0.324, "bias_gap": 0.676}),
            SEVERITY_MEDIUM,
        )

    def test_missing_metrics_default_to_medium(self) -> None:
        self.assertEqual(_classify_severity(None), SEVERITY_MEDIUM)
        self.assertEqual(_classify_severity({}), SEVERITY_MEDIUM)
        self.assertEqual(
            _classify_severity({"accuracy": None, "bias_gap": 0.5}),
            SEVERITY_MEDIUM,
        )


# ── Baseline handling ──────────────────────────────────────────────────

class BaselineHandlingTests(unittest.TestCase):
    def test_baseline_none_emits_warning_but_does_not_crash(self) -> None:
        payload = _build_payload(confidence_level="high")
        out = simulate_soft_metadata(
            payload,
            regime_features={"pos20": 0.81, "avgo_minus_soxx_20d": 7.3},
            baseline=None,
        )
        self.assertIn("missing_baseline", out["summary"]["warnings"])
        # signal still emits, but historical_metrics_in_sample is {}
        self.assertEqual(out["signals"][0]["name"], "r4_overextension")
        self.assertEqual(
            out["signals"][0]["historical_metrics_in_sample"], {},
        )

    def test_metrics_window_passes_through_from_baseline(self) -> None:
        baseline = _r4_baseline_dict()
        out = simulate_soft_metadata(
            _build_payload(confidence_level="high"),
            regime_features={"pos20": 0.81, "avgo_minus_soxx_20d": 7.3},
            baseline=baseline,
        )
        self.assertEqual(
            out["metrics_window"]["analysis_date_min"], "2023-01-03",
        )
        self.assertEqual(
            out["metrics_window"]["analysis_date_max"], "2024-08-02",
        )
        self.assertEqual(out["metrics_window"]["paired_total"], 286)
        self.assertEqual(
            out["metrics_computed_at"], "2026-05-04T00:00:00",
        )


# ── R4 threshold constants are same source as dashboard ────────────────

class ThresholdConstantSourceTests(unittest.TestCase):
    def test_r4_avgo_minus_soxx_threshold_is_dashboard_constant(self) -> None:
        self.assertIs(
            _R4_AVGO_MINUS_SOXX_THRESHOLD,
            dashboard._R4_AVGO_MINUS_SOXX_THRESHOLD,
        )

    def test_r4_pos20_threshold_is_dashboard_constant(self) -> None:
        self.assertIs(_R4_POS20_THRESHOLD, dashboard._R4_POS20_THRESHOLD)

    def test_simulator_has_no_local_numeric_r4_literals(self) -> None:
        # Grep for literal 5.0 / 0.62 in the simulator module's source.
        # (These are R4 thresholds; allowed to appear only via the imports.)
        import services.soft_metadata_simulator as mod
        src = Path(mod.__file__).read_text(encoding="utf-8")
        # Every appearance of these literals should only be inside an
        # import statement; we check by grepping with explicit context.
        self.assertNotIn(" 5.0 ", src)
        self.assertNotIn("=5.0", src)
        self.assertNotIn(" 0.62 ", src)
        self.assertNotIn("=0.62", src)


# ── 2026 final test cutoff ───────────────────────────────────────────────

class FinalTestCutoffTests(unittest.TestCase):
    def test_analysis_date_at_cutoff_refuses_signals(self) -> None:
        payload = _build_payload(
            confidence_level="high", analysis_date="2026-01-01",
        )
        out = simulate_soft_metadata(
            payload,
            regime_features={"pos20": 0.81, "avgo_minus_soxx_20d": 7.3},
            baseline=_r4_baseline_dict(),
        )
        self.assertEqual(out["signals"], [])
        self.assertIn(
            "final_test_range_refusal", out["summary"]["warnings"],
        )

    def test_analysis_date_after_cutoff_refuses_signals(self) -> None:
        payload = _build_payload(
            confidence_level="high", analysis_date="2026-03-15",
        )
        out = simulate_soft_metadata(
            payload,
            regime_features={"pos20": 0.81, "avgo_minus_soxx_20d": 7.3},
            baseline=_r4_baseline_dict(),
        )
        self.assertEqual(out["signals"], [])

    def test_analysis_date_before_cutoff_does_not_refuse(self) -> None:
        payload = _build_payload(
            confidence_level="high", analysis_date="2025-12-31",
        )
        out = simulate_soft_metadata(
            payload,
            regime_features={"pos20": 0.81, "avgo_minus_soxx_20d": 7.3},
            baseline=_r4_baseline_dict(),
        )
        self.assertNotEqual(out["signals"], [])
        self.assertNotIn(
            "final_test_range_refusal", out["summary"]["warnings"],
        )

    def test_analysis_date_override_takes_precedence(self) -> None:
        payload = _build_payload(
            confidence_level="high", analysis_date="2024-01-08",
        )
        out = simulate_soft_metadata(
            payload,
            regime_features={"pos20": 0.81, "avgo_minus_soxx_20d": 7.3},
            baseline=_r4_baseline_dict(),
            analysis_date="2026-06-01",  # override
        )
        self.assertEqual(out["signals"], [])
        self.assertIn(
            "final_test_range_refusal", out["summary"]["warnings"],
        )

    def test_default_cutoff_constant(self) -> None:
        self.assertEqual(DEFAULT_FINAL_TEST_CUTOFF, "2026-01-01")


# ── Missing regime features ─────────────────────────────────────────────

class MissingRegimeFeaturesTests(unittest.TestCase):
    def test_no_regime_features_returns_no_signals_and_warning(self) -> None:
        payload = _build_payload(confidence_level="high")
        out = simulate_soft_metadata(payload, baseline=_r4_baseline_dict())
        self.assertEqual(out["signals"], [])
        self.assertTrue(any(
            "missing_regime_features" in w
            for w in out["summary"]["warnings"]
        ))

    def test_partial_regime_features_pos20_only(self) -> None:
        payload = _build_payload(confidence_level="high")
        out = simulate_soft_metadata(
            payload,
            regime_features={"pos20": 0.81},
            baseline=_r4_baseline_dict(),
        )
        self.assertEqual(out["signals"], [])
        self.assertTrue(any(
            "avgo_minus_soxx_20d" in w
            for w in out["summary"]["warnings"]
        ))


# ── Read-only / no DB writes ───────────────────────────────────────────

class _IsolatedStoreTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        ps.DB_PATH = Path(self._tmpdir.name) / "test.db"
        ps.init_db()
        self.coded_dir = Path(self._tmpdir.name) / "coded_data"
        self.coded_dir.mkdir()

    def tearDown(self) -> None:
        self._tmpdir.cleanup()


class ReadOnlyTests(_IsolatedStoreTestCase):
    def test_simulate_does_not_touch_db(self) -> None:
        # Write a few replay rows
        for i in range(3):
            ps.save_prediction(
                symbol="AVGO",
                prediction_for_date=f"2024-01-{9+i:02d}",
                scan_result=None, research_result=None,
                predict_result={
                    "symbol": "AVGO", "final_bias": "bullish",
                    "final_confidence": "high",
                    "scan_bias": "bullish", "scan_confidence": "high",
                    "pred_open": "高开", "pred_path": "高开高走",
                    "pred_close": "收涨", "prediction_summary": "",
                    "supporting_factors": [], "conflicting_factors": [],
                },
                snapshot_id=f"replay_AVGO_2024-01-{8+i:02d}",
                analysis_date_override=f"2024-01-{8+i:02d}",
            )
        with ps._get_conn() as conn:
            n_pred_before = conn.execute(
                "SELECT COUNT(*) FROM prediction_log"
            ).fetchone()[0]
            n_out_before = conn.execute(
                "SELECT COUNT(*) FROM outcome_log"
            ).fetchone()[0]

        for _ in range(5):
            simulate_soft_metadata(
                _build_payload(confidence_level="high"),
                regime_features={"pos20": 0.81, "avgo_minus_soxx_20d": 7.3},
                baseline=_r4_baseline_dict(),
            )

        with ps._get_conn() as conn:
            n_pred_after = conn.execute(
                "SELECT COUNT(*) FROM prediction_log"
            ).fetchone()[0]
            n_out_after = conn.execute(
                "SELECT COUNT(*) FROM outcome_log"
            ).fetchone()[0]
        self.assertEqual(n_pred_before, n_pred_after)
        self.assertEqual(n_out_before, n_out_after)


class NoForbiddenImportsTests(unittest.TestCase):
    def test_simulator_module_does_not_import_network_or_trading(self) -> None:
        # Inspect only actual import statements (parsed via ast), not the
        # docstring — Step 2G-4.5 prose intentionally names the forbidden
        # modules in narrative text, but they must never show up as real
        # module imports.
        import ast
        import services.soft_metadata_simulator as mod
        tree = ast.parse(Path(mod.__file__).read_text(encoding="utf-8"))
        forbidden_modules = {
            "yfinance", "requests", "longbridge", "broker", "paper_trade",
            "services.confidence_engine", "services.contradiction_engine",
            "services.risk_model",
            "confidence_engine", "contradiction_engine", "risk_model",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn(alias.name, forbidden_modules)
            elif isinstance(node, ast.ImportFrom):
                self.assertNotIn(node.module, forbidden_modules)


# ── build_soft_metadata_baseline tests ─────────────────────────────────

def _save_replay_with_outcome(
    *, analysis_date: str, prediction_for_date: str,
    confidence_level: str, direction_correct: int | None,
    actual_close: float = 105.0, actual_prev_close: float = 100.0,
) -> str:
    payload = _build_payload(
        analysis_date=analysis_date,
        confidence_level=confidence_level,
    )
    pid = ps.save_prediction(
        symbol="AVGO",
        prediction_for_date=prediction_for_date,
        scan_result=None, research_result=None,
        predict_result={
            "symbol": "AVGO", "final_bias": "bullish",
            "final_confidence": confidence_level,
            "scan_bias": "bullish", "scan_confidence": confidence_level,
            "pred_open": "高开", "pred_path": "高开高走",
            "pred_close": "收涨", "prediction_summary": "",
            "supporting_factors": [], "conflicting_factors": [],
        },
        snapshot_id=f"replay_AVGO_{analysis_date}",
        contract_payload=payload,
        analysis_date_override=analysis_date,
    )
    if direction_correct is not None:
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


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=["Date", "Open", "High", "Low", "Close"]
        )
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


class BuildBaselineTests(_IsolatedStoreTestCase):
    def test_no_records_returns_empty_baseline_with_warning(self) -> None:
        out = build_soft_metadata_baseline(coded_data_dir=self.coded_dir)
        self.assertEqual(out["metrics_source"], METRICS_SOURCE)
        self.assertIsNone(out["r4_overextension"])
        self.assertIsNone(out["bullish_high_pos20_residual"])
        self.assertIn("baseline_no_records", out["warnings"])

    def test_missing_csv_returns_baseline_without_residual(self) -> None:
        # Save a replay row but no CSV
        _save_replay_with_outcome(
            analysis_date="2024-01-08",
            prediction_for_date="2024-01-09",
            confidence_level="high", direction_correct=1,
        )
        out = build_soft_metadata_baseline(coded_data_dir=self.coded_dir)
        # No coded CSV → residual cannot be computed → warning
        self.assertIsNone(out["bullish_high_pos20_residual"])
        self.assertTrue(any(
            "coded_data_csv_missing" in w for w in out["warnings"]
        ))

    def test_baseline_uses_dashboard_holdout_status(self) -> None:
        out = build_soft_metadata_baseline(coded_data_dir=self.coded_dir)
        self.assertEqual(out["holdout_status"], HOLDOUT_STATUS)


# ── CLI smoke tests ────────────────────────────────────────────────────

class CliSmokeTests(_IsolatedStoreTestCase):
    SCRIPT = ROOT / "scripts" / "soft_metadata_simulator.py"

    def test_cli_baseline_only_smoke(self) -> None:
        proc = subprocess.run(
            [
                sys.executable, str(self.SCRIPT),
                "--db", str(ps.DB_PATH),
                "--symbol", "AVGO", "--limit", "10",
                "--coded-data-dir", str(self.coded_dir),
            ],
            capture_output=True, text=True, check=True,
        )
        result = json.loads(proc.stdout)
        self.assertEqual(result["mode"], "baseline_only")
        self.assertIn("baseline", result)
        self.assertEqual(
            result["baseline"]["metrics_source"], METRICS_SOURCE,
        )

    def test_cli_payload_json_smoke(self) -> None:
        payload = _build_payload(confidence_level="high")
        proc = subprocess.run(
            [
                sys.executable, str(self.SCRIPT),
                "--db", str(ps.DB_PATH),
                "--symbol", "AVGO", "--limit", "10",
                "--coded-data-dir", str(self.coded_dir),
                "--payload-json", json.dumps(payload),
                "--no-baseline",
            ],
            capture_output=True, text=True, check=True,
        )
        result = json.loads(proc.stdout)
        self.assertEqual(result["schema_version"], SCHEMA_VERSION)
        # Without coded_data CSV, regime_features can't be computed →
        # signals=[] + warning
        self.assertEqual(result["signals"], [])
        self.assertTrue(any(
            "missing" in w for w in result["summary"]["warnings"]
        ))


if __name__ == "__main__":
    unittest.main()
