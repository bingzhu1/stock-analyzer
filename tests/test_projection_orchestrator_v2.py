from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.projection_orchestrator_v2 import run_projection_v2


def _legacy_result(
    *,
    advisory: dict | None = None,
    scan_result: dict | None = None,
    projection_report: dict | None = None,
) -> dict:
    return {
        "symbol": "AVGO",
        "request": {"symbol": "AVGO", "lookback_days": 20},
        "advisory": advisory if advisory is not None else {
            "matched_count": 1,
            "caution_level": "low",
            "reminder_lines": ["历史提醒：等待确认。"],
            "ready": True,
        },
        "projection_report": projection_report if projection_report is not None else {
            "kind": "final_projection_report",
            "target_date": "2026-04-21",
            "direction": "偏多",
            "open_tendency": "平开",
            "close_tendency": "偏强",
            "confidence": "medium",
            "basis_summary": ["主分析依据。"],
            "risk_reminders": ["风险提醒。"],
            "report_text": "明日基准判断：偏多。",
            "readable_summary": {
                "baseline_judgment": {"risk_level": "中"},
            },
        },
        "predict_result": {"final_bias": "bullish", "final_confidence": "medium"},
        "scan_result": scan_result if scan_result is not None else {
            "confirmation_state": "confirmed",
            "relative_strength_5d_summary": {
                "vs_nvda": "stronger",
                "vs_soxx": "neutral",
                "vs_qqq": "stronger",
            },
            "relative_strength_same_day_summary": {
                "vs_nvda": "stronger",
                "vs_soxx": "neutral",
                "vs_qqq": "neutral",
            },
            "historical_match_summary": {
                "exact_match_count": 2,
                "near_match_count": 4,
                "dominant_historical_outcome": "up_bias",
            },
        },
        "ready": True,
    }


def _runner_with(payload: dict):
    def _runner(**_: object) -> dict:
        return payload
    return _runner


def _primary_result(**overrides) -> dict:
    result = {
        "kind": "primary_20day_analysis",
        "symbol": "AVGO",
        "lookback_days": 20,
        "target_date": "2026-04-21",
        "ready": True,
        "direction": "偏多",
        "confidence": "medium",
        "position_label": "高位",
        "stage_label": "延续",
        "volume_state": "正常",
        "summary": "AVGO 最近20天主分析：方向偏多。",
        "basis": ["最近5日收益为 +3.00%。", "主分析方向信号归纳为偏多。"],
        "warnings": [],
        "features": {
            "latest_close": 120.0,
            "ret_5d": 3.0,
            "ret_10d": 5.0,
            "pos_20d": 80.0,
            "high_20d": 121.0,
            "low_20d": 100.0,
            "vol_ratio_5d": 1.0,
            "days_used": 20,
        },
    }
    result.update(overrides)
    return result


def _primary_builder(result: dict | None = None):
    def _builder(**_: object) -> dict:
        return result or _primary_result()
    return _builder


def _noop_preflight(**_) -> dict:
    return {
        "kind": "projection_rule_preflight",
        "symbol": "AVGO",
        "target_date": None,
        "lookback_days": 20,
        "ready": True,
        "matched_rules": [],
        "rule_warnings": [],
        "rule_adjustments": [],
        "summary": "未命中历史规则。",
        "warnings": [],
        "source_counts": {"memory_items": 0, "review_items": 0, "matched_rule_count": 0},
    }


def _preflight_with_rules(rules: list[dict]) -> object:
    def _builder(**_) -> dict:
        return {
            "kind": "projection_rule_preflight",
            "symbol": "AVGO",
            "target_date": None,
            "lookback_days": 20,
            "ready": True,
            "matched_rules": rules,
            "rule_warnings": [r["message"] for r in rules],
            "rule_adjustments": ["复核主方向。"] * len(rules),
            "summary": f"命中 {len(rules)} 条历史规则提醒。",
            "warnings": [],
            "source_counts": {
                "memory_items": len(rules),
                "review_items": 0,
                "matched_rule_count": len(rules),
            },
        }
    return _builder


def _run(payload: dict, preflight_builder=None) -> dict:
    return run_projection_v2(
        _projection_runner=_runner_with(payload),
        _primary_analysis_builder=_primary_builder(),
        _rule_preflight_builder=preflight_builder if preflight_builder is not None else _noop_preflight,
    )


class ProjectionOrchestratorV2Tests(unittest.TestCase):
    def test_happy_path_returns_fixed_report_shape(self) -> None:
        result = _run(_legacy_result())

        self.assertEqual(result["kind"], "projection_v2_report")
        self.assertEqual(result["symbol"], "AVGO")
        self.assertTrue(result["ready"])
        for key in (
            "feature_payload",
            "exclusion_result",
            "main_projection",
            "consistency",
            "historical_match_result",
            "primary_choice",
            "secondary_choice",
            "least_likely",
            "prediction_log_id",
        ):
            self.assertIn(key, result)
        self.assertIsNone(result["prediction_log_id"])
        for key in (
            "preflight",
            "primary_analysis",
            "peer_adjustment",
            "historical_probability",
            "final_decision",
        ):
            self.assertIn(key, result)
            self.assertEqual(result["step_status"][key], "success")
        self.assertEqual(result["final_decision"]["kind"], "final_decision")
        self.assertEqual(result["final_decision"]["final_direction"], "偏多")
        self.assertEqual(result["final_decision"]["final_confidence"], "high")
        self.assertEqual(result["final_decision"]["direction"], "偏多")
        self.assertIn("layer_contributions", result["final_decision"])
        self.assertIn("why_not_more_bullish_or_bearish", result["final_decision"])
        self.assertEqual(
            result["final_decision"]["source_snapshot"]["peer_adjustment"],
            "reinforce_bullish",
        )
        self.assertEqual(
            result["final_decision"]["source_snapshot"]["historical_bias"],
            "supports_bullish",
        )
        self.assertEqual(result["peer_adjustment"]["kind"], "peer_adjustment")
        self.assertEqual(result["peer_adjustment"]["adjustment"], "reinforce_bullish")
        self.assertEqual(result["peer_adjustment"]["adjusted_direction"], "偏多")
        self.assertEqual(result["peer_adjustment"]["adjusted_confidence"], "high")
        self.assertEqual(result["historical_probability"]["kind"], "historical_probability")
        self.assertEqual(result["historical_probability"]["sample_count"], 6)
        self.assertEqual(result["historical_probability"]["sample_quality"], "limited")
        self.assertEqual(result["historical_probability"]["historical_bias"], "supports_bullish")
        self.assertEqual(result["historical_probability"]["impact"], "support")
        self.assertIn("主分析", result["final_decision"]["summary"])
        self.assertIn("peer 修正", result["final_decision"]["summary"])
        self.assertIn("历史概率", result["final_decision"]["summary"])
        self.assertIn("predicted_top1", result["main_projection"])
        self.assertIn("consistency_flag", result["consistency"])

    def test_peer_step_degrades_when_peer_data_missing(self) -> None:
        payload = _legacy_result(scan_result={
            "historical_match_summary": {
                "exact_match_count": 3,
                "near_match_count": 2,
                "dominant_historical_outcome": "mixed",
            },
        })

        result = _run(payload)

        self.assertTrue(result["ready"])
        self.assertEqual(result["step_status"]["peer_adjustment"], "skipped")
        self.assertEqual(result["peer_adjustment"]["kind"], "peer_adjustment")
        self.assertEqual(result["peer_adjustment"]["confirmation_level"], "missing")
        self.assertEqual(result["peer_adjustment"]["adjustment"], "missing")
        self.assertEqual(result["peer_adjustment"]["adjusted_direction"], "偏多")
        self.assertTrue(any("peer_adjustment 缺少" in w for w in result["warnings"]))
        self.assertIn("未获 peers 确认", result["final_decision"]["summary"])

    def test_peer_step_degrades_when_confirmation_is_mixed_but_all_peers_unavailable(self) -> None:
        payload = _legacy_result(scan_result={
            "confirmation_state": "mixed",
            "relative_strength_5d_summary": {
                "vs_nvda": "unavailable",
                "vs_soxx": "unavailable",
                "vs_qqq": "unavailable",
            },
            "relative_strength_same_day_summary": {
                "vs_nvda": "unavailable",
                "vs_soxx": "unavailable",
                "vs_qqq": "unavailable",
            },
            "historical_match_summary": {
                "exact_match_count": 3,
                "near_match_count": 2,
                "dominant_historical_outcome": "mixed",
            },
        })

        result = _run(payload)

        self.assertTrue(result["ready"])
        self.assertEqual(result["step_status"]["peer_adjustment"], "skipped")
        self.assertTrue(any("peer_adjustment 缺少" in w for w in result["warnings"]))
        self.assertIn("未获 peers 确认", result["final_decision"]["summary"])

    def test_historical_probability_degrades_when_missing(self) -> None:
        payload = _legacy_result(scan_result={
            "confirmation_state": "mixed",
            "relative_strength_5d_summary": {"vs_nvda": "neutral"},
            "relative_strength_same_day_summary": {"vs_nvda": "neutral"},
        })

        result = _run(payload)

        self.assertTrue(result["ready"])
        self.assertEqual(result["step_status"]["historical_probability"], "skipped")
        self.assertEqual(result["historical_probability"]["kind"], "historical_probability")
        self.assertEqual(result["historical_probability"]["sample_count"], 0)
        self.assertEqual(result["historical_probability"]["sample_quality"], "missing")
        self.assertEqual(result["historical_probability"]["historical_bias"], "missing")
        self.assertEqual(result["historical_probability"]["impact"], "missing")
        self.assertIsNone(result["historical_probability"]["up_rate"])
        self.assertIsNone(result["historical_probability"]["down_rate"])
        self.assertTrue(any("historical_probability" in w for w in result["warnings"]))
        self.assertIn("未获得历史概率支持", result["final_decision"]["summary"])

    def test_historical_probability_builder_receives_target_date_as_as_of_date(self) -> None:
        payload = _legacy_result(scan_result={
            "confirmation_state": "confirmed",
            "relative_strength_5d_summary": {"vs_nvda": "stronger"},
            "relative_strength_same_day_summary": {"vs_nvda": "stronger"},
            "historical_match_summary": {
                "exact_match_count": 2,
                "near_match_count": 4,
                "dominant_historical_outcome": "up_bias",
            },
            "coded_history": "coded-marker",
            "feature_history": "feature-marker",
        })
        captured: dict[str, object] = {}

        def _historical_builder(**kwargs: object) -> dict:
            captured.update(kwargs)
            return {
                "kind": "historical_probability",
                "symbol": "AVGO",
                "ready": True,
                "sample_count": 6,
                "sample_quality": "limited",
                "up_rate": 0.6,
                "down_rate": 0.4,
                "gap_up_rate": None,
                "strong_close_rate": None,
                "historical_bias": "supports_bullish",
                "impact": "support",
                "code_match": {
                    "sample_count": 3,
                    "up_rate": 0.6667,
                    "down_rate": 0.3333,
                    "summary": "code ok",
                },
                "window_similarity": {
                    "sample_count": 3,
                    "up_rate": 0.5,
                    "down_rate": 0.5,
                    "avg_similarity": 0.9,
                    "summary": "window ok",
                },
                "combined_probability": {
                    "up_rate": 0.6,
                    "down_rate": 0.4,
                    "gap_up_rate": None,
                    "strong_close_rate": None,
                    "method": "blended",
                },
                "summary": "historical ok",
                "basis": [],
                "warnings": [],
                "source_summary": kwargs.get("historical_summary") or {},
            }

        result = run_projection_v2(
            target_date="2026-04-21",
            _projection_runner=_runner_with(payload),
            _primary_analysis_builder=_primary_builder(),
            _historical_probability_builder=_historical_builder,
            _rule_preflight_builder=_noop_preflight,
        )

        self.assertTrue(result["ready"])
        self.assertEqual(captured["as_of_date"], "2026-04-21")
        self.assertEqual(captured["coded_history"], "coded-marker")
        self.assertEqual(captured["feature_history"], "feature-marker")

    def test_primary_analysis_failure_does_not_fake_final_decision(self) -> None:
        def bad_runner(**_: object) -> dict:
            raise RuntimeError("legacy projection unavailable")

        result = run_projection_v2(_projection_runner=bad_runner)

        self.assertFalse(result["ready"])
        self.assertEqual(result["step_status"]["primary_analysis"], "failed")
        self.assertEqual(result["step_status"]["final_decision"], "failed")
        self.assertEqual(result["final_decision"]["kind"], "final_decision")
        self.assertFalse(result["final_decision"]["ready"])
        self.assertEqual(result["final_decision"]["final_direction"], "unknown")
        self.assertEqual(result["final_decision"]["final_confidence"], "unknown")
        self.assertIn("不能伪造完整结论", result["final_decision"]["summary"])
        self.assertTrue(any("legacy projection unavailable" in w for w in result["warnings"]))

    def test_trace_contains_all_steps_in_order(self) -> None:
        result = _run(_legacy_result())

        self.assertEqual(
            [item["step"] for item in result["trace"]],
            [
                "preflight",
                "primary_analysis",
                "peer_adjustment",
                "historical_probability",
                "final_decision",
            ],
        )
        self.assertTrue(all(item["message"] for item in result["trace"]))

    def test_preflight_exception_is_skipped_without_blocking_primary(self) -> None:
        def _failing_preflight(**_):
            raise RuntimeError("preflight 数据源不可用")

        result = _run(_legacy_result(), preflight_builder=_failing_preflight)

        self.assertTrue(result["ready"])
        self.assertEqual(result["step_status"]["preflight"], "skipped")
        self.assertEqual(result["preflight"]["matched_rules"], [])
        self.assertTrue(any("preflight 失败" in w for w in result["warnings"]))

    def test_preflight_ready_false_is_skipped_without_blocking_primary(self) -> None:
        def _not_ready(**_):
            return {
                "ready": False,
                "matched_rules": [],
                "rule_warnings": [],
                "rule_adjustments": [],
                "summary": "preflight 降级：数据源未就绪。",
                "warnings": ["preflight 未接入历史规则。"],
                "source_counts": {"memory_items": 0, "review_items": 0, "matched_rule_count": 0},
            }

        result = _run(_legacy_result(), preflight_builder=_not_ready)

        self.assertTrue(result["ready"])
        self.assertEqual(result["step_status"]["preflight"], "skipped")
        self.assertEqual(result["preflight"]["matched_rules"], [])

    def test_step0_preflight_rules_appear_in_output(self) -> None:
        rule = {
            "rule_id": "memory-1",
            "title": "历史记忆提醒：wrong_direction",
            "category": "wrong_direction",
            "severity": "high",
            "message": "历史提醒：上次方向判断有误。",
        }
        result = _run(_legacy_result(), preflight_builder=_preflight_with_rules([rule]))

        self.assertEqual(result["step_status"]["preflight"], "success")
        self.assertEqual(len(result["preflight"]["matched_rules"]), 1)
        self.assertEqual(result["preflight"]["matched_rules"][0]["rule_id"], "memory-1")
        self.assertEqual(result["preflight"]["matched_rules"][0]["category"], "wrong_direction")
        self.assertIn("rule_adjustments", result["preflight"])
        self.assertIn("source_counts", result["preflight"])

    def test_step0_preflight_source_counts_propagated(self) -> None:
        rule = {
            "rule_id": "r1",
            "title": "提醒",
            "category": "false_confidence",
            "severity": "high",
            "message": "控制置信度。",
        }
        result = _run(_legacy_result(), preflight_builder=_preflight_with_rules([rule]))

        sc = result["preflight"]["source_counts"]
        self.assertIn("memory_items", sc)
        self.assertIn("review_items", sc)
        self.assertIn("matched_rule_count", sc)
        self.assertEqual(sc["matched_rule_count"], 1)

    def test_f2_error_path_preflight_has_full_contract_fields(self) -> None:
        # Regression for F2: when _projection_runner raises, the hardcoded preflight
        # must contain all contract fields (not a truncated 3-key dict).
        def bad_runner(**_: object) -> dict:
            raise RuntimeError("runner down")

        result = run_projection_v2(_projection_runner=bad_runner)

        preflight = result["preflight"]
        for field in ("kind", "ready", "matched_rules", "rule_warnings",
                      "rule_adjustments", "summary", "warnings", "source_counts"):
            self.assertIn(field, preflight, msg=f"preflight missing field: {field}")
        self.assertEqual(preflight["kind"], "projection_rule_preflight")
        self.assertIsInstance(preflight["matched_rules"], list)
        self.assertIsInstance(preflight["rule_adjustments"], list)
        self.assertIsInstance(preflight["warnings"], list)
        self.assertIn("memory_items", preflight["source_counts"])


if __name__ == "__main__":
    unittest.main()
