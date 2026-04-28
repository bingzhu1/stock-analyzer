"""Task 084 — audit record_02 five-state collapse from SQLite records.

Reads `projection_runs` + `record_02_projection` from a SQLite DB and audits
whether recent cases collapse toward `five_state_top1=震荡` and
`final_direction=偏多`, or whether the pattern is better explained by
low-margin top-1 probabilities, malformed probability payloads, or a
direction/state mismatch.

This is audit-only. The script does not modify the DB and does not touch any
projection / final-decision / negative-system logic.
"""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


CANONICAL_STATES = ("大涨", "小涨", "震荡", "小跌", "大跌")
STATE_ORDER = {state: idx for idx, state in enumerate(CANONICAL_STATES)}

MIN_CASES = 5
COLLAPSE_THRESHOLD = 0.70
MALFORMED_THRESHOLD = 0.20
LOW_MARGIN_THRESHOLD = 0.50
DIRECTION_MISMATCH_THRESHOLD = 0.70

DEFAULT_SYMBOL = "AVGO"
DEFAULT_DB_PATH = ROOT / "data" / "market_data.db"
DEFAULT_OUTPUT_DIR = ROOT / "logs" / "five_state_collapse_audit"

JUDGMENT_INSUFFICIENT_DATA = "insufficient_data"
JUDGMENT_MALFORMED_PROBABILITY_DATA = "malformed_probability_data"
JUDGMENT_FIVE_STATE_TOP1_COLLAPSED = "five_state_top1_collapsed"
JUDGMENT_FINAL_DIRECTION_COLLAPSED = "final_direction_collapsed"
JUDGMENT_LOW_MARGIN_TOP1_PROBLEM = "low_margin_top1_problem"
JUDGMENT_DIRECTION_STATE_MISMATCH = "direction_state_mismatch"
JUDGMENT_NO_COLLAPSE = "no_collapse"

_TOP1_DIST_COLUMNS = ("five_state_top1", "count", "share")
_FINAL_DIRECTION_COLUMNS = ("final_direction", "count", "share")
_MARGIN_CASE_COLUMNS = (
    "run_id",
    "as_of_date",
    "prediction_for_date",
    "five_state_top1",
    "final_direction",
    "derived_top1",
    "second_state",
    "top1_prob",
    "second_prob",
    "top1_margin",
    "margin_lt_0_03",
    "margin_lt_0_05",
    "margin_lt_0_10",
)
_PROBABILITY_SUMMARY_COLUMNS = ("state", "average_probability", "valid_case_count")
_MISMATCH_CASE_COLUMNS = (
    "run_id",
    "as_of_date",
    "prediction_for_date",
    "five_state_top1",
    "final_direction",
    "derived_top1",
    "second_state",
    "top1_margin",
    "malformed_probability",
    "malformed_reason",
)


def _log(message: str) -> None:
    print(f"[task084] {message}", flush=True)


def _normalize_symbol(symbol: Any) -> str:
    text = str(symbol or "").strip().upper()
    return text or DEFAULT_SYMBOL


def _safe_json_loads(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    text = str(value).strip()
    if not text or text.lower() in {"null", "none"}:
        return None
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return None


def _parse_probability_number(value: Any) -> tuple[float | None, bool]:
    """Return `(number, had_percent_suffix)` for one raw probability cell."""
    if isinstance(value, bool):
        return None, False
    if isinstance(value, (int, float)):
        return float(value), False
    text = str(value or "").strip()
    if not text:
        return None, False
    had_percent = text.endswith("%")
    if had_percent:
        text = text[:-1].strip()
    try:
        return float(text), had_percent
    except ValueError:
        return None, had_percent


def parse_five_state_distribution(
    raw: Any,
) -> tuple[dict[str, float] | None, str | None]:
    """Parse one `five_state_distribution_json` cell into canonical floats."""
    payload = _safe_json_loads(raw)
    if not isinstance(payload, dict):
        return None, "distribution is not a JSON object"

    missing_states = [state for state in CANONICAL_STATES if state not in payload]
    if missing_states:
        return None, f"missing states: {', '.join(missing_states)}"

    parsed: dict[str, float] = {}
    saw_percent = False
    for state in CANONICAL_STATES:
        number, had_percent = _parse_probability_number(payload.get(state))
        saw_percent = saw_percent or had_percent
        if number is None:
            return None, f"non-numeric probability for {state}"
        if number < 0:
            return None, f"negative probability for {state}"
        parsed[state] = number

    max_value = max(parsed.values()) if parsed else 0.0
    if saw_percent or max_value > 1.0:
        if max_value > 100.0:
            return None, "probability exceeds 100"
        parsed = {state: value / 100.0 for state, value in parsed.items()}

    if not parsed:
        return None, "empty probability distribution"

    if max(parsed.values()) > 1.0 + 1e-9:
        return None, "probability exceeds 1 after normalization"

    if sum(parsed.values()) <= 0:
        return None, "probability sum is not positive"

    return parsed, None


def _sorted_distribution(probabilities: dict[str, float]) -> list[tuple[str, float]]:
    return sorted(
        probabilities.items(),
        key=lambda item: (-item[1], STATE_ORDER[item[0]]),
    )


def build_margin_case(run: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    probabilities, reason = parse_five_state_distribution(
        run.get("five_state_distribution_json")
    )
    if probabilities is None:
        return None, reason

    ranked = _sorted_distribution(probabilities)
    if len(ranked) < 2:
        return None, "fewer than two ranked states"

    derived_top1, top1_prob = ranked[0]
    second_state, second_prob = ranked[1]
    margin = top1_prob - second_prob
    return {
        "run_id": run.get("run_id"),
        "as_of_date": run.get("as_of_date"),
        "prediction_for_date": run.get("prediction_for_date"),
        "five_state_top1": run.get("five_state_top1"),
        "final_direction": run.get("final_direction"),
        "derived_top1": derived_top1,
        "second_state": second_state,
        "top1_prob": top1_prob,
        "second_prob": second_prob,
        "top1_margin": margin,
        "margin_lt_0_03": margin < 0.03,
        "margin_lt_0_05": margin < 0.05,
        "margin_lt_0_10": margin < 0.10,
        "probabilities": probabilities,
    }, None


def fetch_runs(
    conn: sqlite3.Connection,
    *,
    symbol: str,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    sym = _normalize_symbol(symbol)
    sql = (
        "SELECT "
        "  r.run_id, r.symbol, r.as_of_date, r.prediction_for_date, r.created_at, "
        "  r2.five_state_top1, r2.final_direction, r2.five_state_distribution_json "
        "FROM projection_runs r "
        "LEFT JOIN record_02_projection r2 ON r2.run_id = r.run_id "
        "WHERE r.symbol = ? "
        "ORDER BY r.created_at DESC, r.run_id DESC"
    )
    params: list[Any] = [sym]
    if limit is not None and limit > 0:
        sql += " LIMIT ?"
        params.append(int(limit))
    cur = conn.execute(sql, params)
    columns = [desc[0] for desc in cur.description]
    return [dict(zip(columns, row, strict=True)) for row in cur.fetchall()]


def _distribution_rows(
    counter: Counter[str],
    *,
    total_cases: int,
    column_name: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for value, count in counter.most_common():
        rows.append({
            column_name: value,
            "count": count,
            "share": (count / total_cases) if total_cases else 0.0,
        })
    return rows


def decide_judgment(
    *,
    total_cases: int,
    malformed_share: float,
    top1_dominant_share: float,
    final_direction_dominant_share: float,
    low_margin_lt_0_05_share: float,
    mismatch_share: float,
) -> tuple[str, dict[str, bool], str]:
    flags = {
        "insufficient_data": total_cases < MIN_CASES,
        "malformed_probability_data": malformed_share > MALFORMED_THRESHOLD,
        "five_state_top1_collapse": top1_dominant_share >= COLLAPSE_THRESHOLD,
        "final_direction_collapse": final_direction_dominant_share >= COLLAPSE_THRESHOLD,
        "low_margin_problem": low_margin_lt_0_05_share > LOW_MARGIN_THRESHOLD,
        "direction_state_mismatch": mismatch_share > DIRECTION_MISMATCH_THRESHOLD,
    }

    if flags["insufficient_data"]:
        return (
            JUDGMENT_INSUFFICIENT_DATA,
            flags,
            f"total_cases={total_cases} < {MIN_CASES}",
        )
    if flags["malformed_probability_data"]:
        return (
            JUDGMENT_MALFORMED_PROBABILITY_DATA,
            flags,
            f"malformed_probability_share={malformed_share:.2%} > {MALFORMED_THRESHOLD:.0%}",
        )
    if flags["five_state_top1_collapse"]:
        return (
            JUDGMENT_FIVE_STATE_TOP1_COLLAPSED,
            flags,
            f"five_state_top1 dominant share={top1_dominant_share:.2%}",
        )
    if flags["final_direction_collapse"]:
        return (
            JUDGMENT_FINAL_DIRECTION_COLLAPSED,
            flags,
            f"final_direction dominant share={final_direction_dominant_share:.2%}",
        )
    if flags["low_margin_problem"]:
        return (
            JUDGMENT_LOW_MARGIN_TOP1_PROBLEM,
            flags,
            f"margin<0.05 share={low_margin_lt_0_05_share:.2%} > {LOW_MARGIN_THRESHOLD:.0%}",
        )
    if flags["direction_state_mismatch"]:
        return (
            JUDGMENT_DIRECTION_STATE_MISMATCH,
            flags,
            f"震荡|偏多 share={mismatch_share:.2%} > {DIRECTION_MISMATCH_THRESHOLD:.0%}",
        )
    return JUDGMENT_NO_COLLAPSE, flags, "no collapse thresholds triggered"


def audit_runs(
    *,
    runs: list[dict[str, Any]],
    symbol: str,
) -> dict[str, Any]:
    total_cases = len(runs)
    top1_counter: Counter[str] = Counter()
    direction_counter: Counter[str] = Counter()
    joint_counter: Counter[str] = Counter()
    malformed_rows: list[dict[str, Any]] = []
    margin_cases: list[dict[str, Any]] = []
    mismatch_cases: list[dict[str, Any]] = []
    probability_totals = {state: 0.0 for state in CANONICAL_STATES}
    zhen_dang_over_xiao_zhang_count = 0
    zhen_dang_over_xiao_zhang_low_margin_count = 0

    for run in runs:
        top1 = str(run.get("five_state_top1") or "").strip() or "<missing>"
        direction = str(run.get("final_direction") or "").strip() or "<missing>"
        top1_counter[top1] += 1
        direction_counter[direction] += 1
        joint_counter[f"{top1}|{direction}"] += 1

        margin_case, malformed_reason = build_margin_case(run)
        if margin_case is None:
            malformed_rows.append({
                "run_id": run.get("run_id"),
                "as_of_date": run.get("as_of_date"),
                "prediction_for_date": run.get("prediction_for_date"),
                "five_state_top1": run.get("five_state_top1"),
                "final_direction": run.get("final_direction"),
                "reason": malformed_reason or "unknown parse error",
            })
        else:
            margin_cases.append(margin_case)
            probabilities = margin_case["probabilities"]
            for state in CANONICAL_STATES:
                probability_totals[state] += probabilities[state]
            if (
                margin_case["derived_top1"] == "震荡"
                and margin_case["second_state"] == "小涨"
            ):
                zhen_dang_over_xiao_zhang_count += 1
                if margin_case["top1_margin"] < 0.05:
                    zhen_dang_over_xiao_zhang_low_margin_count += 1

        if top1 == "震荡" and direction == "偏多":
            mismatch_cases.append({
                "run_id": run.get("run_id"),
                "as_of_date": run.get("as_of_date"),
                "prediction_for_date": run.get("prediction_for_date"),
                "five_state_top1": run.get("five_state_top1"),
                "final_direction": run.get("final_direction"),
                "derived_top1": margin_case["derived_top1"] if margin_case else None,
                "second_state": margin_case["second_state"] if margin_case else None,
                "top1_margin": margin_case["top1_margin"] if margin_case else None,
                "malformed_probability": margin_case is None,
                "malformed_reason": malformed_reason,
            })

    valid_probability_rows = len(margin_cases)
    malformed_probability_rows = len(malformed_rows)
    malformed_share = (
        malformed_probability_rows / total_cases if total_cases else 0.0
    )

    low_margin_lt_0_03 = sum(1 for case in margin_cases if case["top1_margin"] < 0.03)
    low_margin_lt_0_05 = sum(1 for case in margin_cases if case["top1_margin"] < 0.05)
    low_margin_lt_0_10 = sum(1 for case in margin_cases if case["top1_margin"] < 0.10)

    top1_dist_rows = _distribution_rows(
        top1_counter,
        total_cases=total_cases,
        column_name="five_state_top1",
    )
    direction_dist_rows = _distribution_rows(
        direction_counter,
        total_cases=total_cases,
        column_name="final_direction",
    )

    top1_dominant = top1_counter.most_common(1)
    top1_dominant_value = top1_dominant[0][0] if top1_dominant else None
    top1_dominant_share = (
        top1_dominant[0][1] / total_cases if total_cases and top1_dominant else 0.0
    )
    direction_dominant = direction_counter.most_common(1)
    direction_dominant_value = direction_dominant[0][0] if direction_dominant else None
    direction_dominant_share = (
        direction_dominant[0][1] / total_cases
        if total_cases and direction_dominant
        else 0.0
    )
    mismatch_key = "震荡|偏多"
    mismatch_count = joint_counter.get(mismatch_key, 0)
    mismatch_share = mismatch_count / total_cases if total_cases else 0.0

    low_margin_lt_0_03_share = (
        low_margin_lt_0_03 / valid_probability_rows if valid_probability_rows else 0.0
    )
    low_margin_lt_0_05_share = (
        low_margin_lt_0_05 / valid_probability_rows if valid_probability_rows else 0.0
    )
    low_margin_lt_0_10_share = (
        low_margin_lt_0_10 / valid_probability_rows if valid_probability_rows else 0.0
    )

    probability_summary = []
    for state in CANONICAL_STATES:
        average_probability = (
            probability_totals[state] / valid_probability_rows
            if valid_probability_rows
            else None
        )
        probability_summary.append({
            "state": state,
            "average_probability": average_probability,
            "valid_case_count": valid_probability_rows,
        })

    judgment, flags, judgment_reason = decide_judgment(
        total_cases=total_cases,
        malformed_share=malformed_share,
        top1_dominant_share=top1_dominant_share,
        final_direction_dominant_share=direction_dominant_share,
        low_margin_lt_0_05_share=low_margin_lt_0_05_share,
        mismatch_share=mismatch_share,
    )

    return {
        "symbol": _normalize_symbol(symbol),
        "total_cases": total_cases,
        "judgment": judgment,
        "judgment_reason": judgment_reason,
        "flags": flags,
        "five_state_top1_distribution": dict(top1_counter),
        "final_direction_distribution": dict(direction_counter),
        "joint_distribution": dict(joint_counter),
        "five_state_top1_distribution_rows": top1_dist_rows,
        "final_direction_distribution_rows": direction_dist_rows,
        "top1_dominant_state": top1_dominant_value,
        "top1_dominant_share": top1_dominant_share,
        "final_direction_dominant": direction_dominant_value,
        "final_direction_dominant_share": direction_dominant_share,
        "valid_probability_rows": valid_probability_rows,
        "malformed_probability_rows": malformed_probability_rows,
        "malformed_probability_share": malformed_share,
        "malformed_probability_cases": malformed_rows,
        "margin_buckets": {
            "lt_0_03": {
                "count": low_margin_lt_0_03,
                "share": low_margin_lt_0_03_share,
            },
            "lt_0_05": {
                "count": low_margin_lt_0_05,
                "share": low_margin_lt_0_05_share,
            },
            "lt_0_10": {
                "count": low_margin_lt_0_10,
                "share": low_margin_lt_0_10_share,
            },
        },
        "five_state_margin_cases": [
            {key: value for key, value in case.items() if key != "probabilities"}
            for case in margin_cases
        ],
        "five_state_probability_summary": probability_summary,
        "zhen_dang_over_xiao_zhang": {
            "count": zhen_dang_over_xiao_zhang_count,
            "low_margin_lt_0_05_count": zhen_dang_over_xiao_zhang_low_margin_count,
        },
        "direction_state_mismatch": {
            "joint_key": mismatch_key,
            "count": mismatch_count,
            "share": mismatch_share,
        },
        "direction_state_mismatch_cases": mismatch_cases,
    }


def render_audit_markdown(audit_result: dict[str, Any]) -> str:
    def _fmt_pct(value: Any) -> str:
        if value is None:
            return "n/a"
        return f"{float(value):.2%}"

    lines = [
        "# Five-State Collapse Audit",
        "",
        f"- symbol: {audit_result.get('symbol')}",
        f"- total_cases: {audit_result.get('total_cases')}",
        f"- judgment: {audit_result.get('judgment')}",
        f"- judgment_reason: {audit_result.get('judgment_reason')}",
        "",
        "## Flags",
    ]
    flags = audit_result.get("flags") or {}
    for key in (
        "insufficient_data",
        "malformed_probability_data",
        "five_state_top1_collapse",
        "final_direction_collapse",
        "low_margin_problem",
        "direction_state_mismatch",
    ):
        lines.append(f"- {key}: {bool(flags.get(key))}")

    lines.extend([
        "",
        "## Distributions",
        f"- five_state_top1: {audit_result.get('five_state_top1_distribution')}",
        f"- final_direction: {audit_result.get('final_direction_distribution')}",
        f"- joint: {audit_result.get('joint_distribution')}",
        "",
        "## Probability Quality",
        f"- valid_probability_rows: {audit_result.get('valid_probability_rows')}",
        f"- malformed_probability_rows: {audit_result.get('malformed_probability_rows')}",
        f"- malformed_probability_share: {_fmt_pct(audit_result.get('malformed_probability_share'))}",
        "",
        "## Margin Buckets",
        f"- margin < 0.03: {audit_result.get('margin_buckets', {}).get('lt_0_03', {}).get('count')} "
        f"({_fmt_pct(audit_result.get('margin_buckets', {}).get('lt_0_03', {}).get('share'))})",
        f"- margin < 0.05: {audit_result.get('margin_buckets', {}).get('lt_0_05', {}).get('count')} "
        f"({_fmt_pct(audit_result.get('margin_buckets', {}).get('lt_0_05', {}).get('share'))})",
        f"- margin < 0.10: {audit_result.get('margin_buckets', {}).get('lt_0_10', {}).get('count')} "
        f"({_fmt_pct(audit_result.get('margin_buckets', {}).get('lt_0_10', {}).get('share'))})",
        "",
        "## Mismatch",
        f"- 震荡|偏多 count: {audit_result.get('direction_state_mismatch', {}).get('count')}",
        f"- 震荡|偏多 share: {_fmt_pct(audit_result.get('direction_state_mismatch', {}).get('share'))}",
        "",
        "## Probability Averages",
    ])

    for row in audit_result.get("five_state_probability_summary") or []:
        lines.append(
            f"- {row.get('state')}: {_fmt_pct(row.get('average_probability'))}"
        )
    return "\n".join(lines) + "\n"


def _write_csv(path: Path, fieldnames: tuple[str, ...], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            cleaned = dict(row)
            for key, value in cleaned.items():
                if isinstance(value, bool):
                    cleaned[key] = "true" if value else "false"
            writer.writerow(cleaned)


def write_audit_outputs(audit_result: dict[str, Any], output_dir: str | Path) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    (output_path / "five_state_collapse_audit.json").write_text(
        json.dumps(audit_result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_path / "five_state_collapse_audit.md").write_text(
        render_audit_markdown(audit_result),
        encoding="utf-8",
    )
    _write_csv(
        output_path / "five_state_top1_distribution.csv",
        _TOP1_DIST_COLUMNS,
        audit_result.get("five_state_top1_distribution_rows") or [],
    )
    _write_csv(
        output_path / "final_direction_distribution.csv",
        _FINAL_DIRECTION_COLUMNS,
        audit_result.get("final_direction_distribution_rows") or [],
    )
    _write_csv(
        output_path / "five_state_margin_cases.csv",
        _MARGIN_CASE_COLUMNS,
        audit_result.get("five_state_margin_cases") or [],
    )
    _write_csv(
        output_path / "five_state_probability_summary.csv",
        _PROBABILITY_SUMMARY_COLUMNS,
        audit_result.get("five_state_probability_summary") or [],
    )
    _write_csv(
        output_path / "direction_state_mismatch_cases.csv",
        _MISMATCH_CASE_COLUMNS,
        audit_result.get("direction_state_mismatch_cases") or [],
    )


def _run_cli(
    *,
    symbol: str,
    db_path: Path,
    limit: int | None,
    output_dir: Path,
) -> dict[str, Any]:
    if not db_path.exists():
        _log(f"DB not found at {db_path}; emitting insufficient-data audit")
        audit_result = audit_runs(runs=[], symbol=symbol)
        write_audit_outputs(audit_result, output_dir)
        return audit_result

    with sqlite3.connect(db_path) as conn:
        runs = fetch_runs(conn, symbol=symbol, limit=limit)
    audit_result = audit_runs(runs=runs, symbol=symbol)
    write_audit_outputs(audit_result, output_dir)
    return audit_result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", default=DEFAULT_SYMBOL)
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args(argv)

    audit_result = _run_cli(
        symbol=args.symbol,
        db_path=Path(args.db_path),
        limit=args.limit,
        output_dir=Path(args.output_dir),
    )
    _log(
        "judgment="
        f"{audit_result.get('judgment')} total_cases={audit_result.get('total_cases')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
