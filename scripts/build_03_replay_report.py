"""scripts/build_03_replay_report.py

Build the formal "03" replay accuracy and exclusion-accuracy record from the
B-path original-system replay outputs (predictions.csv + reviews.csv).

Inputs (from --replay-dir):
    predictions.csv  — per-day prediction with forced_state_probabilities and
                       forced_excluded_states columns
    reviews.csv      — per-day review with actual_state and excluded_states

Outputs (written into --replay-dir):
    03_replay_accuracy_summary.json
    03_replay_accuracy_report.md
    03_prediction_details.csv
    03_exclusion_action_details.csv
    03_false_exclusion_details.csv
    03_confusion_matrix.csv

Plus the canonical record copied to --record-path:
    records/03_replay_accuracy_and_exclusion_accuracy.md

Hard-rule scope: this script reads only B-path CSVs. It never imports
projection_v2, rule_scoring, active_rule_pool, AVGO_technical_features,
exclusion_reliability_review, contradiction-card payloads, shadow-backtest, or
3C review payloads.
"""
from __future__ import annotations

import argparse
import ast
import json
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

ALL_STATES: tuple[str, ...] = ("大涨", "小涨", "震荡", "小跌", "大跌")


def _parse_dict(value: Any) -> dict[str, float]:
    if isinstance(value, dict):
        return {str(k): float(v) for k, v in value.items()}
    text = str(value or "").strip()
    if not text:
        return {}
    try:
        parsed = ast.literal_eval(text)
    except (SyntaxError, ValueError):
        return {}
    if not isinstance(parsed, dict):
        return {}
    return {str(k): float(v) for k, v in parsed.items()}


def _parse_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    text = str(value or "").strip()
    if not text:
        return []
    try:
        parsed = ast.literal_eval(text)
    except (SyntaxError, ValueError):
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed]


def _safe_div(num: float, den: float) -> float | None:
    return None if not den else num / den


def _fmt_pct(value: float | None) -> str:
    return "N/A" if value is None else f"{value * 100:.2f}%"


def build_join(replay_dir: Path) -> pd.DataFrame:
    pred = pd.read_csv(replay_dir / "predictions.csv")
    rev = pd.read_csv(replay_dir / "reviews.csv")

    pred_lookup = pred.set_index("pred_01_date")
    needed_cols = {"forced_predicted_state", "forced_state_probabilities", "forced_excluded_states"}
    missing = needed_cols - set(pred.columns)
    if missing:
        raise SystemExit(
            f"predictions.csv missing required columns: {sorted(missing)}; "
            "this script requires the current B-path script output (with forced_* fields). "
            "Re-run scripts/run_historical_training.py to regenerate."
        )

    rev = rev.copy()
    rev["predicted_state"] = rev["prediction_date"].map(pred_lookup["forced_predicted_state"])
    rev["state_probabilities_raw"] = rev["prediction_date"].map(pred_lookup["forced_state_probabilities"])
    rev["excluded_states_pred"] = rev["prediction_date"].map(pred_lookup["forced_excluded_states"])

    rev["state_probabilities"] = rev["state_probabilities_raw"].apply(_parse_dict)
    rev["excluded_states_list"] = rev["excluded_states"].apply(_parse_list)
    if rev["excluded_states_list"].apply(len).sum() == 0:
        # Fallback: use the prediction-side list (should match in normal case).
        rev["excluded_states_list"] = rev["excluded_states_pred"].apply(_parse_list)
    return rev


def write_prediction_details(joined: pd.DataFrame, out_path: Path) -> None:
    rows = []
    for _, row in joined.iterrows():
        probs = row["state_probabilities"]
        rows.append({
            "prediction_date": row["prediction_date"],
            "actual_date": row["actual_date"],
            "predicted_state": row["predicted_state"],
            "actual_state": row["actual_state"],
            "correct": bool(row["predicted_state"] == row["actual_state"]),
            **{f"p_{state}": probs.get(state) for state in ALL_STATES},
        })
    pd.DataFrame(rows).to_csv(out_path, index=False)


def write_exclusion_action_details(joined: pd.DataFrame, out_path: Path) -> tuple[Path, list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    for _, row in joined.iterrows():
        probs = row["state_probabilities"]
        actual = row["actual_state"]
        for excluded in row["excluded_states_list"]:
            rows.append({
                "prediction_date": row["prediction_date"],
                "actual_date": row["actual_date"],
                "excluded_state": excluded,
                "p_excluded_state": probs.get(excluded),
                "actual_state": actual,
                "predicted_state": row["predicted_state"],
                "correct": bool(excluded != actual),
            })
    pd.DataFrame(rows).to_csv(out_path, index=False)
    return out_path, rows


def write_false_exclusion_details(action_rows: list[dict[str, Any]], joined: pd.DataFrame, out_path: Path) -> list[dict[str, Any]]:
    prob_lookup = joined.set_index("prediction_date")["state_probabilities"].to_dict()
    rows = []
    for r in action_rows:
        if r["correct"]:
            continue
        probs = prob_lookup.get(r["prediction_date"], {})
        rows.append({
            "prediction_date": r["prediction_date"],
            "actual_date": r["actual_date"],
            "excluded_state": r["excluded_state"],
            "p_excluded_state": r["p_excluded_state"],
            "actual_state": r["actual_state"],
            "predicted_state": r["predicted_state"],
            "p_actual_state": probs.get(r["actual_state"]),
        })
    pd.DataFrame(rows).to_csv(out_path, index=False)
    return rows


def build_confusion_matrix(joined: pd.DataFrame) -> pd.DataFrame:
    matrix = pd.DataFrame(0, index=list(ALL_STATES), columns=list(ALL_STATES))
    matrix.index.name = "predicted_state \\ actual_state"
    for _, row in joined.iterrows():
        pred = row["predicted_state"]
        actual = row["actual_state"]
        if pred in matrix.index and actual in matrix.columns:
            matrix.loc[pred, actual] += 1
    matrix["total_predicted"] = matrix.sum(axis=1)
    actual_totals = matrix.iloc[:, :5].sum(axis=0)
    actual_totals["total_predicted"] = actual_totals.sum()
    matrix.loc["total_actual"] = actual_totals
    return matrix


def compute_summary(joined: pd.DataFrame, action_rows: list[dict[str, Any]], false_rows: list[dict[str, Any]]) -> dict[str, Any]:
    total_days = int(len(joined))
    overall_correct = int((joined["predicted_state"] == joined["actual_state"]).sum())
    overall_acc = _safe_div(overall_correct, total_days)

    pred_dist = Counter(joined["predicted_state"])
    actual_dist = Counter(joined["actual_state"])

    cm = build_confusion_matrix(joined)
    recall_by_actual: dict[str, dict[str, Any]] = {}
    precision_by_predicted: dict[str, dict[str, Any]] = {}
    for state in ALL_STATES:
        true_pos = int(cm.loc[state, state]) if state in cm.index else 0
        actual_total = int(actual_dist.get(state, 0))
        pred_total = int(pred_dist.get(state, 0))
        recall_by_actual[state] = {
            "true_positive": true_pos,
            "actual_total": actual_total,
            "recall": _safe_div(true_pos, actual_total),
        }
        precision_by_predicted[state] = {
            "true_positive": true_pos,
            "predicted_total": pred_total,
            "precision": _safe_div(true_pos, pred_total),
        }

    total_actions = len(action_rows)
    correct_actions = sum(1 for r in action_rows if r["correct"])
    false_actions = total_actions - correct_actions
    exclusion_acc = _safe_div(correct_actions, total_actions)
    false_rate = _safe_div(false_actions, total_actions)

    by_excluded: dict[str, dict[str, Any]] = {}
    for state in ALL_STATES:
        rows = [r for r in action_rows if r["excluded_state"] == state]
        total = len(rows)
        correct = sum(1 for r in rows if r["correct"])
        wrong = total - correct
        by_excluded[state] = {
            "total_actions": total,
            "correct_actions": correct,
            "false_actions": wrong,
            "accuracy": _safe_div(correct, total),
        }

    p_excluded_dist: dict[str, float] = {}
    if false_rows:
        p_values = [r["p_excluded_state"] for r in false_rows if r["p_excluded_state"] is not None]
        if p_values:
            series = pd.Series(p_values)
            p_excluded_dist = {
                "n": int(series.size),
                "min": float(series.min()),
                "p25": float(series.quantile(0.25)),
                "median": float(series.median()),
                "mean": float(series.mean()),
                "p75": float(series.quantile(0.75)),
                "max": float(series.max()),
            }

    p_excluded_by_state: dict[str, dict[str, Any]] = {}
    for state in ALL_STATES:
        state_rows = [r for r in false_rows if r["excluded_state"] == state and r["p_excluded_state"] is not None]
        if not state_rows:
            p_excluded_by_state[state] = {"n": 0}
            continue
        series = pd.Series([r["p_excluded_state"] for r in state_rows])
        p_excluded_by_state[state] = {
            "n": int(series.size),
            "min": float(series.min()),
            "median": float(series.median()),
            "mean": float(series.mean()),
            "max": float(series.max()),
        }

    date_range = {
        "start_prediction_date": str(joined["prediction_date"].iloc[0]),
        "end_prediction_date": str(joined["prediction_date"].iloc[-1]),
        "start_actual_date": str(joined["actual_date"].iloc[0]),
        "end_actual_date": str(joined["actual_date"].iloc[-1]),
    }

    return {
        "kind": "03_replay_accuracy_summary",
        "source": "B-path scripts/run_historical_training.py — original main pipeline",
        "scope_excluded": [
            "projection_v2", "rule_scoring", "rule_lifecycle", "active_rule_pool",
            "AVGO_technical_features", "exclusion_reliability_review",
            "contradiction_card", "shadow_backtest", "3C review payloads",
            "yfinance live calls",
        ],
        "total_days": total_days,
        "is_exactly_1005": total_days == 1005,
        "date_range": date_range,
        "five_state_overall_accuracy": {
            "correct": overall_correct,
            "total": total_days,
            "accuracy": overall_acc,
        },
        "predicted_state_distribution": dict(pred_dist),
        "actual_state_distribution": dict(actual_dist),
        "confusion_matrix": {
            pred: {actual: int(cm.loc[pred, actual]) for actual in ALL_STATES}
            for pred in ALL_STATES
        },
        "recall_by_actual_state": recall_by_actual,
        "precision_by_predicted_state": precision_by_predicted,
        "exclusion_action_totals": {
            "total_exclusion_actions": total_actions,
            "correct_exclusion_actions": correct_actions,
            "false_exclusion_actions": false_actions,
            "exclusion_accuracy": exclusion_acc,
            "false_exclusion_rate": false_rate,
        },
        "exclusion_accuracy_by_excluded_state": by_excluded,
        "false_exclusion_p_excluded_distribution_overall": p_excluded_dist,
        "false_exclusion_p_excluded_distribution_by_state": p_excluded_by_state,
    }


def render_report_md(summary: dict[str, Any], *, title: str, intro_lines: list[str]) -> str:
    lines: list[str] = [f"# {title}", ""]
    lines += intro_lines
    if intro_lines:
        lines.append("")

    lines += [
        "## Replay scope",
        "",
        f"- Source pipeline: `{summary['source']}`",
        f"- Total days: **{summary['total_days']}** (target 1005 → match: **{'yes' if summary['is_exactly_1005'] else 'no'}**)",
        f"- Date range: {summary['date_range']['start_prediction_date']} (pred) → "
        f"{summary['date_range']['end_actual_date']} (actual)",
        "- Modules confirmed NOT used: " + ", ".join(f"`{m}`" for m in summary["scope_excluded"]),
        "",
        "## Five-state prediction accuracy (overall)",
        "",
        f"- Correct: {summary['five_state_overall_accuracy']['correct']} / {summary['five_state_overall_accuracy']['total']}",
        f"- Accuracy: **{_fmt_pct(summary['five_state_overall_accuracy']['accuracy'])}**",
        "",
        "## Predicted state distribution",
        "",
        "| state | count | share |",
        "|-------|------:|------:|",
    ]
    total_days = summary["total_days"] or 1
    for state in ALL_STATES:
        count = summary["predicted_state_distribution"].get(state, 0)
        lines.append(f"| {state} | {count} | {_fmt_pct(count / total_days)} |")
    lines += [
        "",
        "## Actual state distribution",
        "",
        "| state | count | share |",
        "|-------|------:|------:|",
    ]
    for state in ALL_STATES:
        count = summary["actual_state_distribution"].get(state, 0)
        lines.append(f"| {state} | {count} | {_fmt_pct(count / total_days)} |")

    lines += [
        "",
        "## Five-state confusion matrix (rows=predicted, cols=actual)",
        "",
        "| predicted \\ actual | " + " | ".join(ALL_STATES) + " | total_predicted |",
        "|---|" + "|".join(["---:"] * (len(ALL_STATES) + 1)) + "|",
    ]
    cm = summary["confusion_matrix"]
    for pred in ALL_STATES:
        row = cm[pred]
        total_pred = sum(row.values())
        lines.append(
            "| " + pred + " | " + " | ".join(str(row[a]) for a in ALL_STATES) + f" | {total_pred} |"
        )
    actual_totals_row = [sum(cm[p][a] for p in ALL_STATES) for a in ALL_STATES]
    lines.append(
        "| **total_actual** | " + " | ".join(str(v) for v in actual_totals_row)
        + f" | **{sum(actual_totals_row)}** |"
    )

    lines += [
        "",
        "## Recall by actual state",
        "",
        "| actual_state | true_positive | actual_total | recall |",
        "|---|---:|---:|---:|",
    ]
    for state in ALL_STATES:
        info = summary["recall_by_actual_state"][state]
        lines.append(
            f"| {state} | {info['true_positive']} | {info['actual_total']} | {_fmt_pct(info['recall'])} |"
        )

    lines += [
        "",
        "## Precision by predicted state",
        "",
        "| predicted_state | true_positive | predicted_total | precision |",
        "|---|---:|---:|---:|",
    ]
    for state in ALL_STATES:
        info = summary["precision_by_predicted_state"][state]
        lines.append(
            f"| {state} | {info['true_positive']} | {info['predicted_total']} | {_fmt_pct(info['precision'])} |"
        )

    et = summary["exclusion_action_totals"]
    lines += [
        "",
        "## Exclusion (negation) totals",
        "",
        f"- total_exclusion_actions: **{et['total_exclusion_actions']}**",
        f"- correct_exclusion_actions: **{et['correct_exclusion_actions']}**",
        f"- false_exclusion_actions: **{et['false_exclusion_actions']}**",
        f"- exclusion_accuracy: **{_fmt_pct(et['exclusion_accuracy'])}**",
        f"- false_exclusion_rate: **{_fmt_pct(et['false_exclusion_rate'])}**",
        "",
        "## Exclusion accuracy by excluded_state",
        "",
        "| excluded_state | total_actions | correct | false | accuracy |",
        "|---|---:|---:|---:|---:|",
    ]
    for state in ALL_STATES:
        info = summary["exclusion_accuracy_by_excluded_state"][state]
        lines.append(
            f"| {state} | {info['total_actions']} | {info['correct_actions']} | "
            f"{info['false_actions']} | {_fmt_pct(info['accuracy'])} |"
        )

    p_overall = summary["false_exclusion_p_excluded_distribution_overall"]
    if p_overall:
        lines += [
            "",
            "## p_excluded_state distribution on FALSE exclusions (overall)",
            "",
            f"- n = {p_overall['n']}",
            f"- min / p25 / median / mean / p75 / max = "
            f"{p_overall['min']:.4f} / {p_overall['p25']:.4f} / {p_overall['median']:.4f} / "
            f"{p_overall['mean']:.4f} / {p_overall['p75']:.4f} / {p_overall['max']:.4f}",
        ]
    else:
        lines += [
            "",
            "## p_excluded_state distribution on FALSE exclusions (overall)",
            "",
            "- n = 0 (no false exclusions captured)",
        ]

    lines += [
        "",
        "## p_excluded_state distribution on FALSE exclusions, by excluded_state",
        "",
        "| excluded_state | n | min | median | mean | max |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for state in ALL_STATES:
        info = summary["false_exclusion_p_excluded_distribution_by_state"][state]
        n = info.get("n", 0)
        if not n:
            lines.append(f"| {state} | 0 | – | – | – | – |")
            continue
        lines.append(
            f"| {state} | {n} | {info['min']:.4f} | {info['median']:.4f} | "
            f"{info['mean']:.4f} | {info['max']:.4f} |"
        )

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build 03 replay accuracy and exclusion-accuracy record")
    parser.add_argument(
        "--replay-dir",
        default="logs/historical_training/03_fresh_replay",
        help="Directory containing predictions.csv + reviews.csv from B-path replay",
    )
    parser.add_argument(
        "--record-path",
        default="records/03_replay_accuracy_and_exclusion_accuracy.md",
        help="Where to write the canonical 03 record",
    )
    args = parser.parse_args()

    replay_dir = Path(args.replay_dir).resolve()
    record_path = Path(args.record_path).resolve()
    record_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[03] reading replay from {replay_dir}")
    joined = build_join(replay_dir)
    print(f"[03] joined rows: {len(joined)}")

    write_prediction_details(joined, replay_dir / "03_prediction_details.csv")
    _, action_rows = write_exclusion_action_details(joined, replay_dir / "03_exclusion_action_details.csv")
    false_rows = write_false_exclusion_details(action_rows, joined, replay_dir / "03_false_exclusion_details.csv")
    cm = build_confusion_matrix(joined)
    cm.to_csv(replay_dir / "03_confusion_matrix.csv")

    summary = compute_summary(joined, action_rows, false_rows)
    with open(replay_dir / "03_replay_accuracy_summary.json", "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)

    intro_replay = [
        f"Built from B-path original-system replay outputs in `{replay_dir}`.",
        "Source pipeline: `scripts/run_historical_training.py` (matcher_v2 + coded_data, no live yfinance).",
    ]
    report_md = render_report_md(
        summary,
        title="AVGO 1005-day replay accuracy and exclusion-accuracy report (03)",
        intro_lines=intro_replay,
    )
    with open(replay_dir / "03_replay_accuracy_report.md", "w", encoding="utf-8") as fh:
        fh.write(report_md)

    intro_record = [
        "**Status: canonical baseline record (03).**",
        "",
        f"Generated from B-path replay run on {pd.Timestamp.now(tz='UTC').strftime('%Y-%m-%d')}.",
        f"Replay artifacts directory: `{replay_dir}`.",
        "",
        "Modules deliberately NOT used in this baseline:",
        "- `services.projection_orchestrator_v2` and the v2 chain (Tasks 038–050)",
        "- `services.rule_scoring` / `rule_lifecycle` / `active_rule_pool*` / `calibration` / `promotion` / `adoption_gate` / `drift`",
        "- `AVGO_technical_features.csv`",
        "- `exclusion_reliability_review`, contradiction-card payloads, shadow-backtest, 3C review payloads",
        "- live `yfinance` (replay reads `coded_data/AVGO_coded.csv` only)",
    ]
    record_md = render_report_md(
        summary,
        title="03 — AVGO original-system 1005-day replay: accuracy and exclusion accuracy",
        intro_lines=intro_record,
    )
    with open(record_path, "w", encoding="utf-8") as fh:
        fh.write(record_md)

    print(f"[03] wrote outputs to {replay_dir}")
    print(f"[03] wrote canonical record to {record_path}")
    print(f"[03] total_days={summary['total_days']} "
          f"five_state_acc={_fmt_pct(summary['five_state_overall_accuracy']['accuracy'])} "
          f"exclusion_acc={_fmt_pct(summary['exclusion_action_totals']['exclusion_accuracy'])} "
          f"false_exclusion_actions={summary['exclusion_action_totals']['false_exclusion_actions']}")


if __name__ == "__main__":
    main()
