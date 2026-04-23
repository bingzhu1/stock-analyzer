# -*- coding: utf-8 -*-
"""
tests/test_review_store.py

Unit tests for services/review_store.py.
All tests run against a temporary in-memory / file-based SQLite DB so the
production avgo_agent.db is never touched.
"""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import services.review_store as _rs

# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

_SYMBOL = "AVGO"
_DATE = "2026-04-21"
_PID = "pred-uuid-001"

_COMPARISON = {
    "symbol": _SYMBOL,
    "prediction_for_date": _DATE,
    "final_bias": "bullish",
    "final_confidence": "medium",
    "pred_open": "高开",
    "pred_path": "高开高走",
    "pred_close": "收涨",
    "actual_open_type": "高开",
    "actual_path": "高开高走",
    "actual_close_type": "收涨",
    "open_correct": True,
    "path_correct": True,
    "close_correct": True,
    "correct_count": 3,
    "total_count": 3,
    "overall_score": 1.0,
    "direction_match": 1,
    "error_category": "correct",
    "summary": "All correct",
    "_missing_fields": [],
}

_ERROR_INFO = {
    "error_types": [],
    "primary_error": None,
    "reason_guesses": [],
    "error_category": "correct",
    "error_dimensions": [],
    "correct_dimensions": ["open", "path", "close"],
    "unclear_dimensions": [],
    "dimension_detail": {
        "open":  {"predicted": "高开", "actual": "高开", "correct": True},
        "path":  {"predicted": "高开高走", "actual": "高开高走", "correct": True},
        "close": {"predicted": "收涨", "actual": "收涨", "correct": True},
    },
    "overall_score": 1.0,
    "correct_count": 3,
    "total_count": 3,
}

_REVIEW_PAYLOAD = {
    "status": "ok",
    "symbol": _SYMBOL,
    "prediction_for_date": _DATE,
    "prediction_id": _PID,
    "comparison": _COMPARISON,
    "error_info": _ERROR_INFO,
    "review_summary": "[AVGO] 2026-04-21 — BULLISH / medium\n方向正确 ✓\n得分 3/3 [███]  100%",
}

_V2_BLOCKS = {
    "meta": {
        "schema_version": 2,
        "review_kind": "deterministic_review_v2",
        "status": "schema_only",
        "symbol": _SYMBOL,
        "prediction_for_date": _DATE,
        "prediction_id": _PID,
    },
    "primary_projection": {
        "status": "reserved_from_legacy_prediction",
        "symbol": _SYMBOL,
        "final_bias": "bullish",
    },
    "peer_adjustment": {
        "status": "reserved",
        "peer_symbols": ["NVDA", "SOXX", "QQQ"],
        "adjustments": [],
    },
    "final_projection": {
        "status": "carried_forward",
        "final_bias": "bullish",
        "pred_open": "高开",
        "pred_path": "高开高走",
        "pred_close": "收涨",
    },
    "historical_probability": {
        "status": "reserved",
        "probabilities": {},
    },
    "actual_outcome": {
        "actual_open": 172.0,
        "actual_close": 174.0,
        "actual_open_type": "高开",
        "actual_path": "高开高走",
        "actual_close_type": "收涨",
    },
    "review_result": {
        "surface_errors": {"overall_score": 1.0, "primary_error": None},
        "mechanism_errors": {"status": "reserved", "items": []},
    },
    "rule_extraction": {
        "status": "reserved",
        "rules": [],
    },
}

_REVIEW_PAYLOAD_V2 = {
    **_REVIEW_PAYLOAD,
    **_V2_BLOCKS,
}

_PARTIAL_PAYLOAD = {
    "status": "ok",
    "symbol": "NVDA",
    "prediction_for_date": "2026-04-22",
    "prediction_id": "pred-uuid-002",
    "comparison": {
        "pred_open": "低开",
        "pred_path": "低开高走",
        "pred_close": "收涨",
        "actual_open_type": "高开",
        "actual_path": "高开高走",
        "actual_close_type": "收涨",
        "open_correct": False,
        "path_correct": False,
        "close_correct": True,
        "correct_count": 1,
        "total_count": 3,
        "overall_score": 1 / 3,
        "error_category": "wrong_direction",
    },
    "error_info": {
        "error_types": ["开盘判断错误", "路径判断错误"],
        "primary_error": "路径判断错误",
        "reason_guesses": ["预测路径与实际结构不一致", "预测开盘方向与实际不一致"],
        "error_category": "wrong_direction",
        "error_dimensions": ["open", "path"],
        "correct_dimensions": ["close"],
        "unclear_dimensions": [],
        "dimension_detail": {},
        "overall_score": 1 / 3,
        "correct_count": 1,
        "total_count": 3,
    },
    "review_summary": "partial",
}


# ─────────────────────────────────────────────────────────────────────────────
# Test base — patches DB_PATH to a temp file for isolation
# ─────────────────────────────────────────────────────────────────────────────

class _StoreTestBase(unittest.TestCase):
    """Base class that redirects DB_PATH to a per-test temp file."""

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        tmp_db = Path(self._tmpdir.name) / "test_review.db"
        self._patcher = patch.object(_rs, "DB_PATH", tmp_db)
        self._patcher.start()
        _rs.init_db()

    def tearDown(self) -> None:
        self._patcher.stop()
        self._tmpdir.cleanup()


# ─────────────────────────────────────────────────────────────────────────────
# save_review_record — return value
# ─────────────────────────────────────────────────────────────────────────────

class SaveReturnValueTests(_StoreTestBase):

    def test_returns_string(self) -> None:
        rid = _rs.save_review_record(_REVIEW_PAYLOAD)
        self.assertIsInstance(rid, str)

    def test_returns_nonempty_string(self) -> None:
        rid = _rs.save_review_record(_REVIEW_PAYLOAD)
        self.assertGreater(len(rid), 0)

    def test_two_saves_return_distinct_ids(self) -> None:
        rid1 = _rs.save_review_record(_REVIEW_PAYLOAD)
        rid2 = _rs.save_review_record(_REVIEW_PAYLOAD)
        self.assertNotEqual(rid1, rid2)


# ─────────────────────────────────────────────────────────────────────────────
# save_review_record → round-trip via get_latest_review_for_target_date
# ─────────────────────────────────────────────────────────────────────────────

class RoundTripTests(_StoreTestBase):

    def setUp(self) -> None:
        super().setUp()
        self._rid = _rs.save_review_record(_REVIEW_PAYLOAD)
        self._row = _rs.get_latest_review_for_target_date(_SYMBOL, _DATE)

    def test_row_not_none(self) -> None:
        self.assertIsNotNone(self._row)

    def test_id_matches(self) -> None:
        self.assertEqual(self._row["id"], self._rid)

    def test_symbol_persisted(self) -> None:
        self.assertEqual(self._row["symbol"], _SYMBOL)

    def test_prediction_for_date_persisted(self) -> None:
        self.assertEqual(self._row["prediction_for_date"], _DATE)

    def test_prediction_id_persisted(self) -> None:
        self.assertEqual(self._row["prediction_id"], _PID)

    def test_overall_score_persisted(self) -> None:
        self.assertAlmostEqual(self._row["overall_score"], 1.0)

    def test_correct_count_persisted(self) -> None:
        self.assertEqual(self._row["correct_count"], 3)

    def test_total_count_persisted(self) -> None:
        self.assertEqual(self._row["total_count"], 3)

    def test_pred_open_persisted(self) -> None:
        self.assertEqual(self._row["pred_open"], "高开")

    def test_pred_path_persisted(self) -> None:
        self.assertEqual(self._row["pred_path"], "高开高走")

    def test_pred_close_persisted(self) -> None:
        self.assertEqual(self._row["pred_close"], "收涨")

    def test_actual_open_type_persisted(self) -> None:
        self.assertEqual(self._row["actual_open_type"], "高开")

    def test_actual_path_persisted(self) -> None:
        self.assertEqual(self._row["actual_path"], "高开高走")

    def test_actual_close_type_persisted(self) -> None:
        self.assertEqual(self._row["actual_close_type"], "收涨")

    def test_open_correct_is_true(self) -> None:
        self.assertIs(self._row["open_correct"], True)

    def test_path_correct_is_true(self) -> None:
        self.assertIs(self._row["path_correct"], True)

    def test_close_correct_is_true(self) -> None:
        self.assertIs(self._row["close_correct"], True)

    def test_error_category_persisted(self) -> None:
        self.assertEqual(self._row["error_category"], "correct")

    def test_primary_error_is_none(self) -> None:
        self.assertIsNone(self._row["primary_error"])

    def test_error_types_json_is_list(self) -> None:
        self.assertIsInstance(self._row["error_types_json"], list)

    def test_error_types_json_empty_when_correct(self) -> None:
        self.assertEqual(self._row["error_types_json"], [])

    def test_reason_guesses_json_is_list(self) -> None:
        self.assertIsInstance(self._row["reason_guesses_json"], list)

    def test_review_summary_persisted(self) -> None:
        self.assertIn(_SYMBOL, self._row["review_summary"])

    def test_comparison_json_parseable(self) -> None:
        cmp = json.loads(self._row["comparison_json"])
        self.assertIsInstance(cmp, dict)

    def test_error_info_json_parseable(self) -> None:
        ei = json.loads(self._row["error_info_json"])
        self.assertIsInstance(ei, dict)

    def test_legacy_payload_defaults_schema_version_one(self) -> None:
        self.assertEqual(self._row["review_schema_version"], 1)

    def test_legacy_payload_has_empty_v2_blocks(self) -> None:
        self.assertEqual(self._row["meta_json"], {})
        self.assertEqual(self._row["primary_projection_json"], {})

    def test_legacy_payload_json_preserves_payload(self) -> None:
        payload = self._row["review_payload_json"]
        self.assertEqual(payload["symbol"], _SYMBOL)
        self.assertEqual(payload["review_id"], self._rid)
        self.assertIn("comparison", payload)


# ─────────────────────────────────────────────────────────────────────────────
# Version 2 review payload round-trip
# ─────────────────────────────────────────────────────────────────────────────

class V2RoundTripTests(_StoreTestBase):

    def setUp(self) -> None:
        super().setUp()
        self._rid = _rs.save_review_record(_REVIEW_PAYLOAD_V2)
        self._row = _rs.get_latest_review_for_target_date(_SYMBOL, _DATE)

    def test_schema_version_persisted(self) -> None:
        self.assertEqual(self._row["review_schema_version"], 2)

    def test_meta_json_decoded(self) -> None:
        self.assertIsInstance(self._row["meta_json"], dict)
        self.assertEqual(self._row["meta_json"]["schema_version"], 2)

    def test_meta_json_includes_review_id(self) -> None:
        self.assertEqual(self._row["meta_json"]["review_id"], self._rid)

    def test_primary_projection_json_decoded(self) -> None:
        self.assertEqual(self._row["primary_projection_json"]["final_bias"], "bullish")

    def test_peer_adjustment_json_decoded(self) -> None:
        self.assertEqual(self._row["peer_adjustment_json"]["peer_symbols"], ["NVDA", "SOXX", "QQQ"])

    def test_final_projection_json_decoded(self) -> None:
        self.assertEqual(self._row["final_projection_json"]["pred_open"], "高开")

    def test_historical_probability_json_decoded(self) -> None:
        self.assertEqual(self._row["historical_probability_json"]["status"], "reserved")

    def test_actual_outcome_json_decoded(self) -> None:
        self.assertEqual(self._row["actual_outcome_json"]["actual_path"], "高开高走")

    def test_review_result_json_decoded(self) -> None:
        self.assertIn("mechanism_errors", self._row["review_result_json"])

    def test_rule_extraction_json_decoded(self) -> None:
        self.assertEqual(self._row["rule_extraction_json"]["rules"], [])

    def test_full_review_payload_json_decoded(self) -> None:
        payload = self._row["review_payload_json"]
        self.assertEqual(payload["review_id"], self._rid)
        self.assertEqual(payload["meta"]["schema_version"], 2)

    def test_load_review_records_returns_v2_blocks(self) -> None:
        row = _rs.load_review_records(symbol=_SYMBOL)[0]
        self.assertEqual(row["review_schema_version"], 2)
        self.assertEqual(row["final_projection_json"]["pred_close"], "收涨")


# ─────────────────────────────────────────────────────────────────────────────
# Bool round-trip for wrong dimensions
# ─────────────────────────────────────────────────────────────────────────────

class BoolRoundTripTests(_StoreTestBase):

    def setUp(self) -> None:
        super().setUp()
        _rs.save_review_record(_PARTIAL_PAYLOAD)
        self._row = _rs.get_latest_review_for_target_date("NVDA", "2026-04-22")

    def test_open_correct_is_false(self) -> None:
        self.assertIs(self._row["open_correct"], False)

    def test_path_correct_is_false(self) -> None:
        self.assertIs(self._row["path_correct"], False)

    def test_close_correct_is_true(self) -> None:
        self.assertIs(self._row["close_correct"], True)

    def test_error_types_json_nonempty(self) -> None:
        self.assertGreater(len(self._row["error_types_json"]), 0)

    def test_primary_error_persisted(self) -> None:
        self.assertEqual(self._row["primary_error"], "路径判断错误")

    def test_reason_guesses_json_nonempty(self) -> None:
        self.assertGreater(len(self._row["reason_guesses_json"]), 0)


# ─────────────────────────────────────────────────────────────────────────────
# None round-trip (unclear dimensions)
# ─────────────────────────────────────────────────────────────────────────────

class NoneCorrectRoundTripTests(_StoreTestBase):

    def test_none_correct_round_trips_as_none(self) -> None:
        payload = {
            "status": "ok",
            "symbol": _SYMBOL,
            "prediction_for_date": _DATE,
            "prediction_id": _PID,
            "comparison": {
                "open_correct": None,
                "path_correct": None,
                "close_correct": None,
                "correct_count": 0,
                "total_count": 3,
                "overall_score": 0.0,
                "error_category": "insufficient_data",
            },
            "error_info": {
                "overall_score": 0.0,
                "correct_count": 0,
                "total_count": 3,
                "error_types": [],
                "primary_error": None,
                "reason_guesses": [],
                "error_category": "insufficient_data",
            },
            "review_summary": "unclear",
        }
        _rs.save_review_record(payload)
        row = _rs.get_latest_review_for_target_date(_SYMBOL, _DATE)
        self.assertIsNone(row["open_correct"])
        self.assertIsNone(row["path_correct"])
        self.assertIsNone(row["close_correct"])


# ─────────────────────────────────────────────────────────────────────────────
# get_latest_review_for_target_date — returns latest of multiple saves
# ─────────────────────────────────────────────────────────────────────────────

class LatestReviewTests(_StoreTestBase):

    def test_returns_none_when_no_records(self) -> None:
        result = _rs.get_latest_review_for_target_date(_SYMBOL, _DATE)
        self.assertIsNone(result)

    def test_returns_latest_when_multiple_saves(self) -> None:
        _rs.save_review_record(_REVIEW_PAYLOAD)
        second = dict(_REVIEW_PAYLOAD)
        second["review_summary"] = "second save"
        second["error_info"] = dict(_ERROR_INFO)
        second["comparison"] = dict(_COMPARISON)
        rid2 = _rs.save_review_record(second)
        row = _rs.get_latest_review_for_target_date(_SYMBOL, _DATE)
        self.assertEqual(row["id"], rid2)

    def test_returns_correct_symbol_only(self) -> None:
        _rs.save_review_record(_PARTIAL_PAYLOAD)  # NVDA
        result = _rs.get_latest_review_for_target_date(_SYMBOL, _DATE)
        self.assertIsNone(result)  # no AVGO row saved


# ─────────────────────────────────────────────────────────────────────────────
# load_review_records — filtering and ordering
# ─────────────────────────────────────────────────────────────────────────────

class LoadRecordsTests(_StoreTestBase):

    def setUp(self) -> None:
        super().setUp()
        _rs.save_review_record(_REVIEW_PAYLOAD)    # AVGO 2026-04-21
        _rs.save_review_record(_PARTIAL_PAYLOAD)   # NVDA 2026-04-22

    def test_load_all_returns_list(self) -> None:
        rows = _rs.load_review_records()
        self.assertIsInstance(rows, list)

    def test_load_all_returns_both_records(self) -> None:
        rows = _rs.load_review_records()
        self.assertEqual(len(rows), 2)

    def test_load_filtered_by_symbol_avgo(self) -> None:
        rows = _rs.load_review_records(symbol=_SYMBOL)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["symbol"], _SYMBOL)

    def test_load_filtered_by_symbol_nvda(self) -> None:
        rows = _rs.load_review_records(symbol="NVDA")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["symbol"], "NVDA")

    def test_load_unknown_symbol_returns_empty(self) -> None:
        rows = _rs.load_review_records(symbol="AAPL")
        self.assertEqual(rows, [])

    def test_limit_respected(self) -> None:
        rows = _rs.load_review_records(limit=1)
        self.assertEqual(len(rows), 1)

    def test_each_row_is_dict(self) -> None:
        for row in _rs.load_review_records():
            self.assertIsInstance(row, dict)

    def test_each_row_has_id(self) -> None:
        for row in _rs.load_review_records():
            self.assertIn("id", row)

    def test_bool_fields_decoded_in_load(self) -> None:
        rows = _rs.load_review_records(symbol=_SYMBOL)
        row = rows[0]
        self.assertIs(row["open_correct"], True)

    def test_error_types_json_decoded_in_load(self) -> None:
        rows = _rs.load_review_records(symbol="NVDA")
        row = rows[0]
        self.assertIsInstance(row["error_types_json"], list)


# ─────────────────────────────────────────────────────────────────────────────
# Edge cases — missing / None fields in payload
# ─────────────────────────────────────────────────────────────────────────────

class EdgeCaseTests(_StoreTestBase):

    def test_save_with_empty_comparison_does_not_raise(self) -> None:
        payload = {
            "status": "ok",
            "symbol": _SYMBOL,
            "prediction_for_date": _DATE,
            "prediction_id": _PID,
            "comparison": {},
            "error_info": {},
            "review_summary": "",
        }
        rid = _rs.save_review_record(payload)
        self.assertIsInstance(rid, str)

    def test_save_with_missing_comparison_key_does_not_raise(self) -> None:
        payload = {
            "status": "ok",
            "symbol": _SYMBOL,
            "prediction_for_date": _DATE,
            "prediction_id": _PID,
            "review_summary": "no comparison key",
        }
        rid = _rs.save_review_record(payload)
        self.assertIsInstance(rid, str)

    def test_load_returns_empty_list_when_table_empty(self) -> None:
        rows = _rs.load_review_records()
        self.assertEqual(rows, [])

    def test_init_db_is_idempotent(self) -> None:
        _rs.init_db()
        _rs.init_db()
        rid = _rs.save_review_record(_REVIEW_PAYLOAD)
        self.assertIsInstance(rid, str)


# ─────────────────────────────────────────────────────────────────────────────
# Schema migration
# ─────────────────────────────────────────────────────────────────────────────

class MigrationTests(unittest.TestCase):

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._db_path = Path(self._tmpdir.name) / "old_review.db"
        self._patcher = patch.object(_rs, "DB_PATH", self._db_path)
        self._patcher.start()

    def tearDown(self) -> None:
        self._patcher.stop()
        self._tmpdir.cleanup()

    def test_init_db_adds_v2_columns_to_existing_table(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """CREATE TABLE deterministic_review_log (
                    id TEXT PRIMARY KEY,
                    prediction_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    prediction_for_date TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    overall_score REAL,
                    correct_count INTEGER,
                    total_count INTEGER,
                    pred_open TEXT,
                    pred_path TEXT,
                    pred_close TEXT,
                    actual_open_type TEXT,
                    actual_path TEXT,
                    actual_close_type TEXT,
                    open_correct INTEGER,
                    path_correct INTEGER,
                    close_correct INTEGER,
                    error_category TEXT,
                    primary_error TEXT,
                    error_types_json TEXT,
                    reason_guesses_json TEXT,
                    review_summary TEXT,
                    comparison_json TEXT,
                    error_info_json TEXT
                )"""
            )

        _rs.init_db()

        with sqlite3.connect(self._db_path) as conn:
            columns = {row[1] for row in conn.execute("PRAGMA table_info(deterministic_review_log)")}

        expected = {
            "review_schema_version",
            "meta_json",
            "primary_projection_json",
            "peer_adjustment_json",
            "final_projection_json",
            "historical_probability_json",
            "actual_outcome_json",
            "review_result_json",
            "rule_extraction_json",
            "review_payload_json",
        }
        self.assertTrue(expected.issubset(columns))


if __name__ == "__main__":
    unittest.main()
