"""Tests for services/inspect_analysis.py — 查验分析 MVP。"""

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import services.log_store as ls
from services.inspect_analysis import (
    inspect_by_consistency,
    inspect_current,
    inspect_with_filter,
)


# ── test isolation ─────────────────────────────────────────────────────────────

class InspectTestBase(unittest.TestCase):
    """Redirect LOGS_DIR to a temp directory for every test."""

    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        tmp = Path(self._tmpdir)
        self._patches = [
            patch.object(ls, "LOGS_DIR",      tmp),
            patch.object(ls, "_PRED_FILE",    tmp / "prediction_log.jsonl"),
            patch.object(ls, "_OUTCOME_FILE", tmp / "outcome_log.jsonl"),
            patch.object(ls, "_TRACE_FILE",   tmp / "rule_trace_log.jsonl"),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self) -> None:
        for p in self._patches:
            p.stop()
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _write_pair(
        self,
        *,
        date: str,
        predicted: str,
        actual: str,
        consistency_passed: bool | None = True,
        consistency_conflicts: list | None = None,
        direction: str = "偏多",
        confidence: str = "medium",
        exclusion_action: str = "allow",
        exclusion_rule: str | None = None,
        direction_correct: bool | None = None,
    ) -> tuple[str, str]:
        pred_id = ls.write_prediction_log({
            "symbol": "AVGO",
            "analysis_date": date,
            "prediction_for_date": date,
            "predicted_state": predicted,
            "state_probabilities": {},
            "direction": direction,
            "confidence": confidence,
            "exclusion_action": exclusion_action,
            "exclusion_triggered_rule": exclusion_rule,
            "consistency_passed": consistency_passed,
            "consistency_conflicts": consistency_conflicts or [],
        })
        out_id = ls.write_outcome_log({
            "prediction_log_id": pred_id,
            "symbol": "AVGO",
            "prediction_for_date": date,
            "actual_state": actual,
            "predicted_state": predicted,
            "state_match": actual == predicted,
            "direction_correct": direction_correct,
            "actual_close_change_pct": 1.0,
        })
        return pred_id, out_id


# ── inspect_by_consistency — empty state ──────────────────────────────────────

class InspectByConsistencyEmptyTests(InspectTestBase):
    def test_empty_logs_returns_zero_total(self):
        r = inspect_by_consistency()
        self.assertEqual(r["total_sample_count"], 0)

    def test_empty_consistent_and_inconsistent_blocks(self):
        r = inspect_by_consistency()
        self.assertEqual(r["consistent_stats"]["sample_count"], 0)
        self.assertEqual(r["inconsistent_stats"]["sample_count"], 0)

    def test_all_rates_none_when_empty(self):
        r = inspect_by_consistency()
        self.assertIsNone(r["consistent_stats"]["top1_hit_rate"])
        self.assertIsNone(r["inconsistent_stats"]["top1_hit_rate"])

    def test_warnings_present_when_no_data(self):
        r = inspect_by_consistency()
        self.assertTrue(len(r["warnings"]) > 0)


# ── inspect_by_consistency — grouping ─────────────────────────────────────────

class InspectByConsistencyGroupingTests(InspectTestBase):
    def test_consistent_records_counted_separately(self):
        self._write_pair(date="2024-04-01", predicted="小涨", actual="小涨",
                         consistency_passed=True)
        self._write_pair(date="2024-04-02", predicted="大涨", actual="震荡",
                         consistency_passed=True)
        self._write_pair(date="2024-04-03", predicted="震荡", actual="大跌",
                         consistency_passed=False)
        r = inspect_by_consistency(window=10)
        self.assertEqual(r["consistent_stats"]["sample_count"], 2)
        self.assertEqual(r["inconsistent_stats"]["sample_count"], 1)
        self.assertEqual(r["total_sample_count"], 3)

    def test_unknown_consistency_grouped_into_unknown_stats(self):
        self._write_pair(date="2024-04-01", predicted="小涨", actual="小涨",
                         consistency_passed=None)
        self._write_pair(date="2024-04-02", predicted="大涨", actual="大涨",
                         consistency_passed=True)
        r = inspect_by_consistency(window=10)
        self.assertEqual(r["unknown_stats"]["sample_count"], 1)
        self.assertEqual(r["consistent_stats"]["sample_count"], 1)
        self.assertTrue(any("unknown" in n.lower() or "缺少" in n for n in r["notes"]))

    def test_consistent_top1_hit_rate_correct(self):
        # 3 consistent records: 2 hits, 1 miss
        self._write_pair(date="2024-04-01", predicted="小涨", actual="小涨",
                         consistency_passed=True)
        self._write_pair(date="2024-04-02", predicted="小涨", actual="小涨",
                         consistency_passed=True)
        self._write_pair(date="2024-04-03", predicted="小涨", actual="大跌",
                         consistency_passed=True)
        r = inspect_by_consistency(window=10)
        self.assertAlmostEqual(r["consistent_stats"]["top1_hit_rate"], 2 / 3, places=3)

    def test_inconsistent_top1_hit_rate_correct(self):
        # 2 inconsistent records: 1 hit
        self._write_pair(date="2024-04-01", predicted="震荡", actual="震荡",
                         consistency_passed=False)
        self._write_pair(date="2024-04-02", predicted="震荡", actual="大涨",
                         consistency_passed=False)
        r = inspect_by_consistency(window=10)
        self.assertAlmostEqual(r["inconsistent_stats"]["top1_hit_rate"], 0.5, places=3)

    def test_high_diff_between_groups_adds_note(self):
        # Consistent: 4/4 hits (100%); Inconsistent: 0/4 hits (0%) → diff > 10pp
        for i in range(4):
            self._write_pair(date=f"2024-04-{i+1:02d}", predicted="小涨", actual="小涨",
                             consistency_passed=True)
        for i in range(4):
            self._write_pair(date=f"2024-04-{i+5:02d}", predicted="大涨", actual="小跌",
                             consistency_passed=False)
        r = inspect_by_consistency(window=20)
        # Should add a diagnostic note about the gap
        self.assertTrue(any("建议" in n or "pp" in n for n in r["notes"]))

    def test_summary_is_non_empty_string(self):
        self._write_pair(date="2024-04-01", predicted="小涨", actual="小涨",
                         consistency_passed=True)
        r = inspect_by_consistency(window=10)
        self.assertIsInstance(r["summary"], str)
        self.assertGreater(len(r["summary"]), 0)


# ── inspect_with_filter ───────────────────────────────────────────────────────

class InspectWithFilterTests(InspectTestBase):
    def test_no_filters_returns_all_records(self):
        for i in range(3):
            self._write_pair(date=f"2024-04-{i+1:02d}", predicted="小涨", actual="小涨")
        r = inspect_with_filter(window=10)
        self.assertEqual(r["sample_count"], 3)

    def test_consistency_true_filter(self):
        self._write_pair(date="2024-04-01", predicted="小涨", actual="小涨",
                         consistency_passed=True)
        self._write_pair(date="2024-04-02", predicted="大涨", actual="小跌",
                         consistency_passed=False)
        r = inspect_with_filter(window=10, consistency=True)
        self.assertEqual(r["sample_count"], 1)

    def test_consistency_false_filter(self):
        self._write_pair(date="2024-04-01", predicted="小涨", actual="小涨",
                         consistency_passed=True)
        self._write_pair(date="2024-04-02", predicted="大涨", actual="小跌",
                         consistency_passed=False)
        r = inspect_with_filter(window=10, consistency=False)
        self.assertEqual(r["sample_count"], 1)

    def test_direction_filter(self):
        self._write_pair(date="2024-04-01", predicted="小涨", actual="小涨",
                         direction="偏多")
        self._write_pair(date="2024-04-02", predicted="小跌", actual="小跌",
                         direction="偏空")
        r = inspect_with_filter(window=10, direction="偏空")
        self.assertEqual(r["sample_count"], 1)

    def test_confidence_filter(self):
        self._write_pair(date="2024-04-01", predicted="小涨", actual="小涨",
                         confidence="high")
        self._write_pair(date="2024-04-02", predicted="大涨", actual="震荡",
                         confidence="low")
        r = inspect_with_filter(window=10, confidence="high")
        self.assertEqual(r["sample_count"], 1)
        self.assertAlmostEqual(r["top1_hit_rate"], 1.0)

    def test_exclusion_action_filter(self):
        self._write_pair(date="2024-04-01", predicted="震荡", actual="震荡",
                         exclusion_action="exclude", exclusion_rule="exclude_big_up")
        self._write_pair(date="2024-04-02", predicted="小涨", actual="小涨",
                         exclusion_action="allow")
        r = inspect_with_filter(window=10, exclusion_action="exclude")
        self.assertEqual(r["sample_count"], 1)

    def test_combined_filters_and_logic(self):
        # Only True consistency AND 偏多 direction should match
        self._write_pair(date="2024-04-01", predicted="小涨", actual="小涨",
                         consistency_passed=True, direction="偏多")
        self._write_pair(date="2024-04-02", predicted="小涨", actual="小涨",
                         consistency_passed=True, direction="偏空")
        self._write_pair(date="2024-04-03", predicted="小涨", actual="小涨",
                         consistency_passed=False, direction="偏多")
        r = inspect_with_filter(window=10, consistency=True, direction="偏多")
        self.assertEqual(r["sample_count"], 1)

    def test_empty_filter_result_has_none_rate(self):
        self._write_pair(date="2024-04-01", predicted="小涨", actual="小涨",
                         direction="偏多")
        r = inspect_with_filter(window=10, direction="偏空")  # no match
        self.assertEqual(r["sample_count"], 0)
        self.assertIsNone(r["top1_hit_rate"])

    def test_small_sample_adds_note(self):
        self._write_pair(date="2024-04-01", predicted="小涨", actual="小涨",
                         confidence="high")
        r = inspect_with_filter(window=10, confidence="high")
        # sample_count=1 < 5 → note about low confidence
        self.assertTrue(any("样本数" in n or "置信度" in n for n in r["notes"]))

    def test_filter_desc_included_in_output(self):
        self._write_pair(date="2024-04-01", predicted="小涨", actual="小涨",
                         direction="偏多", confidence="high")
        r = inspect_with_filter(window=10, direction="偏多", confidence="high")
        self.assertIn("filter_desc", r)
        self.assertIsInstance(r["filter_desc"], str)

    def test_summary_string_returned(self):
        self._write_pair(date="2024-04-01", predicted="小涨", actual="小涨")
        r = inspect_with_filter(window=10)
        self.assertIsInstance(r["summary"], str)


# ── inspect_current ───────────────────────────────────────────────────────────

class InspectCurrentTests(InspectTestBase):
    def test_empty_logs_returns_fallback_with_zero_samples(self):
        snap = {"consistency_passed": True, "direction": "偏多", "confidence": "high"}
        r = inspect_current(snap)
        self.assertEqual(r["sample_count"], 0)
        self.assertEqual(r["match_level"], "兜底（全部记录）")

    def test_level1_full_match_chosen_when_enough_samples(self):
        # Write 4 records matching all snapshot fields
        for i in range(4):
            self._write_pair(
                date=f"2024-04-{i+1:02d}",
                predicted="小涨", actual="小涨",
                consistency_passed=True, direction="偏多",
                confidence="high", exclusion_action="allow",
            )
        snap = {
            "consistency_passed": True,
            "direction": "偏多",
            "confidence": "high",
            "exclusion_action": "allow",
        }
        r = inspect_current(snap)
        self.assertEqual(r["match_level"], "全字段匹配")
        self.assertEqual(r["sample_count"], 4)

    def test_level2_chosen_when_level1_insufficient(self):
        # 1 exact match, but 4 consistency+direction matches
        self._write_pair(date="2024-04-01", predicted="小涨", actual="小涨",
                         consistency_passed=True, direction="偏多",
                         confidence="high", exclusion_action="allow")
        for i in range(3):
            self._write_pair(
                date=f"2024-04-{i+2:02d}",
                predicted="小涨", actual="小涨",
                consistency_passed=True, direction="偏多",
                confidence="low",  # different confidence
            )
        snap = {
            "consistency_passed": True,
            "direction": "偏多",
            "confidence": "high",
            "exclusion_action": "allow",
        }
        r = inspect_current(snap)
        self.assertEqual(r["match_level"], "一致性+方向匹配")
        self.assertEqual(r["sample_count"], 4)

    def test_level3_chosen_when_level2_insufficient(self):
        # Only 2 consistency+direction matches, 4 consistency-only matches
        self._write_pair(date="2024-04-01", predicted="小涨", actual="小涨",
                         consistency_passed=True, direction="偏多")
        self._write_pair(date="2024-04-02", predicted="小涨", actual="小涨",
                         consistency_passed=True, direction="偏多")
        for i in range(3):
            self._write_pair(
                date=f"2024-04-{i+3:02d}",
                predicted="小涨", actual="小涨",
                consistency_passed=True, direction="偏空",  # different direction
            )
        snap = {
            "consistency_passed": True,
            "direction": "偏多",
            "confidence": "high",
        }
        r = inspect_current(snap)
        self.assertEqual(r["match_level"], "仅一致性匹配")
        self.assertEqual(r["sample_count"], 5)

    def test_level4_fallback_chosen_when_all_insufficient(self):
        # Only 2 consistency matches, 4 total records (includes inconsistent)
        self._write_pair(date="2024-04-01", predicted="小涨", actual="小涨",
                         consistency_passed=True, direction="偏多")
        self._write_pair(date="2024-04-02", predicted="小涨", actual="小涨",
                         consistency_passed=True, direction="偏多")
        for i in range(3):
            self._write_pair(
                date=f"2024-04-{i+3:02d}",
                predicted="小涨", actual="小涨",
                consistency_passed=False,
            )
        snap = {
            "consistency_passed": True,
            "direction": "偏多",
            "confidence": "high",
        }
        r = inspect_current(snap)
        self.assertEqual(r["match_level"], "兜底（全部记录）")
        self.assertEqual(r["sample_count"], 5)

    def test_filter_used_reflects_snapshot(self):
        self._write_pair(date="2024-04-01", predicted="小涨", actual="小涨",
                         consistency_passed=True, direction="偏多", confidence="high")
        snap = {
            "consistency_passed": True,
            "direction": "偏多",
            "confidence": "high",
        }
        r = inspect_current(snap)
        self.assertEqual(r["filter_used"]["consistency_passed"], True)
        self.assertEqual(r["filter_used"]["direction"], "偏多")
        self.assertEqual(r["filter_used"]["confidence"], "high")

    def test_consistency_flag_consistent_derives_true(self):
        # If consistency_passed is absent but consistency_flag == "consistent"
        for i in range(3):
            self._write_pair(
                date=f"2024-04-{i+1:02d}",
                predicted="小涨", actual="小涨",
                consistency_passed=True,
            )
        snap = {"consistency_flag": "consistent"}
        r = inspect_current(snap)
        self.assertEqual(r["filter_used"]["consistency_passed"], True)

    def test_consistency_flag_conflict_derives_false(self):
        for i in range(3):
            self._write_pair(
                date=f"2024-04-{i+1:02d}",
                predicted="小涨", actual="小涨",
                consistency_passed=False,
            )
        snap = {"consistency_flag": "conflict"}
        r = inspect_current(snap)
        self.assertEqual(r["filter_used"]["consistency_passed"], False)

    def test_small_sample_note_added(self):
        self._write_pair(date="2024-04-01", predicted="小涨", actual="小涨",
                         consistency_passed=True, direction="偏多",
                         confidence="high", exclusion_action="allow")
        snap = {
            "consistency_passed": True,
            "direction": "偏多",
            "confidence": "high",
            "exclusion_action": "allow",
        }
        r = inspect_current(snap)
        # 1 sample < 5 → note about low confidence
        self.assertTrue(any("样本" in n or "置信度" in n for n in r["notes"]))

    def test_summary_string_returned(self):
        snap = {"consistency_passed": True}
        r = inspect_current(snap)
        self.assertIsInstance(r["summary"], str)

    def test_empty_snapshot_uses_all_records(self):
        for i in range(3):
            self._write_pair(date=f"2024-04-{i+1:02d}", predicted="小涨", actual="小涨")
        r = inspect_current({})
        # No filters → level4 fallback or level3 with 3 samples
        self.assertEqual(r["sample_count"], 3)


# ── integration: all three functions on shared data ───────────────────────────

class IntegrationTest(InspectTestBase):
    """Full round-trip using a common fixture set."""

    def setUp(self):
        super().setUp()
        # 8 records: 5 consistent, 3 inconsistent; mix of directions and hits
        records = [
            # (date, predicted, actual, consistency, direction, confidence, excl_action, excl_rule)
            ("2024-04-01", "小涨", "小涨", True,  "偏多", "high",   "allow",   None),
            ("2024-04-02", "小涨", "小涨", True,  "偏多", "high",   "allow",   None),
            ("2024-04-03", "大涨", "震荡", True,  "偏多", "medium", "allow",   None),
            ("2024-04-04", "震荡", "震荡", True,  "中性", "medium", "allow",   None),
            ("2024-04-05", "小跌", "大跌", True,  "偏空", "low",    "allow",   None),
            ("2024-04-06", "大涨", "小涨", False, "偏多", "high",   "allow",   None),
            ("2024-04-07", "震荡", "震荡", False, "中性", "medium", "exclude", "exclude_big_up"),
            ("2024-04-08", "震荡", "大涨", False, "中性", "medium", "exclude", "exclude_big_up"),
        ]
        for (date, pred, actual, cons, dirn, conf, excl, rule) in records:
            self._write_pair(
                date=date, predicted=pred, actual=actual,
                consistency_passed=cons, direction=dirn,
                confidence=conf, exclusion_action=excl, exclusion_rule=rule,
            )

    def test_by_consistency_totals(self):
        r = inspect_by_consistency(window=20)
        self.assertEqual(r["total_sample_count"], 8)
        self.assertEqual(r["consistent_stats"]["sample_count"], 5)
        self.assertEqual(r["inconsistent_stats"]["sample_count"], 3)

    def test_consistent_top1_hit_rate(self):
        r = inspect_by_consistency(window=20)
        # consistent hits: 04-01(小涨==小涨), 04-02(小涨==小涨), 04-04(震荡==震荡) = 3/5
        self.assertAlmostEqual(r["consistent_stats"]["top1_hit_rate"], 3 / 5, places=3)

    def test_inconsistent_exclusion_stats(self):
        r = inspect_by_consistency(window=20)
        # 2 inconsistent exclusion records (07,08)
        ic = r["inconsistent_stats"]
        self.assertEqual(ic["exclusion_total"], 2)
        # 07: exclude_big_up, actual=震荡 → 大涨未发生 → hit
        # 08: exclude_big_up, actual=大涨 → 大涨发生 → miss
        self.assertEqual(ic["exclusion_hit_count"], 1)
        self.assertEqual(ic["exclusion_miss_count"], 1)

    def test_filter_high_confidence_only(self):
        r = inspect_with_filter(window=20, confidence="high")
        # 04-01, 04-02 (consistent+high), 04-06 (inconsistent+high) = 3 records
        self.assertEqual(r["sample_count"], 3)

    def test_filter_consistent_and_bullish(self):
        r = inspect_with_filter(window=20, consistency=True, direction="偏多")
        # 04-01, 04-02, 04-03 = 3 consistent+偏多
        self.assertEqual(r["sample_count"], 3)
        # hits: 04-01, 04-02 = 2/3
        self.assertAlmostEqual(r["top1_hit_rate"], 2 / 3, places=3)

    def test_inspect_current_level1_match(self):
        # snapshot = consistent + 偏多 + high + allow → 04-01, 04-02 = 2 records
        # 2 < 3 → falls to level2: consistent + 偏多 = 04-01, 04-02, 04-03 = 3 records
        snap = {
            "consistency_passed": True,
            "direction": "偏多",
            "confidence": "high",
            "exclusion_action": "allow",
        }
        r = inspect_current(snap, window=20)
        self.assertIn(r["match_level"], ("全字段匹配", "一致性+方向匹配"))

    def test_inspect_current_summary_contains_level(self):
        snap = {"consistency_passed": True, "direction": "偏多"}
        r = inspect_current(snap, window=20)
        self.assertIn(r["match_level"], r["summary"])


if __name__ == "__main__":
    unittest.main()
