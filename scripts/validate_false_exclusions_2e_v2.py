#!/usr/bin/env python3
"""Task 2E-v2 — validate the 165 historical false exclusions only.

Hard requirements for this driver:
1. Reproduce false_big_up=105 and false_big_down=60 from the v4 replay source.
2. Stop if those counts do not match exactly.
3. Only after reproducing them, evaluate how many of those 165 cases are:
   - unsupported by raw/enriched data
   - unsupported by technical features
   - unsupported by either source

Read-only analysis. No prediction-rule changes. No UI changes.
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.big_down_tail_warning import build_big_down_tail_warning
from services.big_up_contradiction_card import build_contradiction_card


DEFAULT_OUTPUT_DIR = ROOT / "logs/historical_training/exclusion_action_validation_2e_v2"

DEFAULT_MAIN_V4 = (
    ROOT / "logs/historical_training/exclusion_log_enriched/enriched_conflict_analysis_v4.csv"
)
DEFAULT_SIBLING_V4 = (
    ROOT
    / ".claude/worktrees/eloquent-stonebraker-e0cd86/logs/historical_training/exclusion_log_enriched/enriched_conflict_analysis_v4.csv"
)
DEFAULT_MAIN_TECHNICAL = ROOT / "enriched_data/AVGO_technical_features.csv"
DEFAULT_SIBLING_TECHNICAL = (
    ROOT
    / ".claude/worktrees/beautiful-mcclintock-1dcda2/enriched_data/AVGO_technical_features.csv"
)

EXPECTED_FALSE_BIG_UP = 105
EXPECTED_FALSE_BIG_DOWN = 60


def _safe_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed != parsed:
        return None
    return parsed


def _split_states(value: Any) -> list[str]:
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


def resolve_inputs(
    v4_path: Path | None = None,
    technical_path: Path | None = None,
) -> tuple[Path, Path, dict[str, str]]:
    if v4_path is not None and technical_path is not None:
        return v4_path, technical_path, {
            "v4_source": "explicit",
            "technical_source": "explicit",
        }

    if DEFAULT_MAIN_V4.exists():
        resolved_v4 = DEFAULT_MAIN_V4
        v4_source = "main_worktree"
    elif DEFAULT_SIBLING_V4.exists():
        resolved_v4 = DEFAULT_SIBLING_V4
        v4_source = "sibling_worktree"
    else:
        raise FileNotFoundError("No enriched_conflict_analysis_v4.csv found.")

    if DEFAULT_MAIN_TECHNICAL.exists():
        resolved_technical = DEFAULT_MAIN_TECHNICAL
        technical_source = "main_worktree"
    elif DEFAULT_SIBLING_TECHNICAL.exists():
        resolved_technical = DEFAULT_SIBLING_TECHNICAL
        technical_source = "sibling_worktree"
    else:
        raise FileNotFoundError("No AVGO_technical_features.csv found.")

    return resolved_v4, resolved_technical, {
        "v4_source": v4_source,
        "technical_source": technical_source,
    }


def load_v4_rows(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def load_technical_rows(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    frame["Date"] = pd.to_datetime(frame["Date"]).dt.strftime("%Y-%m-%d")
    return frame


def extract_false_exclusion_rows(v4_rows: pd.DataFrame) -> pd.DataFrame:
    states = v4_rows["forced_excluded_states"].map(_split_states)
    actual = v4_rows["actual_state"].fillna("").astype(str)
    false_big_up_mask = actual.eq("大涨") & states.map(lambda items: "大涨" in items)
    false_big_down_mask = actual.eq("大跌") & states.map(lambda items: "大跌" in items)

    false_rows = v4_rows.loc[false_big_up_mask | false_big_down_mask].copy()
    false_rows["excluded_state_under_validation"] = [
        "大涨" if up else "大跌"
        for up in false_big_up_mask[false_big_up_mask | false_big_down_mask].tolist()
    ]
    return false_rows.reset_index(drop=True)


def verify_expected_false_counts(false_rows: pd.DataFrame) -> dict[str, int]:
    false_big_up = int((false_rows["excluded_state_under_validation"] == "大涨").sum())
    false_big_down = int((false_rows["excluded_state_under_validation"] == "大跌").sum())
    if false_big_up != EXPECTED_FALSE_BIG_UP or false_big_down != EXPECTED_FALSE_BIG_DOWN:
        raise ValueError(
            "false exclusion counts do not match required baseline: "
            f"false_big_up={false_big_up}, false_big_down={false_big_down}"
        )
    return {
        "false_big_up": false_big_up,
        "false_big_down": false_big_down,
        "false_total": false_big_up + false_big_down,
    }


def join_technical_features(
    false_rows: pd.DataFrame,
    technical_rows: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    merged = false_rows.merge(
        technical_rows,
        left_on="prediction_date",
        right_on="Date",
        how="left",
        suffixes=("", "__tech"),
    )
    return merged, {
        "false_rows": int(len(false_rows)),
        "technical_joined_rows": int(merged["Date"].notna().sum()),
        "technical_missing_rows": int(merged["Date"].isna().sum()),
    }


def _big_up_technical_flags(row: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    rsi_14 = _safe_float(row.get("rsi_14"))
    macd = _safe_float(row.get("macd"))
    macd_signal = _safe_float(row.get("macd_signal"))
    macd_hist = _safe_float(row.get("macd_hist"))
    close_vs_ma20_pct = _safe_float(row.get("close_vs_ma20_pct"))
    close_vs_ma50_pct = _safe_float(row.get("close_vs_ma50_pct"))
    ret1 = _safe_float(row.get("ret1"))
    ret5 = _safe_float(row.get("ret5"))
    ret10 = _safe_float(row.get("ret10"))
    pos20 = _safe_float(row.get("pos20"))
    pos60 = _safe_float(row.get("pos60"))
    vol_ratio_20 = _safe_float(row.get("vol_ratio_20"))

    if rsi_14 is not None and rsi_14 >= 60.0:
        flags.append("rsi_bullish")
    if (
        macd_hist is not None
        and macd_hist > 0
        and macd is not None
        and macd_signal is not None
        and macd > macd_signal
    ):
        flags.append("macd_bullish")
    if (
        close_vs_ma20_pct is not None
        and close_vs_ma20_pct > 0
        and close_vs_ma50_pct is not None
        and close_vs_ma50_pct > 0
    ):
        flags.append("trend_above_ma20_ma50")
    if (ret5 is not None and ret5 >= 2.0) or (ret10 is not None and ret10 >= 4.0):
        flags.append("positive_momentum")
    if (
        pos20 is not None
        and pos20 >= 70.0
        and pos60 is not None
        and pos60 >= 60.0
    ):
        flags.append("high_position")
    if (
        vol_ratio_20 is not None
        and vol_ratio_20 >= 1.2
        and ret1 is not None
        and ret1 > 0
    ):
        flags.append("volume_confirmation")
    return flags


def _big_down_technical_flags(row: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    rsi_14 = _safe_float(row.get("rsi_14"))
    macd = _safe_float(row.get("macd"))
    macd_signal = _safe_float(row.get("macd_signal"))
    macd_hist = _safe_float(row.get("macd_hist"))
    close_vs_ma20_pct = _safe_float(row.get("close_vs_ma20_pct"))
    close_vs_ma50_pct = _safe_float(row.get("close_vs_ma50_pct"))
    ret1 = _safe_float(row.get("ret1"))
    ret5 = _safe_float(row.get("ret5"))
    ret10 = _safe_float(row.get("ret10"))
    pos20 = _safe_float(row.get("pos20"))
    pos60 = _safe_float(row.get("pos60"))
    vol_ratio_20 = _safe_float(row.get("vol_ratio_20"))

    if rsi_14 is not None and rsi_14 <= 40.0:
        flags.append("rsi_bearish")
    if (
        macd_hist is not None
        and macd_hist < 0
        and macd is not None
        and macd_signal is not None
        and macd < macd_signal
    ):
        flags.append("macd_bearish")
    if (
        close_vs_ma20_pct is not None
        and close_vs_ma20_pct < 0
        and close_vs_ma50_pct is not None
        and close_vs_ma50_pct < 0
    ):
        flags.append("trend_below_ma20_ma50")
    if (ret5 is not None and ret5 <= -2.0) or (ret10 is not None and ret10 <= -4.0):
        flags.append("negative_momentum")
    if (
        pos20 is not None
        and pos20 <= 30.0
        and pos60 is not None
        and pos60 <= 40.0
    ):
        flags.append("low_position")
    if (
        vol_ratio_20 is not None
        and vol_ratio_20 >= 1.2
        and ret1 is not None
        and ret1 < 0
    ):
        flags.append("volume_stress")
    return flags


def evaluate_false_row(row: dict[str, Any]) -> dict[str, Any]:
    excluded_state = str(row.get("excluded_state_under_validation") or "")
    base = {
        "prediction_date": row.get("prediction_date"),
        "target_date": row.get("target_date"),
        "actual_state": row.get("actual_state"),
        "actual_close_change": row.get("actual_close_change"),
        "forced_excluded_states": row.get("forced_excluded_states"),
        "excluded_state_under_validation": excluded_state,
        "unsupported_by_raw_enriched": False,
        "unsupported_by_technical_features": False,
        "unsupported_combined": False,
        "raw_enriched_signal": "",
        "technical_flags": "",
    }

    if excluded_state == "大涨":
        raw_unsupported = build_contradiction_card(row)["audit_decision"] != "hard_excluded"
        technical_flags = _big_up_technical_flags(row)
    elif excluded_state == "大跌":
        # Use the underlying contradiction trigger before UI-level downgrade.
        raw_unsupported = bool(build_big_down_tail_warning(row)["tail_compression_triggered"])
        technical_flags = _big_down_technical_flags(row)
    else:
        raw_unsupported = False
        technical_flags = []

    technical_unsupported = len(technical_flags) >= 2
    base.update({
        "unsupported_by_raw_enriched": raw_unsupported,
        "unsupported_by_technical_features": technical_unsupported,
        "unsupported_combined": raw_unsupported or technical_unsupported,
        "raw_enriched_signal": "unsupported" if raw_unsupported else "supported",
        "technical_flags": "|".join(technical_flags),
    })
    return base


def summarize_results(detail_rows: list[dict[str, Any]]) -> dict[str, Any]:
    frame = pd.DataFrame(detail_rows)
    overall = {
        "false_big_up": int((frame["excluded_state_under_validation"] == "大涨").sum()),
        "false_big_down": int((frame["excluded_state_under_validation"] == "大跌").sum()),
        "false_total": int(len(frame)),
        "unsupported_by_raw_enriched": int(frame["unsupported_by_raw_enriched"].sum()),
        "unsupported_by_technical_features": int(frame["unsupported_by_technical_features"].sum()),
        "unsupported_combined": int(frame["unsupported_combined"].sum()),
    }
    by_state: dict[str, Any] = {}
    for state, subset in frame.groupby("excluded_state_under_validation"):
        by_state[state] = {
            "false_total": int(len(subset)),
            "unsupported_by_raw_enriched": int(subset["unsupported_by_raw_enriched"].sum()),
            "unsupported_by_technical_features": int(subset["unsupported_by_technical_features"].sum()),
            "unsupported_combined": int(subset["unsupported_combined"].sum()),
        }
    return {
        "overall": overall,
        "by_state": by_state,
    }


def build_report_markdown(
    *,
    source: dict[str, Any],
    join_summary: dict[str, Any],
    summary: dict[str, Any],
) -> str:
    overall = summary["overall"]
    lines = [
        "# Task 2E-v2 — False Exclusion Validation",
        "",
        "## Source",
        f"- v4 replay: `{source['v4_path']}` ({source['v4_source']})",
        f"- technical features: `{source['technical_path']}` ({source['technical_source']})",
        f"- joined technical rows: {join_summary['technical_joined_rows']}/{join_summary['false_rows']}",
        "",
        "## Required Baseline",
        f"- false_big_up = {overall['false_big_up']}",
        f"- false_big_down = {overall['false_big_down']}",
        f"- false_total = {overall['false_total']}",
        "",
        "## Unsupported Counts",
        f"- unsupported_by_raw_enriched = {overall['unsupported_by_raw_enriched']}",
        f"- unsupported_by_technical_features = {overall['unsupported_by_technical_features']}",
        f"- unsupported_combined = {overall['unsupported_combined']}",
        "",
        "## Three-Line Summary",
        f"- 错误否定大涨 {overall['false_big_up']}",
        f"- 错误否定大跌 {overall['false_big_down']}",
        f"- 合计 {overall['false_total']}",
    ]
    return "\n".join(lines) + "\n"


def write_outputs(
    *,
    output_dir: Path,
    detail_rows: list[dict[str, Any]],
    source: dict[str, Any],
    join_summary: dict[str, Any],
    summary: dict[str, Any],
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "false_exclusion_validation_details.csv"
    json_path = output_dir / "false_exclusion_validation_summary.json"
    md_path = output_dir / "false_exclusion_validation_report.md"

    pd.DataFrame(detail_rows).to_csv(csv_path, index=False)
    json_path.write_text(
        json.dumps(
            {
                "source": source,
                "join_summary": join_summary,
                "summary": summary,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    md_path.write_text(
        build_report_markdown(
            source=source,
            join_summary=join_summary,
            summary=summary,
        ),
        encoding="utf-8",
    )
    return {
        "csv": csv_path.as_posix(),
        "json": json_path.as_posix(),
        "md": md_path.as_posix(),
    }


def run(
    *,
    v4_path: Path | None = None,
    technical_path: Path | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    resolved_v4, resolved_technical, source_notes = resolve_inputs(
        v4_path=v4_path,
        technical_path=technical_path,
    )
    v4_rows = load_v4_rows(resolved_v4)
    false_rows = extract_false_exclusion_rows(v4_rows)
    baseline = verify_expected_false_counts(false_rows)

    technical_rows = load_technical_rows(resolved_technical)
    joined_rows, join_summary = join_technical_features(false_rows, technical_rows)
    detail_rows = [
        evaluate_false_row(record)
        for record in joined_rows.to_dict("records")
    ]
    summary = summarize_results(detail_rows)
    # Keep the required baseline explicit in the summary payload.
    summary["overall"].update(baseline)

    source = {
        "v4_path": resolved_v4.as_posix(),
        "technical_path": resolved_technical.as_posix(),
        **source_notes,
    }
    output_paths = write_outputs(
        output_dir=output_dir,
        detail_rows=detail_rows,
        source=source,
        join_summary=join_summary,
        summary=summary,
    )
    return {
        "source": source,
        "join_summary": join_summary,
        "summary": summary,
        "detail_rows": detail_rows,
        "output_paths": output_paths,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v4-csv", type=Path, default=None)
    parser.add_argument("--technical-csv", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)

    result = run(
        v4_path=args.v4_csv,
        technical_path=args.technical_csv,
        output_dir=args.output_dir,
    )
    overall = result["summary"]["overall"]
    print("Task 2E-v2 validation completed")
    print(f"false_big_up={overall['false_big_up']}")
    print(f"false_big_down={overall['false_big_down']}")
    print(f"false_total={overall['false_total']}")
    print(f"unsupported_by_raw_enriched={overall['unsupported_by_raw_enriched']}")
    print(f"unsupported_by_technical_features={overall['unsupported_by_technical_features']}")
    print(f"unsupported_combined={overall['unsupported_combined']}")
    print(f"csv: {result['output_paths']['csv']}")
    print(f"json: {result['output_paths']['json']}")
    print(f"md: {result['output_paths']['md']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
