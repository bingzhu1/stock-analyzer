#!/usr/bin/env python3
"""Task 3C-5 — shadow backtest exclusion reliability review on 1005 days.

Read-only analysis.

This script does not change prediction rules, UI, forced_exclusion, or any
prediction output field. It only simulates a shadow rule:

    downgrade strong exclusions when exclusion_reliability_review emits
    strongest_tier_cn == "强证据"

Analysis unit:
    exclusion action

If a row excludes both "大涨" and "大跌", it is expanded into two actions.
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


DEFAULT_OUTPUT_DIR = ROOT / "logs/technical_features/exclusion_reliability_shadow_backtest_3c5"
DEFAULT_REPLAY_REVIEW_DETAILS = (
    ROOT / "logs/technical_features/exclusion_reliability_review_batch_3c3/replay_batch_review_details.csv"
)
DEFAULT_FALSE_REVIEW_DETAILS = (
    ROOT / "logs/technical_features/exclusion_reliability_review_batch_3c3/false_exclusion_batch_review_details.csv"
)
DEFAULT_FALSE_VALIDATION_DETAILS = (
    ROOT / "logs/historical_training/exclusion_action_validation_2e_v2/false_exclusion_validation_details.csv"
)
PREFERRED_REPLAY_JSONL = ROOT / "replay_full_prob_rows_with_technical_features.jsonl"
BIG_STATES = {"大涨", "大跌"}


def _split_states(value: Any) -> list[str]:
    return [state for state in task2e_v2._split_states(value) if state in BIG_STATES]


def _make_action_key(frame: pd.DataFrame, excluded_col: str) -> pd.Series:
    return (
        frame["prediction_date"].astype(str)
        + "|"
        + frame["target_date"].astype(str)
        + "|"
        + frame[excluded_col].astype(str)
    )


def resolve_inputs(
    *,
    v4_path: Path | None = None,
    replay_review_details_path: Path | None = None,
    false_validation_details_path: Path | None = None,
    false_review_details_path: Path | None = None,
) -> dict[str, Any]:
    resolved_v4, _, v4_meta = task2e_v2.resolve_inputs(v4_path=v4_path, technical_path=task2e_v2.DEFAULT_SIBLING_TECHNICAL if task2e_v2.DEFAULT_SIBLING_TECHNICAL.exists() else task2e_v2.DEFAULT_MAIN_TECHNICAL)
    replay_review = replay_review_details_path or DEFAULT_REPLAY_REVIEW_DETAILS
    false_validation = false_validation_details_path or DEFAULT_FALSE_VALIDATION_DETAILS
    false_review = false_review_details_path or DEFAULT_FALSE_REVIEW_DETAILS

    missing = [str(path) for path in [replay_review, false_validation, false_review] if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Required 3C-5 inputs missing: {missing}")

    return {
        "preferred_replay_jsonl": str(PREFERRED_REPLAY_JSONL),
        "preferred_replay_jsonl_exists": PREFERRED_REPLAY_JSONL.exists(),
        "v4_path": str(resolved_v4),
        "v4_source": v4_meta["v4_source"],
        "replay_review_details_path": str(replay_review),
        "false_validation_details_path": str(false_validation),
        "false_review_details_path": str(false_review),
    }


def load_replay_rows(v4_path: Path) -> pd.DataFrame:
    return task2e_v2.load_v4_rows(v4_path)


def explode_exclusion_actions(v4_rows: pd.DataFrame) -> pd.DataFrame:
    detail_rows: list[dict[str, Any]] = []
    for row in v4_rows.to_dict("records"):
        excluded_states = _split_states(row.get("forced_excluded_states"))
        for excluded_state in excluded_states:
            detail_rows.append(
                {
                    "prediction_date": row.get("prediction_date"),
                    "target_date": row.get("target_date"),
                    "actual_state": row.get("actual_state"),
                    "predicted_state": row.get("predicted_state"),
                    "forced_excluded_states": row.get("forced_excluded_states"),
                    "excluded_state": excluded_state,
                }
            )
    return pd.DataFrame(detail_rows)


def load_review_details(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    frame = frame.loc[frame["excluded_state_reviewed"].astype(str).isin(BIG_STATES)].copy()
    frame["excluded_state"] = frame["excluded_state_reviewed"].astype(str)
    return frame.reset_index(drop=True)


def load_false_validation_details(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    frame["excluded_state"] = frame["excluded_state_under_validation"].astype(str)
    return frame.reset_index(drop=True)


def verify_inputs(
    *,
    replay_actions: pd.DataFrame,
    replay_review_details: pd.DataFrame,
    false_validation_details: pd.DataFrame,
    false_review_details: pd.DataFrame,
    v4_rows: pd.DataFrame,
) -> dict[str, Any]:
    if len(v4_rows) != 1005:
        raise ValueError(f"Expected 1005 replay rows, got {len(v4_rows)}")

    replay_actions = replay_actions.copy()
    replay_review_details = replay_review_details.copy()
    false_validation_details = false_validation_details.copy()
    false_review_details = false_review_details.copy()

    replay_actions["action_key"] = _make_action_key(replay_actions, "excluded_state")
    replay_review_details["action_key"] = _make_action_key(replay_review_details, "excluded_state")
    false_validation_details["action_key"] = _make_action_key(false_validation_details, "excluded_state")
    false_review_details["action_key"] = _make_action_key(false_review_details, "excluded_state")

    if replay_actions["action_key"].duplicated().any():
        raise ValueError("Replay actions contain duplicate action keys.")
    if replay_review_details["action_key"].duplicated().any():
        raise ValueError("Replay review details contain duplicate action keys.")
    if false_validation_details["action_key"].duplicated().any():
        raise ValueError("False validation details contain duplicate action keys.")
    if false_review_details["action_key"].duplicated().any():
        raise ValueError("False review details contain duplicate action keys.")

    missing_review = sorted(set(replay_actions["action_key"]) - set(replay_review_details["action_key"]))
    extra_review = sorted(set(replay_review_details["action_key"]) - set(replay_actions["action_key"]))
    if missing_review or extra_review:
        raise ValueError(
            "Replay review details do not match exploded replay actions: "
            f"missing={len(missing_review)}, extra={len(extra_review)}"
        )

    false_counts = task2e_v2.verify_expected_false_counts(false_validation_details)
    false_review_big_up = int((false_review_details["excluded_state"] == "大涨").sum())
    false_review_big_down = int((false_review_details["excluded_state"] == "大跌").sum())
    if (
        false_review_big_up != task2e_v2.EXPECTED_FALSE_BIG_UP
        or false_review_big_down != task2e_v2.EXPECTED_FALSE_BIG_DOWN
    ):
        raise ValueError(
            "False review detail counts do not match required baseline: "
            f"false_big_up={false_review_big_up}, false_big_down={false_review_big_down}"
        )

    missing_false_review = sorted(
        set(false_validation_details["action_key"]) - set(false_review_details["action_key"])
    )
    if missing_false_review:
        raise ValueError(
            "False review details are missing baseline false exclusions: "
            f"{len(missing_false_review)} missing"
        )

    return {
        "replay_days": int(len(v4_rows)),
        "replay_rows_with_big_exclusions": int(v4_rows["forced_excluded_states"].map(_split_states).map(bool).sum()),
        "replay_actions_total": int(len(replay_actions)),
        "baseline_false_big_up": int(false_counts["false_big_up"]),
        "baseline_false_big_down": int(false_counts["false_big_down"]),
        "baseline_false_total": int(false_counts["false_total"]),
    }


def build_shadow_backtest_details(
    replay_actions: pd.DataFrame,
    replay_review_details: pd.DataFrame,
) -> pd.DataFrame:
    base = replay_actions.merge(
        replay_review_details[
            [
                "prediction_date",
                "target_date",
                "excluded_state",
                "has_reliability_concern",
                "unsupported_by_raw_enriched",
                "unsupported_by_technical_features",
                "support_mix",
                "raw_source_labels",
                "technical_source_labels",
                "taxonomy_keys",
                "strongest_tier_cn",
                "display_summary_cn",
            ]
        ],
        on=["prediction_date", "target_date", "excluded_state"],
        how="left",
    )
    base["is_false_exclusion"] = base["excluded_state"] == base["actual_state"]
    base["is_correct_exclusion"] = ~base["is_false_exclusion"]
    base["has_reliability_concern"] = base["has_reliability_concern"].fillna(False).astype(bool)
    base["unsupported_by_raw_enriched"] = base["unsupported_by_raw_enriched"].fillna(False).astype(bool)
    base["unsupported_by_technical_features"] = base["unsupported_by_technical_features"].fillna(False).astype(bool)
    base["shadow_downgrade_triggered"] = base["strongest_tier_cn"].fillna("") == "强证据"
    base["shadow_outcome"] = "kept"
    base.loc[
        base["shadow_downgrade_triggered"] & base["is_false_exclusion"],
        "shadow_outcome",
    ] = "rescued_false_exclusion"
    base.loc[
        base["shadow_downgrade_triggered"] & base["is_correct_exclusion"],
        "shadow_outcome",
    ] = "hurt_correct_exclusion"
    return base


def _state_summary(frame: pd.DataFrame) -> dict[str, Any]:
    total_actions = int(len(frame))
    false_total = int(frame["is_false_exclusion"].sum())
    correct_total = int(frame["is_correct_exclusion"].sum())
    triggered = frame.loc[frame["shadow_downgrade_triggered"]].copy()
    rescued_false = int((triggered["is_false_exclusion"]).sum())
    hurt_correct = int((triggered["is_correct_exclusion"]).sum())
    kept_false = false_total - rescued_false
    kept_correct = correct_total - hurt_correct
    return {
        "actions_total": total_actions,
        "false_exclusions_total": false_total,
        "correct_exclusions_total": correct_total,
        "shadow_downgrade_triggered": int(len(triggered)),
        "rescued_false_exclusions": rescued_false,
        "hurt_correct_exclusions": hurt_correct,
        "remaining_false_exclusions_after_shadow": kept_false,
        "remaining_correct_exclusions_after_shadow": kept_correct,
        "false_rescue_rate": round((rescued_false / false_total) * 100, 2) if false_total else 0.0,
        "correct_hurt_rate": round((hurt_correct / correct_total) * 100, 2) if correct_total else 0.0,
        "flagged_false_precision": round((rescued_false / len(triggered)) * 100, 2) if len(triggered) else 0.0,
    }


def summarize_shadow_backtest(
    details: pd.DataFrame,
    *,
    source_info: dict[str, Any],
    verification: dict[str, Any],
) -> dict[str, Any]:
    overall = _state_summary(details)
    by_state = {
        state: _state_summary(subset.copy())
        for state, subset in details.groupby("excluded_state")
    }
    strongest_tier_counts = details["strongest_tier_cn"].fillna("无").value_counts().to_dict()
    support_mix_counts = details["support_mix"].fillna("supported").value_counts().to_dict()

    return {
        "task": "3C-5",
        "shadow_rule": {
            "name": "downgrade_strong_exclusion_when_review_has_strong_evidence",
            "trigger_definition": 'strongest_tier_cn == "强证据"',
            "prediction_fields_changed": False,
        },
        "source_info": source_info,
        "verification": verification,
        "overall": overall,
        "by_excluded_state": by_state,
        "strongest_tier_counts": strongest_tier_counts,
        "support_mix_counts": support_mix_counts,
    }


def build_report_markdown(summary: dict[str, Any]) -> str:
    source = summary["source_info"]
    verification = summary["verification"]
    overall = summary["overall"]
    by_state = summary["by_excluded_state"]
    lines = [
        "# Task 3C-5 — Exclusion Reliability Review Shadow Backtest",
        "",
        "## Actual Paths Used",
        f"- preferred replay_with_technical_features jsonl: `{source['preferred_replay_jsonl']}` (exists={source['preferred_replay_jsonl_exists']})",
        f"- replay base rows: `{source['v4_path']}` ({source['v4_source']})",
        f"- replay review details: `{source['replay_review_details_path']}`",
        f"- false exclusion baseline: `{source['false_validation_details_path']}`",
        f"- false exclusion review details: `{source['false_review_details_path']}`",
        "",
        "## Shadow Rule",
        "- action unit: exclusion action",
        '- trigger: `strongest_tier_cn == "强证据"`',
        "- prediction / forced_exclusion fields remain unchanged",
        "",
        "## Replay Coverage",
        f"- replay_days: {verification['replay_days']}",
        f"- replay_rows_with_big_exclusions: {verification['replay_rows_with_big_exclusions']}",
        f"- replay_actions_total: {verification['replay_actions_total']}",
        f"- baseline_false_big_up: {verification['baseline_false_big_up']}",
        f"- baseline_false_big_down: {verification['baseline_false_big_down']}",
        f"- baseline_false_total: {verification['baseline_false_total']}",
        "",
        "## Overall",
        f"- false_exclusions_total: {overall['false_exclusions_total']}",
        f"- correct_exclusions_total: {overall['correct_exclusions_total']}",
        f"- shadow_downgrade_triggered: {overall['shadow_downgrade_triggered']}",
        f"- rescued_false_exclusions: {overall['rescued_false_exclusions']}",
        f"- hurt_correct_exclusions: {overall['hurt_correct_exclusions']}",
        f"- false_rescue_rate: {overall['false_rescue_rate']}%",
        f"- correct_hurt_rate: {overall['correct_hurt_rate']}%",
        f"- flagged_false_precision: {overall['flagged_false_precision']}%",
        "",
        "## By Excluded State",
        f"- 大涨: rescued_false={by_state['大涨']['rescued_false_exclusions']}, hurt_correct={by_state['大涨']['hurt_correct_exclusions']}, false_rescue_rate={by_state['大涨']['false_rescue_rate']}%, correct_hurt_rate={by_state['大涨']['correct_hurt_rate']}%",
        f"- 大跌: rescued_false={by_state['大跌']['rescued_false_exclusions']}, hurt_correct={by_state['大跌']['hurt_correct_exclusions']}, false_rescue_rate={by_state['大跌']['false_rescue_rate']}%, correct_hurt_rate={by_state['大跌']['correct_hurt_rate']}%",
        "",
    ]
    return "\n".join(lines)


def write_outputs(
    *,
    output_dir: Path,
    details: pd.DataFrame,
    summary: dict[str, Any],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    details.to_csv(output_dir / "shadow_backtest_action_details.csv", index=False)
    with (output_dir / "shadow_backtest_summary.json").open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)
    (output_dir / "shadow_backtest_report.md").write_text(
        build_report_markdown(summary),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v4-path", type=Path, default=None)
    parser.add_argument("--replay-review-details-path", type=Path, default=None)
    parser.add_argument("--false-validation-details-path", type=Path, default=None)
    parser.add_argument("--false-review-details-path", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_info = resolve_inputs(
        v4_path=args.v4_path,
        replay_review_details_path=args.replay_review_details_path,
        false_validation_details_path=args.false_validation_details_path,
        false_review_details_path=args.false_review_details_path,
    )
    v4_rows = load_replay_rows(Path(source_info["v4_path"]))
    replay_actions = explode_exclusion_actions(v4_rows)
    replay_review_details = load_review_details(Path(source_info["replay_review_details_path"]))
    false_validation_details = load_false_validation_details(
        Path(source_info["false_validation_details_path"])
    )
    false_review_details = load_review_details(Path(source_info["false_review_details_path"]))
    verification = verify_inputs(
        replay_actions=replay_actions,
        replay_review_details=replay_review_details,
        false_validation_details=false_validation_details,
        false_review_details=false_review_details,
        v4_rows=v4_rows,
    )
    details = build_shadow_backtest_details(replay_actions, replay_review_details)
    summary = summarize_shadow_backtest(
        details,
        source_info=source_info,
        verification=verification,
    )
    write_outputs(
        output_dir=args.output_dir,
        details=details,
        summary=summary,
    )


if __name__ == "__main__":
    main()
