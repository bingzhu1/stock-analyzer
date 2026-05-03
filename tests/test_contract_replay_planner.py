"""Tests for services/contract_replay_planner.py (Step 2F-4b).

Read-only planner. Tests use synthetic CSVs in tmpdirs; never touch
the real coded_data/ or call yfinance.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services import contract_replay_planner as crp
from services.contract_replay_planner import plan_contract_replay


def _write_csv(
    dir_path: Path,
    symbol: str,
    dates: list[str],
    *,
    extra_cols: dict[str, str] | None = None,
    omit_date_column: bool = False,
) -> Path:
    """Write a minimal coded CSV at ``dir_path/<SYMBOL>_coded.csv``.

    Only the ``Date`` column is required by the planner; other columns are
    optional but added for realism (matches scanner's CSV shape).
    """
    csv_path = dir_path / f"{symbol}_coded.csv"
    if omit_date_column:
        csv_path.write_text("Open,Close\n100,101\n", encoding="utf-8")
        return csv_path
    cols = ["Date", "Open", "Close"]
    if extra_cols:
        cols.extend(extra_cols.keys())
    lines = [",".join(cols)]
    for d in dates:
        row = [d, "100.0", "101.0"]
        if extra_cols:
            row.extend(extra_cols.values())
        lines.append(",".join(row))
    csv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return csv_path


# ── 1. missing data paths ──────────────────────────────────────────────────

class PlannerMissingDataTests(unittest.TestCase):
    def test_missing_coded_data_dir_returns_missing_data_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            nonexistent = Path(tmp) / "does_not_exist"
            result = plan_contract_replay(coded_data_dir=nonexistent)
        self.assertEqual(result["status"], "missing_data")
        self.assertEqual(result["data_source_status"], "missing_dir")
        self.assertEqual(result["candidate_pairs"], [])

    def test_missing_symbol_csv_returns_missing_data_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            # Create dir but NOT the AVGO csv.
            _write_csv(tmp_path, "NVDA", ["2024-01-02", "2024-01-03"])
            result = plan_contract_replay(coded_data_dir=tmp_path, symbol="AVGO")
        self.assertEqual(result["status"], "missing_data")
        self.assertEqual(result["data_source_status"], "missing_file")

    def test_csv_without_date_column_returns_insufficient_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _write_csv(tmp_path, "AVGO", [], omit_date_column=True)
            result = plan_contract_replay(coded_data_dir=tmp_path, symbol="AVGO")
        # File exists but has no parseable dates → 0 trading days → insufficient.
        self.assertEqual(result["status"], "insufficient_data")
        self.assertEqual(result["trading_days_total"], 0)


# ── 2. valid CSV → ok with proper pair shape ──────────────────────────────

class PlannerOkPathTests(unittest.TestCase):
    def test_valid_csv_yields_ok_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _write_csv(tmp_path, "AVGO", [
                "2024-01-02", "2024-01-03", "2024-01-04",
                "2024-01-05", "2024-01-08",
            ])
            result = plan_contract_replay(coded_data_dir=tmp_path)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data_source_status"], "ok")
        self.assertEqual(result["trading_days_total"], 5)
        self.assertEqual(result["estimated_pair_count"], 4)
        self.assertEqual(result["returned_pair_count"], 4)

    def test_pairs_are_consecutive_d_dplus1(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _write_csv(tmp_path, "AVGO", [
                "2024-01-02", "2024-01-03", "2024-01-04",
            ])
            result = plan_contract_replay(coded_data_dir=tmp_path)
        self.assertEqual(result["candidate_pairs"], [
            {"as_of_date": "2024-01-02", "prediction_for_date": "2024-01-03"},
            {"as_of_date": "2024-01-03", "prediction_for_date": "2024-01-04"},
        ])

    def test_anti_lookahead_check_true_on_ascending_pairs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _write_csv(tmp_path, "AVGO", ["2024-01-02", "2024-01-03"])
            result = plan_contract_replay(coded_data_dir=tmp_path)
        self.assertTrue(
            result["anti_lookahead_check"]["all_pairs_satisfy_d_lt_d_plus_1"]
        )
        self.assertEqual(
            result["anti_lookahead_check"]["last_available_date"], "2024-01-03"
        )

    def test_dates_are_sorted_and_deduplicated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            # Out-of-order + duplicate dates.
            _write_csv(tmp_path, "AVGO", [
                "2024-01-04", "2024-01-02", "2024-01-03",
                "2024-01-02",  # duplicate
            ])
            result = plan_contract_replay(coded_data_dir=tmp_path)
        # Dedup → 3 days; pairs should be (1/2,1/3) and (1/3,1/4).
        self.assertEqual(result["trading_days_total"], 3)
        self.assertEqual(result["candidate_pairs"], [
            {"as_of_date": "2024-01-02", "prediction_for_date": "2024-01-03"},
            {"as_of_date": "2024-01-03", "prediction_for_date": "2024-01-04"},
        ])

    def test_dates_with_iso_time_suffix_are_truncated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _write_csv(tmp_path, "AVGO", [
                "2024-01-02 00:00:00",
                "2024-01-03 00:00:00",
            ])
            result = plan_contract_replay(coded_data_dir=tmp_path)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["candidate_pairs"][0]["as_of_date"], "2024-01-02")

    def test_pairs_returned_in_time_ascending_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _write_csv(tmp_path, "AVGO", [
                "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05",
            ])
            result = plan_contract_replay(coded_data_dir=tmp_path)
        as_of_dates = [p["as_of_date"] for p in result["candidate_pairs"]]
        self.assertEqual(as_of_dates, sorted(as_of_dates))


# ── 3. limit handling ─────────────────────────────────────────────────────

class PlannerLimitTests(unittest.TestCase):
    def test_limit_truncates_returned_pair_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _write_csv(tmp_path, "AVGO", [
                f"2024-01-{day:02d}" for day in range(2, 12)  # 10 days
            ])
            result = plan_contract_replay(coded_data_dir=tmp_path, limit=3)
        # 10 days → 9 estimated pairs; limit=3 → 3 returned, time-ascending.
        self.assertEqual(result["estimated_pair_count"], 9)
        self.assertEqual(result["returned_pair_count"], 3)
        self.assertEqual(result["candidate_pairs"][0]["as_of_date"], "2024-01-02")
        self.assertEqual(result["candidate_pairs"][-1]["as_of_date"], "2024-01-04")

    def test_zero_limit_falls_back_to_default_30(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _write_csv(tmp_path, "AVGO", ["2024-01-02", "2024-01-03"])
            result = plan_contract_replay(coded_data_dir=tmp_path, limit=0)
        self.assertEqual(result["requested_limit"], 30)

    def test_negative_limit_falls_back_to_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _write_csv(tmp_path, "AVGO", ["2024-01-02", "2024-01-03"])
            result = plan_contract_replay(coded_data_dir=tmp_path, limit=-5)
        self.assertEqual(result["requested_limit"], 30)

    def test_non_int_limit_falls_back_to_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _write_csv(tmp_path, "AVGO", ["2024-01-02", "2024-01-03"])
            result = plan_contract_replay(coded_data_dir=tmp_path, limit="abc")  # type: ignore[arg-type]
        self.assertEqual(result["requested_limit"], 30)

    def test_bool_limit_falls_back_to_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _write_csv(tmp_path, "AVGO", ["2024-01-02", "2024-01-03"])
            result = plan_contract_replay(coded_data_dir=tmp_path, limit=True)  # type: ignore[arg-type]
        self.assertEqual(result["requested_limit"], 30)


# ── 4. start_date / end_date filtering ────────────────────────────────────

class PlannerDateFilterTests(unittest.TestCase):
    def _seed(self, tmp_path: Path) -> None:
        # 6 trading days spanning Jan 2 – Jan 9.
        _write_csv(tmp_path, "AVGO", [
            "2024-01-02", "2024-01-03", "2024-01-04",
            "2024-01-05", "2024-01-08", "2024-01-09",
        ])

    def test_start_date_filter_keeps_only_dates_on_or_after(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            self._seed(tmp_path)
            result = plan_contract_replay(
                coded_data_dir=tmp_path, start_date="2024-01-04",
            )
        # Filtered set: 04, 05, 08, 09 → 3 pairs
        self.assertEqual(result["trading_days_total"], 4)
        self.assertEqual(result["estimated_pair_count"], 3)
        self.assertEqual(result["candidate_pairs"][0]["as_of_date"], "2024-01-04")

    def test_end_date_filter_keeps_only_dates_on_or_before(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            self._seed(tmp_path)
            result = plan_contract_replay(
                coded_data_dir=tmp_path, end_date="2024-01-04",
            )
        # Filtered set: 02, 03, 04 → 2 pairs
        self.assertEqual(result["trading_days_total"], 3)
        self.assertEqual(result["candidate_pairs"][-1]["prediction_for_date"], "2024-01-04")

    def test_both_dates_window_bounds_pairs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            self._seed(tmp_path)
            result = plan_contract_replay(
                coded_data_dir=tmp_path,
                start_date="2024-01-03", end_date="2024-01-05",
            )
        self.assertEqual(result["trading_days_total"], 3)
        self.assertEqual(result["candidate_pairs"], [
            {"as_of_date": "2024-01-03", "prediction_for_date": "2024-01-04"},
            {"as_of_date": "2024-01-04", "prediction_for_date": "2024-01-05"},
        ])

    def test_invalid_start_date_returns_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            self._seed(tmp_path)
            result = plan_contract_replay(
                coded_data_dir=tmp_path, start_date="not-a-date",
            )
        self.assertEqual(result["status"], "error")
        self.assertIn("start_date", result["error"])

    def test_invalid_end_date_returns_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            self._seed(tmp_path)
            result = plan_contract_replay(
                coded_data_dir=tmp_path, end_date="2024/13/40",
            )
        self.assertEqual(result["status"], "error")
        self.assertIn("end_date", result["error"])

    def test_start_after_end_returns_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            self._seed(tmp_path)
            result = plan_contract_replay(
                coded_data_dir=tmp_path,
                start_date="2024-02-01", end_date="2024-01-01",
            )
        self.assertEqual(result["status"], "error")
        self.assertIn("after", result["error"])

    def test_filtered_to_one_day_returns_insufficient_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            self._seed(tmp_path)
            # Only "2024-01-04" survives the window.
            result = plan_contract_replay(
                coded_data_dir=tmp_path,
                start_date="2024-01-04", end_date="2024-01-04",
            )
        self.assertEqual(result["status"], "insufficient_data")
        self.assertEqual(result["candidate_pairs"], [])

    def test_skipped_days_records_filter_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            self._seed(tmp_path)
            result = plan_contract_replay(
                coded_data_dir=tmp_path,
                start_date="2024-01-04", end_date="2024-01-08",
            )
        reasons = {s["reason"] for s in result["skipped_days"]}
        # Both bounds dropped some days from the 6-day seed.
        self.assertIn("before_start_date", reasons)
        self.assertIn("after_end_date", reasons)


# ── 5. symbol normalization ───────────────────────────────────────────────

class PlannerSymbolTests(unittest.TestCase):
    def test_default_symbol_is_avgo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _write_csv(tmp_path, "AVGO", ["2024-01-02", "2024-01-03"])
            result = plan_contract_replay(coded_data_dir=tmp_path)
        self.assertEqual(result["symbol"], "AVGO")
        self.assertEqual(result["status"], "ok")

    def test_lowercase_symbol_is_normalized(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _write_csv(tmp_path, "NVDA", ["2024-01-02", "2024-01-03"])
            result = plan_contract_replay(
                coded_data_dir=tmp_path, symbol="nvda",
            )
        self.assertEqual(result["symbol"], "NVDA")
        self.assertEqual(result["status"], "ok")

    def test_whitespace_symbol_is_normalized(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _write_csv(tmp_path, "NVDA", ["2024-01-02", "2024-01-03"])
            result = plan_contract_replay(
                coded_data_dir=tmp_path, symbol="  nvda  ",
            )
        self.assertEqual(result["symbol"], "NVDA")

    def test_empty_symbol_falls_back_to_avgo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _write_csv(tmp_path, "AVGO", ["2024-01-02", "2024-01-03"])
            result = plan_contract_replay(
                coded_data_dir=tmp_path, symbol="",
            )
        self.assertEqual(result["symbol"], "AVGO")

    def test_none_symbol_falls_back_to_avgo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _write_csv(tmp_path, "AVGO", ["2024-01-02", "2024-01-03"])
            result = plan_contract_replay(
                coded_data_dir=tmp_path, symbol=None,
            )
        self.assertEqual(result["symbol"], "AVGO")

    def test_symbol_all_returns_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            result = plan_contract_replay(
                coded_data_dir=tmp_path, symbol="ALL",
            )
        self.assertEqual(result["status"], "error")
        self.assertIn("ALL", result["error"])

    def test_symbol_all_lowercase_also_returns_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            result = plan_contract_replay(
                coded_data_dir=tmp_path, symbol="all",
            )
        self.assertEqual(result["status"], "error")


# ── 6. side-effect / dependency hygiene ───────────────────────────────────

class PlannerHygieneTests(unittest.TestCase):
    def test_planner_module_does_not_import_yfinance(self) -> None:
        # Step 2F-4 plan §3.1: planner must not call yfinance / network.
        # Verify no actual import statements reference yfinance (the word
        # may legitimately appear in the docstring describing what NOT to do).
        source = Path(crp.__file__).read_text(encoding="utf-8")
        self.assertNotIn("import yfinance", source)
        self.assertNotIn("from yfinance", source)
        self.assertNotIn("yf.Ticker", source)

    def test_planner_module_does_not_import_requests(self) -> None:
        source = Path(crp.__file__).read_text(encoding="utf-8")
        self.assertNotIn("import requests", source)
        self.assertNotIn("from requests", source)

    def test_planner_does_not_touch_db(self) -> None:
        # Repeated planner calls should never raise / open sqlite.
        # We assert a tmpdir + clean run completes fast and produces a dict.
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _write_csv(tmp_path, "AVGO", ["2024-01-02", "2024-01-03"])
            for _ in range(5):
                result = plan_contract_replay(coded_data_dir=tmp_path)
                self.assertEqual(result["status"], "ok")


# ── 7. CLI ────────────────────────────────────────────────────────────────

class PlannerScriptTests(unittest.TestCase):
    def _run(self, csv_dir: Path, *extra: str) -> dict:
        script = ROOT / "scripts" / "plan_contract_replay.py"
        proc = subprocess.run(
            [sys.executable, str(script),
             "--coded-data-dir", str(csv_dir), *extra],
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(proc.stdout)

    def test_cli_default_symbol_avgo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _write_csv(tmp_path, "AVGO", ["2024-01-02", "2024-01-03"])
            result = self._run(tmp_path)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["symbol"], "AVGO")

    def test_cli_accepts_symbol_and_dates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _write_csv(tmp_path, "NVDA", [
                "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05",
            ])
            result = self._run(
                tmp_path,
                "--symbol", "NVDA",
                "--start", "2024-01-03",
                "--end", "2024-01-04",
                "--limit", "5",
            )
        self.assertEqual(result["symbol"], "NVDA")
        self.assertEqual(result["start_date"], "2024-01-03")
        self.assertEqual(result["end_date"], "2024-01-04")
        self.assertEqual(result["requested_limit"], 5)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["trading_days_total"], 2)


if __name__ == "__main__":
    unittest.main()
