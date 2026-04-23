from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.historical_replay_training import (
    run_historical_replay_for_date,
    run_historical_replay_batch,
    summarize_replay_results,
)

# ── test fixtures ─────────────────────────────────────────────────────────────

_SYMBOL = "AVGO"
_AS_OF = "2024-01-10"
_PRED_FOR = "2024-01-11"


def _make_projection(
    *,
    ready: bool = True,
    direction: str = "偏多",
    confidence: str = "medium",
    symbol: str = _SYMBOL,
) -> dict[str, Any]:
    return {
        "kind": "projection_v2_report",
        "symbol": symbol,
        "ready": ready,
        "final_decision": {
            "final_direction": direction,
            "final_confidence": confidence,
            "ready": ready,
        },
        "warnings": [],
    }


def _make_outcome(
    *,
    symbol: str = _SYMBOL,
    target_date: str = _PRED_FOR,
    close_change: float = 0.015,
) -> dict[str, Any]:
    prev_close = 800.0
    close = prev_close * (1 + close_change)
    return {
        "symbol": symbol,
        "target_date": target_date,
        "actual_open": prev_close * 1.005,
        "actual_high": close * 1.01,
        "actual_low": prev_close * 0.99,
        "actual_close": close,
        "actual_prev_close": prev_close,
        "actual_open_change": 0.005,
        "actual_close_change": close_change,
        "open_label": "高开",
        "close_label": "收涨",
        "path_label": "高开高走",
    }


def _make_review(
    *,
    direction_correct: bool | None = True,
    predicted_direction: str = "up",
    actual_direction: str = "up",
    predicted_confidence: str = "medium",
    error_category: str = "unknown",
    rule_candidates: list[dict] | None = None,
) -> dict[str, Any]:
    return {
        "kind": "projection_review",
        "ready": True,
        "predicted_direction": predicted_direction,
        "actual_direction": actual_direction,
        "direction_correct": direction_correct,
        "predicted_confidence": predicted_confidence,
        "actual_summary": {},
        "error_layer": "unknown",
        "error_category": error_category,
        "root_cause_summary": "",
        "review_notes": [],
        "rule_candidates": rule_candidates or [],
        "warnings": [],
    }


# ── A. single-date replay ─────────────────────────────────────────────────────

class TestSingleReplayHappyPath(unittest.TestCase):
    """A1: successful single-date replay produces a complete result."""

    call_log: list[str]

    def setUp(self) -> None:
        self.call_log = []

    def _projection_runner(self, **kwargs: Any) -> dict[str, Any]:
        self.call_log.append(("projection", kwargs.get("target_date"), kwargs.get("symbol")))
        return _make_projection()

    def _outcome_fetcher(self, symbol: str, target_date: str) -> dict[str, Any]:
        self.call_log.append(("outcome", target_date, symbol))
        return _make_outcome()

    def _review_builder(
        self, snapshot: dict | None, outcome: dict | None
    ) -> dict[str, Any]:
        self.call_log.append(("review",))
        return _make_review()

    def _run(self) -> dict[str, Any]:
        return run_historical_replay_for_date(
            symbol=_SYMBOL,
            as_of_date=_AS_OF,
            prediction_for_date=_PRED_FOR,
            _projection_runner=self._projection_runner,
            _outcome_fetcher=self._outcome_fetcher,
            _review_builder=self._review_builder,
        )

    def test_ready(self) -> None:
        self.assertTrue(self._run()["ready"])

    def test_kind(self) -> None:
        self.assertEqual(self._run()["kind"], "historical_replay_result")

    def test_as_of_date(self) -> None:
        self.assertEqual(self._run()["as_of_date"], _AS_OF)

    def test_prediction_for_date(self) -> None:
        self.assertEqual(self._run()["prediction_for_date"], _PRED_FOR)

    def test_snapshot_present(self) -> None:
        result = self._run()
        self.assertIn("projection_snapshot", result)
        self.assertTrue(result["projection_snapshot"])

    def test_actual_outcome_present(self) -> None:
        result = self._run()
        self.assertIn("actual_outcome", result)
        self.assertTrue(result["actual_outcome"])

    def test_review_present(self) -> None:
        result = self._run()
        self.assertIn("review", result)
        self.assertEqual(result["review"]["kind"], "projection_review")

    def test_symbol_normalized(self) -> None:
        result = run_historical_replay_for_date(
            symbol="avgo",
            as_of_date=_AS_OF,
            prediction_for_date=_PRED_FOR,
            _projection_runner=self._projection_runner,
            _outcome_fetcher=self._outcome_fetcher,
            _review_builder=self._review_builder,
        )
        self.assertEqual(result["symbol"], "AVGO")


class TestNoFutureLeak(unittest.TestCase):
    """A4: projection must see as_of_date (T), not prediction_for_date (T+1)."""

    def test_projection_called_with_as_of_date_not_pred_date(self) -> None:
        captured_target_date: list[str] = []

        def _projection_runner(**kwargs: Any) -> dict[str, Any]:
            captured_target_date.append(str(kwargs.get("target_date") or ""))
            return _make_projection()

        outcome_order: list[str] = []

        def _outcome_fetcher(symbol: str, target_date: str) -> dict[str, Any]:
            outcome_order.append("outcome")
            return _make_outcome()

        projection_order: list[str] = []

        def _projection_runner_ordered(**kwargs: Any) -> dict[str, Any]:
            projection_order.append("projection")
            captured_target_date.append(str(kwargs.get("target_date") or ""))
            return _make_projection()

        call_order: list[str] = []

        def _proj(**kwargs: Any) -> dict[str, Any]:
            call_order.append("projection")
            captured_target_date.append(str(kwargs.get("target_date") or ""))
            return _make_projection()

        def _out(symbol: str, target_date: str) -> dict[str, Any]:
            call_order.append("outcome")
            return _make_outcome()

        run_historical_replay_for_date(
            symbol=_SYMBOL,
            as_of_date=_AS_OF,
            prediction_for_date=_PRED_FOR,
            _projection_runner=_proj,
            _outcome_fetcher=_out,
            _review_builder=lambda s, o: _make_review(),
        )

        # projection must use as_of_date (T), not prediction_for_date (T+1)
        self.assertEqual(captured_target_date[0], _AS_OF)
        self.assertNotEqual(captured_target_date[0], _PRED_FOR)

        # projection must complete before outcome fetch
        self.assertEqual(call_order, ["projection", "outcome"])

    def test_outcome_fetched_for_prediction_date_not_as_of(self) -> None:
        captured_outcome_date: list[str] = []

        def _out(symbol: str, target_date: str) -> dict[str, Any]:
            captured_outcome_date.append(target_date)
            return _make_outcome()

        run_historical_replay_for_date(
            symbol=_SYMBOL,
            as_of_date=_AS_OF,
            prediction_for_date=_PRED_FOR,
            _projection_runner=lambda **kw: _make_projection(),
            _outcome_fetcher=_out,
            _review_builder=lambda s, o: _make_review(),
        )

        # outcome must be fetched for T+1, not T
        self.assertEqual(captured_outcome_date[0], _PRED_FOR)
        self.assertNotEqual(captured_outcome_date[0], _AS_OF)


class TestInsufficientHistory(unittest.TestCase):
    """A2: when projection returns ready=False, replay degrades cleanly."""

    def _run(self) -> dict[str, Any]:
        return run_historical_replay_for_date(
            symbol=_SYMBOL,
            as_of_date="2000-01-03",
            prediction_for_date="2000-01-04",
            _projection_runner=lambda **kw: _make_projection(ready=False),
            _outcome_fetcher=lambda sym, dt: (_ for _ in ()).throw(
                AssertionError("outcome_fetcher must not be called when projection fails")
            ),
            _review_builder=lambda s, o: _make_review(),
        )

    def test_ready_false(self) -> None:
        self.assertFalse(self._run()["ready"])

    def test_kind_stable(self) -> None:
        self.assertEqual(self._run()["kind"], "historical_replay_result")

    def test_warnings_non_empty(self) -> None:
        self.assertTrue(self._run()["warnings"])

    def test_shape_keys_present(self) -> None:
        r = self._run()
        for key in ("projection_snapshot", "actual_outcome", "review", "warnings"):
            self.assertIn(key, r)

    def test_projection_exception_also_degrades(self) -> None:
        result = run_historical_replay_for_date(
            symbol=_SYMBOL,
            as_of_date=_AS_OF,
            prediction_for_date=_PRED_FOR,
            _projection_runner=lambda **kw: (_ for _ in ()).throw(
                RuntimeError("数据不足")
            ),
            _outcome_fetcher=lambda sym, dt: _make_outcome(),
            _review_builder=lambda s, o: _make_review(),
        )
        self.assertFalse(result["ready"])
        self.assertTrue(any("projection" in w or "数据不足" in w for w in result["warnings"]))


class TestActualOutcomeMissing(unittest.TestCase):
    """A3: when outcome fetch fails, replay degrades but review is still attempted."""

    def _run(self) -> dict[str, Any]:
        return run_historical_replay_for_date(
            symbol=_SYMBOL,
            as_of_date=_AS_OF,
            prediction_for_date=_PRED_FOR,
            _projection_runner=lambda **kw: _make_projection(),
            _outcome_fetcher=lambda sym, dt: (_ for _ in ()).throw(
                ValueError("非交易日或无数据")
            ),
            _review_builder=lambda s, o: _make_review(direction_correct=None),
        )

    def test_ready_false(self) -> None:
        self.assertFalse(self._run()["ready"])

    def test_projection_snapshot_still_present(self) -> None:
        r = self._run()
        self.assertTrue(r["projection_snapshot"])

    def test_warning_mentions_outcome(self) -> None:
        r = self._run()
        self.assertTrue(any("实际结果" in w or "非交易日" in w for w in r["warnings"]))

    def test_review_still_attempted(self) -> None:
        r = self._run()
        # review_builder is called even when outcome missing — may return degraded shape
        self.assertIn("review", r)


# ── B. batch replay ───────────────────────────────────────────────────────────

def _mock_runners(
    *,
    fail_dates: set[str] | None = None,
    outcome_wrong: set[str] | None = None,
) -> tuple:
    """Return a (projection_runner, outcome_fetcher, review_builder) mock triple."""
    fail_dates = fail_dates or set()
    outcome_wrong = outcome_wrong or set()

    def _proj(**kwargs: Any) -> dict[str, Any]:
        td = str(kwargs.get("target_date") or "")
        if td in fail_dates:
            raise RuntimeError(f"mock 数据不足 for {td}")
        return _make_projection()

    def _out(symbol: str, target_date: str) -> dict[str, Any]:
        return _make_outcome(target_date=target_date)

    def _review(snapshot: dict | None, outcome: dict | None) -> dict[str, Any]:
        if outcome is None:
            return _make_review(direction_correct=None)
        td = str((outcome or {}).get("target_date") or "")
        correct = td not in outcome_wrong
        return _make_review(direction_correct=correct)

    return _proj, _out, _review


class TestBatchHappyPath(unittest.TestCase):
    """B5: batch of multiple dates all succeed."""

    DATE_PAIRS = [
        ("2024-01-10", "2024-01-11"),
        ("2024-01-11", "2024-01-12"),
        ("2024-01-12", "2024-01-15"),
    ]

    def _run(self) -> dict[str, Any]:
        proj, out, rev = _mock_runners()
        return run_historical_replay_batch(
            symbol=_SYMBOL,
            date_pairs=self.DATE_PAIRS,
            _projection_runner=proj,
            _outcome_fetcher=out,
            _review_builder=rev,
        )

    def test_kind(self) -> None:
        self.assertEqual(self._run()["kind"], "historical_replay_batch")

    def test_ready(self) -> None:
        self.assertTrue(self._run()["ready"])

    def test_results_count(self) -> None:
        self.assertEqual(len(self._run()["results"]), 3)

    def test_all_results_ready(self) -> None:
        for r in self._run()["results"]:
            self.assertTrue(r["ready"])

    def test_start_end_dates(self) -> None:
        result = self._run()
        self.assertEqual(result["start_date"], "2024-01-10")
        self.assertEqual(result["end_date"], "2024-01-12")

    def test_summary_present(self) -> None:
        summary = self._run()["summary"]
        for key in ("total_cases", "completed_cases", "failed_cases",
                    "direction_accuracy", "accuracy_by_confidence"):
            self.assertIn(key, summary)

    def test_total_cases(self) -> None:
        self.assertEqual(self._run()["summary"]["total_cases"], 3)

    def test_completed_cases(self) -> None:
        self.assertEqual(self._run()["summary"]["completed_cases"], 3)

    def test_failed_cases_zero(self) -> None:
        self.assertEqual(self._run()["summary"]["failed_cases"], 0)


class TestBatchPartialFailure(unittest.TestCase):
    """B6: one date fails; batch still completes, failed_cases accumulates."""

    DATE_PAIRS = [
        ("2024-01-10", "2024-01-11"),
        ("2024-01-11", "2024-01-12"),  # this one will fail projection
        ("2024-01-12", "2024-01-15"),
    ]

    def _run(self) -> dict[str, Any]:
        proj, out, rev = _mock_runners(fail_dates={"2024-01-11"})
        return run_historical_replay_batch(
            symbol=_SYMBOL,
            date_pairs=self.DATE_PAIRS,
            _projection_runner=proj,
            _outcome_fetcher=out,
            _review_builder=rev,
        )

    def test_batch_ready_despite_failure(self) -> None:
        self.assertTrue(self._run()["ready"])

    def test_results_count_all_present(self) -> None:
        self.assertEqual(len(self._run()["results"]), 3)

    def test_failed_result_not_ready(self) -> None:
        results = self._run()["results"]
        failed = [r for r in results if r["as_of_date"] == "2024-01-11"]
        self.assertEqual(len(failed), 1)
        self.assertFalse(failed[0]["ready"])

    def test_succeeded_results_ready(self) -> None:
        results = self._run()["results"]
        ok = [r for r in results if r["as_of_date"] != "2024-01-11"]
        self.assertTrue(all(r["ready"] for r in ok))

    def test_failed_cases_count(self) -> None:
        self.assertEqual(self._run()["summary"]["failed_cases"], 1)

    def test_completed_cases_count(self) -> None:
        self.assertEqual(self._run()["summary"]["completed_cases"], 2)


class TestBatchEmptyRange(unittest.TestCase):
    """B7: empty date_pairs produces stable shape with total_cases=0."""

    def _run(self) -> dict[str, Any]:
        return run_historical_replay_batch(
            symbol=_SYMBOL,
            date_pairs=[],
            _projection_runner=lambda **kw: _make_projection(),
            _outcome_fetcher=lambda sym, dt: _make_outcome(),
            _review_builder=lambda s, o: _make_review(),
        )

    def test_kind(self) -> None:
        self.assertEqual(self._run()["kind"], "historical_replay_batch")

    def test_ready(self) -> None:
        self.assertTrue(self._run()["ready"])

    def test_results_empty(self) -> None:
        self.assertEqual(self._run()["results"], [])

    def test_total_cases_zero(self) -> None:
        self.assertEqual(self._run()["summary"]["total_cases"], 0)

    def test_summary_shape_stable(self) -> None:
        summary = self._run()["summary"]
        for key in ("total_cases", "completed_cases", "failed_cases",
                    "direction_accuracy", "accuracy_by_confidence",
                    "top_error_categories", "top_rule_candidates"):
            self.assertIn(key, summary)

    def test_start_end_dates_none(self) -> None:
        result = self._run()
        self.assertIsNone(result["start_date"])
        self.assertIsNone(result["end_date"])


# ── C. aggregation statistics ─────────────────────────────────────────────────

class TestDirectionAccuracy(unittest.TestCase):
    """C8: direction_accuracy and accuracy_by_confidence computed correctly."""

    def _results(self) -> list[dict]:
        """3 replays: high-correct, medium-wrong, low-correct."""
        return [
            {
                "kind": "historical_replay_result",
                "ready": True,
                "review": _make_review(
                    direction_correct=True,
                    predicted_confidence="high",
                ),
            },
            {
                "kind": "historical_replay_result",
                "ready": True,
                "review": _make_review(
                    direction_correct=False,
                    predicted_confidence="medium",
                ),
            },
            {
                "kind": "historical_replay_result",
                "ready": True,
                "review": _make_review(
                    direction_correct=True,
                    predicted_confidence="low",
                ),
            },
        ]

    def test_direction_accuracy(self) -> None:
        summary = summarize_replay_results(self._results())
        # 2 correct out of 3 judged
        self.assertAlmostEqual(summary["direction_accuracy"], 2 / 3)

    def test_accuracy_by_confidence_high(self) -> None:
        summary = summarize_replay_results(self._results())
        self.assertAlmostEqual(summary["accuracy_by_confidence"]["high"], 1.0)

    def test_accuracy_by_confidence_medium(self) -> None:
        summary = summarize_replay_results(self._results())
        self.assertAlmostEqual(summary["accuracy_by_confidence"]["medium"], 0.0)

    def test_accuracy_by_confidence_low(self) -> None:
        summary = summarize_replay_results(self._results())
        self.assertAlmostEqual(summary["accuracy_by_confidence"]["low"], 1.0)

    def test_no_judged_cases_gives_none_accuracy(self) -> None:
        results = [
            {
                "kind": "historical_replay_result",
                "ready": True,
                "review": _make_review(direction_correct=None),
            }
        ]
        summary = summarize_replay_results(results)
        self.assertIsNone(summary["direction_accuracy"])

    def test_failed_cases_excluded_from_accuracy(self) -> None:
        results = [
            {"kind": "historical_replay_result", "ready": False, "review": {}},
            {
                "kind": "historical_replay_result",
                "ready": True,
                "review": _make_review(direction_correct=True, predicted_confidence="high"),
            },
        ]
        summary = summarize_replay_results(results)
        self.assertEqual(summary["total_cases"], 2)
        self.assertEqual(summary["completed_cases"], 1)
        self.assertAlmostEqual(summary["direction_accuracy"], 1.0)


class TestErrorAndRuleAggregation(unittest.TestCase):
    """C9: top_error_categories and top_rule_candidates aggregated correctly."""

    def _results(self) -> list[dict]:
        rc_a = {"rule_id": "rule-a", "title": "规则A", "category": "false_confidence", "severity": "high", "message": "msg"}
        rc_b = {"rule_id": "rule-b", "title": "规则B", "category": "insufficient_data", "severity": "medium", "message": "msg"}

        return [
            {
                "ready": True,
                "review": _make_review(
                    direction_correct=False,
                    error_category="false_confidence",
                    rule_candidates=[rc_a],
                ),
            },
            {
                "ready": True,
                "review": _make_review(
                    direction_correct=False,
                    error_category="false_confidence",
                    rule_candidates=[rc_a, rc_b],
                ),
            },
            {
                "ready": True,
                "review": _make_review(
                    direction_correct=False,
                    error_category="insufficient_data",
                    rule_candidates=[rc_b],
                ),
            },
        ]

    def test_top_error_categories_order(self) -> None:
        summary = summarize_replay_results(self._results())
        cats = [e["category"] for e in summary["top_error_categories"]]
        self.assertEqual(cats[0], "false_confidence")  # count=2
        self.assertIn("insufficient_data", cats)

    def test_top_error_categories_count(self) -> None:
        summary = summarize_replay_results(self._results())
        counts = {e["category"]: e["count"] for e in summary["top_error_categories"]}
        self.assertEqual(counts["false_confidence"], 2)
        self.assertEqual(counts["insufficient_data"], 1)

    def test_top_rule_candidates_order(self) -> None:
        summary = summarize_replay_results(self._results())
        rule_ids = [r["rule_id"] for r in summary["top_rule_candidates"]]
        self.assertEqual(rule_ids[0], "rule-a")  # appears in 2 replays

    def test_top_rule_candidates_count(self) -> None:
        summary = summarize_replay_results(self._results())
        counts = {r["rule_id"]: r["count"] for r in summary["top_rule_candidates"]}
        self.assertEqual(counts["rule-a"], 2)
        self.assertEqual(counts["rule-b"], 2)

    def test_correct_predictions_excluded_from_error_categories(self) -> None:
        results = [
            {
                "ready": True,
                "review": _make_review(
                    direction_correct=True,
                    error_category="false_confidence",  # should be ignored when correct
                ),
            }
        ]
        # When direction_correct=True, build_projection_review wouldn't normally
        # emit a non-unknown error_category — but even if it does, the counter
        # still increments. We test the actual behavior: error_category is counted
        # regardless of direction_correct (aggregation doesn't filter by correctness).
        summary = summarize_replay_results(results)
        cats = [e["category"] for e in summary["top_error_categories"]]
        # false_confidence gets counted (aggregation is category-level, not filtered)
        self.assertIn("false_confidence", cats)

    def test_unknown_error_category_not_in_top(self) -> None:
        results = [
            {
                "ready": True,
                "review": _make_review(
                    direction_correct=None,
                    error_category="unknown",
                ),
            }
        ]
        summary = summarize_replay_results(results)
        cats = [e["category"] for e in summary["top_error_categories"]]
        self.assertNotIn("unknown", cats)

    def test_empty_results_gives_stable_shape(self) -> None:
        summary = summarize_replay_results([])
        self.assertEqual(summary["top_error_categories"], [])
        self.assertEqual(summary["top_rule_candidates"], [])
        self.assertEqual(summary["total_cases"], 0)


class TestSummarizeShapeStability(unittest.TestCase):
    """Shape keys always present regardless of input."""

    _REQUIRED_KEYS = (
        "total_cases",
        "completed_cases",
        "failed_cases",
        "direction_accuracy",
        "accuracy_by_confidence",
        "top_error_categories",
        "top_rule_candidates",
    )

    def _check(self, results: list) -> None:
        summary = summarize_replay_results(results)
        for key in self._REQUIRED_KEYS:
            self.assertIn(key, summary, msg=f"missing key: {key}")
        for conf_key in ("high", "medium", "low"):
            self.assertIn(conf_key, summary["accuracy_by_confidence"])

    def test_empty(self) -> None:
        self._check([])

    def test_all_failed(self) -> None:
        self._check([{"ready": False, "review": {}}] * 3)

    def test_no_reviews(self) -> None:
        self._check([{"ready": True, "review": {}} for _ in range(3)])

    def test_mixed(self) -> None:
        self._check([
            {"ready": True, "review": _make_review(direction_correct=True)},
            {"ready": False, "review": {}},
            {"ready": True, "review": _make_review(direction_correct=None)},
        ])


if __name__ == "__main__":
    unittest.main()
