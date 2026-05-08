"""Contract enforcement tests for Step 12C-A (RISK-3 stage A).

These tests pin the standalone confidence evaluator boundary:

1. ``build_confidence_result`` returns the full ``confidence_system_result.v1``
   schema (07C §9 / 11C §6) including projection_confidence /
   exclusion_confidence / agreement_status / conflict_level /
   combined_confidence / reliability_warnings / sample_size_notes /
   calibration_notes / raw_evidence_refs / non_mutation_confirmations.
2. The evaluator does NOT mutate ``projection_result`` /
   ``exclusion_result`` / any context inputs.
3. agreement detection: strong_conflict / partial_conflict / aligned /
   unknown follow 07C §10.
4. Missing calibration_context → all confidence levels degrade to
   ``unknown`` (11C §9.3); the evaluator never fabricates a heuristic.
5. Output level / score is monotonic per 11C §6.1 thresholds.
6. Output contains no forbidden fields (most_likely_state /
   most_unlikely_state / trading / hard / forced / required / promotion /
   modified_*).
7. The module imports no LLM / DB-write / future-outcome surfaces.
8. The evaluator is deterministic for the same input.

Design contracts: 06 / 07C / 11C / 11H.
"""

from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


_FORBIDDEN_FIELDS = (
    "most_likely_state",
    "most_unlikely_state",
    "modified_projection",
    "modified_exclusion",
    "projection_correction",
    "exclusion_correction",
    "hard_exclusion",
    "forced_exclusion",
    "required_decision",
    "trading_action",
    "buy",
    "sell",
    "hold",
    "simulated_trade",
    "no_trade",
    "final_report_mutation",
    "production_promotion",
    "_PROTECTION_LAYER_CONNECTED",
)

_VALID_LEVELS = {"low", "medium", "high", "unknown"}
_VALID_AGREEMENT = {"aligned", "partial_conflict", "strong_conflict", "unknown"}
_VALID_CONFLICT = {"none", "low", "medium", "high", "unknown"}


def _projection(
    most_likely: str = "小涨",
    *,
    ranked: list[str] | None = None,
) -> dict:
    return {
        "schema_version": "projection_system_result.v1",
        "system_name": "projection_system",
        "most_likely_state": most_likely,
        "ranked_states": ranked or [most_likely, "震荡", "大涨", "小跌", "大跌"],
        "state_scores": {
            "大涨": 0.10,
            "小涨": 0.40,
            "震荡": 0.30,
            "小跌": 0.15,
            "大跌": 0.05,
        },
        "primary_reasoning": ["test"],
    }


def _exclusion(
    most_unlikely: str = "大跌",
    *,
    ranked_unlikely: list[str] | None = None,
) -> dict:
    return {
        "schema_version": "exclusion_system_result.v1",
        "system_name": "exclusion_system",
        "most_unlikely_state": most_unlikely,
        "ranked_unlikely_states": ranked_unlikely or [most_unlikely, "小跌", "震荡", "大涨", "小涨"],
        "state_impossibility_scores": {
            "大涨": 0.10,
            "小涨": 0.05,
            "震荡": 0.20,
            "小跌": 0.30,
            "大跌": 0.50,
        },
        "primary_exclusion_reasoning": ["test"],
    }


def _calibration(*, ready: bool = True, projection_score: float = 0.6, exclusion_score: float = 0.7, notes: list[str] | None = None) -> dict:
    return {
        "ready": ready,
        "projection_score": projection_score,
        "exclusion_score": exclusion_score,
        "notes": notes or [],
    }


class SchemaTests(unittest.TestCase):
    def test_confidence_result_schema(self) -> None:
        from services.confidence_evaluator import build_confidence_result

        result = build_confidence_result(
            projection_result=_projection(),
            exclusion_result=_exclusion(),
            calibration_context=_calibration(),
            target_date="2026-04-21",
        )
        for key in (
            "schema_version",
            "confidence_date",
            "target_date",
            "system_name",
            "question_answered",
            "projection_confidence",
            "exclusion_confidence",
            "agreement_status",
            "conflict_level",
            "combined_confidence",
            "reliability_warnings",
            "sample_size_notes",
            "calibration_notes",
            "raw_evidence_refs",
            "non_mutation_confirmations",
        ):
            self.assertIn(key, result, msg=f"missing schema key: {key}")
        self.assertEqual(result["schema_version"], "confidence_system_result.v1")
        self.assertEqual(result["system_name"], "confidence_system")
        self.assertEqual(result["question_answered"], "system_reliability_evaluation")
        self.assertEqual(result["target_date"], "2026-04-21")
        for section_key in ("projection_confidence", "exclusion_confidence", "combined_confidence"):
            section = result[section_key]
            self.assertIsInstance(section, dict)
            self.assertIn("level", section)
            self.assertIn("score", section)
            self.assertIn("reasoning", section)
            self.assertIn(section["level"], _VALID_LEVELS)
            self.assertTrue(section["score"] is None or isinstance(section["score"], (int, float)))
            self.assertIsInstance(section["reasoning"], list)
        self.assertIn(result["agreement_status"], _VALID_AGREEMENT)
        self.assertIn(result["conflict_level"], _VALID_CONFLICT)


class NonMutationTests(unittest.TestCase):
    def test_confidence_evaluator_does_not_mutate_projection_or_exclusion(self) -> None:
        from services.confidence_evaluator import build_confidence_result

        projection = _projection(most_likely="小涨")
        exclusion = _exclusion(most_unlikely="大跌")
        market_context = {"date": "2026-04-21", "regime": "trend_up"}
        historical_context = {"hit_rate": 0.55, "samples": 100}
        calibration_context = _calibration()

        projection_snap = copy.deepcopy(projection)
        exclusion_snap = copy.deepcopy(exclusion)
        market_snap = copy.deepcopy(market_context)
        historical_snap = copy.deepcopy(historical_context)
        calibration_snap = copy.deepcopy(calibration_context)

        build_confidence_result(
            projection_result=projection,
            exclusion_result=exclusion,
            market_context=market_context,
            historical_context=historical_context,
            calibration_context=calibration_context,
            target_date="2026-04-21",
        )

        self.assertEqual(projection, projection_snap)
        self.assertEqual(exclusion, exclusion_snap)
        self.assertEqual(market_context, market_snap)
        self.assertEqual(historical_context, historical_snap)
        self.assertEqual(calibration_context, calibration_snap)

    def test_confidence_evaluator_non_mutation_confirmations(self) -> None:
        from services.confidence_evaluator import build_confidence_result

        result = build_confidence_result(
            projection_result=_projection(),
            exclusion_result=_exclusion(),
            calibration_context=_calibration(),
            target_date="2026-04-21",
        )
        confirmations = result["non_mutation_confirmations"]
        self.assertIs(confirmations["projection_result_mutated"], False)
        self.assertIs(confirmations["exclusion_result_mutated"], False)


class AgreementTests(unittest.TestCase):
    def test_confidence_evaluator_detects_strong_conflict(self) -> None:
        from services.confidence_evaluator import build_confidence_result

        result = build_confidence_result(
            projection_result=_projection(most_likely="大涨"),
            exclusion_result=_exclusion(most_unlikely="大涨"),
            calibration_context=_calibration(),
            target_date="2026-04-21",
        )
        self.assertEqual(result["agreement_status"], "strong_conflict")
        self.assertIn(result["conflict_level"], {"medium", "high"})

    def test_confidence_evaluator_detects_aligned(self) -> None:
        from services.confidence_evaluator import build_confidence_result

        # most_likely=小涨, most_unlikely=大跌; ranked_states top2={小涨, 震荡};
        # ranked_unlikely top2={大跌, 小跌}; no overlap → aligned
        result = build_confidence_result(
            projection_result=_projection(
                most_likely="小涨",
                ranked=["小涨", "震荡", "大涨", "小跌", "大跌"],
            ),
            exclusion_result=_exclusion(
                most_unlikely="大跌",
                ranked_unlikely=["大跌", "小跌", "震荡", "大涨", "小涨"],
            ),
            calibration_context=_calibration(),
            target_date="2026-04-21",
        )
        self.assertEqual(result["agreement_status"], "aligned")
        self.assertIn(result["conflict_level"], {"none", "low"})

    def test_confidence_evaluator_detects_partial_conflict(self) -> None:
        from services.confidence_evaluator import build_confidence_result

        # most_likely=小涨, most_unlikely=大跌 (not equal);
        # ranked_states top2 = {小涨, 大跌}; ranked_unlikely top2 = {大跌, 震荡};
        # overlap on "大跌" but most_likely != most_unlikely → partial_conflict
        result = build_confidence_result(
            projection_result=_projection(
                most_likely="小涨",
                ranked=["小涨", "大跌", "震荡", "小跌", "大涨"],
            ),
            exclusion_result=_exclusion(
                most_unlikely="大跌",
                ranked_unlikely=["大跌", "震荡", "小跌", "大涨", "小涨"],
            ),
            calibration_context=_calibration(),
            target_date="2026-04-21",
        )
        self.assertEqual(result["agreement_status"], "partial_conflict")
        self.assertIn(result["conflict_level"], {"low", "medium"})

    def test_confidence_evaluator_unknown_when_projection_missing(self) -> None:
        from services.confidence_evaluator import build_confidence_result

        result = build_confidence_result(
            projection_result={},
            exclusion_result=_exclusion(),
            calibration_context=_calibration(),
            target_date="2026-04-21",
        )
        self.assertEqual(result["agreement_status"], "unknown")
        self.assertEqual(result["conflict_level"], "unknown")

    def test_confidence_evaluator_unknown_when_exclusion_missing(self) -> None:
        from services.confidence_evaluator import build_confidence_result

        result = build_confidence_result(
            projection_result=_projection(),
            exclusion_result={},
            calibration_context=_calibration(),
            target_date="2026-04-21",
        )
        self.assertEqual(result["agreement_status"], "unknown")
        self.assertEqual(result["conflict_level"], "unknown")


class CalibrationDegradationTests(unittest.TestCase):
    def test_confidence_evaluator_missing_calibration_returns_unknown(self) -> None:
        from services.confidence_evaluator import build_confidence_result

        result = build_confidence_result(
            projection_result=_projection(),
            exclusion_result=_exclusion(),
            calibration_context=None,
            target_date="2026-04-21",
        )
        self.assertEqual(result["projection_confidence"]["level"], "unknown")
        self.assertEqual(result["exclusion_confidence"]["level"], "unknown")
        self.assertEqual(result["combined_confidence"]["level"], "unknown")
        self.assertIsNone(result["projection_confidence"]["score"])
        self.assertIsNone(result["exclusion_confidence"]["score"])
        self.assertIsNone(result["combined_confidence"]["score"])
        joined = " ".join(result["reliability_warnings"]) + " ".join(result["calibration_notes"])
        self.assertIn("calibration", joined.lower())

    def test_confidence_evaluator_calibration_not_ready_returns_unknown(self) -> None:
        from services.confidence_evaluator import build_confidence_result

        result = build_confidence_result(
            projection_result=_projection(),
            exclusion_result=_exclusion(),
            calibration_context=_calibration(ready=False),
            target_date="2026-04-21",
        )
        self.assertEqual(result["projection_confidence"]["level"], "unknown")
        self.assertEqual(result["exclusion_confidence"]["level"], "unknown")
        self.assertEqual(result["combined_confidence"]["level"], "unknown")

    def test_confidence_evaluator_missing_projection_or_exclusion_unknown_confidence(self) -> None:
        from services.confidence_evaluator import build_confidence_result

        result = build_confidence_result(
            projection_result={},
            exclusion_result=_exclusion(),
            calibration_context=_calibration(),
            target_date="2026-04-21",
        )
        self.assertEqual(result["projection_confidence"]["level"], "unknown")
        # When inputs are missing the combined_confidence falls back to unknown
        # too (cannot meaningfully combine).
        self.assertEqual(result["combined_confidence"]["level"], "unknown")


class LevelScoreMonotonicTests(unittest.TestCase):
    def test_confidence_evaluator_score_level_monotonic(self) -> None:
        from services.confidence_evaluator import build_confidence_result

        # Sweep projection_score from low to high; exclusion_score fixed at high
        # so we can read the projection_confidence.level.
        scores_levels = []
        for projection_score in (0.05, 0.30, 0.50, 0.85):
            result = build_confidence_result(
                projection_result=_projection(),
                exclusion_result=_exclusion(),
                calibration_context=_calibration(
                    projection_score=projection_score,
                    exclusion_score=0.8,
                ),
                target_date="2026-04-21",
            )
            level = result["projection_confidence"]["level"]
            score = result["projection_confidence"]["score"]
            scores_levels.append((projection_score, level, score))

        levels_in_order = [entry[1] for entry in scores_levels]
        order_rank = {"unknown": -1, "low": 0, "medium": 1, "high": 2}
        ranks = [order_rank[lvl] for lvl in levels_in_order]
        # monotonic non-decreasing
        for i in range(1, len(ranks)):
            self.assertLessEqual(
                ranks[i - 1],
                ranks[i],
                msg=f"projection level not monotonic: {levels_in_order}",
            )
        # The lowest score must be 'low' or 'unknown', the highest must be 'high'.
        self.assertIn(levels_in_order[0], {"low", "unknown"})
        self.assertEqual(levels_in_order[-1], "high")

    def test_confidence_evaluator_score_within_level_band(self) -> None:
        from services.confidence_evaluator import build_confidence_result

        # Each level must have score in its declared band.
        cases = [
            (0.10, "low", (0.0, 0.4)),
            (0.50, "medium", (0.4, 0.7)),
            (0.85, "high", (0.7, 1.0)),
        ]
        for score_in, expected_level, (lo, hi) in cases:
            result = build_confidence_result(
                projection_result=_projection(),
                exclusion_result=_exclusion(),
                calibration_context=_calibration(
                    projection_score=score_in,
                    exclusion_score=score_in,
                ),
                target_date="2026-04-21",
            )
            level = result["projection_confidence"]["level"]
            score = result["projection_confidence"]["score"]
            self.assertEqual(level, expected_level)
            self.assertIsNotNone(score)
            self.assertGreaterEqual(score, lo - 1e-9)
            self.assertLessEqual(score, hi + 1e-9)


class ForbiddenFieldsTests(unittest.TestCase):
    def test_confidence_evaluator_no_forbidden_fields(self) -> None:
        from services.confidence_evaluator import build_confidence_result

        result = build_confidence_result(
            projection_result=_projection(most_likely="大涨"),
            exclusion_result=_exclusion(most_unlikely="大涨"),
            calibration_context=_calibration(),
            target_date="2026-04-21",
        )
        for forbidden in _FORBIDDEN_FIELDS:
            self.assertNotIn(
                forbidden,
                result,
                msg=f"confidence_result must not contain {forbidden!r}",
            )

    def test_confidence_evaluator_unknown_path_no_forbidden_fields(self) -> None:
        from services.confidence_evaluator import build_confidence_result

        result = build_confidence_result(
            projection_result={},
            exclusion_result={},
            calibration_context=None,
            target_date=None,
        )
        for forbidden in _FORBIDDEN_FIELDS:
            self.assertNotIn(forbidden, result)


class StaticImportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module_path = ROOT / "services" / "confidence_evaluator.py"
        self.source = self.module_path.read_text(encoding="utf-8")
        self.tree = ast.parse(self.source)

    def test_confidence_evaluator_no_llm_import(self) -> None:
        for forbidden in (
            "from services.openai_client",
            "import openai",
            "openai_client",
        ):
            self.assertNotIn(
                forbidden,
                self.source,
                msg=f"confidence_evaluator must not import LLM surface: {forbidden}",
            )

    def test_confidence_evaluator_no_db_import(self) -> None:
        for forbidden in (
            "import sqlite3",
            "from sqlite3",
            "from services.log_store",
            "from services.prediction_store",
            "from services.db",
        ):
            self.assertNotIn(
                forbidden,
                self.source,
                msg=f"confidence_evaluator must not import DB surface: {forbidden}",
            )

    def test_confidence_evaluator_no_db_writes(self) -> None:
        upper = self.source.upper()
        # Crude SQL write detection. Allow SELECT-only; flag write keywords.
        for keyword in (" INSERT ", " UPDATE ", " DELETE ", " DROP ", " ALTER "):
            self.assertNotIn(keyword, upper, msg=f"confidence_evaluator must not contain SQL write: {keyword}")

    def test_confidence_evaluator_does_not_import_active_path_modules(self) -> None:
        # Stage A must not couple to the active orchestrator / final_decision /
        # main projection / exclusion engine / predict.py.
        for forbidden in (
            "from services.final_decision",
            "from services.projection_orchestrator_v2",
            "from services.projection_orchestrator",
            "from services.main_projection_layer",
            "from services.exclusion_layer",
            "from services.projection_three_systems_renderer",
            "import predict",
        ):
            self.assertNotIn(
                forbidden,
                self.source,
                msg=f"confidence_evaluator must not import active path: {forbidden}",
            )

    def test_confidence_evaluator_module_does_not_perform_io(self) -> None:
        # No file open / read / write at module-import or function-call surface.
        for forbidden in ("open(", "Path(", "requests.", "urllib", "http.client"):
            self.assertNotIn(
                forbidden,
                self.source,
                msg=f"confidence_evaluator must not perform I/O: {forbidden}",
            )


class DeterministicTests(unittest.TestCase):
    def test_confidence_evaluator_deterministic(self) -> None:
        from services.confidence_evaluator import build_confidence_result

        kwargs = dict(
            projection_result=_projection(),
            exclusion_result=_exclusion(),
            calibration_context=_calibration(),
            target_date="2026-04-21",
        )
        result_a = build_confidence_result(**kwargs)
        result_b = build_confidence_result(**copy.deepcopy(kwargs))
        self.assertEqual(result_a, result_b)


if __name__ == "__main__":
    unittest.main()
