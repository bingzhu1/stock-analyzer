from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.peer_adjustment import build_peer_adjustment


def _primary(direction: str = "偏多", confidence: str = "medium", ready: bool = True) -> dict:
    return {
        "kind": "primary_20day_analysis",
        "symbol": "AVGO",
        "ready": ready,
        "direction": direction,
        "confidence": confidence,
        "summary": f"主分析方向{direction}。",
        "basis": ["主分析依据。"],
    }


def _snapshot(
    *,
    confirmation_state: str = "confirmed",
    rs_5d: dict | None = None,
    rs_day: dict | None = None,
) -> dict:
    return {
        "confirmation_state": confirmation_state,
        "relative_strength_5d_summary": rs_5d if rs_5d is not None else {
            "vs_nvda": "stronger",
            "vs_soxx": "stronger",
            "vs_qqq": "neutral",
        },
        "relative_strength_same_day_summary": rs_day if rs_day is not None else {
            "vs_nvda": "stronger",
            "vs_soxx": "neutral",
            "vs_qqq": "stronger",
        },
    }


class PeerAdjustmentTests(unittest.TestCase):
    def test_bullish_peers_reinforce_bullish_primary(self) -> None:
        result = build_peer_adjustment(
            primary_analysis=_primary("偏多", "medium"),
            peer_snapshot=_snapshot(),
        )

        self.assertEqual(result["kind"], "peer_adjustment")
        self.assertTrue(result["ready"])
        self.assertEqual(result["confirmation_level"], "confirmed")
        self.assertEqual(result["adjustment"], "reinforce_bullish")
        self.assertEqual(result["adjusted_direction"], "偏多")
        self.assertEqual(result["adjusted_confidence"], "high")
        self.assertIn("peers 支持", result["summary"])
        self.assertFalse(result["warnings"])
        for key in ("confirmation_state", "relative_strength_5d_summary", "relative_strength_same_day_summary"):
            self.assertIn(key, result["peer_snapshot"])

    def test_bearish_peers_reinforce_bearish_primary(self) -> None:
        result = build_peer_adjustment(
            primary_analysis=_primary("偏空", "medium"),
            peer_snapshot=_snapshot(
                rs_5d={"vs_nvda": "weaker", "vs_soxx": "weaker", "vs_qqq": "neutral"},
                rs_day={"vs_nvda": "weaker", "vs_soxx": "neutral", "vs_qqq": "weaker"},
            ),
        )

        self.assertTrue(result["ready"])
        self.assertEqual(result["confirmation_level"], "confirmed")
        self.assertEqual(result["adjustment"], "reinforce_bearish")
        self.assertEqual(result["adjusted_direction"], "偏空")
        self.assertEqual(result["adjusted_confidence"], "high")

    def test_mixed_or_opposing_peers_downgrade_directional_primary(self) -> None:
        result = build_peer_adjustment(
            primary_analysis=_primary("偏多", "medium"),
            peer_snapshot=_snapshot(
                confirmation_state="diverging",
                rs_5d={"vs_nvda": "weaker", "vs_soxx": "weaker", "vs_qqq": "neutral"},
                rs_day={"vs_nvda": "weaker", "vs_soxx": "neutral", "vs_qqq": "weaker"},
            ),
        )

        self.assertTrue(result["ready"])
        self.assertEqual(result["confirmation_level"], "weak")
        self.assertEqual(result["adjustment"], "downgrade")
        self.assertEqual(result["adjusted_direction"], "偏多")
        self.assertEqual(result["adjusted_confidence"], "low")
        self.assertIn("下调置信度", result["summary"])

    def test_all_neutral_peers_do_not_downgrade_bullish_primary(self) -> None:
        neutral = {"vs_nvda": "neutral", "vs_soxx": "neutral", "vs_qqq": "neutral"}

        result = build_peer_adjustment(
            primary_analysis=_primary("偏多", "medium"),
            peer_snapshot=_snapshot(
                confirmation_state="mixed",
                rs_5d=neutral,
                rs_day=neutral,
            ),
        )

        self.assertTrue(result["ready"])
        self.assertEqual(result["adjustment"], "no_change")
        self.assertEqual(result["adjusted_direction"], "偏多")
        self.assertEqual(result["adjusted_confidence"], "medium")

    def test_all_neutral_peers_do_not_downgrade_bearish_primary(self) -> None:
        neutral = {"vs_nvda": "neutral", "vs_soxx": "neutral", "vs_qqq": "neutral"}

        result = build_peer_adjustment(
            primary_analysis=_primary("偏空", "medium"),
            peer_snapshot=_snapshot(
                confirmation_state="mixed",
                rs_5d=neutral,
                rs_day=neutral,
            ),
        )

        self.assertTrue(result["ready"])
        self.assertEqual(result["adjustment"], "no_change")
        self.assertEqual(result["adjusted_direction"], "偏空")
        self.assertEqual(result["adjusted_confidence"], "medium")

    def test_missing_peer_snapshot_degrades(self) -> None:
        result = build_peer_adjustment(
            primary_analysis=_primary("偏多", "medium"),
            peer_snapshot=None,
        )

        self.assertFalse(result["ready"])
        self.assertEqual(result["confirmation_level"], "missing")
        self.assertEqual(result["adjustment"], "missing")
        self.assertEqual(result["adjusted_direction"], "偏多")
        self.assertEqual(result["adjusted_confidence"], "medium")
        self.assertTrue(result["warnings"])
        self.assertIn("未获 peers 确认", result["summary"])

    def test_confirmation_state_mixed_with_all_unavailable_rs_degrades(self) -> None:
        unavailable = {"vs_nvda": "unavailable", "vs_soxx": "unavailable", "vs_qqq": "unavailable"}

        result = build_peer_adjustment(
            primary_analysis=_primary("偏多", "medium"),
            peer_snapshot=_snapshot(
                confirmation_state="mixed",
                rs_5d=unavailable,
                rs_day=unavailable,
            ),
        )

        self.assertFalse(result["ready"])
        self.assertEqual(result["confirmation_level"], "missing")
        self.assertEqual(result["adjustment"], "missing")
        self.assertTrue(result["warnings"])
        self.assertIn("未获 peers 确认", result["summary"])

    def test_primary_missing_degrades_without_fake_adjustment(self) -> None:
        result = build_peer_adjustment(
            primary_analysis=_primary("unknown", "unknown", ready=False),
            peer_snapshot=_snapshot(),
        )

        self.assertFalse(result["ready"])
        self.assertEqual(result["confirmation_level"], "unknown")
        self.assertEqual(result["adjustment"], "unknown")
        self.assertEqual(result["adjusted_direction"], "unknown")
        self.assertEqual(result["adjusted_confidence"], "unknown")
        self.assertTrue(result["warnings"])
        self.assertIn("主分析不可用", result["summary"])

    def test_neutral_primary_is_not_overridden_by_peers(self) -> None:
        result = build_peer_adjustment(
            primary_analysis=_primary("中性", "low"),
            peer_snapshot=_snapshot(),
        )

        self.assertTrue(result["ready"])
        self.assertEqual(result["adjustment"], "no_change")
        self.assertEqual(result["adjusted_direction"], "中性")
        self.assertEqual(result["adjusted_confidence"], "low")


if __name__ == "__main__":
    unittest.main()
