"""Contract enforcement tests for Step 12A (RISK-1 + RISK-6).

These tests pin the projection / exclusion decoupling boundary:

1. ``build_main_projection_layer`` must not let ``exclusion_result`` change its
   ``state_probabilities`` output.
2. ``services/main_projection_layer.py`` must not import or call
   ``run_exclusion_layer`` (the exclusion entry point).
3. ``services/projection_orchestrator_v2.py`` must not pass ``exclusion_result``
   into ``build_main_projection_layer``.
4. ``services/home_terminal_orchestrator.py`` must not pass ``exclusion_result``
   into ``build_main_projection_layer``.
5. ``exclusion_result`` must remain an independent top-level field in the
   orchestrators' unified payload.
6. ``main_projection`` output must not contain exclusion-adjusted-score fields
   such as ``scores_after_exclusion`` / ``exclusion_applied`` /
   ``raw_scores_before_exclusion`` (see 11A §6 forbidden anti-patterns).
7. The ``main_projection_layer`` peer_alignment fallback chain must not read
   ``exclusion_result.peer_alignment`` (see 11A §2.3 / §4 / §5.1).

Design contracts: 06 / 07A / 07B / 11A / 11H.
"""

from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


_FORBIDDEN_PROJECTION_FIELDS = (
    "scores_after_exclusion",
    "raw_scores_before_exclusion",
    "exclusion_applied",
    "exclusion_adjusted_scores",
    "post_exclusion_scores",
)


def _features_bullish() -> dict[str, object]:
    return {
        "symbol": "AVGO",
        "pos20": 84.0,
        "vol_ratio20": 1.18,
        "upper_shadow_ratio": 0.08,
        "lower_shadow_ratio": 0.10,
        "ret1": 1.8,
        "ret3": 3.2,
        "ret5": 5.8,
        "ret10": 7.5,
    }


def _features_bearish() -> dict[str, object]:
    return {
        "symbol": "AVGO",
        "pos20": 16.0,
        "vol_ratio20": 1.25,
        "upper_shadow_ratio": 0.12,
        "lower_shadow_ratio": 0.08,
        "ret1": -1.7,
        "ret3": -3.0,
        "ret5": -5.4,
        "ret10": -7.2,
    }


class ProjectionLayerDoesNotApplyExclusionTests(unittest.TestCase):
    def test_projection_layer_scores_ignore_exclusion_result_for_big_up(self) -> None:
        from services.main_projection_layer import build_main_projection_layer

        baseline = build_main_projection_layer(
            current_20day_features=_features_bullish(),
            exclusion_result=None,
            historical_match_result={"dominant_historical_outcome": "up_bias"},
            peer_alignment={"up_support": "supported", "down_support": "unsupported"},
        )
        with_exclude_big_up = build_main_projection_layer(
            current_20day_features=_features_bullish(),
            exclusion_result={
                "excluded": True,
                "triggered_rule": "exclude_big_up",
                "peer_alignment": {
                    "up_support": "supported",
                    "down_support": "unsupported",
                },
            },
            historical_match_result={"dominant_historical_outcome": "up_bias"},
            peer_alignment={"up_support": "supported", "down_support": "unsupported"},
        )

        self.assertEqual(
            baseline["state_probabilities"],
            with_exclude_big_up["state_probabilities"],
            msg="projection scores must not be modified by exclusion_result",
        )
        self.assertEqual(
            baseline["predicted_top1"],
            with_exclude_big_up["predicted_top1"],
        )

    def test_projection_layer_scores_ignore_exclusion_result_for_big_down(self) -> None:
        from services.main_projection_layer import build_main_projection_layer

        baseline = build_main_projection_layer(
            current_20day_features=_features_bearish(),
            exclusion_result=None,
            historical_match_result={"dominant_historical_outcome": "down_bias"},
            peer_alignment={"up_support": "unsupported", "down_support": "supported"},
        )
        with_exclude_big_down = build_main_projection_layer(
            current_20day_features=_features_bearish(),
            exclusion_result={
                "excluded": True,
                "triggered_rule": "exclude_big_down",
                "peer_alignment": {
                    "up_support": "unsupported",
                    "down_support": "supported",
                },
            },
            historical_match_result={"dominant_historical_outcome": "down_bias"},
            peer_alignment={"up_support": "unsupported", "down_support": "supported"},
        )

        self.assertEqual(
            baseline["state_probabilities"],
            with_exclude_big_down["state_probabilities"],
            msg="projection scores must not be modified by exclusion_result",
        )
        self.assertEqual(
            baseline["predicted_top1"],
            with_exclude_big_down["predicted_top1"],
        )

    def test_projection_layer_does_not_apply_exclusion(self) -> None:
        """The three calls (None / exclude_big_up / exclude_big_down) must yield
        bit-equal state_probabilities."""
        from services.main_projection_layer import build_main_projection_layer

        features = _features_bullish()

        none_result = build_main_projection_layer(
            current_20day_features=features,
            exclusion_result=None,
            peer_alignment={"up_support": "supported", "down_support": "unsupported"},
        )
        big_up_result = build_main_projection_layer(
            current_20day_features=features,
            exclusion_result={"excluded": True, "triggered_rule": "exclude_big_up"},
            peer_alignment={"up_support": "supported", "down_support": "unsupported"},
        )
        big_down_result = build_main_projection_layer(
            current_20day_features=features,
            exclusion_result={"excluded": True, "triggered_rule": "exclude_big_down"},
            peer_alignment={"up_support": "supported", "down_support": "unsupported"},
        )

        self.assertEqual(
            none_result["state_probabilities"],
            big_up_result["state_probabilities"],
        )
        self.assertEqual(
            none_result["state_probabilities"],
            big_down_result["state_probabilities"],
        )

    def test_projection_output_has_no_exclusion_adjusted_scores(self) -> None:
        from services.main_projection_layer import build_main_projection_layer

        result = build_main_projection_layer(
            current_20day_features=_features_bullish(),
            exclusion_result={"excluded": True, "triggered_rule": "exclude_big_up"},
            peer_alignment={"up_support": "supported", "down_support": "unsupported"},
        )

        for forbidden in _FORBIDDEN_PROJECTION_FIELDS:
            self.assertNotIn(
                forbidden,
                result,
                msg=f"main_projection must not expose {forbidden!r}",
            )


class ProjectionLayerStaticBoundaryTests(unittest.TestCase):
    """Static checks against services/main_projection_layer.py to ensure it
    does not consume exclusion_result inside its function bodies."""

    def setUp(self) -> None:
        self.module_path = (
            ROOT / "services" / "main_projection_layer.py"
        )
        self.source = self.module_path.read_text(encoding="utf-8")
        self.tree = ast.parse(self.source)

    def test_main_projection_layer_does_not_call_run_exclusion_layer(self) -> None:
        # No `run_exclusion_layer` import or call anywhere in the module.
        self.assertNotIn("run_exclusion_layer", self.source)

    def test_main_projection_layer_does_not_apply_exclusion_to_scores(self) -> None:
        """`_apply_exclusion(...)` must not be called in build_main_projection_layer."""
        for node in ast.walk(self.tree):
            if (
                isinstance(node, ast.FunctionDef)
                and node.name == "build_main_projection_layer"
            ):
                func_source = ast.get_source_segment(self.source, node) or ""
                self.assertNotIn(
                    "_apply_exclusion(",
                    func_source,
                    msg="build_main_projection_layer must not call _apply_exclusion",
                )
                # Also: function body must not read exclusion_result.<anything>
                # for the purpose of producing scores. The peer_alignment
                # fallback used to read exclusion_result["peer_alignment"];
                # that fallback is forbidden by 11A §2.3 / §5.1.
                self.assertNotIn(
                    'exclusion_result).get("peer_alignment")',
                    func_source,
                    msg=(
                        "main_projection_layer must not fall back to "
                        "exclusion_result.peer_alignment"
                    ),
                )
                return
        self.fail("build_main_projection_layer not found in module")

    def test_main_projection_peer_alignment_does_not_come_from_exclusion_result(
        self,
    ) -> None:
        # No `exclusion_result.get("peer_alignment")` anywhere in the module.
        self.assertNotIn('exclusion_result.get("peer_alignment")', self.source)
        self.assertNotIn("exclusion_result.get('peer_alignment')", self.source)


class OrchestratorCallSiteBoundaryTests(unittest.TestCase):
    """Static checks against the two active callers to ensure they don't pass
    exclusion_result into build_main_projection_layer."""

    def _read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def _find_call(self, source: str, callee: str) -> ast.Call | None:
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id == callee:
                    return node
                if isinstance(func, ast.Attribute) and func.attr == callee:
                    return node
        return None

    def test_projection_orchestrator_v2_does_not_pass_exclusion_into_projection(
        self,
    ) -> None:
        source = self._read("services/projection_orchestrator_v2.py")
        call = self._find_call(source, "build_main_projection_layer")
        self.assertIsNotNone(call, msg="build_main_projection_layer call missing")
        kw_names = {kw.arg for kw in call.keywords if kw.arg is not None}
        self.assertNotIn("exclusion_result", kw_names)

    def test_home_terminal_orchestrator_does_not_pass_exclusion_into_projection(
        self,
    ) -> None:
        source = self._read("services/home_terminal_orchestrator.py")
        call = self._find_call(source, "build_main_projection_layer")
        self.assertIsNotNone(call, msg="build_main_projection_layer call missing")
        kw_names = {kw.arg for kw in call.keywords if kw.arg is not None}
        self.assertNotIn("exclusion_result", kw_names)


class OrchestratorRuntimeBoundaryTests(unittest.TestCase):
    """Runtime checks: regardless of what the exclusion layer says, projection
    output is unchanged; and exclusion_result remains a parallel field."""

    def _coded_df(self):
        import pandas as pd

        rows = []
        closes = [
            100.0, 100.8, 101.2, 101.6, 102.1,
            102.8, 103.0, 103.6, 104.1, 104.8,
            105.2, 105.9, 106.3, 106.9, 107.1,
            107.8, 108.2, 108.9, 109.4, 110.2,
        ]
        for idx, close in enumerate(closes, start=1):
            rows.append({
                "Date": f"2026-04-{idx:02d}",
                "Open": close - 0.6,
                "High": close + 1.2,
                "Low": close - 1.0,
                "Close": close,
                "Volume": 1000 + idx * 20,
            })
        return pd.DataFrame(rows)

    def _peer_loader(self, move: float):
        import pandas as pd

        df = pd.DataFrame({"Date": ["2026-04-20"], "C_move": [move / 100.0]})

        def _loader(_symbol: str):
            return df

        return _loader

    def test_home_terminal_projection_independent_of_exclusion_result(self) -> None:
        from services import home_terminal_orchestrator as hto

        coded_df = self._coded_df()

        baseline_payload = None
        excluded_payload = None

        original_run_exclusion_layer = hto.run_exclusion_layer

        def _run_exclusion_neutral(_features):
            return {
                "kind": "exclusion_layer",
                "excluded": False,
                "triggered_rule": None,
                "reasons": [],
                "peer_alignment": {
                    "alignment": "mixed",
                    "up_support": "partial",
                    "down_support": "partial",
                },
                "feature_snapshot": {},
            }

        def _run_exclusion_big_up(_features):
            return {
                "kind": "exclusion_layer",
                "excluded": True,
                "triggered_rule": "exclude_big_up",
                "reasons": ["test exclusion"],
                "peer_alignment": {
                    "alignment": "mixed",
                    "up_support": "partial",
                    "down_support": "partial",
                },
                "feature_snapshot": {},
            }

        try:
            hto.run_exclusion_layer = _run_exclusion_neutral
            baseline_payload = hto.build_home_terminal_orchestrator_result(
                scan_result={},
                target_date_str="2026-04-20",
                coded_df=coded_df,
                target_row=coded_df.iloc[-1],
                target_ctx={"ret3": 1.9, "ret5": 3.8},
                peer_loader=self._peer_loader(1.1),
                persist_log=False,
            )

            hto.run_exclusion_layer = _run_exclusion_big_up
            excluded_payload = hto.build_home_terminal_orchestrator_result(
                scan_result={},
                target_date_str="2026-04-20",
                coded_df=coded_df,
                target_row=coded_df.iloc[-1],
                target_ctx={"ret3": 1.9, "ret5": 3.8},
                peer_loader=self._peer_loader(1.1),
                persist_log=False,
            )
        finally:
            hto.run_exclusion_layer = original_run_exclusion_layer

        self.assertIsNotNone(baseline_payload)
        self.assertIsNotNone(excluded_payload)
        self.assertEqual(
            baseline_payload["main_projection"]["state_probabilities"],
            excluded_payload["main_projection"]["state_probabilities"],
            msg=(
                "home_terminal main_projection.state_probabilities must not "
                "depend on exclusion_result"
            ),
        )
        # exclusion_result still appears as parallel top-level field.
        self.assertIn("exclusion_result", excluded_payload)
        self.assertEqual(
            excluded_payload["exclusion_result"].get("triggered_rule"),
            "exclude_big_up",
        )
        # main_projection must not expose exclusion-adjusted-score fields.
        for forbidden in _FORBIDDEN_PROJECTION_FIELDS:
            self.assertNotIn(forbidden, excluded_payload["main_projection"])

    def test_projection_orchestrator_v2_projection_independent_of_exclusion(
        self,
    ) -> None:
        from services import projection_orchestrator_v2 as v2

        # Reuse the existing test helpers' shape by composing a minimal legacy
        # result and primary analysis result here. We must populate
        # avgo_recent_20 so the feature payload has enough features for the
        # projection layer to escape its fallback distribution.
        avgo_recent_20 = []
        closes = [
            100.0, 100.8, 101.2, 101.6, 102.1,
            102.8, 103.0, 103.6, 104.1, 104.8,
            105.2, 105.9, 106.3, 106.9, 107.1,
            107.8, 108.2, 108.9, 109.4, 110.2,
        ]
        for idx, close in enumerate(closes, start=1):
            avgo_recent_20.append({
                "Date": f"2026-04-{idx:02d}",
                "Open": close - 0.6,
                "High": close + 1.2,
                "Low": close - 1.0,
                "Close": close,
                "Volume": 1000 + idx * 20,
            })

        legacy_payload = {
            "symbol": "AVGO",
            "request": {"symbol": "AVGO", "lookback_days": 20},
            "advisory": {
                "matched_count": 0,
                "caution_level": "low",
                "reminder_lines": [],
                "ready": True,
            },
            "projection_report": {
                "kind": "final_projection_report",
                "target_date": "2026-04-21",
                "direction": "偏多",
                "open_tendency": "平开",
                "close_tendency": "偏强",
                "confidence": "medium",
                "basis_summary": [],
                "risk_reminders": [],
                "report_text": "",
                "readable_summary": {"baseline_judgment": {"risk_level": "中"}},
            },
            "predict_result": {"final_bias": "bullish", "final_confidence": "medium"},
            "scan_result": {
                "confirmation_state": "confirmed",
                "avgo_recent_20": avgo_recent_20,
                "relative_strength_5d_summary": {
                    "vs_nvda": "stronger",
                    "vs_soxx": "stronger",
                    "vs_qqq": "stronger",
                },
                "relative_strength_same_day_summary": {
                    "vs_nvda": "stronger",
                    "vs_soxx": "stronger",
                    "vs_qqq": "stronger",
                },
                "historical_match_summary": {
                    "exact_match_count": 2,
                    "near_match_count": 4,
                    "dominant_historical_outcome": "up_bias",
                },
            },
            "ready": True,
        }

        primary_result = {
            "kind": "primary_20day_analysis",
            "symbol": "AVGO",
            "lookback_days": 20,
            "target_date": "2026-04-21",
            "ready": True,
            "direction": "偏多",
            "confidence": "medium",
            "position_label": "高位",
            "stage_label": "延续",
            "volume_state": "正常",
            "summary": "primary",
            "basis": [],
            "warnings": [],
            "features": {
                "latest_close": 120.0,
                "ret_5d": 5.0,
                "ret_10d": 7.0,
                "pos_20d": 85.0,
                "high_20d": 121.0,
                "low_20d": 100.0,
                "vol_ratio_5d": 1.2,
                "days_used": 20,
            },
        }

        empty_preflight = {
            "kind": "projection_rule_preflight",
            "symbol": "AVGO",
            "target_date": None,
            "lookback_days": 20,
            "ready": True,
            "matched_rules": [],
            "rule_warnings": [],
            "rule_adjustments": [],
            "summary": "no rules",
            "warnings": [],
            "source_counts": {
                "memory_items": 0,
                "review_items": 0,
                "matched_rule_count": 0,
            },
        }

        original_run_exclusion_layer = v2.run_exclusion_layer

        def _exclusion_neutral(_features):
            return {
                "kind": "exclusion_layer",
                "excluded": False,
                "triggered_rule": None,
                "reasons": [],
                "peer_alignment": {
                    "alignment": "mixed",
                    "up_support": "partial",
                    "down_support": "partial",
                },
                "feature_snapshot": {},
            }

        def _exclusion_big_up(_features):
            return {
                "kind": "exclusion_layer",
                "excluded": True,
                "triggered_rule": "exclude_big_up",
                "reasons": ["test exclusion"],
                "peer_alignment": {
                    "alignment": "mixed",
                    "up_support": "partial",
                    "down_support": "partial",
                },
                "feature_snapshot": {},
            }

        def _runner(**_):
            return legacy_payload

        def _primary(**_):
            return primary_result

        def _preflight(**_):
            return empty_preflight

        try:
            v2.run_exclusion_layer = _exclusion_neutral
            baseline = v2.run_projection_v2(
                _projection_runner=_runner,
                _primary_analysis_builder=_primary,
                _rule_preflight_builder=_preflight,
            )
            v2.run_exclusion_layer = _exclusion_big_up
            excluded = v2.run_projection_v2(
                _projection_runner=_runner,
                _primary_analysis_builder=_primary,
                _rule_preflight_builder=_preflight,
            )
        finally:
            v2.run_exclusion_layer = original_run_exclusion_layer

        self.assertEqual(
            baseline["main_projection"]["state_probabilities"],
            excluded["main_projection"]["state_probabilities"],
            msg=(
                "projection_orchestrator_v2 main_projection.state_probabilities "
                "must not depend on exclusion_result"
            ),
        )
        # exclusion_result still appears as parallel top-level field.
        self.assertIn("exclusion_result", excluded)
        self.assertEqual(
            excluded["exclusion_result"].get("triggered_rule"),
            "exclude_big_up",
        )


class ExclusionResultRemainsIndependentOutputTests(unittest.TestCase):
    """``exclusion_result`` must continue to be produced independently and
    surfaced in the unified payload alongside ``main_projection``."""

    def test_exclusion_result_remains_independent_output_in_v2(self) -> None:
        # Re-uses the existing test harness shape (run_projection_v2 with
        # default exclusion runner). We assert that the unified payload
        # exposes both `main_projection` and `exclusion_result`.
        from services.projection_orchestrator_v2 import run_projection_v2

        legacy_payload = {
            "symbol": "AVGO",
            "request": {"symbol": "AVGO", "lookback_days": 20},
            "projection_report": {
                "kind": "final_projection_report",
                "target_date": "2026-04-21",
                "direction": "偏多",
                "confidence": "medium",
                "basis_summary": [],
                "risk_reminders": [],
                "report_text": "",
                "readable_summary": {"baseline_judgment": {"risk_level": "中"}},
            },
            "predict_result": {"final_bias": "bullish", "final_confidence": "medium"},
            "scan_result": {
                "confirmation_state": "confirmed",
                "relative_strength_5d_summary": {"vs_nvda": "stronger"},
                "relative_strength_same_day_summary": {"vs_nvda": "stronger"},
                "historical_match_summary": {
                    "exact_match_count": 1,
                    "near_match_count": 1,
                    "dominant_historical_outcome": "mixed",
                },
            },
            "ready": True,
        }

        def _runner(**_):
            return legacy_payload

        def _primary(**_):
            return {
                "kind": "primary_20day_analysis",
                "symbol": "AVGO",
                "lookback_days": 20,
                "target_date": "2026-04-21",
                "ready": True,
                "direction": "偏多",
                "confidence": "medium",
                "summary": "primary",
                "basis": [],
                "warnings": [],
                "features": {
                    "latest_close": 120.0,
                    "ret_5d": 1.0,
                    "ret_10d": 1.0,
                    "pos_20d": 60.0,
                    "high_20d": 121.0,
                    "low_20d": 100.0,
                    "vol_ratio_5d": 1.0,
                    "days_used": 20,
                },
            }

        def _preflight(**_):
            return {
                "kind": "projection_rule_preflight",
                "symbol": "AVGO",
                "target_date": None,
                "lookback_days": 20,
                "ready": True,
                "matched_rules": [],
                "rule_warnings": [],
                "rule_adjustments": [],
                "summary": "no rules",
                "warnings": [],
                "source_counts": {
                    "memory_items": 0,
                    "review_items": 0,
                    "matched_rule_count": 0,
                },
            }

        result = run_projection_v2(
            _projection_runner=_runner,
            _primary_analysis_builder=_primary,
            _rule_preflight_builder=_preflight,
        )

        self.assertIn("main_projection", result)
        self.assertIn("exclusion_result", result)
        self.assertIsInstance(result["exclusion_result"], dict)


if __name__ == "__main__":
    unittest.main()
