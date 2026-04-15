from __future__ import annotations

import runpy
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import matcher  # noqa: E402
import predict  # noqa: E402
import scanner  # noqa: E402
import stats_reporter  # noqa: E402


def fake_coded_df() -> pd.DataFrame:
    dates = pd.to_datetime(
        [
            "2026-04-06",
            "2026-04-07",
            "2026-04-08",
            "2026-04-09",
            "2026-04-13",
        ]
    )
    return pd.DataFrame(
        {
            "Date": dates,
            "Open": [100, 101, 102, 103, 104],
            "High": [101, 102, 103, 104, 105],
            "Low": [99, 100, 101, 102, 103],
            "Close": [100.5, 101.5, 102.5, 103.5, 104.5],
            "Volume": [1000, 1100, 1200, 1300, 1400],
            "PrevClose": [99.5, 100.5, 101.5, 102.5, 103.5],
            "MA20_Volume": [1000, 1000, 1000, 1000, 1000],
            "O_gap": [0.01, 0.01, 0.01, 0.01, 0.01],
            "H_up": [0.01, 0.01, 0.01, 0.01, 0.01],
            "L_down": [0.01, 0.01, 0.01, 0.01, 0.01],
            "C_move": [0.005, 0.005, 0.005, 0.005, 0.005],
            "V_ratio": [1.0, 1.1, 1.2, 1.3, 1.4],
            "Code": ["11111", "22222", "33333", "15142", pd.NA],
        }
    )


def fake_match_df(target_date: str) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "TargetDate": [target_date],
            "TargetCode": ["15142"],
            "MatchDate": ["2026-04-08"],
            "MatchCode": ["33333"],
            "MatchType": ["exact"],
            "NextDate": ["2026-04-09"],
            "NextOpen": [103.0],
            "NextHigh": [104.0],
            "NextLow": [102.0],
            "NextClose": [103.5],
            "NextVolume": [1300],
            "NextOpenChange": [0.01],
            "NextHighMove": [0.02],
            "NextLowMove": [-0.01],
            "NextCloseMove": [0.005],
            "VCodeDiff": [0],
        }
    )


def fake_summary(_target_date: str) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"MatchType": "exact", "SampleSize": 1, "DominantNextDayBias": "up_bias"},
            {"MatchType": "near", "SampleSize": 0, "DominantNextDayBias": "insufficient_sample"},
        ]
    )


def fake_scan(target_date_str: str, *args, **kwargs) -> dict:
    return {
        "symbol": "AVGO",
        "scan_phase": "daily",
        "scan_timestamp": target_date_str,
        "scan_bias": "bullish",
        "scan_confidence": "medium",
        "confirmation_state": "mixed",
        "notes": f"fake scan for {target_date_str}",
        "avgo_gap_state": "gap_up",
        "avgo_intraday_state": "high_go",
        "avgo_volume_state": "normal",
        "avgo_price_state": "bullish",
        "avgo_pattern_code": "15142",
        "relative_strength_5d_summary": {},
        "relative_strength_same_day_summary": {},
        "historical_match_summary": {
            "exact_match_count": 1,
            "near_match_count": 0,
            "top_context_score": None,
            "dominant_historical_outcome": "up_bias",
        },
    }


def fake_predict(scan_result: dict, research_result: dict | None, symbol: str = "AVGO") -> dict:
    return {
        "symbol": symbol,
        "final_bias": "bullish",
        "final_confidence": "medium",
        "open_tendency": "up",
        "close_tendency": "up",
        "prediction_summary": "fake predict",
        "supporting_factors": [],
        "conflicting_factors": [],
    }


matcher.load_coded_avgo = fake_coded_df
matcher.build_next_day_match_table = lambda coded_df, target_date: fake_match_df(target_date)
matcher.build_near_match_table = lambda coded_df, target_date: fake_match_df(target_date)
matcher.save_match_results = lambda *args, **kwargs: None
matcher.save_near_match_results = lambda *args, **kwargs: None
stats_reporter.build_stats_summary = fake_summary
stats_reporter.save_stats_summary = lambda *args, **kwargs: None
scanner.run_scan = fake_scan
predict.run_predict = fake_predict

runpy.run_path(str(ROOT / "app.py"), run_name="__main__")
