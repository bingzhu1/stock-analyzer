"""Tests for services/protection_layer_diagnostics.py (Step 2G-8A.1)."""
from __future__ import annotations

import ast
import sys
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.protection_layer_diagnostics import (  # noqa: E402
    GUARD_HOLDOUT_STABILITY,
    GUARD_NET_BENEFIT,
    SCHEMA_VERSION,
    build_protection_layer_diagnostics,
    build_protection_layer_diagnostics_from_dashboard,
)


# ── fixtures ────────────────────────────────────────────────────────────

def _dashboard_summary(*, holdout_status: str = "FAIL",
                       net_benefit: float | None = 0.0219) -> dict:
    """Mirror services.anti_false_exclusion_dashboard
    .summarize_anti_false_exclusion_dashboard output shape."""
    return {
        "status": "ok",
        "symbol": "AVGO",
        "soft_metadata_summary": {
            "r4_overextension": {
                "samples": 36, "paired": 34,
                "correct_when_triggered": 11, "wrong_when_triggered": 23,
                "accuracy": 0.324,
                "false_exclusion_rate": 0.3235,
                "net_benefit": net_benefit,
                "bias_gap": 0.676,
                "holdout_status": holdout_status,
            },
            "bullish_high_pos20_residual": {
                "samples": 47, "paired": 47,
                "correct_when_triggered": 23, "wrong_when_triggered": 24,
                "accuracy": 0.489,
                "false_exclusion_rate": 0.489,
                "net_benefit": -0.001,
                "bias_gap": 0.511,
                "holdout_status": holdout_status,
            },
        },
        "warnings": [],
    }


def _r4_signal(*, holdout_status: str = "FAIL",
               net_benefit: float | None = 0.0219) -> dict:
    return {
        "name": "r4_overextension",
        "display_label": "高位跑赢同行后的偏多过热",
        "severity": "medium",
        "holdout_status": holdout_status,
        "historical_metrics_in_sample": {
            "samples": 36, "paired": 34,
            "accuracy": 0.324, "bias_gap": 0.676,
            "false_exclusion_rate": 0.3235,
            "net_benefit": net_benefit,
        },
    }


def _soft_metadata(*, signals: list[dict] | None = None,
                   warnings: list[str] | None = None) -> dict:
    sigs = signals if signals is not None else [_r4_signal()]
    return {
        "schema_version": "soft_metadata.v1",
        "signals": sigs,
        "summary": {
            "has_overextension_signal": bool(sigs),
            "max_severity": "medium" if sigs else "none",
            "hard_exclusion_allowed": False,
            "signal_count": len(sigs),
            "primary_signal": sigs[0]["name"] if sigs else None,
            "warnings": list(warnings or []),
        },
    }


# ── 1. output schema ────────────────────────────────────────────────────

class OutputSchemaTests(unittest.TestCase):
    def test_top_level_required_keys_present(self) -> None:
        out = build_protection_layer_diagnostics(_dashboard_summary())
        for key in (
            "schema_version",
            "diagnostic_connected",
            "hard_gate_connected",
            "required_field_connected",
            "protection_layer_connected_for_gate",
            "guards",
            "summary",
            "warnings",
        ):
            self.assertIn(key, out)

    def test_schema_version_is_v1(self) -> None:
        out = build_protection_layer_diagnostics(_dashboard_summary())
        self.assertEqual(out["schema_version"], SCHEMA_VERSION)
        self.assertEqual(SCHEMA_VERSION, "protection_layer_diagnostics.v1")

    def test_summary_required_keys_present(self) -> None:
        out = build_protection_layer_diagnostics(_dashboard_summary())
        for key in (
            "hard_upgrade_blocked",
            "display_only",
            "blocking_guard_count",
            "required_next_step",
        ):
            self.assertIn(key, out["summary"])
        self.assertEqual(
            out["summary"]["required_next_step"],
            "narrower_candidate_research",
        )

    def test_each_guard_has_required_fields(self) -> None:
        out = build_protection_layer_diagnostics(_dashboard_summary())
        self.assertGreaterEqual(len(out["guards"]), 1)
        for g in out["guards"]:
            for key in ("name", "status", "reason", "evidence", "message"):
                self.assertIn(key, g)
            self.assertEqual(g["status"], "blocking")


# ── 2. holdout_stability_guard ──────────────────────────────────────────

class HoldoutStabilityGuardTests(unittest.TestCase):
    def test_holdout_FAIL_triggers_guard(self) -> None:
        out = build_protection_layer_diagnostics(
            _dashboard_summary(holdout_status="FAIL"),
        )
        names = [g["name"] for g in out["guards"]]
        self.assertIn(GUARD_HOLDOUT_STABILITY, names)
        guard = next(g for g in out["guards"]
                     if g["name"] == GUARD_HOLDOUT_STABILITY)
        self.assertEqual(guard["reason"], "holdout_status_FAIL")
        self.assertEqual(guard["evidence"]["holdout_status"], "FAIL")

    def test_holdout_PASS_does_not_trigger_guard(self) -> None:
        out = build_protection_layer_diagnostics(
            _dashboard_summary(holdout_status="PASS", net_benefit=0.10),
        )
        names = [g["name"] for g in out["guards"]]
        self.assertNotIn(GUARD_HOLDOUT_STABILITY, names)

    def test_holdout_unknown_does_not_trigger_guard(self) -> None:
        # Defensive: only the literal "FAIL" string should trigger the
        # guard. UNKNOWN / None / "" must NOT (otherwise we'd surface
        # bogus blocking when the metric is missing — that case is
        # handled separately via missing_metrics warning).
        for status in ("UNKNOWN", "", None):
            out = build_protection_layer_diagnostics(
                _dashboard_summary(
                    holdout_status=status, net_benefit=0.10,
                ),
            )
            names = [g["name"] for g in out["guards"]]
            self.assertNotIn(GUARD_HOLDOUT_STABILITY, names)

    def test_holdout_FAIL_via_soft_metadata_signal(self) -> None:
        sm = _soft_metadata(signals=[_r4_signal(
            holdout_status="FAIL", net_benefit=0.10,
        )])
        out = build_protection_layer_diagnostics(soft_metadata=sm)
        names = [g["name"] for g in out["guards"]]
        self.assertIn(GUARD_HOLDOUT_STABILITY, names)


# ── 3. net_benefit_guard ────────────────────────────────────────────────

class NetBenefitGuardTests(unittest.TestCase):
    def test_nb_below_gate_triggers_guard(self) -> None:
        out = build_protection_layer_diagnostics(
            _dashboard_summary(holdout_status="PASS", net_benefit=0.0219),
        )
        names = [g["name"] for g in out["guards"]]
        self.assertIn(GUARD_NET_BENEFIT, names)
        guard = next(g for g in out["guards"]
                     if g["name"] == GUARD_NET_BENEFIT)
        self.assertEqual(guard["reason"], "net_benefit_below_gate")
        self.assertAlmostEqual(guard["evidence"]["net_benefit"], 0.0219)
        self.assertEqual(guard["evidence"]["threshold"], 0.05)

    def test_nb_at_gate_does_not_trigger_guard(self) -> None:
        out = build_protection_layer_diagnostics(
            _dashboard_summary(holdout_status="PASS", net_benefit=0.05),
        )
        names = [g["name"] for g in out["guards"]]
        self.assertNotIn(GUARD_NET_BENEFIT, names)

    def test_nb_above_gate_does_not_trigger_guard(self) -> None:
        out = build_protection_layer_diagnostics(
            _dashboard_summary(holdout_status="PASS", net_benefit=0.20),
        )
        names = [g["name"] for g in out["guards"]]
        self.assertNotIn(GUARD_NET_BENEFIT, names)

    def test_nb_below_gate_via_soft_metadata_signal(self) -> None:
        sm = _soft_metadata(signals=[_r4_signal(
            holdout_status="PASS", net_benefit=0.01,
        )])
        out = build_protection_layer_diagnostics(soft_metadata=sm)
        names = [g["name"] for g in out["guards"]]
        self.assertIn(GUARD_NET_BENEFIT, names)


# ── 4. missing-metrics graceful path ────────────────────────────────────

class MissingMetricsTests(unittest.TestCase):
    def test_no_inputs_returns_empty_guard_list_with_warning(self) -> None:
        out = build_protection_layer_diagnostics()
        self.assertEqual(out["guards"], [])
        self.assertIn("missing_metrics", out["warnings"])

    def test_empty_dashboard_summary_warns(self) -> None:
        out = build_protection_layer_diagnostics({})
        self.assertEqual(out["guards"], [])
        self.assertIn("missing_metrics", out["warnings"])

    def test_dashboard_with_no_r4_warns(self) -> None:
        out = build_protection_layer_diagnostics({
            "soft_metadata_summary": {"r4_overextension": None},
            "warnings": [],
        })
        self.assertEqual(out["guards"], [])
        self.assertIn("missing_metrics", out["warnings"])

    def test_unknown_candidate_payload_graceful(self) -> None:
        # Garbage shapes must not raise and must not falsely emit guards.
        for junk in (
            "string",
            123,
            ["list", "of", "things"],
            {"foo": "bar"},
            {"r4_overextension": "not_a_dict"},
        ):
            out = build_protection_layer_diagnostics(junk)  # type: ignore[arg-type]
            self.assertEqual(out["guards"], [])
            self.assertIn("missing_metrics", out["warnings"])

    def test_connection_flags_locked_in_missing_path(self) -> None:
        out = build_protection_layer_diagnostics()
        self.assertTrue(out["diagnostic_connected"])
        self.assertFalse(out["hard_gate_connected"])
        self.assertFalse(out["required_field_connected"])
        self.assertFalse(out["protection_layer_connected_for_gate"])
        self.assertTrue(out["summary"]["hard_upgrade_blocked"])


# ── 5. spec invariants — connection flags + summary lock ───────────────

class ConnectionFlagInvariantTests(unittest.TestCase):
    SCENARIOS = [
        # (label, dashboard_summary)
        ("default", _dashboard_summary()),
        ("holdout_pass", _dashboard_summary(holdout_status="PASS")),
        ("nb_above_gate", _dashboard_summary(net_benefit=0.10)),
        ("both_pass", _dashboard_summary(
            holdout_status="PASS", net_benefit=0.10,
        )),
        ("empty", {}),
        ("empty_with_partial_data", {
            "soft_metadata_summary": {
                "r4_overextension": {"holdout_status": "PASS"},
            },
        }),
    ]

    def test_diagnostic_connected_always_true(self) -> None:
        for label, dash in self.SCENARIOS:
            with self.subTest(scenario=label):
                out = build_protection_layer_diagnostics(dash)
                self.assertTrue(out["diagnostic_connected"])

    def test_hard_gate_connected_always_false(self) -> None:
        for label, dash in self.SCENARIOS:
            with self.subTest(scenario=label):
                out = build_protection_layer_diagnostics(dash)
                self.assertFalse(out["hard_gate_connected"])

    def test_required_field_connected_always_false(self) -> None:
        for label, dash in self.SCENARIOS:
            with self.subTest(scenario=label):
                out = build_protection_layer_diagnostics(dash)
                self.assertFalse(out["required_field_connected"])

    def test_protection_layer_connected_for_gate_always_false(self) -> None:
        for label, dash in self.SCENARIOS:
            with self.subTest(scenario=label):
                out = build_protection_layer_diagnostics(dash)
                self.assertFalse(out["protection_layer_connected_for_gate"])


class SummaryInvariantTests(unittest.TestCase):
    def test_hard_upgrade_blocked_always_true(self) -> None:
        for dash in (
            _dashboard_summary(),
            _dashboard_summary(holdout_status="PASS", net_benefit=0.10),
            {},
        ):
            out = build_protection_layer_diagnostics(dash)
            self.assertTrue(out["summary"]["hard_upgrade_blocked"])

    def test_display_only_always_true(self) -> None:
        for dash in (
            _dashboard_summary(),
            _dashboard_summary(holdout_status="PASS", net_benefit=0.10),
            {},
        ):
            out = build_protection_layer_diagnostics(dash)
            self.assertTrue(out["summary"]["display_only"])

    def test_blocking_guard_count_matches_guard_list(self) -> None:
        out = build_protection_layer_diagnostics(_dashboard_summary())
        self.assertEqual(
            out["summary"]["blocking_guard_count"],
            sum(1 for g in out["guards"] if g["status"] == "blocking"),
        )

    def test_required_next_step_locked(self) -> None:
        out = build_protection_layer_diagnostics(_dashboard_summary())
        self.assertEqual(
            out["summary"]["required_next_step"],
            "narrower_candidate_research",
        )


# ── 6. input not mutated ────────────────────────────────────────────────

class InputImmutabilityTests(unittest.TestCase):
    def test_dashboard_summary_not_mutated(self) -> None:
        dash = _dashboard_summary()
        snap = deepcopy(dash)
        build_protection_layer_diagnostics(dash)
        self.assertEqual(dash, snap)

    def test_soft_metadata_not_mutated(self) -> None:
        sm = _soft_metadata()
        snap = deepcopy(sm)
        build_protection_layer_diagnostics(soft_metadata=sm)
        self.assertEqual(sm, snap)

    def test_both_inputs_not_mutated(self) -> None:
        dash = _dashboard_summary()
        sm = _soft_metadata()
        dsnap = deepcopy(dash)
        msnap = deepcopy(sm)
        build_protection_layer_diagnostics(dash, soft_metadata=sm)
        self.assertEqual(dash, dsnap)
        self.assertEqual(sm, msnap)


# ── 7. from_dashboard convenience wrapper ──────────────────────────────

class FromDashboardTests(unittest.TestCase):
    def test_extracts_holdout_and_net_benefit(self) -> None:
        out = build_protection_layer_diagnostics_from_dashboard(
            _dashboard_summary(),
        )
        self.assertEqual(out["schema_version"], SCHEMA_VERSION)
        names = [g["name"] for g in out["guards"]]
        self.assertIn(GUARD_HOLDOUT_STABILITY, names)
        self.assertIn(GUARD_NET_BENEFIT, names)

    def test_pass_through_path_no_guards(self) -> None:
        out = build_protection_layer_diagnostics_from_dashboard(
            _dashboard_summary(holdout_status="PASS", net_benefit=0.10),
        )
        self.assertEqual(out["guards"], [])
        self.assertTrue(out["summary"]["hard_upgrade_blocked"])

    def test_garbage_input_graceful(self) -> None:
        for junk in ("not a dict", 123, None, []):
            out = build_protection_layer_diagnostics_from_dashboard(junk)  # type: ignore[arg-type]
            self.assertEqual(out["schema_version"], SCHEMA_VERSION)
            self.assertEqual(out["guards"], [])


# ── 8. final_test_range_refusal warning passthrough ────────────────────

class FinalTestRangeWarningTests(unittest.TestCase):
    def test_passes_through_from_dashboard_warnings(self) -> None:
        dash = _dashboard_summary()
        dash["warnings"] = ["final_test_range_refusal"]
        out = build_protection_layer_diagnostics(dash)
        self.assertIn("final_test_range_refusal", out["warnings"])

    def test_passes_through_from_soft_metadata_summary_warnings(self) -> None:
        sm = _soft_metadata(warnings=["final_test_range_refusal"])
        out = build_protection_layer_diagnostics(soft_metadata=sm)
        self.assertIn("final_test_range_refusal", out["warnings"])

    def test_warning_list_deduplicates(self) -> None:
        dash = _dashboard_summary()
        dash["warnings"] = ["final_test_range_refusal"]
        sm = _soft_metadata(warnings=["final_test_range_refusal"])
        out = build_protection_layer_diagnostics(dash, soft_metadata=sm)
        count = sum(
            1 for w in out["warnings"] if w == "final_test_range_refusal"
        )
        self.assertEqual(count, 1)


# ── 9. dashboard + soft_metadata cross-sourcing ────────────────────────

class CrossSourceTests(unittest.TestCase):
    def test_dashboard_metrics_take_precedence_when_present(self) -> None:
        dash = _dashboard_summary(holdout_status="PASS", net_benefit=0.10)
        # Soft-metadata says FAIL / 0.01, but dashboard says PASS / 0.10
        sm = _soft_metadata(signals=[_r4_signal(
            holdout_status="FAIL", net_benefit=0.01,
        )])
        out = build_protection_layer_diagnostics(dash, soft_metadata=sm)
        self.assertEqual(out["guards"], [])

    def test_soft_metadata_fills_when_dashboard_missing_field(self) -> None:
        # Dashboard exists but R4 has no net_benefit field.
        dash = {
            "soft_metadata_summary": {
                "r4_overextension": {"holdout_status": "PASS"},
            },
        }
        sm = _soft_metadata(signals=[_r4_signal(
            holdout_status="PASS", net_benefit=0.01,
        )])
        out = build_protection_layer_diagnostics(dash, soft_metadata=sm)
        names = [g["name"] for g in out["guards"]]
        self.assertIn(GUARD_NET_BENEFIT, names)


# ── 10. isolation: no DB / network / trading imports ───────────────────

class IsolationTests(unittest.TestCase):
    def test_module_does_not_import_forbidden(self) -> None:
        import services.protection_layer_diagnostics as mod
        tree = ast.parse(Path(mod.__file__).read_text(encoding="utf-8"))
        forbidden_modules = {
            "yfinance", "requests",
            "longbridge", "broker", "paper_trade",
            "sqlite3",
            "services.prediction_store",
            "services.confidence_engine",
            "services.contradiction_engine",
            "services.risk_model",
            "services.soft_metadata_simulator",
            "services.anti_false_exclusion_dashboard",
            "confidence_engine", "contradiction_engine", "risk_model",
            "predict", "scanner",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn(alias.name, forbidden_modules)
            elif isinstance(node, ast.ImportFrom):
                self.assertNotIn(node.module, forbidden_modules)


# ── 11. forbidden-copy lockdown (sidecar messages only) ────────────────

class ForbiddenCopyTests(unittest.TestCase):
    """The 19-token AFX forbidden list is inherited by this sidecar's
    messages (Step 2G-8A §9 / checkpoint §9.4). Even though there is no
    markdown renderer in this helper (renderer is Step 2G-8A.2), guard
    ``message`` strings still must not contain forbidden copy."""

    FORBIDDEN_TOKENS: tuple[str, ...] = (
        "禁止交易", "强制否定", "必须不做",
        "hard exclusion", "forced exclusion",
        "自动拦截", "no_trade",
        "卖出信号", "做空信号", "看空信号",
        "否决主推演", "推翻主推演",
        "强制平仓", "force close",
        "阻止下单", "block order",
        " hard ", " forced ", "排除",
    )

    def _all_messages(self, out: dict) -> list[str]:
        msgs: list[str] = []
        for g in out.get("guards", []):
            m = g.get("message")
            if isinstance(m, str):
                msgs.append(m)
        return msgs

    def test_default_path_messages_clean(self) -> None:
        out = build_protection_layer_diagnostics(_dashboard_summary())
        for msg in self._all_messages(out):
            for tok in self.FORBIDDEN_TOKENS:
                self.assertNotIn(tok, msg)

    def test_soft_metadata_path_messages_clean(self) -> None:
        out = build_protection_layer_diagnostics(
            soft_metadata=_soft_metadata(),
        )
        for msg in self._all_messages(out):
            for tok in self.FORBIDDEN_TOKENS:
                self.assertNotIn(tok, msg)


if __name__ == "__main__":
    unittest.main()
