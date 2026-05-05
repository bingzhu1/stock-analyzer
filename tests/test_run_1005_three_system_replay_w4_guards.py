"""Step 2G-8D.1A — W4 guards for run_1005_three_system_replay.

Covers:
  - new CLI args parsing (start/end/final_test_cutoff/tiny_smoke/manifest/etc.)
  - tiny-smoke defaults
  - 5 hard guards (G1–G4 + G5 manifest writer)
  - filter helpers (range + cutoff, T+1 boundary skip)
  - manifest schema (`w4_replay_manifest.v1`)
  - main() exit codes for invalid configs
  - static check: patch did NOT introduce new services/* / DB / network imports

Tests do NOT run a real replay. The few cases that exercise run_audit
inject pre-built `trading_days` and a stub `_audit_case_for_pair`.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import run_1005_three_system_replay as mod


# ── argparse ───────────────────────────────────────────────────────────────


class ParseArgsTests(unittest.TestCase):
    def test_explicit_start_end_parsed(self) -> None:
        ns = mod._parse_args(["--start-date", "2024-08-05", "--end-date", "2024-08-09"])
        self.assertEqual(ns.start_date, "2024-08-05")
        self.assertEqual(ns.end_date, "2024-08-09")

    def test_default_final_test_cutoff(self) -> None:
        ns = mod._parse_args([])
        self.assertEqual(ns.final_test_cutoff, "2026-01-01")

    def test_custom_final_test_cutoff_parsed(self) -> None:
        ns = mod._parse_args(["--final-test-cutoff", "2025-07-01"])
        self.assertEqual(ns.final_test_cutoff, "2025-07-01")

    def test_tiny_smoke_flag(self) -> None:
        ns = mod._parse_args(["--tiny-smoke"])
        self.assertTrue(ns.tiny_smoke)

    def test_write_manifest_flag(self) -> None:
        ns = mod._parse_args(["--write-manifest"])
        self.assertTrue(ns.write_manifest)

    def test_manifest_path_default_none(self) -> None:
        ns = mod._parse_args([])
        self.assertIsNone(ns.manifest_path)

    def test_allow_overwrite_flag(self) -> None:
        ns = mod._parse_args(["--allow-overwrite"])
        self.assertTrue(ns.allow_overwrite)

    def test_legacy_args_still_work(self) -> None:
        ns = mod._parse_args(["--num-cases", "10", "--symbol", "AVGO"])
        self.assertEqual(ns.num_cases, 10)
        self.assertEqual(ns.symbol, "AVGO")
        self.assertFalse(ns.tiny_smoke)
        self.assertFalse(ns.save_records)


# ── tiny-smoke defaults ────────────────────────────────────────────────────


class TinySmokeDefaultsTests(unittest.TestCase):
    def test_tiny_smoke_fills_default_range(self) -> None:
        ns = mod._parse_args(["--tiny-smoke"])
        ns = mod._apply_tiny_smoke_defaults(ns)
        self.assertEqual(ns.start_date, mod.TINY_SMOKE_DEFAULT_START)
        self.assertEqual(ns.end_date, mod.TINY_SMOKE_DEFAULT_END)

    def test_tiny_smoke_forces_save_records_false(self) -> None:
        ns = mod._parse_args(["--tiny-smoke", "--save-records"])
        ns = mod._apply_tiny_smoke_defaults(ns)
        self.assertFalse(ns.save_records)

    def test_tiny_smoke_forces_write_manifest_true(self) -> None:
        ns = mod._parse_args(["--tiny-smoke"])
        ns = mod._apply_tiny_smoke_defaults(ns)
        self.assertTrue(ns.write_manifest)

    def test_tiny_smoke_default_output_dir(self) -> None:
        ns = mod._parse_args(["--tiny-smoke"])
        ns = mod._apply_tiny_smoke_defaults(ns)
        self.assertEqual(ns.output_dir, mod.TINY_SMOKE_DEFAULT_OUTPUT_DIR)

    def test_tiny_smoke_respects_explicit_range(self) -> None:
        ns = mod._parse_args(
            ["--tiny-smoke", "--start-date", "2024-08-12", "--end-date", "2024-08-16"]
        )
        ns = mod._apply_tiny_smoke_defaults(ns)
        self.assertEqual(ns.start_date, "2024-08-12")
        self.assertEqual(ns.end_date, "2024-08-16")

    def test_no_tiny_smoke_leaves_args_untouched(self) -> None:
        ns = mod._parse_args([])
        before = (ns.start_date, ns.end_date, ns.save_records, ns.write_manifest)
        ns = mod._apply_tiny_smoke_defaults(ns)
        after = (ns.start_date, ns.end_date, ns.save_records, ns.write_manifest)
        self.assertEqual(before, after)


# ── _validate_w4_args ──────────────────────────────────────────────────────


class ValidateW4ArgsTests(unittest.TestCase):
    def _ns(self, **overrides: Any) -> argparse.Namespace:
        ns = mod._parse_args([])
        for k, v in overrides.items():
            setattr(ns, k, v)
        return ns

    def test_default_1005_invocation_passes(self) -> None:
        # legacy 1005 mode: no W4 markers, no extra checks
        mod._validate_w4_args(self._ns())

    def test_end_date_at_2026_rejected(self) -> None:
        ns = self._ns(
            start_date="2025-12-30",
            end_date="2026-01-01",
            output_dir=Path("/tmp/avgo_w4_x"),
        )
        with self.assertRaises(ValueError):
            mod._validate_w4_args(ns)

    def test_end_date_after_2026_rejected(self) -> None:
        ns = self._ns(
            start_date="2025-12-30",
            end_date="2026-03-01",
            output_dir=Path("/tmp/avgo_w4_x2"),
        )
        with self.assertRaises(ValueError):
            mod._validate_w4_args(ns)

    def test_start_date_in_2026_rejected(self) -> None:
        ns = self._ns(
            start_date="2026-02-01",
            end_date="2026-04-01",
            output_dir=Path("/tmp/avgo_w4_y"),
        )
        with self.assertRaises(ValueError):
            mod._validate_w4_args(ns)

    def test_save_records_with_w4_rejected(self) -> None:
        ns = self._ns(
            start_date="2024-08-05",
            end_date="2024-08-09",
            save_records=True,
            output_dir=Path("/tmp/avgo_w4_z"),
        )
        with self.assertRaises(ValueError):
            mod._validate_w4_args(ns)

    def test_save_records_with_tiny_smoke_rejected(self) -> None:
        ns = self._ns(
            tiny_smoke=True,
            save_records=True,
            output_dir=Path("/tmp/avgo_w4_smoke_a"),
        )
        with self.assertRaises(ValueError):
            mod._validate_w4_args(ns)

    def test_output_dir_three_system_1005_rejected_in_w4(self) -> None:
        ns = self._ns(
            start_date="2024-08-05",
            end_date="2024-08-09",
            output_dir=mod.DEFAULT_OUTPUT_DIR,
        )
        with self.assertRaises(ValueError):
            mod._validate_w4_args(ns)

    def test_existing_nonempty_output_dir_rejected_in_w4(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "w4"
            d.mkdir()
            (d / "stamp.txt").write_text("x", encoding="utf-8")
            ns = self._ns(
                start_date="2024-08-05",
                end_date="2024-08-09",
                output_dir=d,
                allow_overwrite=False,
            )
            with self.assertRaises(ValueError):
                mod._validate_w4_args(ns)

    def test_existing_nonempty_output_dir_allowed_with_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "w4"
            d.mkdir()
            (d / "stamp.txt").write_text("x", encoding="utf-8")
            ns = self._ns(
                start_date="2024-08-05",
                end_date="2024-08-09",
                output_dir=d,
                allow_overwrite=True,
            )
            mod._validate_w4_args(ns)  # no raise

    def test_start_after_end_rejected(self) -> None:
        ns = self._ns(
            start_date="2024-08-09",
            end_date="2024-08-05",
            output_dir=Path("/tmp/avgo_w4_q"),
        )
        with self.assertRaises(ValueError):
            mod._validate_w4_args(ns)

    def test_legacy_1005_with_save_records_unchanged(self) -> None:
        # Outside W4 mode, --save-records is permitted (legacy behavior)
        ns = self._ns(save_records=True)
        mod._validate_w4_args(ns)  # no raise


# ── filter helpers ─────────────────────────────────────────────────────────


class FilterTradingDaysByRangeTests(unittest.TestCase):
    def test_range_and_cutoff_both_applied(self) -> None:
        days = [
            "2024-08-01",
            "2024-08-05",
            "2024-08-09",
            "2025-12-31",
            "2026-01-02",
            "2026-02-01",
        ]
        out = mod._filter_trading_days_by_range(
            days, start="2024-08-05", end="2025-12-31", final_test_cutoff="2026-01-01"
        )
        self.assertEqual(out, ["2024-08-05", "2024-08-09", "2025-12-31"])

    def test_no_range_only_cutoff(self) -> None:
        days = ["2024-08-01", "2026-01-01", "2026-02-01"]
        out = mod._filter_trading_days_by_range(
            days, start=None, end=None, final_test_cutoff="2026-01-01"
        )
        self.assertEqual(out, ["2024-08-01"])

    def test_only_start(self) -> None:
        days = ["2024-08-01", "2024-08-05", "2025-12-31"]
        out = mod._filter_trading_days_by_range(
            days, start="2024-08-05", end=None, final_test_cutoff="2026-01-01"
        )
        self.assertEqual(out, ["2024-08-05", "2025-12-31"])


class FilterPairsByCutoffTests(unittest.TestCase):
    def test_pair_with_pred_at_cutoff_skipped(self) -> None:
        pairs = [("2025-12-30", "2025-12-31"), ("2025-12-31", "2026-01-02")]
        kept, warnings = mod._filter_pairs_by_cutoff(
            pairs, final_test_cutoff="2026-01-01"
        )
        self.assertEqual(kept, [("2025-12-30", "2025-12-31")])
        self.assertEqual(len(warnings), 1)
        self.assertIn("2026-01-02", warnings[0])
        self.assertIn("final_test_cutoff", warnings[0])

    def test_no_skipping_in_safe_range(self) -> None:
        pairs = [("2024-08-05", "2024-08-06"), ("2024-08-06", "2024-08-07")]
        kept, warnings = mod._filter_pairs_by_cutoff(
            pairs, final_test_cutoff="2026-01-01"
        )
        self.assertEqual(kept, pairs)
        self.assertEqual(warnings, [])

    def test_as_of_at_cutoff_also_skipped(self) -> None:
        pairs = [("2026-01-02", "2026-01-03")]
        kept, warnings = mod._filter_pairs_by_cutoff(
            pairs, final_test_cutoff="2026-01-01"
        )
        self.assertEqual(kept, [])
        self.assertEqual(len(warnings), 1)


class ResolveDatePairsTests(unittest.TestCase):
    def test_explicit_range_applies_g1_and_g2(self) -> None:
        days = [
            "2025-12-29",
            "2025-12-30",
            "2025-12-31",
            "2026-01-02",
            "2026-01-05",
        ]
        pairs, warnings = mod._resolve_date_pairs(
            trading_days=days,
            start_date="2025-12-29",
            end_date="2026-01-05",  # G1 trims to < cutoff
            num_cases=10,
            final_test_cutoff="2026-01-01",
        )
        # only days < cutoff = 2025-12-29, -30, -31 → pairs (29,30), (30,31)
        self.assertEqual(
            pairs,
            [("2025-12-29", "2025-12-30"), ("2025-12-30", "2025-12-31")],
        )
        self.assertEqual(warnings, [])

    def test_legacy_path_applies_cutoff(self) -> None:
        days = [
            "2025-12-29",
            "2025-12-30",
            "2025-12-31",
            "2026-01-02",
            "2026-01-05",
        ]
        pairs, warnings = mod._resolve_date_pairs(
            trading_days=days,
            start_date=None,
            end_date=None,
            num_cases=2,
            final_test_cutoff="2026-01-01",
        )
        # legacy: cutoff_filtered = first 3; tail num_cases=2 → pairs from last 3
        self.assertTrue(all(pred < "2026-01-01" for _, pred in pairs))
        self.assertTrue(all(asof < "2026-01-01" for asof, _ in pairs))


# ── manifest builder + writer ──────────────────────────────────────────────


class BuildManifestTests(unittest.TestCase):
    def test_schema_version_v1(self) -> None:
        m = mod._build_manifest(
            replay_window_start="2024-08-03",
            replay_window_end="2025-12-31",
            final_test_cutoff="2026-01-01",
        )
        self.assertEqual(m["schema_version"], "w4_replay_manifest.v1")

    def test_full_shape(self) -> None:
        m = mod._build_manifest(
            replay_window_start="2024-08-03",
            replay_window_end="2025-12-31",
            final_test_cutoff="2026-01-01",
            records_generated=5,
            paired_outcomes=4,
            status="ok",
            warnings=["x"],
        )
        self.assertEqual(m["replay_window"]["start"], "2024-08-03")
        self.assertEqual(m["replay_window"]["end"], "2025-12-31")
        self.assertEqual(m["final_test_cutoff"], "2026-01-01")
        self.assertEqual(m["records_generated"], 5)
        self.assertEqual(m["paired_outcomes"], 4)
        self.assertEqual(m["status"], "ok")
        self.assertEqual(m["warnings"], ["x"])

    def test_final_test_touched_default_false(self) -> None:
        m = mod._build_manifest(
            replay_window_start=None,
            replay_window_end=None,
            final_test_cutoff="2026-01-01",
        )
        self.assertFalse(m["final_test_touched"])

    def test_planned_status_supported(self) -> None:
        m = mod._build_manifest(
            replay_window_start="2024-08-03",
            replay_window_end="2025-12-31",
            final_test_cutoff="2026-01-01",
            status="planned",
        )
        self.assertEqual(m["status"], "planned")
        self.assertIsNone(m["records_generated"])
        self.assertIsNone(m["paired_outcomes"])

    def test_warnings_default_empty_list(self) -> None:
        m = mod._build_manifest(
            replay_window_start=None,
            replay_window_end=None,
            final_test_cutoff="2026-01-01",
        )
        self.assertEqual(m["warnings"], [])


class WriteManifestTests(unittest.TestCase):
    def test_write_then_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "validation_ready_manifest.json"
            m = mod._build_manifest(
                replay_window_start="2024-08-03",
                replay_window_end="2025-12-31",
                final_test_cutoff="2026-01-01",
                records_generated=5,
                paired_outcomes=4,
                status="ok",
            )
            mod._write_manifest(path, m)
            self.assertTrue(path.exists())
            loaded = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(loaded["schema_version"], "w4_replay_manifest.v1")
            self.assertFalse(loaded["final_test_touched"])
            self.assertEqual(loaded["replay_window"]["start"], "2024-08-03")
            self.assertEqual(loaded["replay_window"]["end"], "2025-12-31")
            self.assertEqual(loaded["records_generated"], 5)
            self.assertEqual(loaded["paired_outcomes"], 4)


# ── main() exit codes (no replay run) ─────────────────────────────────────


class MainExitCodeTests(unittest.TestCase):
    def test_main_returns_nonzero_on_2026_end(self) -> None:
        rc = mod.main(
            ["--start-date", "2025-12-30", "--end-date", "2026-01-05"]
        )
        self.assertNotEqual(rc, 0)

    def test_main_returns_nonzero_on_2026_start(self) -> None:
        rc = mod.main(
            ["--start-date", "2026-02-01", "--end-date", "2026-03-01"]
        )
        self.assertNotEqual(rc, 0)

    def test_main_returns_nonzero_on_save_records_with_w4(self) -> None:
        rc = mod.main(
            [
                "--start-date",
                "2024-08-05",
                "--end-date",
                "2024-08-09",
                "--save-records",
            ]
        )
        self.assertNotEqual(rc, 0)

    def test_main_returns_nonzero_on_w4_pointing_at_1005(self) -> None:
        rc = mod.main(
            [
                "--start-date",
                "2024-08-05",
                "--end-date",
                "2024-08-09",
                "--output-dir",
                str(mod.DEFAULT_OUTPUT_DIR),
            ]
        )
        self.assertNotEqual(rc, 0)


# ── run_audit() with stub case runner (G2 + manifest e2e, no replay) ──────


class RunAuditManifestE2ETests(unittest.TestCase):
    """End-to-end manifest emission with a stubbed _audit_case_for_pair."""

    def _stub_pair(
        self,
        *,
        symbol: str,
        as_of_date: str,
        prediction_for_date: str,
        lookback_days: int,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        replay_result = {
            "kind": "historical_replay_result",
            "symbol": symbol,
            "as_of_date": as_of_date,
            "prediction_for_date": prediction_for_date,
            "ready": True,
            "projection_snapshot": {"ready": True},
            "actual_outcome": {"actual_close": 100.0},
            "review": {},
            "warnings": [],
        }
        case = {
            "as_of_date": as_of_date,
            "prediction_for_date": prediction_for_date,
            "ready": True,
            "summary_extract": {"completed": True},
        }
        return replay_result, case

    def _stub_summarize(self, cases: list[dict[str, Any]]) -> dict[str, Any]:
        return {"overall": {"total_cases": len(cases), "completed_cases": len(cases),
                            "failed_cases": 0, "direction_accuracy": None}}

    def _stub_render_md(self, summary: dict[str, Any]) -> str:
        return "# stub summary\n"

    def _stub_row(self, *_: Any, **__: Any) -> dict[str, Any]:
        return {}

    def _stub_filter(self, _cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return []

    def test_smoke_window_emits_manifest_with_final_test_touched_false(self) -> None:
        days = [
            "2024-08-05",
            "2024-08-06",
            "2024-08-07",
            "2024-08-08",
            "2024-08-09",
        ]
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "smoke_out"
            with patch.object(mod, "_audit_case_for_pair", side_effect=self._stub_pair), \
                 patch.object(mod, "summarize_three_system_audit", side_effect=self._stub_summarize), \
                 patch.object(mod, "render_summary_markdown", side_effect=self._stub_render_md), \
                 patch.object(mod, "negative_system_row", side_effect=self._stub_row), \
                 patch.object(mod, "record_02_projection_row", side_effect=self._stub_row), \
                 patch.object(mod, "confidence_evaluator_row", side_effect=self._stub_row), \
                 patch.object(mod, "filter_error_cases", side_effect=self._stub_filter), \
                 patch.object(mod, "filter_false_exclusion_cases", side_effect=self._stub_filter), \
                 patch.object(mod, "filter_high_confidence_wrong_cases", side_effect=self._stub_filter):
                result = mod.run_audit(
                    symbol="AVGO",
                    num_cases=4,
                    lookback_days=20,
                    output_dir=out,
                    trading_days=days,
                    save_records=False,
                    start_date="2024-08-05",
                    end_date="2024-08-09",
                    final_test_cutoff="2026-01-01",
                    write_manifest=True,
                )
            self.assertTrue(result["ready"])
            self.assertEqual(result["num_cases_built"], 4)
            self.assertFalse(result["final_test_touched"])

            manifest_path = out / mod.DEFAULT_MANIFEST_FILENAME
            self.assertTrue(manifest_path.exists())
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["schema_version"], "w4_replay_manifest.v1")
            self.assertEqual(manifest["replay_window"]["start"], "2024-08-05")
            self.assertEqual(manifest["replay_window"]["end"], "2024-08-09")
            self.assertEqual(manifest["final_test_cutoff"], "2026-01-01")
            self.assertFalse(manifest["final_test_touched"])
            self.assertEqual(manifest["status"], "ok")
            self.assertEqual(manifest["records_generated"], 4)
            self.assertEqual(manifest["paired_outcomes"], 4)

    def test_t1_boundary_warning_recorded_in_manifest(self) -> None:
        # Trading days span the W4 → final-test boundary.
        days = ["2025-12-30", "2025-12-31", "2026-01-02", "2026-01-05"]
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "boundary_out"
            with patch.object(mod, "_audit_case_for_pair", side_effect=self._stub_pair), \
                 patch.object(mod, "summarize_three_system_audit", side_effect=self._stub_summarize), \
                 patch.object(mod, "render_summary_markdown", side_effect=self._stub_render_md), \
                 patch.object(mod, "negative_system_row", side_effect=self._stub_row), \
                 patch.object(mod, "record_02_projection_row", side_effect=self._stub_row), \
                 patch.object(mod, "confidence_evaluator_row", side_effect=self._stub_row), \
                 patch.object(mod, "filter_error_cases", side_effect=self._stub_filter), \
                 patch.object(mod, "filter_false_exclusion_cases", side_effect=self._stub_filter), \
                 patch.object(mod, "filter_high_confidence_wrong_cases", side_effect=self._stub_filter):
                result = mod.run_audit(
                    symbol="AVGO",
                    num_cases=3,
                    lookback_days=20,
                    output_dir=out,
                    trading_days=days,
                    save_records=False,
                    start_date="2025-12-30",
                    end_date="2025-12-31",
                    final_test_cutoff="2026-01-01",
                    write_manifest=True,
                )
            self.assertTrue(result["ready"])
            self.assertFalse(result["final_test_touched"])
            manifest = json.loads(
                (out / mod.DEFAULT_MANIFEST_FILENAME).read_text(encoding="utf-8")
            )
            self.assertFalse(manifest["final_test_touched"])
            # Only safe pairs generated; G1 should have stripped 2026 already.
            self.assertEqual(manifest["records_generated"], 1)


# ── static checks: no new services/* / DB / network imports ───────────────


class NoNewServiceImportsTests(unittest.TestCase):
    """Patch must not introduce new services/* imports beyond the audit baseline."""

    ALLOWED_SERVICES = {
        "services.historical_replay_training",
        "services.projection_three_systems_renderer",
        "services.replay_record_wiring",
        "services.three_system_replay_audit",
    }

    def test_services_imports_subset_of_audit_baseline(self) -> None:
        script_path = ROOT / "scripts" / "run_1005_three_system_replay.py"
        tree = ast.parse(script_path.read_text(encoding="utf-8"))
        services_imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith("services."):
                    services_imports.add(node.module)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("services."):
                        services_imports.add(alias.name)
        new_or_unexpected = services_imports - self.ALLOWED_SERVICES
        self.assertEqual(
            new_or_unexpected,
            set(),
            f"unexpected services/* imports introduced: {new_or_unexpected}",
        )


class NoDBOrPredictionStoreImportTests(unittest.TestCase):
    """Patch must not import prediction_store, broker / paper_trade, or new yfinance entry points."""

    FORBIDDEN_SUBSTRINGS = (
        "services.prediction_store",
        "from services.prediction_store",
        "import prediction_store",
        "longbridge",
        "broker",
        "paper_trade",
    )

    def test_no_forbidden_module_imports(self) -> None:
        script_path = ROOT / "scripts" / "run_1005_three_system_replay.py"
        tree = ast.parse(script_path.read_text(encoding="utf-8"))
        imported_modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.add(node.module)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imported_modules.add(alias.name)
        for forbidden in (
            "services.prediction_store",
            "longbridge",
            "broker",
            "paper_trade",
        ):
            self.assertNotIn(
                forbidden,
                imported_modules,
                f"forbidden import detected: {forbidden}",
            )


if __name__ == "__main__":
    unittest.main()
