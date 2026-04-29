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
) -> dict[str, Any]:
    if trading_days is None:
        _log(f"loading AVGO trading days (target={num_cases + 1})")
        trading_days = _load_avgo_trading_days(symbol=symbol, minimum_days=num_cases + 1)
        _log(f"loaded {len(trading_days)} trading day(s)")

    date_pairs = _build_date_pairs(trading_days, num_cases=num_cases)
    if not date_pairs:
        _log("no usable date pairs — aborting")
        return {
            "ready": False,
            "warnings": ["no trading days available to build replay pairs"],
            "num_cases_built": 0,
        }
    _log(f"built {len(date_pairs)} replay pair(s) ({date_pairs[0][0]} → {date_pairs[-1][1]})")

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
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = run_audit(
        symbol=args.symbol,
        num_cases=args.num_cases,
        lookback_days=args.lookback_days,
        output_dir=args.output_dir,
        save_records=args.save_records,
        db_path=args.db_path,
    )
    return 0 if result.get("ready") else 1


if __name__ == "__main__":
    raise SystemExit(main())
