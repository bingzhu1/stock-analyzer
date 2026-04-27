from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import shadow_backtest_exclusion_reliability_review_3c5 as task3c5


def test_explode_exclusion_actions_splits_big_states_only():
    frame = pd.DataFrame(
        [
            {
                "prediction_date": "2020-01-02",
                "target_date": "2020-01-03",
                "actual_state": "大涨",
                "predicted_state": "震荡",
                "forced_excluded_states": "大涨|大跌|小涨",
            },
            {
                "prediction_date": "2020-01-03",
                "target_date": "2020-01-06",
                "actual_state": "震荡",
                "predicted_state": "震荡",
                "forced_excluded_states": "小涨|小跌",
            },
        ]
    )
    exploded = task3c5.explode_exclusion_actions(frame)
    assert len(exploded) == 2
    assert exploded["excluded_state"].tolist() == ["大涨", "大跌"]


def test_build_shadow_backtest_details_marks_rescued_and_hurt_actions():
    actions = pd.DataFrame(
        [
            {
                "prediction_date": "2020-01-02",
                "target_date": "2020-01-03",
                "actual_state": "大涨",
                "predicted_state": "震荡",
                "forced_excluded_states": "大涨",
                "excluded_state": "大涨",
            },
            {
                "prediction_date": "2020-01-03",
                "target_date": "2020-01-06",
                "actual_state": "震荡",
                "predicted_state": "震荡",
                "forced_excluded_states": "大跌",
                "excluded_state": "大跌",
            },
        ]
    )
    reviews = pd.DataFrame(
        [
            {
                "prediction_date": "2020-01-02",
                "target_date": "2020-01-03",
                "excluded_state": "大涨",
                "has_reliability_concern": True,
                "unsupported_by_raw_enriched": True,
                "unsupported_by_technical_features": True,
                "support_mix": "raw_and_technical",
                "raw_source_labels": "macro_contradiction",
                "technical_source_labels": "macd_bullish|positive_momentum",
                "taxonomy_keys": "macro_rebound_conflicts_with_big_up_exclusion|bullish_momentum_cluster",
                "strongest_tier_cn": "强证据",
                "display_summary_cn": "x",
            },
            {
                "prediction_date": "2020-01-03",
                "target_date": "2020-01-06",
                "excluded_state": "大跌",
                "has_reliability_concern": True,
                "unsupported_by_raw_enriched": True,
                "unsupported_by_technical_features": False,
                "support_mix": "raw_only",
                "raw_source_labels": "dual_extremes",
                "technical_source_labels": "",
                "taxonomy_keys": "dual_tail_conflict_against_big_down_exclusion",
                "strongest_tier_cn": "辅助证据",
                "display_summary_cn": "y",
            },
        ]
    )
    details = task3c5.build_shadow_backtest_details(actions, reviews)
    assert details["shadow_outcome"].tolist() == [
        "rescued_false_exclusion",
        "kept",
    ]
    assert details["shadow_downgrade_triggered"].tolist() == [True, False]


def test_state_summary_computes_shadow_metrics():
    frame = pd.DataFrame(
        [
            {"is_false_exclusion": True, "is_correct_exclusion": False, "shadow_downgrade_triggered": True},
            {"is_false_exclusion": True, "is_correct_exclusion": False, "shadow_downgrade_triggered": False},
            {"is_false_exclusion": False, "is_correct_exclusion": True, "shadow_downgrade_triggered": True},
            {"is_false_exclusion": False, "is_correct_exclusion": True, "shadow_downgrade_triggered": False},
        ]
    )
    summary = task3c5._state_summary(frame)
    assert summary["false_exclusions_total"] == 2
    assert summary["correct_exclusions_total"] == 2
    assert summary["rescued_false_exclusions"] == 1
    assert summary["hurt_correct_exclusions"] == 1
    assert summary["false_rescue_rate"] == 50.0
    assert summary["correct_hurt_rate"] == 50.0


def test_verify_inputs_rejects_mismatched_review_actions():
    replay_actions = pd.DataFrame(
        [
            {
                "prediction_date": "2020-01-02",
                "target_date": "2020-01-03",
                "actual_state": "大涨",
                "predicted_state": "震荡",
                "forced_excluded_states": "大涨",
                "excluded_state": "大涨",
            }
        ]
    )
    replay_review = pd.DataFrame(
        [
            {
                "prediction_date": "2020-01-02",
                "target_date": "2020-01-03",
                "actual_state": "大涨",
                "forced_excluded_states": "大涨",
                "excluded_state_reviewed": "大跌",
                "excluded_state": "大跌",
            }
        ]
    )
    false_validation = pd.DataFrame(
        [
            {
                "prediction_date": "2020-01-02",
                "target_date": "2020-01-03",
                "excluded_state_under_validation": "大涨",
                "excluded_state": "大涨",
            }
        ]
    )
    false_review = pd.DataFrame(
        [
            {
                "prediction_date": "2020-01-02",
                "target_date": "2020-01-03",
                "actual_state": "大涨",
                "forced_excluded_states": "大涨",
                "excluded_state_reviewed": "大涨",
                "excluded_state": "大涨",
            }
        ]
    )
    v4_rows = pd.DataFrame([{"forced_excluded_states": "大涨"}] * 1005)

    try:
        task3c5.verify_inputs(
            replay_actions=replay_actions,
            replay_review_details=replay_review,
            false_validation_details=false_validation,
            false_review_details=false_review,
            v4_rows=v4_rows,
        )
    except ValueError as exc:
        assert "Replay review details do not match exploded replay actions" in str(exc)
    else:
        raise AssertionError("Expected verify_inputs to fail on mismatched replay actions.")
