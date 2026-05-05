"""Step 3R-4.2 — read-only 4-fold validation helper tests.

Covers:
  - schema (output keys / default windows / fold_count)
  - W4 manifest gate (5 fail paths + happy path + require_w4_manifest=False)
  - 6 metrics formula (FER / NB / survival / variance / collapse / sample size)
  - overall_status (pass / fail / error)
  - worst-window priority
  - safety: 2026 refusal, missing fields, input immutability,
    no DB / prediction_store / yfinance / requests / streamlit / trading
  - acceptance: R4-like fixture fails 4-fold; pooled-pass-but-worst-fail fails
"""
from __future__ import annotations

import ast
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.regime_validation_helper import (
    DEFAULT_FINAL_TEST_CUTOFF,
    DEFAULT_WINDOWS,
    SCHEMA_VERSION,
    build_regime_validation_report,
)


# ── fixtures ─────────────────────────────────────────────────────────────


_VALID_W4_MANIFEST = {
    "schema_version": "w4_replay_manifest.v1",
    "replay_window": {"start": "2024-08-03", "end": "2025-12-31"},
    "final_test_cutoff": "2026-01-01",
    "final_test_touched": False,
    "records_generated": 353,
    "paired_outcomes": 353,
    "status": "ok",
    "warnings": [],
}


def _write_manifest(tmp: Path, payload: dict[str, Any] | None = None) -> str:
    target = tmp / "validation_ready_manifest.json"
    target.write_text(
        json.dumps(payload if payload is not None else _VALID_W4_MANIFEST),
        encoding="utf-8",
    )
    return str(target)


def _record(
    *,
    analysis_date: str,
    candidate_triggered: bool,
    prediction_correct: bool,
    baseline_correct: bool | None = None,
    exclusion_would_block: bool | None = None,
    survival_case: bool | None = None,
) -> dict[str, Any]:
    return {
        "analysis_date": analysis_date,
        "candidate_triggered": candidate_triggered,
        "prediction_correct": prediction_correct,
        "baseline_correct": (
            prediction_correct if baseline_correct is None else baseline_correct
        ),
        "exclusion_would_block": (
            candidate_triggered
            if exclusion_would_block is None
            else exclusion_would_block
        ),
        "survival_case": (
            (candidate_triggered and prediction_correct)
            if survival_case is None
            else survival_case
        ),
    }


def _balanced_window_records(
    *,
    window_dates: list[str],
    triggered_per_date: int,
    correct_when_triggered: int,
    untriggered_per_date: int = 1,
) -> list[dict[str, Any]]:
    """Generate records for a window with deterministic FER / paired counts.

    triggered_per_date = paired with candidate_triggered=True
    correct_when_triggered = those that are prediction_correct=True (FER)
    untriggered_per_date = paired with candidate_triggered=False (baseline)
    """
    out: list[dict[str, Any]] = []
    for d in window_dates:
        for i in range(triggered_per_date):
            correct = i < correct_when_triggered
            out.append(
                _record(
                    analysis_date=d,
                    candidate_triggered=True,
                    prediction_correct=correct,
                    baseline_correct=correct,
                )
            )
        for i in range(untriggered_per_date):
            out.append(
                _record(
                    analysis_date=d,
                    candidate_triggered=False,
                    prediction_correct=True,
                    baseline_correct=False,
                )
            )
    return out


def _make_records_passing_all_gates() -> list[dict[str, Any]]:
    """Records that should make every gate pass.

    Each window: 25 triggered (1 correct = FER 0.04) + 30 untriggered
    where candidate cleanly beats baseline (NB > +0.05).
    """
    pass_records: list[dict[str, Any]] = []
    window_dates = {
        "W1": ["2023-03-01"] * 25 + ["2023-04-01"] * 30,
        "W2": ["2023-10-01"] * 25 + ["2023-11-01"] * 30,
        "W3": ["2024-04-01"] * 25 + ["2024-05-01"] * 30,
        "W4": ["2024-09-01"] * 25 + ["2024-10-01"] * 30,
    }
    for _name, dates in window_dates.items():
        # 25 triggered: ALL wrong (FER = 0, no survival cases → preservation
        # vacuously 1.0).
        for d in dates[:25]:
            pass_records.append(
                _record(
                    analysis_date=d,
                    candidate_triggered=True,
                    prediction_correct=False,
                    baseline_correct=False,
                )
            )
        # 30 untriggered: candidate_correct=True, baseline_correct=False
        # → after excluding 25 blocked, candidate_acc = 30/30 = 1.0;
        # baseline_acc = 0/55 = 0.0; NB = 1.0 (well above gate).
        for d in dates[25:]:
            pass_records.append(
                _record(
                    analysis_date=d,
                    candidate_triggered=False,
                    prediction_correct=True,
                    baseline_correct=False,
                )
            )
    return pass_records


def _make_r4_like_records() -> list[dict[str, Any]]:
    """R4-like fixture: high FER, low NB, large variance — must FAIL."""
    out: list[dict[str, Any]] = []
    # W1: mild — 25 triggered, fer 0.20 → still > GATE 0.10 → fail
    for i in range(25):
        out.append(
            _record(
                analysis_date="2023-04-01",
                candidate_triggered=True,
                prediction_correct=i < 5,
                baseline_correct=False,
            )
        )
    # W2: severe — 25 triggered, fer 0.40 (10/25) → triggers collapse > 0.20
    for i in range(25):
        out.append(
            _record(
                analysis_date="2023-12-15",
                candidate_triggered=True,
                prediction_correct=i < 10,
                baseline_correct=False,
            )
        )
    # W3: mild — 25 triggered, fer 0.16
    for i in range(25):
        out.append(
            _record(
                analysis_date="2024-04-15",
                candidate_triggered=True,
                prediction_correct=i < 4,
                baseline_correct=False,
            )
        )
    # W4: also bad — 25 triggered, fer 0.32
    for i in range(25):
        out.append(
            _record(
                analysis_date="2024-10-10",
                candidate_triggered=True,
                prediction_correct=i < 8,
                baseline_correct=False,
            )
        )
    return out


# ── 1. schema ────────────────────────────────────────────────────────────


class OutputSchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.manifest = _write_manifest(Path(self.tmp.name))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_output_keys_present(self) -> None:
        report = build_regime_validation_report(
            [],
            candidate_name="empty_v1",
            w4_manifest_path=self.manifest,
        )
        for key in (
            "schema_version",
            "candidate_name",
            "candidate_kind",
            "fold_count",
            "windows",
            "per_window_metrics",
            "pooled_metrics",
            "worst_window",
            "worst_window_metrics",
            "cross_window_variance",
            "leave_one_window_out",
            "gate_status",
            "overall_status",
            "final_test_refusal",
            "data_cutoff_used",
            "warnings",
        ):
            self.assertIn(key, report)
        self.assertEqual(report["schema_version"], "regime_validation_report.v1")
        self.assertEqual(report["schema_version"], SCHEMA_VERSION)

    def test_default_windows_are_w1_w4(self) -> None:
        report = build_regime_validation_report(
            [],
            candidate_name="x",
            w4_manifest_path=self.manifest,
        )
        self.assertEqual(set(report["windows"].keys()), {"W1", "W2", "W3", "W4"})
        self.assertEqual(DEFAULT_WINDOWS["W1"]["start"], "2023-01-03")
        self.assertEqual(DEFAULT_WINDOWS["W4"]["end"], "2025-12-31")

    def test_fold_count_is_4(self) -> None:
        report = build_regime_validation_report(
            [],
            candidate_name="x",
            w4_manifest_path=self.manifest,
        )
        self.assertEqual(report["fold_count"], 4)

    def test_overall_status_only_three_values(self) -> None:
        report = build_regime_validation_report(
            [],
            candidate_name="x",
            w4_manifest_path=self.manifest,
        )
        self.assertIn(report["overall_status"], {"pass", "fail", "error"})
        self.assertNotIn(report["overall_status"], {"partial"})


# ── 2. W4 manifest gate ──────────────────────────────────────────────────


class W4ManifestGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_valid_manifest_passes_gate(self) -> None:
        path = _write_manifest(Path(self.tmp.name))
        report = build_regime_validation_report(
            [],
            candidate_name="x",
            w4_manifest_path=path,
        )
        # Empty records → metrics fail gates → overall fail (not error)
        # But manifest gate itself is passed (warnings should not include
        # any w4_* failure markers).
        manifest_failures = [
            w for w in report["warnings"] if w.startswith("w4_")
        ]
        self.assertEqual(manifest_failures, [])

    def test_final_test_touched_true_returns_error(self) -> None:
        bad = dict(_VALID_W4_MANIFEST)
        bad["final_test_touched"] = True
        path = _write_manifest(Path(self.tmp.name), bad)
        report = build_regime_validation_report(
            [],
            candidate_name="x",
            w4_manifest_path=path,
        )
        self.assertEqual(report["overall_status"], "error")
        self.assertTrue(report["final_test_refusal"])
        self.assertIn(
            "w4_final_test_touched_true_report_void", report["warnings"]
        )

    def test_wrong_w4_start_returns_error(self) -> None:
        bad = json.loads(json.dumps(_VALID_W4_MANIFEST))
        bad["replay_window"]["start"] = "2024-09-01"
        path = _write_manifest(Path(self.tmp.name), bad)
        report = build_regime_validation_report(
            [],
            candidate_name="x",
            w4_manifest_path=path,
        )
        self.assertEqual(report["overall_status"], "error")
        self.assertIn("w4_replay_window_start_mismatch", report["warnings"])

    def test_wrong_w4_end_returns_error(self) -> None:
        bad = json.loads(json.dumps(_VALID_W4_MANIFEST))
        bad["replay_window"]["end"] = "2025-06-30"
        path = _write_manifest(Path(self.tmp.name), bad)
        report = build_regime_validation_report(
            [],
            candidate_name="x",
            w4_manifest_path=path,
        )
        self.assertEqual(report["overall_status"], "error")
        self.assertIn("w4_replay_window_end_mismatch", report["warnings"])

    def test_paired_below_minimum_returns_error(self) -> None:
        bad = dict(_VALID_W4_MANIFEST)
        bad["paired_outcomes"] = 5
        path = _write_manifest(Path(self.tmp.name), bad)
        report = build_regime_validation_report(
            [],
            candidate_name="x",
            w4_manifest_path=path,
        )
        self.assertEqual(report["overall_status"], "error")
        self.assertIn("w4_paired_below_minimum", report["warnings"])

    def test_status_not_ok_returns_error(self) -> None:
        bad = dict(_VALID_W4_MANIFEST)
        bad["status"] = "error"
        path = _write_manifest(Path(self.tmp.name), bad)
        report = build_regime_validation_report(
            [],
            candidate_name="x",
            w4_manifest_path=path,
        )
        self.assertEqual(report["overall_status"], "error")
        self.assertIn("w4_manifest_status_not_ok", report["warnings"])

    def test_schema_version_mismatch_returns_error(self) -> None:
        bad = dict(_VALID_W4_MANIFEST)
        bad["schema_version"] = "w4_replay_manifest.v0"
        path = _write_manifest(Path(self.tmp.name), bad)
        report = build_regime_validation_report(
            [],
            candidate_name="x",
            w4_manifest_path=path,
        )
        self.assertEqual(report["overall_status"], "error")
        self.assertIn("w4_manifest_schema_mismatch", report["warnings"])

    def test_cutoff_mismatch_returns_error(self) -> None:
        bad = dict(_VALID_W4_MANIFEST)
        bad["final_test_cutoff"] = "2025-12-01"
        path = _write_manifest(Path(self.tmp.name), bad)
        report = build_regime_validation_report(
            [],
            candidate_name="x",
            w4_manifest_path=path,
        )
        self.assertEqual(report["overall_status"], "error")
        self.assertIn("w4_final_test_cutoff_mismatch", report["warnings"])

    def test_missing_path_returns_error_when_required(self) -> None:
        report = build_regime_validation_report(
            [],
            candidate_name="x",
            w4_manifest_path=None,
            require_w4_manifest=True,
        )
        self.assertEqual(report["overall_status"], "error")
        self.assertIn("w4_manifest_path_missing", report["warnings"])

    def test_require_w4_false_skips_gate(self) -> None:
        report = build_regime_validation_report(
            [],
            candidate_name="x",
            require_w4_manifest=False,
        )
        # No manifest gate failure (the informational marker is allowed)
        manifest_failures = [
            w
            for w in report["warnings"]
            if w.startswith("w4_") and w != "w4_manifest_not_required"
        ]
        self.assertEqual(manifest_failures, [])
        self.assertIn("w4_manifest_not_required", report["warnings"])
        # Overall is fail (no records), not error
        self.assertIn(report["overall_status"], {"fail", "pass"})


# ── 3. metrics formula ──────────────────────────────────────────────────


class MetricsFormulaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.manifest = _write_manifest(Path(self.tmp.name))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_false_exclusion_rate_correct_over_paired(self) -> None:
        # 25 triggered, 5 correct, fer = 0.20 → fails 0.10 gate
        records = []
        for i in range(25):
            records.append(
                _record(
                    analysis_date="2023-04-01",  # W1
                    candidate_triggered=True,
                    prediction_correct=i < 5,
                    baseline_correct=False,
                )
            )
        report = build_regime_validation_report(
            records,
            candidate_name="fer_v1",
            w4_manifest_path=self.manifest,
        )
        w1 = report["per_window_metrics"]["W1"]
        self.assertAlmostEqual(w1["false_exclusion_rate"], 0.20, places=4)

    def test_net_benefit_excludes_blocked(self) -> None:
        # 1 triggered+correct (blocked) + 1 untriggered+correct
        # baseline acc = 2/2 = 1.0
        # candidate-adjusted acc = 1/1 = 1.0
        # NB = 0.0 → below 0.05
        records = [
            _record(
                analysis_date="2023-04-01",
                candidate_triggered=True,
                prediction_correct=True,
                baseline_correct=True,
            ),
            _record(
                analysis_date="2023-04-02",
                candidate_triggered=False,
                prediction_correct=True,
                baseline_correct=True,
            ),
        ]
        report = build_regime_validation_report(
            records,
            candidate_name="nb_v1",
            w4_manifest_path=self.manifest,
        )
        w1 = report["per_window_metrics"]["W1"]
        self.assertEqual(w1["net_benefit"], 0.0)

    def test_survival_preservation_when_block_strips_correct(self) -> None:
        # 10 survival cases, all blocked → preservation = 0
        records = [
            _record(
                analysis_date="2023-04-01",
                candidate_triggered=True,
                prediction_correct=True,
                baseline_correct=True,
                exclusion_would_block=True,
                survival_case=True,
            )
            for _ in range(10)
        ]
        report = build_regime_validation_report(
            records,
            candidate_name="surv_v1",
            w4_manifest_path=self.manifest,
        )
        w1 = report["per_window_metrics"]["W1"]
        self.assertEqual(w1["survival_case_preservation"], 0.0)

    def test_cross_window_variance_max_minus_min(self) -> None:
        # W1 fer = 0.04, W2 fer = 0.04, W3 fer = 0.04, W4 fer = 0.32 → variance ≈ 0.28
        records = (
            _balanced_window_records(
                window_dates=["2023-04-01"] * 25, triggered_per_date=1, correct_when_triggered=0
            )
            + [
                _record(
                    analysis_date="2023-04-01",
                    candidate_triggered=True,
                    prediction_correct=True,
                    baseline_correct=False,
                )
            ]
            + _balanced_window_records(
                window_dates=["2023-10-01"] * 25, triggered_per_date=1, correct_when_triggered=0
            )
            + [
                _record(
                    analysis_date="2023-10-01",
                    candidate_triggered=True,
                    prediction_correct=True,
                    baseline_correct=False,
                )
            ]
            + _balanced_window_records(
                window_dates=["2024-04-01"] * 25, triggered_per_date=1, correct_when_triggered=0
            )
            + [
                _record(
                    analysis_date="2024-04-01",
                    candidate_triggered=True,
                    prediction_correct=True,
                    baseline_correct=False,
                )
            ]
            + _balanced_window_records(
                window_dates=["2024-10-01"] * 25, triggered_per_date=1, correct_when_triggered=1
            )
        )
        report = build_regime_validation_report(
            records,
            candidate_name="variance_v1",
            w4_manifest_path=self.manifest,
        )
        var = report["cross_window_variance"]["false_exclusion_rate"]
        self.assertIsNotNone(var)
        self.assertGreater(var, 0.10)

    def test_no_single_window_collapse_triggers_on_high_fer(self) -> None:
        # 25 triggered, all correct → fer = 1.0 ≥ 0.20 → collapse
        records = [
            _record(
                analysis_date="2023-04-01",
                candidate_triggered=True,
                prediction_correct=True,
                baseline_correct=False,
            )
            for _ in range(25)
        ]
        report = build_regime_validation_report(
            records,
            candidate_name="collapse_v1",
            w4_manifest_path=self.manifest,
        )
        self.assertEqual(report["gate_status"]["no_single_window_collapse"], "fail")

    def test_minimum_window_sample_size_below_20_fails(self) -> None:
        records = [
            _record(
                analysis_date="2023-04-01",
                candidate_triggered=True,
                prediction_correct=False,
                baseline_correct=False,
            )
            for _ in range(5)
        ]
        report = build_regime_validation_report(
            records,
            candidate_name="small_v1",
            w4_manifest_path=self.manifest,
        )
        self.assertEqual(
            report["gate_status"]["minimum_window_sample_size"], "fail"
        )


# ── 4. overall_status / worst-window ───────────────────────────────────


class OverallStatusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.manifest = _write_manifest(Path(self.tmp.name))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_any_gate_fail_means_overall_fail(self) -> None:
        records = _make_r4_like_records()
        report = build_regime_validation_report(
            records,
            candidate_name="r4_like",
            w4_manifest_path=self.manifest,
        )
        self.assertEqual(report["overall_status"], "fail")

    def test_all_gates_pass_means_overall_pass(self) -> None:
        records = _make_records_passing_all_gates()
        report = build_regime_validation_report(
            records,
            candidate_name="all_pass",
            w4_manifest_path=self.manifest,
        )
        # If our all-pass fixture is engineered correctly → pass.
        self.assertEqual(report["overall_status"], "pass", msg=str(report))

    def test_no_partial_status(self) -> None:
        for records in (
            [],
            _make_r4_like_records(),
            _make_records_passing_all_gates(),
        ):
            report = build_regime_validation_report(
                records,
                candidate_name="x",
                w4_manifest_path=self.manifest,
            )
            self.assertIn(report["overall_status"], {"pass", "fail", "error"})

    def test_worst_window_priority_picks_highest_fer(self) -> None:
        records = _make_r4_like_records()
        report = build_regime_validation_report(
            records,
            candidate_name="r4_like_worst",
            w4_manifest_path=self.manifest,
        )
        # W2 has fer = 0.40 — highest among the 4 windows.
        self.assertEqual(report["worst_window"], "W2")


# ── 5. safety: 2026 / missing fields / immutability / isolation ─────────


class SafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.manifest = _write_manifest(Path(self.tmp.name))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_record_with_2026_date_triggers_refusal(self) -> None:
        records = [
            _record(
                analysis_date="2026-02-01",
                candidate_triggered=True,
                prediction_correct=False,
                baseline_correct=False,
            )
        ]
        report = build_regime_validation_report(
            records,
            candidate_name="cutoff",
            w4_manifest_path=self.manifest,
        )
        self.assertEqual(report["overall_status"], "error")
        self.assertTrue(report["final_test_refusal"])

    def test_record_at_cutoff_boundary_refused(self) -> None:
        records = [
            _record(
                analysis_date="2026-01-01",
                candidate_triggered=True,
                prediction_correct=False,
                baseline_correct=False,
            )
        ]
        report = build_regime_validation_report(
            records,
            candidate_name="boundary",
            w4_manifest_path=self.manifest,
        )
        self.assertEqual(report["overall_status"], "error")
        self.assertTrue(report["final_test_refusal"])

    def test_missing_required_field_skipped_with_warning(self) -> None:
        bad = {
            "analysis_date": "2023-04-01",
            "candidate_triggered": True,
            # missing prediction_correct / baseline_correct / etc.
        }
        report = build_regime_validation_report(
            [bad],
            candidate_name="missing_fields",
            w4_manifest_path=self.manifest,
        )
        self.assertEqual(report["overall_status"], "fail")
        self.assertTrue(
            any(
                w.startswith("record_skipped:missing_field")
                for w in report["warnings"]
            )
        )

    def test_input_records_not_mutated(self) -> None:
        records = _make_r4_like_records()
        snapshot = copy.deepcopy(records)
        build_regime_validation_report(
            records,
            candidate_name="immut",
            w4_manifest_path=self.manifest,
        )
        self.assertEqual(records, snapshot)

    def test_data_cutoff_used_is_2026_01_01(self) -> None:
        report = build_regime_validation_report(
            [],
            candidate_name="x",
            w4_manifest_path=self.manifest,
        )
        self.assertEqual(report["data_cutoff_used"], DEFAULT_FINAL_TEST_CUTOFF)
        self.assertEqual(report["data_cutoff_used"], "2026-01-01")


class IsolationTests(unittest.TestCase):
    def test_module_does_not_import_forbidden(self) -> None:
        import services.regime_validation_helper as mod

        tree = ast.parse(Path(mod.__file__).read_text(encoding="utf-8"))
        forbidden_modules = {
            "yfinance",
            "requests",
            "longbridge",
            "broker",
            "paper_trade",
            "sqlite3",
            "services.prediction_store",
            "services.confidence_engine",
            "services.contradiction_engine",
            "services.risk_model",
            "services.soft_metadata_simulator",
            "services.anti_false_exclusion_dashboard",
            "services.regime_diagnostics_dashboard",
            "services.protection_layer_diagnostics",
            "services.historical_replay_training",
            "services.outcome_capture",
            "predict",
            "scanner",
            "streamlit",
            "ui.protection_layer_diagnostics_renderer",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn(alias.name, forbidden_modules)
            elif isinstance(node, ast.ImportFrom):
                self.assertNotIn(node.module, forbidden_modules)

    def test_module_does_not_reference_hard_required_fields(self) -> None:
        """Helper must not reference hard / forced / required mutation."""
        import services.regime_validation_helper as mod

        text = Path(mod.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "hard_exclusion_allowed",
            "forced_exclusion",
            "anti_false_exclusion_triggered",
            "_PROTECTION_LAYER_CONNECTED",
            "simulated_trade",
            "no_trade",
            "final_direction",
            "final_projection",
        ):
            self.assertNotIn(
                forbidden,
                text,
                f"helper unexpectedly references {forbidden}",
            )


# ── 6. acceptance: R4-like fail + pooled-pass-but-worst-fail ───────────


class AcceptanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.manifest = _write_manifest(Path(self.tmp.name))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_r4_like_fixture_fails_4fold_validation(self) -> None:
        """Acceptance: the R4 problem statement (high FER, regime-shift gap)
        must reproduce as overall_status='fail' with FER + collapse / variance
        gate failures."""
        records = _make_r4_like_records()
        report = build_regime_validation_report(
            records,
            candidate_name="r4_baseline",
            w4_manifest_path=self.manifest,
        )
        self.assertEqual(report["overall_status"], "fail")
        # Must fail at least one of: FER, collapse (fer ≥ 0.20), variance.
        failed_gates = {
            k for k, v in report["gate_status"].items() if v == "fail"
        }
        self.assertTrue(
            failed_gates
            & {
                "false_exclusion_rate",
                "no_single_window_collapse",
                "cross_window_variance",
            },
            msg=f"R4-like fixture did not fail any of the expected gates: {report}",
        )

    def test_pooled_pass_but_worst_window_fail(self) -> None:
        """Pooled FER may look acceptable, but worst-window must drive fail."""
        # 3 windows with fer 0.04 (1/25), 1 window with fer 0.40 (10/25)
        # Pooled fer = 13/100 = 0.13 (above gate, but engineered scenario)
        # → worst window definitely fails 0.10 gate
        records: list[dict[str, Any]] = []
        for d in ["2023-04-01"] * 25:  # W1
            records.append(
                _record(
                    analysis_date=d,
                    candidate_triggered=True,
                    prediction_correct=False,
                    baseline_correct=False,
                )
            )
        # Insert 1 correct in W1 → fer = 1/25 = 0.04
        records[-1] = _record(
            analysis_date="2023-04-01",
            candidate_triggered=True,
            prediction_correct=True,
            baseline_correct=False,
        )
        for d in ["2023-10-01"] * 25:  # W2 — same low fer
            records.append(
                _record(
                    analysis_date=d,
                    candidate_triggered=True,
                    prediction_correct=False,
                    baseline_correct=False,
                )
            )
        records[-1] = _record(
            analysis_date="2023-10-01",
            candidate_triggered=True,
            prediction_correct=True,
            baseline_correct=False,
        )
        for d in ["2024-04-01"] * 25:  # W3 — same low fer
            records.append(
                _record(
                    analysis_date=d,
                    candidate_triggered=True,
                    prediction_correct=False,
                    baseline_correct=False,
                )
            )
        records[-1] = _record(
            analysis_date="2024-04-01",
            candidate_triggered=True,
            prediction_correct=True,
            baseline_correct=False,
        )
        # W4 — fer = 10/25 = 0.40 → triggers FER + collapse
        for d in ["2024-10-01"] * 25:
            records.append(
                _record(
                    analysis_date=d,
                    candidate_triggered=True,
                    prediction_correct=False,
                    baseline_correct=False,
                )
            )
        for i in range(10):
            records[-1 - i] = _record(
                analysis_date="2024-10-01",
                candidate_triggered=True,
                prediction_correct=True,
                baseline_correct=False,
            )
        report = build_regime_validation_report(
            records,
            candidate_name="pooled_vs_worst",
            w4_manifest_path=self.manifest,
        )
        self.assertEqual(report["overall_status"], "fail")
        self.assertEqual(report["worst_window"], "W4")


if __name__ == "__main__":
    unittest.main()
