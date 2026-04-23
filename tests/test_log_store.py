"""Tests for services/log_store.py — lightweight file-based log system."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import services.log_store as ls


# ── test isolation: redirect LOGS_DIR to a temp directory ────────────────────

class LogStoreTestBase(unittest.TestCase):
    """Patch LOGS_DIR and all _*_FILE paths to a fresh temp directory."""

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


# ── prediction_log ─────────────────────────────────────────────────────────

class PredictionLogWriteTests(LogStoreTestBase):
    def _sample(self, **overrides) -> dict:
        base = {
            "symbol": "AVGO",
            "analysis_date": "2024-04-22",
            "prediction_for_date": "2024-04-23",
            "predicted_state": "小涨",
            "predicted_top1": {"state": "小涨", "probability": 0.40},
            "predicted_top2": {"state": "震荡", "probability": 0.30},
            "state_probabilities": {"大涨": 0.10, "小涨": 0.40, "震荡": 0.30, "小跌": 0.15, "大跌": 0.05},
            "direction": "偏多",
            "confidence": "medium",
            "exclusion_action": "allow",
            "exclusion_triggered_rule": None,
            "consistency_passed": True,
            "consistency_flag": "consistent",
            "consistency_score": 1.0,
            "consistency_conflicts": [],
            "feature_snapshot": {"pos20": 65.0, "ret1": 1.2, "vol_ratio20": 1.1},
            "peer_alignment": {"alignment": "bullish"},
            "notes": [],
        }
        base.update(overrides)
        return base

    def test_returns_log_id_string(self):
        log_id = ls.write_prediction_log(self._sample())
        self.assertIsInstance(log_id, str)
        self.assertTrue(len(log_id) > 0)

    def test_file_is_created(self):
        ls.write_prediction_log(self._sample())
        self.assertTrue(ls._PRED_FILE.exists())

    def test_file_contains_valid_json_line(self):
        ls.write_prediction_log(self._sample())
        lines = ls._PRED_FILE.read_text().strip().splitlines()
        self.assertEqual(len(lines), 1)
        parsed = json.loads(lines[0])
        self.assertEqual(parsed["symbol"], "AVGO")

    def test_auto_injects_log_id_and_created_at(self):
        log_id = ls.write_prediction_log(self._sample())
        entries = ls.read_prediction_log()
        self.assertEqual(entries[0]["log_id"], log_id)
        self.assertIn("created_at", entries[0])

    def test_multiple_writes_produce_multiple_lines(self):
        ls.write_prediction_log(self._sample(prediction_for_date="2024-04-23"))
        ls.write_prediction_log(self._sample(prediction_for_date="2024-04-24"))
        entries = ls.read_prediction_log()
        self.assertEqual(len(entries), 2)

    def test_explicit_log_id_is_preserved(self):
        ls.write_prediction_log(self._sample(log_id="fixed-id-001"))
        entries = ls.read_prediction_log()
        self.assertEqual(entries[0]["log_id"], "fixed-id-001")

    def test_defaults_applied_for_missing_keys(self):
        ls.write_prediction_log({"symbol": "AVGO", "prediction_for_date": "2024-04-23"})
        entries = ls.read_prediction_log()
        self.assertEqual(entries[0]["window_days"], 20)
        self.assertEqual(entries[0]["notes"], [])
        self.assertEqual(entries[0]["predicted_top1"], {})
        self.assertEqual(entries[0]["predicted_top2"], {})

    def test_derives_new_prediction_fields_from_existing_semantics(self):
        ls.write_prediction_log({
            "symbol": "AVGO",
            "prediction_for_date": "2024-04-23",
            "predicted_top1": {"state": "大涨", "probability": 0.51},
            "exclusion_triggered_rule": "exclude_big_up",
            "consistency_flag": "conflict",
        })
        entries = ls.read_prediction_log()
        self.assertEqual(entries[0]["predicted_state"], "大涨")
        self.assertEqual(entries[0]["excluded_state"], "大涨")
        self.assertFalse(entries[0]["consistency_passed"])

    def test_read_newest_first(self):
        ls.write_prediction_log(self._sample(prediction_for_date="2024-04-23"))
        ls.write_prediction_log(self._sample(prediction_for_date="2024-04-24"))
        entries = ls.read_prediction_log()
        self.assertEqual(entries[0]["prediction_for_date"], "2024-04-24")

    def test_filter_by_symbol(self):
        ls.write_prediction_log(self._sample(symbol="AVGO"))
        ls.write_prediction_log(self._sample(symbol="NVDA"))
        entries = ls.read_prediction_log(symbol="AVGO")
        self.assertTrue(all(e["symbol"] == "AVGO" for e in entries))

    def test_filter_by_date(self):
        ls.write_prediction_log(self._sample(prediction_for_date="2024-04-23"))
        ls.write_prediction_log(self._sample(prediction_for_date="2024-04-24"))
        entries = ls.read_prediction_log(date="2024-04-23")
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["prediction_for_date"], "2024-04-23")

    def test_filter_by_since_date(self):
        ls.write_prediction_log(self._sample(prediction_for_date="2024-04-20"))
        ls.write_prediction_log(self._sample(prediction_for_date="2024-04-23"))
        ls.write_prediction_log(self._sample(prediction_for_date="2024-04-24"))
        entries = ls.read_prediction_log(since_date="2024-04-23")
        self.assertEqual(len(entries), 2)

    def test_limit_respected(self):
        for i in range(10):
            ls.write_prediction_log(self._sample(prediction_for_date=f"2024-04-{i+1:02d}"))
        entries = ls.read_prediction_log(limit=3)
        self.assertEqual(len(entries), 3)

    def test_read_empty_file_returns_empty_list(self):
        self.assertEqual(ls.read_prediction_log(), [])


# ── outcome_log ────────────────────────────────────────────────────────────

class OutcomeLogWriteTests(LogStoreTestBase):
    def _sample_pred_id(self) -> str:
        return ls.write_prediction_log({
            "symbol": "AVGO",
            "prediction_for_date": "2024-04-23",
            "predicted_state": "小涨",
        })

    def _sample_outcome(self, pred_id: str, **overrides) -> dict:
        base = {
            "prediction_log_id": pred_id,
            "symbol": "AVGO",
            "prediction_for_date": "2024-04-23",
            "actual_open": 170.0,
            "actual_high": 175.0,
            "actual_low": 168.0,
            "actual_close": 173.5,
            "actual_prev_close": 171.2,
            "actual_close_change_pct": 1.34,
            "actual_state": "小涨",
            "predicted_state": "小涨",
            "state_match": True,
            "direction_correct": True,
            "actual_upper_shadow_ratio": 0.20,
            "actual_lower_shadow_ratio": 0.08,
        }
        base.update(overrides)
        return base

    def test_returns_log_id(self):
        pred_id = self._sample_pred_id()
        log_id = ls.write_outcome_log(self._sample_outcome(pred_id))
        self.assertIsInstance(log_id, str)

    def test_file_created(self):
        pred_id = self._sample_pred_id()
        ls.write_outcome_log(self._sample_outcome(pred_id))
        self.assertTrue(ls._OUTCOME_FILE.exists())

    def test_filter_by_prediction_log_id(self):
        pid1 = self._sample_pred_id()
        pid2 = self._sample_pred_id()
        ls.write_outcome_log(self._sample_outcome(pid1))
        ls.write_outcome_log(self._sample_outcome(pid2))
        results = ls.read_outcome_log(prediction_log_id=pid1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["prediction_log_id"], pid1)

    def test_filter_by_date(self):
        pred_id = self._sample_pred_id()
        ls.write_outcome_log(self._sample_outcome(pred_id, prediction_for_date="2024-04-23"))
        ls.write_outcome_log(self._sample_outcome(pred_id, prediction_for_date="2024-04-24"))
        results = ls.read_outcome_log(date="2024-04-23")
        self.assertEqual(len(results), 1)

    def test_actual_close_change_pct_is_percentage_not_ratio(self):
        pred_id = self._sample_pred_id()
        # +2% should be stored as 2.0, not 0.02
        ls.write_outcome_log(self._sample_outcome(pred_id, actual_close_change_pct=2.0, actual_state=None))
        results = ls.read_outcome_log(prediction_log_id=pred_id)
        self.assertAlmostEqual(results[0]["actual_close_change_pct"], 2.0)
        self.assertEqual(results[0]["actual_state"], "大涨")

    def test_actual_state_and_state_match_can_be_derived(self):
        pred_id = self._sample_pred_id()
        ls.write_outcome_log({
            "prediction_log_id": pred_id,
            "symbol": "AVGO",
            "prediction_for_date": "2024-04-23",
            "actual_close_change_pct": -0.8,
            "predicted_state": "小跌",
        })
        results = ls.read_outcome_log(prediction_log_id=pred_id)
        self.assertEqual(results[0]["actual_state"], "小跌")
        self.assertTrue(results[0]["state_match"])

    def test_state_match_false_when_mismatch(self):
        pred_id = self._sample_pred_id()
        ls.write_outcome_log(self._sample_outcome(
            pred_id,
            actual_state="大跌",
            predicted_state="小涨",
            state_match=False,
        ))
        results = ls.read_outcome_log(prediction_log_id=pred_id)
        self.assertFalse(results[0]["state_match"])

    def test_read_empty_returns_empty_list(self):
        self.assertEqual(ls.read_outcome_log(), [])


# ── rule_trace_log ─────────────────────────────────────────────────────────

class RuleTraceLogWriteTests(LogStoreTestBase):
    def _sample_trace(self, **overrides) -> dict:
        base = {
            "prediction_log_id": "pred-001",
            "symbol": "AVGO",
            "analysis_date": "2024-04-22",
            "prediction_for_date": "2024-04-23",
            "layer": "exclusion",
            "rule_name": "exclude_big_up",
            "rule_result": "not_triggered",
            "feature_values": {"pos20": 65.0, "ret3": 2.1},
            "summary": "排除层：大涨排除规则未触发，当前位置不极端。",
        }
        base.update(overrides)
        return base

    def test_returns_log_id(self):
        log_id = ls.write_rule_trace_log(self._sample_trace())
        self.assertIsInstance(log_id, str)

    def test_filter_by_prediction_log_id(self):
        ls.write_rule_trace_log(self._sample_trace(prediction_log_id="pred-001"))
        ls.write_rule_trace_log(self._sample_trace(prediction_log_id="pred-002"))
        results = ls.read_rule_trace_log(prediction_log_id="pred-001")
        self.assertEqual(len(results), 1)

    def test_filter_by_layer(self):
        ls.write_rule_trace_log(self._sample_trace(layer="exclusion"))
        ls.write_rule_trace_log(self._sample_trace(layer="main_projection"))
        ls.write_rule_trace_log(self._sample_trace(layer="consistency"))
        results = ls.read_rule_trace_log(layer="exclusion")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["layer"], "exclusion")

    def test_filter_by_rule_name(self):
        ls.write_rule_trace_log(self._sample_trace(rule_name="exclude_big_up"))
        ls.write_rule_trace_log(self._sample_trace(rule_name="exclude_big_down"))
        results = ls.read_rule_trace_log(rule_name="exclude_big_up")
        self.assertEqual(len(results), 1)

    def test_triggered_rule_recorded(self):
        ls.write_rule_trace_log(self._sample_trace(
            rule_name="exclude_big_up",
            rule_result="triggered",
            feature_values={"pos20": 95.0, "ret3": 4.5},
            summary="排除层：pos20过高，大涨排除触发。",
        ))
        results = ls.read_rule_trace_log(rule_name="exclude_big_up")
        self.assertEqual(results[0]["rule_result"], "triggered")
        self.assertAlmostEqual(results[0]["feature_values"]["pos20"], 95.0)

    def test_conflict_rule_recorded(self):
        ls.write_rule_trace_log(self._sample_trace(
            layer="consistency",
            rule_name="exclusion_projection_conflict",
            rule_result="conflict",
            summary="一致性层：排除层排除大涨，主推演层 Top1 仍给出大涨，硬冲突。",
        ))
        results = ls.read_rule_trace_log(layer="consistency")
        self.assertEqual(results[0]["rule_result"], "conflict")

    def test_read_empty_returns_empty_list(self):
        self.assertEqual(ls.read_rule_trace_log(), [])

    def test_combined_filters(self):
        ls.write_rule_trace_log(self._sample_trace(
            prediction_log_id="pred-A", layer="exclusion", rule_name="exclude_big_up"
        ))
        ls.write_rule_trace_log(self._sample_trace(
            prediction_log_id="pred-A", layer="main_projection", rule_name="bias_signal"
        ))
        ls.write_rule_trace_log(self._sample_trace(
            prediction_log_id="pred-B", layer="exclusion", rule_name="exclude_big_up"
        ))
        results = ls.read_rule_trace_log(prediction_log_id="pred-A", layer="exclusion")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["rule_name"], "exclude_big_up")


# ── convenience helpers ────────────────────────────────────────────────────

class ConvenienceHelperTests(LogStoreTestBase):
    def test_get_prediction_by_id_found(self):
        log_id = ls.write_prediction_log({
            "symbol": "AVGO",
            "prediction_for_date": "2024-04-23",
        })
        entry = ls.get_prediction_by_id(log_id)
        self.assertIsNotNone(entry)
        self.assertEqual(entry["log_id"], log_id)  # type: ignore[index]

    def test_get_prediction_by_id_not_found(self):
        ls.write_prediction_log({"symbol": "AVGO", "prediction_for_date": "2024-04-23"})
        entry = ls.get_prediction_by_id("nonexistent-id")
        self.assertIsNone(entry)

    def test_get_latest_prediction(self):
        ls.write_prediction_log({"symbol": "AVGO", "prediction_for_date": "2024-04-22"})
        ls.write_prediction_log({"symbol": "AVGO", "prediction_for_date": "2024-04-23"})
        latest = ls.get_latest_prediction("AVGO")
        self.assertIsNotNone(latest)
        # newest-first ordering means file order reversed, so last written is returned
        self.assertEqual(latest["prediction_for_date"], "2024-04-23")  # type: ignore[index]

    def test_get_latest_prediction_empty(self):
        self.assertIsNone(ls.get_latest_prediction("AVGO"))

    def test_summarize_logs_counts(self):
        ls.write_prediction_log({"symbol": "AVGO", "prediction_for_date": "2024-04-22"})
        ls.write_prediction_log({"symbol": "AVGO", "prediction_for_date": "2024-04-23"})
        ls.write_outcome_log({"symbol": "AVGO", "prediction_for_date": "2024-04-22"})
        ls.write_rule_trace_log({"layer": "exclusion", "analysis_date": "2024-04-22"})
        summary = ls.summarize_logs()
        self.assertEqual(summary["prediction_log"]["count"], 2)
        self.assertEqual(summary["outcome_log"]["count"], 1)
        self.assertEqual(summary["rule_trace_log"]["count"], 1)

    def test_summarize_logs_empty(self):
        summary = ls.summarize_logs()
        self.assertEqual(summary["prediction_log"]["count"], 0)
        self.assertIsNone(summary["prediction_log"]["earliest"])


# ── integration: full round-trip ──────────────────────────────────────────

class RoundTripTest(LogStoreTestBase):
    def test_full_prediction_outcome_trace_roundtrip(self):
        # 1. Write prediction
        pred_id = ls.write_prediction_log({
            "symbol": "AVGO",
            "analysis_date": "2024-04-22",
            "prediction_for_date": "2024-04-23",
            "predicted_state": "小涨",
            "state_probabilities": {"大涨": 0.10, "小涨": 0.40, "震荡": 0.30, "小跌": 0.15, "大跌": 0.05},
            "direction": "偏多",
            "confidence": "medium",
            "exclusion_action": "allow",
            "exclusion_triggered_rule": None,
            "consistency_passed": True,
            "consistency_conflicts": [],
            "feature_snapshot": {"pos20": 65.0, "ret1": 1.2, "vol_ratio20": 1.1},
            "peer_alignment": {"alignment": "bullish"},
        })

        # 2. Write rule traces for each layer
        ls.write_rule_trace_log({
            "prediction_log_id": pred_id,
            "symbol": "AVGO",
            "analysis_date": "2024-04-22",
            "prediction_for_date": "2024-04-23",
            "layer": "exclusion",
            "rule_name": "exclude_big_up",
            "rule_result": "not_triggered",
            "feature_values": {"pos20": 65.0},
            "summary": "pos20=65, 未触发大涨排除。",
        })
        ls.write_rule_trace_log({
            "prediction_log_id": pred_id,
            "layer": "consistency",
            "rule_name": "exclusion_projection_alignment",
            "rule_result": "not_triggered",
            "summary": "排除层与主推演层方向一致，无冲突。",
        })

        # 3. Capture actual outcome
        out_id = ls.write_outcome_log({
            "prediction_log_id": pred_id,
            "symbol": "AVGO",
            "prediction_for_date": "2024-04-23",
            "actual_close": 173.5,
            "actual_prev_close": 171.2,
            "actual_close_change_pct": 1.34,
            "actual_state": "小涨",
            "predicted_state": "小涨",
            "state_match": True,
            "direction_correct": True,
        })

        # 4. Assert all are readable and linked
        pred_entries = ls.read_prediction_log(date="2024-04-23")
        self.assertEqual(len(pred_entries), 1)
        self.assertEqual(pred_entries[0]["log_id"], pred_id)

        out_entries = ls.read_outcome_log(prediction_log_id=pred_id)
        self.assertEqual(len(out_entries), 1)
        self.assertTrue(out_entries[0]["state_match"])

        trace_entries = ls.read_rule_trace_log(prediction_log_id=pred_id)
        self.assertEqual(len(trace_entries), 2)
        layers = {e["layer"] for e in trace_entries}
        self.assertIn("exclusion", layers)
        self.assertIn("consistency", layers)


if __name__ == "__main__":
    unittest.main()
