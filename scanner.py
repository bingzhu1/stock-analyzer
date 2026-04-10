# -*- coding: utf-8 -*-
"""
scanner.py — Scan module for the AVGO Pattern Analyzer.

Aggregates all existing pipeline outputs (pattern code, stage, position,
context scores, stats summary) plus peer relative-strength into one
standardised ScanResult dict.

No UI code here.  Call run_scan() from app.py after the Run Analysis
pipeline completes.

Output schema
─────────────
{
  symbol                   : str          — always "AVGO"
  scan_timestamp           : str          — ISO-format datetime
  scan_phase               : str          — daily | premarket | open30 | midday | preclose
  scan_phase_note          : str          — honest source/fallback note
  avgo_price_state         : str          — bullish | bearish | neutral | unknown
  avgo_gap_state           : str          — gap_up | flat | gap_down | unknown
  avgo_intraday_state      : str          — high_go | low_go | range | unknown
  avgo_volume_state        : str          — expanding | shrinking | normal | unknown
  avgo_pattern_code        : str          — 5-digit code string, e.g. "33142"
  historical_match_summary : dict
      exact_match_count           : int
      near_match_count            : int
      top_context_score           : float | None
      dominant_historical_outcome : str  — up_bias | down_bias | mixed | insufficient_sample
  relative_strength_summary : dict        — 5-day layer, kept for compatibility
      vs_nvda  : str  — stronger | weaker | neutral | unavailable
      vs_soxx  : str
      vs_qqq   : str
  relative_strength_same_day_summary : dict
      vs_nvda  : str  — stronger | weaker | neutral | unavailable
      vs_soxx  : str
      vs_qqq   : str
  confirmation_state : str  — confirmed | diverging | mixed
  scan_bias          : str  — bullish | bearish | neutral
  scan_confidence    : str  — high | medium | low
  notes              : str  — concise human-readable summary
}
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

CODED_DIR      = Path("coded_data")
PEER_SYMBOLS   = ["NVDA", "SOXX", "QQQ"]
_GAP_THRESHOLD = 0.005   # ±0.5 % boundary for gap vs flat classification
_RS_MARGIN     = 0.005   # 0.5 pp — AVGO must beat peer by this to be "stronger"
_VALID_SCAN_PHASES = {"premarket", "open30", "midday", "preclose", "daily"}


# ─────────────────────────────────────────────────────────────────────────────
# Peer data loading
# ─────────────────────────────────────────────────────────────────────────────

def load_peer_coded(symbol: str) -> pd.DataFrame | None:
    """Load coded CSV for a peer symbol.  Returns None if file is missing."""
    path = CODED_DIR / f"{symbol}_coded.csv"
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path, dtype={"Code": "string"})
        df["Date"]  = pd.to_datetime(df["Date"])
        df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
        if "C_move" in df.columns:
            df["C_move"] = pd.to_numeric(df["C_move"], errors="coerce")
        return df.sort_values("Date").reset_index(drop=True)
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Relative strength
# ─────────────────────────────────────────────────────────────────────────────

def _get_nday_return(df: pd.DataFrame, target_date_str: str, n: int = 5) -> float | None:
    """5-day price return ending at target_date, in percent.  None if data missing."""
    target_ts = pd.to_datetime(target_date_str)
    idx_list = df.index[df["Date"] == target_ts].tolist()
    if not idx_list:
        return None
    idx = idx_list[0]
    if idx < n:
        return None
    c_now  = df.iloc[idx]["Close"]
    c_prev = df.iloc[idx - n]["Close"]
    if pd.isna(c_now) or pd.isna(c_prev) or c_prev == 0:
        return None
    return (c_now - c_prev) / c_prev * 100


def _get_same_day_move(df: pd.DataFrame, target_date_str: str) -> float | None:
    """Same-day close-vs-open move ending at target_date, in percent."""
    if "C_move" not in df.columns:
        return None
    target_ts = pd.to_datetime(target_date_str)
    rows = df[df["Date"] == target_ts]
    if rows.empty:
        return None
    c_move = rows.iloc[0].get("C_move")
    if pd.isna(c_move):
        return None
    return float(c_move) * 100


def _classify_rs(avgo_ret: float | None, peer_ret: float | None) -> str:
    """Compare AVGO and peer returns.  Margin = 0.5 pp."""
    if avgo_ret is None or peer_ret is None:
        return "unavailable"
    diff = avgo_ret - peer_ret
    if diff > _RS_MARGIN * 100:      # _RS_MARGIN is ratio; returns are in %
        return "stronger"
    if diff < -_RS_MARGIN * 100:
        return "weaker"
    return "neutral"


def compute_relative_strength_summary(
    target_date_str: str,
    avgo_ret5: float | None,
    peer_codeds: dict[str, pd.DataFrame | None],
) -> dict[str, str]:
    """
    Compare AVGO's 5-day return vs NVDA, SOXX, QQQ.
    Returns {vs_nvda, vs_soxx, vs_qqq} each: stronger / weaker / neutral / unavailable.
    """
    result: dict[str, str] = {}
    for sym in PEER_SYMBOLS:
        peer_df  = peer_codeds.get(sym)
        peer_ret = _get_nday_return(peer_df, target_date_str) if peer_df is not None else None
        result[f"vs_{sym.lower()}"] = _classify_rs(avgo_ret5, peer_ret)
    return result


def compute_same_day_relative_strength_summary(
    target_date_str: str,
    avgo_same_day_move: float | None,
    peer_codeds: dict[str, pd.DataFrame | None],
) -> dict[str, str]:
    """
    Compare AVGO's same-day close-vs-open move vs NVDA, SOXX, QQQ.
    Reuses the existing C_move daily feature when available.
    """
    result: dict[str, str] = {}
    for sym in PEER_SYMBOLS:
        peer_df = peer_codeds.get(sym)
        peer_move = _get_same_day_move(peer_df, target_date_str) if peer_df is not None else None
        result[f"vs_{sym.lower()}"] = _classify_rs(avgo_same_day_move, peer_move)
    return result


def normalize_scan_phase(scan_phase: str | None) -> str:
    """Return a supported scan phase, falling back honestly to daily."""
    phase = str(scan_phase or "daily").strip().lower()
    return phase if phase in _VALID_SCAN_PHASES else "daily"


def build_scan_phase_note(scan_phase: str) -> str:
    """Explain whether the phase is true daily data or a manual intraday label."""
    if scan_phase == "daily":
        return "Daily close-based scan using daily OHLCV features."
    return (
        f"{scan_phase} manual phase selected; using daily OHLCV fallback "
        "because intraday/minute data is not available."
    )


# ─────────────────────────────────────────────────────────────────────────────
# AVGO state derivation
# ─────────────────────────────────────────────────────────────────────────────

def derive_avgo_states(
    target_row: pd.Series | None,
    mom_row: pd.Series | None,
) -> dict[str, str]:
    """
    Produce four categorical state strings from the target day's feature data.

    avgo_gap_state      — gap_up / flat / gap_down / unknown  (from O_gap)
    avgo_intraday_state — high_go / low_go / range / unknown  (from C_move)
    avgo_volume_state   — expanding / shrinking / normal / unknown  (from V_ratio)
    avgo_price_state    — bullish / bearish / neutral / unknown  (from StageLabel)
    """
    result: dict[str, str] = {
        "avgo_gap_state":      "unknown",
        "avgo_price_state":    "unknown",
        "avgo_intraday_state": "unknown",
        "avgo_volume_state":   "unknown",
    }

    if target_row is None:
        return result

    # gap state — O_gap = (Open − PrevClose) / PrevClose
    o_gap = target_row.get("O_gap")
    if pd.notna(o_gap):
        o_gap = float(o_gap)
        if o_gap > _GAP_THRESHOLD:
            result["avgo_gap_state"] = "gap_up"
        elif o_gap < -_GAP_THRESHOLD:
            result["avgo_gap_state"] = "gap_down"
        else:
            result["avgo_gap_state"] = "flat"

    # intraday state — C_move = (Close − Open) / Open
    c_move = target_row.get("C_move")
    if pd.notna(c_move):
        c_move = float(c_move)
        if c_move > _GAP_THRESHOLD:
            result["avgo_intraday_state"] = "high_go"
        elif c_move < -_GAP_THRESHOLD:
            result["avgo_intraday_state"] = "low_go"
        else:
            result["avgo_intraday_state"] = "range"

    # volume state — V_ratio = Volume / MA20_Volume
    v_ratio = target_row.get("V_ratio")
    if pd.notna(v_ratio):
        v_ratio = float(v_ratio)
        if v_ratio > 1.10:
            result["avgo_volume_state"] = "expanding"
        elif v_ratio < 0.90:
            result["avgo_volume_state"] = "shrinking"
        else:
            result["avgo_volume_state"] = "normal"

    # price state — from classify_stage() result stored in mom_df
    if mom_row is not None:
        stage = str(mom_row.get("StageLabel", "—"))
        if stage in ("启动", "加速", "延续"):
            result["avgo_price_state"] = "bullish"
        elif stage in ("衰竭风险", "分歧"):
            result["avgo_price_state"] = "bearish"
        elif stage in ("整理", "—"):
            result["avgo_price_state"] = "neutral"
        # Fallback: use Ret5 when StageLabel is missing
        if result["avgo_price_state"] == "unknown":
            ret5 = mom_row.get("Ret5")
            if pd.notna(ret5):
                ret5 = float(ret5)
                result["avgo_price_state"] = (
                    "bullish" if ret5 > 2.0 else "bearish" if ret5 < -2.0 else "neutral"
                )

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Historical match summary
# ─────────────────────────────────────────────────────────────────────────────

def build_historical_match_summary(
    exact_df: pd.DataFrame,
    near_df: pd.DataFrame,
    summary_df: pd.DataFrame,
) -> dict[str, Any]:
    """
    Distil match pipeline outputs into a compact summary.
    Uses exact matches for dominant outcome; top context score across both.
    """
    # Top context score across exact + near
    top_ctx: float | None = None
    for df in (exact_df, near_df):
        if not df.empty and "ContextScore" in df.columns:
            m = df["ContextScore"].dropna()
            if not m.empty:
                top_ctx = max(top_ctx or 0.0, float(m.max()))

    # Dominant outcome — prefer exact matches
    dominant = "insufficient_sample"
    if not summary_df.empty:
        exact_row = summary_df[summary_df["MatchType"] == "exact"]
        if not exact_row.empty:
            dominant = str(exact_row.iloc[0].get("DominantNextDayBias", "insufficient_sample"))

    return {
        "exact_match_count":           len(exact_df),
        "near_match_count":            len(near_df),
        "top_context_score":           top_ctx,
        "dominant_historical_outcome": dominant,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Confirmation state
# ─────────────────────────────────────────────────────────────────────────────

def compute_confirmation_state(
    price_state: str,
    rs_5d_summary: dict[str, str],
    rs_same_day_summary: dict[str, str],
) -> str:
    """
    Does peer RS confirm AVGO's directional state across two daily layers?

    confirmed  — peer evidence agrees with AVGO direction
    diverging  — peer evidence opposes AVGO direction
    mixed      — split, or price_state is neutral/unknown
    """
    if price_state not in ("bullish", "bearish"):
        return "mixed"

    votes_confirm = 0
    votes_oppose  = 0

    def _layer_vote(val: str) -> str:
        if val == "unavailable":
            return "unavailable"
        if price_state == "bullish":
            if val == "stronger":
                return "confirm"
            if val == "weaker":
                return "oppose"
        else:
            if val == "weaker":
                return "confirm"
            if val == "stronger":
                return "oppose"
        return "mixed"

    for sym in PEER_SYMBOLS:
        key = f"vs_{sym.lower()}"
        layer_votes = {
            _layer_vote(rs_5d_summary.get(key, "unavailable")),
            _layer_vote(rs_same_day_summary.get(key, "unavailable")),
        }
        if "confirm" in layer_votes and "oppose" in layer_votes:
            peer_vote = "mixed"
        elif "confirm" in layer_votes:
            peer_vote = "confirm"
        elif "oppose" in layer_votes:
            peer_vote = "oppose"
        elif layer_votes == {"unavailable"}:
            peer_vote = "unavailable"
        else:
            peer_vote = "mixed"

        if peer_vote == "confirm":
            votes_confirm += 1
        elif peer_vote == "oppose":
            votes_oppose += 1

    if votes_confirm >= 2:
        return "confirmed"
    if votes_oppose >= 2:
        return "diverging"
    return "mixed"


# ─────────────────────────────────────────────────────────────────────────────
# Scan bias + confidence  (v1 rule-based)
# ─────────────────────────────────────────────────────────────────────────────

def compute_scan_bias_and_confidence(
    gap_state:          str,
    vol_state:          str,
    price_state:        str,
    dominant_outcome:   str,
    confirmation_state: str,
) -> tuple[str, str]:
    """
    Explainable v1.1 score:
      1. gap_state:        gap_up +1 / gap_down -1
      2. vol_state:        expanding +1 / shrinking -1
      3. price_state:      bullish +1 / bearish -1
      4. dominant_outcome: up_bias +0.5 / down_bias -0.5
      5. RS confirmation:  confirmed/directional +2, diverging/opposite -2

    scan_bias:       score >= 3 -> bullish | <= -3 -> bearish | else neutral
    scan_confidence: |score| >= 4 -> high | >= 3 -> medium | else low
                     Divergence downgrades confidence aggressively.
    """
    score = 0.0

    if gap_state == "gap_up":
        score += 1
    elif gap_state == "gap_down":
        score -= 1

    if vol_state == "expanding":
        score += 1
    elif vol_state == "shrinking":
        score -= 1

    if price_state == "bullish":
        score += 1
    elif price_state == "bearish":
        score -= 1

    if dominant_outcome == "up_bias":
        score += 0.5
    elif dominant_outcome == "down_bias":
        score -= 0.5

    # RS confirmation matters more than historical sample bias in Scan v1.1.
    if price_state == "bullish":
        if confirmation_state == "confirmed":
            score += 2
        elif confirmation_state == "diverging":
            score -= 2
    elif price_state == "bearish":
        if confirmation_state == "confirmed":
            score -= 2
        elif confirmation_state == "diverging":
            score += 2

    bias = "bullish" if score >= 3 else "bearish" if score <= -3 else "neutral"

    abs_score = abs(score)
    if abs_score >= 4:
        confidence = "high"
    elif abs_score >= 3:
        confidence = "medium"
    else:
        confidence = "low"

    if confirmation_state == "diverging":
        confidence = "low"

    return bias, confidence


# ─────────────────────────────────────────────────────────────────────────────
# Notes generator
# ─────────────────────────────────────────────────────────────────────────────

_GAP_LABELS   = {"gap_up": "gap up", "flat": "flat open", "gap_down": "gap down", "unknown": "gap unknown"}
_VOL_LABELS   = {"expanding": "volume expanding", "normal": "normal volume", "shrinking": "volume shrinking", "unknown": "volume unknown"}
_PRICE_LABELS = {"bullish": "bullish stage", "neutral": "neutral stage", "bearish": "bearish stage", "unknown": "stage unknown"}
_INTRA_LABELS = {"high_go": "closed above open", "low_go": "closed below open", "range": "range day", "unknown": "intraday unknown"}
_RS_LABELS    = {"stronger": "stronger", "weaker": "weaker", "neutral": "neutral", "unavailable": "n/a"}
_CONF_LABELS  = {"confirmed": "confirmed", "diverging": "diverging", "mixed": "mixed"}
_BIAS_LABELS  = {"bullish": "bullish", "bearish": "bearish", "neutral": "neutral"}
_CONFD_LABELS = {"high": "high confidence", "medium": "medium confidence", "low": "low confidence"}
_OUTCOME_LABELS = {
    "up_bias": "historical up bias",
    "down_bias": "historical down bias",
    "mixed": "historical mixed",
    "insufficient_sample": "insufficient sample",
}


def _build_notes(
    states: dict[str, str],
    rs_5d_summary: dict[str, str],
    rs_same_day_summary: dict[str, str],
    hist_summary: dict[str, Any],
    confirmation_state: str,
    bias: str,
    confidence: str,
) -> str:
    gap_l   = _GAP_LABELS.get(states["avgo_gap_state"], states["avgo_gap_state"])
    vol_l   = _VOL_LABELS.get(states["avgo_volume_state"], states["avgo_volume_state"])
    price_l = _PRICE_LABELS.get(states["avgo_price_state"], states["avgo_price_state"])
    intra_l = _INTRA_LABELS.get(states["avgo_intraday_state"], states["avgo_intraday_state"])

    def _format_rs(summary: dict[str, str]) -> str:
        parts = [
            f"{sym.replace('vs_', '').upper()} {_RS_LABELS.get(v, v)}"
            for sym, v in summary.items()
            if v != "unavailable"
        ]
        return ", ".join(parts) if parts else "n/a"

    top_ctx    = hist_summary["top_context_score"]
    ctx_str    = f"{top_ctx:.0f}" if top_ctx is not None else "n/a"
    outcome_l  = _OUTCOME_LABELS.get(hist_summary["dominant_historical_outcome"], "n/a")
    conf_l     = _CONF_LABELS.get(confirmation_state, "n/a")
    bias_l     = _BIAS_LABELS.get(bias, bias)
    confidence_l = _CONFD_LABELS.get(confidence, confidence)

    sentences = [
        f"AVGO: {gap_l}, {intra_l}, {vol_l}; {price_l}.",
        (
            f"Matches: exact {hist_summary['exact_match_count']}, "
            f"near {hist_summary['near_match_count']}, "
            f"top context {ctx_str}, {outcome_l}."
        ),
        f"RS 5d: {_format_rs(rs_5d_summary)}.",
        f"RS same-day: {_format_rs(rs_same_day_summary)}.",
        f"Confirmation: {conf_l}.",
        f"Scan: {bias_l} / {confidence_l}.",
    ]
    return " ".join(s for s in sentences if s)


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

def run_scan(
    target_date_str: str,
    coded_df: pd.DataFrame,
    exact_df: pd.DataFrame,
    near_df: pd.DataFrame,
    summary_df: pd.DataFrame,
    pos_df: pd.DataFrame,
    prev_df: pd.DataFrame,
    mom_df: pd.DataFrame,
    scan_phase: str = "daily",
) -> dict[str, Any]:
    """
    Produce a standardised ScanResult dict from already-computed pipeline outputs.
    All inputs come from app.py session_state after Run Analysis completes.
    Loads peer coded CSVs internally (fast — small files, cached by OS).
    """
    scan_phase = normalize_scan_phase(scan_phase)
    scan_phase_note = build_scan_phase_note(scan_phase)
    timestamp  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    target_ts  = pd.to_datetime(target_date_str)

    # ── Target day rows ───────────────────────────────────────────────────────
    target_row: pd.Series | None = None
    cr = coded_df[coded_df["Date"] == target_ts]
    if not cr.empty:
        target_row = cr.iloc[0]

    mom_row: pd.Series | None = None
    if not mom_df.empty:
        mr = mom_df[mom_df["Date"] == target_ts]
        if not mr.empty:
            mom_row = mr.iloc[0]

    # ── Pattern code ──────────────────────────────────────────────────────────
    pattern_code = "—"
    if target_row is not None and pd.notna(target_row.get("Code")):
        pattern_code = str(target_row["Code"])

    # ── AVGO state labels ─────────────────────────────────────────────────────
    states = derive_avgo_states(target_row, mom_row)

    # ── Peer relative strength ────────────────────────────────────────────────
    peer_codeds: dict[str, pd.DataFrame | None] = {
        sym: load_peer_coded(sym) for sym in PEER_SYMBOLS
    }
    avgo_ret5: float | None = (
        float(mom_row["Ret5"])
        if mom_row is not None and pd.notna(mom_row.get("Ret5"))
        else None
    )
    avgo_same_day_move: float | None = (
        float(target_row["C_move"]) * 100
        if target_row is not None and pd.notna(target_row.get("C_move"))
        else None
    )
    rs_5d_summary = compute_relative_strength_summary(target_date_str, avgo_ret5, peer_codeds)
    rs_same_day_summary = compute_same_day_relative_strength_summary(
        target_date_str, avgo_same_day_move, peer_codeds
    )

    # ── Historical match summary ──────────────────────────────────────────────
    hist_summary = build_historical_match_summary(exact_df, near_df, summary_df)

    # ── Confirmation ──────────────────────────────────────────────────────────
    conf_state = compute_confirmation_state(
        states["avgo_price_state"], rs_5d_summary, rs_same_day_summary
    )

    # ── Scan bias + confidence ────────────────────────────────────────────────
    bias, confidence = compute_scan_bias_and_confidence(
        gap_state=states["avgo_gap_state"],
        vol_state=states["avgo_volume_state"],
        price_state=states["avgo_price_state"],
        dominant_outcome=hist_summary["dominant_historical_outcome"],
        confirmation_state=conf_state,
    )

    # ── Notes ─────────────────────────────────────────────────────────────────
    notes = _build_notes(
        states, rs_5d_summary, rs_same_day_summary, hist_summary, conf_state, bias, confidence
    )

    return {
        "symbol":         "AVGO",
        "scan_timestamp": timestamp,
        "scan_phase":     scan_phase,
        "scan_phase_note": scan_phase_note,
        # AVGO state
        "avgo_price_state":    states["avgo_price_state"],
        "avgo_gap_state":      states["avgo_gap_state"],
        "avgo_intraday_state": states["avgo_intraday_state"],
        "avgo_volume_state":   states["avgo_volume_state"],
        "avgo_pattern_code":   pattern_code,
        # Aggregated sub-dicts
        "historical_match_summary":  hist_summary,
        "relative_strength_summary": rs_5d_summary,
        "relative_strength_5d_summary": rs_5d_summary,
        "relative_strength_same_day_summary": rs_same_day_summary,
        # Derived meta-fields
        "confirmation_state": conf_state,
        "scan_bias":          bias,
        "scan_confidence":    confidence,
        "notes":              notes,
    }
