from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services import exclusion_reliability_review as review


def test_build_item_from_3a_style_row_maps_taxonomy_and_summary():
    row = {
        "excluded_state_under_validation": "大涨",
        "actual_state": "大涨",
        "support_mix": "raw_and_technical",
        "unsupported_by_raw_enriched": True,
        "unsupported_by_technical_features": True,
        "raw_source_labels": "macro_contradiction|sample_confidence_invalidation",
        "technical_source_labels": "macd_bullish|positive_momentum",
    }

    item = review.build_exclusion_reliability_item(row, excluded_state="大涨")
    assert item["has_exclusion"] is True
    assert item["has_reliability_concern"] is True
    assert item["support_mix"] == "raw_and_technical"
    assert item["taxonomy_keys"] == [
        "macro_rebound_conflicts_with_big_up_exclusion",
        "bullish_momentum_cluster",
        "history_support_thin_for_big_up_exclusion",
    ]
    assert item["strongest_tier_cn"] == "强证据"
    assert "系统原先否定了“大涨”" in item["display_summary_cn"]


def test_build_review_from_row_without_exclusion_returns_empty_review():
    payload = review.build_exclusion_reliability_review(
        {
            "forced_excluded_states": "小涨|震荡",
            "predicted_state": "震荡",
        }
    )
    assert payload["has_exclusion_review"] is False
    assert payload["review_items"] == []
    assert "无需生成" in payload["summary_cn"]


def test_supported_item_does_not_emit_taxonomy_or_tier():
    item = review.build_exclusion_reliability_item(
        {
            "excluded_state_under_validation": "大涨",
            "unsupported_by_raw_enriched": False,
            "unsupported_by_technical_features": False,
            "support_mix": "supported",
            "raw_source_labels": "",
            "technical_source_labels": "macd_bullish",
        },
        excluded_state="大涨",
    )
    assert item["has_reliability_concern"] is False
    assert item["taxonomy_keys"] == []
    assert item["technical_source_labels"] == []
    assert item["strongest_tier_cn"] == ""


def test_build_review_infers_big_down_signals_from_prediction_row():
    row = {
        "forced_excluded_states": "大涨|大跌",
        "predicted_state": "震荡",
        "p_大跌": 0.03,
        "p_大涨": 0.03,
        "is_high_vol_regime": True,
        "is_crisis_regime": False,
        "vol_ratio20": 1.4,
        "ret3": -3.5,
        "ret5": -5.2,
        "market_regime_label": "risk",
        "historical_sample_confidence": "medium",
        "historical_big_down_rate": 0.15,
        "contradiction_inputs_available": True,
        "rsi_14": 35.0,
        "macd": -1.0,
        "macd_signal": 0.0,
        "macd_hist": -0.5,
        "close_vs_ma20_pct": -1.0,
        "close_vs_ma50_pct": -2.0,
        "ret1": -1.2,
        "ret10": -5.5,
        "pos20": 20.0,
        "pos60": 35.0,
        "vol_ratio_20": 1.4,
    }

    payload = review.build_exclusion_reliability_review(row)
    assert payload["has_exclusion_review"] is True
    assert payload["has_reliability_concern"] is True
    assert payload["excluded_states_reviewed"] == ["大涨", "大跌"]

    big_down_item = next(item for item in payload["review_items"] if item["excluded_state"] == "大跌")
    big_up_item = next(item for item in payload["review_items"] if item["excluded_state"] == "大涨")
    assert big_up_item["has_reliability_concern"] is False
    assert "可靠性下降解释" in big_up_item["display_summary_cn"]
    assert big_up_item["taxonomy_keys"] == []
    assert big_up_item["strongest_tier_cn"] == ""
    assert big_down_item["unsupported_by_raw_enriched"] is True
    assert big_down_item["unsupported_by_technical_features"] is True
    assert big_down_item["support_mix"] == "raw_and_technical"
    assert "dual_tail_conflict_against_big_down_exclusion" in big_down_item["taxonomy_keys"]
    assert "bearish_momentum_cluster" in big_down_item["taxonomy_keys"]
    assert big_down_item["strongest_tier_cn"] == "强证据"


def test_build_item_for_non_matching_state_returns_no_exclusion_message():
    row = {
        "excluded_state_under_validation": "大涨",
        "raw_source_labels": "macro_contradiction",
    }
    item = review.build_exclusion_reliability_item(row, excluded_state="大跌")
    assert item["has_exclusion"] is False
    assert item["taxonomy_keys"] == []
    assert "没有否定“大跌”" in item["display_summary_cn"]
