"""Contract enforcement tests for Step 12E-X4-C (isolated V2-payload
bridge wiring).

X4-C introduces ``services/predict_legacy_v2_bridge.py``, an isolated
helper that lets offline / diagnostic / contract-replay callers exercise
``predict.run_predict``'s X4-B opt-in adapter path. The bridge is the
ONLY caller that wires the v2_payload kwarg in this codebase. No active
caller (UI / app.py / command bar / live prediction / V1 orchestrator
re-entry / replay writer) passes ``v2_payload`` to ``run_predict``.

Pinned contract:

1. The bridge's default behavior with ``v2_payload=None`` returns the
   wrapper's X3 legacy baseline plus bridge metadata; no overlay.
2. Passing a dict ``v2_payload`` exercises the X4-B opt-in path:
   ``v2_adapter_used == True`` and the allowlisted compat keys are
   overlaid from the adapter result.
3. Missing / non-dict ``v2_payload`` does NOT raise; the bridge logs a
   warning and returns the legacy baseline. The wrapper output never
   reports ``v2_adapter_used == True`` in this case.
4. The bridge module's TOP-LEVEL imports do not include
   ``projection_orchestrator_v2``, ``ai_summary``, the promotion
   modules, ``continuous_smoothing``, ``app``, ``ui.``, ``streamlit``,
   ``sqlite3``, or ``services.prediction_store``. The lone import of
   ``predict.run_predict`` is intentionally lazy (inside the helper)
   and is allowed.
5. Active callers (``app.py`` / ``ui/predict_tab.py`` /
   ``ui/command_bar.py`` / ``services/projection_orchestrator.py`` /
   ``scripts/run_e2e_loop.py`` / ``services/contract_replay_writer.py``)
   do NOT import the bridge and do NOT pass ``v2_payload`` to
   ``run_predict``.
6. ``predict.run_predict`` does not default-call the V2 orchestrator and
   still does not import ``services.projection_orchestrator_v2`` at
   module load (X4-B already enforces this; X4-C re-affirms it through
   a direct AST check, with the same lazy-import allowance for
   ``_build_projection_three_systems_attachment``).
7. Bridge output never carries trading / hard / forced / required /
   promotion / mutation surfaces.
8. Bridge does not mutate ``v2_payload``.
9. Bridge does not write to the database (``save_prediction`` /
   ``save_outcome`` / ``services.prediction_store`` are not invoked by
   the bridge call).

Design contracts: 06 / 07A / 07C / 07D / 11E §7 X4 / 11H.
"""

from __future__ import annotations

import ast
import copy
import importlib
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _fresh_predict_module():
    """Reload ``predict`` to defeat the ``app_analysis_context_fixture``
    monkeypatch that replaces ``predict.run_predict`` during AppTest
    runs (see the X1/X2/X3/X4-B boundary test files for the same
    workaround)."""
    import predict as _predict

    return importlib.reload(_predict)


def _fresh_bridge_module():
    """Return a fresh ``services.predict_legacy_v2_bridge`` module.

    Reloading the bridge after reloading ``predict`` ensures the lazy
    import inside ``build_legacy_prediction_from_v2_payload`` rebinds to
    the real (un-monkeypatched) wrapper."""
    _fresh_predict_module()
    import services.predict_legacy_v2_bridge as _bridge

    return importlib.reload(_bridge)


_FORBIDDEN_OUTPUT_FIELDS = (
    "trading_action",
    "buy",
    "sell",
    "hold",
    "simulated_trade",
    "no_trade",
    "hard_exclusion",
    "forced_exclusion",
    "required_decision",
    "production_promotion",
    "_PROTECTION_LAYER_CONNECTED",
    "final_report_mutation",
    "modified_projection",
    "modified_exclusion",
    "modified_confidence",
    "overridden_most_likely_state",
    "corrected_confidence",
)


_OVERLAY_KEYS = (
    "final_bias",
    "direction",
    "final_confidence",
    "confidence",
    "prediction_summary",
    "summary",
    "primary_projection",
    "peer_adjustment",
    "final_projection",
    "path_risk",
    "supporting_factors",
    "conflicting_factors",
)


def _populated_v2_payload() -> dict:
    """A minimally complete V2 payload that exercises every adapter
    priority-1 source (final_decision direction + confidence_result
    level + final_report.combined_user_summary + main projection /
    peer / final_projection blocks)."""
    return {
        "final_decision": {
            "final_direction": "偏多",
            "decision_factors": {
                "supporting": ["bridge_test:gap_up", "bridge_test:vol_expand"],
                "conflicting": ["bridge_test:weak_close"],
            },
            "risk_level": "low",
        },
        "confidence_result": {
            "combined_confidence": {"level": "medium"},
        },
        "final_report": {
            "combined_user_summary": "Bridge test summary from final_report.",
        },
        "primary_analysis": {"predicted_top1": {"state": "high_go"}},
        "peer_adjustment": {"vs_nvda": "stronger"},
        "final_projection": {"final_direction": "偏多"},
        "path_risk": {"risk_level": "low"},
    }


# ── 1. Bridge: default / missing v2_payload ───────────────────────────


class BridgeDefaultBaselineTests(unittest.TestCase):
    """When ``v2_payload`` is None or invalid, the bridge returns the
    wrapper's X3 legacy baseline and records a warning. No adapter
    overlay is applied."""

    def test_bridge_default_does_not_use_v2_payload(self) -> None:
        bridge = _fresh_bridge_module()
        result = bridge.build_legacy_prediction_from_v2_payload(
            v2_payload=None,
        )
        # X4-B contract: when run_predict receives v2_payload=None, the
        # overlay helper is a no-op. The bridge layer must NOT inject
        # ``v2_adapter_used`` from its own warning bookkeeping.
        self.assertNotIn(
            "v2_adapter_used",
            result,
            msg="v2_payload=None must NOT cause v2_adapter_used to be set",
        )
        # Legacy missing-scan baseline is preserved.
        self.assertEqual(result["final_bias"], "unavailable")
        self.assertEqual(result["scan_bias"], "missing")
        # Bridge metadata is always attached.
        self.assertEqual(result["bridge_kind"], bridge.BRIDGE_KIND)
        self.assertEqual(result["bridge_version"], bridge.BRIDGE_VERSION)

    def test_bridge_default_records_warning(self) -> None:
        bridge = _fresh_bridge_module()
        result = bridge.build_legacy_prediction_from_v2_payload(
            v2_payload=None,
        )
        warnings = result.get("v2_adapter_warnings") or []
        joined = " ".join(warnings)
        self.assertIn("predict_legacy_v2_bridge", joined)
        self.assertIn("v2_payload missing", joined)


class BridgeNonDictPayloadTests(unittest.TestCase):
    """Non-dict v2_payload (string / list / int / bool) is non-fatal."""

    def test_bridge_string_v2_payload_does_not_crash(self) -> None:
        bridge = _fresh_bridge_module()
        result = bridge.build_legacy_prediction_from_v2_payload(
            v2_payload="not a dict",
        )
        self.assertNotIn("v2_adapter_used", result)
        self.assertEqual(result["bridge_kind"], bridge.BRIDGE_KIND)

    def test_bridge_list_v2_payload_does_not_crash(self) -> None:
        bridge = _fresh_bridge_module()
        result = bridge.build_legacy_prediction_from_v2_payload(
            v2_payload=[{"final_decision": {}}],  # noqa: list, not dict
        )
        warnings = result.get("v2_adapter_warnings") or []
        self.assertTrue(
            any("predict_legacy_v2_bridge" in w for w in warnings),
            msg="bridge must record a warning for non-dict v2_payload",
        )


# ── 2. Bridge: dict v2_payload exercises X4-B opt-in path ─────────────


class BridgeDictPayloadOverlayTests(unittest.TestCase):
    """Dict v2_payload routes through run_predict's X4-B path and
    overlays the allowlist compat keys."""

    def test_bridge_dict_payload_sets_v2_adapter_used(self) -> None:
        bridge = _fresh_bridge_module()
        result = bridge.build_legacy_prediction_from_v2_payload(
            v2_payload=_populated_v2_payload(),
        )
        self.assertIs(result.get("v2_adapter_used"), True)

    def test_bridge_dict_payload_overlays_direction(self) -> None:
        bridge = _fresh_bridge_module()
        result = bridge.build_legacy_prediction_from_v2_payload(
            v2_payload=_populated_v2_payload(),
        )
        # Adapter pulls final_decision.final_direction.
        self.assertEqual(result["final_bias"], "偏多")
        self.assertEqual(result["direction"], "偏多")

    def test_bridge_dict_payload_overlays_confidence(self) -> None:
        bridge = _fresh_bridge_module()
        result = bridge.build_legacy_prediction_from_v2_payload(
            v2_payload=_populated_v2_payload(),
        )
        self.assertEqual(result["final_confidence"], "medium")
        self.assertEqual(result["confidence"], "medium")

    def test_bridge_dict_payload_overlays_summary(self) -> None:
        bridge = _fresh_bridge_module()
        result = bridge.build_legacy_prediction_from_v2_payload(
            v2_payload=_populated_v2_payload(),
        )
        self.assertEqual(
            result["prediction_summary"],
            "Bridge test summary from final_report.",
        )

    def test_bridge_dict_payload_surfaces_adapter_result(self) -> None:
        bridge = _fresh_bridge_module()
        result = bridge.build_legacy_prediction_from_v2_payload(
            v2_payload=_populated_v2_payload(),
        )
        adapter_result = result.get("v2_adapter_result") or {}
        self.assertEqual(
            adapter_result.get("adapter_kind"),
            "v2_to_predict_legacy_adapter",
        )
        self.assertEqual(
            adapter_result.get("adapter_version"),
            "v2_to_predict_legacy_adapter.v1",
        )
        # Adapter result must NOT carry the bulk legacy_fields (already
        # merged into the top-level result by the X4-B helper).
        self.assertNotIn("legacy_fields", adapter_result)


class BridgeMetadataTests(unittest.TestCase):
    def test_bridge_kind_and_version_constants(self) -> None:
        bridge = _fresh_bridge_module()
        self.assertEqual(bridge.BRIDGE_KIND, "predict_legacy_v2_bridge")
        self.assertEqual(bridge.BRIDGE_VERSION, "predict_legacy_v2_bridge.v1")

    def test_bridge_dict_result_carries_bridge_metadata(self) -> None:
        bridge = _fresh_bridge_module()
        result = bridge.build_legacy_prediction_from_v2_payload(
            v2_payload=_populated_v2_payload(),
        )
        self.assertEqual(result["bridge_kind"], "predict_legacy_v2_bridge")
        self.assertEqual(result["bridge_version"], "predict_legacy_v2_bridge.v1")


# ── 3. Bridge does not mutate inputs ───────────────────────────────────


class BridgeNonMutationTests(unittest.TestCase):
    def test_bridge_does_not_mutate_v2_payload(self) -> None:
        bridge = _fresh_bridge_module()
        payload = _populated_v2_payload()
        snapshot = copy.deepcopy(payload)
        bridge.build_legacy_prediction_from_v2_payload(v2_payload=payload)
        self.assertEqual(payload, snapshot)

    def test_bridge_does_not_mutate_fallback_legacy_payload(self) -> None:
        bridge = _fresh_bridge_module()
        fallback = {"final_bias": "neutral", "final_confidence": "low"}
        snapshot = copy.deepcopy(fallback)
        bridge.build_legacy_prediction_from_v2_payload(
            v2_payload=_populated_v2_payload(),
            fallback_legacy_payload=fallback,
        )
        self.assertEqual(fallback, snapshot)


# ── 4. Bridge output forbidden-field enforcement ──────────────────────


class BridgeForbiddenFieldsTests(unittest.TestCase):
    def test_bridge_no_forbidden_fields_default(self) -> None:
        bridge = _fresh_bridge_module()
        result = bridge.build_legacy_prediction_from_v2_payload(
            v2_payload=None,
        )
        for field in _FORBIDDEN_OUTPUT_FIELDS:
            self.assertNotIn(
                field,
                result,
                msg=f"bridge default output must not contain {field!r}",
            )

    def test_bridge_no_forbidden_fields_with_payload(self) -> None:
        bridge = _fresh_bridge_module()
        result = bridge.build_legacy_prediction_from_v2_payload(
            v2_payload=_populated_v2_payload(),
        )
        for field in _FORBIDDEN_OUTPUT_FIELDS:
            self.assertNotIn(
                field,
                result,
                msg=f"bridge output must not contain {field!r}",
            )


# ── 5. Bridge does not run V2 orchestrator / write DB / call LLM ──────


class BridgeRuntimeIsolationTests(unittest.TestCase):
    """Runtime checks: invoking the bridge must not call into the V2
    orchestrator, the prediction_store DB-write entry points, or the
    OpenAI LLM client."""

    def _patch_targets(self):
        return [
            mock.patch(
                "services.projection_orchestrator_v2.run_projection_v2",
                side_effect=AssertionError(
                    "bridge must not call run_projection_v2"
                ),
            ),
            mock.patch(
                "services.prediction_store.save_prediction",
                side_effect=AssertionError(
                    "bridge must not call save_prediction"
                ),
            ),
            mock.patch(
                "services.prediction_store.save_outcome",
                side_effect=AssertionError(
                    "bridge must not call save_outcome"
                ),
            ),
        ]

    def test_bridge_default_does_not_call_v2_orchestrator(self) -> None:
        bridge = _fresh_bridge_module()
        patchers = self._patch_targets()
        for p in patchers:
            p.start()
        try:
            bridge.build_legacy_prediction_from_v2_payload(v2_payload=None)
        finally:
            for p in patchers:
                p.stop()

    def test_bridge_dict_payload_does_not_call_v2_orchestrator(self) -> None:
        bridge = _fresh_bridge_module()
        patchers = self._patch_targets()
        for p in patchers:
            p.start()
        try:
            bridge.build_legacy_prediction_from_v2_payload(
                v2_payload=_populated_v2_payload(),
            )
        finally:
            for p in patchers:
                p.stop()


# ── 6. Static checks: bridge module imports + active path imports ─────


class BridgeStaticImportTests(unittest.TestCase):
    """Inspect ``services/predict_legacy_v2_bridge.py``'s top-level AST
    Import / ImportFrom nodes. The bridge must not import V2
    orchestrator, ai_summary, promotion, continuous_smoothing, app,
    ui.*, streamlit, sqlite3, or prediction_store at module load.
    The lazy import of ``predict.run_predict`` is allowed because it
    happens inside the helper's function body."""

    def setUp(self) -> None:
        self.module_path = ROOT / "services" / "predict_legacy_v2_bridge.py"
        self.source = self.module_path.read_text(encoding="utf-8")
        self.tree = ast.parse(self.source, filename=str(self.module_path))

    def _module_level_modules(self) -> list[str]:
        names: list[str] = []
        for node in self.tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    names.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    names.append(node.module)
        return names

    def test_bridge_does_not_import_v2_orchestrator(self) -> None:
        for name in self._module_level_modules():
            self.assertNotIn(
                "projection_orchestrator_v2",
                name,
                msg=(
                    f"bridge top-level import {name!r} must not reference "
                    "projection_orchestrator_v2"
                ),
            )

    def test_bridge_does_not_import_ai_summary(self) -> None:
        for name in self._module_level_modules():
            self.assertFalse(
                name.endswith("services.ai_summary")
                or name == "ai_summary",
                msg=(
                    f"bridge top-level import {name!r} must not reference "
                    "ai_summary"
                ),
            )

    def test_bridge_does_not_import_promotion_modules(self) -> None:
        for forbidden in (
            "services.active_rule_pool_promotion",
            "services.promotion_adoption_gate",
            "services.promotion_execution_bridge",
        ):
            for name in self._module_level_modules():
                self.assertNotEqual(
                    name,
                    forbidden,
                    msg=f"bridge must not import {forbidden!r}",
                )

    def test_bridge_does_not_import_continuous_smoothing(self) -> None:
        for name in self._module_level_modules():
            self.assertNotIn(
                "continuous_smoothing",
                name,
                msg=(
                    f"bridge top-level import {name!r} must not reference "
                    "continuous_smoothing"
                ),
            )

    def test_bridge_does_not_import_ui_or_app(self) -> None:
        for name in self._module_level_modules():
            self.assertFalse(
                name == "app" or name.startswith("ui.") or name == "ui",
                msg=(
                    f"bridge top-level import {name!r} must not reference "
                    "app / ui"
                ),
            )

    def test_bridge_does_not_import_streamlit(self) -> None:
        for name in self._module_level_modules():
            self.assertNotIn(
                "streamlit",
                name,
                msg=f"bridge must not import streamlit at module load",
            )

    def test_bridge_does_not_import_db_or_prediction_store(self) -> None:
        for name in self._module_level_modules():
            self.assertNotIn(
                "sqlite3",
                name,
                msg="bridge must not import sqlite3 at module load",
            )
            self.assertNotIn(
                "prediction_store",
                name,
                msg="bridge must not import prediction_store at module load",
            )

    def test_bridge_does_not_import_predict_at_module_level(self) -> None:
        """Lazy import inside the helper is the only allowed ``predict``
        reference; pulling ``predict`` into module load would inflate
        the active import graph for any bystander that touches the
        bridge."""
        for name in self._module_level_modules():
            self.assertNotEqual(
                name,
                "predict",
                msg=(
                    "bridge must not import predict at module level "
                    "(lazy import inside helper is required)"
                ),
            )


class ActiveCallerStaticImportTests(unittest.TestCase):
    """The X4-C bridge must NOT be imported by any active caller. Active
    callers must NOT pass ``v2_payload`` to ``run_predict`` either."""

    _ACTIVE_CALLER_PATHS = (
        ("app.py",),
        ("ui", "predict_tab.py"),
        ("ui", "command_bar.py"),
        ("ui", "history_tab.py"),
        ("ui", "home_tab.py"),
        ("ui", "scan_tab.py"),
        ("ui", "research_tab.py"),
        ("ui", "review_tab.py"),
        ("ui", "inspect_tab.py"),
        ("services", "projection_orchestrator.py"),
        ("services", "contract_replay_writer.py"),
        ("scripts", "run_e2e_loop.py"),
    )

    def _read(self, parts: tuple[str, ...]) -> str:
        path = ROOT.joinpath(*parts)
        return path.read_text(encoding="utf-8")

    def test_active_callers_do_not_import_bridge(self) -> None:
        forbidden_imports = (
            "services.predict_legacy_v2_bridge",
            "predict_legacy_v2_bridge",
        )
        for parts in self._ACTIVE_CALLER_PATHS:
            source = self._read(parts)
            for forbidden in forbidden_imports:
                self.assertNotIn(
                    forbidden,
                    source,
                    msg=(
                        f"{'/'.join(parts)} must not import the X4-C bridge"
                    ),
                )

    def test_active_callers_do_not_pass_v2_payload(self) -> None:
        for parts in self._ACTIVE_CALLER_PATHS:
            source = self._read(parts)
            self.assertNotIn(
                "v2_payload=",
                source,
                msg=(
                    f"{'/'.join(parts)} must not pass v2_payload= to "
                    "run_predict (X4-C scope: opt-in is bridge-only)"
                ),
            )


class PredictRunPredictDefaultStaticReaffirmTests(unittest.TestCase):
    """X4-C re-affirms: ``predict.py`` does not pull V2 / promotion /
    continuous_smoothing / ai_summary at module load. The helper in
    ``_build_projection_three_systems_attachment`` keeps its lazy
    ``from services.projection_orchestrator_v2 import ...`` line, which
    is allowed because it lives inside the function body and is gated
    by the re-entry guard introduced in Task 104."""

    def setUp(self) -> None:
        self.module_path = ROOT / "predict.py"
        self.source = self.module_path.read_text(encoding="utf-8")
        self.tree = ast.parse(self.source, filename=str(self.module_path))

    def _module_level_modules(self) -> list[str]:
        names: list[str] = []
        for node in self.tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    names.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    names.append(node.module)
        return names

    def test_predict_module_does_not_top_level_import_v2(self) -> None:
        for name in self._module_level_modules():
            self.assertNotIn(
                "projection_orchestrator_v2",
                name,
                msg=(
                    f"predict.py top-level import {name!r} must not "
                    "reference projection_orchestrator_v2"
                ),
            )

    def test_predict_module_does_not_import_promotion(self) -> None:
        for forbidden in (
            "services.active_rule_pool_promotion",
            "services.promotion_adoption_gate",
            "services.promotion_execution_bridge",
        ):
            for name in self._module_level_modules():
                self.assertNotEqual(
                    name,
                    forbidden,
                    msg=f"predict.py must not import {forbidden!r}",
                )

    def test_predict_module_does_not_import_continuous_smoothing(self) -> None:
        for name in self._module_level_modules():
            self.assertNotIn(
                "continuous_smoothing",
                name,
                msg=(
                    f"predict.py top-level import {name!r} must not reference "
                    "continuous_smoothing"
                ),
            )

    def test_predict_module_does_not_import_ai_summary(self) -> None:
        for name in self._module_level_modules():
            self.assertFalse(
                name.endswith("services.ai_summary")
                or name == "ai_summary",
                msg=f"predict.py must not import ai_summary at module load",
            )


# ── 7. Bridge runtime: run_predict default vs opt-in branch ───────────


class BridgeRunPredictBranchTests(unittest.TestCase):
    """Verify the bridge invokes ``run_predict`` exactly once per call,
    and the v2_payload kwarg is forwarded only when a dict was supplied."""

    def test_bridge_default_calls_run_predict_with_none_v2_payload(self) -> None:
        bridge = _fresh_bridge_module()
        with mock.patch(
            "predict.run_predict", autospec=True
        ) as mock_run:
            mock_run.return_value = {"final_bias": "unavailable"}
            bridge.build_legacy_prediction_from_v2_payload(v2_payload=None)
        self.assertEqual(mock_run.call_count, 1)
        kwargs = mock_run.call_args.kwargs
        # v2_payload must NOT be present when v2_payload is None — the
        # bridge takes the simple legacy code path.
        self.assertNotIn("v2_payload", kwargs)

    def test_bridge_dict_payload_forwards_v2_payload(self) -> None:
        bridge = _fresh_bridge_module()
        payload = _populated_v2_payload()
        with mock.patch(
            "predict.run_predict", autospec=True
        ) as mock_run:
            mock_run.return_value = {
                "final_bias": "偏多",
                "v2_adapter_used": True,
            }
            bridge.build_legacy_prediction_from_v2_payload(
                v2_payload=payload,
            )
        self.assertEqual(mock_run.call_count, 1)
        kwargs = mock_run.call_args.kwargs
        self.assertIn("v2_payload", kwargs)
        self.assertIs(kwargs["v2_payload"], payload)

    def test_bridge_non_dict_payload_does_not_forward_v2_payload(self) -> None:
        bridge = _fresh_bridge_module()
        with mock.patch(
            "predict.run_predict", autospec=True
        ) as mock_run:
            mock_run.return_value = {"final_bias": "unavailable"}
            bridge.build_legacy_prediction_from_v2_payload(
                v2_payload="not a dict",
            )
        self.assertEqual(mock_run.call_count, 1)
        kwargs = mock_run.call_args.kwargs
        self.assertNotIn(
            "v2_payload",
            kwargs,
            msg=(
                "non-dict v2_payload must not be forwarded; bridge falls "
                "back to legacy run_predict call"
            ),
        )


if __name__ == "__main__":
    unittest.main()
