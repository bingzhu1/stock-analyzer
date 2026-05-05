"""Step 3R-4.3A — read-only replay → records adapter tests.

Covers:
  - output schema (top-level keys, schema_version, windows)
  - candidate_threshold required + bounds (raises ValueError)
  - W4 manifest gate (8 fail paths + happy path + require=False)
  - W4 row mapping (as_of_date, direction_correct, actual_state)
  - candidate_triggered (>= threshold), candidate refusal / unavailable / missing
  - exclusion_would_block / survival_case / baseline_correct (v1)
  - window assignment W1/W2/W3/W4
  - 2026 cutoff refusal + invalid dates + outside windows
  - input row immutability + manifest immutability
  - no forbidden output fields
  - isolation: no DB / prediction_store / yfinance / requests / streamlit /
    trading / regime_validation_helper imports
  - does not read files (no `open`, no path arg)
"""
from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.replay_validation_record_adapter import (
    DEFAULT_CANDIDATE_NAME,
    DEFAULT_FINAL_TEST_CUTOFF,
    DEFAULT_WINDOWS,
    SCHEMA_VERSION,
    build_replay_validation_records,
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


def _row(
    *,
    as_of_date: str = "2024-09-15",
    prediction_for_date: str | None = None,
    direction_correct: bool = True,
    actual_state: str = "小涨",
    actual_close_change: float = 0.012,
    risk_score: float | None = 0.7,
    candidate_final_test_refusal: bool = False,
    include_candidate: bool = True,
    labels: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if prediction_for_date is None:
        # naive next-day date that passes _is_valid_iso_date
        d = list(as_of_date)
        d[-1] = str((int(d[-1]) + 1) % 10)
        prediction_for_date = "".join(d)
    row: dict[str, Any] = {
        "as_of_date": as_of_date,
        "prediction_for_date": prediction_for_date,
        "direction_correct": direction_correct,
        "actual_state": actual_state,
        "actual_close_change": actual_close_change,
        "ready": True,
    }
    if include_candidate:
        row["candidate"] = {
            "schema_version": "continuous_smoothing_candidate.v1",
            "as_of_date": as_of_date,
            "data_cutoff_date": as_of_date,
            "candidate_name": "continuous_smoothing_v1",
            "risk_score": risk_score,
            "adjustment_score": (
                None if risk_score is None else risk_score - 0.5
            ),
            "risk_bucket": "high",
            "features_used": {"seed_coefficients": {}},
            "warnings": [],
            "final_test_refusal": candidate_final_test_refusal,
        }
    if labels is not None:
        row["labels"] = dict(labels)
    return row


# ── 1. output schema ─────────────────────────────────────────────────────


class OutputSchemaTests(unittest.TestCase):
    def test_top_level_keys(self) -> None:
        out = build_replay_validation_records(
            [],
            candidate_threshold=0.6,
            w4_manifest=_VALID_W4_MANIFEST,
        )
        for key in (
            "schema_version",
            "candidate_name",
            "candidate_threshold",
            "records",
            "windows",
            "source_files",
            "final_test_refusal",
            "warnings",
        ):
            self.assertIn(key, out)
        self.assertEqual(out["schema_version"], "replay_validation_records.v1")
        self.assertEqual(out["schema_version"], SCHEMA_VERSION)
        self.assertEqual(out["candidate_name"], DEFAULT_CANDIDATE_NAME)
        self.assertEqual(out["candidate_threshold"], 0.6)

    def test_default_windows_w1_to_w4(self) -> None:
        out = build_replay_validation_records(
            [],
            candidate_threshold=0.6,
            w4_manifest=_VALID_W4_MANIFEST,
        )
        self.assertEqual(set(out["windows"].keys()), {"W1", "W2", "W3", "W4"})
        self.assertEqual(out["windows"]["W4"]["end"], "2025-12-31")

    def test_data_cutoff_default(self) -> None:
        # function constant
        self.assertEqual(DEFAULT_FINAL_TEST_CUTOFF, "2026-01-01")


# ── 2. candidate_threshold required + bounds ─────────────────────────────


class ThresholdValidationTests(unittest.TestCase):
    def test_none_threshold_raises(self) -> None:
        with self.assertRaises(ValueError):
            build_replay_validation_records(
                [], candidate_threshold=None, w4_manifest=_VALID_W4_MANIFEST  # type: ignore[arg-type]
            )

    def test_negative_threshold_raises(self) -> None:
        with self.assertRaises(ValueError):
            build_replay_validation_records(
                [], candidate_threshold=-0.1, w4_manifest=_VALID_W4_MANIFEST
            )

    def test_above_one_threshold_raises(self) -> None:
        with self.assertRaises(ValueError):
            build_replay_validation_records(
                [], candidate_threshold=1.1, w4_manifest=_VALID_W4_MANIFEST
            )

    def test_non_numeric_threshold_raises(self) -> None:
        with self.assertRaises(ValueError):
            build_replay_validation_records(
                [], candidate_threshold="0.5", w4_manifest=_VALID_W4_MANIFEST  # type: ignore[arg-type]
            )

    def test_bool_threshold_rejected(self) -> None:
        # bool is subclass of int — adapter must reject
        with self.assertRaises(ValueError):
            build_replay_validation_records(
                [], candidate_threshold=True, w4_manifest=_VALID_W4_MANIFEST  # type: ignore[arg-type]
            )

    def test_zero_threshold_accepted(self) -> None:
        out = build_replay_validation_records(
            [], candidate_threshold=0.0, w4_manifest=_VALID_W4_MANIFEST
        )
        self.assertEqual(out["candidate_threshold"], 0.0)

    def test_one_threshold_accepted(self) -> None:
        out = build_replay_validation_records(
            [], candidate_threshold=1.0, w4_manifest=_VALID_W4_MANIFEST
        )
        self.assertEqual(out["candidate_threshold"], 1.0)


# ── 3. W4 manifest gate ──────────────────────────────────────────────────


class W4ManifestGateTests(unittest.TestCase):
    def test_valid_manifest_passes(self) -> None:
        out = build_replay_validation_records(
            [], candidate_threshold=0.6, w4_manifest=_VALID_W4_MANIFEST
        )
        manifest_failures = [w for w in out["warnings"] if w.startswith("w4_")]
        self.assertEqual(manifest_failures, [])
        self.assertFalse(out["final_test_refusal"])

    def test_final_test_touched_true_returns_empty_with_refusal(self) -> None:
        bad = dict(_VALID_W4_MANIFEST)
        bad["final_test_touched"] = True
        out = build_replay_validation_records(
            [], candidate_threshold=0.6, w4_manifest=bad
        )
        self.assertEqual(out["records"], [])
        self.assertTrue(out["final_test_refusal"])
        self.assertIn(
            "w4_final_test_touched_true_report_void", out["warnings"]
        )

    def test_wrong_replay_window_start(self) -> None:
        import json
        bad = json.loads(json.dumps(_VALID_W4_MANIFEST))
        bad["replay_window"]["start"] = "2024-09-01"
        out = build_replay_validation_records(
            [], candidate_threshold=0.6, w4_manifest=bad
        )
        self.assertEqual(out["records"], [])
        self.assertIn("w4_replay_window_start_mismatch", out["warnings"])

    def test_wrong_replay_window_end(self) -> None:
        import json
        bad = json.loads(json.dumps(_VALID_W4_MANIFEST))
        bad["replay_window"]["end"] = "2025-06-30"
        out = build_replay_validation_records(
            [], candidate_threshold=0.6, w4_manifest=bad
        )
        self.assertEqual(out["records"], [])
        self.assertIn("w4_replay_window_end_mismatch", out["warnings"])

    def test_paired_below_minimum(self) -> None:
        bad = dict(_VALID_W4_MANIFEST)
        bad["paired_outcomes"] = 5
        out = build_replay_validation_records(
            [], candidate_threshold=0.6, w4_manifest=bad
        )
        self.assertEqual(out["records"], [])
        self.assertIn("w4_paired_below_minimum", out["warnings"])

    def test_status_not_ok(self) -> None:
        bad = dict(_VALID_W4_MANIFEST)
        bad["status"] = "error"
        out = build_replay_validation_records(
            [], candidate_threshold=0.6, w4_manifest=bad
        )
        self.assertEqual(out["records"], [])
        self.assertIn("w4_manifest_status_not_ok", out["warnings"])

    def test_schema_version_mismatch(self) -> None:
        bad = dict(_VALID_W4_MANIFEST)
        bad["schema_version"] = "w4_replay_manifest.v0"
        out = build_replay_validation_records(
            [], candidate_threshold=0.6, w4_manifest=bad
        )
        self.assertEqual(out["records"], [])
        self.assertIn("w4_manifest_schema_mismatch", out["warnings"])

    def test_cutoff_mismatch(self) -> None:
        bad = dict(_VALID_W4_MANIFEST)
        bad["final_test_cutoff"] = "2025-12-01"
        out = build_replay_validation_records(
            [], candidate_threshold=0.6, w4_manifest=bad
        )
        self.assertEqual(out["records"], [])
        self.assertIn("w4_final_test_cutoff_mismatch", out["warnings"])

    def test_missing_manifest_when_required(self) -> None:
        out = build_replay_validation_records(
            [], candidate_threshold=0.6, require_w4_manifest=True, w4_manifest=None
        )
        self.assertEqual(out["records"], [])
        self.assertIn("w4_manifest_missing", out["warnings"])

    def test_require_w4_false_works_with_warning(self) -> None:
        out = build_replay_validation_records(
            [],
            candidate_threshold=0.6,
            require_w4_manifest=False,
            w4_manifest=None,
        )
        self.assertIn("w4_manifest_not_required", out["warnings"])
        # No w4_* failure markers
        for w in out["warnings"]:
            if w.startswith("w4_"):
                self.assertEqual(w, "w4_manifest_not_required")


# ── 4. row mapping ──────────────────────────────────────────────────────


class RowMappingTests(unittest.TestCase):
    def test_w4_row_maps_dates(self) -> None:
        rows = [_row(as_of_date="2024-09-15", prediction_for_date="2024-09-16")]
        out = build_replay_validation_records(
            rows, candidate_threshold=0.6, w4_manifest=_VALID_W4_MANIFEST
        )
        self.assertEqual(len(out["records"]), 1)
        rec = out["records"][0]
        self.assertEqual(rec["analysis_date"], "2024-09-15")
        self.assertEqual(rec["prediction_for_date"], "2024-09-16")
        self.assertEqual(rec["window"], "W4")

    def test_direction_correct_maps_to_prediction_and_baseline(self) -> None:
        rows = [_row(as_of_date="2024-09-15", direction_correct=True)]
        out = build_replay_validation_records(
            rows, candidate_threshold=0.6, w4_manifest=_VALID_W4_MANIFEST
        )
        rec = out["records"][0]
        self.assertTrue(rec["prediction_correct"])
        self.assertTrue(rec["baseline_correct"])

        rows2 = [_row(as_of_date="2024-09-15", direction_correct=False)]
        out2 = build_replay_validation_records(
            rows2, candidate_threshold=0.6, w4_manifest=_VALID_W4_MANIFEST
        )
        rec2 = out2["records"][0]
        self.assertFalse(rec2["prediction_correct"])
        self.assertFalse(rec2["baseline_correct"])

    def test_actual_direction_from_actual_state(self) -> None:
        for state, expected in (
            ("大涨", "up"),
            ("小涨", "up"),
            ("震荡", "flat"),
            ("小跌", "down"),
            ("大跌", "down"),
        ):
            rows = [_row(as_of_date="2024-09-15", actual_state=state)]
            out = build_replay_validation_records(
                rows, candidate_threshold=0.6, w4_manifest=_VALID_W4_MANIFEST
            )
            self.assertEqual(out["records"][0]["actual_direction"], expected)


# ── 5. candidate_triggered ──────────────────────────────────────────────


class CandidateTriggeredTests(unittest.TestCase):
    def test_triggered_when_risk_score_ge_threshold(self) -> None:
        rows = [_row(as_of_date="2024-09-15", risk_score=0.75)]
        out = build_replay_validation_records(
            rows, candidate_threshold=0.6, w4_manifest=_VALID_W4_MANIFEST
        )
        self.assertTrue(out["records"][0]["candidate_triggered"])

    def test_not_triggered_when_risk_score_lt_threshold(self) -> None:
        rows = [_row(as_of_date="2024-09-15", risk_score=0.50)]
        out = build_replay_validation_records(
            rows, candidate_threshold=0.6, w4_manifest=_VALID_W4_MANIFEST
        )
        self.assertFalse(out["records"][0]["candidate_triggered"])

    def test_triggered_at_exact_threshold(self) -> None:
        rows = [_row(as_of_date="2024-09-15", risk_score=0.6)]
        out = build_replay_validation_records(
            rows, candidate_threshold=0.6, w4_manifest=_VALID_W4_MANIFEST
        )
        self.assertTrue(out["records"][0]["candidate_triggered"])

    def test_missing_candidate_warning(self) -> None:
        rows = [_row(as_of_date="2024-09-15", include_candidate=False)]
        out = build_replay_validation_records(
            rows, candidate_threshold=0.6, w4_manifest=_VALID_W4_MANIFEST
        )
        rec = out["records"][0]
        self.assertFalse(rec["candidate_triggered"])
        self.assertIn("missing_candidate", rec["warnings"])

    def test_risk_score_none_warning(self) -> None:
        rows = [_row(as_of_date="2024-09-15", risk_score=None)]
        out = build_replay_validation_records(
            rows, candidate_threshold=0.6, w4_manifest=_VALID_W4_MANIFEST
        )
        rec = out["records"][0]
        self.assertFalse(rec["candidate_triggered"])
        self.assertIn("candidate_unavailable", rec["warnings"])

    def test_candidate_final_test_refusal_warning(self) -> None:
        rows = [_row(as_of_date="2024-09-15", candidate_final_test_refusal=True)]
        out = build_replay_validation_records(
            rows, candidate_threshold=0.6, w4_manifest=_VALID_W4_MANIFEST
        )
        rec = out["records"][0]
        self.assertFalse(rec["candidate_triggered"])
        self.assertIn("candidate_final_test_refusal", rec["warnings"])


# ── 6. derived fields ──────────────────────────────────────────────────


class DerivedFieldsTests(unittest.TestCase):
    def test_exclusion_equals_candidate_triggered(self) -> None:
        rows = [_row(as_of_date="2024-09-15", risk_score=0.75)]
        out = build_replay_validation_records(
            rows, candidate_threshold=0.6, w4_manifest=_VALID_W4_MANIFEST
        )
        rec = out["records"][0]
        self.assertEqual(rec["exclusion_would_block"], rec["candidate_triggered"])

    def test_survival_case_logic(self) -> None:
        # triggered + correct → survival
        rows = [_row(as_of_date="2024-09-15", risk_score=0.75, direction_correct=True)]
        out = build_replay_validation_records(
            rows, candidate_threshold=0.6, w4_manifest=_VALID_W4_MANIFEST
        )
        self.assertTrue(out["records"][0]["survival_case"])

        # triggered + wrong → not survival
        rows = [_row(as_of_date="2024-09-15", risk_score=0.75, direction_correct=False)]
        out = build_replay_validation_records(
            rows, candidate_threshold=0.6, w4_manifest=_VALID_W4_MANIFEST
        )
        self.assertFalse(out["records"][0]["survival_case"])

        # not triggered + correct → not survival
        rows = [_row(as_of_date="2024-09-15", risk_score=0.30, direction_correct=True)]
        out = build_replay_validation_records(
            rows, candidate_threshold=0.6, w4_manifest=_VALID_W4_MANIFEST
        )
        self.assertFalse(out["records"][0]["survival_case"])


# ── 7. window assignment ───────────────────────────────────────────────


class WindowAssignmentTests(unittest.TestCase):
    def test_w1(self) -> None:
        rows = [_row(as_of_date="2023-04-01")]
        out = build_replay_validation_records(
            rows,
            candidate_threshold=0.6,
            require_w4_manifest=False,
        )
        self.assertEqual(out["records"][0]["window"], "W1")

    def test_w2(self) -> None:
        rows = [_row(as_of_date="2023-12-15")]
        out = build_replay_validation_records(
            rows,
            candidate_threshold=0.6,
            require_w4_manifest=False,
        )
        self.assertEqual(out["records"][0]["window"], "W2")

    def test_w3(self) -> None:
        rows = [_row(as_of_date="2024-05-15")]
        out = build_replay_validation_records(
            rows,
            candidate_threshold=0.6,
            require_w4_manifest=False,
        )
        self.assertEqual(out["records"][0]["window"], "W3")

    def test_w4(self) -> None:
        rows = [_row(as_of_date="2024-12-15")]
        out = build_replay_validation_records(
            rows, candidate_threshold=0.6, w4_manifest=_VALID_W4_MANIFEST
        )
        self.assertEqual(out["records"][0]["window"], "W4")


# ── 8. cutoff / invalid / outside ──────────────────────────────────────


class SafetyTests(unittest.TestCase):
    def test_2026_record_skipped_with_refusal(self) -> None:
        rows = [_row(as_of_date="2026-02-01")]
        out = build_replay_validation_records(
            rows, candidate_threshold=0.6, w4_manifest=_VALID_W4_MANIFEST
        )
        self.assertEqual(out["records"], [])
        self.assertTrue(out["final_test_refusal"])
        self.assertTrue(
            any("final_test_range_refusal" in w for w in out["warnings"])
        )

    def test_cutoff_boundary_2026_01_01_skipped(self) -> None:
        rows = [_row(as_of_date="2026-01-01")]
        out = build_replay_validation_records(
            rows, candidate_threshold=0.6, w4_manifest=_VALID_W4_MANIFEST
        )
        self.assertEqual(out["records"], [])
        self.assertTrue(out["final_test_refusal"])

    def test_outside_windows_skipped(self) -> None:
        rows = [_row(as_of_date="2022-12-30")]
        out = build_replay_validation_records(
            rows,
            candidate_threshold=0.6,
            require_w4_manifest=False,
        )
        self.assertEqual(out["records"], [])
        self.assertTrue(
            any(
                "outside_validation_windows" in w for w in out["warnings"]
            )
        )

    def test_invalid_date_skipped(self) -> None:
        rows = [{"as_of_date": "not-a-date", "prediction_for_date": "2024-09-16"}]
        out = build_replay_validation_records(
            rows,
            candidate_threshold=0.6,
            require_w4_manifest=False,
        )
        self.assertEqual(out["records"], [])
        self.assertTrue(
            any("invalid_analysis_date" in w for w in out["warnings"])
        )

    def test_missing_direction_correct_skipped(self) -> None:
        rows = [
            _row(as_of_date="2024-09-15"),
        ]
        del rows[0]["direction_correct"]
        out = build_replay_validation_records(
            rows, candidate_threshold=0.6, w4_manifest=_VALID_W4_MANIFEST
        )
        self.assertEqual(out["records"], [])

    def test_input_rows_not_mutated(self) -> None:
        rows = [_row(as_of_date="2024-09-15")]
        snapshot = copy.deepcopy(rows)
        build_replay_validation_records(
            rows, candidate_threshold=0.6, w4_manifest=_VALID_W4_MANIFEST
        )
        self.assertEqual(rows, snapshot)

    def test_manifest_not_mutated(self) -> None:
        manifest = copy.deepcopy(_VALID_W4_MANIFEST)
        snapshot = copy.deepcopy(manifest)
        build_replay_validation_records(
            [], candidate_threshold=0.6, w4_manifest=manifest
        )
        self.assertEqual(manifest, snapshot)


# ── 9. no forbidden output fields + isolation ─────────────────────────


class NoForbiddenOutputTests(unittest.TestCase):
    FORBIDDEN_KEYS = (
        "gate_status",
        "validation_passed",
        "overall_status",
        "hard_exclusion_allowed",
        "hard_gate_status",
        "simulated_trade",
        "no_trade",
        "final_direction",
        "final_projection",
    )

    def test_no_forbidden_top_level_keys(self) -> None:
        rows = [_row(as_of_date="2024-09-15")]
        out = build_replay_validation_records(
            rows, candidate_threshold=0.6, w4_manifest=_VALID_W4_MANIFEST
        )
        for forbidden in self.FORBIDDEN_KEYS:
            self.assertNotIn(forbidden, out)

    def test_no_forbidden_record_keys(self) -> None:
        rows = [_row(as_of_date="2024-09-15")]
        out = build_replay_validation_records(
            rows, candidate_threshold=0.6, w4_manifest=_VALID_W4_MANIFEST
        )
        for rec in out["records"]:
            for forbidden in self.FORBIDDEN_KEYS:
                self.assertNotIn(forbidden, rec)


class IsolationTests(unittest.TestCase):
    def test_module_does_not_import_forbidden(self) -> None:
        import services.replay_validation_record_adapter as mod

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
            "services.regime_validation_helper",
            "services.continuous_smoothing_candidate",
            "services.regime_labels_builder",
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

    def test_does_not_call_validation_helper(self) -> None:
        import services.replay_validation_record_adapter as mod
        text = Path(mod.__file__).read_text(encoding="utf-8")
        self.assertNotIn("build_regime_validation_report", text)
        self.assertNotIn("regime_validation_report.v1", text)

    def test_does_not_read_files(self) -> None:
        """Adapter must not call open / read files."""
        import services.replay_validation_record_adapter as mod
        text = Path(mod.__file__).read_text(encoding="utf-8")
        # bare `open(` is the most common file-read trigger.
        self.assertNotIn("open(", text)
        # should not import json (we keep parsing in caller)
        # (json may appear in a comment, so check imports separately)
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotEqual(alias.name, "json")
                    self.assertNotEqual(alias.name, "io")
                    self.assertNotEqual(alias.name, "os")
                    self.assertNotEqual(alias.name, "pathlib")
            elif isinstance(node, ast.ImportFrom):
                self.assertNotEqual(node.module, "pathlib")
                self.assertNotEqual(node.module, "os")

    def test_does_not_reference_hard_or_required_fields(self) -> None:
        import services.replay_validation_record_adapter as mod
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
                f"adapter unexpectedly references {forbidden}",
            )


if __name__ == "__main__":
    unittest.main()
