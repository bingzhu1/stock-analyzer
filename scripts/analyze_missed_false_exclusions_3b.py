#!/usr/bin/env python3
"""Task 3B — analyze the 54 missed false exclusions from Task 2E-v2.

Read-only analysis.

Input priority:
1. User-spec path under logs/technical_features/false_bigup_bigdown_support_validation/
2. Existing Task 2E-v2 output under logs/historical_training/exclusion_action_validation_2e_v2/

This script does not change prediction rules, UI, warnings, or thresholds.
It only explains why the remaining 54 false exclusions were still treated as
supported by the new raw/enriched validators and technical-feature checks.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import decompose_unsupported_false_exclusions_3a as task3a
from scripts import validate_false_exclusions_2e_v2 as task2e_v2
from services.big_down_tail_warning import (
    TAIL_COMPRESSION_THRESHOLD,
    build_big_down_tail_warning,
)
from services.big_up_contradiction_card import build_contradiction_card


DEFAULT_OUTPUT_DIR = (
    ROOT / "logs/technical_features/false_bigup_bigdown_missed_residual_3b"
)
EXPECTED_MISSED_TOTAL = 54

BIG_DOWN_REASON_LABELS = {
    "系统同时排除了大涨和大跌两端状态": "dual_extremes",
    "预测结果偏向震荡": "predicted_neutral",
    "大跌概率被压低到 0.05 以下": "p_big_down_compressed",
    "大涨概率被压低到 0.05 以下": "p_big_up_compressed",
    "当前处于高波动或危机环境": "high_vol_or_crisis",
    "近期量能明显放大": "volume_expansion",
    "近 3/5 日波动已经放大": "recent_volatility_expansion",
    "降级因素：市场处于 calm，尾部风险证据偏弱": "downgrade_calm_regime",
    "降级因素：量能不足，双尾收缩信号不够强": "downgrade_low_volume",
    "降级因素：高置信历史样本中未出现大跌": "downgrade_no_big_down_history",
    "数据受限：缺少关键字段 p_大跌": "missing_p_big_down",
    "数据受限：缺少关键字段 forced_excluded_states": "missing_forced_excluded_states",
    "数据受限：缺少关键字段 predicted_state": "missing_predicted_state",
    "数据受限：缺少关键字段 p_大涨": "missing_p_big_up",
    "数据受限：contradiction_inputs_available 为 false": "contradiction_inputs_unavailable",
}


def resolve_technical_path(technical_path: Path | None = None) -> tuple[Path, str]:
    if technical_path is not None:
        return technical_path, "explicit"
    if task2e_v2.DEFAULT_MAIN_TECHNICAL.exists():
        return task2e_v2.DEFAULT_MAIN_TECHNICAL, "main_worktree"
    if task2e_v2.DEFAULT_SIBLING_TECHNICAL.exists():
        return task2e_v2.DEFAULT_SIBLING_TECHNICAL, "sibling_worktree"
    raise FileNotFoundError("No AVGO_technical_features.csv found.")


def load_inputs(details_path: Path, summary_path: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    details = pd.read_csv(details_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    return details, summary


def filter_missed_rows(details: pd.DataFrame) -> pd.DataFrame:
    missed = details.loc[~details["unsupported_combined"].fillna(False).astype(bool)].copy()
    if len(missed) != EXPECTED_MISSED_TOTAL:
        raise ValueError(f"Expected {EXPECTED_MISSED_TOTAL} missed rows, got {len(missed)}")
    return missed.reset_index(drop=True)


def join_support_context(
    missed_rows: pd.DataFrame,
    *,
    v4_path: Path,
    technical_path: Path,
) -> pd.DataFrame:
    v4_rows = pd.read_csv(v4_path)
    technical_rows = task2e_v2.load_technical_rows(technical_path)
    joined = missed_rows.merge(
        v4_rows,
        on=["prediction_date", "target_date"],
        how="left",
        suffixes=("", "__v4"),
    )
    joined = joined.merge(
        technical_rows,
        left_on="prediction_date",
        right_on="Date",
        how="left",
        suffixes=("", "__tech"),
    )
    return joined


def _normalize_reasons(reasons: list[str]) -> list[str]:
    labels: list[str] = []
    for reason in reasons:
        label = BIG_DOWN_REASON_LABELS.get(str(reason).strip())
        if label:
            labels.append(label)
    return sorted(set(labels))


def classify_big_up_raw_residual(card_payload: dict[str, Any]) -> tuple[str, list[str]]:
    decision = str(card_payload.get("audit_decision") or "")
    flags = list(card_payload.get("triggered_flags") or [])
    if decision == "hard_excluded" and not flags:
        return "raw_no_contradiction_flags", ["audit_hard_excluded", "no_triggered_flags"]
    labels = [f"audit_{decision}"] if decision else []
    labels.extend(str(flag).strip() for flag in flags if str(flag).strip())
    return "raw_other", labels or ["raw_unlabeled"]


def classify_big_down_raw_residual(
    row: dict[str, Any],
    payload: dict[str, Any],
) -> tuple[str, list[str]]:
    forced_states = task2e_v2._split_states(row.get("forced_excluded_states"))
    predicted_state = str(row.get("predicted_state") or "").strip()
    p_big_down = task2e_v2._safe_float(row.get("p_大跌"))
    p_big_up = task2e_v2._safe_float(row.get("p_大涨"))
    dual_extremes = "大涨" in forced_states and "大跌" in forced_states
    base_candidate = dual_extremes or (
        predicted_state == "震荡"
        and p_big_down is not None
        and p_big_down <= 0.05
        and p_big_up is not None
        and p_big_up <= 0.05
    )
    labels = _normalize_reasons(list(payload.get("reasons") or []))
    if not base_candidate:
        return "raw_no_base_tail_pattern", labels
    if int(payload.get("tail_compression_score") or 0) < TAIL_COMPRESSION_THRESHOLD:
        return "raw_tail_pattern_but_score_below_threshold", labels
    return "raw_other", labels or ["raw_unlabeled"]


def classify_technical_residual(
    *,
    excluded_state: str,
    row: dict[str, Any],
) -> tuple[str, list[str]]:
    if excluded_state == "大涨":
        flags = task2e_v2._big_up_technical_flags(row)
    elif excluded_state == "大跌":
        flags = task2e_v2._big_down_technical_flags(row)
    else:
        flags = []

    if not flags:
        return "tech_zero_support_signals", []
    if len(flags) == 1:
        return f"tech_single_signal_{flags[0]}", flags
    return "tech_other", flags


def evaluate_missed_row(row: dict[str, Any]) -> dict[str, Any]:
    excluded_state = str(row.get("excluded_state_under_validation") or "")
    technical_label, technical_flags = classify_technical_residual(
        excluded_state=excluded_state,
        row=row,
    )

    if excluded_state == "大涨":
        card_payload = build_contradiction_card(row)
        raw_label, raw_reason_labels = classify_big_up_raw_residual(card_payload)
        raw_support_snapshot = {
            "audit_decision": card_payload.get("audit_decision"),
            "raw_score": None,
        }
    elif excluded_state == "大跌":
        warning_payload = build_big_down_tail_warning(row)
        raw_label, raw_reason_labels = classify_big_down_raw_residual(row, warning_payload)
        raw_support_snapshot = {
            "audit_decision": None,
            "raw_score": warning_payload.get("tail_compression_score"),
        }
    else:
        raw_label, raw_reason_labels = "raw_other", ["unknown_state"]
        raw_support_snapshot = {
            "audit_decision": None,
            "raw_score": None,
        }

    return {
        "prediction_date": row.get("prediction_date"),
        "target_date": row.get("target_date"),
        "excluded_state_under_validation": excluded_state,
        "actual_state": row.get("actual_state"),
        "raw_residual_label": raw_label,
        "raw_reason_labels": "|".join(raw_reason_labels),
        "technical_residual_label": technical_label,
        "technical_flags": "|".join(technical_flags),
        "technical_flag_count": len(technical_flags),
        "raw_signal_status": row.get("raw_enriched_signal"),
        "unsupported_by_raw_enriched": bool(row.get("unsupported_by_raw_enriched")),
        "unsupported_by_technical_features": bool(row.get("unsupported_by_technical_features")),
        "audit_decision": raw_support_snapshot["audit_decision"],
        "tail_compression_score": raw_support_snapshot["raw_score"],
    }


def _counter_from_column(frame: pd.DataFrame, column: str) -> dict[str, int]:
    counter = frame[column].value_counts(dropna=False).to_dict() if not frame.empty else {}
    return dict(sorted(((str(key), int(value)) for key, value in counter.items()), key=lambda item: (-item[1], item[0])))


def _counter_from_labels(frame: pd.DataFrame, column: str) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for raw in frame[column].fillna(""):
        for item in task3a._split_listish(raw):
            counter[item] += 1
    return dict(sorted(counter.items(), key=lambda item: (-item[1], item[0])))


def _combo_counter(frame: pd.DataFrame) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for _, row in frame.iterrows():
        combo = f"{row['raw_residual_label']} + {row['technical_residual_label']}"
        counter[combo] += 1
    return dict(sorted(counter.items(), key=lambda item: (-item[1], item[0]))[:20])


def build_summary(
    evaluated: pd.DataFrame,
    original_summary: dict[str, Any],
) -> dict[str, Any]:
    baseline = original_summary.get("overall") or original_summary.get("summary", {}).get("overall", {})
    summary: dict[str, Any] = {
        "baseline": baseline,
        "missed_total": int(len(evaluated)),
        "raw_residual_counts": _counter_from_column(evaluated, "raw_residual_label"),
        "technical_residual_counts": _counter_from_column(evaluated, "technical_residual_label"),
        "raw_reason_counts": _counter_from_labels(evaluated, "raw_reason_labels"),
        "technical_flag_counts": _counter_from_labels(evaluated, "technical_flags"),
        "cross_residual_combo_counts": _combo_counter(evaluated),
        "by_state": {},
    }

    for state, subset in evaluated.groupby("excluded_state_under_validation"):
        summary["by_state"][state] = {
            "missed_total": int(len(subset)),
            "raw_residual_counts": _counter_from_column(subset, "raw_residual_label"),
            "technical_residual_counts": _counter_from_column(subset, "technical_residual_label"),
            "raw_reason_counts": _counter_from_labels(subset, "raw_reason_labels"),
            "technical_flag_counts": _counter_from_labels(subset, "technical_flags"),
        }

    return summary


def build_report_markdown(
    *,
    source: dict[str, Any],
    summary: dict[str, Any],
) -> str:
    lines = [
        "# Task 3B — Missed False Exclusion Residual Analysis",
        "",
        "## Sources",
        f"- details: `{source['details_path']}` ({source['input_source']})",
        f"- summary: `{source['summary_path']}` ({source['input_source']})",
        f"- v4 replay: `{source['v4_path']}` ({source['v4_source']})",
        f"- technical features: `{source['technical_path']}` ({source['technical_source']})",
        "",
        "## Residual Total",
        f"- missed_total: {summary['missed_total']}",
        "",
        "## Raw Residual Sources",
    ]
    for key, value in summary["raw_residual_counts"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Technical Residual Sources"])
    for key, value in summary["technical_residual_counts"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Raw Supporting Context"])
    for key, value in summary["raw_reason_counts"].items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines) + "\n"


def write_outputs(
    *,
    output_dir: Path,
    evaluated: pd.DataFrame,
    source: dict[str, Any],
    summary: dict[str, Any],
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "missed_false_exclusion_residual_details.csv"
    json_path = output_dir / "missed_false_exclusion_residual_summary.json"
    md_path = output_dir / "missed_false_exclusion_residual_report.md"

    evaluated.to_csv(csv_path, index=False)
    json_path.write_text(
        json.dumps({"source": source, "summary": summary}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    md_path.write_text(
        build_report_markdown(source=source, summary=summary),
        encoding="utf-8",
    )
    return {
        "csv": csv_path.as_posix(),
        "json": json_path.as_posix(),
        "md": md_path.as_posix(),
    }


def run(
    *,
    details_path: Path | None = None,
    summary_path: Path | None = None,
    v4_path: Path | None = None,
    technical_path: Path | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    resolved_details, resolved_summary, input_notes = task3a.resolve_input_paths(
        details_path=details_path,
        summary_path=summary_path,
    )
    resolved_v4, v4_source = task3a.resolve_v4_path(v4_path=v4_path)
    resolved_technical, technical_source = resolve_technical_path(technical_path=technical_path)
    details, original_summary = load_inputs(resolved_details, resolved_summary)
    missed_rows = filter_missed_rows(details)
    joined = join_support_context(
        missed_rows,
        v4_path=resolved_v4,
        technical_path=resolved_technical,
    )
    evaluated = pd.DataFrame(
        [evaluate_missed_row(record) for record in joined.to_dict("records")]
    )
    summary = build_summary(evaluated, original_summary)
    source = {
        "details_path": resolved_details.as_posix(),
        "summary_path": resolved_summary.as_posix(),
        "v4_path": resolved_v4.as_posix(),
        "technical_path": resolved_technical.as_posix(),
        "v4_source": v4_source,
        "technical_source": technical_source,
        **input_notes,
    }
    output_paths = write_outputs(
        output_dir=output_dir,
        evaluated=evaluated,
        source=source,
        summary=summary,
    )
    return {
        "source": source,
        "summary": summary,
        "evaluated": evaluated,
        "output_paths": output_paths,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--details-csv", type=Path, default=None)
    parser.add_argument("--summary-json", type=Path, default=None)
    parser.add_argument("--v4-csv", type=Path, default=None)
    parser.add_argument("--technical-csv", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)

    result = run(
        details_path=args.details_csv,
        summary_path=args.summary_json,
        v4_path=args.v4_csv,
        technical_path=args.technical_csv,
        output_dir=args.output_dir,
    )
    summary = result["summary"]
    print("Task 3B missed-false-exclusion residual analysis completed")
    print(f"missed_total={summary['missed_total']}")
    for label, count in summary["raw_residual_counts"].items():
        print(f"raw:{label}={count}")
    for label, count in summary["technical_residual_counts"].items():
        print(f"tech:{label}={count}")
    print(f"csv: {result['output_paths']['csv']}")
    print(f"json: {result['output_paths']['json']}")
    print(f"md: {result['output_paths']['md']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
