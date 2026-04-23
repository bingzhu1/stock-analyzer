from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.primary_bias_diagnosis import build_primary_bias_report


def _primary(
    *,
    direction: str = "偏多",
    position_label: str = "高位",
    stage_label: str = "延续",
    volume_state: str = "正常",
    basis: list[str] | None = None,
    ready: bool = True,
) -> dict:
    return {
        "kind": "primary_20day_analysis",
        "ready": ready,
        "direction": direction,
        "confidence": "medium",
        "position_label": position_label,
        "stage_label": stage_label,
        "volume_state": volume_state,
        "basis": basis or [
            "最近5日收益为 +3.20%。",
            "最近10日收益为 +4.80%。",
            "当前价格位于20日区间约 82.0% 位置。",
            f"简化阶段标签为{stage_label}。",
            f"主分析方向信号归纳为{direction}。",
        ],
        "features": {
            "ret_5d": 3.2,
            "ret_10d": 4.8,
            "pos_20d": 82.0,
        },
    }


def _replay(
    *,
    primary_analysis: dict | None = None,
    direction_correct: bool | None = False,
    error_layer: str = "primary",
    error_category: str = "wrong_direction",
    ready: bool = True,
) -> dict:
    return {
        "kind": "historical_replay_result",
        "symbol": "AVGO",
        "as_of_date": "2026-02-01",
        "prediction_for_date": "2026-02-02",
        "ready": ready,
        "projection_snapshot": {
            "kind": "projection_v2_report",
            "primary_analysis": primary_analysis if primary_analysis is not None else _primary(),
        },
        "review": {
            "direction_correct": direction_correct,
            "error_layer": error_layer,
            "error_category": error_category,
        },
        "warnings": [],
    }


class PrimaryBiasDiagnosisTests(unittest.TestCase):
    def test_happy_path_returns_complete_shape_and_distribution(self) -> None:
        report = build_primary_bias_report(
            replay_results=[
                _replay(primary_analysis=_primary(direction="偏多"), direction_correct=False),
                _replay(primary_analysis=_primary(direction="偏多"), direction_correct=True, error_category="correct"),
                _replay(primary_analysis=_primary(direction="中性", position_label="中位", stage_label="整理"), direction_correct=None, error_layer="unknown", error_category="unknown"),
                _replay(primary_analysis=_primary(direction="偏空", position_label="低位", stage_label="衰竭风险"), direction_correct=False, error_layer="primary"),
            ]
        )

        self.assertEqual(report["kind"], "primary_bias_report")
        self.assertTrue(report["ready"])
        self.assertEqual(report["total_cases"], 4)
        self.assertEqual(report["judged_cases"], 4)
        self.assertEqual(report["primary_direction_distribution"]["bullish"], 2)
        self.assertEqual(report["primary_direction_distribution"]["neutral"], 1)
        self.assertEqual(report["primary_direction_distribution"]["bearish"], 1)
        self.assertEqual(report["wrong_direction_cases"], 2)
        self.assertEqual(report["primary_error_share"], 1.0)

    def test_error_patterns_are_grouped_from_primary_error_cases(self) -> None:
        report = build_primary_bias_report(
            replay_results=[
                _replay(primary_analysis=_primary(position_label="高位", stage_label="延续", volume_state="正常")),
                _replay(primary_analysis=_primary(position_label="高位", stage_label="延续", volume_state="正常")),
                _replay(primary_analysis=_primary(position_label="高位", stage_label="延续", volume_state="放量")),
                _replay(primary_analysis=_primary(position_label="低位", stage_label="衰竭风险"), error_layer="peer"),
            ]
        )

        self.assertEqual(report["top_position_labels"][0]["label"], "高位")
        self.assertEqual(report["top_position_labels"][0]["count"], 3)
        self.assertEqual(report["top_stage_labels"][0]["label"], "延续")
        self.assertEqual(report["top_stage_labels"][0]["count"], 3)
        self.assertTrue(any("短期收益偏强" == row["pattern"] for row in report["top_basis_patterns"]))

    def test_obvious_persistent_bullish_bias_produces_suspected_sources(self) -> None:
        report = build_primary_bias_report(
            replay_results=[
                _replay(primary_analysis=_primary()),
                _replay(primary_analysis=_primary()),
                _replay(primary_analysis=_primary()),
                _replay(primary_analysis=_primary()),
                _replay(primary_analysis=_primary(direction="中性", position_label="中位", stage_label="整理"), direction_correct=None, error_layer="unknown", error_category="unknown"),
            ]
        )

        self.assertGreaterEqual(len(report["suspected_bias_sources"]), 2)
        titles = " ".join(item["title"] for item in report["suspected_bias_sources"])
        self.assertIn("偏多", titles)
        self.assertTrue(report["diagnosis_summary"])
        self.assertTrue(report["recommended_next_actions"])

    def test_missing_inputs_degrades_with_stable_shape(self) -> None:
        report = build_primary_bias_report(replay_results=None, historical_snapshots=None)

        self.assertFalse(report["ready"])
        self.assertEqual(report["total_cases"], 0)
        self.assertTrue(report["warnings"])
        self.assertEqual(
            sorted(report.keys()),
            sorted(
                [
                    "kind",
                    "symbol",
                    "ready",
                    "total_cases",
                    "judged_cases",
                    "primary_direction_distribution",
                    "wrong_direction_cases",
                    "wrong_direction_rate",
                    "primary_error_share",
                    "top_position_labels",
                    "top_stage_labels",
                    "top_volume_states",
                    "top_basis_patterns",
                    "suspected_bias_sources",
                    "diagnosis_summary",
                    "recommended_next_actions",
                    "warnings",
                ]
            ),
        )

    def test_partial_fields_do_not_crash_and_keep_partial_diagnosis(self) -> None:
        report = build_primary_bias_report(
            replay_results=[
                {"kind": "historical_replay_result", "projection_snapshot": {}, "review": {}},
                _replay(primary_analysis={"direction": "偏多"}, error_layer="primary"),
                _replay(primary_analysis={"ready": False}, direction_correct=None, error_layer="unknown", error_category="unknown"),
            ]
        )

        self.assertTrue(report["ready"])
        self.assertEqual(report["total_cases"], 3)
        self.assertGreaterEqual(report["primary_direction_distribution"]["unknown"], 1)
        self.assertTrue(report["diagnosis_summary"])
        self.assertTrue(report["recommended_next_actions"])

    def test_summary_and_actions_are_consistent_not_empty(self) -> None:
        report = build_primary_bias_report(
            replay_results=[
                _replay(primary_analysis=_primary(direction="偏多"), error_layer="primary"),
                _replay(primary_analysis=_primary(direction="偏多"), error_layer="primary"),
                _replay(primary_analysis=_primary(direction="偏多"), error_layer="primary"),
                _replay(primary_analysis=_primary(direction="偏空", position_label="低位", stage_label="衰竭风险"), error_layer="primary"),
            ]
        )

        self.assertIn("bullish=3", report["diagnosis_summary"])
        self.assertTrue(any("neutral" in action or "bullish" in action or "primary" in action for action in report["recommended_next_actions"]))


if __name__ == "__main__":
    unittest.main()
