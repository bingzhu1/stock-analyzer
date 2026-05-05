"""Step 3R-3.3A — dry-run continuous smoothing validation orchestrator tests.

Covers:
  - top-level run dict + run_manifest schema
  - candidate generator called / candidate attached to enriched rows
  - adapter records produced + records_adapted matches
  - helper called and report returned
  - input rows + manifest not mutated
  - final-test row skipped (cutoff)
  - regime_label_provider final_test_refusal propagates
  - candidate_threshold passed to adapter; default = 0.60
  - no threshold sweep (string + AST scan)
  - write_outputs=False writes no files; write_outputs=True writes 4
  - existing output_dir raises FileExistsError
  - report_status mirrors helper.overall_status (or error on touched)
  - warnings propagate
  - isolation: no DB / prediction_store / yfinance / requests / streamlit /
    trading imports; no W4 path hardcoded; no hard / forced / required
    field references
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

from scripts.run_continuous_smoothing_validation import (
    DEFAULT_CANDIDATE_NAME,
    DEFAULT_CANDIDATE_THRESHOLD,
    DEFAULT_FINAL_TEST_CUTOFF,
    RUN_MANIFEST_SCHEMA_VERSION,
    RUN_SCHEMA_VERSION,
    run_continuous_smoothing_validation,
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


def _regime_labels(
    *,
    as_of_date: str = "2024-09-15",
    final_test_refusal: bool = False,
    pos20: float | None = 0.50,
    avgo_minus_soxx_20d: float | None = 0.04,
    peer_5d_aligned_pct: float | None = 0.50,
    qqq_60d_slope_per_month: float | None = 0.02,
    qqq_60d_drawdown: float | None = 0.03,
    soxx_60d_slope_per_month: float | None = 0.02,
    monthly_max_abs_daily_return: float | None = 0.02,
    monthly_return_pct: float | None = 0.04,
) -> dict[str, Any]:
    return {
        "schema_version": "regime_labels.v1",
        "as_of_date": as_of_date,
        "data_cutoff_date": as_of_date,
        "labels": {
            "pos20_regime": "mid",
            "avgo_minus_soxx_20d_regime": "neutral",
            "peer_momentum_regime": "mixed",
            "market_trend_regime": "sustained_bull_market",
            "monthly_context_regime": "normal",
        },
        "raw_features": {
            "pos20": pos20,
            "avgo_minus_soxx_20d": avgo_minus_soxx_20d,
            "peer_confirm_count": 2,
            "peer_5d_aligned_pct": peer_5d_aligned_pct,
            "qqq_60d_slope_per_month": qqq_60d_slope_per_month,
            "qqq_60d_drawdown": qqq_60d_drawdown,
            "soxx_60d_slope_per_month": soxx_60d_slope_per_month,
            "monthly_return_pct": monthly_return_pct,
            "monthly_max_abs_daily_return": monthly_max_abs_daily_return,
        },
        "warnings": [],
        "final_test_refusal": final_test_refusal,
    }


def _replay_row(
    *,
    as_of_date: str = "2024-09-15",
    prediction_for_date: str = "2024-09-16",
    direction_correct: bool = True,
    actual_state: str = "小涨",
    actual_close_change: float = 0.012,
) -> dict[str, Any]:
    return {
        "as_of_date": as_of_date,
        "prediction_for_date": prediction_for_date,
        "direction_correct": direction_correct,
        "actual_state": actual_state,
        "actual_close_change": actual_close_change,
        "ready": True,
    }


def _stub_provider(refusal_dates: set[str] | None = None):
    refusal_dates = refusal_dates or set()

    def provider(as_of_date: str, _row: dict[str, Any]) -> dict[str, Any]:
        return _regime_labels(
            as_of_date=as_of_date,
            final_test_refusal=as_of_date in refusal_dates,
        )

    return provider


def _multi_window_rows() -> list[dict[str, Any]]:
    """Rows spanning W1/W2/W3/W4 to exercise window assignment."""
    rows: list[dict[str, Any]] = []
    rows.extend(
        _replay_row(
            as_of_date=f"2023-04-{day:02d}",
            prediction_for_date=f"2023-04-{day + 1:02d}",
            direction_correct=(day % 2 == 0),
        )
        for day in range(3, 12)  # W1
    )
    rows.extend(
        _replay_row(
            as_of_date=f"2023-12-{day:02d}",
            prediction_for_date=f"2023-12-{day + 1:02d}",
            direction_correct=(day % 2 == 1),
        )
        for day in range(3, 12)  # W2
    )
    rows.extend(
        _replay_row(
            as_of_date=f"2024-05-{day:02d}",
            prediction_for_date=f"2024-05-{day + 1:02d}",
            direction_correct=(day % 2 == 0),
        )
        for day in range(3, 12)  # W3
    )
    rows.extend(
        _replay_row(
            as_of_date=f"2024-12-{day:02d}",
            prediction_for_date=f"2024-12-{day + 1:02d}",
            direction_correct=(day % 2 == 1),
        )
        for day in range(3, 12)  # W4
    )
    return rows


# ── 1. schema ───────────────────────────────────────────────────────────


class RunSchemaTests(unittest.TestCase):
    def test_top_level_keys(self) -> None:
        out = run_continuous_smoothing_validation(
            [_replay_row()],
            regime_label_provider=_stub_provider(),
            w4_manifest=_VALID_W4_MANIFEST,
        )
        for key in (
            "schema_version",
            "candidate_name",
            "candidate_threshold",
            "records_loaded",
            "records_adapted",
            "report_status",
            "replay_validation_records",
            "regime_validation_report",
            "run_manifest",
            "warnings",
        ):
            self.assertIn(key, out)
        self.assertEqual(out["schema_version"], RUN_SCHEMA_VERSION)
        self.assertEqual(
            out["schema_version"], "continuous_smoothing_validation_run.v1"
        )

    def test_run_manifest_keys(self) -> None:
        out = run_continuous_smoothing_validation(
            [_replay_row()],
            regime_label_provider=_stub_provider(),
            w4_manifest=_VALID_W4_MANIFEST,
        )
        m = out["run_manifest"]
        for key in (
            "schema_version",
            "candidate_name",
            "candidate_threshold",
            "fold_count",
            "windows",
            "w4_manifest_status",
            "final_test_cutoff",
            "final_test_touched",
            "records_loaded",
            "records_adapted",
            "report_status",
            "warnings",
        ):
            self.assertIn(key, m)
        self.assertEqual(m["schema_version"], RUN_MANIFEST_SCHEMA_VERSION)
        self.assertEqual(m["fold_count"], 4)
        self.assertEqual(m["final_test_cutoff"], "2026-01-01")


# ── 2. orchestration flow ──────────────────────────────────────────────


class FlowTests(unittest.TestCase):
    def test_candidate_attached_to_each_record(self) -> None:
        out = run_continuous_smoothing_validation(
            [_replay_row()],
            regime_label_provider=_stub_provider(),
            w4_manifest=_VALID_W4_MANIFEST,
        )
        records = out["replay_validation_records"]["records"]
        self.assertEqual(len(records), 1)
        self.assertIsInstance(records[0]["candidate"], dict)
        self.assertEqual(
            records[0]["candidate"]["schema_version"],
            "continuous_smoothing_candidate.v1",
        )

    def test_records_adapted_matches_input_count(self) -> None:
        rows = _multi_window_rows()
        out = run_continuous_smoothing_validation(
            rows,
            regime_label_provider=_stub_provider(),
            w4_manifest=_VALID_W4_MANIFEST,
        )
        # All rows are valid + in-window → records_adapted == records_loaded
        self.assertEqual(out["records_loaded"], len(rows))
        self.assertEqual(out["records_adapted"], len(rows))

    def test_helper_report_returned(self) -> None:
        out = run_continuous_smoothing_validation(
            _multi_window_rows(),
            regime_label_provider=_stub_provider(),
            w4_manifest=_VALID_W4_MANIFEST,
        )
        report = out["regime_validation_report"]
        self.assertEqual(
            report["schema_version"], "regime_validation_report.v1"
        )
        self.assertIn("gate_status", report)
        self.assertIn(
            report["overall_status"], {"pass", "fail", "error"}
        )


# ── 3. immutability ────────────────────────────────────────────────────


class ImmutabilityTests(unittest.TestCase):
    def test_input_rows_not_mutated(self) -> None:
        rows = [_replay_row()]
        snapshot = copy.deepcopy(rows)
        run_continuous_smoothing_validation(
            rows,
            regime_label_provider=_stub_provider(),
            w4_manifest=_VALID_W4_MANIFEST,
        )
        self.assertEqual(rows, snapshot)

    def test_w4_manifest_not_mutated(self) -> None:
        manifest = copy.deepcopy(_VALID_W4_MANIFEST)
        snapshot = copy.deepcopy(manifest)
        run_continuous_smoothing_validation(
            [_replay_row()],
            regime_label_provider=_stub_provider(),
            w4_manifest=manifest,
        )
        self.assertEqual(manifest, snapshot)


# ── 4. final-test guards ──────────────────────────────────────────────


class FinalTestGuardTests(unittest.TestCase):
    def test_2026_row_skipped_and_marks_final_test_touched(self) -> None:
        rows = [_replay_row(), _replay_row(as_of_date="2026-02-01", prediction_for_date="2026-02-02")]
        out = run_continuous_smoothing_validation(
            rows,
            regime_label_provider=_stub_provider(),
            w4_manifest=_VALID_W4_MANIFEST,
        )
        self.assertTrue(out["run_manifest"]["final_test_touched"])
        self.assertEqual(out["report_status"], "error")
        self.assertTrue(
            any(
                "final_test_range_refusal" in w
                for w in out["warnings"]
            )
        )

    def test_regime_label_final_test_refusal_propagates(self) -> None:
        provider = _stub_provider(refusal_dates={"2024-09-15"})
        out = run_continuous_smoothing_validation(
            [_replay_row(as_of_date="2024-09-15", prediction_for_date="2024-09-16")],
            regime_label_provider=provider,
            w4_manifest=_VALID_W4_MANIFEST,
        )
        self.assertTrue(out["run_manifest"]["final_test_touched"])
        self.assertEqual(out["report_status"], "error")

    def test_w4_manifest_final_test_touched_returns_error(self) -> None:
        bad_manifest = dict(_VALID_W4_MANIFEST)
        bad_manifest["final_test_touched"] = True
        out = run_continuous_smoothing_validation(
            [_replay_row()],
            regime_label_provider=_stub_provider(),
            w4_manifest=bad_manifest,
        )
        self.assertEqual(out["report_status"], "error")
        self.assertEqual(
            out["run_manifest"]["w4_manifest_status"], "error"
        )
        self.assertTrue(out["run_manifest"]["final_test_touched"])


# ── 5. threshold policy ───────────────────────────────────────────────


class ThresholdPolicyTests(unittest.TestCase):
    def test_default_threshold_is_0_60(self) -> None:
        self.assertEqual(DEFAULT_CANDIDATE_THRESHOLD, 0.60)
        out = run_continuous_smoothing_validation(
            [_replay_row()],
            regime_label_provider=_stub_provider(),
            w4_manifest=_VALID_W4_MANIFEST,
        )
        self.assertEqual(out["candidate_threshold"], 0.60)
        self.assertEqual(
            out["replay_validation_records"]["candidate_threshold"], 0.60
        )

    def test_custom_threshold_passed_to_adapter(self) -> None:
        out = run_continuous_smoothing_validation(
            [_replay_row()],
            regime_label_provider=_stub_provider(),
            w4_manifest=_VALID_W4_MANIFEST,
            candidate_threshold=0.5,
        )
        self.assertEqual(out["candidate_threshold"], 0.5)
        self.assertEqual(
            out["replay_validation_records"]["candidate_threshold"], 0.5
        )

    def test_invalid_threshold_raises(self) -> None:
        # adapter raises ValueError; orchestrator must propagate
        with self.assertRaises(ValueError):
            run_continuous_smoothing_validation(
                [_replay_row()],
                regime_label_provider=_stub_provider(),
                w4_manifest=_VALID_W4_MANIFEST,
                candidate_threshold=1.5,
            )

    def test_no_threshold_sweep_in_source(self) -> None:
        """Static check: orchestrator does not iterate over a list of thresholds."""
        import scripts.run_continuous_smoothing_validation as mod

        text = Path(mod.__file__).read_text(encoding="utf-8")
        # Must not contain typical sweep patterns.
        for forbidden in (
            "thresholds = [",
            "for threshold in",
            "for t in thresholds",
            "candidate_thresholds",
            "threshold_grid",
            "optimize_threshold",
            "sweep_threshold",
        ):
            self.assertNotIn(forbidden, text)


# ── 6. write_outputs ──────────────────────────────────────────────────


class WriteOutputsTests(unittest.TestCase):
    def test_default_does_not_write_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "run_dir"
            run_continuous_smoothing_validation(
                [_replay_row()],
                regime_label_provider=_stub_provider(),
                w4_manifest=_VALID_W4_MANIFEST,
                output_dir=str(target),
                write_outputs=False,
            )
            self.assertFalse(target.exists())

    def test_write_outputs_true_requires_output_dir(self) -> None:
        with self.assertRaises(ValueError):
            run_continuous_smoothing_validation(
                [_replay_row()],
                regime_label_provider=_stub_provider(),
                w4_manifest=_VALID_W4_MANIFEST,
                write_outputs=True,
                output_dir=None,
            )

    def test_write_outputs_true_writes_4_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "run_dir"
            run_continuous_smoothing_validation(
                [_replay_row()],
                regime_label_provider=_stub_provider(),
                w4_manifest=_VALID_W4_MANIFEST,
                output_dir=str(target),
                write_outputs=True,
            )
            files = sorted(p.name for p in target.iterdir())
            self.assertEqual(
                files,
                sorted(
                    [
                        "regime_validation_report.json",
                        "regime_validation_summary.md",
                        "replay_validation_records.json",
                        "run_manifest.json",
                    ]
                ),
            )
            # Verify each json round-trips
            for name in (
                "regime_validation_report.json",
                "replay_validation_records.json",
                "run_manifest.json",
            ):
                json.loads((target / name).read_text(encoding="utf-8"))

    def test_existing_output_dir_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "run_dir"
            target.mkdir()
            (target / "stamp.txt").write_text("x", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                run_continuous_smoothing_validation(
                    [_replay_row()],
                    regime_label_provider=_stub_provider(),
                    w4_manifest=_VALID_W4_MANIFEST,
                    output_dir=str(target),
                    write_outputs=True,
                )

    def test_does_not_write_outside_output_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            target = tmp_path / "run_dir"
            before = sorted(p.name for p in tmp_path.iterdir())
            run_continuous_smoothing_validation(
                [_replay_row()],
                regime_label_provider=_stub_provider(),
                w4_manifest=_VALID_W4_MANIFEST,
                output_dir=str(target),
                write_outputs=True,
            )
            after = sorted(p.name for p in tmp_path.iterdir())
            # Only the new run_dir was added at top level
            self.assertEqual(set(after) - set(before), {"run_dir"})


# ── 7. report_status / warnings ───────────────────────────────────────


class ReportStatusTests(unittest.TestCase):
    def test_report_status_mirrors_helper_overall_status(self) -> None:
        out = run_continuous_smoothing_validation(
            _multi_window_rows(),
            regime_label_provider=_stub_provider(),
            w4_manifest=_VALID_W4_MANIFEST,
        )
        helper_status = out["regime_validation_report"]["overall_status"]
        # If final_test_touched=false and w4_manifest_status=ok, report_status
        # should equal helper status.
        self.assertFalse(out["run_manifest"]["final_test_touched"])
        self.assertEqual(
            out["run_manifest"]["w4_manifest_status"], "ok"
        )
        self.assertEqual(out["report_status"], helper_status)

    def test_warnings_propagate(self) -> None:
        rows = [_replay_row(), _replay_row(as_of_date="2026-02-01", prediction_for_date="2026-02-02")]
        out = run_continuous_smoothing_validation(
            rows,
            regime_label_provider=_stub_provider(),
            w4_manifest=_VALID_W4_MANIFEST,
        )
        # Orchestrator-level warning for cutoff skip + helper-level warning for require_w4_manifest=False.
        self.assertTrue(any("final_test_range_refusal" in w for w in out["warnings"]))


# ── 8. isolation ──────────────────────────────────────────────────────


class IsolationTests(unittest.TestCase):
    def test_module_does_not_import_forbidden(self) -> None:
        import scripts.run_continuous_smoothing_validation as mod

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

    def test_module_does_not_hardcode_w4_paths(self) -> None:
        import scripts.run_continuous_smoothing_validation as mod

        text = Path(mod.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "three_system_w4_2024_08_2025_12",
            "validation_ready_manifest.json",
            "three_system_replay_results.jsonl",
        ):
            self.assertNotIn(forbidden, text)

    def test_module_does_not_reference_hard_or_required_fields(self) -> None:
        import scripts.run_continuous_smoothing_validation as mod

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
                f"orchestrator unexpectedly references {forbidden}",
            )


if __name__ == "__main__":
    unittest.main()
