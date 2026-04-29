# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from predict import (
    apply_peer_adjustment,
    build_final_projection,
    build_primary_projection,
    run_predict,
)


def _recent_rows(close_start: float = 100.0, close_step: float = 1.0) -> list[dict]:
    return [
        {
            "Date": f"2026-04-{day:02d}",
            "Open": close_start + (day - 1) * close_step - 0.25,
            "Close": close_start + (day - 1) * close_step,
            "O_gap": 0.006 if close_step >= 0 else -0.006,
            "C_move": 0.01 if close_step >= 0 else -0.01,
            "V_ratio": 1.2 if close_step >= 0 else 0.8,
        }
        for day in range(1, 21)
    ]


def _scan(
    *,
    gap: str = "gap_up",
    intraday: str = "high_go",
    volume: str = "expanding",
    price: str = "bullish",
    dominant: str = "up_bias",
    rs_5d: dict | None = None,
    rs_same_day: dict | None = None,
) -> dict:
    return {
        "symbol": "AVGO",
        "scan_bias": "bullish",
        "scan_confidence": "medium",
        "avgo_gap_state": gap,
        "avgo_intraday_state": intraday,
        "avgo_volume_state": volume,
        "avgo_price_state": price,
        "historical_match_summary": {
            "dominant_historical_outcome": dominant,
        },
        "avgo_recent_20": _recent_rows(close_step=1.0),
        "relative_strength_summary": rs_5d or {
            "vs_nvda": "stronger",
            "vs_soxx": "stronger",
            "vs_qqq": "neutral",
        },
        "relative_strength_same_day_summary": rs_same_day or {
            "vs_nvda": "stronger",
            "vs_soxx": "neutral",
            "vs_qqq": "stronger",
        },
    }


class PrimaryProjectionTests(unittest.TestCase):
    def test_primary_projection_is_avgo_only(self) -> None:
        scan = _scan(
            rs_5d={"vs_nvda": "weaker", "vs_soxx": "weaker", "vs_qqq": "weaker"},
            rs_same_day={"vs_nvda": "weaker", "vs_soxx": "weaker", "vs_qqq": "weaker"},
        )

        primary = build_primary_projection(scan)

        self.assertEqual(primary["status"], "computed")
        self.assertIs(primary["peer_inputs_used"], False)
        self.assertEqual(primary["lookback_days"], 20)
        self.assertEqual(primary["recent_20_summary"]["sample_count"], 20)
        self.assertGreater(primary["recent_20_summary"]["close_return"], 0)
        self.assertEqual(primary["direct_features"]["gap_state"], "gap_up")
        self.assertEqual(primary["direct_features"]["recent_20_trend_state"], "bullish")
        self.assertFalse(primary["input_boundary"]["fallback_scan_states_used"])
        self.assertIn("historical_match_summary", primary["input_boundary"]["excluded_inputs"])
        self.assertNotIn("historical_match_summary", primary)
        self.assertFalse(any("dominant_historical_outcome" in signal for signal in primary["signals"]))
        self.assertEqual(primary["final_bias"], "bullish")
        self.assertEqual(primary["pred_open"], "高开")
        self.assertEqual(primary["pred_close"], "收涨")
        self.assertEqual(primary["pred_path"], "高开高走")

    def test_primary_projection_ignores_historical_match_direction(self) -> None:
        up_history = build_primary_projection(_scan(dominant="up_bias"))
        down_history = build_primary_projection(_scan(dominant="down_bias"))

        self.assertEqual(up_history["score"], down_history["score"])
        self.assertEqual(up_history["signals"], down_history["signals"])

    def test_missing_scan_returns_unavailable_primary(self) -> None:
        primary = build_primary_projection(None)

        self.assertEqual(primary["status"], "unavailable")
        self.assertEqual(primary["lookback_days"], 20)
        self.assertEqual(primary["final_bias"], "unavailable")
        self.assertIs(primary["pred_open"], None)


class PeerAdjustmentTests(unittest.TestCase):
    def test_peer_confirmation_reinforces_confidence(self) -> None:
        primary = {
            "final_bias": "bullish",
            "final_confidence": "medium",
        }

        adjustment = apply_peer_adjustment(primary, _scan())

        self.assertEqual(adjustment["status"], "computed")
        self.assertEqual(adjustment["adjustment_direction"], "reinforce")
        self.assertEqual(adjustment["adjusted_bias"], "bullish")
        self.assertEqual(adjustment["adjusted_confidence"], "high")
        self.assertEqual(adjustment["confirm_count"], 3)
        self.assertEqual(adjustment["path_risk_adjustment"]["risk_direction"], "lower")
        self.assertEqual(adjustment["path_risk_adjustment"]["after"], "low")
        self.assertEqual(adjustment["data_source"]["current"], "scanner_relative_strength_labels")

    def test_peer_divergence_weakens_confidence(self) -> None:
        primary = {
            "final_bias": "bullish",
            "final_confidence": "medium",
        }
        scan = _scan(
            rs_5d={"vs_nvda": "weaker", "vs_soxx": "weaker", "vs_qqq": "neutral"},
            rs_same_day={"vs_nvda": "weaker", "vs_soxx": "weaker", "vs_qqq": "weaker"},
        )

        adjustment = apply_peer_adjustment(primary, scan)

        self.assertEqual(adjustment["adjustment_direction"], "weaken")
        self.assertEqual(adjustment["adjusted_bias"], "bullish")
        self.assertEqual(adjustment["adjusted_confidence"], "low")
        self.assertEqual(adjustment["oppose_count"], 3)
        self.assertEqual(adjustment["path_risk_adjustment"]["risk_direction"], "higher")
        self.assertEqual(adjustment["path_risk_adjustment"]["after"], "high")


class FinalProjectionTests(unittest.TestCase):
    def test_final_projection_keeps_prediction_compatibility_fields(self) -> None:
        primary = build_primary_projection(_scan())
        peer = apply_peer_adjustment(primary, _scan())

        final = build_final_projection(primary, peer, research_result=None, scan_result=_scan())

        self.assertEqual(final["status"], "computed")
        self.assertEqual(final["source"], "primary_projection_plus_peer_adjustment")
        self.assertEqual(final["final_bias"], "bullish")
        self.assertEqual(final["final_confidence"], "high")
        self.assertEqual(final["open_tendency"], "gap_up_bias")
        self.assertEqual(final["close_tendency"], "close_strong")
        self.assertEqual(final["pred_open"], "高开")
        self.assertEqual(final["pred_path"], "高开高走")
        self.assertEqual(final["path_risk"], "low")
        self.assertEqual(final["peer_path_risk_adjustment"]["risk_direction"], "lower")

    def test_final_projection_keeps_path_label_but_marks_peer_path_risk(self) -> None:
        primary = build_primary_projection(_scan())
        peer = apply_peer_adjustment(
            primary,
            _scan(
                rs_5d={"vs_nvda": "weaker", "vs_soxx": "weaker", "vs_qqq": "weaker"},
                rs_same_day={"vs_nvda": "weaker", "vs_soxx": "weaker", "vs_qqq": "weaker"},
            ),
        )

        final = build_final_projection(primary, peer, research_result=None, scan_result=_scan())

        self.assertEqual(final["pred_path"], primary["pred_path"])
        self.assertEqual(final["path_risk"], "medium")
        self.assertEqual(final["peer_path_risk_adjustment"]["risk_direction"], "higher")
        self.assertIn("peer_path_risk=medium", final["conflicting_factors"])


class RunPredictV2Tests(unittest.TestCase):
    def test_run_predict_returns_old_fields_and_v2_blocks(self) -> None:
        result = run_predict(_scan(), research_result=None, symbol="AVGO")

        for key in (
            "symbol",
            "final_bias",
            "final_confidence",
            "open_tendency",
            "close_tendency",
            "prediction_summary",
        ):
            self.assertIn(key, result)

        self.assertEqual(result["primary_projection"]["status"], "computed")
        self.assertEqual(result["peer_adjustment"]["status"], "computed")
        self.assertEqual(result["final_projection"]["status"], "computed")
        self.assertEqual(result["final_bias"], result["final_projection"]["final_bias"])
        self.assertEqual(result["pred_open"], result["final_projection"]["pred_open"])
        self.assertEqual(result["path_risk"], result["final_projection"]["path_risk"])

    def test_run_predict_missing_scan_keeps_final_unavailable(self) -> None:
        result = run_predict(None, research_result=None, symbol="AVGO")

        self.assertEqual(result["final_bias"], "unavailable")
        self.assertEqual(result["primary_projection"]["status"], "unavailable")
        self.assertEqual(result["final_projection"]["status"], "unavailable")
        self.assertEqual(result["final_projection"]["final_bias"], "unavailable")


class RunPredictThreeSystemsAttachmentTests(unittest.TestCase):
    """Task 104 — verify run_predict attaches a fully-populated
    projection_three_systems block (or its degraded counterpart) so the
    Task 103 three-column UI can render real
    confidence_evaluator data."""

    _CONFIDENCE_KEYS = {
        "negative_system_confidence",
        "projection_system_confidence",
        "overall_confidence",
        "conflicts",
        "reliability_warnings",
    }

    def _stub_v2_raw_ready(self) -> dict:
        """Minimal v2_raw shape that exercises the populated branch
        without touching disk / network."""
        return {
            "symbol": "AVGO",
            "ready": True,
            "warnings": [],
            "step_status": {"primary": "success", "peer": "success",
                            "historical": "success", "final": "success"},
            "primary_analysis": {"ready": True, "direction": "偏多",
                                 "confidence": "medium"},
            "peer_adjustment": {"ready": True, "summary": "peers ok"},
            "historical_probability": {"ready": True, "summary": "hist ok"},
            "exclusion_result": {
                "excluded": False,
                "triggered_rule": None,
                "reasons": [],
                "feature_snapshot": {"a": 1, "b": 2},
                "peer_alignment": {"alignment": "neutral",
                                   "available_peer_count": 3},
            },
            "main_projection": {
                "predicted_top1": {"state": "震荡"},
                "state_probabilities": {"震荡": 0.4, "小涨": 0.3,
                                        "小跌": 0.2, "大涨": 0.05,
                                        "大跌": 0.05},
            },
            "final_decision": {
                "ready": True,
                "final_direction": "偏多",
                "final_confidence": "medium",
                "risk_level": "medium",
                "summary": "stub final summary",
                "layer_contributions": {"primary": "p", "peer": "pe",
                                         "historical": "h",
                                         "preflight": "pf"},
                "warnings": [],
            },
            "consistency": {"conflict_reasons": []},
        }

    def test_run_predict_attaches_projection_three_systems(self) -> None:
        import predict

        original_runner = getattr(predict, "_build_projection_three_systems_attachment")

        captured_symbols: list[str] = []

        def fake_runner(*, symbol: str, reason: str | None = None) -> dict:
            captured_symbols.append(symbol)
            from services.projection_three_systems_renderer import (
                build_projection_three_systems,
            )
            return build_projection_three_systems(
                projection_v2_raw=self._stub_v2_raw_ready(), symbol=symbol
            )

        predict._build_projection_three_systems_attachment = fake_runner
        try:
            result = run_predict(_scan(), research_result=None, symbol="AVGO")
        finally:
            predict._build_projection_three_systems_attachment = original_runner

        self.assertIn("projection_three_systems", result)
        three = result["projection_three_systems"]
        self.assertEqual(three["kind"], "projection_three_systems")
        self.assertEqual(three["symbol"], "AVGO")
        self.assertTrue(three["ready"])
        self.assertEqual(captured_symbols, ["AVGO"])

        evaluator = three["confidence_evaluator"]
        self.assertEqual(set(evaluator.keys()), self._CONFIDENCE_KEYS)

        for sub in ("negative_system_confidence",
                    "projection_system_confidence"):
            self.assertIn("level", evaluator[sub])
            self.assertIn("score", evaluator[sub])
            self.assertIn("reasoning", evaluator[sub])
            self.assertIn("risks", evaluator[sub])

        self.assertIn("level", evaluator["overall_confidence"])
        self.assertIn("score", evaluator["overall_confidence"])

        # Legacy fields untouched.
        self.assertEqual(result["final_bias"],
                         result["final_projection"]["final_bias"])
        self.assertEqual(result["primary_projection"]["status"], "computed")
        self.assertEqual(result["final_projection"]["status"], "computed")

    def test_run_predict_projection_three_systems_degrades_when_v2_raises(self) -> None:
        """When run_projection_v2 explodes, run_predict must still
        return its legacy answer and attach a degraded
        projection_three_systems block whose confidence_evaluator levels
        are all 'unknown'."""
        from services import projection_orchestrator_v2

        original_v2 = projection_orchestrator_v2.run_projection_v2

        def fake_v2(*_, **__):
            raise RuntimeError("simulated v2 outage")

        projection_orchestrator_v2.run_projection_v2 = fake_v2
        try:
            result = run_predict(_scan(), research_result=None, symbol="AVGO")
        finally:
            projection_orchestrator_v2.run_projection_v2 = original_v2

        # Legacy answer still intact.
        self.assertEqual(result["final_bias"],
                         result["final_projection"]["final_bias"])
        self.assertEqual(result["primary_projection"]["status"], "computed")
        self.assertEqual(result["final_projection"]["status"], "computed")

        # Degraded three-systems block attached with the canonical shape.
        self.assertIn("projection_three_systems", result)
        three = result["projection_three_systems"]
        self.assertEqual(three["kind"], "projection_three_systems")
        self.assertEqual(three["symbol"], "AVGO")
        self.assertFalse(three["ready"])

        evaluator = three["confidence_evaluator"]
        self.assertEqual(set(evaluator.keys()), self._CONFIDENCE_KEYS)
        self.assertEqual(evaluator["negative_system_confidence"]["level"],
                         "unknown")
        self.assertEqual(evaluator["projection_system_confidence"]["level"],
                         "unknown")
        self.assertEqual(evaluator["overall_confidence"]["level"], "unknown")
        self.assertIsNone(evaluator["negative_system_confidence"]["score"])
        self.assertIsNone(evaluator["projection_system_confidence"]["score"])
        self.assertIsNone(evaluator["overall_confidence"]["score"])

    def test_run_predict_missing_scan_attaches_degraded_three_systems(self) -> None:
        """Missing scan_result short-circuits the legacy path; the
        degraded three-systems block must still attach so the UI
        contract stays stable."""
        result = run_predict(None, research_result=None, symbol="AVGO")

        self.assertEqual(result["final_bias"], "unavailable")
        self.assertIn("projection_three_systems", result)
        three = result["projection_three_systems"]
        self.assertEqual(three["kind"], "projection_three_systems")
        self.assertEqual(three["symbol"], "AVGO")
        self.assertFalse(three["ready"])
        evaluator = three["confidence_evaluator"]
        self.assertEqual(set(evaluator.keys()), self._CONFIDENCE_KEYS)
        self.assertEqual(evaluator["overall_confidence"]["level"], "unknown")


class ProjectionThreeSystemsReentryGuardTests(unittest.TestCase):
    """Task 108 — verify the re-entry guard around
    `_build_projection_three_systems_attachment` prevents recursive
    `run_predict → run_projection_v2 → legacy orchestrator → run_predict`
    cycles caused by PR-I.

    The guard turns a nested attachment call into a single deterministic
    degraded payload instead of letting the chain re-fan-out into
    ~30 stack levels of CSV-load + match-table + scan + run_predict
    work per replay case.
    """

    _CONFIDENCE_KEYS = {
        "negative_system_confidence",
        "projection_system_confidence",
        "overall_confidence",
        "conflicts",
        "reliability_warnings",
    }

    def test_projection_three_systems_attachment_reentry_degrades_without_calling_v2(
        self,
    ) -> None:
        """When the guard is active (simulating mid-recursion state), the
        attachment helper must short-circuit to a degraded payload and
        must NOT call run_projection_v2."""
        import predict
        from services import projection_orchestrator_v2

        original_v2 = projection_orchestrator_v2.run_projection_v2
        v2_call_count = {"n": 0}

        def fake_v2(*_args, **_kwargs):
            v2_call_count["n"] += 1
            raise AssertionError("run_projection_v2 must not be called when re-entry guard is active")

        # Activate the guard manually and verify the attachment helper
        # short-circuits without touching v2.
        state = predict._projection_three_systems_attachment_state
        had_active_attr = hasattr(state, "active")
        prior_active = getattr(state, "active", None)

        projection_orchestrator_v2.run_projection_v2 = fake_v2
        try:
            state.active = True
            payload = predict._build_projection_three_systems_attachment(symbol="AVGO")
        finally:
            projection_orchestrator_v2.run_projection_v2 = original_v2
            if had_active_attr:
                state.active = prior_active
            else:
                # Restore clean state — no `active` attribute on a fresh thread-local.
                try:
                    delattr(state, "active")
                except AttributeError:
                    pass

        self.assertEqual(v2_call_count["n"], 0,
                         "run_projection_v2 should not be invoked under the guard")
        self.assertEqual(payload["kind"], "projection_three_systems")
        self.assertEqual(payload["symbol"], "AVGO")
        self.assertFalse(payload["ready"])
        evaluator = payload["confidence_evaluator"]
        self.assertEqual(set(evaluator.keys()), self._CONFIDENCE_KEYS)
        self.assertEqual(evaluator["projection_system_confidence"]["level"],
                         "unknown")
        self.assertEqual(evaluator["negative_system_confidence"]["level"],
                         "unknown")
        self.assertEqual(evaluator["overall_confidence"]["level"], "unknown")

        # Re-entry message must surface in reasoning so future debugging
        # can spot the guard firing.
        reasoning_text = " ".join(
            str(line) for line in evaluator["projection_system_confidence"]["reasoning"]
        )
        self.assertIn("re-entry", reasoning_text)

    def test_run_predict_attachment_does_not_recursively_reenter_v2(self) -> None:
        """Simulate the real recursion shape: a fake run_projection_v2
        re-enters predict.run_predict mid-call. Without the guard this
        would explode the call stack; with the guard the inner attachment
        degrades and the outer run_predict completes with v2 invoked
        exactly once.
        """
        import predict
        from services import projection_orchestrator_v2

        original_v2 = projection_orchestrator_v2.run_projection_v2
        call_count = {"v2": 0, "inner_run_predict": 0}

        def fake_v2(*_args, **_kwargs):
            call_count["v2"] += 1
            # Exactly one re-entrant run_predict, mirroring how the legacy
            # orchestrator's _build_predict_result invokes run_predict.
            inner = run_predict(_scan(), research_result=None, symbol="AVGO")
            call_count["inner_run_predict"] += 1
            # Hand the outer caller a tiny v2_raw so the renderer can run.
            inner_three = inner.get("projection_three_systems") or {}
            return {
                "kind": "projection_v2_raw",
                "symbol": "AVGO",
                "ready": False,
                "_inner_three_systems": inner_three,
            }

        projection_orchestrator_v2.run_projection_v2 = fake_v2
        try:
            outer = run_predict(_scan(), research_result=None, symbol="AVGO")
        finally:
            projection_orchestrator_v2.run_projection_v2 = original_v2

        # v2 invoked exactly once (outer attachment); inner run_predict
        # took the guard path and did NOT trigger another v2 call.
        self.assertEqual(call_count["v2"], 1,
                         f"run_projection_v2 should be called exactly once, got {call_count['v2']}")
        self.assertEqual(call_count["inner_run_predict"], 1,
                         "inner run_predict should have been invoked exactly once by the fake v2")

        # Outer run_predict still returns its legacy answer.
        self.assertEqual(outer["final_bias"],
                         outer["final_projection"]["final_bias"])
        self.assertEqual(outer["primary_projection"]["status"], "computed")
        self.assertEqual(outer["final_projection"]["status"], "computed")

        # Outer attachment carries the _inner_three_systems sentinel
        # under the build_projection_three_systems envelope (renderer is
        # a pure transform on whatever v2_raw it receives).
        outer_three = outer["projection_three_systems"]
        self.assertEqual(outer_three["kind"], "projection_three_systems")
        self.assertEqual(outer_three["symbol"], "AVGO")

    def test_guard_is_cleared_after_normal_attachment_run(self) -> None:
        """After a normal (non-re-entry) call returns, the guard must be
        cleared so subsequent calls in the same thread are not blocked."""
        import predict
        from services import projection_orchestrator_v2

        original_v2 = projection_orchestrator_v2.run_projection_v2

        def fake_v2(*_args, **_kwargs):
            return {"kind": "projection_v2_raw", "symbol": "AVGO", "ready": False}

        projection_orchestrator_v2.run_projection_v2 = fake_v2
        try:
            predict._build_projection_three_systems_attachment(symbol="AVGO")
            state_after = getattr(
                predict._projection_three_systems_attachment_state, "active", False
            )
            # Second call must not be blocked by leftover guard state.
            predict._build_projection_three_systems_attachment(symbol="AVGO")
        finally:
            projection_orchestrator_v2.run_projection_v2 = original_v2

        self.assertFalse(state_after, "guard must be cleared in finally block")


if __name__ == "__main__":
    unittest.main()
