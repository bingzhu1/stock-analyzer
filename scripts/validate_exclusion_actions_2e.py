#!/usr/bin/env python3
"""Task 2E — validate historical exclusion actions against new evidence.

This is a read-only offline validator. It does NOT change prediction rules,
UI, warning levels, or existing contradiction-card logic.

Input sources:
  - replay_full_prob_rows_enriched.jsonl
    New collected raw-data evidence (macro / earnings / peer / regime / etc.)
  - replay_full_prob_rows_with_technical_features.jsonl
    Task 2D-attached technical indicators (RSI / MACD / MA distance / etc.)

Analysis unit:
  - one exclusion action = one excluded state on one replay row

Support rule:
  - `unsupported_by_raw_data`: the existing read-only raw-data auditor says the
    historical hard exclusion is not fully supported.
  - `unsupported_by_technical_features`: a conservative technical-evidence
    cluster contradicts the exclusion.
  - `unsupported`: either of the two checks is true.
"""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
import sys
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.big_down_tail_warning import build_big_down_tail_warning
from services.big_up_contradiction_card import build_contradiction_card


DEFAULT_OUTPUT_DIR = ROOT / "logs/historical_training/exclusion_action_validation_2e"

DEFAULT_MAIN_ENRICHED = (
    ROOT / "logs/historical_training/state_probabilities_v1/replay_full_prob_rows_enriched.jsonl"
)
DEFAULT_MAIN_TECHNICAL = (
    ROOT
    / "logs/historical_training/state_probabilities_v1/replay_full_prob_rows_with_technical_features.jsonl"
)
DEFAULT_SIBLING_ENRICHED = (
    ROOT
    / ".claude/worktrees/beautiful-mcclintock-1dcda2/logs/historical_training/state_probabilities_v1/replay_full_prob_rows_enriched.jsonl"
)
DEFAULT_SIBLING_TECHNICAL = (
    ROOT
    / ".claude/worktrees/beautiful-mcclintock-1dcda2/logs/historical_training/state_probabilities_v1/replay_full_prob_rows_with_technical_features.jsonl"
)


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


def _split_excluded_states(value: Any) -> list[str]:
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


def _load_jsonl_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def resolve_input_paths(
    enriched_path: Path | None = None,
    technical_path: Path | None = None,
) -> tuple[Path, Path, dict[str, str]]:
    if enriched_path is not None and technical_path is not None:
        return enriched_path, technical_path, {
            "enriched_source": "explicit",
            "technical_source": "explicit",
        }

    if DEFAULT_MAIN_ENRICHED.exists() and DEFAULT_MAIN_TECHNICAL.exists():
        return DEFAULT_MAIN_ENRICHED, DEFAULT_MAIN_TECHNICAL, {
            "enriched_source": "main_worktree",
            "technical_source": "main_worktree",
        }

    if DEFAULT_SIBLING_ENRICHED.exists() and DEFAULT_SIBLING_TECHNICAL.exists():
        return DEFAULT_SIBLING_ENRICHED, DEFAULT_SIBLING_TECHNICAL, {
            "enriched_source": "sibling_worktree",
            "technical_source": "sibling_worktree",
        }

    raise FileNotFoundError(
        "Task 2E inputs not found in main or sibling worktree."
    )


def merge_replay_sources(
    enriched_path: Path,
    technical_path: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    technical_rows = _load_jsonl_rows(technical_path)
    technical_by_date = {
        str(row.get("as_of_date")): row
        for row in technical_rows
        if row.get("as_of_date")
    }

    merged_rows: list[dict[str, Any]] = []
    missing_technical_dates: list[str] = []
    for row in _load_jsonl_rows(enriched_path):
        as_of_date = str(row.get("as_of_date") or "")
        merged = dict(row)
        technical = technical_by_date.get(as_of_date)
        if technical is None:
            missing_technical_dates.append(as_of_date)
            merged_rows.append(merged)
            continue
        for key, value in technical.items():
            if key not in merged or merged.get(key) in (None, ""):
                merged[key] = value
        # Existing raw-data validators expect the legacy `vol_ratio20` name.
        if merged.get("vol_ratio20") is None and merged.get("vol_ratio_20") is not None:
            merged["vol_ratio20"] = merged["vol_ratio_20"]
        merged_rows.append(merged)

    return merged_rows, {
        "rows_enriched": len(_load_jsonl_rows(enriched_path)),
        "rows_technical": len(technical_rows),
        "rows_merged": len(merged_rows),
        "missing_technical_dates_count": len(missing_technical_dates),
        "missing_technical_dates_examples": missing_technical_dates[:10],
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
    if (
        (ret5 is not None and ret5 >= 2.0)
        or (ret10 is not None and ret10 >= 4.0)
    ):
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
    if (
        (ret5 is not None and ret5 <= -2.0)
        or (ret10 is not None and ret10 <= -4.0)
    ):
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


def evaluate_exclusion_action(
    row: dict[str, Any],
    excluded_state: str,
) -> dict[str, Any]:
    base = {
        "as_of_date": row.get("as_of_date"),
        "prediction_for_date": row.get("prediction_for_date"),
        "excluded_state": excluded_state,
        "triggered_rules": "|".join(str(x) for x in (row.get("triggered_rules") or []) if str(x).strip()),
        "unsupported_by_raw_data": False,
        "unsupported_by_technical_features": False,
        "unsupported": False,
        "raw_support_signal": "",
        "technical_support_flags": "",
    }

    if excluded_state == "大涨":
        card = build_contradiction_card(row)
        raw_unsupported = card.get("audit_decision") != "hard_excluded"
        technical_flags = _big_up_technical_flags(row)
        technical_unsupported = len(technical_flags) >= 2
        base.update({
            "unsupported_by_raw_data": raw_unsupported,
            "unsupported_by_technical_features": technical_unsupported,
            "unsupported": raw_unsupported or technical_unsupported,
            "raw_support_signal": str(card.get("audit_decision") or ""),
            "technical_support_flags": "|".join(technical_flags),
        })
        return base

    if excluded_state == "大跌":
        payload = build_big_down_tail_warning(row)
        raw_unsupported = bool(payload.get("tail_compression_triggered"))
        technical_flags = _big_down_technical_flags(row)
        technical_unsupported = len(technical_flags) >= 2
        base.update({
            "unsupported_by_raw_data": raw_unsupported,
            "unsupported_by_technical_features": technical_unsupported,
            "unsupported": raw_unsupported or technical_unsupported,
            "raw_support_signal": "tail_compression_triggered" if raw_unsupported else "no_raw_contradiction",
            "technical_support_flags": "|".join(technical_flags),
        })
        return base

    base["raw_support_signal"] = "unsupported_state_not_evaluated"
    return base


def build_action_rows(merged_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    action_rows: list[dict[str, Any]] = []
    for row in merged_rows:
        for excluded_state in _split_excluded_states(row.get("forced_excluded_states")):
            if excluded_state not in {"大涨", "大跌"}:
                continue
            action_rows.append(evaluate_exclusion_action(row, excluded_state))
    return action_rows


def _ratio(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return numerator / denominator


def summarize_action_rows(action_rows: list[dict[str, Any]]) -> dict[str, Any]:
    frame = pd.DataFrame(action_rows)
    if frame.empty:
        return {
            "overall": {
                "total_exclusion_actions": 0,
                "unsupported_actions": 0,
                "unsupported_rate": None,
            },
            "by_state": {},
        }

    overall_total = int(len(frame))
    overall_unsupported = int(frame["unsupported"].sum())
    overall_raw = int(frame["unsupported_by_raw_data"].sum())
    overall_technical = int(frame["unsupported_by_technical_features"].sum())
    both = int((frame["unsupported_by_raw_data"] & frame["unsupported_by_technical_features"]).sum())
    raw_only = int((frame["unsupported_by_raw_data"] & ~frame["unsupported_by_technical_features"]).sum())
    technical_only = int((~frame["unsupported_by_raw_data"] & frame["unsupported_by_technical_features"]).sum())

    by_state: dict[str, Any] = {}
    for excluded_state, subset in frame.groupby("excluded_state"):
        total = int(len(subset))
        unsupported = int(subset["unsupported"].sum())
        unsupported_raw = int(subset["unsupported_by_raw_data"].sum())
        unsupported_technical = int(subset["unsupported_by_technical_features"].sum())
        both_state = int((subset["unsupported_by_raw_data"] & subset["unsupported_by_technical_features"]).sum())
        raw_only_state = int((subset["unsupported_by_raw_data"] & ~subset["unsupported_by_technical_features"]).sum())
        technical_only_state = int((~subset["unsupported_by_raw_data"] & subset["unsupported_by_technical_features"]).sum())
        by_state[excluded_state] = {
            "total_exclusion_actions": total,
            "unsupported_actions": unsupported,
            "unsupported_rate": _ratio(unsupported, total),
            "unsupported_by_raw_data": unsupported_raw,
            "unsupported_by_technical_features": unsupported_technical,
            "unsupported_by_both": both_state,
            "unsupported_by_raw_only": raw_only_state,
            "unsupported_by_technical_only": technical_only_state,
            "supported_actions": total - unsupported,
        }

    return {
        "overall": {
            "total_exclusion_actions": overall_total,
            "unsupported_actions": overall_unsupported,
            "unsupported_rate": _ratio(overall_unsupported, overall_total),
            "unsupported_by_raw_data": overall_raw,
            "unsupported_by_technical_features": overall_technical,
            "unsupported_by_both": both,
            "unsupported_by_raw_only": raw_only,
            "unsupported_by_technical_only": technical_only,
            "supported_actions": overall_total - overall_unsupported,
        },
        "by_state": by_state,
    }


def build_report_markdown(
    *,
    source: dict[str, Any],
    merge_summary: dict[str, Any],
    summary: dict[str, Any],
) -> str:
    overall = summary["overall"]
    lines = [
        "# Task 2E — Exclusion Action Validation",
        "",
        "## Scope",
        "- No prediction-rule changes",
        "- No UI changes",
        "- No warning / strong_warning output layer",
        "- Unit of analysis: one exclusion action",
        "",
        "## Sources",
        f"- Enriched replay: `{source['enriched_path']}` ({source['enriched_source']})",
        f"- Technical replay: `{source['technical_path']}` ({source['technical_source']})",
        f"- Merged replay rows: {merge_summary['rows_merged']}",
        f"- Missing technical joins: {merge_summary['missing_technical_dates_count']}",
        "",
        "## Overall",
        f"- Total exclusion actions: {overall['total_exclusion_actions']}",
        f"- Unsupported actions: {overall['unsupported_actions']}",
        f"- Unsupported rate: {overall['unsupported_rate']:.2%}" if overall["unsupported_rate"] is not None else "- Unsupported rate: N/A",
        f"- Unsupported by raw data: {overall['unsupported_by_raw_data']}",
        f"- Unsupported by technical features: {overall['unsupported_by_technical_features']}",
        f"- Unsupported by both: {overall['unsupported_by_both']}",
        f"- Unsupported by raw only: {overall['unsupported_by_raw_only']}",
        f"- Unsupported by technical only: {overall['unsupported_by_technical_only']}",
        "",
        "## By State",
    ]
    for excluded_state in ("大涨", "大跌"):
        state = summary["by_state"].get(excluded_state)
        if not state:
            lines.append(f"- {excluded_state}: no exclusion actions")
            continue
        rate = (
            f"{state['unsupported_rate']:.2%}"
            if state["unsupported_rate"] is not None
            else "N/A"
        )
        lines.append(
            f"- {excluded_state}: unsupported {state['unsupported_actions']}/{state['total_exclusion_actions']} "
            f"({rate}); raw={state['unsupported_by_raw_data']}, technical={state['unsupported_by_technical_features']}, "
            f"both={state['unsupported_by_both']}"
        )
    return "\n".join(lines) + "\n"


def write_outputs(
    *,
    output_dir: Path,
    action_rows: list[dict[str, Any]],
    source: dict[str, Any],
    merge_summary: dict[str, Any],
    summary: dict[str, Any],
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "exclusion_action_validation_details.csv"
    json_path = output_dir / "exclusion_action_validation_summary.json"
    md_path = output_dir / "exclusion_action_validation_report.md"

    pd.DataFrame(action_rows).to_csv(csv_path, index=False)
    json_path.write_text(
        json.dumps(
            {
                "source": source,
                "merge_summary": merge_summary,
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
            merge_summary=merge_summary,
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
    enriched_path: Path | None = None,
    technical_path: Path | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    resolved_enriched, resolved_technical, source_notes = resolve_input_paths(
        enriched_path=enriched_path,
        technical_path=technical_path,
    )
    merged_rows, merge_summary = merge_replay_sources(
        enriched_path=resolved_enriched,
        technical_path=resolved_technical,
    )
    action_rows = build_action_rows(merged_rows)
    summary = summarize_action_rows(action_rows)
    source = {
        "enriched_path": resolved_enriched.as_posix(),
        "technical_path": resolved_technical.as_posix(),
        **source_notes,
    }
    output_paths = write_outputs(
        output_dir=output_dir,
        action_rows=action_rows,
        source=source,
        merge_summary=merge_summary,
        summary=summary,
    )
    return {
        "source": source,
        "merge_summary": merge_summary,
        "action_rows": action_rows,
        "summary": summary,
        "output_paths": output_paths,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--enriched-jsonl", type=Path, default=None)
    parser.add_argument("--technical-jsonl", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)

    result = run(
        enriched_path=args.enriched_jsonl,
        technical_path=args.technical_jsonl,
        output_dir=args.output_dir,
    )
    overall = result["summary"]["overall"]
    print("Task 2E exclusion-action validation completed")
    print(
        f"unsupported={overall['unsupported_actions']}/"
        f"{overall['total_exclusion_actions']}"
    )
    print(
        f"raw={overall['unsupported_by_raw_data']} "
        f"technical={overall['unsupported_by_technical_features']} "
        f"both={overall['unsupported_by_both']}"
    )
    print(f"csv: {result['output_paths']['csv']}")
    print(f"json: {result['output_paths']['json']}")
    print(f"md: {result['output_paths']['md']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
