"""Read-only boundary tests for the Review & Learning Layer briefing
modules (Step 18X / PR-REVIEW-3).

Spec source of truth:

- `tasks/record_1_0_architecture_reset_canonical_principles.md` §8 (Branch 7) /
  §13 hard rule
- `tasks/record_06_three_system_independence_principle.md` §6 / §7
- `tasks/record_17k_review_learning_layer_rebuild_plan.md` §6.1 / §6.6 /
  §6.9 / §15 PR-REVIEW-3
- `tasks/record_18s_third_layer_based_implementation_batch_selection.md`
  §4 / §6 / §10

Status (per 17K §15 PR-REVIEW-3 / 18S §6):

PR-REVIEW-3 is a **pure-tests addition** — zero changes to any
existing business code. The Review & Learning Layer must learn
**ex-post only** (1.0 §13 / 06 §6 / 07A §3.2 / 07B §3.2 / 07C §3.3 /
07D §11 / 17K §6); the *pre-prediction* briefing trio
(``pre_prediction_briefing`` / ``projection_memory_briefing`` /
``memory_feedback``) and ``predict._apply_briefing_caution`` may
**only** read prior review history and surface advisory warnings.
They must not:

- import the projection / exclusion / confidence / final_report /
  prediction modules (would let pre-prediction briefing influence
  current inference);
- mutate the current prediction's
  ``final_confidence`` / ``final_direction`` / ``final_prediction`` /
  ``final_bias`` / ``primary_*`` / ``final_projection``;
- emit ``hard`` / ``forced`` / ``required`` / ``buy`` / ``sell`` /
  ``hold`` / ``trading_action`` / ``order`` / ``execution`` /
  ``broker_order`` / ``live_trade`` keys;
- write to the database, write files, or write active rules / promote
  rules.

This suite verifies the above as **source-level** invariants (so the
tests do not require a working DB / network) plus a small functional
output-shape check that uses ``unittest.mock`` to keep the briefing
helpers DB-free.

Test classes (numbers correspond to the user spec):

1. ReviewBriefingSourceBoundaryTests — forbidden imports
2. NoCurrentPredictionMutationSourceTests — protected-field
   assignment scan
3. NoHardForcedRequiredReviewOutputSourceTests — forbidden
   trading / forcing token scan
4. ReviewMemoryNoActiveRuleWriteBoundaryTests — active rule write
   token scan
5. ApplyBriefingCautionRegressionBoundaryTests — pin 18R fix
6. BriefingOutputShapeBoundaryTests — mocked end-to-end output
   shape (no DB)
7. NoDBWriteOrFileWriteBoundaryTests — write-side syscall scan
"""

from __future__ import annotations

import ast
import re
import unittest
from copy import deepcopy
from pathlib import Path
from typing import Iterable
from unittest.mock import patch


_REPO_ROOT = Path(__file__).resolve().parent.parent


def _read(rel: str) -> str:
    return (_REPO_ROOT / rel).read_text(encoding="utf-8")


# Three "briefing trio" modules that must run *before* the current
# prediction is finalised. The constraint they all share: read-only
# advisory output; no current-prediction mutation; no DB write.
_BRIEFING_MODULES: tuple[str, ...] = (
    "services/pre_prediction_briefing.py",
    "services/projection_memory_briefing.py",
    "services/memory_feedback.py",
)


# Field names the briefing trio must never touch on the current
# prediction's result dict (1.0 §13 hard rule / 06 §6).
_PROTECTED_PREDICTION_FIELDS: tuple[str, ...] = (
    "final_confidence",
    "final_direction",
    "final_prediction",
    "prediction",
    "primary_direction",
    "primary_projection",
    "final_projection",
    "final_bias",
)


# Trading / forcing tokens forbidden in any Review-Layer briefing /
# memory output (1.0 §6 / §13 / 17K §6 / §15 / 18S).
_FORBIDDEN_REVIEW_TOKENS: tuple[str, ...] = (
    "hard",
    "forced",
    "required",
    "forced_downgrade",
    "required_downgrade",
    "hard_downgrade",
    "buy",
    "sell",
    "hold",
    "trading_action",
    "order",
    "execution",
    "broker_order",
    "live_trade",
)


# Active-rule promotion tokens forbidden in any briefing module.
_FORBIDDEN_ACTIVE_RULE_TOKENS: tuple[str, ...] = (
    "active_rule_promotion",
    "promote_rule",
    "write_active_rule",
    "save_active_rule",
    "insert_active_rule",
    "update_active_rule",
)


def _quoted_keys(field: str) -> tuple[str, ...]:
    """Quoted-key spellings used in subscript / dict-literal contexts."""
    return (f'"{field}"', f"'{field}'")


def _has_word_token(source: str, token: str) -> bool:
    """Return True when ``token`` appears in ``source`` as a whole
    word (alnum / underscore boundary)."""
    pattern = r"(?<![A-Za-z0-9_])" + re.escape(token) + r"(?![A-Za-z0-9_])"
    return re.search(pattern, source) is not None


# ---------------------------------------------------------------------------
# 1. Source-level forbidden-import boundary
# ---------------------------------------------------------------------------

class ReviewBriefingSourceBoundaryTests(unittest.TestCase):
    """The briefing trio must not import any module that would let it
    influence the current inference path."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.sources = {rel: _read(rel) for rel in _BRIEFING_MODULES}

    def test_no_predict_or_inference_module_imports(self) -> None:
        forbidden = (
            "from predict",
            "import predict",
            "from services.final_decision",
            "import services.final_decision",
            "from services.confidence_evaluator",
            "import services.confidence_evaluator",
            "from services.main_projection_layer",
            "import services.main_projection_layer",
            "from services.exclusion_layer",
            "import services.exclusion_layer",
            "from services.peer_alignment",
            "import services.peer_alignment",
            "from services.consistency_layer",
            "import services.consistency_layer",
            "from services.projection_orchestrator",
            "import services.projection_orchestrator",
            "from services.projection_orchestrator_v2",
            "import services.projection_orchestrator_v2",
            "from services.projection_entrypoint",
            "import services.projection_entrypoint",
            "from services.projection_v2_adapter",
            "import services.projection_v2_adapter",
            "from services.home_terminal_orchestrator",
            "import services.home_terminal_orchestrator",
            "from services.predict_legacy_adapter",
            "import services.predict_legacy_adapter",
            "from services.predict_legacy_v2_bridge",
            "import services.predict_legacy_v2_bridge",
            "from services.predict_summary",
            "import services.predict_summary",
            "from services.final_report_result_contract",
            "import services.final_report_result_contract",
            "from services.warning_cards",
            "import services.warning_cards",
        )
        for rel, source in self.sources.items():
            for f in forbidden:
                with self.subTest(module=rel, forbidden=f):
                    self.assertNotIn(
                        f, source,
                        msg=f"{rel} must not contain `{f}`",
                    )

    def test_no_ui_or_app_imports(self) -> None:
        forbidden = (
            "from app",
            "import app",
            "from ui",
            "import ui",
            "import streamlit",
            "from streamlit",
        )
        for rel, source in self.sources.items():
            for f in forbidden:
                with self.subTest(module=rel, forbidden=f):
                    self.assertNotIn(
                        f, source,
                        msg=f"{rel} must not contain `{f}`",
                    )

    def test_no_writer_store_imports(self) -> None:
        # ``review_store`` exposes ``save_review_record`` (writer) and
        # ``load_review_records`` (reader). Briefing modules only need
        # the reader path (which lives behind ``review_analyzer``); a
        # direct import of ``review_store`` from a briefing module
        # would expose ``save_review_record`` to the pre-prediction
        # path. ``prediction_store`` / ``review_orchestrator`` are
        # post-close writers and must not be imported by the briefing
        # trio either.
        forbidden = (
            "from services.review_store",
            "import services.review_store",
            "from services.prediction_store",
            "import services.prediction_store",
            "from services.review_orchestrator",
            "import services.review_orchestrator",
            "from services.review_agent",
            "import services.review_agent",
        )
        for rel, source in self.sources.items():
            for f in forbidden:
                with self.subTest(module=rel, forbidden=f):
                    self.assertNotIn(
                        f, source,
                        msg=f"{rel} must not contain `{f}`",
                    )


# ---------------------------------------------------------------------------
# 2. Source-level: no assignment to current-prediction protected fields
# ---------------------------------------------------------------------------

class NoCurrentPredictionMutationSourceTests(unittest.TestCase):
    """The briefing trio must not assign to ``result[<protected>] =`` /
    ``result.update({<protected>: ...})`` / ``result.setdefault(<protected>, ...)``."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.sources = {rel: _read(rel) for rel in _BRIEFING_MODULES}

    def test_no_subscript_assignment_to_protected_fields(self) -> None:
        for rel, source in self.sources.items():
            for field in _PROTECTED_PREDICTION_FIELDS:
                for quoted in _quoted_keys(field):
                    forbidden = f"result[{quoted}] = "
                    with self.subTest(module=rel, forbidden=forbidden):
                        self.assertNotIn(
                            forbidden, source,
                            msg=f"{rel} must not contain `{forbidden}`",
                        )

    def test_no_dict_update_with_protected_fields(self) -> None:
        for rel, source in self.sources.items():
            for field in _PROTECTED_PREDICTION_FIELDS:
                for quoted in _quoted_keys(field):
                    forbidden = f"result.update({{{quoted}:"
                    with self.subTest(module=rel, forbidden=forbidden):
                        self.assertNotIn(
                            forbidden, source,
                            msg=f"{rel} must not contain `{forbidden}`",
                        )

    def test_no_setdefault_with_protected_fields(self) -> None:
        for rel, source in self.sources.items():
            for field in _PROTECTED_PREDICTION_FIELDS:
                for quoted in _quoted_keys(field):
                    forbidden = f"result.setdefault({quoted}"
                    with self.subTest(module=rel, forbidden=forbidden):
                        self.assertNotIn(
                            forbidden, source,
                            msg=f"{rel} must not contain `{forbidden}`",
                        )

    def test_no_quoted_protected_field_keys_at_all(self) -> None:
        # Stronger guard: a briefing module should not even *mention*
        # the protected field names as quoted dict keys, since the
        # only way they would surface is via mutation / output of a
        # current-prediction field. (``review_orchestrator`` / other
        # post-close paths legitimately use these keys; this guard is
        # scoped to the briefing trio only.)
        for rel, source in self.sources.items():
            for field in _PROTECTED_PREDICTION_FIELDS:
                for quoted in _quoted_keys(field):
                    with self.subTest(module=rel, key=quoted):
                        self.assertNotIn(
                            quoted, source,
                            msg=f"{rel} must not contain quoted key `{quoted}`",
                        )


# ---------------------------------------------------------------------------
# 3. Source-level: no hard / forced / required / trading tokens
# ---------------------------------------------------------------------------

class NoHardForcedRequiredReviewOutputSourceTests(unittest.TestCase):
    """The briefing trio must not declare quoted output keys for
    forbidden trading / forcing semantics."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.sources = {rel: _read(rel) for rel in _BRIEFING_MODULES}

    def test_no_quoted_forbidden_output_keys(self) -> None:
        for rel, source in self.sources.items():
            for token in _FORBIDDEN_REVIEW_TOKENS:
                for quoted in _quoted_keys(token):
                    with self.subTest(module=rel, key=quoted):
                        self.assertNotIn(
                            quoted, source,
                            msg=(
                                f"{rel} must not contain forbidden quoted key "
                                f"`{quoted}`"
                            ),
                        )

    def test_no_subscript_assignment_to_forbidden_keys(self) -> None:
        for rel, source in self.sources.items():
            for token in _FORBIDDEN_REVIEW_TOKENS:
                for quoted in _quoted_keys(token):
                    forbidden = f"result[{quoted}] = "
                    with self.subTest(module=rel, forbidden=forbidden):
                        self.assertNotIn(
                            forbidden, source,
                            msg=f"{rel} must not contain `{forbidden}`",
                        )


# ---------------------------------------------------------------------------
# 4. Source-level: no active rule write / promotion tokens
# ---------------------------------------------------------------------------

class ReviewMemoryNoActiveRuleWriteBoundaryTests(unittest.TestCase):
    """Briefing modules must not promote / write active rules."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.sources = {rel: _read(rel) for rel in _BRIEFING_MODULES}

    def test_no_active_rule_promotion_tokens(self) -> None:
        for rel, source in self.sources.items():
            for token in _FORBIDDEN_ACTIVE_RULE_TOKENS:
                with self.subTest(module=rel, token=token):
                    self.assertFalse(
                        _has_word_token(source, token),
                        msg=(
                            f"{rel} must not contain active-rule "
                            f"promotion / write token `{token}`"
                        ),
                    )

    def test_no_active_rule_pool_imports(self) -> None:
        forbidden = (
            "from services.active_rule_pool",
            "import services.active_rule_pool",
            "from services.active_rule_pool_promotion",
            "import services.active_rule_pool_promotion",
            "from services.active_rule_pool_calibration",
            "import services.active_rule_pool_calibration",
            "from services.promotion_adoption_gate",
            "import services.promotion_adoption_gate",
            "from services.promotion_execution_bridge",
            "import services.promotion_execution_bridge",
        )
        for rel, source in self.sources.items():
            for f in forbidden:
                with self.subTest(module=rel, forbidden=f):
                    self.assertNotIn(
                        f, source,
                        msg=f"{rel} must not contain `{f}`",
                    )


# ---------------------------------------------------------------------------
# 5. _apply_briefing_caution regression boundary (pin 18R)
# ---------------------------------------------------------------------------

class ApplyBriefingCautionRegressionBoundaryTests(unittest.TestCase):
    """Pin the 18R / PR-REVIEW-2 invariant: ``_apply_briefing_caution``
    must remain warning-only.

    This test extracts the function body from ``predict.py`` and runs
    the same source-level scans as the boundary trio, so that a future
    PR cannot quietly re-introduce an in-place rewrite of
    ``final_confidence`` / a forced / required / trading token, etc."""

    @classmethod
    def setUpClass(cls) -> None:
        source = _read("predict.py")
        start = source.index("def _apply_briefing_caution(")
        end_match = re.search(r"\n(def |class )", source[start + 1:])
        end = (start + 1 + end_match.start()) if end_match else len(source)
        cls.body = source[start:end]

    def test_body_does_not_assign_protected_fields(self) -> None:
        for field in _PROTECTED_PREDICTION_FIELDS:
            for quoted in _quoted_keys(field):
                forbidden = f"result[{quoted}] = "
                with self.subTest(field=field, forbidden=forbidden):
                    self.assertNotIn(
                        forbidden, self.body,
                        msg=(
                            f"_apply_briefing_caution body must not assign "
                            f"`{field}`"
                        ),
                    )

    def test_body_does_not_update_protected_fields(self) -> None:
        for field in _PROTECTED_PREDICTION_FIELDS:
            for quoted in _quoted_keys(field):
                forbidden = f"result.update({{{quoted}:"
                with self.subTest(field=field, forbidden=forbidden):
                    self.assertNotIn(
                        forbidden, self.body,
                        msg=(
                            f"_apply_briefing_caution body must not update "
                            f"`{field}`"
                        ),
                    )

    def test_body_does_not_emit_forbidden_tokens(self) -> None:
        for token in _FORBIDDEN_REVIEW_TOKENS:
            for quoted in _quoted_keys(token):
                forbidden = f"result[{quoted}]"
                with self.subTest(token=token, forbidden=forbidden):
                    self.assertNotIn(
                        forbidden, self.body,
                        msg=(
                            f"_apply_briefing_caution body must not "
                            f"reference forbidden output key `{token}`"
                        ),
                    )

    def test_body_only_writes_briefing_caution_marker_keys(self) -> None:
        # AST scan: every ``result["..."] = ...`` subscript-store
        # inside the function body must target a ``briefing_caution_*``
        # key. ``result = dict(result)`` (an identifier rebind) is
        # ignored by this check.
        tree = ast.parse(self.body)
        offending: list[str] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                if not isinstance(target, ast.Subscript):
                    continue
                value = target.value
                if not isinstance(value, ast.Name) or value.id != "result":
                    continue
                slice_node = target.slice
                if not isinstance(slice_node, ast.Constant):
                    continue
                key = slice_node.value
                if not isinstance(key, str):
                    continue
                if not key.startswith("briefing_caution_"):
                    offending.append(key)
        self.assertEqual(
            offending, [],
            msg=(
                "_apply_briefing_caution may only write keys prefixed "
                f"`briefing_caution_`; offending keys: {offending!r}"
            ),
        )


# ---------------------------------------------------------------------------
# 6. End-to-end output shape (mocked; no DB)
# ---------------------------------------------------------------------------

_PATCH_PRE_BRIEF_SUMMARIZE = (
    "services.pre_prediction_briefing.summarize_review_history"
)
_PATCH_PRE_BRIEF_SCENARIO = (
    "services.pre_prediction_briefing."
    "summarize_review_history_by_open_scenario"
)
_PATCH_PRE_BRIEF_RULES = (
    "services.pre_prediction_briefing.extract_review_rules"
)
_PATCH_PROJ_BRIEF_FEEDBACK = (
    "services.projection_memory_briefing.build_memory_feedback"
)


def _empty_summary(symbol: str = "AVGO") -> dict:
    return {
        "symbol": symbol,
        "record_count": 0,
        "overall_accuracy": 0.0,
        "dimension_accuracy": {"open": None, "path": None, "close": None},
        "dimension_sample_count": {"open": 0, "path": 0, "close": 0},
        "weakest_dimension": None,
        "strongest_dimension": None,
        "error_category_counts": {},
        "primary_error_counts": {},
        "most_common_error_category": None,
        "most_common_primary_error": None,
    }


def _scenario_summary(symbol: str = "AVGO") -> dict:
    return {"symbol": symbol, "scenarios": {}}


def _empty_memory_feedback(symbol: str = "AVGO") -> dict:
    return {
        "symbol": symbol.upper(),
        "error_category": None,
        "matched_count": 0,
        "reminders": [],
        "top_categories": [],
    }


class BriefingOutputShapeBoundaryTests(unittest.TestCase):
    """Mocked invocations of the briefing builders: confirm the
    returned dicts contain only advisory / caution / rule / metadata
    keys, never protected prediction-side fields or forbidden trading
    tokens."""

    def _assert_no_protected_or_forbidden_keys(
        self, briefing: dict, *, label: str
    ) -> None:
        for field in _PROTECTED_PREDICTION_FIELDS:
            with self.subTest(label=label, field=field):
                self.assertNotIn(
                    field, briefing,
                    msg=f"{label} output must not carry `{field}`",
                )
        for token in _FORBIDDEN_REVIEW_TOKENS:
            with self.subTest(label=label, token=token):
                self.assertNotIn(
                    token, briefing,
                    msg=f"{label} output must not carry `{token}`",
                )
        for token in _FORBIDDEN_ACTIVE_RULE_TOKENS:
            with self.subTest(label=label, token=token):
                self.assertNotIn(
                    token, briefing,
                    msg=f"{label} output must not carry `{token}`",
                )

    def test_pre_prediction_briefing_empty_state_shape(self) -> None:
        from services.pre_prediction_briefing import build_pre_prediction_briefing
        with patch(_PATCH_PRE_BRIEF_SUMMARIZE, return_value=_empty_summary()), \
             patch(_PATCH_PRE_BRIEF_SCENARIO, return_value=_scenario_summary()), \
             patch(_PATCH_PRE_BRIEF_RULES, return_value=[]):
            briefing = build_pre_prediction_briefing(symbol="AVGO")
        self.assertEqual(briefing.get("advisory_only"), True)
        self.assertIn("caution_level", briefing)
        self.assertIn("has_data", briefing)
        self._assert_no_protected_or_forbidden_keys(
            briefing, label="build_pre_prediction_briefing(empty)"
        )

    def test_pre_prediction_briefing_with_history_shape(self) -> None:
        from services.pre_prediction_briefing import build_pre_prediction_briefing
        history_summary = _empty_summary()
        history_summary.update(
            {
                "record_count": 12,
                "overall_accuracy": 0.30,
                "weakest_dimension": "open",
                "dimension_accuracy": {"open": 0.25, "path": 0.6, "close": 0.55},
                "dimension_sample_count": {"open": 12, "path": 12, "close": 12},
                "most_common_primary_error": "误判开盘",
                "primary_error_counts": {"误判开盘": 5},
                "most_common_error_category": "open_misjudge",
                "error_category_counts": {"open_misjudge": 5},
            }
        )
        with patch(_PATCH_PRE_BRIEF_SUMMARIZE, return_value=history_summary), \
             patch(_PATCH_PRE_BRIEF_SCENARIO, return_value=_scenario_summary()), \
             patch(_PATCH_PRE_BRIEF_RULES, return_value=["历史规则提示 1"]):
            briefing = build_pre_prediction_briefing(symbol="AVGO")
        self.assertEqual(briefing["caution_level"], "high")
        self.assertEqual(briefing["advisory_only"], True)
        self._assert_no_protected_or_forbidden_keys(
            briefing, label="build_pre_prediction_briefing(history)"
        )

    def test_projection_memory_briefing_empty_state_shape(self) -> None:
        from services.projection_memory_briefing import (
            build_projection_memory_briefing,
        )
        with patch(_PATCH_PROJ_BRIEF_FEEDBACK,
                   return_value=_empty_memory_feedback()):
            briefing = build_projection_memory_briefing(symbol="AVGO")
        self.assertEqual(briefing.get("advisory_only"), True)
        self.assertEqual(briefing.get("caution_level"), "none")
        self.assertEqual(briefing.get("matched_count"), 0)
        self._assert_no_protected_or_forbidden_keys(
            briefing, label="build_projection_memory_briefing(empty)"
        )

    def test_projection_memory_briefing_with_matches_shape(self) -> None:
        from services.projection_memory_briefing import (
            build_projection_memory_briefing,
        )
        feedback = _empty_memory_feedback()
        feedback.update(
            {
                "matched_count": 5,
                "reminders": ["Prior AVGO open_misjudge: review past similar"],
                "top_categories": [{"error_category": "open_misjudge", "count": 5}],
            }
        )
        with patch(_PATCH_PROJ_BRIEF_FEEDBACK, return_value=feedback):
            briefing = build_projection_memory_briefing(symbol="AVGO")
        self.assertEqual(briefing.get("advisory_only"), True)
        self.assertEqual(briefing.get("caution_level"), "high")
        self.assertEqual(briefing.get("matched_count"), 5)
        self._assert_no_protected_or_forbidden_keys(
            briefing, label="build_projection_memory_briefing(matches)"
        )

    def test_pre_prediction_briefing_does_not_mutate_summary_input(self) -> None:
        # The briefing builder reads the summary dict but must not
        # mutate it (the cached ``review_analyzer`` callsite would
        # leak modifications back into the analyzer's own state).
        from services.pre_prediction_briefing import build_pre_prediction_briefing
        history_summary = _empty_summary()
        history_summary.update(
            {
                "record_count": 4,
                "overall_accuracy": 0.5,
                "weakest_dimension": "close",
                "dimension_accuracy": {"open": 0.6, "path": 0.5, "close": 0.4},
                "dimension_sample_count": {"open": 4, "path": 4, "close": 4},
            }
        )
        snapshot = deepcopy(history_summary)
        with patch(_PATCH_PRE_BRIEF_SUMMARIZE, return_value=history_summary), \
             patch(_PATCH_PRE_BRIEF_SCENARIO, return_value=_scenario_summary()), \
             patch(_PATCH_PRE_BRIEF_RULES, return_value=[]):
            build_pre_prediction_briefing(symbol="AVGO")
        self.assertEqual(history_summary, snapshot)


# ---------------------------------------------------------------------------
# 7. Source-level: no DB / file write surface in briefing modules
# ---------------------------------------------------------------------------

class NoDBWriteOrFileWriteBoundaryTests(unittest.TestCase):
    """Briefing modules must not contain DB or file write surface
    (insert / update / sqlite connect / write_text / json.dump / open
    in write mode). All persistence is the *post-close* review path's
    job (``review_store.save_review_record`` /
    ``prediction_store.save_*`` / ``memory_store.save_experience``);
    none of those callers may live inside the briefing trio."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.sources = {rel: _read(rel) for rel in _BRIEFING_MODULES}

    def test_no_sqlite_connect(self) -> None:
        for rel, source in self.sources.items():
            with self.subTest(module=rel):
                self.assertNotIn(
                    "sqlite3.connect(", source,
                    msg=f"{rel} must not contain `sqlite3.connect(`",
                )
                self.assertNotIn(
                    "import sqlite3", source,
                    msg=f"{rel} must not contain `import sqlite3`",
                )

    def test_no_insert_or_update_sql(self) -> None:
        for rel, source in self.sources.items():
            for forbidden in (
                ".execute(\"INSERT",
                ".execute('INSERT",
                ".execute(\"UPDATE",
                ".execute('UPDATE",
                ".execute(\"DELETE",
                ".execute('DELETE",
                ".executemany(",
                ".to_sql(",
            ):
                with self.subTest(module=rel, forbidden=forbidden):
                    self.assertNotIn(
                        forbidden, source,
                        msg=f"{rel} must not contain `{forbidden}`",
                    )

    def test_no_file_write_calls(self) -> None:
        # ``open()`` with a write / append mode (``"w"``/``"a"``/``"x"``
        # / their ``b`` variants) is forbidden, as are the high-level
        # ``Path.write_text`` / ``Path.write_bytes`` and
        # ``json.dump(`` / ``json.dumps`` -> file. The grep is a
        # substring scan so any of these surfaces fails the test.
        for rel, source in self.sources.items():
            for forbidden in (
                ".write_text(",
                ".write_bytes(",
                "json.dump(",
                'open("',
                "open('",
            ):
                with self.subTest(module=rel, forbidden=forbidden):
                    self.assertNotIn(
                        forbidden, source,
                        msg=f"{rel} must not contain `{forbidden}`",
                    )

    def test_no_writer_function_calls(self) -> None:
        # Even if a writer module is *not* imported, a future PR could
        # re-export the writer through another module. Scan for the
        # writer call surface as a defence-in-depth.
        for rel, source in self.sources.items():
            for token in (
                "save_review_record",
                "save_experience",
                "save_review",
                "save_prediction",
                "log_prediction",
                "insert_prediction",
                "update_prediction_status",
            ):
                with self.subTest(module=rel, token=token):
                    self.assertFalse(
                        _has_word_token(source, token),
                        msg=(
                            f"{rel} must not contain writer call "
                            f"surface `{token}`"
                        ),
                    )


# ---------------------------------------------------------------------------
# Sanity check: keep the briefing module list aligned with the spec.
# ---------------------------------------------------------------------------

class BriefingModuleListSanityTests(unittest.TestCase):
    def test_each_briefing_module_exists(self) -> None:
        for rel in _BRIEFING_MODULES:
            with self.subTest(module=rel):
                self.assertTrue(
                    (_REPO_ROOT / rel).exists(),
                    msg=f"missing briefing module: {rel}",
                )

    def test_briefing_module_list_has_no_duplicates(self) -> None:
        self.assertEqual(len(set(_BRIEFING_MODULES)), len(_BRIEFING_MODULES))


if __name__ == "__main__":
    unittest.main()
