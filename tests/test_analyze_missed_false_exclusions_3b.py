from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import analyze_missed_false_exclusions_3b as task3b


def test_filter_missed_rows_requires_54():
    frame = pd.DataFrame([{"unsupported_combined": False}] * 3)
    with pytest.raises(ValueError):
        task3b.filter_missed_rows(frame)


def test_classify_big_up_raw_residual_detects_no_contradiction_flags():
    label, reasons = task3b.classify_big_up_raw_residual(
        {"audit_decision": "hard_excluded", "triggered_flags": []}
    )
    assert label == "raw_no_contradiction_flags"
    assert reasons == ["audit_hard_excluded", "no_triggered_flags"]


def test_classify_big_down_raw_residual_detects_no_base_tail_pattern():
    row = {
        "forced_excluded_states": "大跌|小跌",
        "predicted_state": "小涨",
        "p_大涨": 0.30,
        "p_大跌": None,
    }
    payload = {"reasons": ["数据受限：缺少关键字段 p_大跌"], "tail_compression_score": 0}
    label, reasons = task3b.classify_big_down_raw_residual(row, payload)
    assert label == "raw_no_base_tail_pattern"
    assert reasons == ["missing_p_big_down"]


def test_classify_big_down_raw_residual_detects_score_below_threshold():
    row = {
        "forced_excluded_states": "大涨|大跌",
        "predicted_state": "震荡",
        "p_大涨": 0.00,
        "p_大跌": None,
    }
    payload = {
        "reasons": [
            "系统同时排除了大涨和大跌两端状态",
            "预测结果偏向震荡",
            "数据受限：缺少关键字段 p_大跌",
        ],
        "tail_compression_score": 3,
    }
    label, reasons = task3b.classify_big_down_raw_residual(row, payload)
    assert label == "raw_tail_pattern_but_score_below_threshold"
    assert reasons == ["dual_extremes", "missing_p_big_down", "predicted_neutral"]


def test_classify_technical_residual_handles_zero_and_single_signal():
    zero_label, zero_flags = task3b.classify_technical_residual(
        excluded_state="大涨",
        row={},
    )
    assert zero_label == "tech_zero_support_signals"
    assert zero_flags == []

    single_label, single_flags = task3b.classify_technical_residual(
        excluded_state="大跌",
        row={
            "rsi_14": 50,
            "macd": -1,
            "macd_signal": 0,
            "macd_hist": -0.5,
            "close_vs_ma20_pct": 1,
            "close_vs_ma50_pct": 1,
            "ret5": 0,
            "ret10": 0,
            "pos20": 50,
            "pos60": 50,
            "vol_ratio_20": 1.0,
            "ret1": 0.0,
        },
    )
    assert single_label == "tech_single_signal_macd_bearish"
    assert single_flags == ["macd_bearish"]


def test_build_summary_counts_residuals_and_context():
    evaluated = pd.DataFrame(
        [
            {
                "excluded_state_under_validation": "大涨",
                "raw_residual_label": "raw_no_contradiction_flags",
                "raw_reason_labels": "audit_hard_excluded|no_triggered_flags",
                "technical_residual_label": "tech_zero_support_signals",
                "technical_flags": "",
            },
            {
                "excluded_state_under_validation": "大跌",
                "raw_residual_label": "raw_no_base_tail_pattern",
                "raw_reason_labels": "missing_p_big_down|volume_expansion",
                "technical_residual_label": "tech_single_signal_macd_bearish",
                "technical_flags": "macd_bearish",
            },
        ]
    )
    summary = task3b.build_summary(evaluated, {"overall": {"unsupported_combined": 111}})
    assert summary["missed_total"] == 2
    assert summary["raw_residual_counts"]["raw_no_contradiction_flags"] == 1
    assert summary["technical_residual_counts"]["tech_zero_support_signals"] == 1
    assert summary["raw_reason_counts"]["missing_p_big_down"] == 1
    assert summary["technical_flag_counts"]["macd_bearish"] == 1


def test_run_uses_fallback_input_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    details = tmp_path / "details.csv"
    summary = tmp_path / "summary.json"
    v4 = tmp_path / "v4.csv"
    tech = tmp_path / "tech.csv"
    dates = pd.date_range("2020-01-01", periods=54, freq="B")
    details.write_text(
        "prediction_date,target_date,excluded_state_under_validation,actual_state,unsupported_combined,unsupported_by_raw_enriched,unsupported_by_technical_features,raw_enriched_signal\n"
        + "\n".join(
            f"{date.strftime('%Y-%m-%d')},{(date + pd.Timedelta(days=1)).strftime('%Y-%m-%d')},大涨,大涨,False,False,False,supported"
            for date in dates
        )
        + "\n",
        encoding="utf-8",
    )
    summary.write_text(json.dumps({"overall": {"unsupported_combined": 111}}), encoding="utf-8")
    v4.write_text(
        "prediction_date,target_date,forced_excluded_states,actual_state,predicted_state,p_大涨\n"
        + "\n".join(
            f"{date.strftime('%Y-%m-%d')},{(date + pd.Timedelta(days=1)).strftime('%Y-%m-%d')},大涨,大涨,小涨,0.5"
            for date in dates
        )
        + "\n",
        encoding="utf-8",
    )
    tech.write_text(
        "Date,rsi_14,macd,macd_signal,macd_hist,close_vs_ma20_pct,close_vs_ma50_pct,ret1,ret5,ret10,pos20,pos60,vol_ratio_20\n"
        + "\n".join(
            f"{date.strftime('%Y-%m-%d')},50,0,0,0,0,0,0,0,0,50,50,1.0"
            for date in dates
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(task3b.task3a, "PREFERRED_DETAILS", tmp_path / "missing-details.csv")
    monkeypatch.setattr(task3b.task3a, "PREFERRED_SUMMARY", tmp_path / "missing-summary.json")
    monkeypatch.setattr(task3b.task3a, "FALLBACK_DETAILS", details)
    monkeypatch.setattr(task3b.task3a, "FALLBACK_SUMMARY", summary)
    monkeypatch.setattr(task3b.task3a, "DEFAULT_MAIN_V4", tmp_path / "missing-v4.csv")
    monkeypatch.setattr(task3b.task3a, "DEFAULT_SIBLING_V4", v4)
    monkeypatch.setattr(task3b.task2e_v2, "DEFAULT_MAIN_TECHNICAL", tmp_path / "missing-tech.csv")
    monkeypatch.setattr(task3b.task2e_v2, "DEFAULT_SIBLING_TECHNICAL", tech)

    result = task3b.run(output_dir=tmp_path / "out")
    assert result["summary"]["missed_total"] == 54
    assert result["source"]["input_source"] == "task_2e_v2_fallback"
    assert result["source"]["v4_source"] == "sibling_worktree"
    assert result["source"]["technical_source"] == "sibling_worktree"
