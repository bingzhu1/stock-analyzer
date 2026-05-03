"""Tests for services/contract_replay_writer.py (Step 2F-4c-1).

The writer is a dry-run-only skeleton today: ``dry_run=True`` is the
default, and ``dry_run=False`` returns ``status="not_implemented_for_write"``
without calling ``run_predict`` / ``save_prediction`` / ``save_outcome``.
These tests pin that contract so the future Step 2F-4c-2 cannot
accidentally regress the safety bounds.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services import contract_replay_writer as crw
from services.contract_replay_writer import run_contract_replay


def _write_csv(dir_path: Path, symbol: str, dates: list[str]) -> Path:
    """Write a minimal coded CSV with only Date / Open / Close columns."""
    csv_path = dir_path / f"{symbol}_coded.csv"
    lines = ["Date,Open,Close"] + [f"{d},100.0,101.0" for d in dates]
    csv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return csv_path


# ── 1. dry_run is the default and is read-only ──────────────────────────────

class WriterDryRunDefaultTests(unittest.TestCase):
    def test_dry_run_default_is_true(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _write_csv(tmp_path, "AVGO", ["2024-01-02", "2024-01-03"])
            result = run_contract_replay(coded_data_dir=tmp_path)
        self.assertIs(result["dry_run"], True)
        self.assertEqual(result["status"], "ok")

    def test_dry_run_returns_candidate_pairs_from_planner(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _write_csv(tmp_path, "AVGO", [
                "2024-01-02", "2024-01-03", "2024-01-04",
            ])
            result = run_contract_replay(coded_data_dir=tmp_path)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["candidate_pair_count"], 2)
        self.assertEqual(result["would_write_count"], 2)
        self.assertEqual(result["written_prediction_count"], 0)
        self.assertEqual(result["written_outcome_count"], 0)
        self.assertEqual(result["candidate_pairs"], [
            {"as_of_date": "2024-01-02", "prediction_for_date": "2024-01-03"},
            {"as_of_date": "2024-01-03", "prediction_for_date": "2024-01-04"},
        ])

    def test_dry_run_includes_planner_result_passthrough(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _write_csv(tmp_path, "AVGO", ["2024-01-02", "2024-01-03"])
            result = run_contract_replay(coded_data_dir=tmp_path)
        self.assertIn("planner_result", result)
        self.assertEqual(result["planner_status"], "ok")
        self.assertEqual(
            result["planner_result"]["data_source_status"], "ok"
        )

    def test_dry_run_notes_explain_no_writes_happened(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _write_csv(tmp_path, "AVGO", ["2024-01-02", "2024-01-03"])
            result = run_contract_replay(coded_data_dir=tmp_path)
        self.assertTrue(any(
            "dry_run=True" in note and "no prediction" in note
            for note in result["notes"]
        ))


# ── 2. dry_run does NOT call run_predict / save_prediction / save_outcome ──

class WriterDryRunDoesNotInvokeWritePathTests(unittest.TestCase):
    """The skeleton must never reach the real write functions, regardless
    of what dry_run is set to (4c-1 stops before run_predict in both)."""

    def _csv_dir(self, tmp_path: Path) -> Path:
        _write_csv(tmp_path, "AVGO", ["2024-01-02", "2024-01-03", "2024-01-04"])
        return tmp_path

    def test_dry_run_does_not_call_run_predict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = self._csv_dir(Path(tmp))
            with patch("predict.run_predict") as mock_run_predict:
                run_contract_replay(coded_data_dir=tmp_path, dry_run=True)
            self.assertEqual(mock_run_predict.call_count, 0)

    def test_dry_run_does_not_call_save_prediction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = self._csv_dir(Path(tmp))
            with patch("services.prediction_store.save_prediction") as mock_save:
                run_contract_replay(coded_data_dir=tmp_path, dry_run=True)
            self.assertEqual(mock_save.call_count, 0)

    def test_dry_run_does_not_call_save_outcome(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = self._csv_dir(Path(tmp))
            with patch("services.prediction_store.save_outcome") as mock_save:
                run_contract_replay(coded_data_dir=tmp_path, dry_run=True)
            self.assertEqual(mock_save.call_count, 0)


# ── 3. planner failure modes pass through ──────────────────────────────────

class WriterPlannerPassthroughTests(unittest.TestCase):
    def test_planner_missing_data_passes_through(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            nonexistent = Path(tmp) / "no_dir_here"
            result = run_contract_replay(coded_data_dir=nonexistent)
        self.assertEqual(result["status"], "missing_data")
        self.assertEqual(result["candidate_pair_count"], 0)
        self.assertEqual(result["would_write_count"], 0)
        self.assertEqual(result["written_prediction_count"], 0)
        self.assertTrue(any(
            "planner returned" in n and "missing_data" in n
            for n in result["notes"]
        ))

    def test_planner_insufficient_data_passes_through(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _write_csv(tmp_path, "AVGO", ["2024-01-02"])  # only 1 day
            result = run_contract_replay(coded_data_dir=tmp_path)
        self.assertEqual(result["status"], "insufficient_data")
        self.assertEqual(result["candidate_pair_count"], 0)

    def test_planner_error_passes_through(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _write_csv(tmp_path, "AVGO", ["2024-01-02", "2024-01-03"])
            result = run_contract_replay(
                coded_data_dir=tmp_path, start_date="not-a-date",
            )
        self.assertEqual(result["status"], "error")


# ── 4. parameters are forwarded to the planner ─────────────────────────────

class WriterParameterForwardingTests(unittest.TestCase):
    def test_symbol_passed_through(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _write_csv(tmp_path, "NVDA", ["2024-01-02", "2024-01-03"])
            result = run_contract_replay(
                coded_data_dir=tmp_path, symbol="nvda",
            )
        self.assertEqual(result["symbol"], "NVDA")

    def test_start_end_passed_through(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _write_csv(tmp_path, "AVGO", [
                "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05",
            ])
            result = run_contract_replay(
                coded_data_dir=tmp_path,
                start_date="2024-01-03", end_date="2024-01-04",
            )
        # planner narrows to 2 days → 1 pair
        self.assertEqual(result["candidate_pair_count"], 1)
        self.assertEqual(
            result["candidate_pairs"][0]["as_of_date"], "2024-01-03",
        )

    def test_coded_data_dir_passed_through(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _write_csv(tmp_path, "AVGO", ["2024-01-02", "2024-01-03"])
            # Use a non-default subdirectory to make the param meaningful.
            result = run_contract_replay(coded_data_dir=tmp_path)
        self.assertIn(
            str(tmp_path), result["planner_result"]["data_source"],
        )


# ── 5. limit handling (+ writer's hard cap) ───────────────────────────────

class WriterLimitTests(unittest.TestCase):
    def _seed_many(self, tmp_path: Path, n: int) -> None:
        # Generate n synthetic trading days starting 2024-01-01.
        from datetime import date, timedelta
        dates = [
            (date(2024, 1, 1) + timedelta(days=i)).isoformat()
            for i in range(n)
        ]
        _write_csv(tmp_path, "AVGO", dates)

    def test_default_limit_is_30(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            self._seed_many(tmp_path, 60)
            result = run_contract_replay(coded_data_dir=tmp_path)
        self.assertEqual(result["requested_limit"], 30)
        # 60 days → 59 pairs estimated; default limit caps at 30.
        self.assertEqual(result["candidate_pair_count"], 30)

    def test_limit_clamped_at_hard_cap_50(self) -> None:
        # Caller asks for 200 but writer must cap to 50.
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            self._seed_many(tmp_path, 100)
            result = run_contract_replay(
                coded_data_dir=tmp_path, limit=200,
            )
        self.assertEqual(result["requested_limit"], 50)
        self.assertEqual(result["candidate_pair_count"], 50)

    def test_limit_at_cap_passes_through(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            self._seed_many(tmp_path, 60)
            result = run_contract_replay(
                coded_data_dir=tmp_path, limit=50,
            )
        self.assertEqual(result["requested_limit"], 50)
        self.assertEqual(result["candidate_pair_count"], 50)

    def test_zero_limit_falls_back_to_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            self._seed_many(tmp_path, 60)
            result = run_contract_replay(coded_data_dir=tmp_path, limit=0)
        self.assertEqual(result["requested_limit"], 30)

    def test_non_int_limit_falls_back_to_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            self._seed_many(tmp_path, 60)
            result = run_contract_replay(
                coded_data_dir=tmp_path, limit="abc",  # type: ignore[arg-type]
            )
        self.assertEqual(result["requested_limit"], 30)

    def test_bool_limit_falls_back_to_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            self._seed_many(tmp_path, 60)
            result = run_contract_replay(
                coded_data_dir=tmp_path, limit=True,  # type: ignore[arg-type]
            )
        self.assertEqual(result["requested_limit"], 30)


# ── 6. dry_run=False (write attempt) returns not_implemented + no DB calls ─

class WriterWriteAttemptIsStubbedTests(unittest.TestCase):
    def test_write_attempt_returns_not_implemented_for_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _write_csv(tmp_path, "AVGO", ["2024-01-02", "2024-01-03"])
            result = run_contract_replay(
                coded_data_dir=tmp_path, dry_run=False,
            )
        self.assertEqual(result["status"], "not_implemented_for_write")
        self.assertEqual(result["written_prediction_count"], 0)
        self.assertEqual(result["written_outcome_count"], 0)
        self.assertEqual(result["would_write_count"], 1)

    def test_write_attempt_does_not_call_run_predict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _write_csv(tmp_path, "AVGO", ["2024-01-02", "2024-01-03"])
            with patch("predict.run_predict") as mock_run_predict:
                run_contract_replay(coded_data_dir=tmp_path, dry_run=False)
            self.assertEqual(mock_run_predict.call_count, 0)

    def test_write_attempt_does_not_call_save_prediction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _write_csv(tmp_path, "AVGO", ["2024-01-02", "2024-01-03"])
            with patch("services.prediction_store.save_prediction") as mock_save:
                run_contract_replay(coded_data_dir=tmp_path, dry_run=False)
            self.assertEqual(mock_save.call_count, 0)

    def test_write_attempt_does_not_call_save_outcome(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _write_csv(tmp_path, "AVGO", ["2024-01-02", "2024-01-03"])
            with patch("services.prediction_store.save_outcome") as mock_save:
                run_contract_replay(coded_data_dir=tmp_path, dry_run=False)
            self.assertEqual(mock_save.call_count, 0)

    def test_write_attempt_notes_explain_skeleton_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _write_csv(tmp_path, "AVGO", ["2024-01-02", "2024-01-03"])
            result = run_contract_replay(
                coded_data_dir=tmp_path, dry_run=False,
            )
        joined = " | ".join(result["notes"])
        self.assertIn("skeleton", joined)
        self.assertIn("4c-2", joined)


# ── 7. dependency hygiene ─────────────────────────────────────────────────

class WriterHygieneTests(unittest.TestCase):
    def test_writer_module_does_not_import_yfinance(self) -> None:
        source = Path(crw.__file__).read_text(encoding="utf-8")
        self.assertNotIn("import yfinance", source)
        self.assertNotIn("from yfinance", source)
        self.assertNotIn("yf.Ticker", source)

    def test_writer_module_does_not_import_requests(self) -> None:
        source = Path(crw.__file__).read_text(encoding="utf-8")
        self.assertNotIn("import requests", source)
        self.assertNotIn("from requests", source)


# ── 8. CLI ────────────────────────────────────────────────────────────────

class WriterScriptTests(unittest.TestCase):
    def _run(self, csv_dir: Path, *extra: str) -> dict:
        script = ROOT / "scripts" / "run_contract_replay.py"
        proc = subprocess.run(
            [sys.executable, str(script),
             "--coded-data-dir", str(csv_dir), *extra],
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(proc.stdout)

    def test_cli_default_is_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _write_csv(tmp_path, "AVGO", ["2024-01-02", "2024-01-03"])
            result = self._run(tmp_path)
        self.assertIs(result["dry_run"], True)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["written_prediction_count"], 0)

    def test_cli_write_flag_returns_not_implemented(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _write_csv(tmp_path, "AVGO", ["2024-01-02", "2024-01-03"])
            result = self._run(tmp_path, "--write")
        self.assertIs(result["dry_run"], False)
        self.assertEqual(result["status"], "not_implemented_for_write")
        self.assertEqual(result["written_prediction_count"], 0)
        self.assertEqual(result["written_outcome_count"], 0)


if __name__ == "__main__":
    unittest.main()
