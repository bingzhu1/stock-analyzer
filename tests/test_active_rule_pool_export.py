from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.active_rule_pool_export import build_active_rule_pool_export


def _pool_rule(
    *,
    rule_key: str = "wrong_direction::primary",
    title: str = "历史复盘提醒：primary 方向错误",
    category: str = "wrong_direction",
    lifecycle_state: str = "promoted_active",
    recommended_action: str = "promote",
    pool_decision: str = "include",
    pool_rationale: str = "生命周期状态为 promoted_active，且建议动作为 promote；当前规则已适合进入 active pool 候选。",
    hit_count: int = 5,
    net_score: float = 3.0,
    effectiveness_rate: float | None = 0.8,
    harm_rate: float | None = 0.2,
    severity: str | None = "high",
    message: str | None = "主分析方向错误，需要复核 primary 分析层的输入假设。",
    effect: str | None = "warn",
) -> dict:
    return {
        "rule_key": rule_key,
        "title": title,
        "category": category,
        "lifecycle_state": lifecycle_state,
        "recommended_action": recommended_action,
        "pool_decision": pool_decision,
        "pool_rationale": pool_rationale,
        "hit_count": hit_count,
        "net_score": net_score,
        "effectiveness_rate": effectiveness_rate,
        "harm_rate": harm_rate,
        "severity": severity,
        "message": message,
        "effect": effect,
    }


class ActiveRulePoolExportTests(unittest.TestCase):
    def test_happy_path_returns_complete_shape_and_bridge_rules(self) -> None:
        report = build_active_rule_pool_export(
            active_rule_pool_report={
                "kind": "active_rule_pool_report",
                "ready": True,
                "rules": [
                    _pool_rule(rule_key="include-1"),
                    _pool_rule(rule_key="hold-1", title="观察规则", pool_decision="hold", lifecycle_state="watchlist", recommended_action="keep_observing"),
                ],
            }
        )

        self.assertEqual(report["kind"], "active_rule_pool_export")
        self.assertTrue(report["ready"])
        self.assertEqual(report["total_input_rules"], 2)
        self.assertEqual(report["exported_rule_count"], 1)
        self.assertEqual(len(report["exported_rules"]), 1)
        self.assertEqual(len(report["preflight_bridge_rules"]), 1)

    def test_include_rules_export_and_hold_exclude_rules_are_filtered(self) -> None:
        report = build_active_rule_pool_export(
            rules=[
                _pool_rule(rule_key="include-1", title="晋升规则", pool_decision="include"),
                _pool_rule(rule_key="hold-1", title="观察规则", pool_decision="hold", lifecycle_state="watchlist", recommended_action="keep_observing"),
                _pool_rule(rule_key="exclude-1", title="淘汰规则", pool_decision="exclude", lifecycle_state="retired", recommended_action="retire"),
            ]
        )

        self.assertEqual(report["exported_rule_count"], 1)
        self.assertEqual(report["exported_rules"][0]["rule_key"], "include-1")
        self.assertEqual(len(report["excluded_from_export"]), 2)
        excluded_keys = {row["rule_key"] for row in report["excluded_from_export"]}
        self.assertEqual(excluded_keys, {"hold-1", "exclude-1"})

    def test_bridge_rule_id_is_deterministic_for_same_rule(self) -> None:
        report_one = build_active_rule_pool_export(
            rules=[_pool_rule(rule_key="same-rule", title="同一规则")],
            pool_name="pool-a",
        )
        report_two = build_active_rule_pool_export(
            rules=[_pool_rule(rule_key="same-rule", title="同一规则")],
            pool_name="pool-a",
        )

        self.assertEqual(
            report_one["preflight_bridge_rules"][0]["rule_id"],
            report_two["preflight_bridge_rules"][0]["rule_id"],
        )

    def test_missing_input_degrades_with_stable_shape(self) -> None:
        report = build_active_rule_pool_export(active_rule_pool_report=None, rules=None)

        self.assertFalse(report["ready"])
        self.assertEqual(report["exported_rule_count"], 0)
        self.assertEqual(
            sorted(report.keys()),
            sorted(
                [
                    "kind",
                    "ready",
                    "pool_name",
                    "version_tag",
                    "total_input_rules",
                    "exported_rule_count",
                    "exported_rules",
                    "excluded_from_export",
                    "preflight_bridge_rules",
                    "summary",
                    "warnings",
                ]
            ),
        )
        self.assertTrue(report["warnings"])

    def test_empty_rules_and_all_non_include_rules_return_readable_empty_export(self) -> None:
        empty_report = build_active_rule_pool_export(active_rule_pool_report={"kind": "active_rule_pool_report", "rules": []})
        self.assertTrue(empty_report["ready"])
        self.assertEqual(empty_report["exported_rule_count"], 0)
        self.assertIn("导出结果为空", empty_report["summary"])

        no_include_report = build_active_rule_pool_export(
            rules=[
                _pool_rule(rule_key="hold-1", title="观察规则", pool_decision="hold", lifecycle_state="watchlist", recommended_action="keep_observing"),
                _pool_rule(rule_key="exclude-1", title="淘汰规则", pool_decision="exclude", lifecycle_state="retired", recommended_action="retire"),
            ]
        )
        self.assertTrue(no_include_report["ready"])
        self.assertEqual(no_include_report["exported_rule_count"], 0)
        self.assertIn("当前无可导出的 include 规则", no_include_report["summary"])

    def test_partial_include_rule_fields_export_conservatively(self) -> None:
        report = build_active_rule_pool_export(
            rules=[
                {"pool_decision": "include", "rule_key": "partial"},
                None,
            ]
        )

        self.assertTrue(report["ready"])
        self.assertEqual(report["exported_rule_count"], 1)
        exported = report["exported_rules"][0]
        bridge = report["preflight_bridge_rules"][0]
        self.assertEqual(exported["severity"], "unknown")
        self.assertEqual(exported["effect"], "unknown")
        self.assertEqual(exported["message"], "unknown")
        self.assertEqual(bridge["rule_id"], build_active_rule_pool_export(rules=[{"pool_decision": "include", "rule_key": "partial"}])["preflight_bridge_rules"][0]["rule_id"])
        self.assertTrue(report["warnings"])


if __name__ == "__main__":
    unittest.main()
