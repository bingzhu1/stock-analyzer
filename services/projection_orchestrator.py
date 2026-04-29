"""Projection orchestrator for command-facing final reports.

The orchestrator keeps projection wiring thin: it builds the existing advisory
package, invokes the existing Scan + Predict path for the latest AVGO daily
data, then formats that result into a user-readable next-day report.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from matcher import build_near_match_table, build_next_day_match_table, load_coded_avgo
from predict import run_predict
from scanner import run_scan
from services.projection_orchestrator_preflight import (
    build_projection_orchestrator_preflight,
)
from services.data_query import load_symbol_data
from services.evidence_trace import build_projection_evidence_trace
from services.predict_summary import build_predict_readable_summary
from stats_reporter import SUMMARY_COLUMNS, summarize_match_df

_PROJECTION_NOTE = "Projection report built from existing Scan + Predict outputs."
_SUPPORTED_FINAL_SYMBOLS = {"AVGO"}


def _normalize_final_symbol(symbol: str) -> str:
    normalized = str(symbol or "").strip().upper()
    if normalized not in _SUPPORTED_FINAL_SYMBOLS:
        raise ValueError("最终推演报告目前仅支持 AVGO / 博通。")
    return normalized


def _latest_target_date(coded_df: pd.DataFrame) -> str:
    if coded_df.empty:
        raise ValueError("AVGO coded data is empty; cannot build projection report.")
    return pd.to_datetime(coded_df["Date"].max()).strftime("%Y-%m-%d")


def _build_summary_df(exact_df: pd.DataFrame, near_df: pd.DataFrame) -> pd.DataFrame:
    rows = [
        summarize_match_df(exact_df, "exact"),
        summarize_match_df(near_df, "near"),
    ]
    return pd.DataFrame(rows)[SUMMARY_COLUMNS]


def _build_momentum_frame(symbol: str, *, target_date: str | None = None) -> pd.DataFrame:
    mom_df = load_symbol_data(
        symbol,
        window=0,
        fields=["Ret3", "Ret5", "StageLabel"],
    )
    mom_df = mom_df.copy()
    mom_df["Date"] = pd.to_datetime(mom_df["Date"])
    if target_date:
        mom_df = mom_df[mom_df["Date"] <= pd.to_datetime(target_date)].reset_index(drop=True)
    return mom_df


def _build_predict_result(
    symbol: str,
    *,
    target_date: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any], str]:
    """
    Run the existing daily Scan + Predict path.

    When ``target_date`` is provided the coded dataframe is filtered to rows
    with ``Date <= target_date`` so the entire pipeline sees only data
    available as of that date. When ``target_date`` is ``None`` the live
    behaviour (latest row) is preserved.
    """
    symbol = _normalize_final_symbol(symbol)
    coded_df = load_coded_avgo()
    if target_date:
        coded_df = coded_df[
            pd.to_datetime(coded_df["Date"]) <= pd.to_datetime(target_date)
        ].reset_index(drop=True)
        if coded_df.empty:
            raise ValueError(
                f"AVGO coded data is empty on or before {target_date}; "
                "cannot build projection report."
            )
        resolved_target_date = pd.to_datetime(target_date).strftime("%Y-%m-%d")
    else:
        resolved_target_date = _latest_target_date(coded_df)

    exact_df = build_next_day_match_table(coded_df, resolved_target_date)
    near_df = build_near_match_table(coded_df, resolved_target_date)
    summary_df = _build_summary_df(exact_df, near_df)
    mom_df = _build_momentum_frame(symbol, target_date=target_date)

    scan_result = run_scan(
        resolved_target_date,
        coded_df,
        exact_df,
        near_df,
        summary_df,
        pd.DataFrame(),
        pd.DataFrame(),
        mom_df,
        scan_phase="daily",
    )
    predict_result = run_predict(scan_result, research_result=None, symbol=symbol)
    return dict(predict_result), dict(scan_result), resolved_target_date


def format_projection_report(
    predict_result: dict[str, Any] | None,
    *,
    advisory: dict[str, Any] | None = None,
    scan_result: dict[str, Any] | None = None,
    target_date: str | None = None,
    lookback_days: int | None = None,
) -> dict[str, Any]:
    """Format Predict output into the command-facing Chinese report shape."""
    readable = build_predict_readable_summary(
        predict_result,
        scan_result=scan_result,
        advisory=advisory,
        lookback_days=lookback_days,
    )

    report = {
        "kind": "final_projection_report",
        "target_date": target_date,
        "direction": readable["baseline_judgment"]["direction"],
        "open_tendency": readable["open_projection"]["tendency"],
        "close_tendency": readable["close_projection"]["tendency"],
        "confidence": readable["baseline_judgment"]["confidence"],
        "basis_summary": readable["rationale"],
        "risk_reminders": readable["risk_reminders"],
        "readable_summary": readable,
    }
    report["report_text"] = readable["summary_text"]
    report["evidence_trace"] = build_projection_evidence_trace(
        predict_result=predict_result,
        scan_result=scan_result,
        projection_report=report,
        advisory=advisory,
    )
    return report


def build_projection_orchestrator_result(
    *,
    symbol: str,
    error_category: str | None = None,
    limit: int = 5,
    lookback_days: int | None = None,
    target_date: str | None = None,
) -> dict[str, Any]:
    """Return a final projection report plus advisory context."""
    advisory = build_projection_orchestrator_preflight(
        symbol=symbol,
        error_category=error_category,
        limit=limit,
    )
    normalized_symbol = _normalize_final_symbol(advisory["symbol"])
    request = {
        "symbol": normalized_symbol,
        "error_category": error_category,
        "limit": limit,
        "lookback_days": lookback_days,
        "target_date": target_date,
    }
    predict_result, scan_result, resolved_target_date = _build_predict_result(
        normalized_symbol, target_date=target_date
    )
    report = format_projection_report(
        predict_result,
        advisory=advisory,
        scan_result=scan_result,
        target_date=resolved_target_date,
        lookback_days=lookback_days,
    )

    return {
        "symbol": normalized_symbol,
        "request": request,
        "advisory": advisory,
        "projection_report": report,
        "predict_result": predict_result,
        "scan_result": scan_result,
        "ready": advisory["ready"] and report["kind"] == "final_projection_report",
        "notes": [_PROJECTION_NOTE],
        "advisory_only": False,
    }
