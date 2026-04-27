#!/usr/bin/env python3
"""Task 3C-1 — build explanation taxonomy for 111 unsupported cases.

Read-only analysis.

Input:
- Task 3A outputs under logs/technical_features/false_bigup_bigdown_support_breakdown_3a/

This script does not change prediction rules, UI, warnings, thresholds, or
forced_exclusion logic. It only turns the existing 3A source labels into a
future-facing explanation taxonomy with Chinese display copy.
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


DEFAULT_OUTPUT_DIR = ROOT / "logs/technical_features/unsupported_explanation_taxonomy_3c1"
DEFAULT_DETAILS = (
    ROOT / "logs/technical_features/false_bigup_bigdown_support_breakdown_3a/unsupported_source_breakdown_details.csv"
)
DEFAULT_SUMMARY = (
    ROOT / "logs/technical_features/false_bigup_bigdown_support_breakdown_3a/unsupported_source_breakdown_summary.json"
)
EXPECTED_UNSUPPORTED_TOTAL = 111

TIER_LABELS_CN = {
    "strong_evidence": "强证据",
    "supporting_evidence": "辅助证据",
    "data_gap_notice": "数据缺口提醒",
}

TIER_SORT_ORDER = {
    "strong_evidence": 0,
    "supporting_evidence": 1,
    "data_gap_notice": 2,
}

TAXONOMY_CATALOG: dict[str, dict[str, Any]] = {
    "history_support_thin_for_big_up_exclusion": {
        "source_type": "raw",
        "applies_to_exclusion": "大涨",
        "display_tier": "data_gap_notice",
        "title_cn": "历史样本对“否定大涨”支撑偏薄",
        "short_cn": "可比历史样本不足，当前没有足够先例继续高置信排除大涨。",
        "display_cn": "历史样本信心不足，说明这次“否定大涨”更像证据偏薄，而不是有强反证支持。",
        "source_labels": ["sample_confidence_invalidation"],
    },
    "macro_rebound_conflicts_with_big_up_exclusion": {
        "source_type": "raw",
        "applies_to_exclusion": "大涨",
        "display_tier": "strong_evidence",
        "title_cn": "宏观反弹条件与“否定大涨”矛盾",
        "short_cn": "宏观环境更像反弹或风险偏好修复，不支持继续强排除大涨。",
        "display_cn": "新补全的宏观环境信号与原先“否定大涨”的判断方向相反，因此这个否定可靠性明显下降。",
        "source_labels": ["macro_contradiction"],
    },
    "post_earnings_repricing_risk": {
        "source_type": "raw",
        "applies_to_exclusion": "大涨",
        "display_tier": "supporting_evidence",
        "title_cn": "财报后重定价窗口不适合强排除大涨",
        "short_cn": "财报后窗口容易出现重新定价，直接否定大涨的把握会下降。",
        "display_cn": "当前仍处于财报后重定价窗口，这类时段更容易出现方向重估，不适合把大涨当成强排除项。",
        "source_labels": ["post_earnings_window"],
    },
    "dual_tail_conflict_against_big_down_exclusion": {
        "source_type": "raw",
        "applies_to_exclusion": "大跌",
        "display_tier": "strong_evidence",
        "title_cn": "系统同时压低双尾，说明“大跌否定”本身不稳",
        "short_cn": "系统把大涨和大跌两端同时压低，说明尾部压缩过强，大跌不能再当成稳定排除项。",
        "display_cn": "原系统同时压低双尾状态，本身就说明判断偏向过度收缩；在这种结构下，继续否定大跌并不可靠。",
        "source_labels": ["dual_extremes"],
    },
    "tail_compression_context_against_big_down_exclusion": {
        "source_type": "raw",
        "applies_to_exclusion": "大跌",
        "display_tier": "supporting_evidence",
        "title_cn": "震荡压缩结构削弱了“否定大跌”的可信度",
        "short_cn": "预测偏向震荡且上行尾部也被压低，说明系统主要是在做双尾收缩，而不是有力地否定大跌。",
        "display_cn": "这类案例更像整体尾部压缩，而不是有充分证据证明不会出现大跌，因此“大跌否定”只能视为弱结论。",
        "source_labels": ["predicted_neutral", "p_big_up_compressed"],
    },
    "tail_risk_expansion_against_big_down_exclusion": {
        "source_type": "raw",
        "applies_to_exclusion": "大跌",
        "display_tier": "supporting_evidence",
        "title_cn": "波动与量能扩张提示尾部下跌风险仍在",
        "short_cn": "高波动、危机环境或量能放大，说明尾部大跌风险没有被真正消除。",
        "display_cn": "新补全数据提示波动和量能都在扩张，这种环境下尾部下跌风险仍然存在，不适合强排除大跌。",
        "source_labels": ["high_vol_or_crisis", "volume_expansion", "recent_volatility_expansion"],
    },
    "bullish_momentum_cluster": {
        "source_type": "technical",
        "applies_to_exclusion": "大涨",
        "display_tier": "strong_evidence",
        "title_cn": "技术动量偏强，不支持“否定大涨”",
        "short_cn": "MACD、RSI 或短中期动量偏强，说明上涨延续条件仍在。",
        "display_cn": "技术动量已经转强，说明价格仍具备继续上攻的条件，因此“否定大涨”缺少技术面支持。",
        "source_labels": ["macd_bullish", "positive_momentum", "rsi_bullish"],
    },
    "bullish_trend_structure_cluster": {
        "source_type": "technical",
        "applies_to_exclusion": "大涨",
        "display_tier": "strong_evidence",
        "title_cn": "价格趋势结构偏强，不支持“否定大涨”",
        "short_cn": "价格站上关键均线或已处于高位强势区间，趋势上不适合直接否定大涨。",
        "display_cn": "价格位置和均线结构都偏强，这说明趋势仍在大涨可达区间内，原先否定大涨的技术依据不足。",
        "source_labels": ["trend_above_ma20_ma50", "high_position"],
    },
    "bullish_volume_confirmation": {
        "source_type": "technical",
        "applies_to_exclusion": "大涨",
        "display_tier": "supporting_evidence",
        "title_cn": "量能配合上行，削弱“否定大涨”",
        "short_cn": "上涨伴随量能确认时，大涨并不能轻易被排除。",
        "display_cn": "量能和价格同向配合，说明市场对上行有确认，不适合把大涨直接视为低概率事件。",
        "source_labels": ["volume_confirmation"],
    },
    "bearish_momentum_cluster": {
        "source_type": "technical",
        "applies_to_exclusion": "大跌",
        "display_tier": "strong_evidence",
        "title_cn": "技术动量转弱，不支持“否定大跌”",
        "short_cn": "MACD、RSI 或短中期动量偏弱，说明向下延续条件仍在。",
        "display_cn": "技术动量已经偏空，价格仍有继续走弱的基础，因此“否定大跌”缺少技术面支撑。",
        "source_labels": ["macd_bearish", "negative_momentum", "rsi_bearish"],
    },
    "bearish_trend_structure_cluster": {
        "source_type": "technical",
        "applies_to_exclusion": "大跌",
        "display_tier": "strong_evidence",
        "title_cn": "价格趋势走弱，不支持“否定大跌”",
        "short_cn": "价格落在关键均线下方或处于低位弱势区间，大跌仍需保留。",
        "display_cn": "价格位置和趋势结构都偏弱，说明大跌风险仍处在可触发区间，原先否定大跌的技术依据不足。",
        "source_labels": ["trend_below_ma20_ma50", "low_position"],
    },
    "bearish_volume_stress": {
        "source_type": "technical",
        "applies_to_exclusion": "大跌",
        "display_tier": "supporting_evidence",
        "title_cn": "放量下行压力削弱“否定大跌”",
        "short_cn": "下跌伴随放量时，尾部下跌风险不能被轻易排除。",
        "display_cn": "量能放大同时价格承压，说明卖压真实存在，因此不适合把大跌直接排除。",
        "source_labels": ["volume_stress"],
    },
}

LABEL_TO_TAXONOMY_KEYS: dict[str, list[str]] = {}
for taxonomy_key, entry in TAXONOMY_CATALOG.items():
    for label in entry["source_labels"]:
        LABEL_TO_TAXONOMY_KEYS.setdefault(label, []).append(taxonomy_key)


def resolve_input_paths(
    details_path: Path | None = None,
    summary_path: Path | None = None,
) -> tuple[Path, Path, str]:
    if details_path is not None and summary_path is not None:
        return details_path, summary_path, "explicit"
    if DEFAULT_DETAILS.exists() and DEFAULT_SUMMARY.exists():
        return DEFAULT_DETAILS, DEFAULT_SUMMARY, "task_3a_output"
    raise FileNotFoundError("Task 3C-1 input files not found.")


def load_inputs(details_path: Path, summary_path: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    details = pd.read_csv(details_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    return details, summary


def filter_unsupported_rows(details: pd.DataFrame) -> pd.DataFrame:
    if len(details) != EXPECTED_UNSUPPORTED_TOTAL:
        raise ValueError(
            f"Expected {EXPECTED_UNSUPPORTED_TOTAL} unsupported rows, got {len(details)}"
        )
    return details.reset_index(drop=True)


def _sorted_taxonomy_keys(keys: set[str]) -> list[str]:
    return sorted(
        keys,
        key=lambda item: (
            TIER_SORT_ORDER[TAXONOMY_CATALOG[item]["display_tier"]],
            TAXONOMY_CATALOG[item]["source_type"],
            item,
        ),
    )


def map_labels_to_taxonomy_keys(labels: list[str]) -> list[str]:
    taxonomy_keys: set[str] = set()
    for label in labels:
        for taxonomy_key in LABEL_TO_TAXONOMY_KEYS.get(label, []):
            taxonomy_keys.add(taxonomy_key)
    return _sorted_taxonomy_keys(taxonomy_keys)


def build_row_display_summary(
    *,
    excluded_state: str,
    taxonomy_keys: list[str],
) -> str:
    if excluded_state == "大涨":
        intro = "系统原先否定了“大涨”，但新补全证据不支持这个否定："
    elif excluded_state == "大跌":
        intro = "系统原先否定了“大跌”，但新补全证据不支持这个否定："
    else:
        intro = "系统原先做出了否定，但新补全证据不支持这个否定："

    lines = [
        str(TAXONOMY_CATALOG[key]["short_cn"]).strip().rstrip("。；")
        for key in taxonomy_keys
    ]
    if not lines:
        return intro + " 当前没有可展示的 taxonomy 文案。"
    return intro + " " + "；".join(lines) + "。"


def evaluate_row(row: dict[str, Any]) -> dict[str, Any]:
    raw_labels = task3a._split_listish(row.get("raw_source_labels"))
    technical_labels = task3a._split_listish(row.get("technical_source_labels"))
    taxonomy_keys = map_labels_to_taxonomy_keys(raw_labels + technical_labels)
    tier_keys = [TIER_LABELS_CN[TAXONOMY_CATALOG[key]["display_tier"]] for key in taxonomy_keys]
    explanation_titles = [TAXONOMY_CATALOG[key]["title_cn"] for key in taxonomy_keys]
    explanation_lines = [TAXONOMY_CATALOG[key]["display_cn"] for key in taxonomy_keys]

    strongest_tier = ""
    if taxonomy_keys:
        strongest_tier = TIER_LABELS_CN[TAXONOMY_CATALOG[taxonomy_keys[0]]["display_tier"]]

    return {
        "prediction_date": row.get("prediction_date"),
        "target_date": row.get("target_date"),
        "excluded_state_under_validation": row.get("excluded_state_under_validation"),
        "actual_state": row.get("actual_state"),
        "support_mix": row.get("support_mix"),
        "raw_source_labels": "|".join(raw_labels),
        "technical_source_labels": "|".join(technical_labels),
        "taxonomy_keys": "|".join(taxonomy_keys),
        "taxonomy_title_cn": " | ".join(explanation_titles),
        "taxonomy_tiers_cn": "|".join(tier_keys),
        "strongest_tier_cn": strongest_tier,
        "display_summary_cn": build_row_display_summary(
            excluded_state=str(row.get("excluded_state_under_validation") or ""),
            taxonomy_keys=taxonomy_keys,
        ),
        "display_lines_cn": " | ".join(explanation_lines),
    }


def _counter_from_key_column(frame: pd.DataFrame, column: str) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for raw in frame[column].fillna(""):
        for item in task3a._split_listish(raw):
            counter[item] += 1
    return dict(sorted(counter.items(), key=lambda item: (-item[1], item[0])))


def _build_catalog_summary(evaluated: pd.DataFrame) -> list[dict[str, Any]]:
    taxonomy_counts = _counter_from_key_column(evaluated, "taxonomy_keys")
    catalog_rows: list[dict[str, Any]] = []
    for key, entry in TAXONOMY_CATALOG.items():
        catalog_rows.append(
            {
                "taxonomy_key": key,
                "count": int(taxonomy_counts.get(key, 0)),
                "source_type": entry["source_type"],
                "applies_to_exclusion": entry["applies_to_exclusion"],
                "display_tier": entry["display_tier"],
                "display_tier_cn": TIER_LABELS_CN[entry["display_tier"]],
                "title_cn": entry["title_cn"],
                "short_cn": entry["short_cn"],
                "display_cn": entry["display_cn"],
                "source_labels": entry["source_labels"],
            }
        )
    return sorted(
        catalog_rows,
        key=lambda item: (
            TIER_SORT_ORDER[item["display_tier"]],
            -item["count"],
            item["taxonomy_key"],
        ),
    )


def build_summary(
    evaluated: pd.DataFrame,
    original_summary: dict[str, Any],
) -> dict[str, Any]:
    tier_counts = _counter_from_key_column(evaluated, "taxonomy_tiers_cn")
    summary: dict[str, Any] = {
        "baseline": original_summary.get("baseline") or original_summary.get("overall") or {},
        "unsupported_total": int(len(evaluated)),
        "support_mix_counts": (
            evaluated["support_mix"].value_counts(dropna=False).to_dict()
            if not evaluated.empty
            else {}
        ),
        "taxonomy_counts": _counter_from_key_column(evaluated, "taxonomy_keys"),
        "display_tier_counts": tier_counts,
        "strongest_tier_counts": (
            evaluated["strongest_tier_cn"].value_counts(dropna=False).to_dict()
            if not evaluated.empty
            else {}
        ),
        "catalog": _build_catalog_summary(evaluated),
        "by_state": {},
    }

    for state, subset in evaluated.groupby("excluded_state_under_validation"):
        summary["by_state"][state] = {
            "unsupported_total": int(len(subset)),
            "support_mix_counts": subset["support_mix"].value_counts(dropna=False).to_dict(),
            "taxonomy_counts": _counter_from_key_column(subset, "taxonomy_keys"),
            "display_tier_counts": _counter_from_key_column(subset, "taxonomy_tiers_cn"),
            "strongest_tier_counts": subset["strongest_tier_cn"].value_counts(dropna=False).to_dict(),
        }
    return summary


def build_report_markdown(
    *,
    source: dict[str, Any],
    summary: dict[str, Any],
) -> str:
    lines = [
        "# Task 3C-1 — Unsupported Explanation Taxonomy",
        "",
        "## Sources",
        f"- details: `{source['details_path']}` ({source['input_source']})",
        f"- summary: `{source['summary_path']}` ({source['input_source']})",
        "",
        "## Overview",
        f"- unsupported_total: {summary['unsupported_total']}",
        "",
        "## Display Tier Counts",
    ]
    for key, value in summary["display_tier_counts"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Taxonomy Catalog"])
    for entry in summary["catalog"]:
        lines.append(
            f"- [{entry['display_tier_cn']}] {entry['title_cn']} ({entry['taxonomy_key']}): {entry['count']}"
        )
        lines.append(f"  labels: {', '.join(entry['source_labels'])}")
        lines.append(f"  copy: {entry['display_cn']}")
    return "\n".join(lines) + "\n"


def write_outputs(
    *,
    output_dir: Path,
    evaluated: pd.DataFrame,
    source: dict[str, Any],
    summary: dict[str, Any],
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "unsupported_explanation_taxonomy_details.csv"
    json_path = output_dir / "unsupported_explanation_taxonomy_summary.json"
    md_path = output_dir / "unsupported_explanation_taxonomy_report.md"

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
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    resolved_details, resolved_summary, input_source = resolve_input_paths(
        details_path=details_path,
        summary_path=summary_path,
    )
    details, original_summary = load_inputs(resolved_details, resolved_summary)
    unsupported_rows = filter_unsupported_rows(details)
    evaluated = pd.DataFrame(
        [evaluate_row(record) for record in unsupported_rows.to_dict("records")]
    )
    summary = build_summary(evaluated, original_summary)
    source = {
        "details_path": resolved_details.as_posix(),
        "summary_path": resolved_summary.as_posix(),
        "input_source": input_source,
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
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)

    result = run(
        details_path=args.details_csv,
        summary_path=args.summary_json,
        output_dir=args.output_dir,
    )
    summary = result["summary"]
    print("Task 3C-1 unsupported explanation taxonomy completed")
    print(f"unsupported_total={summary['unsupported_total']}")
    print(f"taxonomy_keys={len(summary['catalog'])}")
    for key, value in summary["display_tier_counts"].items():
        print(f"tier:{key}={value}")
    print(f"csv: {result['output_paths']['csv']}")
    print(f"json: {result['output_paths']['json']}")
    print(f"md: {result['output_paths']['md']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
