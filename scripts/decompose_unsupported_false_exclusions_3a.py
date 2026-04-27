#!/usr/bin/env python3
"""Task 3A — decompose the 111 unsupported false-exclusion cases.

Read-only analysis.

Input priority:
1. User-spec path under logs/technical_features/false_bigup_bigdown_support_validation/
2. Existing Task 2E-v2 output under logs/historical_training/exclusion_action_validation_2e_v2/

This script does not change prediction rules, UI, warnings, or thresholds.
It only explains where the 111 `unsupported_combined=True` cases come from.
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.big_down_tail_warning import build_big_down_tail_warning
from services.big_up_contradiction_card import build_contradiction_card


DEFAULT_OUTPUT_DIR = (
    ROOT / "logs/technical_features/false_bigup_bigdown_support_breakdown_3a"
)

PREFERRED_DETAILS = (
    ROOT
    / "logs/technical_features/false_bigup_bigdown_support_validation/false_bigup_bigdown_support_validation_details.csv"
)
PREFERRED_SUMMARY = (
    ROOT
    / "logs/technical_features/false_bigup_bigdown_support_validation/false_bigup_bigdown_support_validation_summary.json"
)
FALLBACK_DETAILS = (
    ROOT
    / "logs/historical_training/exclusion_action_validation_2e_v2/false_exclusion_validation_details.csv"
)
FALLBACK_SUMMARY = (
    ROOT
    / "logs/historical_training/exclusion_action_validation_2e_v2/false_exclusion_validation_summary.json"
)

DEFAULT_MAIN_V4 = (
    ROOT / "logs/historical_training/exclusion_log_enriched/enriched_conflict_analysis_v4.csv"
)
DEFAULT_SIBLING_V4 = (
    ROOT
    / ".claude/worktrees/eloquent-stonebraker-e0cd86/logs/historical_training/exclusion_log_enriched/enriched_conflict_analysis_v4.csv"
)

EXPECTED_UNSUPPORTED_TOTAL = 111


BIG_UP_RAW_LABELS = {
    "macro_contradiction_softening": "macro_contradiction",
    "earnings_post_window_softening": "post_earnings_window",
    "sample_confidence_invalidation": "sample_confidence_invalidation",
    "oversold_rebound_risk": "oversold_rebound",
    "breakout_continuation_risk": "breakout_continuation",
    "peer_catchup_risk": "peer_catchup",
    "consolidation_breakout_risk": "consolidation_breakout",
    "market_rebound_softening": "market_rebound",
    "crisis_regime_softening": "crisis_regime",
    "low_sample_confidence_softening": "low_sample_confidence",
}

BIG_DOWN_REASON_LABELS = {
    "系统同时排除了大涨和大跌两端状态": "dual_extremes",
    "预测结果偏向震荡": "predicted_neutral",
    "大跌概率被压低到 0.05 以下": "p_big_down_compressed",
    "大涨概率被压低到 0.05 以下": "p_big_up_compressed",
    "当前处于高波动或危机环境": "high_vol_or_crisis",
    "近期量能明显放大": "volume_expansion",
    "近 3/5 日波动已经放大": "recent_volatility_expansion",
}

TECH_LABELS = {
    "rsi_bullish": "rsi_bullish",
    "macd_bullish": "macd_bullish",
    "trend_above_ma20_ma50": "trend_above_ma20_ma50",
    "positive_momentum": "positive_momentum",
    "high_position": "high_position",
    "volume_confirmation": "volume_confirmation",
    "rsi_bearish": "rsi_bearish",
    "macd_bearish": "macd_bearish",
    "trend_below_ma20_ma50": "trend_below_ma20_ma50",
    "negative_momentum": "negative_momentum",
    "low_position": "low_position",
    "volume_stress": "volume_stress",
}


def _split_listish(value: Any) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    if not text:
        return []
    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = ast.literal_eval(text)
        except Exception:
            parsed = None
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    return [item.strip() for item in text.split("|") if item.strip()]


def resolve_input_paths(
    details_path: Path | None = None,
    summary_path: Path | None = None,
) -> tuple[Path, Path, dict[str, str]]:
    if details_path is not None and summary_path is not None:
        return details_path, summary_path, {"input_source": "explicit"}

    if PREFERRED_DETAILS.exists() and PREFERRED_SUMMARY.exists():
        return PREFERRED_DETAILS, PREFERRED_SUMMARY, {"input_source": "preferred_task_path"}

    if FALLBACK_DETAILS.exists() and FALLBACK_SUMMARY.exists():
        return FALLBACK_DETAILS, FALLBACK_SUMMARY, {"input_source": "task_2e_v2_fallback"}

    raise FileNotFoundError("Task 3A input files not found.")


def resolve_v4_path(v4_path: Path | None = None) -> tuple[Path, str]:
    if v4_path is not None:
        return v4_path, "explicit"
    if DEFAULT_MAIN_V4.exists():
        return DEFAULT_MAIN_V4, "main_worktree"
    if DEFAULT_SIBLING_V4.exists():
        return DEFAULT_SIBLING_V4, "sibling_worktree"
    raise FileNotFoundError("No enriched_conflict_analysis_v4.csv found.")


def load_inputs(details_path: Path, summary_path: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    details = pd.read_csv(details_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    return details, summary


def filter_unsupported_rows(details: pd.DataFrame) -> pd.DataFrame:
    unsupported = details.loc[details["unsupported_combined"].fillna(False).astype(bool)].copy()
    if len(unsupported) != EXPECTED_UNSUPPORTED_TOTAL:
        raise ValueError(
            f"Expected {EXPECTED_UNSUPPORTED_TOTAL} unsupported rows, got {len(unsupported)}"
        )
    return unsupported.reset_index(drop=True)


def join_v4_rows(unsupported_rows: pd.DataFrame, v4_path: Path) -> pd.DataFrame:
    v4 = pd.read_csv(v4_path)
    joined = unsupported_rows.merge(
        v4,
        on=["prediction_date", "target_date"],
        how="left",
        suffixes=("", "__v4"),
    )
    return joined


def normalize_big_up_raw_sources(card_payload: dict[str, Any]) -> list[str]:
    labels: list[str] = []
    for flag in card_payload.get("triggered_flags") or []:
        label = BIG_UP_RAW_LABELS.get(str(flag).strip())
        if label:
            labels.append(label)
    return sorted(set(labels))


def normalize_big_down_raw_sources(payload: dict[str, Any]) -> list[str]:
    labels: list[str] = []
    for reason in payload.get("reasons") or []:
        text = str(reason).strip()
        if not text or text.startswith("降级因素：") or text.startswith("数据受限："):
            continue
        label = BIG_DOWN_REASON_LABELS.get(text)
        if label:
            labels.append(label)
    return sorted(set(labels))


def normalize_technical_sources(raw_flags: Any) -> list[str]:
    labels: list[str] = []
    for flag in _split_listish(raw_flags):
        label = TECH_LABELS.get(flag)
        if label:
            labels.append(label)
    return sorted(set(labels))


def evaluate_source_row(row: dict[str, Any]) -> dict[str, Any]:
    excluded_state = str(row.get("excluded_state_under_validation") or "")
    raw_unsupported = bool(row.get("unsupported_by_raw_enriched"))
    technical_unsupported = bool(row.get("unsupported_by_technical_features"))
    raw_sources: list[str] = []
    technical_sources = normalize_technical_sources(row.get("technical_flags"))

    if excluded_state == "大涨" and raw_unsupported:
        card_payload = build_contradiction_card(row)
        raw_sources = normalize_big_up_raw_sources(card_payload)
        if not raw_sources:
            raw_sources = [f"audit_decision_{card_payload.get('audit_decision') or 'unknown'}"]
    elif excluded_state == "大跌" and raw_unsupported:
        payload = build_big_down_tail_warning(row)
        raw_sources = normalize_big_down_raw_sources(payload)
        if not raw_sources:
            raw_sources = ["tail_compression_unlabeled"]

    if technical_unsupported and not technical_sources:
        technical_sources = ["technical_unlabeled"]

    support_mix = "supported"
    if raw_unsupported and technical_unsupported:
        support_mix = "raw_and_technical"
    elif raw_unsupported:
        support_mix = "raw_only"
    elif technical_unsupported:
        support_mix = "technical_only"

    return {
        "prediction_date": row.get("prediction_date"),
        "target_date": row.get("target_date"),
        "excluded_state_under_validation": excluded_state,
        "actual_state": row.get("actual_state"),
        "unsupported_by_raw_enriched": raw_unsupported,
        "unsupported_by_technical_features": technical_unsupported,
        "support_mix": support_mix,
        "raw_source_labels": "|".join(raw_sources),
        "technical_source_labels": "|".join(technical_sources),
        "raw_source_count": len(raw_sources),
        "technical_source_count": len(technical_sources),
    }


def _counter_from_label_column(frame: pd.DataFrame, column: str) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for raw in frame[column].fillna(""):
        for item in _split_listish(raw):
            counter[item] += 1
    return dict(sorted(counter.items(), key=lambda item: (-item[1], item[0])))


def _combo_counter(frame: pd.DataFrame, columns: list[str]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for _, row in frame.iterrows():
        labels: list[str] = []
        for column in columns:
            labels.extend(_split_listish(row.get(column)))
        if not labels:
            continue
        counter["|".join(sorted(set(labels)))] += 1
    return dict(sorted(counter.items(), key=lambda item: (-item[1], item[0]))[:20])


def build_summary(
    evaluated: pd.DataFrame,
    original_summary: dict[str, Any],
) -> dict[str, Any]:
    mix_counts = (
        evaluated["support_mix"].value_counts(dropna=False).to_dict()
        if not evaluated.empty
        else {}
    )

    raw_only = evaluated.loc[evaluated["support_mix"] == "raw_only"]
    tech_only = evaluated.loc[evaluated["support_mix"] == "technical_only"]
    both = evaluated.loc[evaluated["support_mix"] == "raw_and_technical"]

    summary: dict[str, Any] = {
        "baseline": original_summary.get("overall") or original_summary.get("summary", {}).get("overall", {}),
        "unsupported_total": int(len(evaluated)),
        "support_mix_counts": {
            "raw_only": int(mix_counts.get("raw_only", 0)),
            "technical_only": int(mix_counts.get("technical_only", 0)),
            "raw_and_technical": int(mix_counts.get("raw_and_technical", 0)),
        },
        "raw_source_counts": _counter_from_label_column(
            evaluated.loc[evaluated["unsupported_by_raw_enriched"]],
            "raw_source_labels",
        ),
        "technical_source_counts": _counter_from_label_column(
            evaluated.loc[evaluated["unsupported_by_technical_features"]],
            "technical_source_labels",
        ),
        "raw_combo_counts": _combo_counter(
            evaluated.loc[evaluated["unsupported_by_raw_enriched"]],
            ["raw_source_labels"],
        ),
        "technical_combo_counts": _combo_counter(
            evaluated.loc[evaluated["unsupported_by_technical_features"]],
            ["technical_source_labels"],
        ),
        "cross_source_combo_counts": _combo_counter(
            both,
            ["raw_source_labels", "technical_source_labels"],
        ),
        "by_state": {},
    }

    for state, subset in evaluated.groupby("excluded_state_under_validation"):
        state_mix = subset["support_mix"].value_counts(dropna=False).to_dict()
        summary["by_state"][state] = {
            "unsupported_total": int(len(subset)),
            "support_mix_counts": {
                "raw_only": int(state_mix.get("raw_only", 0)),
                "technical_only": int(state_mix.get("technical_only", 0)),
                "raw_and_technical": int(state_mix.get("raw_and_technical", 0)),
            },
            "raw_source_counts": _counter_from_label_column(
                subset.loc[subset["unsupported_by_raw_enriched"]],
                "raw_source_labels",
            ),
            "technical_source_counts": _counter_from_label_column(
                subset.loc[subset["unsupported_by_technical_features"]],
                "technical_source_labels",
            ),
        }

    return summary


def build_report_markdown(
    *,
    source: dict[str, Any],
    summary: dict[str, Any],
) -> str:
    lines = [
        "# Task 3A — Unsupported Source Breakdown",
        "",
        "## Sources",
        f"- details: `{source['details_path']}` ({source['input_source']})",
        f"- summary: `{source['summary_path']}` ({source['input_source']})",
        f"- v4 replay: `{source['v4_path']}` ({source['v4_source']})",
        "",
        "## Unsupported Mix",
        f"- unsupported_total: {summary['unsupported_total']}",
        f"- raw_only: {summary['support_mix_counts']['raw_only']}",
        f"- technical_only: {summary['support_mix_counts']['technical_only']}",
        f"- raw_and_technical: {summary['support_mix_counts']['raw_and_technical']}",
        "",
        "## Raw Sources",
    ]
    for key, value in summary["raw_source_counts"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Technical Sources"])
    for key, value in summary["technical_source_counts"].items():
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
    csv_path = output_dir / "unsupported_source_breakdown_details.csv"
    json_path = output_dir / "unsupported_source_breakdown_summary.json"
    md_path = output_dir / "unsupported_source_breakdown_report.md"

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
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    resolved_details, resolved_summary, input_notes = resolve_input_paths(
        details_path=details_path,
        summary_path=summary_path,
    )
    resolved_v4, v4_source = resolve_v4_path(v4_path=v4_path)
    details, original_summary = load_inputs(resolved_details, resolved_summary)
    unsupported_rows = filter_unsupported_rows(details)
    joined = join_v4_rows(unsupported_rows, resolved_v4)
    evaluated = pd.DataFrame(
        [evaluate_source_row(record) for record in joined.to_dict("records")]
    )
    summary = build_summary(evaluated, original_summary)
    source = {
        "details_path": resolved_details.as_posix(),
        "summary_path": resolved_summary.as_posix(),
        "v4_path": resolved_v4.as_posix(),
        "v4_source": v4_source,
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
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)

    result = run(
        details_path=args.details_csv,
        summary_path=args.summary_json,
        v4_path=args.v4_csv,
        output_dir=args.output_dir,
    )
    mix = result["summary"]["support_mix_counts"]
    print("Task 3A unsupported-source breakdown completed")
    print(f"unsupported_total={result['summary']['unsupported_total']}")
    print(
        f"raw_only={mix['raw_only']} "
        f"technical_only={mix['technical_only']} "
        f"raw_and_technical={mix['raw_and_technical']}"
    )
    print(f"csv: {result['output_paths']['csv']}")
    print(f"json: {result['output_paths']['json']}")
    print(f"md: {result['output_paths']['md']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
