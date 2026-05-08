from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.final_decision import build_final_decision


def _primary(**overrides) -> dict:
    result = {
        "kind": "primary_20day_analysis",
        "symbol": "AVGO",
        "ready": True,
        "direction": "偏多",
        "confidence": "medium",
        "summary": "主分析偏多。",
        "basis": ["主分析依据。"],
    }
    result.update(overrides)
    return result


def _peer(**overrides) -> dict:
    result = {
        "kind": "peer_adjustment",
        "ready": True,
        "confirmation_level": "confirmed",
        "adjustment": "reinforce_bullish",
        "adjusted_direction": "偏多",
        "adjusted_confidence": "high",
        "summary": "peers 支持主分析偏多。",
        "basis": ["peer basis"],
        "warnings": [],
    }
    result.update(overrides)
    return result


def _historical(**overrides) -> dict:
    result = {
        "kind": "historical_probability",
        "ready": True,
        "sample_count": 12,
        "sample_quality": "enough",
        "historical_bias": "supports_bullish",
        "impact": "support",
        "summary": "历史层支持偏多。",
        "basis": ["historical basis"],
        "warnings": [],
    }
    result.update(overrides)
    return result


def _preflight(**overrides) -> dict:
    result = {
        "matched_count": 1,
        "matched_rules": ["历史提醒。"],
        "summary": "preflight 完成。",
    }
    result.update(overrides)
    return result


def _confidence_result(level: str = "high") -> dict:
    return {
        "kind": "confidence_evaluator_result",
        "ready": True,
        "combined_confidence": {"level": level},
        "agreement_status": "consistent",
        "conflict_level": "low",
    }


class FinalDecisionTests(unittest.TestCase):
    """Step 12B (RISK-2): final_decision is a pure aggregator.

    These tests assert the post-purification contract:
    - final_direction == primary_analysis.direction
    - final_confidence == confidence_result.combined_confidence.level (or
      "unknown" when no confidence_result is wired)
    - peer / historical / preflight do not change direction or confidence
    """

    def test_full_support_returns_fixed_schema(self) -> None:
        result = build_final_decision(
            primary_analysis=_primary(),
            peer_adjustment=_peer(),
            historical_probability=_historical(),
            preflight=_preflight(),
        )

        for key in (
            "kind",
            "symbol",
            "ready",
            "final_direction",
            "final_confidence",
            "risk_level",
            "summary",
            "decision_factors",
            "warnings",
            "layer_contributions",
            "why_not_more_bullish_or_bearish",
            "source_snapshot",
            "non_mutation_confirmations",
            "source_attribution",
        ):
            self.assertIn(key, result)
        self.assertEqual(result["kind"], "final_decision")
        self.assertEqual(result["schema_version"], "final_report_aggregator_result.v1")
        self.assertEqual(result["system_name"], "final_report_aggregator")
        self.assertTrue(result["ready"])
        self.assertEqual(result["final_direction"], "偏多")
        # No confidence_result wired → unknown (Step 12C-B will change this).
        self.assertEqual(result["final_confidence"], "unknown")
        self.assertEqual(result["source_snapshot"]["peer_adjustment"], "reinforce_bullish")
        self.assertEqual(result["source_snapshot"]["historical_bias"], "supports_bullish")

    def test_full_support_with_confidence_result_uses_confidence_level(self) -> None:
        result = build_final_decision(
            primary_analysis=_primary(),
            peer_adjustment=_peer(),
            historical_probability=_historical(),
            preflight=_preflight(),
            confidence_result=_confidence_result("high"),
        )

        self.assertTrue(result["ready"])
        self.assertEqual(result["final_direction"], "偏多")
        self.assertEqual(result["final_confidence"], "high")

    def test_bearish_full_support_follows_primary_direction(self) -> None:
        result = build_final_decision(
            primary_analysis=_primary(direction="偏空", confidence="medium"),
            peer_adjustment=_peer(
                adjustment="reinforce_bearish",
                adjusted_direction="偏空",
                adjusted_confidence="high",
                summary="peers 支持主分析偏空。",
            ),
            historical_probability=_historical(
                historical_bias="supports_bearish",
                impact="support",
                summary="历史层支持偏空。",
            ),
            preflight=_preflight(),
            confidence_result=_confidence_result("high"),
        )

        self.assertTrue(result["ready"])
        self.assertEqual(result["final_direction"], "偏空")
        self.assertEqual(result["final_confidence"], "high")
        self.assertEqual(result["source_snapshot"]["peer_adjustment"], "reinforce_bearish")
        self.assertEqual(result["source_snapshot"]["historical_bias"], "supports_bearish")

    def test_peer_downgrade_does_not_change_direction_or_confidence(self) -> None:
        """Boundary contract: peer downgrade no longer flips direction or
        recomputes confidence. final_direction stays primary; final_confidence
        comes from confidence_result."""
        result = build_final_decision(
            primary_analysis=_primary(confidence="high"),
            peer_adjustment=_peer(
                confirmation_level="weak",
                adjustment="downgrade",
                adjusted_confidence="medium",
                summary="peers 未充分确认主分析方向。",
            ),
            historical_probability=_historical(),
            preflight=_preflight(),
            confidence_result=_confidence_result("medium"),
        )

        self.assertTrue(result["ready"])
        self.assertEqual(result["final_direction"], "偏多")
        self.assertEqual(result["final_confidence"], "medium")
        self.assertIn("同业未确认或偏弱", result["why_not_more_bullish_or_bearish"])
        self.assertIn("peer 修正削弱", result["layer_contributions"]["peer"])

    def test_historical_mixed_does_not_recompute_confidence(self) -> None:
        result = build_final_decision(
            primary_analysis=_primary(confidence="high"),
            peer_adjustment=_peer(adjustment="no_change", adjusted_confidence="high"),
            historical_probability=_historical(
                historical_bias="mixed",
                impact="caution",
                summary="历史样本混杂。",
            ),
            preflight=_preflight(),
            confidence_result=_confidence_result("medium"),
        )

        self.assertTrue(result["ready"])
        self.assertEqual(result["final_direction"], "偏多")
        # final_confidence comes from the confidence_result, not from
        # historical impact.
        self.assertEqual(result["final_confidence"], "medium")
        self.assertIn("历史样本混杂", result["why_not_more_bullish_or_bearish"])

    def test_historical_insufficient_keeps_direction_and_uses_confidence_result(self) -> None:
        result = build_final_decision(
            primary_analysis=_primary(confidence="high"),
            peer_adjustment=_peer(adjustment="no_change", adjusted_confidence="high"),
            historical_probability=_historical(
                ready=False,
                sample_count=2,
                sample_quality="insufficient",
                historical_bias="insufficient",
                impact="missing",
                summary="历史样本不足。",
            ),
            preflight=_preflight(),
            confidence_result=_confidence_result("low"),
        )

        self.assertTrue(result["ready"])
        self.assertEqual(result["final_direction"], "偏多")
        self.assertEqual(result["final_confidence"], "low")
        self.assertIn("历史样本不足", result["why_not_more_bullish_or_bearish"])
        self.assertTrue(any("历史样本" in warning for warning in result["warnings"]))

    def test_peer_missing_and_history_missing_does_not_recompute_confidence(self) -> None:
        result = build_final_decision(
            primary_analysis=_primary(confidence="medium"),
            peer_adjustment=_peer(
                ready=False,
                confirmation_level="missing",
                adjustment="missing",
                summary="未获 peers 确认。",
            ),
            historical_probability=_historical(
                ready=False,
                sample_count=0,
                sample_quality="missing",
                historical_bias="missing",
                impact="missing",
                summary="当前未获得历史样本支持。",
            ),
            preflight={},
        )

        self.assertTrue(result["ready"])
        self.assertEqual(result["final_direction"], "偏多")
        # No confidence_result wired → unknown, regardless of peer/historical
        # being missing.
        self.assertEqual(result["final_confidence"], "unknown")
        self.assertIn("未获 peers 确认", result["summary"])
        self.assertIn("未获得历史概率支持", result["summary"])
        self.assertTrue(any("peers" in warning for warning in result["warnings"]))

    def test_primary_missing_does_not_fake_final_decision(self) -> None:
        result = build_final_decision(
            primary_analysis=_primary(ready=False, direction="unknown", confidence="unknown"),
            peer_adjustment=_peer(),
            historical_probability=_historical(),
            preflight=_preflight(),
        )

        self.assertFalse(result["ready"])
        self.assertEqual(result["final_direction"], "unknown")
        self.assertEqual(result["final_confidence"], "unknown")
        self.assertIn("不能伪造完整", result["summary"])
        self.assertTrue(result["warnings"])
        self.assertIn("non_mutation_confirmations", result)
        self.assertIn("source_attribution", result)

    def test_preflight_rules_count_reads_matched_rules_list_not_matched_count(self) -> None:
        # Regression for F1: new preflight emits matched_rules (list of dicts).
        new_format_preflight = {
            "kind": "projection_rule_preflight",
            "ready": True,
            "matched_rules": [
                {"rule_id": "m1", "category": "wrong_direction", "severity": "high", "message": "提醒1。"},
                {"rule_id": "m2", "category": "false_confidence", "severity": "high", "message": "提醒2。"},
                {"rule_id": "m3", "category": "insufficient_data", "severity": "low", "message": "提醒3。"},
            ],
            "rule_warnings": ["提醒1。", "提醒2。", "提醒3。"],
            "rule_adjustments": ["复核方向。", "控制置信度。", "确认数据。"],
            "summary": "命中 3 条历史规则提醒。",
            "warnings": [],
            "source_counts": {"memory_items": 3, "review_items": 0, "matched_rule_count": 3},
        }

        result = build_final_decision(
            primary_analysis=_primary(),
            peer_adjustment=_peer(),
            historical_probability=_historical(),
            preflight=new_format_preflight,
        )

        self.assertEqual(result["source_snapshot"]["preflight_rules_count"], 3)
        self.assertIn("3", result["layer_contributions"]["preflight"])
        self.assertNotIn("未命中规则", result["layer_contributions"]["preflight"])

    def test_primary_neutral_is_not_overridden_by_secondary_layers(self) -> None:
        result = build_final_decision(
            primary_analysis=_primary(direction="中性", confidence="medium"),
            peer_adjustment=_peer(
                adjustment="reinforce_bullish",
                adjusted_direction="偏多",
                adjusted_confidence="high",
            ),
            historical_probability=_historical(),
            preflight=_preflight(),
        )

        self.assertTrue(result["ready"])
        self.assertEqual(result["final_direction"], "中性")
        # No confidence_result wired → unknown.
        self.assertEqual(result["final_confidence"], "unknown")
        self.assertIn("主分析信号混杂", result["why_not_more_bullish_or_bearish"])


class PreflightDisplayOnlyTests(unittest.TestCase):
    """Step 12B: preflight is display-only. applied_effects stays [] for
    every severity; preflight cannot change direction, confidence, or risk."""

    def _rule(self, severity: str, category: str = "wrong_direction") -> dict:
        return {
            "rule_id": f"test-{severity}",
            "title": f"测试规则 {severity}",
            "category": category,
            "severity": severity,
            "message": f"{severity} 级别规则提醒。",
        }

    def _preflight_with_rules(self, *rules) -> dict:
        rule_list = list(rules)
        return {
            "kind": "projection_rule_preflight",
            "ready": True,
            "matched_rules": rule_list,
            "rule_warnings": [r["message"] for r in rule_list if isinstance(r, dict)],
            "rule_adjustments": [],
            "summary": f"命中 {len(rule_list)} 条规则。",
            "warnings": [],
            "source_counts": {"matched_rule_count": len(rule_list)},
        }

    def test_no_rules_preflight_influence_shape_present(self) -> None:
        """preflight_influence key always present even with zero rules."""
        result = build_final_decision(
            primary_analysis=_primary(),
            peer_adjustment=_peer(),
            historical_probability=_historical(),
            preflight=_preflight(matched_rules=[]),
        )
        self.assertIn("preflight_influence", result)
        inf = result["preflight_influence"]
        self.assertEqual(inf["matched_rule_count"], 0)
        self.assertEqual(inf["applied_effects"], [])
        self.assertIsInstance(inf["summary"], str)

    def test_string_rules_no_influence_applied(self) -> None:
        """String rules produce no score changes; applied_effects stays []."""
        confidence = _confidence_result("high")
        base = build_final_decision(
            primary_analysis=_primary(confidence="high"),
            peer_adjustment=_peer(),
            historical_probability=_historical(),
            preflight=_preflight(matched_rules=[]),
            confidence_result=confidence,
        )
        with_strings = build_final_decision(
            primary_analysis=_primary(confidence="high"),
            peer_adjustment=_peer(),
            historical_probability=_historical(),
            preflight=_preflight(matched_rules=["文本提醒1", "文本提醒2"]),
            confidence_result=confidence,
        )
        self.assertEqual(base["final_confidence"], with_strings["final_confidence"])
        self.assertEqual(with_strings["preflight_influence"]["applied_effects"], [])

    def test_primary_missing_result_has_preflight_influence(self) -> None:
        """preflight_influence present even when primary is missing."""
        result = build_final_decision(
            primary_analysis=_primary(ready=False, direction="unknown", confidence="unknown"),
            peer_adjustment=_peer(),
            historical_probability=_historical(),
            preflight=self._preflight_with_rules(self._rule("high")),
        )
        self.assertFalse(result["ready"])
        self.assertIn("preflight_influence", result)

    def test_low_severity_rule_no_score_change(self) -> None:
        confidence = _confidence_result("high")
        without_rule = build_final_decision(
            primary_analysis=_primary(confidence="high"),
            peer_adjustment=_peer(),
            historical_probability=_historical(),
            preflight=_preflight(matched_rules=[]),
            confidence_result=confidence,
        )
        with_low = build_final_decision(
            primary_analysis=_primary(confidence="high"),
            peer_adjustment=_peer(),
            historical_probability=_historical(),
            preflight=self._preflight_with_rules(self._rule("low")),
            confidence_result=confidence,
        )
        self.assertEqual(without_rule["final_confidence"], with_low["final_confidence"])
        self.assertEqual(with_low["preflight_influence"]["applied_effects"], [])
        self.assertEqual(with_low["preflight_influence"]["matched_rule_count"], 1)

    def test_high_severity_rule_does_not_lower_confidence(self) -> None:
        """Boundary contract: high severity preflight rule must NOT lower
        final_confidence. final_confidence stays equal to
        confidence_result.combined_confidence.level."""
        result = build_final_decision(
            primary_analysis=_primary(confidence="medium"),
            peer_adjustment=_peer(adjustment="reinforce_bullish"),
            historical_probability=_historical(impact="support"),
            preflight=self._preflight_with_rules(self._rule("high")),
            confidence_result=_confidence_result("high"),
        )
        self.assertEqual(result["final_confidence"], "high")
        self.assertEqual(result["preflight_influence"]["applied_effects"], [])
        self.assertEqual(result["final_direction"], "偏多")

    def test_high_severity_rule_does_not_change_direction(self) -> None:
        result = build_final_decision(
            primary_analysis=_primary(direction="偏空", confidence="high"),
            peer_adjustment=_peer(adjustment="reinforce_bearish", adjusted_direction="偏空"),
            historical_probability=_historical(historical_bias="supports_bearish"),
            preflight=self._preflight_with_rules(self._rule("high")),
        )
        self.assertEqual(result["final_direction"], "偏空")
        self.assertEqual(result["preflight_influence"]["applied_effects"], [])

    def test_medium_severity_rule_does_not_raise_risk(self) -> None:
        """Boundary contract: medium severity preflight rule must NOT raise
        risk_level. applied_effects stays []; risk_level is decoupled from
        preflight (it now defaults to unknown until 12C-B wires
        confidence_result reliability)."""
        result = build_final_decision(
            primary_analysis=_primary(confidence="high"),
            peer_adjustment=_peer(adjustment="reinforce_bullish"),
            historical_probability=_historical(impact="support"),
            preflight=self._preflight_with_rules(self._rule("medium")),
        )
        self.assertEqual(result["preflight_influence"]["applied_effects"], [])
        self.assertEqual(result["final_direction"], "偏多")

    def test_three_high_rules_still_apply_zero_effects(self) -> None:
        result = build_final_decision(
            primary_analysis=_primary(confidence="medium"),
            peer_adjustment=_peer(adjustment="reinforce_bullish"),
            historical_probability=_historical(impact="support"),
            preflight=self._preflight_with_rules(
                self._rule("high"),
                self._rule("high"),
                self._rule("high"),
            ),
            confidence_result=_confidence_result("high"),
        )
        self.assertEqual(result["final_confidence"], "high")
        self.assertEqual(result["preflight_influence"]["applied_effects"], [])

    def test_high_and_medium_rules_apply_zero_effects(self) -> None:
        result = build_final_decision(
            primary_analysis=_primary(confidence="medium"),
            peer_adjustment=_peer(adjustment="reinforce_bullish"),
            historical_probability=_historical(impact="support"),
            preflight=self._preflight_with_rules(
                self._rule("high"),
                self._rule("medium"),
            ),
        )
        self.assertEqual(result["preflight_influence"]["applied_effects"], [])
        self.assertEqual(result["final_direction"], "偏多")

    def test_neutral_primary_stays_neutral_under_high_preflight_rules(self) -> None:
        result = build_final_decision(
            primary_analysis=_primary(direction="中性", confidence="medium"),
            peer_adjustment=_peer(adjustment="reinforce_bullish", adjusted_direction="偏多"),
            historical_probability=_historical(),
            preflight=self._preflight_with_rules(
                self._rule("high"),
                self._rule("medium"),
            ),
        )
        self.assertEqual(result["final_direction"], "中性")
        self.assertEqual(result["preflight_influence"]["applied_effects"], [])

    def test_preflight_influence_shape_complete(self) -> None:
        for preflight_arg in [
            None,
            {},
            _preflight(matched_rules=[]),
            self._preflight_with_rules(self._rule("high")),
        ]:
            result = build_final_decision(
                primary_analysis=_primary(),
                peer_adjustment=_peer(),
                historical_probability=_historical(),
                preflight=preflight_arg,
            )
            if result.get("ready"):
                inf = result["preflight_influence"]
                self.assertIn("matched_rule_count", inf)
                self.assertIn("applied_effects", inf)
                self.assertIn("summary", inf)
                self.assertEqual(inf["applied_effects"], [])

    def test_task_045_rule_candidate_format_is_display_only(self) -> None:
        task_045_candidates = [
            {
                "rule_id": "review-rc-a1b2c3d4",
                "title": "历史复盘提醒：peer 缺失时过度自信",
                "category": "false_confidence",
                "severity": "high",
                "message": "当 peer 数据缺失时，不应给出 high confidence 结论。",
            },
            {
                "rule_id": "review-rc-e5f6g7h8",
                "title": "历史复盘提醒：historical 样本不足",
                "category": "insufficient_data",
                "severity": "medium",
                "message": "当 historical 样本不足时，不应把 final risk 设为 low。",
            },
        ]
        preflight = {
            "kind": "projection_rule_preflight",
            "ready": True,
            "matched_rules": task_045_candidates,
            "rule_warnings": [r["message"] for r in task_045_candidates],
            "rule_adjustments": [],
            "summary": "命中 2 条来自 review 闭环的规则。",
            "warnings": [],
        }
        result = build_final_decision(
            primary_analysis=_primary(confidence="medium"),
            peer_adjustment=_peer(adjustment="reinforce_bullish"),
            historical_probability=_historical(impact="support"),
            preflight=preflight,
        )
        self.assertTrue(result["ready"])
        self.assertEqual(result["preflight_influence"]["applied_effects"], [])
        self.assertEqual(result["preflight_influence"]["matched_rule_count"], 2)
        self.assertEqual(result["final_direction"], "偏多")

    def test_explicit_effect_field_is_ignored_by_aggregator(self) -> None:
        """Even when the rule carries an explicit effect, the aggregator
        treats it as display-only — applied_effects stays []."""
        rule = {
            "rule_id": "explicit-effect-rule",
            "title": "显式 effect 规则",
            "category": "false_confidence",
            "severity": "high",
            "effect": "raise_risk",
            "message": "显式 raise_risk 规则不应再影响最终结论。",
        }
        result = build_final_decision(
            primary_analysis=_primary(confidence="high"),
            peer_adjustment=_peer(adjustment="reinforce_bullish"),
            historical_probability=_historical(impact="support"),
            preflight=self._preflight_with_rules(rule),
        )
        self.assertEqual(result["preflight_influence"]["applied_effects"], [])


if __name__ == "__main__":
    unittest.main()
