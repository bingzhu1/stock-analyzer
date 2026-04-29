"""Task 107 — verify build_audit_case flattens projection_snapshot.feature_payload.

Step 3A diagnosed that the audit case dropped pos20 / vol_ratio20 / etc. silently
even though projection_snapshot.feature_payload had them. Step 3B added the
flattening; these tests lock the contract so future refactors don't regress it.

Pure additive coverage — no changes to existing audit case keys are tested here.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.three_system_replay_audit import build_audit_case


def _three_systems_stub() -> dict:
    """Minimal three_systems envelope; the feature-flattening tests only care
    about the top-level audit case fields, not the system blocks."""
    return {
        "negative_system": {"excluded_states": [], "strength": "none", "evidence": []},
        "record_02_projection_system": {
            "five_state_projection": {},
            "historical_sample_summary": "",
            "peer_market_confirmation": "",
            "risk_notes": [],
        },
        "confidence_evaluator": {
            "negative_system_confidence": {"level": "unknown"},
            "projection_system_confidence": {"level": "unknown"},
            "overall_confidence": {"level": "unknown"},
            "conflicts": [],
            "reliability_warnings": [],
        },
    }


def _replay_stub_with_features(features: dict | None) -> dict:
    snapshot: dict = {
        "final_decision": {"final_direction": "偏多", "final_confidence": "medium"},
        "main_projection": {"predicted_top1": {"state": "震荡"}},
        "exclusion_result": {"excluded": False, "triggered_rule": None,
                             "reasons": [], "feature_snapshot": features or {}},
        "historical_probability": {"sample_quality": "limited"},
        "peer_adjustment": {"confirmation_level": "confirmed"},
    }
    if features is not None:
        snapshot["feature_payload"] = features
    return {
        "kind": "historical_replay_result",
        "symbol": "AVGO",
        "as_of_date": "2026-04-23",
        "prediction_for_date": "2026-04-24",
        "ready": True,
        "projection_snapshot": snapshot,
        "actual_outcome": {"actual_close_change": 0.4, "open_label": "平开",
                           "close_label": "收涨", "path_label": "平开走高"},
        "review": {"direction_correct": True, "error_layer": "n/a",
                   "error_category": "correct", "rule_candidates": []},
        "warnings": [],
    }


class BuildAuditCaseFeatureFlatteningTests(unittest.TestCase):
    """Task 107 — verify Step 3B feature flattening contract."""

    EXPECTED_FEATURE_KEYS = (
        "pos20", "vol_ratio20", "upper_shadow_ratio", "lower_shadow_ratio",
        "ret1", "ret3", "ret5", "ret10",
        "nvda_ret1", "soxx_ret1", "qqq_ret1",
    )

    def test_build_audit_case_includes_feature_payload_fields(self) -> None:
        replay = _replay_stub_with_features({
            "pos20": 93.3,
            "vol_ratio20": 1.0,
            "upper_shadow_ratio": 0.6012,
            "lower_shadow_ratio": 0.1859,
            "ret1": -0.64,
            "ret3": 5.08,
            "ret5": 5.39,
            "ret10": 18.32,
            "nvda_ret1": 0.45,
            "soxx_ret1": -0.12,
            "qqq_ret1": 0.20,
        })
        case = build_audit_case(replay_result=replay,
                                three_systems=_three_systems_stub())

        self.assertEqual(case["pos20"], 93.3)
        self.assertEqual(case["vol_ratio20"], 1.0)
        self.assertEqual(case["upper_shadow_ratio"], 0.6012)
        self.assertEqual(case["lower_shadow_ratio"], 0.1859)
        self.assertEqual(case["ret1"], -0.64)
        self.assertEqual(case["ret3"], 5.08)
        self.assertEqual(case["ret5"], 5.39)
        self.assertEqual(case["ret10"], 18.32)
        self.assertEqual(case["nvda_ret1"], 0.45)
        self.assertEqual(case["soxx_ret1"], -0.12)
        self.assertEqual(case["qqq_ret1"], 0.20)

        # Sanity: the surrounding audit-case shape was not disturbed.
        self.assertEqual(case["as_of_date"], "2026-04-23")
        self.assertEqual(case["prediction_for_date"], "2026-04-24")
        self.assertTrue(case["ready"])
        self.assertEqual(case["five_state_top1"], "震荡")

    def test_build_audit_case_missing_feature_payload_degrades_to_none(self) -> None:
        # No projection_snapshot at all → all new fields must exist and be None,
        # no exception raised.
        replay = {
            "kind": "historical_replay_result",
            "symbol": "AVGO",
            "as_of_date": "2026-04-23",
            "prediction_for_date": "2026-04-24",
            "ready": False,
            "warnings": ["projection_snapshot missing"],
            "actual_outcome": {},
            "review": {},
        }
        case = build_audit_case(replay_result=replay,
                                three_systems=_three_systems_stub())
        for key in self.EXPECTED_FEATURE_KEYS:
            self.assertIn(key, case, f"audit case must include key {key} even when degraded")
            self.assertIsNone(case[key], f"{key} should be None when feature_payload is missing")

    def test_build_audit_case_partial_feature_payload(self) -> None:
        # Only some keys present — the missing ones must come back as None,
        # and the present ones must come through as floats.
        replay = _replay_stub_with_features({
            "pos20": 50.5,
            "vol_ratio20": 1.2,
            # everything else absent
        })
        case = build_audit_case(replay_result=replay,
                                three_systems=_three_systems_stub())

        self.assertEqual(case["pos20"], 50.5)
        self.assertEqual(case["vol_ratio20"], 1.2)
        for key in ("upper_shadow_ratio", "lower_shadow_ratio",
                    "ret1", "ret3", "ret5", "ret10",
                    "nvda_ret1", "soxx_ret1", "qqq_ret1"):
            self.assertIsNone(case[key], f"{key} should be None when missing from payload")

    def test_build_audit_case_handles_malformed_feature_values(self) -> None:
        # String / unparseable values must not raise — _safe_float returns None.
        replay = _replay_stub_with_features({
            "pos20": "not-a-number",
            "vol_ratio20": None,
            "upper_shadow_ratio": "",
            "ret1": "0.5",        # parseable string → 0.5
            "ret3": 3.14,
        })
        case = build_audit_case(replay_result=replay,
                                three_systems=_three_systems_stub())
        self.assertIsNone(case["pos20"])
        self.assertIsNone(case["vol_ratio20"])
        self.assertIsNone(case["upper_shadow_ratio"])
        self.assertEqual(case["ret1"], 0.5)
        self.assertEqual(case["ret3"], 3.14)


if __name__ == "__main__":
    unittest.main()
