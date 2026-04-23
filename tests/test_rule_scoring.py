from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.rule_scoring import build_rule_score_report


def _candidate(
    *,
    rule_id: str = "review-rc-1",
    title: str = "历史复盘提醒：primary 方向错误",
    category: str = "wrong_direction",
    message: str = "主分析方向错误，需要复核 primary 分析层的输入假设。",
) -> dict:
    return {
        "rule_id": rule_id,
        "title": title,
        "category": category,
        "severity": "high",
        "message": message,
    }


def _review(
    *,
    direction_correct: bool | None,
    error_category: str = "wrong_direction",
    rule_candidates: list[dict] | None = None,
) -> dict:
    return {
        "direction_correct": direction_correct,
        "error_category": error_category,
        "rule_candidates": rule_candidates or [],
    }


def _replay(
    *,
    as_of_date: str = "2026-03-01",
    prediction_for_date: str = "2026-03-02",
    review: dict | None = None,
) -> dict:
    return {
        "kind": "historical_replay_result",
        "symbol": "AVGO",
        "as_of_date": as_of_date,
        "prediction_for_date": prediction_for_date,
        "review": review or _review(direction_correct=False),
    }


class RuleScoringTests(unittest.TestCase):
    def test_happy_path_returns_stable_shape_and_counts(self) -> None:
        report = build_rule_score_report(
            replay_results=[
                _replay(review=_review(direction_correct=True, rule_candidates=[_candidate(rule_id="a1")])),
                _replay(review=_review(direction_correct=False, rule_candidates=[_candidate(rule_id="a2")])),
                _replay(
                    review=_review(
                        direction_correct=None,
                        error_category="unknown",
                        rule_candidates=[_candidate(rule_id="a3")],
                    )
                ),
            ]
        )

        self.assertEqual(report["kind"], "rule_score_report")
        self.assertTrue(report["ready"])
        self.assertEqual(report["total_reviews"], 3)
        self.assertEqual(report["total_rule_hits"], 3)
        self.assertEqual(len(report["rules"]), 1)
        rule = report["rules"][0]
        self.assertEqual(rule["hit_count"], 3)
        self.assertEqual(rule["effective_count"], 1)
        self.assertEqual(rule["harmful_count"], 1)
        self.assertEqual(rule["neutral_count"], 1)
        self.assertAlmostEqual(rule["effectiveness_rate"], 0.3333, places=4)
        self.assertAlmostEqual(rule["harm_rate"], 0.3333, places=4)
        self.assertEqual(rule["net_score"], 0.0)

    def test_title_plus_category_normalization_aggregates_different_rule_ids(self) -> None:
        report = build_rule_score_report(
            replay_results=[
                _replay(review=_review(direction_correct=True, rule_candidates=[_candidate(rule_id="a1")])),
                _replay(review=_review(direction_correct=False, rule_candidates=[_candidate(rule_id="a2")])),
                _replay(
                    review=_review(
                        direction_correct=False,
                        rule_candidates=[
                            _candidate(
                                rule_id="b1",
                                title="历史复盘提醒：historical 样本不足",
                                category="insufficient_data",
                                message="当 historical 样本不足时，不应把 final risk 设为 low。",
                            )
                        ],
                    )
                ),
            ]
        )

        self.assertEqual(len(report["rules"]), 2)
        merged = next(rule for rule in report["rules"] if rule["title"] == "历史复盘提醒：primary 方向错误")
        self.assertEqual(merged["hit_count"], 2)
        self.assertEqual(merged["effective_count"], 1)
        self.assertEqual(merged["harmful_count"], 1)

    def test_promising_and_risky_rules_are_ranked_and_explained(self) -> None:
        report = build_rule_score_report(
            replay_results=[
                _replay(review=_review(direction_correct=True, rule_candidates=[_candidate(rule_id="p1", title="规则A", category="false_confidence", message="规则A说明")])),
                _replay(review=_review(direction_correct=True, rule_candidates=[_candidate(rule_id="p2", title="规则A", category="false_confidence", message="规则A说明")])),
                _replay(review=_review(direction_correct=True, rule_candidates=[_candidate(rule_id="p3", title="规则A", category="false_confidence", message="规则A说明")])),
                _replay(review=_review(direction_correct=False, rule_candidates=[_candidate(rule_id="r1", title="规则B", category="wrong_direction", message="规则B说明")])),
                _replay(review=_review(direction_correct=False, rule_candidates=[_candidate(rule_id="r2", title="规则B", category="wrong_direction", message="规则B说明")])),
            ]
        )

        self.assertEqual(report["top_promising_rules"][0]["title"], "规则A")
        self.assertEqual(report["top_promising_rules"][0]["recommended_status"], "promising")
        self.assertEqual(report["top_risky_rules"][0]["title"], "规则B")
        self.assertEqual(report["top_risky_rules"][0]["recommended_status"], "risky")
        self.assertTrue(report["summary"])
        self.assertIn("promising=1", report["summary"])
        self.assertIn("risky=1", report["summary"])
        self.assertTrue(report["top_promising_rules"][0]["notes"])
        self.assertTrue(report["top_risky_rules"][0]["notes"])

    def test_missing_inputs_degrade_with_stable_shape(self) -> None:
        report = build_rule_score_report(replay_results=None, reviews=None)

        self.assertFalse(report["ready"])
        self.assertEqual(report["total_reviews"], 0)
        self.assertEqual(
            sorted(report.keys()),
            sorted(
                [
                    "kind",
                    "ready",
                    "total_reviews",
                    "total_rule_hits",
                    "rules",
                    "top_promising_rules",
                    "top_risky_rules",
                    "summary",
                    "warnings",
                ]
            ),
        )
        self.assertTrue(report["warnings"])

    def test_partial_fields_and_malformed_candidates_do_not_crash(self) -> None:
        report = build_rule_score_report(
            replay_results=[
                {"kind": "historical_replay_result", "review": {"rule_candidates": [None, {}, _candidate(rule_id="x1")]}}
            ],
            reviews=[
                {"direction_correct": None, "rule_candidates": ["bad", _candidate(rule_id="x2")]},
            ],
        )

        self.assertTrue(report["ready"])
        self.assertEqual(report["total_reviews"], 2)
        self.assertEqual(report["total_rule_hits"], 2)
        self.assertEqual(report["rules"][0]["neutral_count"], 2)
        self.assertTrue(report["warnings"])

    def test_no_rule_hits_returns_readable_empty_scoring_state(self) -> None:
        report = build_rule_score_report(
            replay_results=[
                _replay(review=_review(direction_correct=False, rule_candidates=[])),
                _replay(review=_review(direction_correct=True, rule_candidates=[])),
            ]
        )

        self.assertTrue(report["ready"])
        self.assertEqual(report["total_reviews"], 2)
        self.assertEqual(report["total_rule_hits"], 0)
        self.assertEqual(report["rules"], [])
        self.assertIn("没有可评分的 rule_candidates", report["summary"])
        self.assertTrue(report["warnings"])


if __name__ == "__main__":
    unittest.main()
