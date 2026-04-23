from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.rule_lifecycle import build_rule_lifecycle_report


def _scored_rule(
    *,
    rule_key: str = "wrong_direction::primary",
    title: str = "历史复盘提醒：primary 方向错误",
    category: str = "wrong_direction",
    hit_count: int = 3,
    effective_count: int = 1,
    harmful_count: int = 1,
    neutral_count: int = 1,
    effectiveness_rate: float | None = 0.3333,
    harm_rate: float | None = 0.3333,
    net_score: float = 0.0,
    recommended_status: str = "watchlist",
) -> dict:
    return {
        "rule_key": rule_key,
        "title": title,
        "category": category,
        "hit_count": hit_count,
        "effective_count": effective_count,
        "harmful_count": harmful_count,
        "neutral_count": neutral_count,
        "effectiveness_rate": effectiveness_rate,
        "harm_rate": harm_rate,
        "net_score": net_score,
        "recommended_status": recommended_status,
    }


class RuleLifecycleTests(unittest.TestCase):
    def test_happy_path_returns_complete_shape_and_counts(self) -> None:
        report = build_rule_lifecycle_report(
            rule_score_report={
                "kind": "rule_score_report",
                "ready": True,
                "rules": [
                    _scored_rule(hit_count=2, recommended_status="candidate"),
                    _scored_rule(
                        rule_key="false_confidence::rule-a",
                        title="规则A",
                        category="false_confidence",
                        hit_count=6,
                        effective_count=5,
                        harmful_count=1,
                        neutral_count=0,
                        effectiveness_rate=0.8333,
                        harm_rate=0.1667,
                        net_score=4.0,
                        recommended_status="promising",
                    ),
                    _scored_rule(
                        rule_key="wrong_direction::rule-b",
                        title="规则B",
                        category="wrong_direction",
                        hit_count=6,
                        effective_count=1,
                        harmful_count=4,
                        neutral_count=1,
                        effectiveness_rate=0.1667,
                        harm_rate=0.6667,
                        net_score=-3.0,
                        recommended_status="risky",
                    ),
                ],
            }
        )

        self.assertEqual(report["kind"], "rule_lifecycle_report")
        self.assertTrue(report["ready"])
        self.assertEqual(report["total_rules"], 3)
        self.assertEqual(report["state_counts"]["candidate"], 1)
        self.assertEqual(report["state_counts"]["promoted_active"], 1)
        self.assertEqual(report["state_counts"]["retired"], 1)

    def test_each_lifecycle_state_is_classified_correctly(self) -> None:
        report = build_rule_lifecycle_report(
            rules=[
                _scored_rule(rule_key="candidate", title="候选规则", hit_count=2, recommended_status="candidate"),
                _scored_rule(rule_key="watchlist", title="观察规则", hit_count=3, effective_count=2, harmful_count=1, neutral_count=0, effectiveness_rate=0.6667, harm_rate=0.3333, net_score=1.0, recommended_status="watchlist"),
                _scored_rule(rule_key="active", title="晋升规则", hit_count=5, effective_count=4, harmful_count=1, neutral_count=0, effectiveness_rate=0.8, harm_rate=0.2, net_score=3.0, recommended_status="promising"),
                _scored_rule(rule_key="weakened", title="弱化规则", hit_count=4, effective_count=2, harmful_count=1, neutral_count=1, effectiveness_rate=0.5, harm_rate=0.25, net_score=1.0, recommended_status="promising"),
                _scored_rule(rule_key="retired", title="淘汰规则", hit_count=5, effective_count=1, harmful_count=3, neutral_count=1, effectiveness_rate=0.2, harm_rate=0.6, net_score=-2.0, recommended_status="risky"),
            ]
        )

        by_key = {row["rule_key"]: row for row in report["rules"]}
        self.assertEqual(by_key["candidate"]["lifecycle_state"], "candidate")
        self.assertEqual(by_key["watchlist"]["lifecycle_state"], "watchlist")
        self.assertEqual(by_key["active"]["lifecycle_state"], "promoted_active")
        self.assertEqual(by_key["weakened"]["lifecycle_state"], "weakened")
        self.assertEqual(by_key["retired"]["lifecycle_state"], "retired")

    def test_rationale_and_actions_match_rule_statistics(self) -> None:
        report = build_rule_lifecycle_report(
            rules=[
                _scored_rule(rule_key="active", title="晋升规则", hit_count=5, effective_count=4, harmful_count=1, neutral_count=0, effectiveness_rate=0.8, harm_rate=0.2, net_score=3.0, recommended_status="promising"),
                _scored_rule(rule_key="retired", title="淘汰规则", hit_count=5, effective_count=1, harmful_count=4, neutral_count=0, effectiveness_rate=0.2, harm_rate=0.8, net_score=-3.0, recommended_status="risky"),
            ]
        )

        by_key = {row["rule_key"]: row for row in report["rules"]}
        self.assertEqual(by_key["active"]["recommended_action"], "promote")
        self.assertIn("建议晋升", by_key["active"]["rationale"])
        self.assertEqual(by_key["retired"]["recommended_action"], "retire")
        self.assertIn("建议淘汰", by_key["retired"]["rationale"])

    def test_missing_score_input_degrades_with_stable_shape(self) -> None:
        report = build_rule_lifecycle_report(rule_score_report=None, rules=None)

        self.assertFalse(report["ready"])
        self.assertEqual(report["total_rules"], 0)
        self.assertEqual(
            sorted(report.keys()),
            sorted(
                [
                    "kind",
                    "ready",
                    "total_rules",
                    "state_counts",
                    "rules",
                    "promoted_active_rules",
                    "retired_rules",
                    "weakened_rules",
                    "summary",
                    "warnings",
                ]
            ),
        )
        self.assertTrue(report["warnings"])

    def test_empty_rules_and_partial_fields_are_conservative(self) -> None:
        empty_report = build_rule_lifecycle_report(rule_score_report={"kind": "rule_score_report", "rules": []})
        self.assertTrue(empty_report["ready"])
        self.assertEqual(empty_report["total_rules"], 0)
        self.assertIn("没有可管理的规则评分记录", empty_report["summary"])

        partial_report = build_rule_lifecycle_report(
            rules=[
                {"title": "字段残缺规则"},
                None,
            ]
        )
        self.assertTrue(partial_report["ready"])
        self.assertEqual(partial_report["total_rules"], 1)
        self.assertEqual(partial_report["rules"][0]["lifecycle_state"], "candidate")
        self.assertEqual(partial_report["rules"][0]["recommended_action"], "keep_observing")
        self.assertTrue(partial_report["warnings"])

    def test_summary_and_grouped_lists_match_state_counts(self) -> None:
        report = build_rule_lifecycle_report(
            rules=[
                _scored_rule(rule_key="active", title="晋升规则", hit_count=5, effective_count=4, harmful_count=1, neutral_count=0, effectiveness_rate=0.8, harm_rate=0.2, net_score=3.0, recommended_status="promising"),
                _scored_rule(rule_key="weakened", title="弱化规则", hit_count=4, effective_count=2, harmful_count=1, neutral_count=1, effectiveness_rate=0.5, harm_rate=0.25, net_score=1.0, recommended_status="promising"),
                _scored_rule(rule_key="retired", title="淘汰规则", hit_count=5, effective_count=1, harmful_count=3, neutral_count=1, effectiveness_rate=0.2, harm_rate=0.6, net_score=-2.0, recommended_status="risky"),
            ]
        )

        self.assertEqual(len(report["promoted_active_rules"]), report["state_counts"]["promoted_active"])
        self.assertEqual(len(report["weakened_rules"]), report["state_counts"]["weakened"])
        self.assertEqual(len(report["retired_rules"]), report["state_counts"]["retired"])
        self.assertIn("promoted_active=1", report["summary"])
        self.assertIn("weakened=1", report["summary"])
        self.assertIn("retired=1", report["summary"])


if __name__ == "__main__":
    unittest.main()
