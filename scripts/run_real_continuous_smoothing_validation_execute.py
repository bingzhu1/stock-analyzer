"""scripts/run_real_continuous_smoothing_validation_execute.py — one-shot execution glue.

Step 3R-3.3C-C-C implementation per Step 3R-3.3C-C-C execution glue
design (commit ``0bf9151``) + checkpoint (``90c0b4e``).

This module is **read-only diagnostics**:
- never writes DB; never imports DB write paths, network clients,
  market-data clients, trading clients, or production-stack modules
  (see test file for the full forbidden-import list)
- never imports ``sqlite3`` directly; DB access is delegated entirely
  to ``scripts.run_real_continuous_smoothing_validation`` (which uses
  ``mode=ro`` URI form)
- threshold is locked at 0.60 (v1 design seed); CLI rejects any other
  value (no sweep, no tuning, no retry-with-different-value)
- final-test cutoff is locked at "2026-01-01"; CLI rejects any other
  value (no silent override)
- output_dir must NOT exist; orchestrator refuses to overwrite
- DB fingerprint is recorded before and after the run; mismatch raises
- ``avgo_agent.db.backup_*`` glob count is recorded before and after;
  mismatch raises
- ``data/market_data.db`` (if it exists) is also fingerprinted before
  and after; mismatch raises
- the script is **opt-in only**: the CLI requires explicit
  ``--run-once-real-validation``; without it, exit 2

Public API:
    get_backup_count(pattern="avgo_agent.db.backup_*") -> int
    assert_backup_count_unchanged(before, after) -> None
    validate_execution_args(args) -> None
    build_execution_summary(...) -> dict
    run_real_validation_execution(args) -> dict
    main(argv=None) -> int

CLI:
    python3 scripts/run_real_continuous_smoothing_validation_execute.py \\
        --run-once-real-validation \\
        --db-path avgo_agent.db \\
        --w4-jsonl <path> \\
        --w4-manifest <path> \\
        --avgo-csv data/AVGO.csv \\
        --nvda-csv data/NVDA.csv \\
        --soxx-csv data/SOXX.csv \\
        --qqq-csv data/QQQ.csv \\
        --candidate-threshold 0.60 \\
        --final-test-cutoff 2026-01-01 \\
        --output-dir logs/regime_validation/continuous_smoothing_v1_real_w1_w4_<TS>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from scripts.run_continuous_smoothing_validation import (
    run_continuous_smoothing_validation,
)
from scripts.run_real_continuous_smoothing_validation import (
    assert_db_unchanged,
    build_real_validation_inputs,
    get_db_fingerprint,
)
from services.real_regime_label_provider import (
    build_real_regime_label_provider,
)


SUMMARY_SCHEMA_VERSION = "real_validation_execution_summary.v1"
LOCKED_CANDIDATE_THRESHOLD = 0.60
LOCKED_FINAL_TEST_CUTOFF = "2026-01-01"
LOCKED_CANDIDATE_NAME = "continuous_smoothing_v1"
DEFAULT_BACKUP_PATTERN = "avgo_agent.db.backup_*"
DEFAULT_MARKET_DATA_DB_PATH = "data/market_data.db"

EXPECTED_OUTPUT_FILES: tuple[str, ...] = (
    "replay_validation_records.json",
    "regime_validation_report.json",
    "regime_validation_summary.md",
    "run_manifest.json",
)


# ── backup count guard ──────────────────────────────────────────────────


def get_backup_count(pattern: str = DEFAULT_BACKUP_PATTERN) -> int:
    """Return the number of files matching ``pattern`` in the cwd.

    Pattern is glob-style (relative to the current working directory).
    Used to assert no DB backup files appeared during a real run.
    """
    return len(list(Path(".").glob(pattern)))


def assert_backup_count_unchanged(before: int, after: int) -> None:
    """Raise ``RuntimeError`` if ``after`` differs from ``before``."""
    if int(before) != int(after):
        raise RuntimeError(
            f"db_backup_count_changed:before={before},after={after}"
        )


# ── arg validation ──────────────────────────────────────────────────────


def validate_execution_args(args: argparse.Namespace) -> None:
    """Validate the parsed CLI args against the v1 lock invariants.

    Raises ``ValueError`` (with a stable error code prefix) on any
    violation. The CLI translates these into ``return 2`` + stderr.
    """
    if not getattr(args, "run_once_real_validation", False):
        raise ValueError(
            "missing_explicit_opt_in:--run-once-real-validation is required"
        )

    required = (
        ("db_path", "--db-path"),
        ("w4_jsonl", "--w4-jsonl"),
        ("w4_manifest", "--w4-manifest"),
        ("avgo_csv", "--avgo-csv"),
        ("nvda_csv", "--nvda-csv"),
        ("soxx_csv", "--soxx-csv"),
        ("qqq_csv", "--qqq-csv"),
        ("output_dir", "--output-dir"),
    )
    missing = [
        flag for attr, flag in required if not getattr(args, attr, None)
    ]
    if missing:
        raise ValueError(
            f"missing_required_args:{','.join(missing)}"
        )

    threshold = getattr(args, "candidate_threshold", None)
    if threshold is None or float(threshold) != LOCKED_CANDIDATE_THRESHOLD:
        raise ValueError(
            f"candidate_threshold_locked:expected={LOCKED_CANDIDATE_THRESHOLD},"
            f"got={threshold!r}"
        )

    cutoff = getattr(args, "final_test_cutoff", None)
    if cutoff != LOCKED_FINAL_TEST_CUTOFF:
        raise ValueError(
            f"final_test_cutoff_locked:expected={LOCKED_FINAL_TEST_CUTOFF!r},"
            f"got={cutoff!r}"
        )

    out_path = Path(args.output_dir)
    if out_path.exists():
        raise ValueError(
            f"output_dir_exists:{out_path} must not exist; refuse to overwrite"
        )


# ── execution summary ───────────────────────────────────────────────────


def build_execution_summary(
    *,
    output_dir: str,
    records_loaded: int,
    records_adapted: int,
    report_status: str,
    final_test_touched: bool,
    db_unchanged: bool,
    backup_count_unchanged: bool,
    output_files: list[str],
) -> dict[str, Any]:
    """Assemble the summary dict returned by ``run_real_validation_execution``."""
    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "candidate_name": LOCKED_CANDIDATE_NAME,
        "candidate_threshold": LOCKED_CANDIDATE_THRESHOLD,
        "final_test_cutoff": LOCKED_FINAL_TEST_CUTOFF,
        "output_dir": str(output_dir),
        "records_loaded": int(records_loaded),
        "records_adapted": int(records_adapted),
        "report_status": str(report_status),
        "final_test_touched": bool(final_test_touched),
        "db_unchanged": bool(db_unchanged),
        "backup_count_unchanged": bool(backup_count_unchanged),
        "output_files": list(output_files),
    }


# ── orchestrator ────────────────────────────────────────────────────────


def _verify_output_files(output_dir: str) -> list[str]:
    """Verify the orchestrator wrote exactly the four expected files."""
    out = Path(output_dir)
    if not out.is_dir():
        raise RuntimeError(
            f"output_dir_missing_after_run:{out}"
        )
    actual = sorted(p.name for p in out.iterdir() if p.is_file())
    expected = sorted(EXPECTED_OUTPUT_FILES)
    missing = [name for name in expected if name not in actual]
    if missing:
        raise RuntimeError(
            f"output_files_missing:{missing} in {out}"
        )
    return list(EXPECTED_OUTPUT_FILES)


def run_real_validation_execution(
    args: argparse.Namespace,
) -> dict[str, Any]:
    """One-shot real validation execution glue.

    See module docstring for full read-only constraints.

    The function:
    - validates CLI args (locks)
    - records DB + market_data DB fingerprints + backup count BEFORE
    - calls the wrapper to assemble the input bundle
    - builds the real CSV-backed regime label provider
    - calls the dry-run orchestrator with ``write_outputs=True``
    - verifies the four output files exist
    - records DB + market_data DB fingerprints + backup count AFTER
    - asserts no DB / market_data DB / backup count changes
    - returns a ``real_validation_execution_summary.v1`` dict
    """
    validate_execution_args(args)

    db_fp_before = get_db_fingerprint(args.db_path)
    market_db_path = Path(DEFAULT_MARKET_DATA_DB_PATH)
    market_fp_before = (
        get_db_fingerprint(str(market_db_path))
        if market_db_path.exists()
        else None
    )
    backup_before = get_backup_count(DEFAULT_BACKUP_PATTERN)

    bundle = build_real_validation_inputs(
        db_path=args.db_path,
        w4_jsonl_path=args.w4_jsonl,
        w4_manifest_path=args.w4_manifest,
        final_test_cutoff=args.final_test_cutoff,
    )

    provider = build_real_regime_label_provider(
        avgo_csv_path=args.avgo_csv,
        nvda_csv_path=args.nvda_csv,
        soxx_csv_path=args.soxx_csv,
        qqq_csv_path=args.qqq_csv,
        final_test_cutoff=args.final_test_cutoff,
    )

    replay_rows = list(bundle["w1_w3_rows"]) + list(bundle["w4_rows"])

    result = run_continuous_smoothing_validation(
        replay_rows,
        regime_label_provider=provider,
        w4_manifest=bundle["w4_manifest"],
        candidate_threshold=LOCKED_CANDIDATE_THRESHOLD,
        candidate_name=LOCKED_CANDIDATE_NAME,
        final_test_cutoff=args.final_test_cutoff,
        output_dir=args.output_dir,
        write_outputs=True,
    )

    output_files = _verify_output_files(args.output_dir)

    db_fp_after = get_db_fingerprint(args.db_path)
    assert_db_unchanged(db_fp_before, db_fp_after)
    if market_fp_before is not None:
        market_fp_after = get_db_fingerprint(str(market_db_path))
        assert_db_unchanged(market_fp_before, market_fp_after)

    backup_after = get_backup_count(DEFAULT_BACKUP_PATTERN)
    assert_backup_count_unchanged(backup_before, backup_after)

    run_manifest = result.get("run_manifest", {}) or {}

    return build_execution_summary(
        output_dir=args.output_dir,
        records_loaded=int(result.get("records_loaded", 0)),
        records_adapted=int(result.get("records_adapted", 0)),
        report_status=str(result.get("report_status", "error")),
        final_test_touched=bool(run_manifest.get("final_test_touched", False)),
        db_unchanged=True,
        backup_count_unchanged=True,
        output_files=output_files,
    )


# ── CLI ─────────────────────────────────────────────────────────────────


def _build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_real_continuous_smoothing_validation_execute",
        description=(
            "Step 3R-3.3C-C-C one-shot real W1-W4 validation execution glue. "
            "Locks: candidate_threshold=0.60, final_test_cutoff=2026-01-01. "
            "Requires --run-once-real-validation. Does not write DB. Does "
            "not connect to network or trading APIs. Output dir must not "
            "exist; the four files written are local untracked diagnostics."
        ),
    )
    parser.add_argument(
        "--run-once-real-validation",
        dest="run_once_real_validation",
        action="store_true",
        help="Required: explicit opt-in for the one-shot real run.",
    )
    parser.add_argument("--db-path", dest="db_path", default=None)
    parser.add_argument("--w4-jsonl", dest="w4_jsonl", default=None)
    parser.add_argument("--w4-manifest", dest="w4_manifest", default=None)
    parser.add_argument("--avgo-csv", dest="avgo_csv", default=None)
    parser.add_argument("--nvda-csv", dest="nvda_csv", default=None)
    parser.add_argument("--soxx-csv", dest="soxx_csv", default=None)
    parser.add_argument("--qqq-csv", dest="qqq_csv", default=None)
    parser.add_argument(
        "--candidate-threshold",
        dest="candidate_threshold",
        type=float,
        default=LOCKED_CANDIDATE_THRESHOLD,
    )
    parser.add_argument(
        "--final-test-cutoff",
        dest="final_test_cutoff",
        default=LOCKED_FINAL_TEST_CUTOFF,
    )
    parser.add_argument("--output-dir", dest="output_dir", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_cli_parser()
    args = parser.parse_args(argv)

    try:
        validate_execution_args(args)
    except ValueError as exc:
        print(f"refuse_to_run:{exc}", file=sys.stderr)
        return 2

    try:
        summary = run_real_validation_execution(args)
    except Exception as exc:  # pragma: no cover — caller-visible
        print(f"execution_failed:{type(exc).__name__}:{exc}", file=sys.stderr)
        return 2

    json.dump(summary, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
