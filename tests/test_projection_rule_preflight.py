from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.projection_rule_preflight import build_projection_rule_preflight


# ── Stub helpers ─────────────────────────────────────────────────────────────

def _empty_briefing(**_):
    return {
        "symbol": "AVGO",
        "matched_count": 0,
        "top_categories": [],
        "reminder_lines": [],
        "caution_level": "none",
        "advisory_only": True,
    }


def _briefing_with_items(reminder_lines, categories=None, caution_level="none"):
    def _builder(**_):
        cats = categories or [{"error_category": "wrong_direction"}] * len(reminder_lines)
        return {
            "symbol": "AVGO",
            "matched_count": len(reminder_lines),
            "top_categories": cats,
            "reminder_lines": reminder_lines,
            "caution_level": caution_level,
            "advisory_only": True,
        }
    return _builder


def _empty_reviews(**_):
    return []


def _reviews_with(items):
    def _loader(**_):
        return items
    return _loader


def _run(
    symbol="AVGO",
    target_date=None,
    lookback_days=20,
    projection_context=None,
    active_rule_pool_export=None,
    active_bridge_rules=None,
    use_active_rule_pool=False,
    briefing_builder=None,
    review_loader=None,
):
    kwargs = {
        "symbol": symbol,
        "target_date": target_date,
        "lookback_days": lookback_days,
    }
    if projection_context is not None:
        kwargs["projection_context"] = projection_context
    if active_rule_pool_export is not None:
        kwargs["active_rule_pool_export"] = active_rule_pool_export
    if active_bridge_rules is not None:
        kwargs["active_bridge_rules"] = active_bridge_rules
    if use_active_rule_pool:
        kwargs["use_active_rule_pool"] = use_active_rule_pool
    if briefing_builder is not None:
        kwargs["_memory_briefing_builder"] = briefing_builder
    if review_loader is not None:
        kwargs["_review_loader"] = review_loader
    return build_projection_rule_preflight(**kwargs)


# ── Tests ─────────────────────────────────────────────────────────────────────

class ProjectionRulePreflightShapeTests(unittest.TestCase):
    def test_empty_sources_returns_valid_shape(self):
        result = _run(briefing_builder=_empty_briefing, review_loader=_empty_reviews)

        self.assertEqual(result["kind"], "projection_rule_preflight")
        self.assertEqual(result["symbol"], "AVGO")
        self.assertIn("matched_rules", result)
        self.assertIn("rule_warnings", result)
        self.assertIn("rule_adjustments", result)
        self.assertIn("summary", result)
        self.assertIn("warnings", result)
        self.assertIn("source_counts", result)
        self.assertIsInstance(result["matched_rules"], list)
        self.assertIsInstance(result["rule_warnings"], list)
        self.assertIsInstance(result["rule_adjustments"], list)
        self.assertIsInstance(result["warnings"], list)
        self.assertIsInstance(result["source_counts"], dict)

    def test_empty_sources_ready_true(self):
        result = _run(briefing_builder=_empty_briefing, review_loader=_empty_reviews)
        self.assertTrue(result["ready"])
        self.assertEqual(result["matched_rules"], [])

    def test_source_counts_keys_present(self):
        result = _run(briefing_builder=_empty_briefing, review_loader=_empty_reviews)
        for key in ("memory_items", "review_items", "matched_rule_count", "active_pool_items", "active_pool_matches"):
            self.assertIn(key, result["source_counts"])
        self.assertFalse(result["active_pool_used"])


class ProjectionRulePreflightSymbolTests(unittest.TestCase):
    def test_symbol_normalised_upper(self):
        result = _run(symbol="avgo", briefing_builder=_empty_briefing, review_loader=_empty_reviews)
        self.assertEqual(result["symbol"], "AVGO")

    def test_symbol_none_defaults_to_avgo(self):
        result = _run(symbol=None, briefing_builder=_empty_briefing, review_loader=_empty_reviews)
        self.assertEqual(result["symbol"], "AVGO")

    def test_target_date_propagated(self):
        result = _run(
            target_date="2026-04-21",
            briefing_builder=_empty_briefing,
            review_loader=_empty_reviews,
        )
        self.assertEqual(result["target_date"], "2026-04-21")

    def test_lookback_days_propagated(self):
        result = _run(
            lookback_days=10,
            briefing_builder=_empty_briefing,
            review_loader=_empty_reviews,
        )
        self.assertEqual(result["lookback_days"], 10)


class ProjectionRulePreflightMemoryBriefingTests(unittest.TestCase):
    def test_memory_briefing_rules_appear_in_output(self):
        builder = _briefing_with_items(
            ["历史错误：方向判断有误。"],
            [{"error_category": "wrong_direction"}],
        )
        result = _run(briefing_builder=builder, review_loader=_empty_reviews)

        self.assertEqual(len(result["matched_rules"]), 1)
        rule = result["matched_rules"][0]
        self.assertEqual(rule["rule_id"], "memory-1")
        self.assertEqual(rule["category"], "wrong_direction")
        self.assertEqual(rule["severity"], "high")
        self.assertEqual(rule["message"], "历史错误：方向判断有误。")

    def test_rule_adjustment_generated_for_wrong_direction(self):
        builder = _briefing_with_items(
            ["历史错误：方向判断有误。"],
            [{"error_category": "wrong_direction"}],
        )
        result = _run(briefing_builder=builder, review_loader=_empty_reviews)
        self.assertEqual(len(result["rule_adjustments"]), 1)
        self.assertIn("方向", result["rule_adjustments"][0])

    def test_rule_warnings_equals_messages(self):
        builder = _briefing_with_items(
            ["提醒一。", "提醒二。"],
            [{"error_category": "false_confidence"}, {"error_category": "insufficient_data"}],
        )
        result = _run(briefing_builder=builder, review_loader=_empty_reviews)
        self.assertEqual(result["rule_warnings"], [r["message"] for r in result["matched_rules"]])

    def test_multiple_memory_rules(self):
        builder = _briefing_with_items(
            ["提醒一。", "提醒二。", "提醒三。"],
            [
                {"error_category": "wrong_direction"},
                {"error_category": "false_confidence"},
                {"error_category": "right_direction_wrong_magnitude"},
            ],
        )
        result = _run(briefing_builder=builder, review_loader=_empty_reviews)
        self.assertEqual(len(result["matched_rules"]), 3)
        self.assertEqual(result["source_counts"]["memory_items"], 3)

    def test_blank_reminder_line_skipped(self):
        builder = _briefing_with_items(["", "  ", "有效提醒。"])
        result = _run(briefing_builder=builder, review_loader=_empty_reviews)
        self.assertEqual(len(result["matched_rules"]), 1)
        self.assertIn("projection_rule_preflight 跳过格式异常", result["warnings"][0])


class ProjectionRulePreflightReviewTests(unittest.TestCase):
    def _review_item(self, category, message, idx=1):
        return {
            "id": f"rev-{idx}",
            "error_category": category,
            "review_summary": message,
        }

    def test_review_items_generate_rules(self):
        items = [self._review_item("wrong_direction", "上次方向预测错误。")]
        result = _run(briefing_builder=_empty_briefing, review_loader=_reviews_with(items))

        self.assertEqual(len(result["matched_rules"]), 1)
        rule = result["matched_rules"][0]
        self.assertEqual(rule["rule_id"], "rev-1")
        self.assertEqual(rule["category"], "wrong_direction")
        self.assertEqual(rule["message"], "上次方向预测错误。")

    def test_review_correct_category_skipped(self):
        items = [self._review_item("correct", "这次预测正确。")]
        result = _run(briefing_builder=_empty_briefing, review_loader=_reviews_with(items))
        self.assertEqual(result["matched_rules"], [])

    def test_review_unknown_category_skipped(self):
        items = [self._review_item("some_unknown_cat", "消息。")]
        result = _run(briefing_builder=_empty_briefing, review_loader=_reviews_with(items))
        # normalize_error_category maps unknown → insufficient_data, which is in set
        # but let's check: result should have 1 rule with category=insufficient_data
        self.assertEqual(len(result["matched_rules"]), 1)
        self.assertEqual(result["matched_rules"][0]["category"], "insufficient_data")

    def test_review_source_counts(self):
        items = [
            self._review_item("wrong_direction", "提醒。", 1),
            self._review_item("false_confidence", "提醒。", 2),
        ]
        result = _run(briefing_builder=_empty_briefing, review_loader=_reviews_with(items))
        self.assertEqual(result["source_counts"]["review_items"], 2)

    def test_review_error_info_json_fallback(self):
        item = {
            "id": "rev-x",
            "error_info_json": {"error_category": "wrong_direction", "primary_error": "err msg"},
        }
        result = _run(briefing_builder=_empty_briefing, review_loader=_reviews_with([item]))
        self.assertEqual(result["matched_rules"][0]["category"], "wrong_direction")
        self.assertEqual(result["matched_rules"][0]["message"], "err msg")


class ProjectionRulePreflightDedupeTests(unittest.TestCase):
    def test_duplicate_rules_deduped(self):
        briefing_builder = _briefing_with_items(
            ["重复的提醒。", "重复的提醒。"],
            [{"error_category": "wrong_direction"}, {"error_category": "wrong_direction"}],
        )
        result = _run(briefing_builder=briefing_builder, review_loader=_empty_reviews)
        self.assertEqual(len(result["matched_rules"]), 1)

    def test_same_category_different_message_not_deduped(self):
        briefing_builder = _briefing_with_items(
            ["提醒一。", "提醒二。"],
            [{"error_category": "wrong_direction"}, {"error_category": "wrong_direction"}],
        )
        result = _run(briefing_builder=briefing_builder, review_loader=_empty_reviews)
        self.assertEqual(len(result["matched_rules"]), 2)


class ProjectionRulePreflightDegradationTests(unittest.TestCase):
    def test_memory_source_error_degrades_gracefully(self):
        def _failing_briefing(**_):
            raise RuntimeError("DB 不可用")

        result = _run(briefing_builder=_failing_briefing, review_loader=_empty_reviews)
        self.assertIn("source_counts", result)

    def test_review_source_error_degrades_gracefully(self):
        def _failing_review(**_):
            raise RuntimeError("review store 不可用")

        result = _run(briefing_builder=_empty_briefing, review_loader=_failing_review)
        self.assertIn("source_counts", result)

    def test_both_sources_fail_ready_false(self):
        def _fail(**_):
            raise RuntimeError("unavailable")

        result = _run(briefing_builder=_fail, review_loader=_fail)
        self.assertFalse(result["ready"])
        self.assertIn("当前未接入历史规则", result["summary"])

    def test_both_sources_fail_warnings_contain_error_text(self):
        def _fail(**_):
            raise RuntimeError("db_down")

        result = _run(briefing_builder=_fail, review_loader=_fail)
        joined = " ".join(result["warnings"])
        self.assertIn("db_down", joined)

    def test_one_source_fails_other_succeeds_ready_true(self):
        def _fail(**_):
            raise RuntimeError("memory unavailable")

        items = [{"id": "r1", "error_category": "wrong_direction", "review_summary": "提醒。"}]
        result = _run(briefing_builder=_fail, review_loader=_reviews_with(items))
        self.assertTrue(result["ready"])
        self.assertEqual(len(result["matched_rules"]), 1)


class ProjectionRulePreflightActivePoolTests(unittest.TestCase):
    def _bridge_rule(
        self,
        *,
        rule_id="arp-1",
        title="Active Pool Rule",
        category="false_confidence",
        severity="high",
        message="来自 active pool 的提醒。",
        effect="warn",
    ):
        return {
            "rule_id": rule_id,
            "title": title,
            "category": category,
            "severity": severity,
            "message": message,
            "effect": effect,
        }

    def test_default_behavior_ignores_active_pool_when_flag_off(self):
        result = _run(
            briefing_builder=_empty_briefing,
            review_loader=_empty_reviews,
            active_bridge_rules=[self._bridge_rule()],
            use_active_rule_pool=False,
        )

        self.assertEqual(result["matched_rules"], [])
        self.assertFalse(result["active_pool_used"])
        self.assertEqual(result["source_counts"]["active_pool_items"], 0)
        self.assertEqual(result["source_counts"]["active_pool_matches"], 0)

    def test_active_pool_bridge_rules_are_consumed_when_flag_on(self):
        result = _run(
            briefing_builder=_empty_briefing,
            review_loader=_empty_reviews,
            active_rule_pool_export={
                "kind": "active_rule_pool_export",
                "preflight_bridge_rules": [self._bridge_rule(rule_id="arp-a", title="Bridge Active Rule")],
            },
            use_active_rule_pool=True,
        )

        self.assertTrue(result["active_pool_used"])
        self.assertEqual(len(result["matched_rules"]), 1)
        self.assertEqual(result["matched_rules"][0]["rule_id"], "arp-a")
        self.assertIn("active_pool", result["matched_rules"][0]["sources"])
        self.assertEqual(result["source_counts"]["active_pool_items"], 1)
        self.assertEqual(result["source_counts"]["active_pool_matches"], 1)
        self.assertIn("active rule pool", result["summary"])

    def test_missing_or_empty_active_pool_source_falls_back_safely(self):
        missing_result = _run(
            briefing_builder=_empty_briefing,
            review_loader=_empty_reviews,
            use_active_rule_pool=True,
        )
        self.assertTrue(missing_result["ready"])
        self.assertEqual(missing_result["matched_rules"], [])
        self.assertTrue(missing_result["active_pool_used"])
        self.assertEqual(missing_result["source_counts"]["active_pool_matches"], 0)

        empty_result = _run(
            briefing_builder=_empty_briefing,
            review_loader=_empty_reviews,
            active_rule_pool_export={"kind": "active_rule_pool_export", "preflight_bridge_rules": []},
            use_active_rule_pool=True,
        )
        self.assertTrue(empty_result["ready"])
        self.assertEqual(empty_result["matched_rules"], [])
        self.assertEqual(empty_result["source_counts"]["active_pool_items"], 0)
        self.assertEqual(empty_result["source_counts"]["active_pool_matches"], 0)

    def test_malformed_active_pool_rule_is_skipped_without_breaking_others(self):
        result = _run(
            briefing_builder=_empty_briefing,
            review_loader=_empty_reviews,
            active_bridge_rules=[
                self._bridge_rule(rule_id="arp-good", title="Good Rule"),
                {"rule_id": "arp-bad", "category": "wrong_direction"},
                "bad",
            ],
            use_active_rule_pool=True,
        )

        self.assertTrue(result["ready"])
        self.assertEqual(len(result["matched_rules"]), 1)
        self.assertEqual(result["matched_rules"][0]["rule_id"], "arp-good")
        self.assertEqual(result["source_counts"]["active_pool_items"], 3)
        self.assertEqual(result["source_counts"]["active_pool_matches"], 1)
        joined = " ".join(result["warnings"])
        self.assertIn("active pool bridge rule", joined)

    def test_active_pool_duplicate_rule_keeps_provenance_and_post_dedupe_counts(self):
        builder = _briefing_with_items(
            ["重复提醒。"],
            [{"error_category": "false_confidence"}],
        )
        result = _run(
            briefing_builder=builder,
            review_loader=_empty_reviews,
            active_bridge_rules=[
                self._bridge_rule(
                    rule_id="arp-dup",
                    category="false_confidence",
                    severity="high",
                    message="重复提醒。",
                )
            ],
            use_active_rule_pool=True,
        )

        self.assertEqual(len(result["matched_rules"]), 1)
        self.assertEqual(result["source_counts"]["matched_rule_count"], 1)
        self.assertEqual(result["source_counts"]["active_pool_matches"], 1)
        self.assertEqual(result["source_counts"]["active_pool_items"], 1)
        self.assertTrue(result["active_pool_used"])
        self.assertEqual(result["matched_rules"][0]["sources"], ["memory", "active_pool"])
        self.assertIn("1 条规则也来自 active rule pool", result["summary"])


class ProjectionRulePreflightContextOverrideTests(unittest.TestCase):
    def test_memory_items_in_context_bypasses_builder(self):
        """context['memory_items'] skips the memory briefing builder call."""
        call_log = []

        def _builder(**_):
            call_log.append("called")
            return _empty_briefing()

        ctx = {
            "memory_items": [
                {"id": "m1", "error_category": "false_confidence", "lesson": "别高估置信度。"}
            ]
        }
        result = _run(projection_context=ctx, briefing_builder=_builder, review_loader=_empty_reviews)
        self.assertEqual(call_log, [], "builder should not be called when memory_items in context")
        self.assertEqual(len(result["matched_rules"]), 1)
        self.assertEqual(result["matched_rules"][0]["category"], "false_confidence")

    def test_review_items_in_context_bypasses_loader(self):
        call_log = []

        def _loader(**_):
            call_log.append("called")
            return []

        ctx = {
            "review_items": [
                {"id": "r1", "error_category": "wrong_direction", "review_summary": "方向判断错了。"}
            ]
        }
        result = _run(projection_context=ctx, briefing_builder=_empty_briefing, review_loader=_loader)
        self.assertEqual(call_log, [], "loader should not be called when review_items in context")
        self.assertEqual(len(result["matched_rules"]), 1)

    def test_memory_briefing_in_context_used_directly(self):
        call_log = []

        def _builder(**_):
            call_log.append("called")
            return _empty_briefing()

        ctx = {
            "memory_briefing": {
                "matched_count": 1,
                "top_categories": [{"error_category": "wrong_direction"}],
                "reminder_lines": ["从 context 来的提醒。"],
                "caution_level": "low",
            }
        }
        result = _run(projection_context=ctx, briefing_builder=_builder, review_loader=_empty_reviews)
        self.assertEqual(call_log, [], "builder not called when memory_briefing in context")
        self.assertEqual(result["matched_rules"][0]["message"], "从 context 来的提醒。")


class ProjectionRulePreflightSummaryTests(unittest.TestCase):
    def test_summary_mentions_count_when_rules_matched(self):
        builder = _briefing_with_items(["提醒。"], [{"error_category": "wrong_direction"}])
        result = _run(briefing_builder=builder, review_loader=_empty_reviews)
        self.assertIn("1", result["summary"])

    def test_summary_no_rules_text(self):
        result = _run(briefing_builder=_empty_briefing, review_loader=_empty_reviews)
        self.assertIn("未命中", result["summary"])

    def test_source_counts_matched_rule_count_correct(self):
        builder = _briefing_with_items(
            ["提醒一。", "提醒二。"],
            [{"error_category": "wrong_direction"}, {"error_category": "false_confidence"}],
        )
        result = _run(briefing_builder=builder, review_loader=_empty_reviews)
        self.assertEqual(result["source_counts"]["matched_rule_count"], 2)


if __name__ == "__main__":
    unittest.main()
