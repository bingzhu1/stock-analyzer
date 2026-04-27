from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import validate_false_exclusions_2e_v2 as validator


def test_extract_false_exclusion_rows_counts_big_up_and_big_down():
    rows = pd.DataFrame(
        [
            {"prediction_date": "2020-01-01", "actual_state": "大涨", "forced_excluded_states": "大涨|小涨"},
            {"prediction_date": "2020-01-02", "actual_state": "大跌", "forced_excluded_states": "大跌"},
            {"prediction_date": "2020-01-03", "actual_state": "小涨", "forced_excluded_states": "大涨"},
        ]
    )
    false_rows = validator.extract_false_exclusion_rows(rows)
    assert len(false_rows) == 2
    assert false_rows["excluded_state_under_validation"].tolist() == ["大涨", "大跌"]


def test_verify_expected_false_counts_rejects_wrong_baseline():
    frame = pd.DataFrame(
        [{"excluded_state_under_validation": "大涨"} for _ in range(3)]
    )
    with pytest.raises(ValueError):
        validator.verify_expected_false_counts(frame)


def test_join_technical_features_uses_prediction_date_key():
    false_rows = pd.DataFrame(
        [
            {
                "prediction_date": "2020-01-02",
                "target_date": "2020-01-03",
                "actual_state": "大涨",
                "forced_excluded_states": "大涨",
                "excluded_state_under_validation": "大涨",
            }
        ]
    )
    technical_rows = pd.DataFrame(
        [
            {
                "Date": "2020-01-02",
                "rsi_14": 65.0,
                "macd": 1.2,
                "macd_signal": 0.7,
                "macd_hist": 0.5,
            }
        ]
    )
    merged, join_summary = validator.join_technical_features(false_rows, technical_rows)
    assert len(merged) == 1
    assert join_summary["technical_joined_rows"] == 1
    assert float(merged.loc[0, "rsi_14"]) == 65.0


def test_evaluate_false_row_big_up_marks_raw_and_technical_unsupported():
    row = {
        "prediction_date": "2020-01-02",
        "target_date": "2020-01-03",
        "actual_state": "大涨",
        "actual_close_change": 2.5,
        "forced_excluded_states": "大涨",
        "excluded_state_under_validation": "大涨",
        "AVGO_T_return": 0.0,
        "AVGO_T_structure": "open=平开|close=平收|path=平开震荡",
        "vol_ratio20": 1.0,
        "pos20": 50.0,
        "pos30": 50.0,
        "ret1": 0.0,
        "ret3": 0.0,
        "ret5": 0.0,
        "upper_shadow": 0.2,
        "lower_shadow": 0.2,
        "NVDA_T_return": 0.0,
        "SOXX_T_return": 0.0,
        "QQQ_T_return": 0.0,
        "peer_alignment": "neutral",
        "macro_contradicts_big_up_exclusion": True,
        "is_nq_short_term_oversold": False,
        "is_nq_rebound_candidate": True,
        "is_vix_spike": False,
        "macro_risk_support_score": 2,
        "is_market_rebound_candidate": False,
        "is_post_earnings_window": True,
        "is_pre_earnings_window": False,
        "is_near_earnings": True,
        "eps_surprise_last_quarter": None,
        "historical_sample_confidence": "high",
        "historical_match_count": 100,
        "historical_big_up_count": 5,
        "historical_big_up_rate": 0.05,
        "p_大涨": 0.05,
        "score_distribution_zeroed": False,
        "rsi_14": 66.0,
        "macd": 1.1,
        "macd_signal": 0.4,
        "macd_hist": 0.3,
        "close_vs_ma20_pct": 2.5,
        "close_vs_ma50_pct": 3.0,
        "ret10": 4.5,
        "pos60": 72.0,
        "vol_ratio_20": 1.3,
    }
    result = validator.evaluate_false_row(row)
    assert result["unsupported_by_raw_enriched"] is True
    assert result["unsupported_by_technical_features"] is True
    assert result["unsupported_combined"] is True


def test_summarize_results_counts_union():
    rows = [
        {
            "excluded_state_under_validation": "大涨",
            "unsupported_by_raw_enriched": True,
            "unsupported_by_technical_features": False,
            "unsupported_combined": True,
        },
        {
            "excluded_state_under_validation": "大跌",
            "unsupported_by_raw_enriched": False,
            "unsupported_by_technical_features": True,
            "unsupported_combined": True,
        },
        {
            "excluded_state_under_validation": "大跌",
            "unsupported_by_raw_enriched": False,
            "unsupported_by_technical_features": False,
            "unsupported_combined": False,
        },
    ]
    summary = validator.summarize_results(rows)
    assert summary["overall"]["false_total"] == 3
    assert summary["overall"]["unsupported_by_raw_enriched"] == 1
    assert summary["overall"]["unsupported_by_technical_features"] == 1
    assert summary["overall"]["unsupported_combined"] == 2
