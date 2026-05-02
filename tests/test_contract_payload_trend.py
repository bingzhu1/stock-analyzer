"""Tests for services/contract_payload_trend.py (Step 1I)."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import services.prediction_store as ps
from services.contract_payload_diff import DIFF_PATHS
from services.contract_payload_trend import (
    summarize_recent_contract_payloads,
)


def _predict_result(
    bias: str = "bullish",
    confidence: str = "medium",
    pred_open: str = "高开",
    pred_path: str = "高开高走",
    pred_close: str = "收涨",
) -> dict:
    return {
        "symbol": "AVGO",
        "final_bias": bias,
        "final_confidence": confidence,
        "scan_bias": bias,
        "scan_confidence": confidence,
        "pred_open": pred_open,
        "pred_path": pred_path,
        "pred_close": pred_close,
        "prediction_summary": "<placeholder>",
        "supporting_factors": ["factor_a"],
        "conflicting_factors": [],
    }


class _IsolatedStoreTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        ps.DB_PATH = Path(self._tmpdir.name) / "test.db"
        ps.init_db()

    def tearDown(self) -> None:
        self._tmpdir.cleanup()


# ── 1. no records ────────────────────────────────────────────────────────────

class TrendNoRecordsTests(_IsolatedStoreTestCase):
    def test_no_records_returns_no_records_status(self) -> None:
        result = summarize_recent_contract_payloads()
        self.assertEqual(result["status"], "no_records")
        self.assertEqual(result["records_scanned"], 0)
        self.assertEqual(result["requested_limit"], 10)


# ── 2. all invalid → no_valid_payloads ───────────────────────────────────────

class TrendAllInvalidTests(_IsolatedStoreTestCase):
    def test_all_records_missing_or_invalid_returns_no_valid_payloads(self) -> None:
        # 3 rows: explicit None (missing), explicit non-contract dict (validation fail),
        # and another None to trigger missing again.
        ps.save_prediction(
            "AVGO", "2026-04-09", None, None, _predict_result(),
            contract_payload=None,
        )
        ps.save_prediction(
            "AVGO", "2026-04-10", None, None, _predict_result(),
            contract_payload={"only_one_section": "bogus"},
        )
        ps.save_prediction(
            "AVGO", "2026-04-11", None, None, _predict_result(),
            contract_payload=None,
        )
        result = summarize_recent_contract_payloads()
        self.assertEqual(result["status"], "no_valid_payloads")
        self.assertEqual(result["records_scanned"], 3)
        self.assertEqual(result["valid_payloads"], 0)
        self.assertEqual(result["invalid_payloads"], 3)
        # All 3 reasons present in skipped_records.
        reasons = sorted(s["reason"] for s in result["skipped_records"])
        self.assertEqual(reasons, ["missing_contract_payload",
                                    "missing_contract_payload",
                                    "validation_failed"])


# ── 3. mixed valid / invalid → ok with skipped_records ───────────────────────

class TrendMixedRecordsTests(_IsolatedStoreTestCase):
    def test_mixed_valid_and_invalid_yields_ok_with_skipped_records(self) -> None:
        # 2 valid (auto-gen via side-path) + 1 invalid (explicit non-contract).
        ps.save_prediction("AVGO", "2026-04-09", None, None, _predict_result())
        ps.save_prediction(
            "AVGO", "2026-04-10", None, None, _predict_result(),
            contract_payload={"only_one_section": "bogus"},
        )
        ps.save_prediction("AVGO", "2026-04-11", None, None, _predict_result())

        result = summarize_recent_contract_payloads()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["records_scanned"], 3)
        self.assertEqual(result["valid_payloads"], 2)
        self.assertEqual(result["invalid_payloads"], 1)
        self.assertEqual(len(result["skipped_records"]), 1)
        self.assertEqual(result["skipped_records"][0]["reason"], "validation_failed")


# ── 4. field distributions ───────────────────────────────────────────────────

class TrendDistributionTests(_IsolatedStoreTestCase):
    def test_field_distributions_count_categorical_values(self) -> None:
        # 5 bullish + 3 bearish → final_direction: 偏多=5, 偏空=3
        for _ in range(5):
            ps.save_prediction(
                "AVGO", "2026-04-11", None, None,
                _predict_result(bias="bullish", pred_close="收涨"),
            )
        for _ in range(3):
            ps.save_prediction(
                "AVGO", "2026-04-11", None, None,
                _predict_result(bias="bearish", pred_close="收跌",
                                 pred_open="低开", pred_path="低开低走"),
            )
        result = summarize_recent_contract_payloads(limit=8)
        self.assertEqual(result["status"], "ok")
        dist = result["field_distributions"]
        self.assertEqual(
            dist["final_projection.final_direction"], {"偏多": 5, "偏空": 3}
        )
        self.assertEqual(
            dist["final_projection.final_five_state"], {"小涨": 5, "小跌": 3}
        )
        # exclusion_level always defaults to "none" via adapter.
        self.assertEqual(
            dist["exclusion_system.exclusion_level"], {"none": 8}
        )

    def test_field_distributions_cover_all_categorical_diff_paths(self) -> None:
        ps.save_prediction("AVGO", "2026-04-11", None, None, _predict_result())
        result = summarize_recent_contract_payloads()
        # 9 categorical (10 DIFF_PATHS - 1 numeric).
        categorical_paths = {
            f"{section}.{field}"
            for section, field in DIFF_PATHS
            if f"{section}.{field}" != "confidence_system.total_confidence"
        }
        self.assertEqual(set(result["field_distributions"].keys()), categorical_paths)
        self.assertEqual(len(result["field_distributions"]), 9)


# ── 5. numeric stats ─────────────────────────────────────────────────────────

class TrendNumericStatsTests(_IsolatedStoreTestCase):
    def test_total_confidence_min_max_mean_correct(self) -> None:
        # 5 medium (0.50) + 3 low (0.25) + 2 high (0.75) → expected:
        # min=0.25, max=0.75, mean=(5*0.5 + 3*0.25 + 2*0.75) / 10 = 4.75/10 = 0.475
        for _ in range(5):
            ps.save_prediction(
                "AVGO", "2026-04-11", None, None,
                _predict_result(confidence="medium"),
            )
        for _ in range(3):
            ps.save_prediction(
                "AVGO", "2026-04-11", None, None,
                _predict_result(confidence="low"),
            )
        for _ in range(2):
            ps.save_prediction(
                "AVGO", "2026-04-11", None, None,
                _predict_result(confidence="high"),
            )
        result = summarize_recent_contract_payloads(limit=10)
        stats = result["numeric_stats"]["confidence_system.total_confidence"]
        self.assertEqual(stats["min"], 0.25)
        self.assertEqual(stats["max"], 0.75)
        self.assertAlmostEqual(stats["mean"], 0.475, places=6)

    def test_numeric_stats_keys_are_only_total_confidence(self) -> None:
        ps.save_prediction("AVGO", "2026-04-11", None, None, _predict_result())
        result = summarize_recent_contract_payloads()
        self.assertEqual(
            set(result["numeric_stats"].keys()),
            {"confidence_system.total_confidence"},
        )


# ── 6. latest_values uses most recent valid payload ──────────────────────────

class TrendLatestValuesTests(_IsolatedStoreTestCase):
    def test_latest_values_take_most_recently_created_valid_payload(self) -> None:
        # Save bearish first, then bullish — bullish is the most recent.
        ps.save_prediction(
            "AVGO", "2026-04-09", None, None,
            _predict_result(bias="bearish", pred_close="收跌",
                             pred_open="低开", pred_path="低开低走"),
        )
        ps.save_prediction(
            "AVGO", "2026-04-10", None, None,
            _predict_result(bias="bullish", pred_close="收涨"),
        )
        result = summarize_recent_contract_payloads()
        latest = result["latest_values"]
        self.assertEqual(latest["final_projection.final_direction"], "偏多")
        self.assertEqual(latest["final_projection.final_five_state"], "小涨")

    def test_latest_values_skip_invalid_and_pick_first_valid(self) -> None:
        # Most recent is INVALID; the value just below it is bullish (valid).
        ps.save_prediction(
            "AVGO", "2026-04-09", None, None,
            _predict_result(bias="bullish", pred_close="收涨"),
        )
        ps.save_prediction(
            "AVGO", "2026-04-10", None, None, _predict_result(),
            contract_payload={"only_one_section": "bogus"},  # invalid (latest)
        )
        result = summarize_recent_contract_payloads()
        # invalid latest → latest_values picks the bullish one below it.
        self.assertEqual(
            result["latest_values"]["final_projection.final_direction"], "偏多"
        )

    def test_latest_values_cover_all_diff_paths(self) -> None:
        ps.save_prediction("AVGO", "2026-04-11", None, None, _predict_result())
        result = summarize_recent_contract_payloads()
        all_paths = {f"{section}.{field}" for section, field in DIFF_PATHS}
        self.assertEqual(set(result["latest_values"].keys()), all_paths)
        self.assertEqual(len(result["latest_values"]), 10)


# ── 7. limit / 8. invalid limit ──────────────────────────────────────────────

class TrendLimitTests(_IsolatedStoreTestCase):
    def test_limit_truncates_records_scanned(self) -> None:
        for _ in range(15):
            ps.save_prediction("AVGO", "2026-04-11", None, None, _predict_result())
        result = summarize_recent_contract_payloads(limit=5)
        self.assertEqual(result["requested_limit"], 5)
        self.assertEqual(result["records_scanned"], 5)
        self.assertEqual(result["valid_payloads"], 5)

    def test_limit_above_total_records_yields_all_records(self) -> None:
        for _ in range(3):
            ps.save_prediction("AVGO", "2026-04-11", None, None, _predict_result())
        result = summarize_recent_contract_payloads(limit=10)
        self.assertEqual(result["requested_limit"], 10)
        self.assertEqual(result["records_scanned"], 3)

    def test_zero_limit_falls_back_to_default_10(self) -> None:
        for _ in range(12):
            ps.save_prediction("AVGO", "2026-04-11", None, None, _predict_result())
        result = summarize_recent_contract_payloads(limit=0)
        self.assertEqual(result["requested_limit"], 10)
        self.assertEqual(result["records_scanned"], 10)

    def test_negative_limit_falls_back_to_default_10(self) -> None:
        for _ in range(12):
            ps.save_prediction("AVGO", "2026-04-11", None, None, _predict_result())
        result = summarize_recent_contract_payloads(limit=-5)
        self.assertEqual(result["requested_limit"], 10)
        self.assertEqual(result["records_scanned"], 10)

    def test_non_int_limit_falls_back_to_default_10(self) -> None:
        for _ in range(12):
            ps.save_prediction("AVGO", "2026-04-11", None, None, _predict_result())
        result = summarize_recent_contract_payloads(limit="abc")  # type: ignore[arg-type]
        self.assertEqual(result["requested_limit"], 10)
        self.assertEqual(result["records_scanned"], 10)

    def test_bool_limit_falls_back_to_default_10(self) -> None:
        for _ in range(12):
            ps.save_prediction("AVGO", "2026-04-11", None, None, _predict_result())
        # bool is a subclass of int in Python; True would otherwise mean limit=1.
        result = summarize_recent_contract_payloads(limit=True)  # type: ignore[arg-type]
        self.assertEqual(result["requested_limit"], 10)


# ── 9. read-only ────────────────────────────────────────────────────────────

class TrendReadOnlyTests(_IsolatedStoreTestCase):
    def test_trend_does_not_change_row_count_or_field_values(self) -> None:
        for _ in range(5):
            ps.save_prediction("AVGO", "2026-04-11", None, None, _predict_result())
        with ps._get_conn() as conn:
            count_before = conn.execute(
                "SELECT COUNT(*) FROM prediction_log"
            ).fetchone()[0]
            rows_before = [
                dict(r) for r in conn.execute("SELECT * FROM prediction_log")
            ]

        summarize_recent_contract_payloads()
        summarize_recent_contract_payloads(limit=3)
        summarize_recent_contract_payloads(limit=100)

        with ps._get_conn() as conn:
            count_after = conn.execute(
                "SELECT COUNT(*) FROM prediction_log"
            ).fetchone()[0]
            rows_after = [
                dict(r) for r in conn.execute("SELECT * FROM prediction_log")
            ]
        self.assertEqual(count_before, count_after)
        self.assertEqual(rows_before, rows_after)


# ── 10. DB error path ───────────────────────────────────────────────────────

class TrendErrorPathTests(unittest.TestCase):
    def test_unreadable_db_path_returns_error_status(self) -> None:
        # Pointing at a directory makes the SELECT fail. Must report
        # "error" rather than raise.
        with tempfile.TemporaryDirectory() as tmpdir:
            result = summarize_recent_contract_payloads(db_path=tmpdir)
        self.assertEqual(result["status"], "error")
        self.assertTrue(result["error"].startswith("db_read_failed"))


# ── 11. DIFF_PATHS reuse contract sanity ────────────────────────────────────

class TrendFieldSetTests(_IsolatedStoreTestCase):
    def test_field_set_is_exactly_diff_paths(self) -> None:
        # All inspected paths (categorical + numeric + latest_values) must be
        # the union of DIFF_PATHS — keeps trend and diff in lockstep.
        ps.save_prediction("AVGO", "2026-04-11", None, None, _predict_result())
        result = summarize_recent_contract_payloads()
        all_paths = {f"{section}.{field}" for section, field in DIFF_PATHS}
        self.assertEqual(
            set(result["field_distributions"].keys())
            | set(result["numeric_stats"].keys()),
            all_paths,
        )
        self.assertEqual(set(result["latest_values"].keys()), all_paths)


if __name__ == "__main__":
    unittest.main()
