from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.active_rule_pool import build_active_rule_pool_report


def _lifecycle_rule(
    *,
    rule_key: str = "wrong_direction::primary",
    title: str = "历史复盘提醒：primary 方向错误",
    category: str = "wrong_direction",
    lifecycle_state: str = "watchlist",
    recommended_action: str = "keep_observing",
    hit_count: int = 3,
    net_score: float = 0.0,
    effectiveness_rate: float | None = 0.3333,
    harm_rate: float | None = 0.3333,
) -> dict:
    return {
        "rule_key": rule_key,
        "title": title,
        "category": category,
        "lifecycle_state": lifecycle_state,
        "recommended_action": recommended_action,
        "hit_count": hit_count,
        "net_score": net_score,
        "effectiveness_rate": effectiveness_rate,
        "harm_rate": harm_rate,
    }


class ActiveRulePoolTests(unittest.TestCase):
    def test_happy_path_returns_complete_shape_and_counts(self) -> None:
        report = build_active_rule_pool_report(
            lifecycle_report={
                "kind": "rule_lifecycle_report",
                "ready": True,
                "rules": [
                    _lifecycle_rule(rule_key="include", title="晋升规则", lifecycle_state="promoted_active", recommended_action="promote", hit_count=6, net_score=4.0, effectiveness_rate=0.8, harm_rate=0.2),
                    _lifecycle_rule(rule_key="hold", title="观察规则", lifecycle_state="watchlist", recommended_action="keep_observing", hit_count=3, net_score=1.0, effectiveness_rate=0.6, harm_rate=0.3),
                    _lifecycle_rule(rule_key="exclude", title="淘汰规则", lifecycle_state="retired", recommended_action="retire", hit_count=6, net_score=-3.0, effectiveness_rate=0.2, harm_rate=0.7),
                ],
            }
        )

        self.assertEqual(report["kind"], "active_rule_pool_report")
        self.assertTrue(report["ready"])
        self.assertEqual(report["total_rules"], 3)
        self.assertEqual(report["pool_counts"]["include"], 1)
        self.assertEqual(report["pool_counts"]["hold"], 1)
        self.assertEqual(report["pool_counts"]["exclude"], 1)

    def test_include_hold_exclude_mapping_is_consistent(self) -> None:
        report = build_active_rule_pool_report(
            rules=[
                _lifecycle_rule(rule_key="include", title="晋升规则", lifecycle_state="promoted_active", recommended_action="promote", hit_count=5, net_score=3.0, effectiveness_rate=0.8, harm_rate=0.2),
                _lifecycle_rule(rule_key="candidate", title="候选规则", lifecycle_state="candidate", recommended_action="keep_observing", hit_count=2, net_score=0.0, effectiveness_rate=0.5, harm_rate=0.2),
                _lifecycle_rule(rule_key="watchlist", title="观察规则", lifecycle_state="watchlist", recommended_action="keep_observing", hit_count=3, net_score=1.0, effectiveness_rate=0.6, harm_rate=0.3),
                _lifecycle_rule(rule_key="weakened", title="弱化规则", lifecycle_state="weakened", recommended_action="weaken", hit_count=4, net_score=0.5, effectiveness_rate=0.5, harm_rate=0.3),
                _lifecycle_rule(rule_key="retired", title="淘汰规则", lifecycle_state="retired", recommended_action="retire", hit_count=5, net_score=-2.0, effectiveness_rate=0.2, harm_rate=0.7),
            ]
        )

        by_key = {row["rule_key"]: row for row in report["rules"]}
        self.assertEqual(by_key["include"]["pool_decision"], "include")
        self.assertEqual(by_key["candidate"]["pool_decision"], "hold")
        self.assertEqual(by_key["watchlist"]["pool_decision"], "hold")
        self.assertEqual(by_key["weakened"]["pool_decision"], "exclude")
        self.assertEqual(by_key["retired"]["pool_decision"], "exclude")

    def test_pool_decision_and_rationale_match_lifecycle_state(self) -> None:
        report = build_active_rule_pool_report(
            rules=[
                _lifecycle_rule(rule_key="include", title="晋升规则", lifecycle_state="promoted_active", recommended_action="promote", hit_count=5, net_score=3.0, effectiveness_rate=0.8, harm_rate=0.2),
                _lifecycle_rule(rule_key="hold", title="观察规则", lifecycle_state="watchlist", recommended_action="keep_observing", hit_count=3, net_score=1.0, effectiveness_rate=0.6, harm_rate=0.3),
                _lifecycle_rule(rule_key="exclude", title="淘汰规则", lifecycle_state="retired", recommended_action="retire", hit_count=5, net_score=-2.0, effectiveness_rate=0.2, harm_rate=0.7),
            ]
        )

        by_key = {row["rule_key"]: row for row in report["rules"]}
        self.assertIn("纳入 active pool 候选", by_key["include"]["pool_rationale"])
        self.assertIn("继续观察", by_key["hold"]["pool_rationale"])
        self.assertIn("明确排除", by_key["exclude"]["pool_rationale"])

    def test_missing_lifecycle_input_degrades_with_stable_shape(self) -> None:
        report = build_active_rule_pool_report(lifecycle_report=None, rules=None)

        self.assertFalse(report["ready"])
        self.assertEqual(report["total_rules"], 0)
        self.assertEqual(
            sorted(report.keys()),
            sorted(
                [
                    "kind",
                    "ready",
                    "total_rules",
                    "pool_counts",
                    "rules",
                    "active_pool_candidates",
                    "holdout_rules",
                    "excluded_rules",
                    "summary",
                    "warnings",
                ]
            ),
        )
        self.assertTrue(report["warnings"])

    def test_empty_rules_and_partial_fields_are_conservative(self) -> None:
        empty_report = build_active_rule_pool_report(lifecycle_report={"kind": "rule_lifecycle_report", "rules": []})
        self.assertTrue(empty_report["ready"])
        self.assertEqual(empty_report["total_rules"], 0)
        self.assertIn("active pool 推荐结果为空", empty_report["summary"])

        partial_report = build_active_rule_pool_report(
            rules=[
                {"title": "字段残缺规则"},
                None,
            ]
        )
        self.assertTrue(partial_report["ready"])
        self.assertEqual(partial_report["total_rules"], 1)
        self.assertIn(partial_report["rules"][0]["pool_decision"], {"hold", "exclude"})
        self.assertTrue(partial_report["warnings"])

    def test_summary_and_grouped_lists_match_pool_counts(self) -> None:
        report = build_active_rule_pool_report(
            rules=[
                _lifecycle_rule(rule_key="include", title="晋升规则", lifecycle_state="promoted_active", recommended_action="promote", hit_count=5, net_score=3.0, effectiveness_rate=0.8, harm_rate=0.2),
                _lifecycle_rule(rule_key="hold", title="观察规则", lifecycle_state="watchlist", recommended_action="keep_observing", hit_count=3, net_score=1.0, effectiveness_rate=0.6, harm_rate=0.3),
                _lifecycle_rule(rule_key="exclude", title="淘汰规则", lifecycle_state="retired", recommended_action="retire", hit_count=5, net_score=-2.0, effectiveness_rate=0.2, harm_rate=0.7),
                _lifecycle_rule(rule_key="weakened", title="弱化规则", lifecycle_state="weakened", recommended_action="weaken", hit_count=4, net_score=0.5, effectiveness_rate=0.5, harm_rate=0.3),
            ]
        )

        self.assertEqual(len(report["active_pool_candidates"]), report["pool_counts"]["include"])
        self.assertEqual(len(report["holdout_rules"]), report["pool_counts"]["hold"])
        self.assertEqual(len(report["excluded_rules"]), report["pool_counts"]["exclude"])
        self.assertIn("include=1", report["summary"])
        self.assertIn("hold=1", report["summary"])
        self.assertIn("exclude=2", report["summary"])


if __name__ == "__main__":
    unittest.main()
