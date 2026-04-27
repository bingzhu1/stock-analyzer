from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_unsupported_explanation_taxonomy_3c1 as task3c1


def test_filter_unsupported_rows_requires_111():
    frame = pd.DataFrame([{"support_mix": "raw_only"}] * 3)
    with pytest.raises(ValueError):
        task3c1.filter_unsupported_rows(frame)


def test_map_labels_to_taxonomy_keys_preserves_tier_priority():
    keys = task3c1.map_labels_to_taxonomy_keys(
        ["sample_confidence_invalidation", "macro_contradiction", "macd_bullish"]
    )
    assert keys == [
        "macro_rebound_conflicts_with_big_up_exclusion",
        "bullish_momentum_cluster",
        "history_support_thin_for_big_up_exclusion",
    ]


def test_evaluate_row_builds_cn_summary_and_tiers():
    row = {
        "prediction_date": "2020-01-02",
        "target_date": "2020-01-03",
        "excluded_state_under_validation": "大涨",
        "actual_state": "大涨",
        "support_mix": "raw_and_technical",
        "raw_source_labels": "macro_contradiction|sample_confidence_invalidation",
        "technical_source_labels": "macd_bullish|positive_momentum",
    }
    result = task3c1.evaluate_row(row)
    assert result["strongest_tier_cn"] == "强证据"
    assert "系统原先否定了“大涨”" in result["display_summary_cn"]
    assert "宏观环境更像反弹" in result["display_summary_cn"]
    assert "历史样本不足" in result["display_summary_cn"] or "历史样本信心不足" in result["display_summary_cn"]


def test_build_summary_counts_taxonomy_and_tiers():
    evaluated = pd.DataFrame(
        [
            {
                "excluded_state_under_validation": "大涨",
                "support_mix": "raw_only",
                "taxonomy_keys": "macro_rebound_conflicts_with_big_up_exclusion|history_support_thin_for_big_up_exclusion",
                "taxonomy_tiers_cn": "强证据|数据缺口提醒",
                "strongest_tier_cn": "强证据",
            },
            {
                "excluded_state_under_validation": "大跌",
                "support_mix": "technical_only",
                "taxonomy_keys": "bearish_momentum_cluster",
                "taxonomy_tiers_cn": "强证据",
                "strongest_tier_cn": "强证据",
            },
        ]
    )
    summary = task3c1.build_summary(evaluated, {"baseline": {"unsupported_total": 111}})
    assert summary["unsupported_total"] == 2
    assert summary["taxonomy_counts"]["macro_rebound_conflicts_with_big_up_exclusion"] == 1
    assert summary["display_tier_counts"]["强证据"] == 2
    assert summary["display_tier_counts"]["数据缺口提醒"] == 1


def test_catalog_summary_exposes_title_and_count():
    evaluated = pd.DataFrame(
        [
            {
                "taxonomy_keys": "bearish_momentum_cluster|bearish_trend_structure_cluster",
                "taxonomy_tiers_cn": "强证据|强证据",
                "support_mix": "technical_only",
                "excluded_state_under_validation": "大跌",
                "strongest_tier_cn": "强证据",
            }
        ]
    )
    catalog = task3c1._build_catalog_summary(evaluated)
    bearish_entry = next(item for item in catalog if item["taxonomy_key"] == "bearish_momentum_cluster")
    assert bearish_entry["count"] == 1
    assert bearish_entry["display_tier_cn"] == "强证据"
    assert "技术动量转弱" in bearish_entry["title_cn"]


def test_run_uses_task_3a_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    details = tmp_path / "details.csv"
    summary = tmp_path / "summary.json"
    rows = []
    for day in range(111):
        rows.append(
            {
                "prediction_date": f"2020-01-{(day % 28) + 1:02d}",
                "target_date": f"2020-02-{(day % 28) + 1:02d}",
                "excluded_state_under_validation": "大涨" if day < 89 else "大跌",
                "actual_state": "大涨" if day < 89 else "大跌",
                "support_mix": "raw_only" if day % 2 == 0 else "technical_only",
                "raw_source_labels": "sample_confidence_invalidation" if day % 2 == 0 else "",
                "technical_source_labels": "macd_bearish|negative_momentum" if day % 2 == 1 else "",
            }
        )
    pd.DataFrame(rows).to_csv(details, index=False)
    summary.write_text(
        json.dumps({"baseline": {"unsupported_total": 111}, "unsupported_total": 111}),
        encoding="utf-8",
    )

    monkeypatch.setattr(task3c1, "DEFAULT_DETAILS", details)
    monkeypatch.setattr(task3c1, "DEFAULT_SUMMARY", summary)

    result = task3c1.run(output_dir=tmp_path / "out")
    assert result["summary"]["unsupported_total"] == 111
    assert result["source"]["input_source"] == "task_3a_output"
    assert result["summary"]["taxonomy_counts"]["history_support_thin_for_big_up_exclusion"] > 0
    assert result["summary"]["taxonomy_counts"]["bearish_momentum_cluster"] > 0
