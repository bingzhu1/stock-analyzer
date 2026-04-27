from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import batch_run_exclusion_reliability_review_3c3 as task3c3


def test_protected_fields_unchanged_detects_no_mutation():
    before = {"predicted_state": "震荡", "forced_excluded_states": "大涨|大跌", "p_大涨": 0.03}
    after = {"predicted_state": "震荡", "forced_excluded_states": "大涨|大跌", "p_大涨": 0.03}
    assert task3c3._protected_fields_unchanged(before, after) is True


def test_validate_payload_shape_flags_missing_keys():
    ok, missing = task3c3._validate_payload_shape({"title": "x", "review_items": []})
    assert ok is False
    assert "has_exclusion_review" in missing


def test_run_batch_flattens_review_items_and_counts_concerns():
    frame = pd.DataFrame(
        [
            {
                "prediction_date": "2020-01-02",
                "target_date": "2020-01-03",
                "actual_state": "大涨",
                "forced_excluded_states": "大涨",
                "excluded_state_under_validation": "大涨",
                "unsupported_by_raw_enriched": True,
                "unsupported_by_technical_features": True,
                "support_mix": "raw_and_technical",
                "raw_source_labels": "macro_contradiction|sample_confidence_invalidation",
                "technical_source_labels": "macd_bullish|positive_momentum",
                "predicted_state": "震荡",
                "p_大涨": 0.01,
                "p_大跌": 0.01,
            },
            {
                "prediction_date": "2020-01-06",
                "target_date": "2020-01-07",
                "actual_state": "大跌",
                "forced_excluded_states": "大跌",
                "excluded_state_under_validation": "大跌",
                "unsupported_by_raw_enriched": False,
                "unsupported_by_technical_features": False,
                "support_mix": "supported",
                "raw_source_labels": "",
                "technical_source_labels": "",
                "predicted_state": "大涨",
                "p_大涨": 0.80,
                "p_大跌": 0.01,
            },
        ]
    )
    details, summary = task3c3._run_batch("false_exclusion_rows", frame)
    assert len(details) == 2
    assert summary["input_rows"] == 2
    assert summary["review_item_rows"] == 2
    assert summary["review_items_with_reliability_concern"] == 1
    assert summary["protected_field_changes"] == 0
    assert summary["payload_shape_failures"] == 0


def test_filter_replay_rows_keeps_only_big_up_or_big_down_exclusions():
    frame = pd.DataFrame(
        [
            {"forced_excluded_states": "大涨|小涨"},
            {"forced_excluded_states": "大跌|小跌"},
            {"forced_excluded_states": "震荡|小涨"},
            {"forced_excluded_states": ""},
        ]
    )
    filtered = task3c3._filter_replay_rows(frame)
    assert len(filtered) == 2
