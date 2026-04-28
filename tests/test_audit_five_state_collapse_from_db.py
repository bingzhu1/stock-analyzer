"""Tests for Task 084 — five-state collapse audit (DB-backed, audit-only)."""
from __future__ import annotations

import csv
import importlib.util
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


_AUDIT_PATH = ROOT / "scripts" / "audit_five_state_collapse_from_db.py"
_spec = importlib.util.spec_from_file_location(
    "audit_five_state_collapse_from_db", _AUDIT_PATH
)
assert _spec is not None and _spec.loader is not None
audit_mod = importlib.util.module_from_spec(_spec)
sys.modules["audit_five_state_collapse_from_db"] = audit_mod
_spec.loader.exec_module(audit_mod)


def _new_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE projection_runs (
            run_id TEXT PRIMARY KEY,
            symbol TEXT NOT NULL,
            as_of_date TEXT NOT NULL,
            prediction_for_date TEXT,
            created_at TEXT NOT NULL,
            status TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE record_02_projection (
            run_id TEXT PRIMARY KEY,
            five_state_top1 TEXT,
            final_direction TEXT,
            five_state_distribution_json TEXT,
            payload_json TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def _distribution(
    *,
    top1: str,
    second: str,
    top1_prob: float,
    second_prob: float,
) -> dict[str, float]:
    remaining = 1.0 - top1_prob - second_prob
    assert remaining >= 0.0
    leftover_states = [
        state for state in audit_mod.CANONICAL_STATES
        if state not in {top1, second}
    ]
    shared = remaining / len(leftover_states)
    out = {state: shared for state in leftover_states}
    out[top1] = top1_prob
    out[second] = second_prob
    return out


def _insert_run(
    conn: sqlite3.Connection,
    *,
    idx: int,
    run_id: str | None = None,
    symbol: str = "AVGO",
    five_state_top1: str = "震荡",
    final_direction: str = "偏多",
    distribution: dict[str, Any] | str | None = None,
) -> str:
    rid = run_id or f"run_{idx:02d}"
    as_of_date = f"2026-04-{idx + 1:02d}"
    prediction_for_date = f"2026-04-{idx + 2:02d}"
    created_at = f"2026-04-28T00:00:{idx:02d}Z"
    dist_json = distribution
    if isinstance(distribution, dict):
        dist_json = json.dumps(distribution, ensure_ascii=False)
    conn.execute(
        """
        INSERT INTO projection_runs (
            run_id, symbol, as_of_date, prediction_for_date, created_at, status
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (rid, symbol, as_of_date, prediction_for_date, created_at, "done"),
    )
    conn.execute(
        """
        INSERT INTO record_02_projection (
            run_id, five_state_top1, final_direction,
            five_state_distribution_json, payload_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (rid, five_state_top1, final_direction, dist_json, "{}", created_at),
    )
    conn.commit()
    return rid


def _fetch(conn: sqlite3.Connection) -> list[dict]:
    return audit_mod.fetch_runs(conn, symbol="AVGO")


class InsufficientDataTests(unittest.TestCase):
    def test_insufficient_data_when_fewer_than_five_rows(self) -> None:
        conn = _new_conn()
        try:
            for idx in range(4):
                _insert_run(
                    conn,
                    idx=idx,
                    five_state_top1="震荡",
                    final_direction="偏多",
                    distribution=_distribution(
                        top1="震荡",
                        second="小涨",
                        top1_prob=0.60,
                        second_prob=0.20,
                    ),
                )
            result = audit_mod.audit_runs(runs=_fetch(conn), symbol="AVGO")
            self.assertEqual(result["judgment"], audit_mod.JUDGMENT_INSUFFICIENT_DATA)
            self.assertTrue(result["flags"]["insufficient_data"])
        finally:
            conn.close()


class CollapseAndMismatchTests(unittest.TestCase):
    def test_detects_top1_collapse(self) -> None:
        conn = _new_conn()
        try:
            top1_labels = ["震荡"] * 8 + ["小涨", "小跌"]
            directions = ["偏多", "偏空", "中性", "偏多", "偏空"] * 2
            for idx, top1 in enumerate(top1_labels):
                second = "小涨" if top1 != "小涨" else "震荡"
                _insert_run(
                    conn,
                    idx=idx,
                    five_state_top1=top1,
                    final_direction=directions[idx],
                    distribution=_distribution(
                        top1=top1,
                        second=second,
                        top1_prob=0.62,
                        second_prob=0.18,
                    ),
                )
            result = audit_mod.audit_runs(runs=_fetch(conn), symbol="AVGO")
            self.assertEqual(
                result["judgment"], audit_mod.JUDGMENT_FIVE_STATE_TOP1_COLLAPSED
            )
            self.assertTrue(result["flags"]["five_state_top1_collapse"])
            self.assertEqual(result["five_state_top1_distribution"]["震荡"], 8)
        finally:
            conn.close()

    def test_detects_final_direction_collapse(self) -> None:
        conn = _new_conn()
        try:
            top1_labels = ["震荡"] * 4 + ["小涨"] * 3 + ["小跌"] * 3
            directions = ["偏多"] * 8 + ["偏空", "中性"]
            for idx, (top1, direction) in enumerate(zip(top1_labels, directions, strict=True)):
                second = "小涨" if top1 != "小涨" else "震荡"
                _insert_run(
                    conn,
                    idx=idx,
                    five_state_top1=top1,
                    final_direction=direction,
                    distribution=_distribution(
                        top1=top1,
                        second=second,
                        top1_prob=0.61,
                        second_prob=0.19,
                    ),
                )
            result = audit_mod.audit_runs(runs=_fetch(conn), symbol="AVGO")
            self.assertEqual(
                result["judgment"], audit_mod.JUDGMENT_FINAL_DIRECTION_COLLAPSED
            )
            self.assertTrue(result["flags"]["final_direction_collapse"])
            self.assertEqual(result["final_direction_distribution"]["偏多"], 8)
        finally:
            conn.close()

    def test_detects_direction_state_mismatch_flag_and_joint_distribution(self) -> None:
        conn = _new_conn()
        try:
            for idx in range(8):
                _insert_run(
                    conn,
                    idx=idx,
                    five_state_top1="震荡",
                    final_direction="偏多",
                    distribution=_distribution(
                        top1="震荡",
                        second="小涨",
                        top1_prob=0.60,
                        second_prob=0.20,
                    ),
                )
            _insert_run(
                conn,
                idx=8,
                five_state_top1="小涨",
                final_direction="偏空",
                distribution=_distribution(
                    top1="小涨",
                    second="震荡",
                    top1_prob=0.60,
                    second_prob=0.20,
                ),
            )
            _insert_run(
                conn,
                idx=9,
                five_state_top1="小跌",
                final_direction="中性",
                distribution=_distribution(
                    top1="小跌",
                    second="震荡",
                    top1_prob=0.60,
                    second_prob=0.20,
                ),
            )
            result = audit_mod.audit_runs(runs=_fetch(conn), symbol="AVGO")
            self.assertTrue(result["flags"]["direction_state_mismatch"])
            self.assertEqual(result["joint_distribution"]["震荡|偏多"], 8)
            self.assertEqual(
                result["direction_state_mismatch"]["share"],
                0.8,
            )
        finally:
            conn.close()


class ProbabilityParsingTests(unittest.TestCase):
    def test_parses_five_state_distribution_json_correctly(self) -> None:
        parsed, reason = audit_mod.parse_five_state_distribution(
            json.dumps({
                "大涨": "5%",
                "小涨": "42%",
                "震荡": "45%",
                "小跌": "4%",
                "大跌": "4%",
            }, ensure_ascii=False)
        )
        self.assertIsNone(reason)
        assert parsed is not None
        self.assertAlmostEqual(parsed["震荡"], 0.45)
        self.assertAlmostEqual(parsed["小涨"], 0.42)

    def test_computes_top1_margin_and_second_state(self) -> None:
        margin_case, reason = audit_mod.build_margin_case({
            "run_id": "r1",
            "as_of_date": "2026-04-01",
            "prediction_for_date": "2026-04-02",
            "five_state_top1": "震荡",
            "final_direction": "偏多",
            "five_state_distribution_json": json.dumps({
                "大涨": 0.05,
                "小涨": 0.42,
                "震荡": 0.45,
                "小跌": 0.04,
                "大跌": 0.04,
            }, ensure_ascii=False),
        })
        self.assertIsNone(reason)
        assert margin_case is not None
        self.assertEqual(margin_case["derived_top1"], "震荡")
        self.assertEqual(margin_case["second_state"], "小涨")
        self.assertAlmostEqual(margin_case["top1_margin"], 0.03)

    def test_handles_malformed_probability_json(self) -> None:
        conn = _new_conn()
        try:
            for idx in range(7):
                _insert_run(
                    conn,
                    idx=idx,
                    five_state_top1="震荡" if idx < 3 else "小涨",
                    final_direction="偏多" if idx % 2 == 0 else "偏空",
                    distribution=_distribution(
                        top1="震荡" if idx < 3 else "小涨",
                        second="小涨" if idx < 3 else "震荡",
                        top1_prob=0.60,
                        second_prob=0.20,
                    ),
                )
            _insert_run(conn, idx=7, distribution="{bad json")
            _insert_run(
                conn,
                idx=8,
                distribution=json.dumps({"震荡": 0.5, "小涨": 0.4}, ensure_ascii=False),
            )
            _insert_run(
                conn,
                idx=9,
                distribution=json.dumps({
                    "大涨": 0.05,
                    "小涨": "oops",
                    "震荡": 0.45,
                    "小跌": 0.25,
                    "大跌": 0.25,
                }, ensure_ascii=False),
            )
            result = audit_mod.audit_runs(runs=_fetch(conn), symbol="AVGO")
            self.assertEqual(
                result["judgment"], audit_mod.JUDGMENT_MALFORMED_PROBABILITY_DATA
            )
            self.assertTrue(result["flags"]["malformed_probability_data"])
            self.assertEqual(result["malformed_probability_rows"], 3)
        finally:
            conn.close()


class MarginAndNoCollapseTests(unittest.TestCase):
    def test_detects_low_margin_top1_problem(self) -> None:
        conn = _new_conn()
        try:
            labels = ["震荡", "震荡", "震荡", "小涨", "小涨", "小跌", "小跌", "大涨", "大涨", "大跌"]
            directions = ["偏多", "偏空", "中性", "偏多", "偏空", "中性", "偏多", "偏空", "中性", "偏多"]
            for idx, (top1, direction) in enumerate(zip(labels, directions, strict=True)):
                if idx < 6:
                    top1_prob, second_prob = 0.45, 0.42
                else:
                    top1_prob, second_prob = 0.62, 0.18
                second = "小涨" if top1 != "小涨" else "震荡"
                _insert_run(
                    conn,
                    idx=idx,
                    five_state_top1=top1,
                    final_direction=direction,
                    distribution=_distribution(
                        top1=top1,
                        second=second,
                        top1_prob=top1_prob,
                        second_prob=second_prob,
                    ),
                )
            result = audit_mod.audit_runs(runs=_fetch(conn), symbol="AVGO")
            self.assertEqual(
                result["judgment"], audit_mod.JUDGMENT_LOW_MARGIN_TOP1_PROBLEM
            )
            self.assertTrue(result["flags"]["low_margin_problem"])
            self.assertEqual(result["margin_buckets"]["lt_0_05"]["count"], 6)
            self.assertAlmostEqual(result["margin_buckets"]["lt_0_05"]["share"], 0.6)
        finally:
            conn.close()

    def test_no_collapse_branch_works(self) -> None:
        conn = _new_conn()
        try:
            labels = ["震荡", "震荡", "小涨", "小涨", "小跌", "小跌", "大涨", "大涨", "大跌", "大跌"]
            directions = ["偏多", "偏空", "中性", "偏多", "偏空", "中性", "偏多", "偏空", "中性", "偏多"]
            for idx, (top1, direction) in enumerate(zip(labels, directions, strict=True)):
                second = "小涨" if top1 != "小涨" else "震荡"
                _insert_run(
                    conn,
                    idx=idx,
                    five_state_top1=top1,
                    final_direction=direction,
                    distribution=_distribution(
                        top1=top1,
                        second=second,
                        top1_prob=0.62,
                        second_prob=0.18,
                    ),
                )
            result = audit_mod.audit_runs(runs=_fetch(conn), symbol="AVGO")
            self.assertEqual(result["judgment"], audit_mod.JUDGMENT_NO_COLLAPSE)
            self.assertFalse(result["flags"]["five_state_top1_collapse"])
            self.assertFalse(result["flags"]["final_direction_collapse"])
            self.assertIn("震荡|偏多", result["joint_distribution"])
        finally:
            conn.close()


class SummaryAndOutputsTests(unittest.TestCase):
    def test_probability_summary_averages_are_correct(self) -> None:
        runs = [
            {
                "run_id": "a",
                "as_of_date": "2026-04-01",
                "prediction_for_date": "2026-04-02",
                "five_state_top1": "震荡",
                "final_direction": "偏多",
                "five_state_distribution_json": json.dumps({
                    "大涨": 0.10,
                    "小涨": 0.20,
                    "震荡": 0.30,
                    "小跌": 0.20,
                    "大跌": 0.20,
                }, ensure_ascii=False),
            },
            {
                "run_id": "b",
                "as_of_date": "2026-04-03",
                "prediction_for_date": "2026-04-04",
                "five_state_top1": "小涨",
                "final_direction": "偏空",
                "five_state_distribution_json": json.dumps({
                    "大涨": 0.20,
                    "小涨": 0.30,
                    "震荡": 0.10,
                    "小跌": 0.20,
                    "大跌": 0.20,
                }, ensure_ascii=False),
            },
        ]
        result = audit_mod.audit_runs(runs=runs, symbol="AVGO")
        summary = {
            row["state"]: row["average_probability"]
            for row in result["five_state_probability_summary"]
        }
        self.assertAlmostEqual(summary["大涨"], 0.15)
        self.assertAlmostEqual(summary["小涨"], 0.25)
        self.assertAlmostEqual(summary["震荡"], 0.20)

    def test_writes_all_output_files(self) -> None:
        conn = _new_conn()
        try:
            labels = ["震荡", "震荡", "小涨", "小涨", "小跌"]
            directions = ["偏多", "偏空", "中性", "偏多", "偏空"]
            for idx, (top1, direction) in enumerate(zip(labels, directions, strict=True)):
                second = "小涨" if top1 != "小涨" else "震荡"
                _insert_run(
                    conn,
                    idx=idx,
                    five_state_top1=top1,
                    final_direction=direction,
                    distribution=_distribution(
                        top1=top1,
                        second=second,
                        top1_prob=0.62,
                        second_prob=0.18,
                    ),
                )
            result = audit_mod.audit_runs(runs=_fetch(conn), symbol="AVGO")
            with tempfile.TemporaryDirectory() as tmpdir:
                out = Path(tmpdir)
                audit_mod.write_audit_outputs(result, out)
                expected = {
                    "five_state_collapse_audit.json",
                    "five_state_collapse_audit.md",
                    "five_state_top1_distribution.csv",
                    "final_direction_distribution.csv",
                    "five_state_margin_cases.csv",
                    "five_state_probability_summary.csv",
                    "direction_state_mismatch_cases.csv",
                }
                self.assertEqual(expected, {path.name for path in out.iterdir()})

                payload = json.loads(
                    (out / "five_state_collapse_audit.json").read_text(encoding="utf-8")
                )
                self.assertEqual(payload["symbol"], "AVGO")

                with (out / "five_state_margin_cases.csv").open(
                    "r", encoding="utf-8", newline=""
                ) as fh:
                    rows = list(csv.DictReader(fh))
                self.assertEqual(len(rows), 5)
                self.assertIn("top1_margin", rows[0])
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
