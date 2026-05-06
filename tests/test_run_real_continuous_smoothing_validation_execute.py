"""Step 3R-3.3C-C-C — real validation execution glue tests.

Covers:
  - get_backup_count counts fixture backups in cwd
  - assert_backup_count_unchanged pass + fail
  - validate_execution_args requires --run-once-real-validation
  - validate_execution_args rejects threshold != 0.60
  - validate_execution_args rejects cutoff != "2026-01-01"
  - validate_execution_args rejects existing output_dir
  - validate_execution_args rejects missing required paths
  - happy path with build_real_validation_inputs / provider /
    orchestrator all mocked: returns real_validation_execution_summary.v1
  - happy path verifies exactly 4 output files
  - DB fingerprint mismatch (mtime / size) raises RuntimeError
  - market_data.db fingerprint mismatch raises RuntimeError
  - backup count mismatch raises RuntimeError
  - tests do not read real W4 jsonl / real 4 csv / real 639 rows
  - CLI without --run-once-real-validation exits 2
  - CLI invalid threshold exits 2
  - CLI invalid cutoff exits 2
  - CLI happy path mocked: exits 0 + prints JSON summary
  - isolation: no forbidden imports
  - isolation: no forbidden strings (allow_overwrite / threshold_sweep /
    skip_db_guard / enable_hard / enable_forced / write_db /
    _PROTECTION_LAYER_CONNECTED / hard_exclusion_allowed /
    forced_exclusion / anti_false_exclusion_triggered)
  - isolation: no direct sqlite3 import
"""
from __future__ import annotations

import argparse
import ast
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.run_real_continuous_smoothing_validation_execute as glue  # noqa: E402
from scripts.run_real_continuous_smoothing_validation_execute import (  # noqa: E402
    EXPECTED_OUTPUT_FILES,
    LOCKED_CANDIDATE_NAME,
    LOCKED_CANDIDATE_THRESHOLD,
    LOCKED_FINAL_TEST_CUTOFF,
    SUMMARY_SCHEMA_VERSION,
    assert_backup_count_unchanged,
    build_execution_summary,
    get_backup_count,
    main,
    run_real_validation_execution,
    validate_execution_args,
)


# ── helpers ─────────────────────────────────────────────────────────────


def _valid_args(
    *,
    tmp: Path,
    output_subdir: str = "out_dir",
    threshold: float = 0.60,
    cutoff: str = "2026-01-01",
    run_once: bool = True,
    skip: tuple[str, ...] = (),
) -> argparse.Namespace:
    """Build a Namespace with all expected attrs filled to valid placeholders."""
    db = tmp / "avgo_agent.db"
    w4_jsonl = tmp / "w4.jsonl"
    w4_manifest = tmp / "manifest.json"
    avgo = tmp / "AVGO.csv"
    nvda = tmp / "NVDA.csv"
    soxx = tmp / "SOXX.csv"
    qqq = tmp / "QQQ.csv"
    out_dir = tmp / output_subdir
    ns = argparse.Namespace(
        run_once_real_validation=run_once,
        db_path=str(db),
        w4_jsonl=str(w4_jsonl),
        w4_manifest=str(w4_manifest),
        avgo_csv=str(avgo),
        nvda_csv=str(nvda),
        soxx_csv=str(soxx),
        qqq_csv=str(qqq),
        candidate_threshold=threshold,
        final_test_cutoff=cutoff,
        output_dir=str(out_dir),
    )
    for attr in skip:
        setattr(ns, attr, None)
    return ns


def _orchestrator_result(
    *,
    records_loaded: int = 5,
    records_adapted: int = 5,
    report_status: str = "fail",
    final_test_touched: bool = False,
) -> dict[str, Any]:
    return {
        "schema_version": "continuous_smoothing_validation_run.v1",
        "candidate_name": LOCKED_CANDIDATE_NAME,
        "candidate_threshold": LOCKED_CANDIDATE_THRESHOLD,
        "records_loaded": records_loaded,
        "records_adapted": records_adapted,
        "report_status": report_status,
        "replay_validation_records": {"records": []},
        "regime_validation_report": {},
        "run_manifest": {
            "schema_version": "regime_validation_run_manifest.v1",
            "candidate_name": LOCKED_CANDIDATE_NAME,
            "candidate_threshold": LOCKED_CANDIDATE_THRESHOLD,
            "fold_count": 4,
            "windows": {},
            "w4_manifest_status": "ok",
            "final_test_cutoff": LOCKED_FINAL_TEST_CUTOFF,
            "final_test_touched": final_test_touched,
            "records_loaded": records_loaded,
            "records_adapted": records_adapted,
            "report_status": report_status,
            "warnings": [],
        },
        "warnings": [],
    }


def _bundle() -> dict[str, Any]:
    return {
        "schema_version": "real_validation_input_bundle.v1",
        "db_path": "x",
        "db_fingerprint": {
            "path": "x", "exists": True, "mtime_ns": 1, "size_bytes": 1,
        },
        "w1_w3_rows": [{"as_of_date": "2024-05-15"}],
        "w4_jsonl_path": "y",
        "w4_rows": [{"as_of_date": "2024-09-15"}],
        "w4_manifest_path": "z",
        "w4_manifest": {
            "schema_version": "w4_replay_manifest.v1",
            "status": "ok",
            "final_test_touched": False,
            "final_test_cutoff": "2026-01-01",
        },
        "final_test_cutoff": "2026-01-01",
        "w4_manifest_status": "ok",
        "warnings": [],
    }


def _write_orchestrator_outputs(output_dir: str) -> None:
    """Side effect: simulate the dry-run orchestrator's 4-file output."""
    p = Path(output_dir)
    p.mkdir(parents=True, exist_ok=False)
    (p / "replay_validation_records.json").write_text("{}", encoding="utf-8")
    (p / "regime_validation_report.json").write_text("{}", encoding="utf-8")
    (p / "regime_validation_summary.md").write_text("# ok\n", encoding="utf-8")
    (p / "run_manifest.json").write_text("{}", encoding="utf-8")


# ── 1. backup count helpers ─────────────────────────────────────────────


class GetBackupCountTests(unittest.TestCase):
    def test_counts_fixture_backups_in_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = os.getcwd()
            try:
                os.chdir(tmp)
                self.assertEqual(get_backup_count(), 0)
                Path("avgo_agent.db.backup_pre_step_1").write_text("a")
                Path("avgo_agent.db.backup_pre_step_2").write_text("b")
                # An unrelated backup file must not match the pattern
                Path("other.db.backup_x").write_text("c")
                self.assertEqual(get_backup_count(), 2)
            finally:
                os.chdir(cwd)


class AssertBackupCountUnchangedTests(unittest.TestCase):
    def test_equal_passes(self) -> None:
        assert_backup_count_unchanged(0, 0)
        assert_backup_count_unchanged(7, 7)

    def test_differs_raises(self) -> None:
        with self.assertRaises(RuntimeError) as ctx:
            assert_backup_count_unchanged(3, 4)
        self.assertIn("db_backup_count_changed", str(ctx.exception))


# ── 2. validate_execution_args ──────────────────────────────────────────


class ValidateExecutionArgsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_requires_run_once_flag(self) -> None:
        args = _valid_args(tmp=self.tmp, run_once=False)
        with self.assertRaises(ValueError) as ctx:
            validate_execution_args(args)
        self.assertIn("missing_explicit_opt_in", str(ctx.exception))

    def test_rejects_threshold_above_lock(self) -> None:
        args = _valid_args(tmp=self.tmp, threshold=0.61)
        with self.assertRaises(ValueError) as ctx:
            validate_execution_args(args)
        self.assertIn("candidate_threshold_locked", str(ctx.exception))

    def test_rejects_threshold_below_lock(self) -> None:
        args = _valid_args(tmp=self.tmp, threshold=0.55)
        with self.assertRaises(ValueError) as ctx:
            validate_execution_args(args)
        self.assertIn("candidate_threshold_locked", str(ctx.exception))

    def test_rejects_cutoff_other_than_2026_01_01(self) -> None:
        for bad in ("2025-12-31", "2026-01-02", "2099-01-01"):
            args = _valid_args(tmp=self.tmp, cutoff=bad)
            with self.assertRaises(ValueError) as ctx:
                validate_execution_args(args)
            self.assertIn("final_test_cutoff_locked", str(ctx.exception))

    def test_rejects_existing_output_dir(self) -> None:
        out = self.tmp / "preexisting"
        out.mkdir()
        args = _valid_args(tmp=self.tmp, output_subdir="preexisting")
        with self.assertRaises(ValueError) as ctx:
            validate_execution_args(args)
        self.assertIn("output_dir_exists", str(ctx.exception))

    def test_rejects_missing_required_paths(self) -> None:
        for attr in (
            "db_path",
            "w4_jsonl",
            "w4_manifest",
            "avgo_csv",
            "nvda_csv",
            "soxx_csv",
            "qqq_csv",
            "output_dir",
        ):
            args = _valid_args(tmp=self.tmp)
            setattr(args, attr, None)
            with self.assertRaises(ValueError) as ctx:
                validate_execution_args(args)
            self.assertIn("missing_required_args", str(ctx.exception))

    def test_happy_path_does_not_raise(self) -> None:
        args = _valid_args(tmp=self.tmp)
        # Make output_dir not exist
        validate_execution_args(args)


# ── 3. build_execution_summary ──────────────────────────────────────────


class BuildExecutionSummaryTests(unittest.TestCase):
    def test_summary_shape(self) -> None:
        summary = build_execution_summary(
            output_dir="/tmp/abc",
            records_loaded=639,
            records_adapted=600,
            report_status="fail",
            final_test_touched=False,
            db_unchanged=True,
            backup_count_unchanged=True,
            output_files=list(EXPECTED_OUTPUT_FILES),
        )
        self.assertEqual(summary["schema_version"], SUMMARY_SCHEMA_VERSION)
        self.assertEqual(summary["candidate_name"], LOCKED_CANDIDATE_NAME)
        self.assertEqual(
            summary["candidate_threshold"], LOCKED_CANDIDATE_THRESHOLD
        )
        self.assertEqual(
            summary["final_test_cutoff"], LOCKED_FINAL_TEST_CUTOFF
        )
        self.assertEqual(summary["records_loaded"], 639)
        self.assertEqual(summary["records_adapted"], 600)
        self.assertEqual(summary["report_status"], "fail")
        self.assertFalse(summary["final_test_touched"])
        self.assertTrue(summary["db_unchanged"])
        self.assertTrue(summary["backup_count_unchanged"])
        self.assertEqual(
            sorted(summary["output_files"]), sorted(EXPECTED_OUTPUT_FILES)
        )


# ── 4. run_real_validation_execution (heavy fns mocked) ─────────────────


class RunRealValidationExecutionHappyPathTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        # Create the DB file so get_db_fingerprint sees mtime_ns / size_bytes
        (self.tmp / "avgo_agent.db").write_bytes(b"db bytes v1")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _patch_heavy_calls(
        self,
        *,
        orchestrator_result: dict[str, Any],
        bundle: dict[str, Any] | None = None,
    ):
        """Patch wrapper / provider / orchestrator. The orchestrator
        side-effect-writes the four output files into output_dir."""
        captured: dict[str, Any] = {}

        def fake_inputs(**kwargs):
            captured["inputs_kwargs"] = kwargs
            return bundle if bundle is not None else _bundle()

        def fake_provider_factory(**kwargs):
            captured["provider_kwargs"] = kwargs
            return lambda as_of_date, row=None: {
                "schema_version": "regime_labels.v1",
                "as_of_date": as_of_date,
                "data_cutoff_date": as_of_date,
                "labels": {},
                "raw_features": {},
                "warnings": [],
                "final_test_refusal": False,
            }

        def fake_run(replay_rows, **kwargs):
            captured["orchestrator_kwargs"] = kwargs
            captured["replay_rows_count"] = len(replay_rows)
            output_dir = kwargs.get("output_dir")
            assert output_dir, "orchestrator must receive output_dir"
            _write_orchestrator_outputs(str(output_dir))
            return orchestrator_result

        return (
            mock.patch.object(
                glue, "build_real_validation_inputs", side_effect=fake_inputs
            ),
            mock.patch.object(
                glue,
                "build_real_regime_label_provider",
                side_effect=fake_provider_factory,
            ),
            mock.patch.object(
                glue,
                "run_continuous_smoothing_validation",
                side_effect=fake_run,
            ),
            captured,
        )

    def test_happy_path_returns_summary_and_writes_4_files(self) -> None:
        result = _orchestrator_result(
            records_loaded=2, records_adapted=2, report_status="fail"
        )
        p_inputs, p_provider, p_run, captured = self._patch_heavy_calls(
            orchestrator_result=result
        )
        args = _valid_args(tmp=self.tmp)
        with p_inputs, p_provider, p_run:
            summary = run_real_validation_execution(args)

        self.assertEqual(summary["schema_version"], SUMMARY_SCHEMA_VERSION)
        self.assertEqual(
            summary["candidate_threshold"], LOCKED_CANDIDATE_THRESHOLD
        )
        self.assertEqual(
            summary["final_test_cutoff"], LOCKED_FINAL_TEST_CUTOFF
        )
        self.assertEqual(summary["records_loaded"], 2)
        self.assertEqual(summary["records_adapted"], 2)
        self.assertEqual(summary["report_status"], "fail")
        self.assertFalse(summary["final_test_touched"])
        self.assertTrue(summary["db_unchanged"])
        self.assertTrue(summary["backup_count_unchanged"])
        self.assertEqual(
            sorted(summary["output_files"]), sorted(EXPECTED_OUTPUT_FILES)
        )
        # 4 files exist on disk
        out = Path(args.output_dir)
        for name in EXPECTED_OUTPUT_FILES:
            self.assertTrue(
                (out / name).exists(),
                f"expected orchestrator-written file {name} to exist",
            )
        # orchestrator received the locked threshold + cutoff
        kwargs = captured["orchestrator_kwargs"]
        self.assertEqual(
            kwargs["candidate_threshold"], LOCKED_CANDIDATE_THRESHOLD
        )
        self.assertEqual(
            kwargs["final_test_cutoff"], LOCKED_FINAL_TEST_CUTOFF
        )
        self.assertTrue(kwargs["write_outputs"])
        self.assertEqual(kwargs["candidate_name"], LOCKED_CANDIDATE_NAME)
        # all rows propagated (1 W1-W3 + 1 W4 = 2)
        self.assertEqual(captured["replay_rows_count"], 2)

    def test_missing_output_file_raises(self) -> None:
        result = _orchestrator_result()

        def fake_inputs(**kwargs):
            return _bundle()

        def fake_provider_factory(**kwargs):
            return lambda as_of_date, row=None: {
                "schema_version": "regime_labels.v1",
                "as_of_date": as_of_date,
                "data_cutoff_date": as_of_date,
                "labels": {},
                "raw_features": {},
                "warnings": [],
                "final_test_refusal": False,
            }

        def fake_run_missing_file(replay_rows, **kwargs):
            output_dir = kwargs["output_dir"]
            p = Path(output_dir)
            p.mkdir(parents=True, exist_ok=False)
            # Only 3 of 4 files
            (p / "replay_validation_records.json").write_text("{}")
            (p / "regime_validation_report.json").write_text("{}")
            (p / "regime_validation_summary.md").write_text("ok")
            return result

        args = _valid_args(tmp=self.tmp)
        with mock.patch.object(
            glue, "build_real_validation_inputs", side_effect=fake_inputs
        ), mock.patch.object(
            glue,
            "build_real_regime_label_provider",
            side_effect=fake_provider_factory,
        ), mock.patch.object(
            glue,
            "run_continuous_smoothing_validation",
            side_effect=fake_run_missing_file,
        ):
            with self.assertRaises(RuntimeError) as ctx:
                run_real_validation_execution(args)
        self.assertIn("output_files_missing", str(ctx.exception))


# ── 5. DB / market-data / backup mismatch ───────────────────────────────


class GuardMismatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        (self.tmp / "avgo_agent.db").write_bytes(b"v0")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _common_patches(
        self,
        *,
        run_side_effect,
        bundle: dict[str, Any] | None = None,
    ):
        def fake_inputs(**kwargs):
            return bundle if bundle is not None else _bundle()

        def fake_provider_factory(**kwargs):
            return lambda as_of_date, row=None: {
                "schema_version": "regime_labels.v1",
                "as_of_date": as_of_date,
                "data_cutoff_date": as_of_date,
                "labels": {},
                "raw_features": {},
                "warnings": [],
                "final_test_refusal": False,
            }

        return (
            mock.patch.object(
                glue, "build_real_validation_inputs", side_effect=fake_inputs
            ),
            mock.patch.object(
                glue,
                "build_real_regime_label_provider",
                side_effect=fake_provider_factory,
            ),
            mock.patch.object(
                glue,
                "run_continuous_smoothing_validation",
                side_effect=run_side_effect,
            ),
        )

    def test_db_size_mismatch_raises(self) -> None:
        result = _orchestrator_result()

        def fake_run(replay_rows, **kwargs):
            output_dir = kwargs["output_dir"]
            _write_orchestrator_outputs(str(output_dir))
            # Simulate a DB write during the run by appending bytes
            db_path = Path(self.tmp) / "avgo_agent.db"
            with db_path.open("ab") as fh:
                fh.write(b"extra bytes")
            return result

        p_inputs, p_provider, p_run = self._common_patches(
            run_side_effect=fake_run
        )
        args = _valid_args(tmp=self.tmp)
        with p_inputs, p_provider, p_run:
            with self.assertRaises(RuntimeError) as ctx:
                run_real_validation_execution(args)
        self.assertIn("db_modified", str(ctx.exception))

    def test_db_mtime_mismatch_raises(self) -> None:
        result = _orchestrator_result()

        def fake_run(replay_rows, **kwargs):
            output_dir = kwargs["output_dir"]
            _write_orchestrator_outputs(str(output_dir))
            # Simulate touching mtime without changing size
            db_path = Path(self.tmp) / "avgo_agent.db"
            st = db_path.stat()
            future_ns = st.st_mtime_ns + 1_000_000_000
            os.utime(db_path, ns=(future_ns, future_ns))
            return result

        p_inputs, p_provider, p_run = self._common_patches(
            run_side_effect=fake_run
        )
        args = _valid_args(tmp=self.tmp)
        with p_inputs, p_provider, p_run:
            with self.assertRaises(RuntimeError) as ctx:
                run_real_validation_execution(args)
        self.assertIn("db_modified", str(ctx.exception))

    def test_backup_count_mismatch_raises(self) -> None:
        result = _orchestrator_result()

        def fake_run(replay_rows, **kwargs):
            output_dir = kwargs["output_dir"]
            _write_orchestrator_outputs(str(output_dir))
            # Simulate a backup file appearing during the run.
            # The backup count is glob'd from cwd, so create the
            # backup in cwd and clean it up afterwards.
            sentinel = Path(
                "avgo_agent.db.backup_pretend_step_3r3_3c_c_c"
            )
            sentinel.write_text("pretend")
            self.addCleanup(sentinel.unlink, missing_ok=True)
            return result

        p_inputs, p_provider, p_run = self._common_patches(
            run_side_effect=fake_run
        )
        args = _valid_args(tmp=self.tmp)
        # The backup pattern is glob'd from cwd; ensure the cwd is a
        # clean tmp dir so the test does not rely on the repo's actual
        # backup files.
        cwd = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as cwd_tmp:
                os.chdir(cwd_tmp)
                with p_inputs, p_provider, p_run:
                    with self.assertRaises(RuntimeError) as ctx:
                        run_real_validation_execution(args)
                self.assertIn("db_backup_count_changed", str(ctx.exception))
        finally:
            os.chdir(cwd)

    def test_market_data_db_mismatch_raises(self) -> None:
        # Pre-create data/market_data.db in a controlled cwd so the guard
        # picks it up; simulate the orchestrator mutating it.
        result = _orchestrator_result()
        cwd = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as cwd_tmp:
                os.chdir(cwd_tmp)
                data_dir = Path(cwd_tmp) / "data"
                data_dir.mkdir()
                market_db = data_dir / "market_data.db"
                market_db.write_bytes(b"v0")

                def fake_run(replay_rows, **kwargs):
                    output_dir = kwargs["output_dir"]
                    _write_orchestrator_outputs(str(output_dir))
                    # mutate market_data.db
                    with market_db.open("ab") as fh:
                        fh.write(b"changed")
                    return result

                p_inputs, p_provider, p_run = self._common_patches(
                    run_side_effect=fake_run
                )
                args = _valid_args(tmp=self.tmp)
                with p_inputs, p_provider, p_run:
                    with self.assertRaises(RuntimeError) as ctx:
                        run_real_validation_execution(args)
                self.assertIn("db_modified", str(ctx.exception))
        finally:
            os.chdir(cwd)


# ── 6. CLI ─────────────────────────────────────────────────────────────


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        (self.tmp / "avgo_agent.db").write_bytes(b"db v0")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _common_argv(
        self,
        *,
        threshold: str = "0.60",
        cutoff: str = "2026-01-01",
        with_run_once: bool = True,
        out_subdir: str = "out_cli",
    ) -> list[str]:
        argv: list[str] = []
        if with_run_once:
            argv.append("--run-once-real-validation")
        argv += [
            "--db-path", str(self.tmp / "avgo_agent.db"),
            "--w4-jsonl", str(self.tmp / "w4.jsonl"),
            "--w4-manifest", str(self.tmp / "manifest.json"),
            "--avgo-csv", str(self.tmp / "AVGO.csv"),
            "--nvda-csv", str(self.tmp / "NVDA.csv"),
            "--soxx-csv", str(self.tmp / "SOXX.csv"),
            "--qqq-csv", str(self.tmp / "QQQ.csv"),
            "--candidate-threshold", threshold,
            "--final-test-cutoff", cutoff,
            "--output-dir", str(self.tmp / out_subdir),
        ]
        return argv

    def test_no_run_once_flag_exits_2(self) -> None:
        err = io.StringIO()
        with redirect_stderr(err):
            rc = main(self._common_argv(with_run_once=False))
        self.assertEqual(rc, 2)
        self.assertIn("missing_explicit_opt_in", err.getvalue())

    def test_invalid_threshold_exits_2(self) -> None:
        err = io.StringIO()
        with redirect_stderr(err):
            rc = main(self._common_argv(threshold="0.61"))
        self.assertEqual(rc, 2)
        self.assertIn("candidate_threshold_locked", err.getvalue())

    def test_invalid_cutoff_exits_2(self) -> None:
        err = io.StringIO()
        with redirect_stderr(err):
            rc = main(self._common_argv(cutoff="2025-12-31"))
        self.assertEqual(rc, 2)
        self.assertIn("final_test_cutoff_locked", err.getvalue())

    def test_existing_output_dir_exits_2(self) -> None:
        out = self.tmp / "preexist"
        out.mkdir()
        err = io.StringIO()
        with redirect_stderr(err):
            rc = main(self._common_argv(out_subdir="preexist"))
        self.assertEqual(rc, 2)
        self.assertIn("output_dir_exists", err.getvalue())

    def test_does_not_accept_forbidden_flags(self) -> None:
        # argparse should reject these unknown flags.
        err = io.StringIO()
        with redirect_stderr(err):
            with self.assertRaises(SystemExit):
                main(
                    self._common_argv()
                    + ["--allow-overwrite"]
                )
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                main(self._common_argv() + ["--threshold-sweep"])
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                main(self._common_argv() + ["--skip-db-guard"])
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                main(self._common_argv() + ["--write-db"])
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                main(self._common_argv() + ["--enable-hard"])
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                main(self._common_argv() + ["--enable-forced"])
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                main(self._common_argv() + ["--allow-network"])

    def test_happy_path_mocked_exits_0_and_prints_json(self) -> None:
        result = _orchestrator_result(
            records_loaded=2, records_adapted=2, report_status="fail"
        )

        def fake_inputs(**kwargs):
            return _bundle()

        def fake_provider_factory(**kwargs):
            return lambda as_of_date, row=None: {
                "schema_version": "regime_labels.v1",
                "as_of_date": as_of_date,
                "data_cutoff_date": as_of_date,
                "labels": {},
                "raw_features": {},
                "warnings": [],
                "final_test_refusal": False,
            }

        def fake_run(replay_rows, **kwargs):
            _write_orchestrator_outputs(str(kwargs["output_dir"]))
            return result

        out = io.StringIO()
        cwd = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as cwd_tmp:
                os.chdir(cwd_tmp)
                with mock.patch.object(
                    glue,
                    "build_real_validation_inputs",
                    side_effect=fake_inputs,
                ), mock.patch.object(
                    glue,
                    "build_real_regime_label_provider",
                    side_effect=fake_provider_factory,
                ), mock.patch.object(
                    glue,
                    "run_continuous_smoothing_validation",
                    side_effect=fake_run,
                ), redirect_stdout(out):
                    rc = main(self._common_argv())
        finally:
            os.chdir(cwd)
        self.assertEqual(rc, 0)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["schema_version"], SUMMARY_SCHEMA_VERSION)
        self.assertEqual(
            payload["candidate_threshold"], LOCKED_CANDIDATE_THRESHOLD
        )
        self.assertEqual(
            payload["final_test_cutoff"], LOCKED_FINAL_TEST_CUTOFF
        )
        self.assertEqual(payload["report_status"], "fail")
        self.assertTrue(payload["db_unchanged"])
        self.assertTrue(payload["backup_count_unchanged"])
        self.assertEqual(
            sorted(payload["output_files"]), sorted(EXPECTED_OUTPUT_FILES)
        )


# ── 7. isolation: forbidden imports / strings ───────────────────────────


class IsolationTests(unittest.TestCase):
    def _module_text(self) -> str:
        return Path(glue.__file__).read_text(encoding="utf-8")

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
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn(alias.name, forbidden)
            elif isinstance(node, ast.ImportFrom):
                self.assertNotIn(node.module, forbidden)

    def test_no_direct_sqlite3_import(self) -> None:
        text = self._module_text()
        # The execution glue must not directly import sqlite3 — the
        # wrapper handles read-only DB access via mode=ro URI.
        for needle in ("import sqlite3", "from sqlite3"):
            self.assertNotIn(needle, text)

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
            "yfinance",
            "paper_trade",
            "longbridge",
        ):
            self.assertNotIn(
                forbidden,
                text,
                f"glue unexpectedly references {forbidden!r}",
            )

    def test_no_threshold_sweep_or_override_strings(self) -> None:
        text = self._module_text()
        for forbidden in (
            "thresholds = [",
            "for threshold in",
            "for t in thresholds",
            "candidate_thresholds",
            "threshold_grid",
            "optimize_threshold",
            "sweep_threshold",
            "--allow-overwrite",
            "--threshold-sweep",
            "--skip-db-guard",
            "--write-db",
            "--enable-hard",
            "--enable-forced",
            "--allow-network",
            "--ignore-final-test-cutoff",
            "--connect-protection-layer",
        ):
            self.assertNotIn(forbidden, text)

    def test_sources_only_locked_threshold_and_cutoff(self) -> None:
        text = self._module_text()
        # Threshold and cutoff are stamped as module-level constants.
        self.assertIn("LOCKED_CANDIDATE_THRESHOLD = 0.60", text)
        self.assertIn(
            'LOCKED_FINAL_TEST_CUTOFF = "2026-01-01"', text
        )


if __name__ == "__main__":
    unittest.main()
