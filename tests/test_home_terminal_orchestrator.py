from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.home_terminal_orchestrator import (
    build_home_terminal_orchestrator_result,
    compute_20d_features,
)


def _coded_df() -> pd.DataFrame:
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


def _peer_df(move: float) -> pd.DataFrame:
    return pd.DataFrame({
        "Date": ["2026-04-20"],
        "C_move": [move / 100.0],
    })


class HomeTerminalOrchestratorTests(unittest.TestCase):
    def test_compute_20d_features_returns_stable_shape(self) -> None:
        features = compute_20d_features(
            coded_df=_coded_df(),
            target_date_str="2026-04-20",
            target_row=_coded_df().iloc[-1],
            target_ctx={"ret3": 1.9, "ret5": 3.8},
            peer_loader=lambda symbol: {"NVDA": _peer_df(1.1), "SOXX": _peer_df(0.7), "QQQ": _peer_df(0.4)}.get(symbol),
        )

        self.assertEqual(features["symbol"], "AVGO")
        for key in ("pos20", "vol_ratio20", "upper_shadow_ratio", "lower_shadow_ratio", "ret1", "ret3", "ret5"):
            self.assertIn(key, features)

    def test_orchestrator_returns_unified_payload_and_writes_log(self) -> None:
        written: list[dict] = []

        def _log_writer(record: dict) -> str:
            written.append(record)
            return "pred-log-001"

        payload = build_home_terminal_orchestrator_result(
            scan_result={
                "historical_match_summary": {
                    "exact_match_count": 2,
                    "near_match_count": 3,
                    "dominant_historical_outcome": "up_bias",
                }
            },
            target_date_str="2026-04-20",
            coded_df=_coded_df(),
            target_row=_coded_df().iloc[-1],
            target_ctx={"ret3": 1.9, "ret5": 3.8},
            peer_loader=lambda symbol: {"NVDA": _peer_df(1.1), "SOXX": _peer_df(0.7), "QQQ": _peer_df(0.4)}.get(symbol),
            log_writer=_log_writer,
            persist_log=True,
        )

        self.assertEqual(payload["kind"], "home_terminal_orchestrator_result")
        self.assertEqual(payload["prediction_log_id"], "pred-log-001")
        self.assertIn("feature_payload", payload)
        self.assertIn("exclusion_result", payload)
        self.assertIn("main_projection", payload)
        self.assertIn("consistency", payload)
        self.assertIn("primary_choice", payload)
        self.assertIn("secondary_choice", payload)
        self.assertIn("least_likely", payload)
        self.assertEqual(len(written), 1)
        self.assertEqual(written[0]["prediction_for_date"], "2026-04-20")
        self.assertIn("predicted_top1", written[0])
        self.assertIn("predicted_top2", written[0])
        self.assertIn("consistency_flag", written[0])
        self.assertIn("consistency_score", written[0])

    def test_orchestrator_can_skip_log_write(self) -> None:
        payload = build_home_terminal_orchestrator_result(
            scan_result={},
            target_date_str="2026-04-20",
            coded_df=_coded_df(),
            target_row=_coded_df().iloc[-1],
            target_ctx={"ret3": 1.9, "ret5": 3.8},
            peer_loader=lambda symbol: None,
            persist_log=False,
        )

        self.assertIsNone(payload["prediction_log_id"])


if __name__ == "__main__":
    unittest.main()
