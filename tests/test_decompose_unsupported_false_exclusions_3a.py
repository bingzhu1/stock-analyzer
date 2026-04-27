from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import decompose_unsupported_false_exclusions_3a as task3a


def test_filter_unsupported_rows_requires_111():
    frame = pd.DataFrame([{"unsupported_combined": True}] * 3)
    with pytest.raises(ValueError):
        task3a.filter_unsupported_rows(frame)


def test_normalize_big_up_raw_sources_maps_known_flags():
    payload = {
        "triggered_flags": [
            "macro_contradiction_softening",
            "sample_confidence_invalidation",
        ]
    }
    labels = task3a.normalize_big_up_raw_sources(payload)
    assert labels == ["macro_contradiction", "sample_confidence_invalidation"]


def test_normalize_big_down_raw_sources_ignores_downgrade_and_data_limited():
    payload = {
        "reasons": [
            "系统同时排除了大涨和大跌两端状态",
            "降级因素：量能不足，双尾收缩信号不够强",
            "数据受限：缺少关键字段 p_大跌, p_大涨",
            "近期量能明显放大",
        ]
    }
    labels = task3a.normalize_big_down_raw_sources(payload)
    assert labels == ["dual_extremes", "volume_expansion"]


def test_normalize_technical_sources_splits_pipe_string():
    labels = task3a.normalize_technical_sources("macd_bullish|positive_momentum")
    assert labels == ["macd_bullish", "positive_momentum"]


def test_build_summary_counts_mix_and_sources():
    evaluated = pd.DataFrame(
        [
            {
                "excluded_state_under_validation": "大涨",
                "unsupported_by_raw_enriched": True,
                "unsupported_by_technical_features": False,
                "support_mix": "raw_only",
                "raw_source_labels": "macro_contradiction|sample_confidence_invalidation",
                "technical_source_labels": "",
            },
            {
                "excluded_state_under_validation": "大跌",
                "unsupported_by_raw_enriched": False,
                "unsupported_by_technical_features": True,
                "support_mix": "technical_only",
                "raw_source_labels": "",
                "technical_source_labels": "macd_bearish|negative_momentum",
            },
            {
                "excluded_state_under_validation": "大涨",
                "unsupported_by_raw_enriched": True,
                "unsupported_by_technical_features": True,
                "support_mix": "raw_and_technical",
                "raw_source_labels": "post_earnings_window",
                "technical_source_labels": "rsi_bullish|macd_bullish",
            },
        ]
    )
    original_summary = {"overall": {"unsupported_combined": 3}}
    summary = task3a.build_summary(evaluated, original_summary)
    assert summary["unsupported_total"] == 3
    assert summary["support_mix_counts"]["raw_only"] == 1
    assert summary["support_mix_counts"]["technical_only"] == 1
    assert summary["support_mix_counts"]["raw_and_technical"] == 1
    assert summary["raw_source_counts"]["macro_contradiction"] == 1
    assert summary["technical_source_counts"]["macd_bearish"] == 1


def test_evaluate_source_row_uses_boolean_mix_even_when_raw_label_is_fallback():
    row = {
        "prediction_date": "2020-01-02",
        "target_date": "2020-01-03",
        "excluded_state_under_validation": "大跌",
        "actual_state": "大跌",
        "unsupported_by_raw_enriched": True,
        "unsupported_by_technical_features": False,
        "technical_flags": "",
        "forced_excluded_states": "大跌",
        "predicted_state": "震荡",
        "p_大跌": 0.03,
        "p_大涨": 0.03,
        "vol_ratio20": 1.0,
        "ret3": 0.0,
        "ret5": 0.0,
        "market_regime_label": "calm",
        "historical_sample_confidence": "high",
        "historical_big_down_rate": 0.0,
        "contradiction_inputs_available": True,
    }
    result = task3a.evaluate_source_row(row)
    assert result["support_mix"] == "raw_only"
    assert result["raw_source_labels"] != ""


def test_resolve_input_paths_uses_fallback_when_preferred_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    details = tmp_path / "details.csv"
    summary = tmp_path / "summary.json"
    details.write_text("unsupported_combined\nTrue\n", encoding="utf-8")
    summary.write_text(json.dumps({"overall": {}}), encoding="utf-8")

    monkeypatch.setattr(task3a, "PREFERRED_DETAILS", tmp_path / "missing-details.csv")
    monkeypatch.setattr(task3a, "PREFERRED_SUMMARY", tmp_path / "missing-summary.json")
    monkeypatch.setattr(task3a, "FALLBACK_DETAILS", details)
    monkeypatch.setattr(task3a, "FALLBACK_SUMMARY", summary)

    resolved_details, resolved_summary, notes = task3a.resolve_input_paths()
    assert resolved_details == details
    assert resolved_summary == summary
    assert notes["input_source"] == "task_2e_v2_fallback"
