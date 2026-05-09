"""Boundary tests for the new ``services.peer_alignment`` shared helper
introduced in Step 17B / PR-C.

Spec source of truth:

- `tasks/record_1_0_architecture_reset_canonical_principles.md` §8 Branch 2
- `tasks/record_16a_architecture_reset_blueprint.md` §6
- `tasks/record_16c_target_dataflow_contract_decision.md` §3 / §7.5
- `tasks/record_16i_core_chain_rebuild_execution_plan.md` §7

PR-C is a **pure move** of ``build_peer_alignment`` from
``services.exclusion_layer`` to ``services.peer_alignment``. Behavior is
unchanged. No other refactor (no ``exclusion_result`` formal-parameter
removal, no schema rename, no orchestrator change).

This suite verifies:

1. ``build_peer_alignment`` is importable from ``services.peer_alignment``.
2. ``services.peer_alignment`` does not import any system / orchestrator /
   UI / DB / LLM module.
3. ``services.main_projection_layer`` no longer imports
   ``services.exclusion_layer`` (the reverse-import boundary violation
   identified in 16B §5.5 / 16C §3.3 is resolved).
4. ``services.exclusion_layer`` re-exports ``build_peer_alignment`` via
   import from ``services.peer_alignment`` (so internal callers keep
   working).
5. Five representative input cases produce the expected output dict
   (semantic-equivalent with the prior implementation; expected values
   are hand-derived from the function logic, not from the pre-move
   module).
6. Both ``services.exclusion_layer.build_peer_alignment`` and
   ``services.peer_alignment.build_peer_alignment`` resolve to the
   **same function object** (re-export, not a fork).
7. ``services.exclusion_layer.run_exclusion_layer`` and
   ``services.exclusion_layer.exclude_big_up`` still execute end-to-end
   after the move (smoke test).
8. ``build_peer_alignment.__module__`` is
   ``services.peer_alignment``.
"""

from __future__ import annotations

import inspect
import unittest
from pathlib import Path

import services.peer_alignment as pa_mod
import services.exclusion_layer as ex_mod
import services.main_projection_layer as mp_mod
from services.peer_alignment import build_peer_alignment


_REPO_ROOT = Path(__file__).resolve().parent.parent


def _read(rel: str) -> str:
    return (_REPO_ROOT / rel).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Import surface
# ---------------------------------------------------------------------------

class PeerAlignmentImportSurfaceTests(unittest.TestCase):
    def test_build_peer_alignment_importable_from_peer_alignment(self) -> None:
        self.assertTrue(callable(build_peer_alignment))
        self.assertEqual(
            build_peer_alignment.__module__,
            "services.peer_alignment",
            msg="build_peer_alignment must live in services.peer_alignment after PR-C",
        )

    def test_exclusion_layer_reexports_same_function_object(self) -> None:
        # exclusion_layer keeps a re-export so its own functions
        # (exclude_big_up / exclude_big_down / run_exclusion_layer) keep
        # calling build_peer_alignment(...) without code change.
        self.assertIs(ex_mod.build_peer_alignment, pa_mod.build_peer_alignment)

    def test_main_projection_layer_uses_same_function_object(self) -> None:
        # main_projection_layer imports from services.peer_alignment now;
        # the function object accessible via the module namespace must be
        # the one defined in services.peer_alignment.
        self.assertIs(mp_mod.build_peer_alignment, pa_mod.build_peer_alignment)


# ---------------------------------------------------------------------------
# 2. Negative-import boundary (peer_alignment is a Feature Layer helper)
# ---------------------------------------------------------------------------

class PeerAlignmentSourceBoundaryTests(unittest.TestCase):
    """The peer_alignment module must not couple to any system /
    orchestrator / UI / DB / LLM. It is feature-only."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = _read("services/peer_alignment.py")

    def test_no_system_or_orchestrator_imports(self) -> None:
        forbidden = (
            "from services.exclusion_layer",
            "import services.exclusion_layer",
            "from services.main_projection_layer",
            "import services.main_projection_layer",
            "from services.confidence_evaluator",
            "import services.confidence_evaluator",
            "from services.final_decision",
            "import services.final_decision",
            "from services.consistency_layer",
            "import services.consistency_layer",
            "from services.projection_orchestrator",
            "import services.projection_orchestrator",
            "from services.projection_orchestrator_v2",
            "import services.projection_orchestrator_v2",
            "from services.home_terminal_orchestrator",
            "import services.home_terminal_orchestrator",
            "from services.standard_projection_payload",
            "import services.standard_projection_payload",
            "from services.predict_legacy_adapter",
            "import services.predict_legacy_adapter",
            "from services.predict_legacy_v2_bridge",
            "import services.predict_legacy_v2_bridge",
            "from predict",
            "import predict",
            "from ui",
            "import ui",
        )
        for f in forbidden:
            self.assertNotIn(
                f,
                self.source,
                msg=f"services.peer_alignment must not contain `{f}`",
            )

    def test_no_db_or_io_or_llm_calls(self) -> None:
        # Pure feature helper: no file / network call patterns.
        for f in ("open(", "Path(", "requests.", "urllib", "http.client"):
            self.assertNotIn(
                f,
                self.source,
                msg=f"services.peer_alignment must not contain `{f}`",
            )

    def test_no_db_or_external_sdk_imports(self) -> None:
        # Match full import statements only — bare names (e.g. "yfinance")
        # would false-positive on docstring prose like
        # "must not import yfinance / OpenAI client".
        for f in (
            "import sqlite3",
            "from sqlite3",
            "import yfinance",
            "from yfinance",
            "import openai",
            "from openai",
        ):
            self.assertNotIn(
                f,
                self.source,
                msg=f"services.peer_alignment must not contain `{f}`",
            )


# ---------------------------------------------------------------------------
# 3. main_projection_layer no longer reverse-imports exclusion_layer
# ---------------------------------------------------------------------------

class MainProjectionLayerImportBoundaryTests(unittest.TestCase):
    """The 16B §5.5 / 16C §3.3 reverse-import violation
    (`from services.exclusion_layer import build_peer_alignment`) must
    be removed by PR-C."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = _read("services/main_projection_layer.py")

    def test_no_exclusion_layer_import_in_main_projection(self) -> None:
        for f in (
            "from services.exclusion_layer",
            "import services.exclusion_layer",
        ):
            self.assertNotIn(
                f,
                self.source,
                msg=(
                    "services.main_projection_layer must not import "
                    "services.exclusion_layer (boundary violation; PR-C "
                    f"should have removed `{f}`)"
                ),
            )

    def test_main_projection_imports_peer_alignment_directly(self) -> None:
        self.assertIn(
            "from services.peer_alignment import build_peer_alignment",
            self.source,
            msg=(
                "services.main_projection_layer should import "
                "build_peer_alignment from services.peer_alignment"
            ),
        )


# ---------------------------------------------------------------------------
# 4. exclusion_layer no longer defines build_peer_alignment locally
# ---------------------------------------------------------------------------

class ExclusionLayerNoLocalDefinitionTests(unittest.TestCase):
    """``services.exclusion_layer`` must not contain its own
    ``def build_peer_alignment`` definition after PR-C; it only
    re-exports the function from ``services.peer_alignment``."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = _read("services/exclusion_layer.py")

    def test_no_local_def_build_peer_alignment(self) -> None:
        self.assertNotIn(
            "def build_peer_alignment",
            self.source,
            msg=(
                "services.exclusion_layer must not define "
                "build_peer_alignment locally after PR-C; the function "
                "lives in services.peer_alignment"
            ),
        )

    def test_imports_build_peer_alignment_from_peer_alignment(self) -> None:
        self.assertIn(
            "from services.peer_alignment import build_peer_alignment",
            self.source,
            msg=(
                "services.exclusion_layer should re-export "
                "build_peer_alignment via import from services.peer_alignment"
            ),
        )


# ---------------------------------------------------------------------------
# 5. Semantic equivalence (5 representative cases — hand-derived expected)
# ---------------------------------------------------------------------------

class PeerAlignmentSemanticEquivalenceTests(unittest.TestCase):
    """Five representative input cases. Expected outputs are derived
    by hand from the function logic in services/peer_alignment.py.

    Threshold semantics:
    - bullish_count counts ret1 >= 0.5
    - bearish_count counts ret1 <= -0.5
    - strong_bullish_count counts ret1 >= 1.0
    - strong_bearish_count counts ret1 <= -1.0
    - up_support: bullish>=2 supported / ==1 partial / else unsupported
    - down_support: bearish>=2 supported / ==1 partial / else unsupported
    - alignment: strong_bullish>=2 bullish / strong_bearish>=2 bearish /
                 (bullish==0 and bearish==0) neutral / else mixed
    """

    def test_case_1_all_strong_bullish(self) -> None:
        # 3 strong bull → bullish=3, strong_bullish=3, bearish=0 →
        # up=supported, down=unsupported, alignment=bullish.
        out = build_peer_alignment(
            {"nvda_ret1": 1.5, "soxx_ret1": 1.2, "qqq_ret1": 1.1}
        )
        self.assertEqual(out["alignment"], "bullish")
        self.assertEqual(out["up_support"], "supported")
        self.assertEqual(out["down_support"], "unsupported")
        self.assertEqual(out["available_peer_count"], 3)
        self.assertEqual(out["peer_returns"], {"NVDA": 1.5, "SOXX": 1.2, "QQQ": 1.1})
        self.assertEqual(
            out["reasons"],
            ["peer alignment：available=3，bullish=3，bearish=0。"],
        )

    def test_case_2_all_strong_bearish(self) -> None:
        # 3 strong bear → bullish=0, bearish=3, strong_bearish=3 →
        # up=unsupported, down=supported, alignment=bearish.
        out = build_peer_alignment(
            {"nvda_ret1": -1.5, "soxx_ret1": -1.2, "qqq_ret1": -1.1}
        )
        self.assertEqual(out["alignment"], "bearish")
        self.assertEqual(out["up_support"], "unsupported")
        self.assertEqual(out["down_support"], "supported")
        self.assertEqual(out["available_peer_count"], 3)
        self.assertEqual(
            out["reasons"],
            ["peer alignment：available=3，bullish=0，bearish=3。"],
        )

    def test_case_3_mixed_one_each(self) -> None:
        # NVDA strong bull, SOXX strong bear, QQQ flat →
        # bullish=1, bearish=1, strong_bullish=1, strong_bearish=1.
        # up=partial, down=partial, alignment=mixed (bullish>0 and bearish>0).
        out = build_peer_alignment(
            {"nvda_ret1": 1.5, "soxx_ret1": -1.5, "qqq_ret1": 0.0}
        )
        self.assertEqual(out["alignment"], "mixed")
        self.assertEqual(out["up_support"], "partial")
        self.assertEqual(out["down_support"], "partial")
        self.assertEqual(out["available_peer_count"], 3)
        self.assertEqual(
            out["peer_returns"],
            {"NVDA": 1.5, "SOXX": -1.5, "QQQ": 0.0},
        )

    def test_case_4_all_neutral_below_thresholds(self) -> None:
        # All available; each |ret1| < 0.5 → bullish=0, bearish=0 →
        # up=unsupported, down=unsupported, alignment=neutral.
        out = build_peer_alignment(
            {"nvda_ret1": 0.1, "soxx_ret1": -0.2, "qqq_ret1": 0.3}
        )
        self.assertEqual(out["alignment"], "neutral")
        self.assertEqual(out["up_support"], "unsupported")
        self.assertEqual(out["down_support"], "unsupported")
        self.assertEqual(out["available_peer_count"], 3)
        self.assertEqual(
            out["reasons"],
            ["peer alignment：available=3，bullish=0，bearish=0。"],
        )

    def test_case_5_missing_all_peers(self) -> None:
        # No peer ret1 at all → safe degrade to "missing".
        out = build_peer_alignment({})
        self.assertEqual(out["alignment"], "missing")
        self.assertEqual(out["up_support"], "unknown")
        self.assertEqual(out["down_support"], "unknown")
        self.assertEqual(out["available_peer_count"], 0)
        self.assertEqual(
            out["peer_returns"],
            {"NVDA": None, "SOXX": None, "QQQ": None},
        )
        self.assertEqual(
            out["reasons"],
            ["缺少 NVDA / SOXX / QQQ 的同日强弱输入，peer alignment 只能保守降级。"],
        )

    def test_case_6_nested_features_envelope(self) -> None:
        # _normalize_features supports a {"features": {...}} envelope
        # plus top-level fields. Verify nested access still works.
        out = build_peer_alignment(
            {"features": {"nvda_ret1": 1.5, "soxx_ret1": 1.2, "qqq_ret1": 1.1}}
        )
        self.assertEqual(out["alignment"], "bullish")
        self.assertEqual(out["up_support"], "supported")
        self.assertEqual(out["available_peer_count"], 3)


# ---------------------------------------------------------------------------
# 6. exclusion_layer internal callers still work (smoke)
# ---------------------------------------------------------------------------

class ExclusionLayerInternalCallersStillWorkTests(unittest.TestCase):
    """Smoke test that ``run_exclusion_layer`` and ``exclude_big_up``
    still execute end-to-end after build_peer_alignment was moved."""

    def test_run_exclusion_layer_smoke(self) -> None:
        from services.exclusion_layer import run_exclusion_layer

        result = run_exclusion_layer({
            "pos20": 50.0,
            "vol_ratio20": 1.0,
            "upper_shadow_ratio": 0.10,
            "lower_shadow_ratio": 0.10,
            "ret1": 0.3,
            "ret3": 0.6,
            "ret5": 0.9,
            "nvda_ret1": 0.4,
            "soxx_ret1": 0.3,
            "qqq_ret1": 0.2,
        })
        self.assertFalse(result["excluded"])
        self.assertEqual(result["action"], "allow")
        self.assertIn("peer_alignment", result)
        self.assertIn("up_support", result["peer_alignment"])
        self.assertIn("down_support", result["peer_alignment"])

    def test_exclude_big_up_uses_shared_peer_alignment(self) -> None:
        from services.exclusion_layer import exclude_big_up

        result = exclude_big_up({
            "pos20": 88.0,
            "vol_ratio20": 0.85,
            "upper_shadow_ratio": 0.40,
            "ret1": 2.5,
            "ret3": 5.0,
            "ret5": 7.5,
            "nvda_ret1": -0.7,
            "soxx_ret1": -0.6,
            "qqq_ret1": -0.5,
        })
        self.assertTrue(result["hit"])
        self.assertIn("peer_alignment", result)


# ---------------------------------------------------------------------------
# 7. Function signature is preserved
# ---------------------------------------------------------------------------

class PeerAlignmentSignaturePreservationTests(unittest.TestCase):
    def test_signature_unchanged(self) -> None:
        sig = inspect.signature(build_peer_alignment)
        self.assertEqual(list(sig.parameters), ["features"])


if __name__ == "__main__":
    unittest.main()
