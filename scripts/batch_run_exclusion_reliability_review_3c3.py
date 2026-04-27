#!/usr/bin/env python3
"""Task 3C-3 — batch-run exclusion reliability review on replay rows.

Read-only validation.

This script does not change prediction rules, UI, warnings, thresholds, or
forced_exclusion logic. It only batch-runs
`build_exclusion_reliability_review(row)` on:

1. Real v4 replay rows that exclude "大涨" or "大跌"
2. The 165 false-exclusion rows from Task 2E-v2

The goal is to validate:
- payload stability
- batch coverage completeness
- no mutation of protected prediction fields
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import validate_false_exclusions_2e_v2 as task2e_v2
from services.exclusion_reliability_review import build_exclusion_reliability_review


DEFAULT_OUTPUT_DIR = (
    ROOT / "logs/technical_features/exclusion_reliability_review_batch_3c3"
)
PROTECTED_FIELDS = [
    "predicted_state",
    "forced_excluded_states",
    "p_大涨",
    "p_大跌",
    "p_震荡",
    "p_小涨",
    "p_小跌",
]
REQUIRED_REVIEW_KEYS = [
    "title",
    "has_exclusion_review",
    "review_items",
    "excluded_states_reviewed",
    "summary_cn",
]
REQUIRED_ITEM_KEYS = [
    "excluded_state",
    "has_exclusion",
    "has_reliability_concern",
    "support_mix",
    "taxonomy_keys",
    "strongest_tier_cn",
    "display_summary_cn",
]


def _extract_protected_snapshot(row: dict[str, Any]) -> dict[str, Any]:
    return {field: row.get(field) for field in PROTECTED_FIELDS if field in row}


def _protected_fields_unchanged(before: dict[str, Any], after: dict[str, Any]) -> bool:
    return before == after


def _validate_payload_shape(payload: dict[str, Any]) -> tuple[bool, list[str]]:
    missing = [key for key in REQUIRED_REVIEW_KEYS if key not in payload]
    for item in payload.get("review_items") or []:
        for key in REQUIRED_ITEM_KEYS:
            if key not in item:
                missing.append(f"review_item.{key}")
    return not missing, missing


def _filter_replay_rows(v4_rows: pd.DataFrame) -> pd.DataFrame:
    mask = (
        v4_rows["forced_excluded_states"]
        .fillna("")
        .astype(str)
        .str.contains("大涨|大跌")
    )
    return v4_rows.loc[mask].copy().reset_index(drop=True)


def _join_technical(frame: pd.DataFrame, technical_rows: pd.DataFrame) -> pd.DataFrame:
    return frame.merge(
        technical_rows,
        left_on="prediction_date",
        right_on="Date",
        how="left",
        suffixes=("", "__tech"),
    )


def _flatten_review_payload(
    *,
    scope: str,
    row: dict[str, Any],
    payload: dict[str, Any],
    protected_fields_unchanged: bool,
    payload_shape_ok: bool,
    payload_shape_missing: list[str],
) -> list[dict[str, Any]]:
    base = {
        "scope": scope,
        "prediction_date": row.get("prediction_date"),
        "target_date": row.get("target_date"),
        "actual_state": row.get("actual_state"),
        "forced_excluded_states": row.get("forced_excluded_states"),
        "payload_has_exclusion_review": bool(payload.get("has_exclusion_review")),
        "payload_has_reliability_concern": bool(payload.get("has_reliability_concern")),
        "excluded_states_reviewed": "|".join(payload.get("excluded_states_reviewed") or []),
        "summary_cn": payload.get("summary_cn") or "",
        "protected_fields_unchanged": protected_fields_unchanged,
        "payload_shape_ok": payload_shape_ok,
        "payload_shape_missing": "|".join(payload_shape_missing),
    }
    rows: list[dict[str, Any]] = []
    for item in payload.get("review_items") or []:
        rows.append(
            {
                **base,
                "excluded_state_reviewed": item.get("excluded_state"),
                "has_exclusion": bool(item.get("has_exclusion")),
                "has_reliability_concern": bool(item.get("has_reliability_concern")),
                "unsupported_by_raw_enriched": bool(item.get("unsupported_by_raw_enriched")),
                "unsupported_by_technical_features": bool(item.get("unsupported_by_technical_features")),
                "support_mix": item.get("support_mix") or "",
                "raw_source_labels": "|".join(item.get("raw_source_labels") or []),
                "technical_source_labels": "|".join(item.get("technical_source_labels") or []),
                "taxonomy_keys": "|".join(item.get("taxonomy_keys") or []),
                "strongest_tier_cn": item.get("strongest_tier_cn") or "",
                "unmapped_source_labels": "|".join(item.get("unmapped_source_labels") or []),
                "display_summary_cn": item.get("display_summary_cn") or "",
            }
        )
    if rows:
        return rows
    return [
        {
            **base,
            "excluded_state_reviewed": "",
            "has_exclusion": False,
            "has_reliability_concern": False,
            "unsupported_by_raw_enriched": False,
            "unsupported_by_technical_features": False,
            "support_mix": "",
            "raw_source_labels": "",
            "technical_source_labels": "",
            "taxonomy_keys": "",
            "strongest_tier_cn": "",
            "unmapped_source_labels": "",
            "display_summary_cn": "",
        }
    ]


def _run_batch(scope: str, frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    detail_rows: list[dict[str, Any]] = []
    rows_with_reliability_concern = 0
    protected_field_changes = 0
    payload_shape_failures = 0

    for record in frame.to_dict("records"):
        before = _extract_protected_snapshot(record)
        payload = build_exclusion_reliability_review(record)
        after = _extract_protected_snapshot(record)
        protected_ok = _protected_fields_unchanged(before, after)
        if not protected_ok:
            protected_field_changes += 1
        payload_ok, payload_missing = _validate_payload_shape(payload)
        if not payload_ok:
            payload_shape_failures += 1
        if payload.get("has_reliability_concern"):
            rows_with_reliability_concern += 1
        detail_rows.extend(
            _flatten_review_payload(
                scope=scope,
                row=record,
                payload=payload,
                protected_fields_unchanged=protected_ok,
                payload_shape_ok=payload_ok,
                payload_shape_missing=payload_missing,
            )
        )

    details = pd.DataFrame(detail_rows)
    review_items = details.loc[details["excluded_state_reviewed"].astype(str) != ""].copy()
    summary = {
        "scope": scope,
        "input_rows": int(len(frame)),
        "detail_rows": int(len(details)),
        "review_item_rows": int(len(review_items)),
        "rows_with_reliability_concern": int(rows_with_reliability_concern),
        "review_items_with_reliability_concern": int(review_items["has_reliability_concern"].sum())
        if not review_items.empty else 0,
        "payload_has_exclusion_review_rows": int(details["payload_has_exclusion_review"].sum()),
        "protected_field_changes": int(protected_field_changes),
        "payload_shape_failures": int(payload_shape_failures),
        "strongest_tier_counts": (
            review_items["strongest_tier_cn"].value_counts(dropna=False).to_dict()
            if not review_items.empty else {}
        ),
        "support_mix_counts": (
            review_items["support_mix"].value_counts(dropna=False).to_dict()
            if not review_items.empty else {}
        ),
        "by_state": {},
    }
    if not review_items.empty:
        for state, subset in review_items.groupby("excluded_state_reviewed"):
            summary["by_state"][state] = {
                "review_item_rows": int(len(subset)),
                "reliability_concern_rows": int(subset["has_reliability_concern"].sum()),
                "support_mix_counts": subset["support_mix"].value_counts(dropna=False).to_dict(),
                "strongest_tier_counts": subset["strongest_tier_cn"].value_counts(dropna=False).to_dict(),
            }
    return details, summary


def build_report_markdown(*, source: dict[str, Any], replay_summary: dict[str, Any], false_summary: dict[str, Any]) -> str:
    lines = [
        "# Task 3C-3 — Exclusion Reliability Review Batch Validation",
        "",
        "## Sources",
        f"- v4 replay: `{source['v4_path']}` ({source['v4_source']})",
        f"- technical features: `{source['technical_path']}` ({source['technical_source']})",
        "",
        "## Replay Batch",
        f"- input_rows: {replay_summary['input_rows']}",
        f"- review_item_rows: {replay_summary['review_item_rows']}",
        f"- rows_with_reliability_concern: {replay_summary['rows_with_reliability_concern']}",
        f"- protected_field_changes: {replay_summary['protected_field_changes']}",
        f"- payload_shape_failures: {replay_summary['payload_shape_failures']}",
        "",
        "## False Exclusion Batch",
        f"- input_rows: {false_summary['input_rows']}",
        f"- review_item_rows: {false_summary['review_item_rows']}",
        f"- review_items_with_reliability_concern: {false_summary['review_items_with_reliability_concern']}",
        f"- protected_field_changes: {false_summary['protected_field_changes']}",
        f"- payload_shape_failures: {false_summary['payload_shape_failures']}",
    ]
    return "\n".join(lines) + "\n"


def write_outputs(
    *,
    output_dir: Path,
    replay_details: pd.DataFrame,
    false_details: pd.DataFrame,
    source: dict[str, Any],
    replay_summary: dict[str, Any],
    false_summary: dict[str, Any],
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    replay_csv = output_dir / "replay_batch_review_details.csv"
    false_csv = output_dir / "false_exclusion_batch_review_details.csv"
    json_path = output_dir / "batch_review_summary.json"
    md_path = output_dir / "batch_review_report.md"

    replay_details.to_csv(replay_csv, index=False)
    false_details.to_csv(false_csv, index=False)
    json_path.write_text(
        json.dumps(
            {
                "source": source,
                "replay_batch": replay_summary,
                "false_exclusion_batch": false_summary,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    md_path.write_text(
        build_report_markdown(
            source=source,
            replay_summary=replay_summary,
            false_summary=false_summary,
        ),
        encoding="utf-8",
    )
    return {
        "replay_csv": replay_csv.as_posix(),
        "false_csv": false_csv.as_posix(),
        "json": json_path.as_posix(),
        "md": md_path.as_posix(),
    }


def run(
    *,
    v4_path: Path | None = None,
    technical_path: Path | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    resolved_v4, resolved_technical, source_notes = task2e_v2.resolve_inputs(
        v4_path=v4_path,
        technical_path=technical_path,
    )
    v4_rows = task2e_v2.load_v4_rows(resolved_v4)
    technical_rows = task2e_v2.load_technical_rows(resolved_technical)
    replay_rows = _join_technical(_filter_replay_rows(v4_rows), technical_rows)

    false_rows = task2e_v2.extract_false_exclusion_rows(v4_rows)
    baseline = task2e_v2.verify_expected_false_counts(false_rows)
    false_rows = _join_technical(false_rows, technical_rows)

    replay_details, replay_summary = _run_batch("replay_rows", replay_rows)
    false_details, false_summary = _run_batch("false_exclusion_rows", false_rows)

    expected_false_concerns = 111
    observed_false_concerns = int(false_summary["review_items_with_reliability_concern"])
    if observed_false_concerns != expected_false_concerns:
        raise ValueError(
            f"false_exclusion_batch concern count mismatch: {observed_false_concerns} != {expected_false_concerns}"
        )

    source = {
        "v4_path": resolved_v4.as_posix(),
        "technical_path": resolved_technical.as_posix(),
        **source_notes,
    }
    false_summary["baseline"] = baseline
    output_paths = write_outputs(
        output_dir=output_dir,
        replay_details=replay_details,
        false_details=false_details,
        source=source,
        replay_summary=replay_summary,
        false_summary=false_summary,
    )
    return {
        "source": source,
        "replay_batch": replay_summary,
        "false_exclusion_batch": false_summary,
        "replay_details": replay_details,
        "false_details": false_details,
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
    replay_summary = result["replay_batch"]
    false_summary = result["false_exclusion_batch"]
    print("Task 3C-3 exclusion reliability review batch completed")
    print(f"replay_rows={replay_summary['input_rows']}")
    print(f"replay_rows_with_reliability_concern={replay_summary['rows_with_reliability_concern']}")
    print(f"false_rows={false_summary['input_rows']}")
    print(f"false_review_items_with_reliability_concern={false_summary['review_items_with_reliability_concern']}")
    print(f"replay_csv: {result['output_paths']['replay_csv']}")
    print(f"false_csv: {result['output_paths']['false_csv']}")
    print(f"json: {result['output_paths']['json']}")
    print(f"md: {result['output_paths']['md']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
