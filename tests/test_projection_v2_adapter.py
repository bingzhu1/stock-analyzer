from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.projection_v2_adapter import (
    build_projection_entrypoint_result,
    build_projection_v2_compat,
    _caution_level,
)


def _v2_result(**overrides) -> dict[str, Any]:
    base: dict[str, Any] = {
        "kind": "projection_v2_report",
        "symbol": "AVGO",
        "lookback_days": 20,
        "target_date": "2026-04-21",
        "ready": True,
        "preflight": {
            "kind": "projection_rule_preflight",
            "ready": True,
            "matched_rules": [],
            "rule_warnings": [],
            "rule_adjustments": [],
            "summary": "未命中历史规则。",
            "warnings": [],
            "source_counts": {"memory_items": 0, "review_items": 0, "matched_rule_count": 0},
        },
        "primary_analysis": {
            "kind": "primary_20day_analysis",
            "symbol": "AVGO",
            "ready": True,
            "direction": "偏多",
            "confidence": "medium",
            "lookback_days": 20,
            "target_date": "2026-04-21",
            "basis": ["最近5日收益为 +3.00%。", "主分析方向信号归纳为偏多。"],
            "summary": "AVGO 主分析：偏多。",
            "warnings": [],
        },
        "peer_adjustment": {"kind": "peer_adjustment", "ready": True, "adjustment": "no_change"},
        "historical_probability": {"kind": "historical_probability", "ready": True, "historical_bias": "supports_bullish", "impact": "support"},
        "final_decision": {
            "kind": "final_decision",
            "symbol": "AVGO",
            "ready": True,
            "final_direction": "偏多",
            "final_confidence": "medium",
            "risk_level": "medium",
            "summary": "综合判断：偏多。",
            "decision_factors": ["主分析偏多，peers 中性，历史支持。"],
            "warnings": [],
            "layer_contributions": {
                "primary": "主分析偏多。",
                "peer": "peers 保持 no_change。",
                "historical": "历史支持。",
                "preflight": "未命中规则。",
            },
            "why_not_more_bullish_or_bearish": "信号对称。",
            "source_snapshot": {
                "primary_direction": "偏多",
                "peer_adjustment": "no_change",
                "historical_bias": "supports_bullish",
                "preflight_rules_count": 0,
            },
        },
        "warnings": [],
        "trace": [
            {"step": "preflight", "status": "success", "message": "未命中规则。"},
            {"step": "primary_analysis", "status": "success", "message": "主分析完成。"},
            {"step": "peer_adjustment", "status": "success", "message": "peer 调整完成。"},
            {"step": "historical_probability", "status": "success", "message": "历史概率完成。"},
            {"step": "final_decision", "status": "success", "message": "最终决策完成。"},
        ],
        "step_status": {
            "preflight": "success",
            "primary_analysis": "success",
            "peer_adjustment": "success",
            "historical_probability": "success",
            "final_decision": "success",
        },
    }
    base.update(overrides)
    return base


def _runner_with(v2: dict[str, Any]):
    def _runner(**_: object) -> dict[str, Any]:
        return v2
    return _runner


def _run(v2: dict[str, Any] | None = None, **kwargs) -> dict[str, Any]:
    return build_projection_v2_compat(
        symbol=kwargs.pop("symbol", "AVGO"),
        _v2_runner=_runner_with(v2 if v2 is not None else _v2_result()),
        **kwargs,
    )


class CautionLevelTests(unittest.TestCase):
    def test_zero_is_none(self):
        self.assertEqual(_caution_level(0), "none")

    def test_one_is_low(self):
        self.assertEqual(_caution_level(1), "low")

    def test_two_is_low(self):
        self.assertEqual(_caution_level(2), "low")

    def test_three_is_medium(self):
        self.assertEqual(_caution_level(3), "medium")

    def test_four_is_medium(self):
        self.assertEqual(_caution_level(4), "medium")

    def test_five_is_high(self):
        self.assertEqual(_caution_level(5), "high")


class AdapterSchemaTests(unittest.TestCase):
    def test_top_level_keys_present(self):
        result = _run()
        for key in (
            "kind",
            "projection_schema",
            "source_of_truth",
            "legacy_compat",
            "symbol",
            "ready",
            "advisory_only",
            "request",
            "notes",
            "advisory",
            "projection_report",
            "projection_v2_raw",
        ):
            self.assertIn(key, result, msg=f"missing top-level key: {key}")

    def test_kind_is_entrypoint_result(self):
        result = _run()
        self.assertEqual(result["kind"], "projection_entrypoint_result")

    def test_v2_raw_is_declared_source_of_truth(self):
        result = _run()
        self.assertEqual(result["projection_schema"], "v2")
        self.assertEqual(result["source_of_truth"], "projection_v2_raw")

    def test_legacy_compat_is_marked_as_fallback(self):
        result = _run()
        self.assertEqual(result["legacy_compat"]["kind"], "projection_v2_legacy_compat")
        self.assertEqual(result["legacy_compat"]["projection_report"], "legacy_fallback")
        self.assertEqual(result["legacy_compat"]["advisory"], "legacy_fallback")

    def test_advisory_only_is_false(self):
        self.assertFalse(_run()["advisory_only"])

    def test_notes_is_list_of_strings(self):
        notes = _run()["notes"]
        self.assertIsInstance(notes, list)
        self.assertTrue(all(isinstance(n, str) for n in notes))

    def test_projection_report_kind(self):
        self.assertEqual(_run()["projection_report"]["kind"], "final_projection_report")

    def test_readable_summary_kind(self):
        rs = _run()["projection_report"]["readable_summary"]
        self.assertEqual(rs["kind"], "predict_readable_summary")

    def test_report_text_contains_direction_marker(self):
        self.assertIn("明日方向：", _run()["projection_report"]["report_text"])

    def test_report_text_contains_basis_marker(self):
        self.assertIn("明日基准判断：", _run()["projection_report"]["report_text"])

    def test_advisory_keys_present(self):
        advisory = _run()["advisory"]
        for key in ("matched_count", "caution_level", "reminder_lines", "ready"):
            self.assertIn(key, advisory, msg=f"advisory missing key: {key}")


class AdapterMappingTests(unittest.TestCase):
    def test_build_projection_entrypoint_result_packages_existing_v2_raw(self):
        v2 = _v2_result()
        result = build_projection_entrypoint_result(v2_raw=v2, symbol="avgo")
        self.assertEqual(result["projection_v2_raw"], v2)
        self.assertEqual(result["source_of_truth"], "projection_v2_raw")

    def test_advisory_matched_count_from_preflight(self):
        v2 = _v2_result()
        v2["preflight"]["matched_rules"] = [
            {"rule_id": "m1", "category": "wrong_direction", "severity": "high", "message": "提醒1。"},
            {"rule_id": "m2", "category": "false_confidence", "severity": "high", "message": "提醒2。"},
        ]
        v2["preflight"]["rule_warnings"] = ["提醒1。", "提醒2。"]
        result = _run(v2)
        self.assertEqual(result["advisory"]["matched_count"], 2)
        self.assertEqual(result["advisory"]["caution_level"], "low")
        self.assertEqual(result["advisory"]["reminder_lines"], ["提醒1。", "提醒2。"])

    def test_advisory_matched_count_zero_when_no_rules(self):
        result = _run()
        self.assertEqual(result["advisory"]["matched_count"], 0)
        self.assertEqual(result["advisory"]["caution_level"], "none")
        self.assertEqual(result["advisory"]["reminder_lines"], [])

    def test_direction_from_final_decision(self):
        v2 = _v2_result()
        v2["final_decision"]["final_direction"] = "偏空"
        result = _run(v2)
        self.assertEqual(result["projection_report"]["direction"], "偏空")
        self.assertIn("偏空", result["projection_report"]["report_text"])

    def test_confidence_from_final_decision(self):
        v2 = _v2_result()
        v2["final_decision"]["final_confidence"] = "high"
        result = _run(v2)
        self.assertEqual(result["projection_report"]["confidence"], "high")

    def test_request_dict_preserves_all_params(self):
        result = build_projection_v2_compat(
            symbol="avgo",
            error_category="wrong-direction",
            limit=3,
            lookback_days=10,
            _v2_runner=_runner_with(_v2_result()),
        )
        self.assertEqual(result["request"], {
            "symbol": "AVGO",
            "error_category": "wrong-direction",
            "limit": 3,
            "lookback_days": 10,
        })

    def test_symbol_normalized_to_upper(self):
        result = _run(symbol="avgo")
        self.assertEqual(result["symbol"], "AVGO")

    def test_blank_symbol_raises(self):
        with self.assertRaises(ValueError):
            _run(symbol=" ")

    def test_ready_propagated_from_v2(self):
        v2 = _v2_result()
        v2["ready"] = False
        self.assertFalse(_run(v2)["ready"])

    def test_degraded_path_projection_report_is_not_blank(self):
        v2 = _v2_result()
        v2["ready"] = False
        v2["final_decision"]["ready"] = False
        v2["final_decision"]["final_direction"] = "unknown"
        v2["final_decision"]["final_confidence"] = "unknown"
        result = _run(v2)
        self.assertFalse(result["ready"])
        report = result["projection_report"]
        self.assertEqual(report["kind"], "final_projection_report")
        self.assertIn("明日方向：", report["report_text"])
        self.assertIn("明日基准判断：", report["report_text"])
        self.assertEqual(report["readable_summary"]["kind"], "predict_readable_summary")

    def test_projection_v2_raw_is_full_v2(self):
        v2 = _v2_result()
        result = _run(v2)
        self.assertEqual(result["projection_v2_raw"]["kind"], "projection_v2_report")

    def test_basis_summary_contains_lookback(self):
        v2 = _v2_result()
        v2["primary_analysis"]["basis"] = []
        v2["final_decision"]["decision_factors"] = []
        result = _run(v2)
        self.assertTrue(any("最近" in b for b in result["projection_report"]["basis_summary"]))

    def test_risk_reminders_include_rule_warnings(self):
        v2 = _v2_result()
        v2["preflight"]["rule_warnings"] = ["历史提醒：方向错误。"]
        result = _run(v2)
        self.assertIn("历史提醒：方向错误。", result["projection_report"]["risk_reminders"])

    def test_evidence_trace_has_final_conclusion(self):
        result = _run()
        trace = result["projection_report"]["evidence_trace"]
        self.assertIn("final_conclusion", trace)
        self.assertEqual(trace["final_conclusion"]["direction"], "偏多")

    def test_evidence_trace_tool_trace_has_step_info(self):
        result = _run()
        tool_trace = result["projection_report"]["evidence_trace"]["tool_trace"]
        self.assertIsInstance(tool_trace, list)
        self.assertTrue(any("preflight" in item for item in tool_trace))


if __name__ == "__main__":
    unittest.main()
