from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import validate_exclusion_actions_2e as validator


def _base_big_up_row(**overrides) -> dict:
    row = {
        "as_of_date": "2026-04-21",
        "prediction_for_date": "2026-04-22",
        "forced_excluded_states": ["大涨"],
        "triggered_rules": ["exclude_big_up"],
        "actual_state": "大涨",
        "AVGO_T_return": 0.0,
        "AVGO_T_structure": "open=平开|close=平收|path=平开震荡",
        "vol_ratio20": 1.0,
        "vol_ratio_20": 1.0,
        "pos20": 50.0,
        "pos30": 50.0,
        "pos60": 50.0,
        "ret1": 0.0,
        "ret3": 0.0,
        "ret5": 0.0,
        "ret10": 0.0,
        "upper_shadow": 0.2,
        "lower_shadow": 0.2,
        "NVDA_T_return": 0.0,
        "SOXX_T_return": 0.0,
        "QQQ_T_return": 0.0,
        "peer_alignment": "neutral",
        "macro_contradicts_big_up_exclusion": False,
        "is_nq_short_term_oversold": False,
        "is_nq_rebound_candidate": False,
        "is_vix_spike": False,
        "macro_risk_support_score": 0,
        "is_market_rebound_candidate": False,
        "is_post_earnings_window": False,
        "is_pre_earnings_window": False,
        "is_near_earnings": False,
        "eps_surprise_last_quarter": None,
        "historical_sample_confidence": "high",
        "historical_match_count": 100,
        "historical_big_up_count": 5,
        "historical_big_up_rate": 0.05,
        "p_大涨": 0.05,
        "score_distribution_zeroed": False,
        "rsi_14": 50.0,
        "macd": 0.0,
        "macd_signal": 0.0,
        "macd_hist": 0.0,
        "close_vs_ma20_pct": 0.0,
        "close_vs_ma50_pct": 0.0,
    }
    row.update(overrides)
    return row


def _base_big_down_row(**overrides) -> dict:
    row = {
        "as_of_date": "2026-04-22",
        "prediction_for_date": "2026-04-23",
        "forced_excluded_states": ["大跌"],
        "triggered_rules": ["exclude_big_down"],
        "predicted_state": "小跌",
        "p_大跌": 0.12,
        "p_大涨": 0.18,
        "market_regime_label": "normal",
        "is_high_vol_regime": False,
        "is_crisis_regime": False,
        "vol_ratio20": 1.0,
        "vol_ratio_20": 1.0,
        "ret1": 0.0,
        "ret3": 0.0,
        "ret5": 0.0,
        "ret10": 0.0,
        "historical_sample_confidence": "low",
        "historical_big_down_rate": 0.12,
        "contradiction_inputs_available": True,
        "pos20": 50.0,
        "pos60": 50.0,
        "rsi_14": 50.0,
        "macd": 0.0,
        "macd_signal": 0.0,
        "macd_hist": 0.0,
        "close_vs_ma20_pct": 0.0,
        "close_vs_ma50_pct": 0.0,
    }
    row.update(overrides)
    return row


def test_split_excluded_states_supports_list_and_string():
    assert validator._split_excluded_states(["大涨", "大跌"]) == ["大涨", "大跌"]
    assert validator._split_excluded_states("大涨|大跌") == ["大涨", "大跌"]
    assert validator._split_excluded_states("['大涨', '大跌']") == ["大涨", "大跌"]


def test_big_up_raw_data_can_mark_action_unsupported():
    action = validator.evaluate_exclusion_action(
        _base_big_up_row(
            macro_contradicts_big_up_exclusion=True,
            is_nq_rebound_candidate=True,
            is_post_earnings_window=True,
            is_near_earnings=True,
        ),
        "大涨",
    )
    assert action["unsupported_by_raw_data"] is True
    assert action["raw_support_signal"] == "blocked_by_audit"


def test_big_up_technical_cluster_can_mark_action_unsupported():
    action = validator.evaluate_exclusion_action(
        _base_big_up_row(
            rsi_14=66.0,
            macd=1.2,
            macd_signal=0.6,
            macd_hist=0.4,
            close_vs_ma20_pct=2.5,
            close_vs_ma50_pct=4.0,
        ),
        "大涨",
    )
    assert action["unsupported_by_raw_data"] is False
    assert action["unsupported_by_technical_features"] is True
    assert "rsi_bullish" in action["technical_support_flags"]
    assert "macd_bullish" in action["technical_support_flags"]


def test_big_down_technical_cluster_can_mark_action_unsupported():
    action = validator.evaluate_exclusion_action(
        _base_big_down_row(
            rsi_14=35.0,
            macd=-1.2,
            macd_signal=-0.5,
            macd_hist=-0.3,
            close_vs_ma20_pct=-3.0,
            close_vs_ma50_pct=-4.0,
            ret5=-2.5,
        ),
        "大跌",
    )
    assert action["unsupported_by_raw_data"] is False
    assert action["unsupported_by_technical_features"] is True
    assert "rsi_bearish" in action["technical_support_flags"]
    assert "macd_bearish" in action["technical_support_flags"]


def test_merge_replay_sources_joins_on_as_of_date_and_aliases_vol_ratio(tmp_path: Path):
    enriched_path = tmp_path / "enriched.jsonl"
    technical_path = tmp_path / "technical.jsonl"

    enriched_rows = [_base_big_up_row(vol_ratio20=None, vol_ratio_20=None)]
    technical_rows = [_base_big_up_row(vol_ratio20=None, prediction_for_date="2026-04-22", vol_ratio_20=1.5)]

    enriched_path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in enriched_rows) + "\n",
        encoding="utf-8",
    )
    technical_path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in technical_rows) + "\n",
        encoding="utf-8",
    )

    merged_rows, merge_summary = validator.merge_replay_sources(
        enriched_path=enriched_path,
        technical_path=technical_path,
    )
    assert merge_summary["missing_technical_dates_count"] == 0
    assert len(merged_rows) == 1
    assert merged_rows[0]["vol_ratio20"] == 1.5


def test_summarize_action_rows_counts_raw_only_technical_only_and_supported():
    rows = [
        {
            "excluded_state": "大涨",
            "unsupported_by_raw_data": True,
            "unsupported_by_technical_features": False,
            "unsupported": True,
        },
        {
            "excluded_state": "大涨",
            "unsupported_by_raw_data": False,
            "unsupported_by_technical_features": True,
            "unsupported": True,
        },
        {
            "excluded_state": "大跌",
            "unsupported_by_raw_data": False,
            "unsupported_by_technical_features": False,
            "unsupported": False,
        },
    ]
    summary = validator.summarize_action_rows(rows)
    assert summary["overall"]["total_exclusion_actions"] == 3
    assert summary["overall"]["unsupported_actions"] == 2
    assert summary["overall"]["unsupported_by_raw_only"] == 1
    assert summary["overall"]["unsupported_by_technical_only"] == 1
    assert summary["overall"]["supported_actions"] == 1
