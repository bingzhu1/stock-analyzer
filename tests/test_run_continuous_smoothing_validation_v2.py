"""Step 3R-3.3F-C — v2 orchestrator tests.

Covers:
  - top-level run dict + run_manifest schema
  - schema_version == "continuous_smoothing_validation_run_v2.v1"
  - candidate_name default == "continuous_smoothing_v2"
  - v2 candidate factory called (and v1 not called)
  - candidate attached to enriched rows under "candidate" key (adapter-readable)
  - adapter records produced + records_adapted matches
  - input rows + manifest not mutated
  - final-test row skipped (cutoff) + final_test_touched=True
  - regime_label_provider final_test_refusal propagates
  - candidate_threshold passed to adapter; default = 0.60
  - no threshold sweep (string + AST scan)
  - write_outputs=False writes no files
  - write_outputs=True writes 4 files
  - existing output_dir raises FileExistsError
  - report_status mirrors helper.overall_status (or error on touched)
  - isolation: no v1 candidate / v1 orchestrator / v1 glue / DB / network /
    trading / streamlit imports
  - isolation: no hard / forced / required / final_direction strings
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
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.run_continuous_smoothing_validation_v2 as orch_v2  # noqa: E402
from scripts.run_continuous_smoothing_validation_v2 import (  # noqa: E402
    DEFAULT_CANDIDATE_NAME,
    DEFAULT_CANDIDATE_THRESHOLD,
    DEFAULT_FINAL_TEST_CUTOFF,
    RUN_MANIFEST_SCHEMA_VERSION,
    RUN_SCHEMA_VERSION,
    run_continuous_smoothing_validation_v2,
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
        "labels": {},
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


def _make_provider(template: dict[str, Any] | None = None):
    """Return provider(as_of_date, row) -> regime_labels with as_of_date set."""
    base = template if template is not None else _regime_labels()

    def _provider(as_of_date: str, _row: dict[str, Any]) -> dict[str, Any]:
        out = copy.deepcopy(base)
        out["as_of_date"] = as_of_date
        out["data_cutoff_date"] = as_of_date
        return out

    return _provider


def _rows_at_dates(dates: list[str]) -> list[dict[str, Any]]:
    return [
        {
            "as_of_date": d,
            "prediction_for_date": d,
            "direction_correct": True,
            "actual_close_change": 0.01,
            "ready": True,
        }
        for d in dates
    ]


# ── 1. output schema ────────────────────────────────────────────────────


class OutputSchemaTests(unittest.TestCase):
    def test_top_level_keys_and_schema_versions(self) -> None:
        result = run_continuous_smoothing_validation_v2(
            _rows_at_dates(["2024-09-15"]),
            regime_label_provider=_make_provider(),
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
            self.assertIn(key, result)
        self.assertEqual(
            result["schema_version"], "continuous_smoothing_validation_run_v2.v1"
        )
        self.assertEqual(result["schema_version"], RUN_SCHEMA_VERSION)
        self.assertEqual(
            result["run_manifest"]["schema_version"],
            RUN_MANIFEST_SCHEMA_VERSION,
        )

    def test_candidate_name_default_is_v2(self) -> None:
        result = run_continuous_smoothing_validation_v2(
            _rows_at_dates(["2024-09-15"]),
            regime_label_provider=_make_provider(),
            w4_manifest=_VALID_W4_MANIFEST,
        )
        self.assertEqual(result["candidate_name"], "continuous_smoothing_v2")
        self.assertEqual(result["candidate_name"], DEFAULT_CANDIDATE_NAME)
        self.assertEqual(
            result["run_manifest"]["candidate_name"], "continuous_smoothing_v2"
        )

    def test_candidate_threshold_default_is_060(self) -> None:
        self.assertEqual(DEFAULT_CANDIDATE_THRESHOLD, 0.60)
        self.assertEqual(DEFAULT_FINAL_TEST_CUTOFF, "2026-01-01")


# ── 2. v2 candidate factory wiring ──────────────────────────────────────


class CandidateFactoryWiringTests(unittest.TestCase):
    def test_v2_candidate_called_not_v1(self) -> None:
        captured: list[str] = []
        v2_real = orch_v2.build_continuous_smoothing_candidate_v2

        def spy(*args, **kwargs):
            captured.append("v2")
            return v2_real(*args, **kwargs)

        with mock.patch.object(
            orch_v2,
            "build_continuous_smoothing_candidate_v2",
            side_effect=spy,
        ):
            run_continuous_smoothing_validation_v2(
                _rows_at_dates(["2024-09-15", "2024-09-16"]),
                regime_label_provider=_make_provider(),
                w4_manifest=_VALID_W4_MANIFEST,
            )
        # Two rows → two v2 candidate calls.
        self.assertEqual(captured, ["v2", "v2"])

    def test_candidate_attached_under_adapter_readable_key(self) -> None:
        # The adapter reads row["candidate"]; verify v2 attaches under that key.
        captured_rows: list[dict[str, Any]] = []
        real_adapter = orch_v2.build_replay_validation_records

        def spy(rows, **kwargs):
            captured_rows.extend(rows)
            return real_adapter(rows, **kwargs)

        with mock.patch.object(
            orch_v2, "build_replay_validation_records", side_effect=spy
        ):
            run_continuous_smoothing_validation_v2(
                _rows_at_dates(["2024-09-15"]),
                regime_label_provider=_make_provider(),
                w4_manifest=_VALID_W4_MANIFEST,
            )
        self.assertGreater(len(captured_rows), 0)
        cand = captured_rows[0].get("candidate")
        self.assertIsInstance(cand, dict)
        self.assertEqual(
            cand.get("schema_version"), "continuous_smoothing_candidate_v2.v1"
        )
        self.assertEqual(cand.get("candidate_name"), "continuous_smoothing_v2")


# ── 3. cutoff / refusal behavior ────────────────────────────────────────


class CutoffBehaviorTests(unittest.TestCase):
    def test_final_test_row_skipped_and_touched(self) -> None:
        rows = _rows_at_dates(["2024-09-15", "2026-04-22"])
        result = run_continuous_smoothing_validation_v2(
            rows,
            regime_label_provider=_make_provider(),
            w4_manifest=_VALID_W4_MANIFEST,
        )
        self.assertEqual(result["records_loaded"], 2)
        self.assertTrue(result["run_manifest"]["final_test_touched"])
        self.assertEqual(result["report_status"], "error")
        self.assertTrue(
            any(
                "final_test_range_refusal" in w
                for w in result["warnings"]
                if isinstance(w, str)
            )
        )

    def test_regime_labels_final_test_refusal_propagates(self) -> None:
        provider_template = _regime_labels(final_test_refusal=True)
        result = run_continuous_smoothing_validation_v2(
            _rows_at_dates(["2024-09-15"]),
            regime_label_provider=_make_provider(provider_template),
            w4_manifest=_VALID_W4_MANIFEST,
        )
        self.assertTrue(result["run_manifest"]["final_test_touched"])
        self.assertEqual(result["report_status"], "error")


# ── 4. threshold passthrough ────────────────────────────────────────────


class ThresholdPassthroughTests(unittest.TestCase):
    def test_threshold_default_passed_to_adapter(self) -> None:
        captured_kwargs: dict[str, Any] = {}
        real_adapter = orch_v2.build_replay_validation_records

        def spy(rows, **kwargs):
            captured_kwargs.update(kwargs)
            return real_adapter(rows, **kwargs)

        with mock.patch.object(
            orch_v2, "build_replay_validation_records", side_effect=spy
        ):
            run_continuous_smoothing_validation_v2(
                _rows_at_dates(["2024-09-15"]),
                regime_label_provider=_make_provider(),
                w4_manifest=_VALID_W4_MANIFEST,
            )
        self.assertEqual(captured_kwargs.get("candidate_threshold"), 0.60)
        self.assertEqual(
            captured_kwargs.get("candidate_name"), "continuous_smoothing_v2"
        )

    def test_threshold_explicit_passed_to_adapter(self) -> None:
        captured_kwargs: dict[str, Any] = {}
        real_adapter = orch_v2.build_replay_validation_records

        def spy(rows, **kwargs):
            captured_kwargs.update(kwargs)
            return real_adapter(rows, **kwargs)

        with mock.patch.object(
            orch_v2, "build_replay_validation_records", side_effect=spy
        ):
            run_continuous_smoothing_validation_v2(
                _rows_at_dates(["2024-09-15"]),
                regime_label_provider=_make_provider(),
                w4_manifest=_VALID_W4_MANIFEST,
                candidate_threshold=0.60,  # v2 lock; same value reused
            )
        self.assertEqual(captured_kwargs["candidate_threshold"], 0.60)


# ── 5. write_outputs behavior ───────────────────────────────────────────


class WriteOutputsTests(unittest.TestCase):
    def test_write_outputs_false_writes_no_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "v2_out"
            run_continuous_smoothing_validation_v2(
                _rows_at_dates(["2024-09-15"]),
                regime_label_provider=_make_provider(),
                w4_manifest=_VALID_W4_MANIFEST,
                output_dir=str(target),
                write_outputs=False,
            )
            self.assertFalse(target.exists())

    def test_write_outputs_true_writes_4_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "v2_out"
            run_continuous_smoothing_validation_v2(
                _rows_at_dates(["2024-09-15"]),
                regime_label_provider=_make_provider(),
                w4_manifest=_VALID_W4_MANIFEST,
                output_dir=str(target),
                write_outputs=True,
            )
            self.assertTrue(target.is_dir())
            expected = {
                "replay_validation_records.json",
                "regime_validation_report.json",
                "regime_validation_summary.md",
                "run_manifest.json",
            }
            actual = {p.name for p in target.iterdir() if p.is_file()}
            self.assertEqual(expected, actual)
            # Sanity: report json is parseable.
            payload = json.loads(
                (target / "regime_validation_report.json").read_text()
            )
            self.assertEqual(payload.get("candidate_name"), "continuous_smoothing_v2")

    def test_existing_output_dir_raises_file_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "preexist"
            target.mkdir()
            with self.assertRaises(FileExistsError):
                run_continuous_smoothing_validation_v2(
                    _rows_at_dates(["2024-09-15"]),
                    regime_label_provider=_make_provider(),
                    w4_manifest=_VALID_W4_MANIFEST,
                    output_dir=str(target),
                    write_outputs=True,
                )

    def test_write_outputs_true_without_output_dir_raises(self) -> None:
        with self.assertRaises(ValueError):
            run_continuous_smoothing_validation_v2(
                _rows_at_dates(["2024-09-15"]),
                regime_label_provider=_make_provider(),
                w4_manifest=_VALID_W4_MANIFEST,
                output_dir=None,
                write_outputs=True,
            )


# ── 6. input not mutated ────────────────────────────────────────────────


class InputNotMutatedTests(unittest.TestCase):
    def test_rows_and_manifest_not_mutated(self) -> None:
        rows = _rows_at_dates(["2024-09-15", "2024-09-16"])
        manifest = copy.deepcopy(_VALID_W4_MANIFEST)
        rows_snap = copy.deepcopy(rows)
        manifest_snap = copy.deepcopy(manifest)
        run_continuous_smoothing_validation_v2(
            rows,
            regime_label_provider=_make_provider(),
            w4_manifest=manifest,
        )
        self.assertEqual(rows, rows_snap)
        self.assertEqual(manifest, manifest_snap)


# ── 7. isolation / forbidden imports / strings ─────────────────────────


class IsolationTests(unittest.TestCase):
    def _module_text(self) -> str:
        return Path(orch_v2.__file__).read_text(encoding="utf-8")

    def test_no_forbidden_imports(self) -> None:
        tree = ast.parse(self._module_text())
        forbidden = {
            "yfinance",
            "requests",
            "urllib",
            "urllib3",
            "httpx",
            "longbridge",
            "broker",
            "paper_trade",
            "sqlite3",
            "services.prediction_store",
            "services.outcome_capture",
            "services.confidence_engine",
            "services.contradiction_engine",
            "services.risk_model",
            "services.soft_metadata_simulator",
            "services.anti_false_exclusion_dashboard",
            "services.regime_diagnostics_dashboard",
            "services.protection_layer_diagnostics",
            "services.historical_replay_training",
            "predict",
            "scanner",
            "streamlit",
            "ui.protection_layer_diagnostics_renderer",
            # v2 must NOT import v1 candidate / v1 orchestrator / v1 glue.
            "services.continuous_smoothing_candidate",
            "scripts.run_continuous_smoothing_validation",
            "scripts.run_real_continuous_smoothing_validation_execute",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn(alias.name, forbidden)
            elif isinstance(node, ast.ImportFrom):
                self.assertNotIn(node.module, forbidden)

    def test_no_v1_module_string_reference(self) -> None:
        text = self._module_text()
        self.assertNotIn(
            "from services.continuous_smoothing_candidate import", text
        )
        self.assertNotIn(
            "from scripts.run_continuous_smoothing_validation import", text
        )
        self.assertNotIn(
            "from scripts.run_real_continuous_smoothing_validation_execute import",
            text,
        )

    def test_no_hard_required_or_trading_strings(self) -> None:
        text = self._module_text()
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
            self.assertNotIn(forbidden, text)

    def test_no_threshold_sweep_strings(self) -> None:
        text = self._module_text()
        for forbidden in (
            "thresholds = [",
            "for threshold in",
            "for t in thresholds",
            "candidate_thresholds",
            "threshold_grid",
            "optimize_threshold",
            "sweep_threshold",
            "grid_search",
        ):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
