"""Step 3R-3.3C-B — real W1-W4 validation input wrapper tests.

Covers:
  - DB fingerprint (missing / existing)
  - assert_db_unchanged pass + fail
  - DB loader returns paired AVGO W1-W3 rows only
  - DB loader filters 2026 rows (cutoff)
  - DB loader filters non-AVGO symbols
  - DB loader filters rows where direction_correct IS NULL
  - DB loader filters W4-territory rows
  - DB loader filters lookahead rows (prediction_for_date <= analysis_date)
  - DB loader maps direction_correct INT 0/1 to bool
  - DB loader does not write DB (mtime/size unchanged)
  - W4 jsonl loader reads + filters 2026 rows
  - W4 jsonl loader tags source = "w4_jsonl"
  - load_w4_manifest reads JSON and returns dict
  - build_static_regime_label_provider returns regime_labels-shaped dict
  - build_real_validation_inputs combines DB + W4 + manifest
  - build_real_validation_inputs does NOT call orchestrator
  - CLI without --prepare-inputs-only exits nonzero
  - CLI with --prepare-inputs-only succeeds with fixture paths
  - isolation: no forbidden imports
  - isolation: no hard / forced / required / no_trade strings
  - no orchestrator import + no threshold sweep strings
"""
from __future__ import annotations

import ast
import copy
import io
import json
import sqlite3
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_real_continuous_smoothing_validation import (
    BUNDLE_SCHEMA_VERSION,
    DB_SOURCE_TAG,
    DEFAULT_FINAL_TEST_CUTOFF,
    W4_SOURCE_TAG,
    assert_db_unchanged,
    build_real_validation_inputs,
    build_static_regime_label_provider,
    get_db_fingerprint,
    load_w1_w3_rows_from_db,
    load_w4_manifest,
    load_w4_rows_from_jsonl,
    main,
)


# ── fixtures ────────────────────────────────────────────────────────────


def _create_db(path: Path) -> None:
    """Write a minimal sqlite db that matches avgo_agent.db's schema."""
    conn = sqlite3.connect(str(path))
    try:
        conn.executescript(
            """
            CREATE TABLE prediction_log (
                id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                analysis_date TEXT NOT NULL,
                prediction_for_date TEXT NOT NULL,
                created_at TEXT NOT NULL,
                final_bias TEXT NOT NULL,
                final_confidence TEXT NOT NULL,
                status TEXT NOT NULL,
                scan_result_json TEXT,
                research_result_json TEXT,
                predict_result_json TEXT NOT NULL,
                snapshot_id TEXT
            );
            CREATE TABLE outcome_log (
                id TEXT PRIMARY KEY,
                prediction_id TEXT NOT NULL,
                prediction_for_date TEXT NOT NULL,
                captured_at TEXT NOT NULL,
                actual_open REAL,
                actual_high REAL,
                actual_low REAL,
                actual_close REAL,
                actual_prev_close REAL,
                actual_open_change REAL,
                actual_close_change REAL,
                direction_correct INTEGER,
                scenario_match TEXT
            );
            """
        )
        predictions = [
            # W1: AVGO, paired
            ("p_w1", "AVGO", "2023-04-15", "2023-04-17", "2026-04-23T11:55:03",
             "bullish", "high", "saved", None, None, "{}", None),
            # W2: AVGO, paired
            ("p_w2", "AVGO", "2023-12-15", "2023-12-18", "2026-04-23T11:55:03",
             "bearish", "medium", "saved", None, None, "{}", None),
            # W3: AVGO, paired
            ("p_w3", "AVGO", "2024-05-15", "2024-05-16", "2026-04-23T11:55:03",
             "neutral", "low", "saved", None, None, "{}", None),
            # W4 territory: should be filtered out by the W1-W3 loader
            ("p_w4", "AVGO", "2024-09-01", "2024-09-03", "2026-04-23T11:55:03",
             "bullish", "high", "saved", None, None, "{}", None),
            # post-2026 final-test: must be filtered
            ("p_2026", "AVGO", "2026-04-22", "2026-04-23", "2026-04-23T11:55:03",
             "bullish", "high", "saved", None, None, "{}", None),
            # different symbol: must be filtered
            ("p_msft", "MSFT", "2023-04-15", "2023-04-17", "2026-04-23T11:55:03",
             "bullish", "high", "saved", None, None, "{}", None),
            # AVGO W2 but no direction_correct outcome
            ("p_unpaired", "AVGO", "2024-01-15", "2024-01-16", "2026-04-23T11:55:03",
             "bullish", "high", "saved", None, None, "{}", None),
            # lookahead anomaly: prediction_for_date == analysis_date
            ("p_lookahead", "AVGO", "2024-04-15", "2024-04-15", "2026-04-23T11:55:03",
             "bullish", "high", "saved", None, None, "{}", None),
        ]
        conn.executemany(
            "INSERT INTO prediction_log VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            predictions,
        )
        outcomes = [
            ("o_w1", "p_w1", "2023-04-17", "2026-04-24",
             100.0, 101.0, 99.5, 100.6, 99.9, 0.001, 0.007, 1, None),
            ("o_w2", "p_w2", "2023-12-18", "2026-04-24",
             50.0, 51.0, 49.0, 49.5, 50.1, 0.0, -0.012, 0, None),
            ("o_w3", "p_w3", "2024-05-16", "2026-04-24",
             80.0, 81.0, 79.5, 80.5, 79.9, 0.001, 0.0075, 1, None),
            ("o_w4", "p_w4", "2024-09-03", "2026-04-24",
             170.0, 172.0, 168.0, 170.5, 169.5, 0.003, 0.006, 1, None),
            ("o_2026", "p_2026", "2026-04-23", "2026-04-24",
             1500.0, 1510.0, 1490.0, 1505.0, 1499.0, 0.001, 0.004, 1, None),
            ("o_msft", "p_msft", "2023-04-17", "2026-04-24",
             300.0, 301.0, 299.0, 300.5, 299.0, 0.005, 0.005, 1, None),
            # null direction_correct
            ("o_unpaired", "p_unpaired", "2024-01-16", "2026-04-24",
             None, None, None, None, None, None, None, None, None),
            ("o_lookahead", "p_lookahead", "2024-04-15", "2026-04-24",
             100.0, 101.0, 99.0, 100.0, 99.5, 0.005, 0.005, 1, None),
        ]
        conn.executemany(
            "INSERT INTO outcome_log VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            outcomes,
        )
        conn.commit()
    finally:
        conn.close()


def _w4_jsonl_rows() -> list[dict[str, Any]]:
    return [
        {
            "as_of_date": "2024-08-05",
            "prediction_for_date": "2024-08-06",
            "direction_correct": True,
            "actual_state": "小涨",
            "actual_close_change": 0.012,
            "ready": True,
            "final_direction": "偏多",
        },
        {
            "as_of_date": "2025-03-15",
            "prediction_for_date": "2025-03-17",
            "direction_correct": False,
            "actual_state": "小跌",
            "actual_close_change": -0.005,
            "ready": True,
            "final_direction": "偏空",
        },
        # post-2026 row that must be filtered
        {
            "as_of_date": "2026-02-01",
            "prediction_for_date": "2026-02-02",
            "direction_correct": True,
            "actual_state": "小涨",
            "actual_close_change": 0.01,
            "ready": True,
        },
    ]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _valid_w4_manifest() -> dict[str, Any]:
    return {
        "schema_version": "w4_replay_manifest.v1",
        "replay_window": {"start": "2024-08-03", "end": "2025-12-31"},
        "final_test_cutoff": "2026-01-01",
        "final_test_touched": False,
        "records_generated": 353,
        "paired_outcomes": 353,
        "status": "ok",
        "warnings": [],
    }


def _regime_labels_template() -> dict[str, Any]:
    return {
        "schema_version": "regime_labels.v1",
        "as_of_date": "REPLACE_ME",
        "data_cutoff_date": "REPLACE_ME",
        "labels": {
            "pos20_regime": "mid",
            "avgo_minus_soxx_20d_regime": "neutral",
            "peer_momentum_regime": "mixed",
            "market_trend_regime": "sustained_bull_market",
            "monthly_context_regime": "normal",
        },
        "raw_features": {
            "pos20": 0.5,
            "avgo_minus_soxx_20d": 0.04,
            "peer_confirm_count": 2,
            "peer_5d_aligned_pct": 0.5,
            "qqq_60d_slope_per_month": 0.02,
            "qqq_60d_drawdown": 0.03,
            "soxx_60d_slope_per_month": 0.02,
            "monthly_return_pct": 0.04,
            "monthly_max_abs_daily_return": 0.02,
        },
        "warnings": [],
        "final_test_refusal": False,
    }


# ── 1. fingerprint + assert_db_unchanged ─────────────────────────────────


class FingerprintTests(unittest.TestCase):
    def test_missing_path_returns_exists_false(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fp = get_db_fingerprint(str(Path(tmp) / "nope.db"))
        self.assertFalse(fp["exists"])
        self.assertIsNone(fp["mtime_ns"])
        self.assertIsNone(fp["size_bytes"])

    def test_existing_path_returns_int_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.db"
            _create_db(path)
            fp = get_db_fingerprint(str(path))
        self.assertTrue(fp["exists"])
        self.assertIsInstance(fp["mtime_ns"], int)
        self.assertIsInstance(fp["size_bytes"], int)


class AssertDbUnchangedTests(unittest.TestCase):
    def test_equal_fingerprints_pass(self) -> None:
        a = {"path": "x", "exists": True, "mtime_ns": 1, "size_bytes": 2}
        assert_db_unchanged(a, dict(a))

    def test_mtime_change_raises(self) -> None:
        a = {"mtime_ns": 1, "size_bytes": 2}
        b = {"mtime_ns": 2, "size_bytes": 2}
        with self.assertRaises(RuntimeError):
            assert_db_unchanged(a, b)

    def test_size_change_raises(self) -> None:
        a = {"mtime_ns": 1, "size_bytes": 2}
        b = {"mtime_ns": 1, "size_bytes": 3}
        with self.assertRaises(RuntimeError):
            assert_db_unchanged(a, b)


# ── 2. DB loader ────────────────────────────────────────────────────────


class LoadW1W3RowsFromDbTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmp.name) / "x.db"
        _create_db(self.db_path)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_returns_only_W1_W3_avgo_paired(self) -> None:
        rows = load_w1_w3_rows_from_db(str(self.db_path))
        as_of_dates = [r["as_of_date"] for r in rows]
        # Expected: p_w1 (W1) + p_w2 (W2) + p_w3 (W3); excludes:
        # - p_w4 (W4 territory)
        # - p_2026 (final-test)
        # - p_msft (non-AVGO)
        # - p_unpaired (null direction_correct)
        # - p_lookahead (prediction_for_date <= analysis_date)
        self.assertEqual(
            as_of_dates,
            ["2023-04-15", "2023-12-15", "2024-05-15"],
        )

    def test_required_fields_present(self) -> None:
        rows = load_w1_w3_rows_from_db(str(self.db_path))
        for row in rows:
            for key in (
                "as_of_date",
                "prediction_for_date",
                "direction_correct",
                "actual_close_change",
                "ready",
                "source",
            ):
                self.assertIn(key, row)
            self.assertEqual(row["source"], DB_SOURCE_TAG)
            self.assertTrue(row["ready"])

    def test_direction_correct_int_to_bool(self) -> None:
        rows = load_w1_w3_rows_from_db(str(self.db_path))
        types = {type(r["direction_correct"]).__name__ for r in rows}
        self.assertEqual(types, {"bool"})
        # Verify mapping faithfulness for fixture rows
        as_of_to_dc = {r["as_of_date"]: r["direction_correct"] for r in rows}
        self.assertTrue(as_of_to_dc["2023-04-15"])
        self.assertFalse(as_of_to_dc["2023-12-15"])
        self.assertTrue(as_of_to_dc["2024-05-15"])

    def test_does_not_modify_db(self) -> None:
        before = get_db_fingerprint(str(self.db_path))
        load_w1_w3_rows_from_db(str(self.db_path))
        after = get_db_fingerprint(str(self.db_path))
        assert_db_unchanged(before, after)

    def test_cutoff_filters_2026(self) -> None:
        # Run with a cutoff that includes 2026 should still filter
        # because the W3 boundary itself stops at 2024-08-02.
        rows = load_w1_w3_rows_from_db(
            str(self.db_path), final_test_cutoff="2099-01-01"
        )
        for r in rows:
            self.assertLess(r["as_of_date"], "2026-01-01")
            self.assertLess(r["prediction_for_date"], "2026-01-01")

    def test_lookahead_rows_excluded(self) -> None:
        rows = load_w1_w3_rows_from_db(str(self.db_path))
        for r in rows:
            self.assertGreater(
                r["prediction_for_date"], r["as_of_date"]
            )


# ── 3. W4 jsonl loader ──────────────────────────────────────────────────


class LoadW4RowsFromJsonlTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "w4.jsonl"
        _write_jsonl(self.path, _w4_jsonl_rows())

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_returns_pre_2026_rows(self) -> None:
        rows = load_w4_rows_from_jsonl(str(self.path))
        as_of_dates = [r["as_of_date"] for r in rows]
        self.assertEqual(as_of_dates, ["2024-08-05", "2025-03-15"])

    def test_source_tag_added(self) -> None:
        rows = load_w4_rows_from_jsonl(str(self.path))
        for r in rows:
            self.assertEqual(r["source"], W4_SOURCE_TAG)

    def test_original_fields_preserved(self) -> None:
        rows = load_w4_rows_from_jsonl(str(self.path))
        first = rows[0]
        self.assertEqual(first["actual_state"], "小涨")
        self.assertTrue(first["direction_correct"])
        self.assertEqual(first["final_direction"], "偏多")

    def test_ignores_blank_lines(self) -> None:
        path = self.path.parent / "with_blanks.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n")
            for row in _w4_jsonl_rows()[:2]:
                f.write(json.dumps(row) + "\n")
            f.write("\n")
        rows = load_w4_rows_from_jsonl(str(path))
        self.assertEqual(len(rows), 2)


# ── 4. W4 manifest loader ───────────────────────────────────────────────


class LoadW4ManifestTests(unittest.TestCase):
    def test_returns_dict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.json"
            payload = _valid_w4_manifest()
            path.write_text(
                json.dumps(payload, ensure_ascii=False), encoding="utf-8"
            )
            out = load_w4_manifest(str(path))
        self.assertIsInstance(out, dict)
        self.assertEqual(out["schema_version"], "w4_replay_manifest.v1")
        self.assertEqual(out["status"], "ok")
        self.assertFalse(out["final_test_touched"])

    def test_non_object_payload_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.json"
            path.write_text("[1, 2, 3]", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_w4_manifest(str(path))


# ── 5. static regime_label_provider ─────────────────────────────────────


class StaticRegimeLabelProviderTests(unittest.TestCase):
    def test_returns_regime_labels_v1_with_date_set(self) -> None:
        provider = build_static_regime_label_provider(
            regime_labels_template=_regime_labels_template()
        )
        labels = provider("2024-05-15", {"as_of_date": "2024-05-15"})
        self.assertEqual(labels["schema_version"], "regime_labels.v1")
        self.assertEqual(labels["as_of_date"], "2024-05-15")
        self.assertEqual(labels["data_cutoff_date"], "2024-05-15")
        self.assertIn("labels", labels)
        self.assertIn("raw_features", labels)

    def test_template_not_mutated_across_calls(self) -> None:
        template = _regime_labels_template()
        snapshot = copy.deepcopy(template)
        provider = build_static_regime_label_provider(
            regime_labels_template=template
        )
        provider("2023-04-15", {})
        provider("2024-05-15", {})
        self.assertEqual(template, snapshot)


# ── 6. build_real_validation_inputs ─────────────────────────────────────


class BuildRealValidationInputsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.db_path = self.tmp / "x.db"
        _create_db(self.db_path)
        self.jsonl = self.tmp / "w4.jsonl"
        _write_jsonl(self.jsonl, _w4_jsonl_rows())
        self.manifest = self.tmp / "manifest.json"
        self.manifest.write_text(
            json.dumps(_valid_w4_manifest()), encoding="utf-8"
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_bundle_shape(self) -> None:
        bundle = build_real_validation_inputs(
            db_path=str(self.db_path),
            w4_jsonl_path=str(self.jsonl),
            w4_manifest_path=str(self.manifest),
        )
        for key in (
            "schema_version",
            "db_path",
            "db_fingerprint",
            "w1_w3_rows",
            "w4_jsonl_path",
            "w4_rows",
            "w4_manifest_path",
            "w4_manifest",
            "final_test_cutoff",
            "w4_manifest_status",
            "warnings",
        ):
            self.assertIn(key, bundle)
        self.assertEqual(bundle["schema_version"], BUNDLE_SCHEMA_VERSION)
        self.assertEqual(bundle["final_test_cutoff"], DEFAULT_FINAL_TEST_CUTOFF)
        self.assertEqual(bundle["w4_manifest_status"], "ok")

    def test_combines_db_and_w4_rows(self) -> None:
        bundle = build_real_validation_inputs(
            db_path=str(self.db_path),
            w4_jsonl_path=str(self.jsonl),
            w4_manifest_path=str(self.manifest),
        )
        self.assertEqual(len(bundle["w1_w3_rows"]), 3)
        self.assertEqual(len(bundle["w4_rows"]), 2)

    def test_does_not_call_orchestrator(self) -> None:
        # Top-level run dict from the orchestrator has key 'records_loaded'
        # — bundle must NOT shadow that shape; it has different keys.
        bundle = build_real_validation_inputs(
            db_path=str(self.db_path),
            w4_jsonl_path=str(self.jsonl),
            w4_manifest_path=str(self.manifest),
        )
        self.assertNotIn("records_loaded", bundle)
        self.assertNotIn("regime_validation_report", bundle)
        self.assertNotIn("replay_validation_records", bundle)
        self.assertNotIn("run_manifest", bundle)
        self.assertNotIn("report_status", bundle)

    def test_does_not_modify_db(self) -> None:
        before = get_db_fingerprint(str(self.db_path))
        build_real_validation_inputs(
            db_path=str(self.db_path),
            w4_jsonl_path=str(self.jsonl),
            w4_manifest_path=str(self.manifest),
        )
        after = get_db_fingerprint(str(self.db_path))
        assert_db_unchanged(before, after)

    def test_warnings_when_w4_manifest_status_not_ok(self) -> None:
        bad = _valid_w4_manifest()
        bad["status"] = "error"
        self.manifest.write_text(json.dumps(bad), encoding="utf-8")
        bundle = build_real_validation_inputs(
            db_path=str(self.db_path),
            w4_jsonl_path=str(self.jsonl),
            w4_manifest_path=str(self.manifest),
        )
        self.assertEqual(bundle["w4_manifest_status"], "error")
        self.assertIn(
            "w4_manifest_surface_status_not_ok", bundle["warnings"]
        )


# ── 7. CLI ──────────────────────────────────────────────────────────────


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.db_path = self.tmp / "x.db"
        _create_db(self.db_path)
        self.jsonl = self.tmp / "w4.jsonl"
        _write_jsonl(self.jsonl, _w4_jsonl_rows())
        self.manifest = self.tmp / "manifest.json"
        self.manifest.write_text(
            json.dumps(_valid_w4_manifest()), encoding="utf-8"
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_without_prepare_flag_exits_nonzero(self) -> None:
        err = io.StringIO()
        with redirect_stderr(err):
            rc = main([])
        self.assertNotEqual(rc, 0)
        self.assertIn("--prepare-inputs-only", err.getvalue())

    def test_missing_required_args_exits_nonzero(self) -> None:
        err = io.StringIO()
        with redirect_stderr(err):
            rc = main(["--prepare-inputs-only"])
        self.assertNotEqual(rc, 0)
        self.assertIn("--db-path", err.getvalue())

    def test_prepare_only_succeeds(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            rc = main(
                [
                    "--prepare-inputs-only",
                    "--db-path",
                    str(self.db_path),
                    "--w4-jsonl",
                    str(self.jsonl),
                    "--w4-manifest",
                    str(self.manifest),
                ]
            )
        self.assertEqual(rc, 0)
        summary = json.loads(out.getvalue())
        self.assertEqual(
            summary["schema_version"], BUNDLE_SCHEMA_VERSION
        )
        self.assertEqual(summary["w1_w3_row_count"], 3)
        self.assertEqual(summary["w4_row_count"], 2)
        self.assertEqual(summary["w4_manifest_status"], "ok")
        self.assertEqual(
            summary["final_test_cutoff"], DEFAULT_FINAL_TEST_CUTOFF
        )
        # CLI also must not change the DB
        before = get_db_fingerprint(str(self.db_path))
        # Run again and check fingerprint
        out2 = io.StringIO()
        with redirect_stdout(out2):
            main(
                [
                    "--prepare-inputs-only",
                    "--db-path",
                    str(self.db_path),
                    "--w4-jsonl",
                    str(self.jsonl),
                    "--w4-manifest",
                    str(self.manifest),
                ]
            )
        after = get_db_fingerprint(str(self.db_path))
        assert_db_unchanged(before, after)


# ── 8. isolation / static checks ────────────────────────────────────────


class IsolationTests(unittest.TestCase):
    def _module_text(self) -> str:
        import scripts.run_real_continuous_smoothing_validation as mod

        return Path(mod.__file__).read_text(encoding="utf-8")

    def test_no_forbidden_imports(self) -> None:
        import scripts.run_real_continuous_smoothing_validation as mod

        tree = ast.parse(Path(mod.__file__).read_text(encoding="utf-8"))
        forbidden = {
            "yfinance",
            "requests",
            "longbridge",
            "broker",
            "paper_trade",
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
            # The wrapper must NOT import the orchestrator module — it only
            # assembles inputs for it.
            "scripts.run_continuous_smoothing_validation",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn(alias.name, forbidden)
            elif isinstance(node, ast.ImportFrom):
                self.assertNotIn(node.module, forbidden)

    def test_does_not_reference_hard_required_or_trading_strings(self) -> None:
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
            "yfinance",
            "paper_trade",
            "longbridge",
        ):
            self.assertNotIn(
                forbidden,
                text,
                f"wrapper unexpectedly references {forbidden!r}",
            )

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
        ):
            self.assertNotIn(forbidden, text)

    def test_no_real_validation_invocation(self) -> None:
        text = self._module_text()
        # The wrapper must not invoke or even reference the orchestrator
        # by name.
        self.assertNotIn("run_continuous_smoothing_validation", text)
        # Also must not fabricate a parallel "run_validation" symbol.
        self.assertNotIn("def run_validation(", text)

    def test_sqlite_open_uses_readonly_mode(self) -> None:
        text = self._module_text()
        self.assertIn("mode=ro", text)
        # The connect call must pass uri=True
        self.assertIn("uri=True", text)


if __name__ == "__main__":
    unittest.main()
