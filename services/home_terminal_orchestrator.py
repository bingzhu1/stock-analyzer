"""Unified home-terminal orchestration for the AVGO homepage MVP.

This service wires together:
1. compute_20d_features(...)
2. run_exclusion_layer(...)
3. build_main_projection_layer(...)
4. build_consistency_layer(...)
5. write_prediction_log(...)

It returns one stable payload that UI consumers can render directly.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

import pandas as pd

from scanner import load_peer_coded
from services.consistency_layer import build_consistency_layer
from services.exclusion_layer import run_exclusion_layer
from services.log_store import write_prediction_log
from services.main_projection_layer import build_main_projection_layer
from services.projection_chain_contract import (
    as_dict,
    build_feature_payload_from_recent_window,
    build_prediction_log_record,
    build_unified_projection_payload,
    safe_float,
)


_PEER_SYMBOLS = ("NVDA", "SOXX", "QQQ")


def _window_df(coded_df: pd.DataFrame, target_date_str: str, window: int = 20) -> pd.DataFrame:
    if coded_df is None or coded_df.empty:
        return pd.DataFrame()
    df = coded_df.copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    target_ts = pd.to_datetime(target_date_str)
    return df[df["Date"] <= target_ts].sort_values("Date").tail(window).reset_index(drop=True)


def _ret_pct(close: pd.Series, n: int) -> float | None:
    if len(close) <= n:
        return None
    latest = safe_float(close.iloc[-1])
    base = safe_float(close.iloc[-(n + 1)])
    if latest is None or base in (None, 0):
        return None
    return round((latest / base - 1.0) * 100.0, 2)


def _shadow_ratio(target_row: pd.Series | dict[str, Any] | None, which: str) -> float | None:
    if target_row is None:
        return None
    row = target_row if isinstance(target_row, dict) else target_row.to_dict()
    open_price = safe_float(row.get("Open"))
    high = safe_float(row.get("High"))
    low = safe_float(row.get("Low"))
    close = safe_float(row.get("Close"))
    if None in {open_price, high, low, close}:
        return None
    total_range = high - low
    if total_range <= 0:
        return None
    upper_shadow = max(high - max(open_price, close), 0.0)
    lower_shadow = max(min(open_price, close) - low, 0.0)
    return round((upper_shadow if which == "upper" else lower_shadow) / total_range, 4)


def _peer_same_day_move(
    symbol: str,
    target_date_str: str,
    *,
    peer_loader: Callable[[str], pd.DataFrame | None],
) -> float | None:
    peer_df = peer_loader(symbol)
    if peer_df is None or peer_df.empty or "Date" not in peer_df.columns or "C_move" not in peer_df.columns:
        return None
    df = peer_df.copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    rows = df[df["Date"] == pd.to_datetime(target_date_str)]
    if rows.empty:
        return None
    value = safe_float(rows.iloc[0].get("C_move"))
    return round(value * 100.0, 2) if value is not None else None


def compute_20d_features(
    *,
    coded_df: pd.DataFrame,
    target_date_str: str,
    target_row: pd.Series | dict[str, Any] | None,
    target_ctx: dict[str, Any] | None,
    peer_loader: Callable[[str], pd.DataFrame | None] = load_peer_coded,
) -> dict[str, Any]:
    """Build the 20-day feature payload used by the new homepage chain."""
    window = _window_df(coded_df, target_date_str, window=20)
    if window.empty:
        return {"symbol": "AVGO"}
    peer_moves = {
        symbol: _peer_same_day_move(symbol, target_date_str, peer_loader=peer_loader)
        for symbol in _PEER_SYMBOLS
    }
    return build_feature_payload_from_recent_window(
        recent_window=window.to_dict("records"),
        symbol="AVGO",
        target_ctx=as_dict(target_ctx),
        peer_moves=peer_moves,
        feature_overrides={
            "upper_shadow_ratio": _shadow_ratio(target_row, "upper"),
            "lower_shadow_ratio": _shadow_ratio(target_row, "lower"),
        },
    )


def _today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def build_home_terminal_orchestrator_result(
    *,
    scan_result: dict[str, Any] | None,
    target_date_str: str,
    coded_df: pd.DataFrame,
    target_row: pd.Series | dict[str, Any] | None,
    target_ctx: dict[str, Any] | None,
    peer_loader: Callable[[str], pd.DataFrame | None] = load_peer_coded,
    log_writer: Callable[[dict[str, Any]], str] = write_prediction_log,
    persist_log: bool = True,
) -> dict[str, Any]:
    """Run the unified homepage orchestration chain and return one payload."""
    feature_payload = compute_20d_features(
        coded_df=coded_df,
        target_date_str=target_date_str,
        target_row=target_row,
        target_ctx=target_ctx,
        peer_loader=peer_loader,
    )
    historical_match_result = as_dict(as_dict(scan_result).get("historical_match_summary"))

    exclusion_result = run_exclusion_layer(feature_payload)
    main_projection = build_main_projection_layer(
        current_20day_features=feature_payload,
        exclusion_result=exclusion_result,
        historical_match_result=historical_match_result,
        peer_alignment=as_dict(exclusion_result.get("peer_alignment")),
        symbol="AVGO",
    )
    consistency = build_consistency_layer(
        exclusion_result=exclusion_result,
        main_projection_result=main_projection,
        peer_alignment=as_dict(exclusion_result.get("peer_alignment")),
        historical_match_result=historical_match_result,
        symbol="AVGO",
    )

    log_id = None
    if persist_log:
        log_id = log_writer(build_prediction_log_record(
            feature_payload=feature_payload,
            exclusion_result=exclusion_result,
            main_projection=main_projection,
            consistency=consistency,
            target_date_str=target_date_str,
            analysis_date=_today_str(),
            symbol="AVGO",
        ))

    return build_unified_projection_payload(
        kind="home_terminal_orchestrator_result",
        symbol="AVGO",
        ready=bool(main_projection.get("ready")),
        feature_payload=feature_payload,
        exclusion_result=exclusion_result,
        main_projection=main_projection,
        consistency=consistency,
        historical_match_result=historical_match_result,
        prediction_log_id=log_id,
    )


run_home_terminal_orchestrator = build_home_terminal_orchestrator_result
