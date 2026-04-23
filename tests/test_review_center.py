"""Tests for services/review_center.py — 复盘中心 MVP。"""

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import services.log_store as ls
from services.review_center import (
    build_review_detail,
    compute_review_stats,
    format_review_summary,
)


# ── test isolation ─────────────────────────────────────────────────────────────

class ReviewCenterTestBase(unittest.TestCase):
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

    # ── fixture helpers ───────────────────────────────────────────────────────

    def _write_pair(
        self,
        *,
        date: str,
        predicted: str,
        actual: str,
        state_probs: dict | None = None,
        exclusion_action: str = "allow",
        exclusion_rule: str | None = None,
        direction: str = "偏多",
        confidence: str = "medium",
        direction_correct: bool | None = None,
    ) -> tuple[str, str]:
        """Write one prediction + outcome pair; return (pred_id, out_id)."""
        probs = state_probs or {}
        pred_id = ls.write_prediction_log({
            "symbol": "AVGO",
            "analysis_date": date,
            "prediction_for_date": date,
            "predicted_state": predicted,
            "state_probabilities": probs,
            "direction": direction,
            "confidence": confidence,
            "exclusion_action": exclusion_action,
            "exclusion_triggered_rule": exclusion_rule,
        })
        state_match = actual == predicted
        out_id = ls.write_outcome_log({
            "prediction_log_id": pred_id,
            "symbol": "AVGO",
            "prediction_for_date": date,
            "actual_state": actual,
            "predicted_state": predicted,
            "state_match": state_match,
            "direction_correct": direction_correct,
            "actual_close_change_pct": 1.0,
        })
        return pred_id, out_id


# ── compute_review_stats — empty state ────────────────────────────────────────

class EmptyLogTests(ReviewCenterTestBase):
    def test_empty_logs_returns_zero_sample_count(self):
        r = compute_review_stats()
        self.assertEqual(r["sample_count"], 0)

    def test_all_rates_none_when_empty(self):
        r = compute_review_stats()
        self.assertIsNone(r["top1_hit_rate"])
        self.assertIsNone(r["top2_coverage_rate"])
        self.assertIsNone(r["exclusion_hit_rate"])
        self.assertIsNone(r["exclusion_miss_rate"])

    def test_warnings_not_empty_when_no_data(self):
        r = compute_review_stats()
        self.assertTrue(len(r["warnings"]) > 0)


# ── Top1 命中率 ───────────────────────────────────────────────────────────────

class Top1HitRateTests(ReviewCenterTestBase):
    def test_perfect_top1(self):
        for i in range(4):
            self._write_pair(date=f"2024-04-{i+1:02d}", predicted="小涨", actual="小涨")
        r = compute_review_stats(window=10)
        self.assertEqual(r["sample_count"], 4)
        self.assertAlmostEqual(r["top1_hit_rate"], 1.0)
        self.assertEqual(r["top1_hit_count"], 4)

    def test_zero_top1(self):
        for i in range(3):
            self._write_pair(date=f"2024-04-{i+1:02d}", predicted="大涨", actual="大跌")
        r = compute_review_stats(window=10)
        self.assertAlmostEqual(r["top1_hit_rate"], 0.0)
        self.assertEqual(r["top1_hit_count"], 0)

    def test_partial_top1(self):
        # 2 hit, 2 miss
        self._write_pair(date="2024-04-01", predicted="小涨", actual="小涨")
        self._write_pair(date="2024-04-02", predicted="小涨", actual="小涨")
        self._write_pair(date="2024-04-03", predicted="大涨", actual="震荡")
        self._write_pair(date="2024-04-04", predicted="大涨", actual="震荡")
        r = compute_review_stats(window=10)
        self.assertAlmostEqual(r["top1_hit_rate"], 0.5)
        self.assertEqual(r["top1_hit_count"], 2)

    def test_window_clips_to_n(self):
        # Write 10 pairs but ask for window=5
        for i in range(10):
            self._write_pair(date=f"2024-04-{i+1:02d}", predicted="小涨", actual="小涨")
        r = compute_review_stats(window=5)
        self.assertEqual(r["sample_count"], 5)

    def test_unpaired_predictions_excluded(self):
        # Write a prediction with no outcome → should not count
        ls.write_prediction_log({
            "symbol": "AVGO",
            "prediction_for_date": "2024-04-01",
            "predicted_state": "小涨",
        })
        self._write_pair(date="2024-04-02", predicted="小涨", actual="小涨")
        r = compute_review_stats(window=10)
        self.assertEqual(r["sample_count"], 1)
        self.assertIn("unpaired" in str(r["warnings"]).lower()
                      or "暂无结果" in str(r["warnings"]),
                      [True])


# ── Top2 覆盖率 ───────────────────────────────────────────────────────────────

class Top2CoverageTests(ReviewCenterTestBase):
    def test_top2_hit_when_actual_is_second_highest(self):
        # predicted Top1=大涨(0.40), Top2=小涨(0.35) → actual=小涨 → covered
        self._write_pair(
            date="2024-04-01",
            predicted="大涨",
            actual="小涨",
            state_probs={"大涨": 0.40, "小涨": 0.35, "震荡": 0.15, "小跌": 0.07, "大跌": 0.03},
        )
        r = compute_review_stats(window=10)
        self.assertEqual(r["top2_coverage_count"], 1)
        self.assertAlmostEqual(r["top2_coverage_rate"], 1.0)

    def test_top2_miss_when_actual_is_third(self):
        # Top1=大涨, Top2=小涨, actual=震荡 → NOT covered
        self._write_pair(
            date="2024-04-01",
            predicted="大涨",
            actual="震荡",
            state_probs={"大涨": 0.40, "小涨": 0.35, "震荡": 0.15, "小跌": 0.07, "大跌": 0.03},
        )
        r = compute_review_stats(window=10)
        self.assertEqual(r["top2_coverage_count"], 0)
        self.assertAlmostEqual(r["top2_coverage_rate"], 0.0)

    def test_top2_degraded_when_no_state_probs(self):
        # No state_probs → top2 = [predicted_state] only
        self._write_pair(
            date="2024-04-01",
            predicted="小涨",
            actual="小涨",
            state_probs={},   # empty
        )
        r = compute_review_stats(window=10)
        # actual == predicted → top2 covered (since top2 = [predicted_state])
        self.assertEqual(r["top2_coverage_count"], 1)
        self.assertIn("降级", r["top2_note"])

    def test_top2_covers_top1_hit(self):
        # Top1 hit always implies Top2 covered
        self._write_pair(
            date="2024-04-01",
            predicted="震荡",
            actual="震荡",
            state_probs={"大涨": 0.10, "小涨": 0.15, "震荡": 0.50, "小跌": 0.15, "大跌": 0.10},
        )
        r = compute_review_stats(window=10)
        self.assertEqual(r["top1_hit_count"], 1)
        self.assertEqual(r["top2_coverage_count"], 1)

    def test_top2_rate_higher_than_top1(self):
        # 3 records: 1 top1 hit + 1 top2-only + 1 full miss
        self._write_pair(
            date="2024-04-01", predicted="大涨", actual="大涨",   # top1 hit → top2 covered
            state_probs={"大涨": 0.50, "小涨": 0.30, "震荡": 0.10, "小跌": 0.06, "大跌": 0.04},
        )
        self._write_pair(
            date="2024-04-02", predicted="大涨", actual="小涨",   # top2 covered (small rise is #2)
            state_probs={"大涨": 0.50, "小涨": 0.30, "震荡": 0.10, "小跌": 0.06, "大跌": 0.04},
        )
        self._write_pair(
            date="2024-04-03", predicted="大涨", actual="大跌",   # complete miss
            state_probs={"大涨": 0.50, "小涨": 0.30, "震荡": 0.10, "小跌": 0.06, "大跌": 0.04},
        )
        r = compute_review_stats(window=10)
        self.assertEqual(r["top1_hit_count"], 1)
        self.assertEqual(r["top2_coverage_count"], 2)
        self.assertGreater(r["top2_coverage_rate"], r["top1_hit_rate"])


# ── 排除命中率 / 误杀率 ───────────────────────────────────────────────────────

class ExclusionRateTests(ReviewCenterTestBase):
    def test_exclusion_hit_big_up_rule(self):
        # 排除大涨，实际为震荡 → 命中（大涨未发生）
        self._write_pair(
            date="2024-04-01",
            predicted="震荡",
            actual="震荡",
            exclusion_action="exclude",
            exclusion_rule="exclude_big_up",
        )
        r = compute_review_stats(window=10)
        self.assertEqual(r["exclusion_total"], 1)
        self.assertEqual(r["exclusion_hit_count"], 1)
        self.assertAlmostEqual(r["exclusion_hit_rate"], 1.0)
        self.assertAlmostEqual(r["exclusion_miss_rate"], 0.0)

    def test_exclusion_miss_big_up_rule(self):
        # 排除大涨，但实际发生了大涨 → 误杀
        self._write_pair(
            date="2024-04-01",
            predicted="震荡",
            actual="大涨",
            exclusion_action="exclude",
            exclusion_rule="exclude_big_up",
        )
        r = compute_review_stats(window=10)
        self.assertEqual(r["exclusion_miss_count"], 1)
        self.assertAlmostEqual(r["exclusion_miss_rate"], 1.0)
        self.assertAlmostEqual(r["exclusion_hit_rate"], 0.0)

    def test_exclusion_hit_big_down_rule(self):
        # 排除大跌，实际为小跌 → 命中
        self._write_pair(
            date="2024-04-01",
            predicted="小跌",
            actual="小跌",
            exclusion_action="exclude",
            exclusion_rule="exclude_big_down",
        )
        r = compute_review_stats(window=10)
        self.assertEqual(r["exclusion_hit_count"], 1)

    def test_exclusion_miss_big_down_rule(self):
        # 排除大跌，实际大跌真发生 → 误杀
        self._write_pair(
            date="2024-04-01",
            predicted="小跌",
            actual="大跌",
            exclusion_action="exclude",
            exclusion_rule="exclude_big_down",
        )
        r = compute_review_stats(window=10)
        self.assertEqual(r["exclusion_miss_count"], 1)
        self.assertAlmostEqual(r["exclusion_miss_rate"], 1.0)

    def test_mixed_exclusion_hits_and_misses(self):
        # 2 hits, 1 miss
        self._write_pair(date="2024-04-01", predicted="震荡", actual="小涨",
                         exclusion_action="exclude", exclusion_rule="exclude_big_up")
        self._write_pair(date="2024-04-02", predicted="震荡", actual="震荡",
                         exclusion_action="exclude", exclusion_rule="exclude_big_up")
        self._write_pair(date="2024-04-03", predicted="震荡", actual="大涨",  # miss
                         exclusion_action="exclude", exclusion_rule="exclude_big_up")
        r = compute_review_stats(window=10)
        self.assertEqual(r["exclusion_total"], 3)
        self.assertEqual(r["exclusion_hit_count"], 2)
        self.assertEqual(r["exclusion_miss_count"], 1)
        self.assertAlmostEqual(r["exclusion_hit_rate"],  2/3, places=3)
        self.assertAlmostEqual(r["exclusion_miss_rate"], 1/3, places=3)

    def test_no_exclusion_warns(self):
        self._write_pair(date="2024-04-01", predicted="小涨", actual="小涨",
                         exclusion_action="allow")
        r = compute_review_stats(window=10)
        self.assertEqual(r["exclusion_total"], 0)
        self.assertIsNone(r["exclusion_hit_rate"])
        self.assertTrue(any("排除" in w for w in r["warnings"]))

    def test_allow_records_not_counted_in_exclusion(self):
        # Mix of allow and exclude
        self._write_pair(date="2024-04-01", predicted="小涨", actual="小涨",
                         exclusion_action="allow")
        self._write_pair(date="2024-04-02", predicted="震荡", actual="震荡",
                         exclusion_action="exclude", exclusion_rule="exclude_big_up")
        r = compute_review_stats(window=10)
        self.assertEqual(r["exclusion_total"], 1)
        self.assertEqual(r["sample_count"], 2)


# ── build_review_detail ───────────────────────────────────────────────────────

class ReviewDetailTests(ReviewCenterTestBase):
    def test_detail_has_all_required_keys(self):
        self._write_pair(date="2024-04-01", predicted="小涨", actual="小涨")
        detail = build_review_detail(window=10)
        required = {
            "prediction_for_date", "predicted_state", "actual_state",
            "state_match", "top2_states", "top2_covered",
            "direction", "direction_correct", "confidence",
            "exclusion_action", "exclusion_triggered_rule",
            "exclusion_hit", "actual_close_change_pct",
        }
        self.assertTrue(required.issubset(detail[0].keys()))

    def test_detail_newest_first(self):
        self._write_pair(date="2024-04-01", predicted="小涨", actual="小涨")
        self._write_pair(date="2024-04-02", predicted="小涨", actual="小涨")
        detail = build_review_detail(window=10)
        self.assertEqual(detail[0]["prediction_for_date"], "2024-04-02")

    def test_detail_top2_covered_true_for_top1_hit(self):
        self._write_pair(
            date="2024-04-01", predicted="小涨", actual="小涨",
            state_probs={"大涨": 0.10, "小涨": 0.50, "震荡": 0.25, "小跌": 0.10, "大跌": 0.05},
        )
        detail = build_review_detail(window=10)
        self.assertTrue(detail[0]["top2_covered"])
        self.assertTrue(detail[0]["state_match"])

    def test_detail_exclusion_hit_set_correctly(self):
        self._write_pair(
            date="2024-04-01", predicted="震荡", actual="小涨",
            exclusion_action="exclude", exclusion_rule="exclude_big_up",
        )
        detail = build_review_detail(window=10)
        self.assertTrue(detail[0]["exclusion_hit"])   # 大涨未发生 → 命中

    def test_empty_detail(self):
        detail = build_review_detail()
        self.assertEqual(detail, [])


# ── format_review_summary ─────────────────────────────────────────────────────

class FormatSummaryTests(ReviewCenterTestBase):
    def test_summary_is_string(self):
        self._write_pair(date="2024-04-01", predicted="小涨", actual="小涨")
        stats = compute_review_stats(window=10)
        s = format_review_summary(stats)
        self.assertIsInstance(s, str)
        self.assertIn("复盘中心", s)

    def test_summary_shows_rates(self):
        self._write_pair(date="2024-04-01", predicted="小涨", actual="小涨")
        s = format_review_summary(compute_review_stats(window=10))
        self.assertIn("Top1", s)
        self.assertIn("Top2", s)
        self.assertIn("排除", s)
        self.assertIn("误杀", s)

    def test_summary_empty_state(self):
        stats = compute_review_stats()
        s = format_review_summary(stats)
        self.assertIn("—", s)   # rates are None → displayed as "—"


# ── integration: full pipeline round-trip ────────────────────────────────────

class IntegrationTest(ReviewCenterTestBase):
    def test_full_10_record_scenario(self):
        probs = {"大涨": 0.40, "小涨": 0.35, "震荡": 0.15, "小跌": 0.07, "大跌": 0.03}
        scenarios = [
            # (predicted, actual, exclusion_action, excl_rule)
            ("大涨", "大涨", "allow",   None),               # top1 hit
            ("大涨", "小涨", "allow",   None),               # top2 covered
            ("大涨", "震荡", "allow",   None),               # miss
            ("小涨", "小涨", "allow",   None),               # top1 hit
            ("震荡", "小跌", "allow",   None),               # miss
            ("震荡", "震荡", "exclude", "exclude_big_up"),   # excl hit
            ("震荡", "小涨", "exclude", "exclude_big_up"),   # excl hit
            ("震荡", "大涨", "exclude", "exclude_big_up"),   # excl MISS (误杀)
            ("小跌", "小跌", "allow",   None),               # top1 hit
            ("小跌", "大跌", "allow",   None),               # miss
        ]
        for i, (pred, actual, action, rule) in enumerate(scenarios):
            self._write_pair(
                date=f"2024-04-{i+1:02d}",
                predicted=pred, actual=actual,
                state_probs=probs,
                exclusion_action=action,
                exclusion_rule=rule,
            )

        r = compute_review_stats(window=20)
        self.assertEqual(r["sample_count"], 10)

        # top1 hits: 0(大涨==大涨)✓ 3(小涨==小涨)✓ 5(震荡==震荡)✓ 8(小跌==小跌)✓ = 4
        self.assertEqual(r["top1_hit_count"], 4)

        # top2 from probs = ["大涨","小涨"] for all records
        # 0:大涨∈top2✓ 1:小涨∈top2✓ 3:小涨∈top2✓ 6:小涨∈top2✓ 7:大涨∈top2✓ = 5
        self.assertEqual(r["top2_coverage_count"], 5)

        # exclusion: 3 records (indices 5,6,7)
        self.assertEqual(r["exclusion_total"], 3)
        self.assertEqual(r["exclusion_hit_count"], 2)   # 5,6 hit; 7 miss
        self.assertEqual(r["exclusion_miss_count"], 1)  # 7 miss
        self.assertAlmostEqual(r["exclusion_hit_rate"],  2/3, places=3)
        self.assertAlmostEqual(r["exclusion_miss_rate"], 1/3, places=3)


if __name__ == "__main__":
    unittest.main()
