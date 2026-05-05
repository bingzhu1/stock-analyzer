"""Task 072 — 1005-day three-system replay audit (offline only).

Runs the existing projection v2 chain over the most recent 1005 trading-day pairs
for AVGO, reshapes each result through the three-system renderer, and writes the
required statistics + case CSVs to ``logs/historical_training/three_system_1005/``.

This script is offline-only: no broker, no automation, no live trading.

Usage
-----
    python -m scripts.run_1005_three_system_replay
    python -m scripts.run_1005_three_system_replay --num-cases 50    # smoke run

The script tolerates partial yfinance / projection failures: each case runs
independently, and degraded cases still appear in the JSONL log with
``ready=false`` so the audit always finishes.
"""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.historical_replay_training import run_historical_replay_for_date
from services.projection_three_systems_renderer import build_projection_three_systems
from services.replay_record_wiring import save_replay_batch_projection_records
from services.three_system_replay_audit import (
    build_audit_case,
    confidence_evaluator_row,
    filter_error_cases,
    filter_false_exclusion_cases,
    filter_high_confidence_wrong_cases,
    negative_system_row,
    record_02_projection_row,
    render_summary_markdown,
    summarize_three_system_audit,
)

DEFAULT_NUM_CASES = 1005
DEFAULT_LOOKBACK_DAYS = 20
DEFAULT_SYMBOL = "AVGO"
DEFAULT_OUTPUT_DIR = ROOT / "logs" / "historical_training" / "three_system_1005"
DEFAULT_DB_PATH = ROOT / "data" / "market_data.db"

# Step 2G-8D.1A — W4 cross-window validation guards
DEFAULT_FINAL_TEST_CUTOFF = "2026-01-01"
W4_RANGE_LOWER_BOUND = "2024-08-03"
TINY_SMOKE_DEFAULT_START = "2024-08-05"
TINY_SMOKE_DEFAULT_END = "2024-08-09"
TINY_SMOKE_DEFAULT_OUTPUT_DIR = (
    ROOT
    / "logs"
    / "historical_training"
    / "three_system_w4_smoke_2024_08_05_2024_08_09"
)
MANIFEST_SCHEMA_VERSION = "w4_replay_manifest.v1"
DEFAULT_MANIFEST_FILENAME = "validation_ready_manifest.json"


def _log(message: str) -> None:
    print(f"[task072] {message}", flush=True)


def _load_avgo_trading_days(*, symbol: str, minimum_days: int) -> list[str]:
    """Pull AVGO trading dates via yfinance (matches the avgo_1000day_training default)."""
    import yfinance as yf

    ticker = yf.Ticker(symbol)
    history = ticker.history(period="10y", interval="1d")
    if history.empty:
        return []

    index = history.index
    if getattr(index, "tz", None) is not None:
        index = index.tz_localize(None)

    seen: set[str] = set()
    dates: list[str] = []
    for raw_date in index:
        text = raw_date.strftime("%Y-%m-%d")
        if text in seen:
            continue
        seen.add(text)
        dates.append(text)

    dates.sort()
    if minimum_days > 0:
        return dates[-minimum_days:]
    return dates


def _build_date_pairs(days: list[str], *, num_cases: int) -> list[tuple[str, str]]:
    if num_cases <= 0 or len(days) < 2:
        return []
    trimmed = days[-(num_cases + 1):]
    return [(trimmed[i], trimmed[i + 1]) for i in range(len(trimmed) - 1)]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, default=str))
            fh.write("\n")


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2, default=str)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]], *, header: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=header)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in header})


# ── Step 2G-8D.1A — W4 helpers (range / cutoff / manifest) ─────────────────

def _is_w4_mode(args: argparse.Namespace) -> bool:
    """W4 mode = explicit start/end OR --tiny-smoke flag."""
    if getattr(args, "tiny_smoke", False):
        return True
    if getattr(args, "start_date", None) is not None:
        return True
    if getattr(args, "end_date", None) is not None:
        return True
    return False


def _apply_tiny_smoke_defaults(args: argparse.Namespace) -> argparse.Namespace:
    """Fill in tiny-smoke defaults when --tiny-smoke is set.

    Forces save_records=False and write_manifest=True regardless of caller
    input — tiny-smoke must never write DB and must always emit manifest.
    """
    if not getattr(args, "tiny_smoke", False):
        return args
    if getattr(args, "start_date", None) is None:
        args.start_date = TINY_SMOKE_DEFAULT_START
    if getattr(args, "end_date", None) is None:
        args.end_date = TINY_SMOKE_DEFAULT_END
    if args.output_dir == DEFAULT_OUTPUT_DIR:
        args.output_dir = TINY_SMOKE_DEFAULT_OUTPUT_DIR
    args.save_records = False
    args.write_manifest = True
    return args


def _validate_w4_args(args: argparse.Namespace) -> None:
    """Apply startup-time hard guards (G1 / G3 / G4). Raise ValueError on first violation.

    G1 — start_date / end_date must be strictly < final_test_cutoff
    G3 — --save-records is forbidden in W4 mode
    G4 — output_dir must not be the 1005 baseline; must not overwrite a
         non-empty existing dir without --allow-overwrite (W4 mode only)
    """
    cutoff = args.final_test_cutoff

    # G1 startup
    if args.start_date is not None and args.start_date >= cutoff:
        raise ValueError(
            f"G1 violation: start_date={args.start_date} must be < "
            f"final_test_cutoff={cutoff}"
        )
    if args.end_date is not None and args.end_date >= cutoff:
        raise ValueError(
            f"G1 violation: end_date={args.end_date} must be < "
            f"final_test_cutoff={cutoff}"
        )
    if args.start_date is not None and args.end_date is not None:
        if args.start_date > args.end_date:
            raise ValueError(
                f"G1 violation: start_date={args.start_date} > "
                f"end_date={args.end_date}"
            )

    in_w4 = _is_w4_mode(args)

    # G3 save-records guard
    if in_w4 and args.save_records:
        raise ValueError(
            "G3 violation: --save-records is not allowed in W4 / tiny-smoke "
            "mode (must not write DB)."
        )

    # G4 output_dir guard
    if in_w4:
        try:
            same_as_1005 = args.output_dir.resolve() == DEFAULT_OUTPUT_DIR.resolve()
        except OSError:
            same_as_1005 = False
        if same_as_1005:
            raise ValueError(
                "G4 violation: output_dir must not point at the 1005 baseline "
                f"({DEFAULT_OUTPUT_DIR}); use a W4-specific directory."
            )
        if (
            args.output_dir.exists()
            and any(args.output_dir.iterdir())
            and not args.allow_overwrite
        ):
            raise ValueError(
                f"G4 violation: output_dir {args.output_dir} already exists "
                "and is non-empty; pass --allow-overwrite to proceed."
            )


def _filter_trading_days_by_range(
    days: list[str],
    *,
    start: str | None,
    end: str | None,
    final_test_cutoff: str,
) -> list[str]:
    """G1 startup-side filter: trim to [start, end] AND strictly < cutoff.

    Always strips dates >= final_test_cutoff regardless of explicit range.
    """
    out = list(days)
    if start is not None:
        out = [d for d in out if d >= start]
    if end is not None:
        out = [d for d in out if d <= end]
    out = [d for d in out if d < final_test_cutoff]
    return out


def _filter_pairs_by_cutoff(
    pairs: list[tuple[str, str]],
    *,
    final_test_cutoff: str,
) -> tuple[list[tuple[str, str]], list[str]]:
    """G2 boundary skip: drop any pair whose prediction_for_date >= cutoff."""
    kept: list[tuple[str, str]] = []
    skipped: list[str] = []
    for as_of, pred in pairs:
        if pred >= final_test_cutoff or as_of >= final_test_cutoff:
            skipped.append(
                f"T+1 boundary skip: as_of={as_of}, prediction_for_date={pred} "
                f">= final_test_cutoff={final_test_cutoff}"
            )
            continue
        kept.append((as_of, pred))
    return kept, skipped


def _build_manifest(
    *,
    replay_window_start: str | None,
    replay_window_end: str | None,
    final_test_cutoff: str,
    records_generated: int | None = None,
    paired_outcomes: int | None = None,
    status: str = "ok",
    warnings: list[str] | None = None,
    final_test_touched: bool = False,
) -> dict[str, Any]:
    """Build a `w4_replay_manifest.v1` dict."""
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "replay_window": {
            "start": replay_window_start,
            "end": replay_window_end,
        },
        "final_test_cutoff": final_test_cutoff,
        "final_test_touched": bool(final_test_touched),
        "records_generated": records_generated,
        "paired_outcomes": paired_outcomes,
        "status": status,
        "warnings": list(warnings or []),
    }


def _write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    """Write a manifest dict to JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2, default=str)


def _resolve_date_pairs(
    *,
    trading_days: list[str],
    start_date: str | None,
    end_date: str | None,
    num_cases: int,
    final_test_cutoff: str,
) -> tuple[list[tuple[str, str]], list[str]]:
    """Combine G1 (range + cutoff) with the legacy num_cases tail.

    Returns (pairs, g2_warnings). G2 (T+1 boundary skip) is always applied
    even after G1, as defense-in-depth.
    """
    if start_date is not None or end_date is not None:
        filtered = _filter_trading_days_by_range(
            trading_days,
            start=start_date,
            end=end_date,
            final_test_cutoff=final_test_cutoff,
        )
        pairs = [
            (filtered[i], filtered[i + 1]) for i in range(len(filtered) - 1)
        ]
    else:
        cutoff_filtered = [d for d in trading_days if d < final_test_cutoff]
        pairs = _build_date_pairs(cutoff_filtered, num_cases=num_cases)

    pairs, warnings = _filter_pairs_by_cutoff(
        pairs, final_test_cutoff=final_test_cutoff
    )
    return pairs, warnings


def _audit_case_for_pair(
    *,
    symbol: str,
    as_of_date: str,
    prediction_for_date: str,
    lookback_days: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run one replay pair and reshape into (replay_result, audit_case).

    The audit_case feeds the existing summary / CSV outputs. The
    replay_result is forwarded to the optional Task 076 DB persistence
    path so degraded cases can be skipped by the wiring helper rather
    than faked here.
    """
    try:
        replay_result = run_historical_replay_for_date(
            symbol=symbol,
            as_of_date=as_of_date,
            prediction_for_date=prediction_for_date,
            lookback_days=lookback_days,
        )
    except Exception as exc:
        replay_result = {
            "kind": "historical_replay_result",
            "symbol": symbol,
            "as_of_date": as_of_date,
            "prediction_for_date": prediction_for_date,
            "ready": False,
            "projection_snapshot": {},
            "actual_outcome": {},
            "review": {},
            "warnings": [f"replay 意外失败：{exc}"],
        }
    snapshot = replay_result.get("projection_snapshot") or {}
    three_systems = build_projection_three_systems(snapshot, symbol=symbol)
    audit_case = build_audit_case(replay_result=replay_result, three_systems=three_systems)
    return replay_result, audit_case


def _persist_replay_records_to_db(
    *,
    replay_results: list[dict[str, Any]],
    db_path: Path,
) -> dict[str, Any]:
    """Best-effort DB save. Captures errors as a structured summary.

    Always returns a dict with a ``status`` field. On a raised exception
    (anywhere from connect → save → commit → close) this returns a
    ``status="failed"`` summary with the error message — the file
    output phase should not crash because of a DB error.
    """
    db_path = Path(db_path)
    summary: dict[str, Any] = {
        "status": "ok",
        "db_path": str(db_path),
        "total_cases": len(replay_results),
        "saved_cases": 0,
        "skipped_cases": 0,
        "failed_cases": 0,
        "run_ids": [],
    }

    batch_payload = {
        "kind": "historical_replay_batch",
        "results": replay_results,
    }

    conn: sqlite3.Connection | None = None
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path))
        save_summary = save_replay_batch_projection_records(conn, batch_payload)
        conn.commit()
        summary.update({
            "total_cases": save_summary.get("total_cases", len(replay_results)),
            "saved_cases": save_summary.get("saved_cases", 0),
            "skipped_cases": save_summary.get("skipped_cases", 0),
            "failed_cases": save_summary.get("failed_cases", 0),
            "run_ids": list(save_summary.get("run_ids") or []),
        })
    except Exception as exc:
        summary["status"] = "failed"
        summary["error"] = str(exc)
        summary["saved_cases"] = 0
        summary["skipped_cases"] = 0
        summary["failed_cases"] = 0
        summary["run_ids"] = []
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass

    return summary


def run_audit(
    *,
    symbol: str,
    num_cases: int,
    lookback_days: int,
    output_dir: Path,
    trading_days: list[str] | None = None,
    save_records: bool = False,
    db_path: Path | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    final_test_cutoff: str = DEFAULT_FINAL_TEST_CUTOFF,
    write_manifest: bool = False,
    manifest_path: Path | None = None,
) -> dict[str, Any]:
    if trading_days is None:
        _log(f"loading AVGO trading days (target={num_cases + 1})")
        trading_days = _load_avgo_trading_days(symbol=symbol, minimum_days=num_cases + 1)
        _log(f"loaded {len(trading_days)} trading day(s)")

    date_pairs, boundary_warnings = _resolve_date_pairs(
        trading_days=trading_days,
        start_date=start_date,
        end_date=end_date,
        num_cases=num_cases,
        final_test_cutoff=final_test_cutoff,
    )

    manifest_payload = {
        "replay_window_start": start_date,
        "replay_window_end": end_date,
        "final_test_cutoff": final_test_cutoff,
    }

    if not date_pairs:
        _log("no usable date pairs — aborting")
        if write_manifest:
            target = manifest_path or (output_dir / DEFAULT_MANIFEST_FILENAME)
            _write_manifest(
                target,
                _build_manifest(
                    **manifest_payload,
                    records_generated=0,
                    paired_outcomes=0,
                    status="error",
                    warnings=[
                        "no trading days available to build replay pairs",
                        *boundary_warnings,
                    ],
                ),
            )
        return {
            "ready": False,
            "warnings": [
                "no trading days available to build replay pairs",
                *boundary_warnings,
            ],
            "num_cases_built": 0,
        }
    _log(f"built {len(date_pairs)} replay pair(s) ({date_pairs[0][0]} → {date_pairs[-1][1]})")
    if boundary_warnings:
        _log(f"T+1 boundary skips: {len(boundary_warnings)}")

    replay_results: list[dict[str, Any]] = []
    cases: list[dict[str, Any]] = []
    progress_step = max(1, len(date_pairs) // 20)
    for idx, (as_of, pred) in enumerate(date_pairs, start=1):
        replay_result, case = _audit_case_for_pair(
            symbol=symbol,
            as_of_date=as_of,
            prediction_for_date=pred,
            lookback_days=lookback_days,
        )
        replay_results.append(replay_result)
        cases.append(case)
        if idx % progress_step == 0 or idx == len(date_pairs):
            _log(f"replay progress: {idx}/{len(date_pairs)}")

    summary = summarize_three_system_audit(cases)

    # ── file outputs ────────────────────────────────────────────────────
    # All file writes happen BEFORE optional DB save so a DB failure
    # cannot destroy the file output. The summary JSON is written LAST
    # so it can include the record_store_summary key.
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_jsonl(output_dir / "three_system_replay_results.jsonl", cases)
    _write_text(output_dir / "three_system_replay_summary.md", render_summary_markdown(summary))

    _write_csv(
        output_dir / "negative_system_stats.csv",
        [negative_system_row(c) for c in cases],
        header=[
            "as_of_date", "prediction_for_date", "ready", "excluded", "triggered_rule",
            "excluded_states", "strength", "negative_confidence_level",
            "evidence_count", "actual_state", "false_exclusion", "direction_correct",
        ],
    )
    _write_csv(
        output_dir / "record_02_projection_stats.csv",
        [record_02_projection_row(c) for c in cases],
        header=[
            "as_of_date", "prediction_for_date", "ready", "final_direction",
            "five_state_top1", "actual_state", "five_state_top1_correct",
            "actual_open_label", "actual_close_label", "actual_path_label",
            "historical_sample_quality", "peer_confirmation_level",
            "projection_risk_note_count", "direction_correct",
        ],
    )
    _write_csv(
        output_dir / "confidence_evaluator_stats.csv",
        [confidence_evaluator_row(c) for c in cases],
        header=[
            "as_of_date", "prediction_for_date", "ready",
            "negative_confidence_level", "projection_confidence_level",
            "overall_confidence_level", "conflict_count",
            "reliability_warning_count", "direction_correct",
            "actual_state", "high_confidence_wrong",
        ],
    )
    _write_csv(
        output_dir / "error_cases.csv",
        filter_error_cases(cases),
        header=[
            "as_of_date", "prediction_for_date", "final_direction",
            "five_state_top1", "actual_state", "overall_confidence_level",
            "error_layer", "error_category", "negative_excluded",
            "negative_triggered_rule", "false_exclusion",
        ],
    )
    _write_csv(
        output_dir / "false_exclusion_cases.csv",
        filter_false_exclusion_cases(cases),
        header=[
            "as_of_date", "prediction_for_date", "triggered_rule",
            "excluded_states", "actual_state", "negative_strength",
            "negative_confidence", "evidence", "invalidating_conditions",
            "final_direction", "overall_confidence",
        ],
    )
    _write_csv(
        output_dir / "high_confidence_wrong_cases.csv",
        filter_high_confidence_wrong_cases(cases),
        header=[
            "as_of_date", "prediction_for_date", "final_direction",
            "five_state_top1", "overall_confidence", "negative_confidence",
            "projection_confidence", "actual_state", "direction_correct",
            "error_category", "conflicts", "reliability_warnings",
        ],
    )

    # ── optional DB persistence ─────────────────────────────────────────
    record_store_summary: dict[str, Any] | None = None
    if save_records:
        resolved_db_path = db_path if db_path is not None else DEFAULT_DB_PATH
        record_store_summary = _persist_replay_records_to_db(
            replay_results=replay_results,
            db_path=resolved_db_path,
        )
        if record_store_summary.get("status") == "ok":
            _log(
                f"record store: status=ok, "
                f"saved={record_store_summary.get('saved_cases')}/{record_store_summary.get('total_cases')}, "
                f"skipped={record_store_summary.get('skipped_cases')}, "
                f"failed={record_store_summary.get('failed_cases')}, "
                f"db={record_store_summary.get('db_path')}"
            )
        else:
            _log(
                f"record store: WARNING DB save failed "
                f"({record_store_summary.get('error')}); file outputs still written"
            )
        summary["record_store_summary"] = record_store_summary

    # ── summary JSON written LAST so it includes record_store_summary ──
    _write_json(output_dir / "three_system_replay_summary.json", summary)

    # ── Step 2G-8D.1A — manifest emission (W4 only) ─────────────────────
    paired_outcomes = sum(
        1
        for r in replay_results
        if r.get("ready") and (r.get("actual_outcome") or {}).get("actual_close") is not None
    )
    final_test_touched = any(
        (r.get("as_of_date") or "") >= final_test_cutoff
        or (r.get("prediction_for_date") or "") >= final_test_cutoff
        for r in replay_results
    )
    if write_manifest:
        target = manifest_path or (output_dir / DEFAULT_MANIFEST_FILENAME)
        _write_manifest(
            target,
            _build_manifest(
                **manifest_payload,
                records_generated=len(date_pairs),
                paired_outcomes=paired_outcomes,
                status="error" if final_test_touched else "ok",
                warnings=list(boundary_warnings),
                final_test_touched=final_test_touched,
            ),
        )
        _log(f"manifest written to {target}")

    overall = summary.get("overall", {})
    _log(
        f"audit complete: total={overall.get('total_cases')}, "
        f"completed={overall.get('completed_cases')}, "
        f"failed={overall.get('failed_cases')}, "
        f"direction_accuracy={overall.get('direction_accuracy')}"
    )
    _log(f"outputs written to {output_dir}")

    return {
        "ready": True,
        "num_cases_built": len(date_pairs),
        "num_cases_run": len(cases),
        "output_dir": str(output_dir),
        "summary": summary,
        "boundary_warnings": list(boundary_warnings),
        "final_test_touched": final_test_touched,
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Task 072 three-system replay audit (offline)")
    parser.add_argument("--symbol", default=DEFAULT_SYMBOL)
    parser.add_argument("--num-cases", type=int, default=DEFAULT_NUM_CASES)
    parser.add_argument("--lookback-days", type=int, default=DEFAULT_LOOKBACK_DAYS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--save-records",
        action="store_true",
        help="If set, persist replay cases into services.projection_record_store",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DEFAULT_DB_PATH,
        help="SQLite DB path used only when --save-records is set",
    )
    # Step 2G-8D.1A — W4 cross-window validation guards
    parser.add_argument(
        "--start-date",
        default=None,
        help="Explicit replay window start (ISO YYYY-MM-DD). When set, overrides --num-cases tail behaviour.",
    )
    parser.add_argument(
        "--end-date",
        default=None,
        help="Explicit replay window end (ISO YYYY-MM-DD). Must be < --final-test-cutoff.",
    )
    parser.add_argument(
        "--final-test-cutoff",
        default=DEFAULT_FINAL_TEST_CUTOFF,
        help=f"Final-test cutoff date (ISO; default {DEFAULT_FINAL_TEST_CUTOFF}); replay never reads dates >= this.",
    )
    parser.add_argument(
        "--tiny-smoke",
        action="store_true",
        help="Run a tiny W4 smoke window (default 2024-08-05 → 2024-08-09); forces --save-records=False and --write-manifest=True.",
    )
    parser.add_argument(
        "--write-manifest",
        action="store_true",
        help="Emit w4_replay_manifest.v1 JSON to output_dir/validation_ready_manifest.json (or --manifest-path).",
    )
    parser.add_argument(
        "--manifest-path",
        type=Path,
        default=None,
        help="Optional explicit manifest output path; default is output_dir/validation_ready_manifest.json.",
    )
    parser.add_argument(
        "--allow-overwrite",
        action="store_true",
        help="Allow writing into a non-empty output_dir (W4 mode only); off by default.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    args = _apply_tiny_smoke_defaults(args)
    try:
        _validate_w4_args(args)
    except ValueError as exc:
        print(f"[task072] config rejected: {exc}", file=sys.stderr, flush=True)
        return 2
    result = run_audit(
        symbol=args.symbol,
        num_cases=args.num_cases,
        lookback_days=args.lookback_days,
        output_dir=args.output_dir,
        save_records=args.save_records,
        db_path=args.db_path,
        start_date=args.start_date,
        end_date=args.end_date,
        final_test_cutoff=args.final_test_cutoff,
        write_manifest=args.write_manifest,
        manifest_path=args.manifest_path,
    )
    return 0 if result.get("ready") else 1


if __name__ == "__main__":
    raise SystemExit(main())
