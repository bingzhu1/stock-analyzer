from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.big_down_tail_warning import build_big_down_tail_warning


def _row(**overrides):
    row = {
        "forced_excluded_states": "大跌",
        "predicted_state": "小跌",
        "p_大跌": 0.12,
        "p_大涨": 0.18,
        "market_regime_label": "normal",
        "is_high_vol_regime": False,
        "is_crisis_regime": False,
        "vol_ratio20": 1.0,
        "ret3": -1.0,
        "ret5": -1.5,
        "historical_sample_confidence": "low",
        "historical_big_down_rate": 0.12,
        "contradiction_inputs_available": True,
    }
    row.update(overrides)
    return row


def test_no_big_down_exclusion_returns_none_warning():
    payload = build_big_down_tail_warning(_row(forced_excluded_states="大涨"))
    assert payload["had_big_down_exclusion"] is False
    assert payload["tail_compression_triggered"] is False
    assert payload["warning_level"] == "none"


def test_big_down_exclusion_without_tail_compression_returns_none_warning():
    payload = build_big_down_tail_warning(_row())
    assert payload["had_big_down_exclusion"] is True
    assert payload["tail_compression_triggered"] is False
    assert payload["warning_level"] == "none"


def test_dual_extremes_adds_score_and_reason():
    payload = build_big_down_tail_warning(_row(forced_excluded_states="大涨|大跌"))
    assert payload["tail_compression_score"] >= 1
    assert "系统同时排除了大涨和大跌两端状态" in payload["reasons"]


def test_shock_with_both_low_tail_probs_adds_score():
    payload = build_big_down_tail_warning(
        _row(predicted_state="震荡", p_大跌=0.05, p_大涨=0.04)
    )
    assert payload["tail_compression_score"] >= 3
    assert "预测结果偏向震荡" in payload["reasons"]
    assert "大跌概率被压低到 0.05 以下" in payload["reasons"]
    assert "大涨概率被压低到 0.05 以下" in payload["reasons"]


def test_score_at_least_four_returns_warning():
    payload = build_big_down_tail_warning(
        _row(
            forced_excluded_states="大涨|大跌",
            predicted_state="震荡",
            p_大跌=0.03,
            p_大涨=0.02,
        )
    )
    assert payload["tail_compression_triggered"] is True
    assert payload["tail_compression_score"] >= 4
    assert payload["warning_level"] == "warning"


def test_score_at_least_five_returns_strong_warning():
    payload = build_big_down_tail_warning(
        _row(
            forced_excluded_states="大涨|大跌",
            predicted_state="震荡",
            p_大跌=0.03,
            p_大涨=0.02,
            is_high_vol_regime=True,
        )
    )
    assert payload["tail_compression_triggered"] is True
    assert payload["tail_compression_score"] >= 5
    assert payload["warning_level"] == "strong_warning"


def test_counter_threshold_downgrades_warning():
    payload = build_big_down_tail_warning(
        _row(
            forced_excluded_states="大涨|大跌",
            predicted_state="震荡",
            p_大跌=0.03,
            p_大涨=0.02,
            is_high_vol_regime=True,
            ret5=5.5,
            market_regime_label="calm",
            vol_ratio20=0.6,
        )
    )
    assert payload["tail_compression_triggered"] is True
    assert payload["warning_level"] == "none"


def test_missing_fields_marks_data_limited_without_error():
    payload = build_big_down_tail_warning(
        _row(p_大跌=None, p_大涨=None, predicted_state=None, contradiction_inputs_available=False)
    )
    assert payload["data_limited"] is True
    assert "predicted_state" in payload["missing_fields"]
    assert "p_大跌" in payload["missing_fields"]
    assert "p_大涨" in payload["missing_fields"]
    assert payload["warning_level"] == "none"


def test_p_big_down_falls_back_to_state_probabilities():
    payload = build_big_down_tail_warning(
        _row(
            forced_excluded_states="大涨|大跌",
            predicted_state="震荡",
            p_大跌=None,
            p_大涨=0.03,
            state_probabilities=json.dumps({"大跌": 0.04, "大涨": 0.03}, ensure_ascii=False),
        )
    )
    assert "p_大跌" not in payload["missing_fields"]
    assert payload["tail_compression_triggered"] is True


def test_p_big_up_falls_back_to_state_probabilities():
    payload = build_big_down_tail_warning(
        _row(
            forced_excluded_states="大涨|大跌",
            predicted_state="震荡",
            p_大跌=0.04,
            p_大涨=None,
            state_probabilities={"大涨": 0.03, "大跌": 0.04},
        )
    )
    assert "p_大涨" not in payload["missing_fields"]
    assert payload["tail_compression_triggered"] is True
