from __future__ import annotations

import os
import shutil
import json
from datetime import datetime
from pathlib import Path

# Ensure the working directory is always the repo root so that all relative
# paths used by the core modules (data/, enriched_data/, etc.) resolve correctly
# regardless of where `streamlit run` is invoked from.
os.chdir(Path(__file__).parent)

from dotenv import load_dotenv

load_dotenv()

import matplotlib
matplotlib.use("Agg")   # non-interactive backend — must be set before pyplot import
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.font_manager as fm


def _setup_matplotlib_fonts() -> None:
    """
    Detect the first available Chinese-capable font and apply it globally.
    Also disables matplotlib's broken minus-sign substitution.

    Priority order (macOS built-ins first, then cross-platform fallbacks):
      PingFang SC       — macOS system font, full CJK coverage
      Heiti SC          — macOS legacy CJK font
      Hiragino Sans GB  — macOS Japanese/CJK font (covers Simplified Chinese)
      Arial Unicode MS  — macOS/Office broad Unicode font
      Noto Sans CJK SC  — Google Noto (Linux / manually installed)
      Noto Sans CJK     — variant name used on some distros
      WenQuanYi Micro Hei — common Linux CJK font
      SimHei            — Windows built-in CJK font
      Microsoft YaHei   — Windows built-in CJK font
    """
    _PREFERRED = [
        "PingFang SC",
        "Heiti SC",
        "Hiragino Sans GB",
        "Arial Unicode MS",
        "Noto Sans CJK SC",
        "Noto Sans CJK",
        "WenQuanYi Micro Hei",
        "SimHei",
        "Microsoft YaHei",
    ]

    available = {f.name for f in fm.fontManager.ttflist}
    chosen = next((f for f in _PREFERRED if f in available), None)

    if chosen:
        matplotlib.rcParams["font.sans-serif"] = [chosen] + matplotlib.rcParams["font.sans-serif"]
        matplotlib.rcParams["font.family"] = "sans-serif"
    # Even without a CJK font, disable the broken minus → unicode replacement
    matplotlib.rcParams["axes.unicode_minus"] = False


_setup_matplotlib_fonts()

import streamlit as st
import pandas as pd

from data_fetcher import batch_update_all
from feature_builder import batch_build_features
from encoder import batch_encode_all
from matcher import (
    build_near_match_table,
    build_next_day_match_table,
    load_coded_avgo,
    save_match_results,
    save_near_match_results,
)
from stats_reporter import build_stats_summary, save_stats_summary
from scanner import run_scan
from services.analysis_context import (
    friendly_analysis_error,
    reset_analysis_context_state,
    validate_target_code_for_analysis,
)
from ui.command_bar import render_command_bar
from services.home_terminal_orchestrator import build_home_terminal_orchestrator_result
from ui.home_tab import render_home_tab
from ui.history_tab import render_history_tab
from ui.predict_tab import render_predict_tab
from ui.research_tab import render_research_tab
from ui.scan_tab import render_scan_tab
from ui.review_tab import render_review_tab
from ui.inspect_tab import render_inspect_tab


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

# Human-readable label for each (dimension, code-digit) pair.
CODE_LABELS: dict[str, dict[int, str]] = {
    "O": {
        1: "Strong gap down  (< −2%)",
        2: "Mild gap down    (−2% to −0.5%)",
        3: "Flat open        (−0.5% to +0.5%)",
        4: "Mild gap up      (+0.5% to +2%)",
        5: "Strong gap up    (> +2%)",
    },
    "H": {
        1: "Tiny wick   (< 0.5%)",
        2: "Small wick  (0.5% – 1.5%)",
        3: "Moderate    (1.5% – 3%)",
        4: "Large       (3% – 5%)",
        5: "Very large  (> 5%)",
    },
    "L": {
        1: "Tiny wick   (< 0.5%)",
        2: "Small wick  (0.5% – 1.5%)",
        3: "Moderate    (1.5% – 3%)",
        4: "Large       (3% – 5%)",
        5: "Very large  (> 5%)",
    },
    "C": {
        1: "Strong close down  (< −2%)",
        2: "Mild close down    (−2% to −0.5%)",
        3: "Flat close         (−0.5% to +0.5%)",
        4: "Mild close up      (+0.5% to +2%)",
        5: "Strong close up    (> +2%)",
    },
    "V": {
        1: "Very low   (< 70% of MA20)",
        2: "Below avg  (70% – 90%)",
        3: "Average    (90% – 110%)",
        4: "Above avg  (110% – 150%)",
        5: "Very high  (> 150%)",
    },
}

# Columns that hold ratios (e.g. 0.012) that should be displayed as percentages.
PCT_MOVE_COLS = [
    "NextOpenChange", "NextHighMove", "NextLowMove", "NextCloseMove",
    "T2OpenChange", "T2CloseMove",
]

BIAS_ICONS = {
    "up_bias":             "🟢 up_bias",
    "down_bias":           "🔴 down_bias",
    "mixed":               "🟡 mixed",
    "insufficient_sample": "⚪ insufficient_sample",
}

# column_config applied to every match dataframe — percentages display as e.g. "+1.23%"
# (values are multiplied by 100 before display, so 0.0123 → 1.23, then "%.2f%%" → "1.23%")
COL_CONFIG: dict[str, st.column_config.Column] = {
    # MatchDate OHLCV
    "MatchOpen":      st.column_config.NumberColumn("Match 开盘",   format="%.2f"),
    "MatchHigh":      st.column_config.NumberColumn("Match 最高",   format="%.2f"),
    "MatchLow":       st.column_config.NumberColumn("Match 最低",   format="%.2f"),
    "MatchClose":     st.column_config.NumberColumn("Match 收盘",   format="%.2f"),
    "MatchVolume":    st.column_config.NumberColumn("Match 成交量"),
    "MatchTurnover":  st.column_config.NumberColumn("Match 成交额"),
    # T+1 moves (values pre-multiplied ×100 before display)
    "NextOpenChange": st.column_config.NumberColumn("T+1 开盘变动", format="%.2f%%"),
    "NextHighMove":   st.column_config.NumberColumn("T+1 日内最高", format="%.2f%%"),
    "NextLowMove":    st.column_config.NumberColumn("T+1 日内最低", format="%.2f%%"),
    "NextCloseMove":  st.column_config.NumberColumn("T+1 收盘变动", format="%.2f%%"),
    # T+1 OHLCV
    "NextOpen":       st.column_config.NumberColumn("T+1 开盘",     format="%.2f"),
    "NextHigh":       st.column_config.NumberColumn("T+1 最高",     format="%.2f"),
    "NextLow":        st.column_config.NumberColumn("T+1 最低",     format="%.2f"),
    "NextClose":      st.column_config.NumberColumn("T+1 收盘",     format="%.2f"),
    "NextVolume":     st.column_config.NumberColumn("T+1 成交量"),
    "NextTurnover":   st.column_config.NumberColumn("T+1 成交额"),
    # T+2 moves
    "T2OpenChange":   st.column_config.NumberColumn("T+2 开盘变动", format="%.2f%%"),
    "T2CloseMove":    st.column_config.NumberColumn("T+2 收盘变动", format="%.2f%%"),
    # T+2 OHLCV
    "T2Open":         st.column_config.NumberColumn("T+2 开盘",     format="%.2f"),
    "T2High":         st.column_config.NumberColumn("T+2 最高",     format="%.2f"),
    "T2Low":          st.column_config.NumberColumn("T+2 最低",     format="%.2f"),
    "T2Close":        st.column_config.NumberColumn("T+2 收盘",     format="%.2f"),
    "T2Volume":       st.column_config.NumberColumn("T+2 成交量"),
    "T2Turnover":     st.column_config.NumberColumn("T+2 成交额"),
    # Position context (values stored as 0–100)
    "MatchPos15":          st.column_config.NumberColumn("位置15日%",    format="%.1f"),
    "MatchPos30":          st.column_config.NumberColumn("位置30日%",    format="%.1f"),
    "MatchPosLabel":       st.column_config.TextColumn("位置标签"),
    # Previous-day state
    "MatchPrevDate":       st.column_config.TextColumn("前一日"),
    "MatchPrevCode":       st.column_config.TextColumn("前一日编码"),
    "MatchPrevOpenType":   st.column_config.TextColumn("前一日开盘"),
    "MatchPrevStructure":  st.column_config.TextColumn("前一日结构"),
    "MatchPrevCloseDir":   st.column_config.TextColumn("前一日收盘"),
    "MatchPrevCloseMove":  st.column_config.NumberColumn("前一日涨跌%",  format="%.2f"),
    "MatchPrevVolume":     st.column_config.NumberColumn("前一日成交量"),
    "MatchPrevTurnover":   st.column_config.NumberColumn("前一日成交额"),
    "MatchPrevVRatio":     st.column_config.NumberColumn("前一日相对量", format="%.2f"),
    # Momentum / stage
    "MatchStageLabel":    st.column_config.TextColumn("阶段"),
    "MatchRet3":          st.column_config.NumberColumn("3日涨跌%",   format="%+.2f"),
    "MatchRet5":          st.column_config.NumberColumn("5日涨跌%",   format="%+.2f"),
    "MatchRet10":         st.column_config.NumberColumn("10日涨跌%",  format="%+.2f"),
    "MatchVol5Ratio":     st.column_config.NumberColumn("量/5日均",   format="%.2f"),
    "MatchVolState":      st.column_config.TextColumn("量能"),
    # Context similarity scoring
    "ContextScore":       st.column_config.NumberColumn("相似度",   format="%.0f"),
    "ContextLabel":       st.column_config.TextColumn("相似标签"),
}
# Keep old alias so any leftover reference still resolves.
PCT_COL_CONFIG = COL_CONFIG

# Canonical display order for intraday structure categories.
STRUCTURE_ORDER = ["高开高走", "高开低走", "低开高走", "低开低走", "平开震荡"]
_STRUCTURE_COLORS = {
    "高开高走": "#2ecc71",
    "低开高走": "#27ae60",
    "高开低走": "#e74c3c",
    "低开低走": "#c0392b",
    "平开震荡": "#95a5a6",
}

_STAGE_COLORS = {
    "启动":    "#3498db",   # blue   — new move beginning from low base
    "加速":    "#2ecc71",   # green  — strong momentum + expanding volume
    "延续":    "#27ae60",   # teal   — normal on-trend continuation
    "整理":    "#95a5a6",   # gray   — sideways / low-volume pause
    "分歧":    "#f39c12",   # amber  — price/volume divergence, caution
    "衰竭风险": "#e74c3c",  # red    — high position + momentum reversing
}

# Stage adjacency groups for context scoring: same group earns partial credit.
_STAGE_ADJACENCY: dict[str, str] = {
    "启动":    "momentum",   # breakout / acceleration group
    "加速":    "momentum",
    "延续":    "neutral",    # steady-state group
    "整理":    "neutral",
    "分歧":    "risk",       # topping / exhaustion group
    "衰竭风险": "risk",
}

# Threshold (as raw ratio) for classifying open/close direction.
_GAP_THRESHOLD = 0.005   # ±0.5 %


# ─────────────────────────────────────────────────────────────────────────────
# Pattern classification helpers
# ─────────────────────────────────────────────────────────────────────────────

def _classify_open(open_chg: float) -> str:
    if open_chg > _GAP_THRESHOLD:
        return "高开"
    if open_chg < -_GAP_THRESHOLD:
        return "低开"
    return "平开"


def _classify_close(close_move: float) -> str:
    if close_move > _GAP_THRESHOLD:
        return "收涨"
    if close_move < -_GAP_THRESHOLD:
        return "收跌"
    return "平收"


def _classify_structure(open_chg: float, close_move: float) -> str:
    ot = _classify_open(open_chg)
    if ot == "高开":
        return "高开高走" if close_move >= 10 else "高开低走"
    if ot == "低开":
        return "低开高走" if close_move >= -10 else "低开低走"
    return "平开震荡"


def enrich_with_t2(match_df: pd.DataFrame, coded_df: pd.DataFrame) -> pd.DataFrame:
    """
    Append T+2 OHLCV and move columns to a match result dataframe.
    T+2 is the trading row two positions after MatchDate in coded_df.
    Rows where T+2 does not yet exist (match too close to end of data)
    are filled with pd.NA — they display as blank cells in Streamlit.
    Does not touch any core module.
    """
    if match_df.empty:
        return match_df

    out = match_df.copy()
    t2_records: list[dict] = []

    for _, row in match_df.iterrows():
        match_ts = pd.to_datetime(row["MatchDate"])
        idx_list = coded_df.index[coded_df["Date"] == match_ts].tolist()

        if not idx_list:
            t2_records.append({})
            continue

        t2_idx = idx_list[0] + 2           # two rows after MatchDate = T+2
        if t2_idx >= len(coded_df):
            t2_records.append({})           # T+2 missing — will become NaN
            continue

        t2       = coded_df.iloc[t2_idx]
        t1_close = float(row["NextClose"])  # T+2 open change is vs T+1 close
        t2_open  = float(t2["Open"])
        t2_close = float(t2["Close"])

        t2_records.append({
            "T2Date":       t2["Date"].strftime("%Y-%m-%d"),
            "T2Open":       t2_open,
            "T2High":       float(t2["High"]),
            "T2Low":        float(t2["Low"]),
            "T2Close":      t2_close,
            "T2Volume":     float(t2["Volume"]),
            "T2OpenChange": (t2_open  - t1_close) / t1_close,
            "T2CloseMove":  (t2_close - t2_open)  / t2_open,
        })

    t2_df = pd.DataFrame(t2_records, index=out.index)
    return pd.concat([out, t2_df], axis=1)


def enrich_with_match_ohlcv(match_df: pd.DataFrame, coded_df: pd.DataFrame) -> pd.DataFrame:
    """
    Append the match day's own OHLCV (MatchOpen/High/Low/Close/Volume) to every row.
    Rows whose MatchDate is not found in coded_df (should not happen in practice)
    produce NaN for all added columns.
    Does not touch any core module.
    """
    if match_df.empty:
        return match_df

    out = match_df.copy()
    records: list[dict] = []

    for _, row in match_df.iterrows():
        match_ts = pd.to_datetime(row["MatchDate"])
        idx_list = coded_df.index[coded_df["Date"] == match_ts].tolist()

        if not idx_list:
            records.append({})
            continue

        m = coded_df.iloc[idx_list[0]]
        records.append({
            "MatchOpen":   float(m["Open"]),
            "MatchHigh":   float(m["High"]),
            "MatchLow":    float(m["Low"]),
            "MatchClose":  float(m["Close"]),
            "MatchVolume": float(m["Volume"]),
        })

    enrich_df = pd.DataFrame(records, index=out.index)
    return pd.concat([out, enrich_df], axis=1)


def add_turnovers(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add trading-value columns (Close × Volume) for MatchDate, T+1, and T+2.
    Turnover here = price × volume (total dollar value traded that day).
    Silently skips any pair whose source columns are absent or all-NaN.
    """
    out = df.copy()
    for close_col, vol_col, new_col in [
        ("MatchClose", "MatchVolume", "MatchTurnover"),
        ("NextClose",  "NextVolume",  "NextTurnover"),
        ("T2Close",    "T2Volume",    "T2Turnover"),
    ]:
        if close_col in out.columns and vol_col in out.columns:
            out[new_col] = out[close_col] * out[vol_col]
    return out


def add_pattern_labels(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add T+1 and T+2 pattern label columns to a match result df.
    T+1: 次日开盘类型 / 次日日内结构 / 次日收盘方向
    T+2: T2结构 / T2收盘方向   (uses T2OpenChange + T2CloseMove if present)
    """
    out = df.copy()
    if out.empty:
        for col in ("次日开盘类型", "次日日内结构", "次日收盘方向", "T2结构", "T2收盘方向"):
            out[col] = pd.Series(dtype="object")
        return out

    def _safe_open(v):
        try:
            return _classify_open(float(v))
        except Exception:
            return "—"

    def _safe_structure(oc_col: str, cm_col: str):
        def _apply(row):
            try:
                return _classify_structure(float(row[oc_col]), float(row[cm_col]))
            except Exception:
                return "—"
        return _apply

    def _safe_close(v):
        try:
            return _classify_close(float(v))
        except Exception:
            return "—"

    # T+1 labels
    out["次日开盘类型"] = out["NextOpenChange"].map(_safe_open)
    out["次日日内结构"] = out.apply(_safe_structure("NextOpenChange", "NextCloseMove"), axis=1)
    out["次日收盘方向"] = out["NextCloseMove"].map(_safe_close)

    # T+2 labels (only when T2 columns have been added by enrich_with_t2)
    if "T2OpenChange" in out.columns and "T2CloseMove" in out.columns:
        out["T2结构"]   = out.apply(_safe_structure("T2OpenChange", "T2CloseMove"), axis=1)
        out["T2收盘方向"] = out["T2CloseMove"].map(_safe_close)
    else:
        out["T2结构"]   = "—"
        out["T2收盘方向"] = "—"

    return out


# ─────────────────────────────────────────────────────────────────────────────
# Position feature helpers (app-layer only — no core module changes)
# ─────────────────────────────────────────────────────────────────────────────

def compute_position_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute rolling price-position metrics for every row in coded_df.

    Pos15 / Pos30  — where Close sits within the N-day High/Low range, 0–100.
    NearHigh30     — Close is within 3 % of the 30-day rolling high.
    NearLow30      — Close is within 3 % of the 30-day rolling low.
    Rebound30      — how far Close has recovered above the 30-day rolling low (%).
    PosLabel       — categorical bucket: 低位 (<33) / 中位 (33–66) / 高位 (≥67).

    Returns a dataframe with Date + position columns only.
    All percentage values stored on a 0–100 scale for direct display.
    """
    high  = df["High"].astype(float)
    low   = df["Low"].astype(float)
    close = df["Close"].astype(float)

    out = df[["Date"]].copy()

    for n, suffix in [(15, "15"), (30, "30")]:
        roll_high = high.rolling(n).max()
        roll_low  = low.rolling(n).min()
        rng = roll_high - roll_low
        pos = (close - roll_low) / rng.where(rng > 0)   # NaN when flat range
        out[f"Pos{suffix}"] = (pos * 100).round(1)

    roll_high30 = high.rolling(30).max()
    roll_low30  = low.rolling(30).min()

    out["NearHigh30"] = (close >= roll_high30 * 0.97).fillna(False)
    out["NearLow30"]  = (close <= roll_low30  * 1.03).fillna(False)
    out["Rebound30"]  = ((close - roll_low30) / roll_low30 * 100).round(2)

    def _label(p: float) -> str:
        if pd.isna(p):
            return "—"
        if p < 33:
            return "低位"
        if p >= 67:
            return "高位"
        return "中位"

    out["PosLabel"] = out["Pos30"].apply(_label)
    return out


def enrich_with_position(match_df: pd.DataFrame, pos_df: pd.DataFrame) -> pd.DataFrame:
    """
    Join Pos15, Pos30, PosLabel from pos_df onto each match row by MatchDate.
    Columns are prefixed with 'Match' so they don't collide with target-day fields.
    """
    if match_df.empty:
        return match_df

    lookup = pos_df.set_index("Date")[["Pos15", "Pos30", "PosLabel"]]
    out = match_df.copy()
    match_dates = pd.to_datetime(out["MatchDate"])

    out["MatchPos15"]    = match_dates.map(lookup["Pos15"])
    out["MatchPos30"]    = match_dates.map(lookup["Pos30"])
    out["MatchPosLabel"] = match_dates.map(lookup["PosLabel"]).fillna("—")
    return out


def compute_prev_day_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    For every row in coded_df, capture summary features of the *previous* trading row.
    The returned frame is keyed by Date (current day) so it can be joined
    onto any match table via MatchDate, or looked up for the target date.

    PrevDate       — calendar date of the prior trading day
    PrevCode       — 5-digit code of the prior day
    PrevOpenType   — 高开 / 低开 / 平开 (classified from O_gap)
    PrevStructure  — intraday structure label (高开高走 etc.)
    PrevCloseDir   — 收涨 / 收跌 / 平收 (classified from C_move)
    PrevCloseMove  — C_move of prior day as a percentage (e.g. 1.23 = +1.23%)
    PrevVolume     — Volume of prior day
    PrevTurnover   — Close × Volume of prior day
    PrevVRatio     — V_ratio of prior day (volume vs 20-day average)
    """
    out = df[["Date"]].copy()

    # Shift raw OHLCV / feature columns by one row
    prev_close   = df["Close"].shift(1)
    prev_volume  = df["Volume"].shift(1)
    prev_o_gap   = df["O_gap"].shift(1)   if "O_gap"   in df.columns else None
    prev_c_move  = df["C_move"].shift(1)  if "C_move"  in df.columns else None
    prev_v_ratio = df["V_ratio"].shift(1) if "V_ratio" in df.columns else None
    prev_code    = df["Code"].shift(1)    if "Code"    in df.columns else None

    # Date as formatted string so it displays consistently with MatchDate
    out["PrevDate"]    = df["Date"].shift(1).dt.strftime("%Y-%m-%d").fillna("—")
    if prev_code is not None:
        out["PrevCode"] = prev_code.fillna("—")

    out["PrevVolume"]   = prev_volume
    out["PrevTurnover"] = prev_close * prev_volume

    if prev_c_move is not None:
        out["PrevCloseMove"] = (prev_c_move * 100).round(2)   # stored as % units

    if prev_v_ratio is not None:
        out["PrevVRatio"] = prev_v_ratio.round(3)

    # Pattern labels — reuse existing classifiers
    def _safe_open(v):
        try:
            return _classify_open(float(v))
        except Exception:
            return "—"

    def _safe_close(v):
        try:
            return _classify_close(float(v))
        except Exception:
            return "—"

    def _safe_structure(o, c):
        try:
            return _classify_structure(float(o), float(c))
        except Exception:
            return "—"

    if prev_o_gap is not None:
        out["PrevOpenType"] = prev_o_gap.apply(_safe_open)
    if prev_c_move is not None:
        out["PrevCloseDir"] = prev_c_move.apply(_safe_close)
    if prev_o_gap is not None and prev_c_move is not None:
        out["PrevStructure"] = pd.Series(
            [_safe_structure(o, c) for o, c in zip(prev_o_gap, prev_c_move)],
            index=df.index,
        )

    return out


def enrich_with_prev_day(match_df: pd.DataFrame, prev_df: pd.DataFrame) -> pd.DataFrame:
    """
    Join previous-day features from prev_df onto each match row by MatchDate.
    All added columns are prefixed with 'Match' for consistency with other enrichments.
    """
    if match_df.empty:
        return match_df

    prev_cols = [c for c in [
        "PrevDate", "PrevCode", "PrevOpenType", "PrevStructure",
        "PrevCloseDir", "PrevCloseMove", "PrevVolume", "PrevTurnover", "PrevVRatio",
    ] if c in prev_df.columns]

    lookup = prev_df.set_index("Date")[prev_cols]
    out = match_df.copy()
    match_dates = pd.to_datetime(out["MatchDate"])

    for col in prev_cols:
        out[f"Match{col}"] = match_dates.map(lookup[col])

    return out


def classify_stage(
    pos30: float,
    ret3: float,
    ret5: float,
    vol5_ratio: float,
    vol_expanding: bool,
) -> str:
    """
    Transparent rule-based momentum / stage classifier.
    Rules are evaluated in strict priority order; first match wins.

    Inputs (all required — returns '—' if any are NaN):
      pos30        : 0–100, where Close sits in the 30-day High/Low range
      ret3         : 3-day price return in percent
      ret5         : 5-day price return in percent
      vol5_ratio   : today's Volume / 5-day average volume
      vol_expanding: True when today's Volume > yesterday's Volume

    Stage assignment rules:
      衰竭风险  pos30 ≥ 70 AND ret3 < −2.0
               OR pos30 ≥ 75 AND ret5 < −1.5
      分歧      pos30 ≥ 65 AND NOT vol_expanding AND |ret3| < 2.0
               OR pos30 ≥ 60 AND ret5 > 0 AND vol5_ratio < 0.85
      加速      ret3 ≥ 4.0 AND vol5_ratio ≥ 1.2
               OR ret5 ≥ 7.0 AND vol5_ratio ≥ 1.15 AND vol_expanding
      启动      pos30 < 35 AND ret3 ≥ 1.5 AND vol_expanding AND vol5_ratio ≥ 1.0
               OR pos30 < 40 AND ret5 ≥ 2.5 AND vol5_ratio ≥ 1.1
      整理      |ret5| < 2.0 AND vol5_ratio < 0.90
               OR |ret3| < 1.0 AND |ret5| < 3.0
      延续      ret5 ≥ 0   (default positive-trend fallback)
      整理      default    (mild negative drift, no other rule fired)
    """
    if any(pd.isna(x) for x in [pos30, ret3, ret5, vol5_ratio]):
        return "—"

    # 1. 衰竭风险 — high position + price rolling over
    if pos30 >= 70 and ret3 < -2.0:
        return "衰竭风险"
    if pos30 >= 75 and ret5 < -1.5:
        return "衰竭风险"

    # 2. 分歧 — price/volume divergence near highs
    if pos30 >= 65 and (not vol_expanding) and abs(ret3) < 2.0:
        return "分歧"
    if pos30 >= 60 and ret5 > 0 and vol5_ratio < 0.85:
        return "分歧"

    # 3. 加速 — strong momentum + above-average expanding volume
    if ret3 >= 4.0 and vol5_ratio >= 1.2:
        return "加速"
    if ret5 >= 7.0 and vol5_ratio >= 1.15 and vol_expanding:
        return "加速"

    # 4. 启动 — low base breakout with rising volume
    if pos30 < 35 and ret3 >= 1.5 and vol_expanding and vol5_ratio >= 1.0:
        return "启动"
    if pos30 < 40 and ret5 >= 2.5 and vol5_ratio >= 1.1:
        return "启动"

    # 5. 整理 — sideways or low-energy pause
    if abs(ret5) < 2.0 and vol5_ratio < 0.90:
        return "整理"
    if abs(ret3) < 1.0 and abs(ret5) < 3.0:
        return "整理"

    # 6. 延续 — positive drift, no special condition triggered
    if ret5 >= 0:
        return "延续"

    # Default
    return "整理"


def compute_momentum_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute rolling momentum / stage metrics for every row in coded_df.

    Ret3 / Ret5 / Ret10  — multi-day price returns in percent (vs N days ago Close)
    Vol5Ratio            — today's Volume / 5-day trailing average Volume (shift-1)
    VolExpanding         — True when today's Volume > yesterday's Volume
    StageLabel           — rule-based stage from classify_stage()

    Pos30 is recomputed internally (same formula as compute_position_features)
    so this function has no dependency on pos_df.
    All percentage values stored as percent units (e.g. 1.23 for +1.23%).
    """
    close  = df["Close"].astype(float)
    high   = df["High"].astype(float)
    low    = df["Low"].astype(float)
    volume = df["Volume"].astype(float)

    out = df[["Date"]].copy()

    # Multi-day price returns
    for n, label in [(3, "3"), (5, "5"), (10, "10")]:
        out[f"Ret{label}"] = ((close / close.shift(n) - 1) * 100).round(2)

    # Volume vs 5-day trailing average (excluding today — shift first, then roll)
    vol5_ma = volume.shift(1).rolling(5).mean()
    out["Vol5Ratio"]   = (volume / vol5_ma).round(3)
    out["VolExpanding"] = volume > volume.shift(1)

    # Pos30 recomputed inline for stage classification
    roll_high30 = high.rolling(30).max()
    roll_low30  = low.rolling(30).min()
    rng30 = roll_high30 - roll_low30
    pos30_ser = (close - roll_low30) / rng30.where(rng30 > 0) * 100

    # Stage label — apply classify_stage row-by-row via a combined frame
    stage_inputs = pd.DataFrame({
        "pos30":   pos30_ser,
        "ret3":    out["Ret3"],
        "ret5":    out["Ret5"],
        "vol5r":   out["Vol5Ratio"],
        "volexp":  out["VolExpanding"],
    })

    def _classify_row(r: pd.Series) -> str:
        return classify_stage(
            r["pos30"], r["ret3"], r["ret5"], r["vol5r"],
            bool(r["volexp"]) if pd.notna(r["volexp"]) else False,
        )

    out["StageLabel"] = stage_inputs.apply(_classify_row, axis=1)
    return out


def enrich_with_momentum(match_df: pd.DataFrame, mom_df: pd.DataFrame) -> pd.DataFrame:
    """
    Join momentum / stage features from mom_df onto each match row by MatchDate.
    MatchVolState converts the raw VolExpanding bool to a readable '量增'/'量缩' label.
    """
    if match_df.empty:
        return match_df

    mom_cols = [c for c in [
        "Ret3", "Ret5", "Ret10", "Vol5Ratio", "VolExpanding", "StageLabel",
    ] if c in mom_df.columns]

    lookup = mom_df.set_index("Date")[mom_cols]
    out = match_df.copy()
    match_dates = pd.to_datetime(out["MatchDate"])

    for col in mom_cols:
        out[f"Match{col}"] = match_dates.map(lookup[col])

    # Convert bool VolExpanding → readable string
    if "MatchVolExpanding" in out.columns:
        out["MatchVolState"] = out["MatchVolExpanding"].apply(
            lambda v: "量增" if (pd.notna(v) and bool(v)) else ("量缩" if pd.notna(v) else "—")
        )
        out = out.drop(columns=["MatchVolExpanding"])

    return out


def get_target_context(
    target_date_str: str,
    pos_df: pd.DataFrame,
    prev_df: pd.DataFrame,
    mom_df: pd.DataFrame,
) -> dict:
    """
    Extract the target day's context features for use in compute_context_scores.
    Returns a dict with keys: pos30, pos_label, prev_structure, prev_open_type,
    prev_close_dir, stage_label, ret3, ret5.  Missing values are stored as None.
    """
    target_ts = pd.to_datetime(target_date_str)
    ctx: dict = {}

    if not pos_df.empty:
        pr = pos_df[pos_df["Date"] == target_ts]
        if not pr.empty:
            row = pr.iloc[0]
            ctx["pos30"]     = float(row["Pos30"])  if pd.notna(row.get("Pos30"))    else None
            ctx["pos_label"] = str(row["PosLabel"]) if pd.notna(row.get("PosLabel")) else None

    if not prev_df.empty:
        pr2 = prev_df[prev_df["Date"] == target_ts]
        if not pr2.empty:
            row2 = pr2.iloc[0]
            ctx["prev_structure"] = str(row2["PrevStructure"]) if pd.notna(row2.get("PrevStructure")) else None
            ctx["prev_open_type"] = str(row2["PrevOpenType"])  if pd.notna(row2.get("PrevOpenType"))  else None
            ctx["prev_close_dir"] = str(row2["PrevCloseDir"])  if pd.notna(row2.get("PrevCloseDir"))  else None

    if not mom_df.empty:
        pr3 = mom_df[mom_df["Date"] == target_ts]
        if not pr3.empty:
            row3 = pr3.iloc[0]
            ctx["stage_label"] = str(row3["StageLabel"]) if pd.notna(row3.get("StageLabel")) else None
            ctx["ret3"]        = float(row3["Ret3"])      if pd.notna(row3.get("Ret3"))       else None
            ctx["ret5"]        = float(row3["Ret5"])      if pd.notna(row3.get("Ret5"))       else None

    return ctx


def compute_context_scores(match_df: pd.DataFrame, target_ctx: dict) -> pd.DataFrame:
    """
    Score each matched sample by contextual similarity to the target day.
    Adds ContextScore (0–100) and ContextLabel (高相似/中相似/低相似) columns.
    Sorts descending by ContextScore.

    Scoring dimensions (max 100 pts total):
      Position proximity   30 pts  max(0, 30 − 2 × |MatchPos30 − target_pos30|)
      Position label       10 pts  exact label match
      Prev-day structure   20 pts  exact=20, same open type=10, else 0
      Prev-day close dir   10 pts  exact match
      Stage label          20 pts  exact=20, same _STAGE_ADJACENCY group=10, else 0
      Ret3 proximity        5 pts  |diff|<1%→5, <2%→3, <4%→1
      Ret5 proximity        5 pts  same scale
    """
    if match_df.empty:
        return match_df

    out = match_df.copy()
    scores: list[float] = []

    t_pos30       = target_ctx.get("pos30")
    t_pos_label   = target_ctx.get("pos_label")
    t_prev_struct = target_ctx.get("prev_structure")
    t_prev_open   = target_ctx.get("prev_open_type")
    t_prev_close  = target_ctx.get("prev_close_dir")
    t_stage       = target_ctx.get("stage_label")
    t_ret3        = target_ctx.get("ret3")
    t_ret5        = target_ctx.get("ret5")

    for _, row in out.iterrows():
        score = 0.0

        # 1. Position proximity (0–30 pts)
        m_pos30 = row.get("MatchPos30")
        if t_pos30 is not None and pd.notna(m_pos30):
            score += max(0.0, 30.0 - 2.0 * abs(float(m_pos30) - t_pos30))

        # 2. Position label exact match (+10 pts)
        m_pos_label = str(row.get("MatchPosLabel", "—"))
        if t_pos_label and m_pos_label == t_pos_label:
            score += 10.0

        # 3. Prev-day structure (0–20 pts)
        m_prev_struct = str(row.get("MatchPrevStructure", "—"))
        if t_prev_struct and t_prev_struct not in ("—", "nan"):
            if m_prev_struct == t_prev_struct:
                score += 20.0
            elif t_prev_open and str(row.get("MatchPrevOpenType", "—")) == t_prev_open:
                score += 10.0

        # 4. Prev-day close direction (0–10 pts)
        m_prev_close = str(row.get("MatchPrevCloseDir", "—"))
        if t_prev_close and t_prev_close not in ("—", "nan") and m_prev_close == t_prev_close:
            score += 10.0

        # 5. Stage label (0–20 pts)
        m_stage = str(row.get("MatchStageLabel", "—"))
        if t_stage and t_stage not in ("—", "nan"):
            if m_stage == t_stage:
                score += 20.0
            elif (
                _STAGE_ADJACENCY.get(m_stage) is not None
                and _STAGE_ADJACENCY.get(m_stage) == _STAGE_ADJACENCY.get(t_stage)
            ):
                score += 10.0

        # 6. Ret3 proximity (0–5 pts)
        m_ret3 = row.get("MatchRet3")
        if t_ret3 is not None and pd.notna(m_ret3):
            diff3 = abs(float(m_ret3) - t_ret3)
            if diff3 < 1.0:
                score += 5.0
            elif diff3 < 2.0:
                score += 3.0
            elif diff3 < 4.0:
                score += 1.0

        # 7. Ret5 proximity (0–5 pts)
        m_ret5 = row.get("MatchRet5")
        if t_ret5 is not None and pd.notna(m_ret5):
            diff5 = abs(float(m_ret5) - t_ret5)
            if diff5 < 1.0:
                score += 5.0
            elif diff5 < 2.0:
                score += 3.0
            elif diff5 < 4.0:
                score += 1.0

        scores.append(round(score, 1))

    out["ContextScore"] = scores
    out["ContextLabel"] = out["ContextScore"].apply(
        lambda s: "高相似" if s >= 65 else ("中相似" if s >= 35 else "低相似")
    )
    out = out.sort_values("ContextScore", ascending=False).reset_index(drop=True)
    return out


def apply_context_filter(df: pd.DataFrame, ctx_filter: str) -> pd.DataFrame:
    """
    Filter a match result dataframe by ContextLabel.
    Stacks on top of any position filter already applied.

    ctx_filter options:
      '全部相似度'   — return df unchanged
      '仅高相似'     — keep rows where ContextLabel == '高相似'  (score ≥ 65)
      '仅高+中相似'  — keep rows where ContextLabel in ['高相似', '中相似']  (score ≥ 35)
    """
    if df.empty or ctx_filter == "全部相似度" or "ContextLabel" not in df.columns:
        return df
    if ctx_filter == "仅高相似":
        return df[df["ContextLabel"] == "高相似"].reset_index(drop=True)
    if ctx_filter == "仅高+中相似":
        return df[df["ContextLabel"].isin(["高相似", "中相似"])].reset_index(drop=True)
    return df


def apply_position_filter(
    df: pd.DataFrame,
    pos_filter: str,
    target_pos30: float | None,
    tolerance: float = 15.0,
) -> pd.DataFrame:
    """
    Post-processing filter applied to an already-generated match result dataframe.
    The underlying match algorithm (matcher.py) is never touched.

    pos_filter options and their exact rules:
      '全部样本'             — return df unchanged
      '仅低位 (<33%)'       — keep rows where MatchPosLabel == '低位'
      '仅中位 (33–67%)'     — keep rows where MatchPosLabel == '中位'
      '仅高位 (≥67%)'       — keep rows where MatchPosLabel == '高位'
      '仅位置相近 (±15%)'   — keep rows where |MatchPos30 − target_pos30| ≤ tolerance

    Rows missing MatchPosLabel / MatchPos30 are dropped in all non-'全部样本' modes.
    Returns a new dataframe (original is never mutated).
    """
    if df.empty or pos_filter == "全部样本":
        return df

    if "MatchPosLabel" not in df.columns:
        return df

    if pos_filter == "仅低位 (<33%)":
        mask = df["MatchPosLabel"] == "低位"
    elif pos_filter == "仅中位 (33–67%)":
        mask = df["MatchPosLabel"] == "中位"
    elif pos_filter == "仅高位 (≥67%)":
        mask = df["MatchPosLabel"] == "高位"
    elif pos_filter == "仅位置相近 (±15%)":
        if "MatchPos30" not in df.columns or target_pos30 is None:
            return df
        mask = (df["MatchPos30"] - target_pos30).abs() <= tolerance
    else:
        return df

    return df[mask].reset_index(drop=True)


# ─────────────────────────────────────────────────────────────────────────────
# Visualization helpers
# ─────────────────────────────────────────────────────────────────────────────

def render_pattern_bar_chart(df: pd.DataFrame) -> None:
    """Render a horizontal bar chart of 次日日内结构 counts."""
    if df.empty or "次日日内结构" not in df.columns:
        return
    raw_counts = df["次日日内结构"].value_counts()
    counts = pd.Series({k: int(raw_counts.get(k, 0)) for k in STRUCTURE_ORDER})

    fig, ax = plt.subplots(figsize=(5, 2.2))
    colors = [_STRUCTURE_COLORS.get(k, "#aaa") for k in counts.index]
    bars = ax.barh(counts.index, counts.values, color=colors, height=0.55)
    ax.bar_label(bars, padding=4, fontsize=9)
    ax.set_xlabel("次数", fontsize=9)
    ax.set_xlim(0, max(counts.max() * 1.35, 2))
    ax.invert_yaxis()
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(labelsize=9)
    fig.tight_layout(pad=0.4)
    st.pyplot(fig, use_container_width=False)
    plt.close(fig)


def get_ohlc_window(
    coded_df: pd.DataFrame,
    match_date_str: str,
    before: int = 3,
    after: int = 2,
) -> pd.DataFrame:
    """
    Return a slice of coded_df centered on match_date_str.
    Window = `before` rows before MatchDate, MatchDate itself,
    NextDate (match+1), then `after` more rows.
    """
    match_ts = pd.to_datetime(match_date_str)
    idx_list = coded_df.index[coded_df["Date"] == match_ts].tolist()
    if not idx_list:
        return pd.DataFrame()
    match_idx = idx_list[0]
    start = max(0, match_idx - before)
    end   = min(len(coded_df) - 1, match_idx + 1 + after)  # +1 so NextDate is always included
    return coded_df.iloc[start: end + 1].reset_index(drop=True)


def make_candlestick_fig(
    window_df: pd.DataFrame,
    match_date_str: str,
    next_date_str: str,
    structure_label: str,
    t2_date_str: str | None = None,
    t2_structure_label: str | None = None,
) -> plt.Figure | None:
    """
    Draw a dark-themed candlestick chart for the OHLC window around match_date.
    - Amber  column = MatchDate   (▼ x-label)
    - Blue   column = T+1 date   (★ x-label)
    - Purple column = T+2 date   (◆ x-label)  — shown when t2_date_str is provided
    Returns None when window_df is empty.
    """
    if window_df.empty:
        return None

    match_ts = pd.to_datetime(match_date_str)
    next_ts  = pd.to_datetime(next_date_str)  if next_date_str  else None
    t2_ts    = pd.to_datetime(t2_date_str)    if t2_date_str    else None

    # ── theme colours ────────────────────────────────────────────────────────
    BG        = "#0e1117"
    AX_BG     = "#131722"
    UP_COL    = "#26a69a"    # teal-green
    DN_COL    = "#ef5350"    # soft red
    TEXT_COL  = "#b0b0c0"
    GRID_COL  = "#1e2030"
    SPINE_COL = "#2a2a3a"
    BODY_W    = 0.55

    n = len(window_df)
    fig_w = max(3.6, n * 0.68)
    fig, ax = plt.subplots(figsize=(fig_w, 2.6))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(AX_BG)

    # Map Date → x position
    date_to_x: dict[pd.Timestamp, int] = {
        row["Date"]: i for i, (_, row) in enumerate(window_df.iterrows())
    }

    # ── highlight bands (drawn first, behind candles) ────────────────────────
    if match_ts in date_to_x:
        mx = date_to_x[match_ts]
        ax.axvspan(mx - 0.5, mx + 0.5, color="#f39c12", alpha=0.13, zorder=0)
    if next_ts and next_ts in date_to_x:
        nx = date_to_x[next_ts]
        ax.axvspan(nx - 0.5, nx + 0.5, color="#3498db", alpha=0.13, zorder=0)
    if t2_ts and t2_ts in date_to_x:
        t2x = date_to_x[t2_ts]
        ax.axvspan(t2x - 0.5, t2x + 0.5, color="#9b59b6", alpha=0.13, zorder=0)

    # ── candles ──────────────────────────────────────────────────────────────
    for i, (_, row) in enumerate(window_df.iterrows()):
        o = float(row["Open"])
        h = float(row["High"])
        l = float(row["Low"])
        c = float(row["Close"])
        color    = UP_COL if c >= o else DN_COL
        body_bot = min(o, c)
        body_top = max(o, c)
        # Guarantee a minimum visible body height (doji candle)
        if body_top <= body_bot:
            body_top = body_bot + (h - l) * 0.02 + 0.01

        ax.vlines(i, l, h, color=color, linewidth=1.0, zorder=2)
        ax.add_patch(plt.Rectangle(
            (i - BODY_W / 2, body_bot),
            BODY_W,
            body_top - body_bot,
            color=color,
            zorder=3,
        ))

    # ── x-axis: compact date labels ──────────────────────────────────────────
    x_labels = []
    for _, row in window_df.iterrows():
        d     = row["Date"]
        label = d.strftime("%m/%d")
        if d == match_ts:
            label = f"▼{label}"
        elif next_ts and d == next_ts:
            label = f"★{label}"
        elif t2_ts and d == t2_ts:
            label = f"◆{label}"
        x_labels.append(label)

    ax.set_xticks(range(n))
    ax.set_xticklabels(x_labels, fontsize=6.5, color=TEXT_COL)
    ax.set_xlim(-0.6, n - 0.4)

    # ── y-axis ───────────────────────────────────────────────────────────────
    lows  = window_df["Low"].astype(float)
    highs = window_df["High"].astype(float)
    pad   = (highs.max() - lows.min()) * 0.06
    ax.set_ylim(lows.min() - pad, highs.max() + pad)
    ax.tick_params(axis="y", labelsize=6.5, labelcolor=TEXT_COL, length=2)
    ax.yaxis.set_major_locator(mticker.MaxNLocator(4, integer=False))

    # ── grid & spines ────────────────────────────────────────────────────────
    ax.yaxis.grid(True, color=GRID_COL, linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_color(SPINE_COL)
    ax.tick_params(axis="x", color=SPINE_COL)

    # ── title: match date on the left; T+1 and T+2 structure badges on the right ──
    ax.set_title(
        f"{match_date_str}",
        fontsize=7.5,
        color=TEXT_COL,
        pad=4,
        loc="left",
    )
    t1_color = _STRUCTURE_COLORS.get(structure_label,    "#888888")
    t2_color = _STRUCTURE_COLORS.get(t2_structure_label, "#888888") if t2_structure_label else "#888888"

    # Build right-side annotation: "T+1 高开高走  T+2 低开低走"
    t2_part = f"  T+2 {t2_structure_label}" if t2_structure_label and t2_structure_label != "—" else ""
    ax.annotate(
        f"T+1 {structure_label}{t2_part}",
        xy=(1.0, 1.02),
        xycoords="axes fraction",
        ha="right",
        va="bottom",
        fontsize=7.0,
        color=t1_color,
        fontweight="bold",
    )

    fig.tight_layout(pad=0.35)
    return fig


def render_mini_cards(
    df: pd.DataFrame,
    coded_df: pd.DataFrame,
    cols_per_row: int = 3,
) -> None:
    """Render one candlestick card per matched sample, arranged in a grid."""
    if df.empty:
        return

    rows_list = list(df.iterrows())
    for batch_start in range(0, len(rows_list), cols_per_row):
        batch = rows_list[batch_start: batch_start + cols_per_row]
        cols  = st.columns(len(batch))
        for col, (_, row) in zip(cols, batch):
            with col:
                match_date   = str(row.get("MatchDate",      ""))
                next_date    = str(row.get("NextDate",       ""))
                match_code   = str(row.get("MatchCode",      ""))
                t2_date      = str(row.get("T2Date",    "")) or None
                structure    = str(row.get("次日日内结构",     "—"))
                t2_struct    = str(row.get("T2结构",          "—"))
                vcode_diff   = row.get("VCodeDiff",   None)
                stage_label  = str(row.get("MatchStageLabel", "—"))
                pos_label    = str(row.get("MatchPosLabel",   "—"))
                ret5_val     = row.get("MatchRet5",    None)
                ctx_label    = str(row.get("ContextLabel",    ""))
                ctx_score    = row.get("ContextScore",  None)

                # ContextScore badge + left border colour highlight
                if ctx_score is not None and pd.notna(ctx_score):
                    if ctx_label == "高相似":
                        _cl_color, _cl_bg = "#f1c40f", "#f1c40f22"
                    elif ctx_label == "中相似":
                        _cl_color, _cl_bg = "#2ecc71", "#2ecc7122"
                    else:
                        _cl_color, _cl_bg = "#888888", "#88888811"
                    st.markdown(
                        f'<div style="border-left:3px solid {_cl_color};'
                        f'background:{_cl_bg};padding:1px 5px;margin-bottom:2px;border-radius:0 3px 3px 0">'
                        f'<span style="color:{_cl_color};font-weight:bold;font-size:0.75em">'
                        f'{ctx_label}  {int(ctx_score)}分</span></div>',
                        unsafe_allow_html=True,
                    )

                # Compact caption: code + optional VCodeDiff
                caption_parts = [f"`{match_code}`"]
                if vcode_diff is not None and pd.notna(vcode_diff):
                    caption_parts.append(f"VDiff={int(vcode_diff)}")
                st.caption("  ".join(caption_parts))

                # Stage badge  |  position label  |  5-day return
                _sc  = _STAGE_COLORS.get(stage_label, "#888888")
                _plc = {"低位": "#3498db", "中位": "#f39c12", "高位": "#e74c3c"}.get(pos_label, "#888888")
                _r5  = f" {ret5_val:+.1f}%" if (ret5_val is not None and pd.notna(ret5_val)) else ""
                st.markdown(
                    f'<span style="background:{_sc}22;color:{_sc};font-weight:bold;'
                    f'padding:1px 5px;border-radius:3px;font-size:0.78em">{stage_label}</span>'
                    f' <span style="color:{_plc};font-size:0.78em">{pos_label}</span>'
                    f'<span style="color:#888888;font-size:0.78em">{_r5}</span>',
                    unsafe_allow_html=True,
                )

                # T+1 / T+2 structure badges on one line
                t1_color = _STRUCTURE_COLORS.get(structure, "#888888")
                t2_color = _STRUCTURE_COLORS.get(t2_struct, "#888888")
                t2_html  = (
                    f'  <span style="color:#9b59b6">◆</span>'
                    f'<span style="color:{t2_color};font-weight:bold"> {t2_struct}</span>'
                    if t2_date else ""
                )
                st.markdown(
                    f'<span style="color:#3498db">★</span>'
                    f'<span style="color:{t1_color};font-weight:bold"> {structure}</span>'
                    f'{t2_html}',
                    unsafe_allow_html=True,
                )

                # Candlestick chart — window includes T+2 via after=2
                window = get_ohlc_window(coded_df, match_date, before=3, after=2)
                fig = make_candlestick_fig(
                    window, match_date, next_date, structure,
                    t2_date_str=t2_date,
                    t2_structure_label=t2_struct if t2_date else None,
                )
                if fig is not None:
                    st.pyplot(fig, use_container_width=True)
                    plt.close(fig)
                else:
                    st.caption("图表数据缺失")


# ─────────────────────────────────────────────────────────────────────────────
# General helpers
# ─────────────────────────────────────────────────────────────────────────────

def fmt_pct(val: object, decimals: int = 2) -> str:
    """Format a raw ratio (e.g. 0.012) as a signed percentage string (+1.20%)."""
    try:
        return f"{float(val) * 100:+.{decimals}f}%"
    except (TypeError, ValueError):
        return "—"


def get_target_row(coded_df: pd.DataFrame, date_str: str) -> pd.Series | None:
    rows = coded_df[coded_df["Date"] == pd.to_datetime(date_str)]
    return rows.iloc[0] if not rows.empty else None


def _pick_cols(df: pd.DataFrame, wanted: list[str]) -> pd.DataFrame:
    """Return df with only the columns in `wanted` that actually exist."""
    return df[[c for c in wanted if c in df.columns]]


def _multiply_pct(df: pd.DataFrame) -> pd.DataFrame:
    """Multiply any PCT_MOVE_COLS present in df by 100 (in-place copy)."""
    out = df.copy()
    for col in PCT_MOVE_COLS:
        if col in out.columns:
            out[col] = out[col] * 100
    return out


def compute_inline_stats(df: pd.DataFrame) -> dict:
    """
    Compute next-day summary statistics directly from a match result dataframe.
    Used by the Stats Summary tab so it can react to the active position filter.

    The input df must contain the standard match columns produced by matcher.py
    (NextOpenChange, NextHighMove, NextLowMove, NextCloseMove) plus the T+2 and
    pattern-label columns added by the app-layer enrichment pipeline.

    Returns a plain dict whose keys mirror the SUMMARY_COLUMNS used by
    stats_reporter.summarize_match_df, plus three extra keys:
      'T1Structure'   — pd.Series of 次日日内结构 value counts (may be absent)
      'T2Structure'   — pd.Series of T2结构 value counts (may be absent)
      'AvgT2CloseMove'    — float (raw ratio, may be absent)
      'MedianT2CloseMove' — float (raw ratio, may be absent)
    """
    out: dict = {"SampleSize": 0, "DominantNextDayBias": "insufficient_sample"}
    if df.empty:
        return out

    # Ensure pattern-label columns exist (次日日内结构, T2结构, etc.)
    working = add_pattern_labels(df) if "次日日内结构" not in df.columns else df.copy()

    n = len(working)
    out["SampleSize"] = n

    def _mean(col: str) -> float:
        return working[col].mean() if col in working.columns else float("nan")

    def _median(col: str) -> float:
        return working[col].median() if col in working.columns else float("nan")

    def _rate(col: str, op, threshold: float) -> float:
        if col not in working.columns:
            return float("nan")
        return op(working[col], threshold).mean()

    # Open
    out["AvgNextOpenChange"]          = _mean("NextOpenChange")
    out["MedianNextOpenChange"]       = _median("NextOpenChange")
    out["PositiveNextOpenChangeRate"] = _rate("NextOpenChange", pd.Series.gt, 0)

    # High / Low
    out["AvgNextHighMove"]     = _mean("NextHighMove")
    out["MedianNextHighMove"]  = _median("NextHighMove")
    out["HighMoveOver1PctRate"] = _rate("NextHighMove", pd.Series.ge, 0.01)
    out["HighMoveOver2PctRate"] = _rate("NextHighMove", pd.Series.ge, 0.02)

    out["AvgNextLowMove"]    = _mean("NextLowMove")
    out["MedianNextLowMove"] = _median("NextLowMove")
    out["LowMoveOver1PctRate"] = _rate("NextLowMove", pd.Series.ge, 0.01)
    out["LowMoveOver2PctRate"] = _rate("NextLowMove", pd.Series.ge, 0.02)

    # Close
    out["AvgNextCloseMove"]          = _mean("NextCloseMove")
    out["MedianNextCloseMove"]       = _median("NextCloseMove")
    pos_close = _rate("NextCloseMove", pd.Series.gt, 0)
    neg_close = _rate("NextCloseMove", pd.Series.lt, 0)
    out["PositiveNextCloseMoveRate"] = pos_close
    out["NegativeNextCloseMoveRate"] = neg_close

    # Bias
    if n < 3:
        out["DominantNextDayBias"] = "insufficient_sample"
    elif not pd.isna(pos_close) and pos_close >= 0.6:
        out["DominantNextDayBias"] = "up_bias"
    elif not pd.isna(neg_close) and neg_close >= 0.6:
        out["DominantNextDayBias"] = "down_bias"
    else:
        out["DominantNextDayBias"] = "mixed"

    # T+1 structure distribution
    if "次日日内结构" in working.columns:
        out["T1Structure"] = working["次日日内结构"].value_counts()

    # T+2 stats
    if "T2CloseMove" in working.columns:
        out["AvgT2CloseMove"]    = _mean("T2CloseMove")
        out["MedianT2CloseMove"] = _median("T2CloseMove")
    if "T2结构" in working.columns:
        out["T2Structure"] = working["T2结构"].value_counts()

    return out


def _render_top_context_matches(df: pd.DataFrame, n: int = 5) -> None:
    """
    Show the top-n highest-scoring rows as a compact highlight table.
    Columns: MatchDate, ContextScore, ContextLabel, position, prev-day structure,
    stage, T+1 structure, T+2 structure.
    """
    if df.empty or "ContextScore" not in df.columns:
        return
    top = df.nlargest(n, "ContextScore")
    cols = [c for c in [
        "MatchDate", "ContextScore", "ContextLabel",
        "MatchPosLabel", "MatchPos30",
        "MatchPrevStructure", "MatchStageLabel",
        "次日日内结构", "T2结构",
    ] if c in top.columns]
    cfg = {k: v for k, v in COL_CONFIG.items() if k in cols}
    st.dataframe(top[cols], hide_index=True, use_container_width=True, column_config=cfg)


def _render_match_tables(
    df: pd.DataFrame,
    has_vcode_diff: bool = False,
    target_ctx: dict | None = None,
) -> None:
    """
    Render four focused sub-tabs for a match result dataframe.
    All tables share the same row order; MatchDate is the left anchor column
    in every sub-tab so rows visually align when switching between them.

      Sub-tab A  匹配日数据  — MatchDate OHLCV + position context + compact prev-day + forward labels
      Sub-tab B  次日 T+1   — T+1 full OHLCV + moves + structure
      Sub-tab C  后天 T+2   — T+2 full OHLCV + moves + structure
      Sub-tab D  前一日状态  — full previous-day OHLCV, code, structure, volume
    """
    # ── Pattern distribution bar chart (always visible, above sub-tabs) ──────
    st.markdown("**次日走势分布（T+1）**")
    render_pattern_bar_chart(df)

    # ── Context scoring explanation (shown only when scores are present) ──────
    if target_ctx and "ContextScore" in df.columns:
        with st.expander("📊 相似度评分说明"):
            t_pos30   = target_ctx.get("pos30")
            t_pl      = target_ctx.get("pos_label",      "—")
            t_ps      = target_ctx.get("prev_structure", "—")
            t_pc      = target_ctx.get("prev_close_dir", "—")
            t_stage   = target_ctx.get("stage_label",    "—")
            t_r3      = target_ctx.get("ret3")
            t_r5      = target_ctx.get("ret5")
            pos_str   = f"{t_pos30:.1f}%" if t_pos30 is not None else "—"
            r3_str    = f"{t_r3:+.2f}%" if t_r3 is not None else "—"
            r5_str    = f"{t_r5:+.2f}%" if t_r5 is not None else "—"
            st.caption(
                f"目标日：阶段={t_stage}　位置={t_pl}（{pos_str}）　"
                f"前日结构={t_ps}　前日收盘={t_pc}　Ret3={r3_str}　Ret5={r5_str}"
            )
            st.markdown(
                "| 维度 | 最高分 | 规则 |\n"
                "|---|---|---|\n"
                "| 30日位置接近度 | 30 | max(0, 30 − 2 × \\|MatchPos30 − 目标Pos30\\|) |\n"
                "| 位置标签一致 | 10 | 完全相同（低位/中位/高位）+10 |\n"
                "| 前一日结构 | 20 | 完全相同+20；开盘类型相同+10 |\n"
                "| 前一日收盘方向 | 10 | 完全相同+10 |\n"
                "| 阶段标签 | 20 | 完全相同+20；同组（动能/稳态/风险）+10 |\n"
                "| 3日涨跌接近度 | 5 | \\|差值\\|<1%→+5；<2%→+3；<4%→+1 |\n"
                "| 5日涨跌接近度 | 5 | 同上 |\n"
                "| **合计** | **100** | ≥65→高相似；≥35→中相似；<35→低相似 |"
            )

    # ── Four sub-tabs ─────────────────────────────────────────────────────────
    sub_a, sub_b, sub_c, sub_d = st.tabs(["匹配日数据", "次日 T+1", "后天 T+2", "前一日状态"])

    # ── Section A: 匹配日数据 ─────────────────────────────────────────────────
    with sub_a:
        st.caption(
            "匹配日（MatchDate）OHLCV、位置标签、前一日简况，以及 T+1 / T+2 走势标签。"
        )
        cols_a = ["MatchDate", "MatchCode"]
        if has_vcode_diff:
            cols_a.append("VCodeDiff")
        # Context similarity score near front for quick ranking
        cols_a += ["ContextScore", "ContextLabel"]
        # Stage + position context near front for quick scanning
        cols_a += ["MatchStageLabel", "MatchPosLabel", "MatchPos30"]
        # Compact momentum numbers
        cols_a += ["MatchRet3", "MatchRet5", "MatchVolState"]
        # Compact prev-day context
        cols_a += ["MatchPrevStructure", "MatchPrevCloseDir"]
        # Full OHLCV
        cols_a += [
            "MatchOpen", "MatchHigh", "MatchLow", "MatchClose",
            "MatchVolume", "MatchTurnover",
            "MatchPos15", "MatchVol5Ratio",
            "次日日内结构", "次日收盘方向",
            "T2结构",       "T2收盘方向",
        ]
        cfg_a = {k: v for k, v in COL_CONFIG.items() if k in cols_a}
        st.dataframe(
            _pick_cols(df, cols_a),
            hide_index=True,
            use_container_width=True,
            column_config=cfg_a,
        )

    # ── Section B: 次日 T+1 ──────────────────────────────────────────────────
    with sub_b:
        st.caption("T+1（次日）完整 OHLCV、涨跌幅及走势标签。")
        cols_b = [
            "MatchDate", "NextDate",
            "NextOpenChange", "NextCloseMove", "NextHighMove", "NextLowMove",
            "NextOpen", "NextHigh", "NextLow", "NextClose",
            "NextVolume", "NextTurnover",
            "次日开盘类型", "次日日内结构", "次日收盘方向",
        ]
        out_b = _multiply_pct(_pick_cols(df, cols_b))
        cfg_b = {k: v for k, v in COL_CONFIG.items() if k in out_b.columns}
        st.dataframe(out_b, hide_index=True, use_container_width=True, column_config=cfg_b)

    # ── Section C: 后天 T+2 ──────────────────────────────────────────────────
    with sub_c:
        st.caption(
            "T+2（后天）完整 OHLCV、涨跌幅及走势标签。"
            "T+2 开盘变动以 T+1 收盘价为基准。"
        )
        cols_c = [
            "MatchDate", "T2Date",
            "T2OpenChange", "T2CloseMove",
            "T2Open", "T2High", "T2Low", "T2Close",
            "T2Volume", "T2Turnover",
            "T2结构", "T2收盘方向",
        ]
        out_c = _multiply_pct(_pick_cols(df, cols_c))
        cfg_c = {k: v for k, v in COL_CONFIG.items() if k in out_c.columns}

        if "T2Date" in out_c.columns:
            missing_n = int(out_c["T2Date"].isna().sum())
            if missing_n:
                st.caption(
                    f"注：{missing_n} 条记录的 T+2 数据暂不存在（匹配日期接近数据末尾）。"
                )

        st.dataframe(out_c, hide_index=True, use_container_width=True, column_config=cfg_c)

    # ── Section D: 前一日状态 ─────────────────────────────────────────────────
    with sub_d:
        st.caption(
            "匹配日（MatchDate）前一个交易日的完整状态：编码、结构、量能，"
            "用于判断当前日型是否具备相同的启动或反转背景。"
        )
        cols_d = [
            "MatchDate",
            "MatchPrevDate", "MatchPrevCode",
            "MatchPrevOpenType", "MatchPrevStructure", "MatchPrevCloseDir",
            "MatchPrevCloseMove", "MatchPrevVolume", "MatchPrevTurnover", "MatchPrevVRatio",
        ]
        cfg_d = {k: v for k, v in COL_CONFIG.items() if k in cols_d}
        st.dataframe(
            _pick_cols(df, cols_d),
            hide_index=True,
            use_container_width=True,
            column_config=cfg_d,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Dataset version / snapshot helpers
# ─────────────────────────────────────────────────────────────────────────────

_DATA_DIR      = Path("data")
_ENRICHED_DIR  = Path("enriched_data")
_CODED_DIR     = Path("coded_data")
_SNAPSHOT_DIR  = Path("snapshots")


def _file_mtime_str(p: Path) -> str:
    """Return last-modified timestamp for *p*, or '—' if the file is missing."""
    try:
        return datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    except OSError:
        return "—"


def get_dataset_version_info() -> dict:
    """Return paths and last-modified times for the three source files."""
    raw_path   = _DATA_DIR     / "AVGO.csv"
    feat_path  = _ENRICHED_DIR / "AVGO_features.csv"
    coded_path = _CODED_DIR    / "AVGO_coded.csv"
    return {
        "raw":   {"path": str(raw_path),   "mtime": _file_mtime_str(raw_path)},
        "feat":  {"path": str(feat_path),  "mtime": _file_mtime_str(feat_path)},
        "coded": {"path": str(coded_path), "mtime": _file_mtime_str(coded_path)},
    }


def save_snapshot() -> str:
    """
    Copy the three source files into a timestamped snapshot folder.
    Returns the snapshot id (e.g. '20260410_143022').
    """
    snap_id  = datetime.now().strftime("%Y%m%d_%H%M%S")
    snap_dir = _SNAPSHOT_DIR / snap_id
    snap_dir.mkdir(parents=True, exist_ok=True)
    for src, dst_name in [
        (_DATA_DIR     / "AVGO.csv",          "AVGO.csv"),
        (_ENRICHED_DIR / "AVGO_features.csv", "AVGO_features.csv"),
        (_CODED_DIR    / "AVGO_coded.csv",    "AVGO_coded.csv"),
    ]:
        if src.exists():
            shutil.copy2(src, snap_dir / dst_name)
    return snap_id


# ─────────────────────────────────────────────────────────────────────────────
# Page config  (must be first Streamlit call)
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="AVGO Pattern Analyzer", layout="wide")

st.title("AVGO Pattern Analyzer")
st.markdown(
    "Encode a selected trading day, find historical days with matching or similar "
    "patterns, and inspect next-day price outcomes."
)

# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("Controls")
    target_date = st.date_input(
        "Target date",
        value=pd.Timestamp("2026-04-08").date(),
        help="The AVGO trading day you want to analyze.",
    )
    scan_phase: str = st.selectbox(
        "Scan phase",
        options=["daily", "premarket", "open30", "midday", "preclose"],
        index=0,
        help=(
            "Manual phase label for the Scan tab. Until intraday/minute data is "
            "available, all phases use the existing daily OHLCV feature fallback."
        ),
    )
    run_clicked = st.button(
        "Run Analysis",
        type="primary",
        use_container_width=True,
        help="Match patterns using the existing local CSV files. Does NOT fetch new data.",
    )
    refresh_clicked = st.button(
        "Refresh Data",
        type="secondary",
        use_container_width=True,
        help=(
            "Fetch latest prices from Yahoo Finance, rebuild features and encoding, "
            "then save a timestamped snapshot. Run this deliberately — it changes "
            "the sample set and may alter match membership."
        ),
    )
    st.divider()

    # ── Dataset version info ─────────────────────────────────────────────────
    _dvi = st.session_state.get("data_version_info") or get_dataset_version_info()
    _snap_id      = st.session_state.get("snapshot_id",     "—")
    _refresh_ts   = st.session_state.get("last_refresh_ts", "—")
    with st.expander("Dataset version", expanded=False):
        st.caption(f"**Raw**  `{_dvi['raw']['path']}`\n\n{_dvi['raw']['mtime']}")
        st.caption(f"**Features**  `{_dvi['feat']['path']}`\n\n{_dvi['feat']['mtime']}")
        st.caption(f"**Coded**  `{_dvi['coded']['path']}`\n\n{_dvi['coded']['mtime']}")
        if _snap_id != "—":
            st.caption(f"**Snapshot**  `snapshots/{_snap_id}`\n\nRefreshed at {_refresh_ts}")
        else:
            st.caption("No refresh performed this session.")
    st.caption("Data source: Yahoo Finance (yfinance)")
    st.divider()
    st.markdown("**位置过滤**")
    pos_filter: str = st.radio(
        "匹配样本范围",
        options=[
            "全部样本",
            "仅低位 (<33%)",
            "仅中位 (33–67%)",
            "仅高位 (≥67%)",
            "仅位置相近 (±15%)",
        ],
        index=0,
        label_visibility="collapsed",
        help=(
            "按匹配日的 30 日价格位置百分位（MatchPos30）过滤。\n\n"
            "「仅位置相近」= |MatchPos30 − 目标日 Pos30| ≤ 15 个百分点。\n\n"
            "过滤仅作用于展示层，不修改底层匹配算法或原始 CSV 结果。"
        ),
    )
    st.divider()
    st.markdown("**相似度过滤**")
    ctx_filter: str = st.radio(
        "相似度范围",
        options=["全部相似度", "仅高相似", "仅高+中相似"],
        index=0,
        label_visibility="collapsed",
        help=(
            "按 ContextScore 过滤匹配样本。\n\n"
            "**高相似** ≥ 65 分（位置 + 阶段 + 前日结构高度一致）\n\n"
            "**高+中相似** ≥ 35 分\n\n"
            "与位置过滤叠加生效。"
        ),
    )

# ─────────────────────────────────────────────────────────────────────────────
# Refresh Data — Steps 1–3 only (fetch / features / encode + snapshot)
# ─────────────────────────────────────────────────────────────────────────────

if refresh_clicked:
    _ref_error: str | None = None

    with st.spinner("Refresh 1/3  —  Fetching price data from Yahoo Finance…"):
        try:
            batch_update_all()
        except Exception as exc:
            _ref_error = f"Data fetch failed: {exc}"

    if not _ref_error:
        with st.spinner("Refresh 2/3  —  Building features…"):
            try:
                batch_build_features()
            except Exception as exc:
                _ref_error = f"Feature build failed: {exc}"

    if not _ref_error:
        with st.spinner("Refresh 3/3  —  Encoding…"):
            try:
                batch_encode_all()
            except Exception as exc:
                _ref_error = f"Encoding failed: {exc}"

    if _ref_error:
        st.error(_ref_error)
    else:
        _snap_id = save_snapshot()
        _now_ts  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.session_state["last_refresh_ts"]   = _now_ts
        st.session_state["snapshot_id"]       = _snap_id
        st.session_state["data_version_info"] = get_dataset_version_info()
        st.success(f"Data refreshed at {_now_ts}. Snapshot saved: `snapshots/{_snap_id}`")

# ─────────────────────────────────────────────────────────────────────────────
# Run Analysis — Steps 4–5 only (matching + stats; no data refresh)
# ─────────────────────────────────────────────────────────────────────────────

if run_clicked:
    target_date_str = target_date.strftime("%Y-%m-%d")
    reset_analysis_context_state(st.session_state, target_date_str)
    run_error: str | None = None

    with st.spinner("Step 1/2  —  Matching historical patterns…"):
        try:
            coded_df = load_coded_avgo()
            target_row, target_code, target_error = validate_target_code_for_analysis(
                coded_df, target_date_str
            )
            st.session_state["coded_df"] = coded_df
            st.session_state["target_row"] = (
                target_row.to_dict() if target_row is not None else None
            )
            st.session_state["target_code"] = target_code

            if target_error:
                run_error = target_error
            else:
                exact_df = build_next_day_match_table(coded_df, target_date_str)
                save_match_results(exact_df, target_date_str)
                near_df = build_near_match_table(coded_df, target_date_str)
                save_near_match_results(near_df, target_date_str)
                # All enrichments are app-layer only; core modules are untouched.
                exact_df = enrich_with_t2(exact_df, coded_df)
                near_df  = enrich_with_t2(near_df,  coded_df)
                exact_df = enrich_with_match_ohlcv(exact_df, coded_df)
                near_df  = enrich_with_match_ohlcv(near_df,  coded_df)
                exact_df = add_turnovers(exact_df)
                near_df  = add_turnovers(near_df)
                pos_df   = compute_position_features(coded_df)
                exact_df = enrich_with_position(exact_df, pos_df)
                near_df  = enrich_with_position(near_df,  pos_df)
                prev_df  = compute_prev_day_features(coded_df)
                exact_df = enrich_with_prev_day(exact_df, prev_df)
                near_df  = enrich_with_prev_day(near_df,  prev_df)
                mom_df   = compute_momentum_features(coded_df)
                exact_df = enrich_with_momentum(exact_df, mom_df)
                near_df  = enrich_with_momentum(near_df,  mom_df)
                _pipeline_ctx = get_target_context(target_date_str, pos_df, prev_df, mom_df)
                exact_df = compute_context_scores(exact_df, _pipeline_ctx)
                near_df  = compute_context_scores(near_df,  _pipeline_ctx)
        except Exception as exc:
            run_error = friendly_analysis_error("Matching", exc, target_date_str)

    if not run_error:
        with st.spinner("Step 2/2  —  Computing statistics…"):
            try:
                summary_df = build_stats_summary(target_date_str)
                save_stats_summary(summary_df, target_date_str)
            except Exception as exc:
                run_error = friendly_analysis_error("Stats", exc, target_date_str)

    if run_error:
        st.session_state["analysis_error"] = run_error
        st.session_state["data_version_info"] = get_dataset_version_info()
    else:
        try:
            scan_result = run_scan(
                target_date_str, coded_df, exact_df, near_df,
                summary_df, pos_df, prev_df, mom_df,
                scan_phase=scan_phase,
            )
        except Exception as exc:
            run_error = friendly_analysis_error("Scan", exc, target_date_str)
            st.session_state["analysis_error"] = run_error
            st.session_state["data_version_info"] = get_dataset_version_info()
        else:
            st.success(f"Analysis complete for {target_date_str}")
            st.session_state.update(
                target_date_str=target_date_str,
                coded_df=coded_df,
                exact_df=exact_df,
                near_df=near_df,
                summary_df=summary_df,
                pos_df=pos_df,
                prev_df=prev_df,
                mom_df=mom_df,
                target_ctx=_pipeline_ctx,
                match_context=_pipeline_ctx,
                scan_result=scan_result,
                research_result=None,
                analysis_error=None,
                data_version_info=get_dataset_version_info(),
            )

render_command_bar()

_BASE_MAIN_VIEW_LABELS: dict[str, str] = {
    "home": "首页",
    "scan": "扫描",
    "research": "研究",
    "predict": "推演",
    "history": "历史",
    "review": "复盘中心",
    "inspect": "查验分析",
    "target": "目标日",
    "exact": "精确匹配",
    "near": "近似匹配",
    "stats": "统计摘要",
}
_MAIN_VIEW_ORDER = list(_BASE_MAIN_VIEW_LABELS.keys())
_ANALYSIS_REQUIRED_VIEWS = {
    "scan",
    "research",
    "predict",
    "inspect",
    "target",
    "exact",
    "near",
    "stats",
}


def _sanitize_main_view(view_key: str | None) -> str:
    if view_key in _BASE_MAIN_VIEW_LABELS:
        return str(view_key)
    return "home"


def _build_main_view_labels(
    *,
    filter_active: bool = False,
    disp_exact_df: pd.DataFrame | None = None,
    exact_df: pd.DataFrame | None = None,
    disp_near_df: pd.DataFrame | None = None,
    near_df: pd.DataFrame | None = None,
) -> dict[str, str]:
    labels = dict(_BASE_MAIN_VIEW_LABELS)

    if exact_df is not None and disp_exact_df is not None:
        labels["exact"] = (
            f"精确匹配（{len(disp_exact_df)}/{len(exact_df)}）"
            if filter_active else f"精确匹配（{len(exact_df)}）"
        )
    if near_df is not None and disp_near_df is not None:
        labels["near"] = (
            f"近似匹配（{len(disp_near_df)}/{len(near_df)}）"
            if filter_active else f"近似匹配（{len(near_df)}）"
        )
    return labels


def _render_main_navigation(view_labels: dict[str, str]) -> str:
    ordered_keys = [key for key in _MAIN_VIEW_ORDER if key in view_labels]
    options = [view_labels[key] for key in ordered_keys]
    current_view = _sanitize_main_view(st.session_state.get("active_main_view"))
    current_label = view_labels.get(current_view, view_labels["home"])
    current_index = options.index(current_label) if current_label in options else 0

    st.markdown("**页面导航**")
    selected_label = st.radio(
        "页面导航",
        options=options,
        index=current_index,
        horizontal=True,
        label_visibility="collapsed",
    )

    label_to_view = {view_labels[key]: key for key in ordered_keys}
    selected_view = label_to_view[selected_label]
    st.session_state["active_main_view"] = selected_view
    return selected_view


def _render_analysis_required_placeholder(view_key: str, analysis_error: str | None) -> None:
    st.subheader(_BASE_MAIN_VIEW_LABELS[view_key])
    if analysis_error:
        st.warning(analysis_error)
    else:
        st.info("请先在侧边栏选择日期并运行分析，然后再进入该页面。")


# ─────────────────────────────────────────────────────────────────────────────
# Navigation / Guard
# ─────────────────────────────────────────────────────────────────────────────

analysis_error: str | None = st.session_state.get("analysis_error")
analysis_ready = all(
    key in st.session_state
    for key in ("target_date_str", "coded_df", "exact_df", "near_df", "summary_df", "scan_result")
)

if not analysis_ready:
    active_main_view = _render_main_navigation(_build_main_view_labels())

    if active_main_view == "home":
        render_home_tab(None)
        if analysis_error:
            st.warning(analysis_error)
        else:
            st.info("请先在侧边栏选择日期并运行分析。")
    elif active_main_view == "history":
        render_history_tab()
    elif active_main_view == "review":
        render_review_tab()
    else:
        _render_analysis_required_placeholder(active_main_view, analysis_error)
    st.stop()

target_date_str: str     = st.session_state["target_date_str"]
coded_df: pd.DataFrame   = st.session_state["coded_df"]
exact_df: pd.DataFrame   = st.session_state["exact_df"]
near_df: pd.DataFrame    = st.session_state["near_df"]
summary_df: pd.DataFrame = st.session_state["summary_df"]
pos_df: pd.DataFrame     = st.session_state.get("pos_df",  pd.DataFrame())
prev_df: pd.DataFrame    = st.session_state.get("prev_df", pd.DataFrame())
mom_df: pd.DataFrame     = st.session_state.get("mom_df",  pd.DataFrame())
scan_result: dict | None = st.session_state.get("scan_result")
research_result: dict | None = st.session_state.get("research_result")
target_row = st.session_state.get("target_row")

# Target day context for context-score expander in match tables.
target_ctx: dict = st.session_state.get("target_ctx") or get_target_context(
    target_date_str, pos_df, prev_df, mom_df
)
_home_scan_ts = ""
if isinstance(scan_result, dict):
    _home_scan_ts = str(scan_result.get("scan_timestamp") or "")
_home_signature = f"{target_date_str}|{_home_scan_ts}|{st.session_state.get('target_code', '')}"
if st.session_state.get("home_terminal_signature") != _home_signature:
    st.session_state["home_terminal_result"] = build_home_terminal_orchestrator_result(
        scan_result=scan_result,
        target_date_str=target_date_str,
        coded_df=coded_df,
        target_row=target_row,
        target_ctx=target_ctx,
        persist_log=True,
    )
    st.session_state["home_terminal_signature"] = _home_signature
home_payload = st.session_state.get("home_terminal_result")

# ─────────────────────────────────────────────────────────────────────────────
# Position filter — display-layer only; raw matches in session_state untouched
# ─────────────────────────────────────────────────────────────────────────────

# Resolve target day's Pos30 for the '位置相近' filter mode.
_target_pos30: float | None = None
if not pos_df.empty:
    _tts = pd.to_datetime(target_date_str)
    _pr  = pos_df[pos_df["Date"] == _tts]
    if not _pr.empty:
        _v = _pr.iloc[0].get("Pos30")
        if pd.notna(_v):
            _target_pos30 = float(_v)

# Position filter applied first, then context filter stacked on top.
disp_exact_df = apply_position_filter(exact_df, pos_filter, _target_pos30)
disp_near_df  = apply_position_filter(near_df,  pos_filter, _target_pos30)
disp_exact_df = apply_context_filter(disp_exact_df, ctx_filter)
disp_near_df  = apply_context_filter(disp_near_df,  ctx_filter)

_filter_active = pos_filter != "全部样本" or ctx_filter != "全部相似度"

active_main_view = _render_main_navigation(
    _build_main_view_labels(
        filter_active=_filter_active,
        disp_exact_df=disp_exact_df,
        exact_df=exact_df,
        disp_near_df=disp_near_df,
        near_df=near_df,
    )
)

if active_main_view == "home":
    render_home_tab(home_payload)


# ── Scan ─────────────────────────────────────────────────────────────────────

if active_main_view == "scan":
    render_scan_tab(target_date_str, scan_result)


if active_main_view == "research":
    research_result = render_research_tab(scan_result, research_result)


if active_main_view == "predict":
    render_predict_tab(scan_result, research_result)

if active_main_view == "history":
    render_history_tab()

if active_main_view == "review":
    render_review_tab()

if active_main_view == "inspect":
    render_inspect_tab()

# ── Target Day ────────────────────────────────────────────────────────────────

if active_main_view == "target":
    st.subheader(f"Target Day — {target_date_str}")
    target_row = get_target_row(coded_df, target_date_str)

    if target_row is None:
        st.warning(
            f"{target_date_str} was not found in AVGO data. "
            "It may be a weekend, market holiday, or outside the downloaded date range."
        )
    else:
        # --- OHLCV ---
        st.markdown("**OHLCV**")
        ohlcv_cols = ["Open", "High", "Low", "Close", "Volume"]
        ohlcv_df = pd.DataFrame(
            {col: [target_row[col]] for col in ohlcv_cols if col in target_row.index}
        )
        st.dataframe(
            ohlcv_df,
            hide_index=True,
            column_config={
                "Open":   st.column_config.NumberColumn(format="%.2f"),
                "High":   st.column_config.NumberColumn(format="%.2f"),
                "Low":    st.column_config.NumberColumn(format="%.2f"),
                "Close":  st.column_config.NumberColumn(format="%.2f"),
            },
        )

        # --- 5-digit code ---
        raw_code = target_row.get("Code", pd.NA)
        code_str = str(raw_code) if pd.notna(raw_code) else ""
        st.markdown(f"**5-Digit Code:** `{code_str if code_str else '—'}`")

        # --- Code breakdown ---
        if len(code_str) == 5 and code_str.isdigit():
            st.markdown("**Code Breakdown**")
            digit_keys = ["O", "H", "L", "C", "V"]
            digit_labels = [
                "O — Open gap vs prev close",
                "H — High wick above open",
                "L — Low wick below open",
                "C — Close vs open",
                "V — Volume vs 20-day avg",
            ]
            breakdown_rows = [
                {
                    "Dimension": lbl,
                    "Code": int(ch),
                    "Meaning": CODE_LABELS[key].get(int(ch), ""),
                }
                for key, lbl, ch in zip(digit_keys, digit_labels, code_str)
            ]
            st.dataframe(
                pd.DataFrame(breakdown_rows),
                hide_index=True,
                use_container_width=False,
            )
        else:
            st.warning(
                "Code is unavailable for this date. "
                "The date may lack enough prior history to compute all features."
            )

        # --- Raw feature values (collapsed) ---
        with st.expander("Raw feature values"):
            feat: dict[str, list] = {}
            for col in ["O_gap", "H_up", "L_down", "C_move"]:
                if col in target_row.index and pd.notna(target_row[col]):
                    feat[col] = [fmt_pct(target_row[col])]
            if "V_ratio" in target_row.index and pd.notna(target_row["V_ratio"]):
                feat["V_ratio"] = [f"{float(target_row['V_ratio']):.3f}×"]
            if "PrevClose" in target_row.index and pd.notna(target_row["PrevClose"]):
                feat["PrevClose"] = [f"{float(target_row['PrevClose']):.2f}"]
            if "MA20_Volume" in target_row.index and pd.notna(target_row["MA20_Volume"]):
                feat["MA20_Volume"] = [f"{int(target_row['MA20_Volume']):,}"]
            if feat:
                st.dataframe(pd.DataFrame(feat), hide_index=True)
            else:
                st.write("No feature data available.")

        # --- Position context ---
        if not pos_df.empty:
            target_ts = pd.to_datetime(target_date_str)
            pos_rows = pos_df[pos_df["Date"] == target_ts]
            if not pos_rows.empty:
                tpos = pos_rows.iloc[0]
                st.markdown("**Position Context**")

                label = str(tpos.get("PosLabel", "—"))
                _LABEL_COLOR = {"低位": "#3498db", "中位": "#f39c12", "高位": "#e74c3c"}
                lcolor = _LABEL_COLOR.get(label, "#888888")
                st.markdown(
                    f'<span style="font-size:1.25em;font-weight:bold;color:{lcolor}">'
                    f'{label}</span>',
                    unsafe_allow_html=True,
                )

                pos_display: dict[str, list] = {}
                if pd.notna(tpos.get("Pos15")):
                    pos_display["15日位置%"] = [f"{tpos['Pos15']:.1f}"]
                if pd.notna(tpos.get("Pos30")):
                    pos_display["30日位置%"] = [f"{tpos['Pos30']:.1f}"]
                if pd.notna(tpos.get("Rebound30")):
                    pos_display["距30日低点反弹%"] = [f"{tpos['Rebound30']:.2f}"]
                near_high = tpos.get("NearHigh30", False)
                near_low  = tpos.get("NearLow30",  False)
                pos_display["近30日高位"] = ["✅" if bool(near_high) else "—"]
                pos_display["近30日低位"] = ["✅" if bool(near_low)  else "—"]

                if pos_display:
                    st.dataframe(pd.DataFrame(pos_display), hide_index=True)

        # --- Previous-day state ---
        if not prev_df.empty:
            target_ts = pd.to_datetime(target_date_str)
            prev_rows = prev_df[prev_df["Date"] == target_ts]
            if not prev_rows.empty:
                tp = prev_rows.iloc[0]
                st.markdown("**前一日状态**")

                prev_struct    = str(tp.get("PrevStructure", "—"))
                prev_close_dir = str(tp.get("PrevCloseDir",  "—"))
                pcolor = _STRUCTURE_COLORS.get(prev_struct, "#888888")
                st.markdown(
                    f'<span style="font-weight:bold;color:{pcolor}">{prev_struct}</span>'
                    f'  <span style="color:#888888">{prev_close_dir}</span>',
                    unsafe_allow_html=True,
                )

                pd_data: dict[str, list] = {}
                pdate = tp.get("PrevDate", "—")
                if pdate and pdate != "—":
                    pd_data["日期"] = [str(pdate)]
                pcode = tp.get("PrevCode", "—")
                if pd.notna(pcode) and str(pcode) not in ("—", "nan", "<NA>"):
                    pd_data["编码"] = [str(pcode)]
                if pd.notna(tp.get("PrevOpenType")):
                    pd_data["开盘类型"] = [str(tp["PrevOpenType"])]
                if pd.notna(tp.get("PrevCloseMove")):
                    pd_data["涨跌%"] = [f"{tp['PrevCloseMove']:+.2f}"]
                if pd.notna(tp.get("PrevVolume")):
                    pd_data["成交量"] = [f"{int(tp['PrevVolume']):,}"]
                if pd.notna(tp.get("PrevTurnover")):
                    pd_data["成交额"] = [f"{tp['PrevTurnover']:,.0f}"]
                if pd.notna(tp.get("PrevVRatio")):
                    pd_data["相对量能"] = [f"{tp['PrevVRatio']:.2f}×"]

                if pd_data:
                    st.dataframe(pd.DataFrame(pd_data), hide_index=True)

        # --- Momentum / Stage ---
        if not mom_df.empty:
            target_ts = pd.to_datetime(target_date_str)
            mom_rows = mom_df[mom_df["Date"] == target_ts]
            if not mom_rows.empty:
                tm = mom_rows.iloc[0]
                st.markdown("**动能 / 阶段**")

                stage = str(tm.get("StageLabel", "—"))
                sc    = _STAGE_COLORS.get(stage, "#888888")
                st.markdown(
                    f'<span style="font-size:1.25em;font-weight:bold;color:{sc}">{stage}</span>',
                    unsafe_allow_html=True,
                )

                mom_display: dict[str, list] = {}
                if pd.notna(tm.get("Ret3")):
                    mom_display["3日涨跌%"] = [f"{tm['Ret3']:+.2f}"]
                if pd.notna(tm.get("Ret5")):
                    mom_display["5日涨跌%"] = [f"{tm['Ret5']:+.2f}"]
                if pd.notna(tm.get("Ret10")):
                    mom_display["10日涨跌%"] = [f"{tm['Ret10']:+.2f}"]
                if pd.notna(tm.get("Vol5Ratio")):
                    mom_display["量/5日均"] = [f"{tm['Vol5Ratio']:.2f}×"]
                vol_exp = tm.get("VolExpanding", False)
                mom_display["量能方向"] = ["↑ 量增" if (pd.notna(vol_exp) and bool(vol_exp)) else "↓ 量缩"]

                if mom_display:
                    st.dataframe(pd.DataFrame(mom_display), hide_index=True)

# ── Exact Matches ─────────────────────────────────────────────────────────────

if active_main_view == "exact":
    st.subheader("Exact Code Matches")
    st.caption(
        "Historical AVGO days whose 5-digit code is identical to the target day."
    )
    if exact_df.empty:
        st.info("No exact matches found for this date.")
    else:
        if _filter_active:
            _tot = len(exact_df)
            _fil = len(disp_exact_df)
            _filter_desc = " + ".join(f for f in [
                pos_filter if pos_filter != "全部样本" else "",
                ctx_filter if ctx_filter != "全部相似度" else "",
            ] if f)
            if _fil == 0:
                st.warning(
                    f"过滤「**{_filter_desc}**」后无剩余样本。"
                    f"原始共 {_tot} 条 — 请在侧栏调整过滤条件。"
                )
            else:
                st.info(f"原始样本数：**{_tot}**　→　过滤后：**{_fil}**　（{_filter_desc}）")

        if not disp_exact_df.empty:
            labeled_exact = add_pattern_labels(disp_exact_df)

            st.markdown("**Top 相似样本**")
            _render_top_context_matches(labeled_exact)

            _render_match_tables(labeled_exact, has_vcode_diff=False, target_ctx=target_ctx)

            with st.expander(f"逐笔 K 线预览（共 {len(labeled_exact)} 条）"):
                render_mini_cards(labeled_exact, coded_df)

# ── Near Matches ──────────────────────────────────────────────────────────────

if active_main_view == "near":
    st.subheader("Near Code Matches")
    st.caption(
        "Historical AVGO days with identical O / H / L / C codes and volume code "
        "within ±1. **VCodeDiff = 0** = identical volume; **1** = adjacent."
    )
    if near_df.empty:
        st.info("No near matches found for this date.")
    else:
        if _filter_active:
            _tot = len(near_df)
            _fil = len(disp_near_df)
            _filter_desc = " + ".join(f for f in [
                pos_filter if pos_filter != "全部样本" else "",
                ctx_filter if ctx_filter != "全部相似度" else "",
            ] if f)
            if _fil == 0:
                st.warning(
                    f"过滤「**{_filter_desc}**」后无剩余样本。"
                    f"原始共 {_tot} 条 — 请在侧栏调整过滤条件。"
                )
            else:
                st.info(f"原始样本数：**{_tot}**　→　过滤后：**{_fil}**　（{_filter_desc}）")

        if not disp_near_df.empty:
            labeled_near = add_pattern_labels(disp_near_df)

            # Sort by context score (most similar first); fall back to VCodeDiff.
            if "ContextScore" in labeled_near.columns:
                labeled_near = labeled_near.sort_values(
                    "ContextScore", ascending=False
                ).reset_index(drop=True)
            elif "VCodeDiff" in labeled_near.columns:
                labeled_near = labeled_near.sort_values(
                    ["VCodeDiff", "MatchDate"]
                ).reset_index(drop=True)

            st.markdown("**Top 相似样本**")
            _render_top_context_matches(labeled_near)

            _render_match_tables(labeled_near, has_vcode_diff=True, target_ctx=target_ctx)

            with st.expander(f"逐笔 K 线预览（共 {len(labeled_near)} 条）"):
                render_mini_cards(labeled_near, coded_df)

# ── Stats Summary ─────────────────────────────────────────────────────────────

if active_main_view == "stats":
    st.subheader("Next-Day Statistics")

    # ── Shared stat sections definition ──────────────────────────────────────
    _STAT_SECTIONS = [
        ("Open — next-day open vs match close", [
            ("Avg open change",   "AvgNextOpenChange"),
            ("Median",            "MedianNextOpenChange"),
            ("% positive opens",  "PositiveNextOpenChangeRate"),
        ]),
        ("High — next-day high from open", [
            ("Avg high move",     "AvgNextHighMove"),
            ("Median",            "MedianNextHighMove"),
            ("Rate ≥ 1%",         "HighMoveOver1PctRate"),
            ("Rate ≥ 2%",         "HighMoveOver2PctRate"),
        ]),
        ("Low — next-day low from open", [
            ("Avg low move",      "AvgNextLowMove"),
            ("Median",            "MedianNextLowMove"),
            ("Rate ≥ 1%",         "LowMoveOver1PctRate"),
            ("Rate ≥ 2%",         "LowMoveOver2PctRate"),
        ]),
        ("Close — next-day close vs open", [
            ("Avg close move",    "AvgNextCloseMove"),
            ("Median",            "MedianNextCloseMove"),
            ("% positive closes", "PositiveNextCloseMoveRate"),
            ("% negative closes", "NegativeNextCloseMoveRate"),
        ]),
    ]

    def _get_row(mtype: str) -> pd.Series | None:
        rows = summary_df[summary_df["MatchType"] == mtype]
        return rows.iloc[0] if not rows.empty else None

    # ── Renderer for pre-computed stats_reporter rows (dict/Series) ──────────
    def _render_stats(container, row: pd.Series | None, label: str) -> None:
        with container:
            st.markdown(f"### {label}")
            if row is None:
                st.info("No data.")
                return
            sample_size = int(row["SampleSize"]) if pd.notna(row.get("SampleSize")) else 0
            if sample_size == 0:
                st.info("No matches — statistics unavailable.")
                return
            bias = str(row.get("DominantNextDayBias", "—"))
            st.metric("Sample Size", sample_size)
            st.markdown(f"**Dominant Bias:** {BIAS_ICONS.get(bias, f'⚪ {bias}')}")
            st.divider()
            for section_title, fields in _STAT_SECTIONS:
                st.markdown(f"**{section_title}**")
                lines = [f"- {lbl}: **{fmt_pct(row.get(col, pd.NA))}**" for lbl, col in fields]
                st.markdown("\n".join(lines))
                st.write("")

    # ── Renderer for inline-computed filtered stats (dict from compute_inline_stats) ──
    def _render_inline_stats(container, stats: dict, label: str) -> None:
        with container:
            st.markdown(f"### {label}")
            n = stats.get("SampleSize", 0)
            if n == 0:
                st.info("过滤后无匹配样本。")
                return
            bias = str(stats.get("DominantNextDayBias", "—"))
            st.metric("Sample Size", n)
            st.markdown(f"**Dominant Bias:** {BIAS_ICONS.get(bias, f'⚪ {bias}')}")
            st.divider()

            for section_title, fields in _STAT_SECTIONS:
                st.markdown(f"**{section_title}**")
                lines = [f"- {lbl}: **{fmt_pct(stats.get(col, float('nan')))}**" for lbl, col in fields]
                st.markdown("\n".join(lines))
                st.write("")

            # T+1 structure distribution
            t1 = stats.get("T1Structure")
            if t1 is not None and len(t1) > 0:
                st.markdown("**次日结构分布**")
                for cat in STRUCTURE_ORDER:
                    cnt = int(t1.get(cat, 0))
                    pct = cnt / n * 100
                    color = _STRUCTURE_COLORS.get(cat, "#888888")
                    st.markdown(
                        f'<span style="color:{color}">■</span> {cat}: **{cnt}** 次（{pct:.0f}%）',
                        unsafe_allow_html=True,
                    )
                st.write("")

            # T+2 stats
            avg_t2 = stats.get("AvgT2CloseMove")
            med_t2 = stats.get("MedianT2CloseMove")
            if avg_t2 is not None and not pd.isna(avg_t2):
                st.markdown("**T+2 收盘（vs 开盘）**")
                st.markdown(
                    f"- Avg: **{fmt_pct(avg_t2)}**\n"
                    f"- Median: **{fmt_pct(med_t2)}**"
                )
                t2 = stats.get("T2Structure")
                if t2 is not None and len(t2) > 0:
                    st.markdown("**后天结构分布**")
                    for cat in STRUCTURE_ORDER:
                        cnt = int(t2.get(cat, 0))
                        pct = cnt / n * 100
                        color = _STRUCTURE_COLORS.get(cat, "#888888")
                        st.markdown(
                            f'<span style="color:{color}">■</span> {cat}: **{cnt}** 次（{pct:.0f}%）',
                            unsafe_allow_html=True,
                        )
                st.write("")

    # ── Stats mode selector ───────────────────────────────────────────────────
    stats_mode: str = st.radio(
        "统计范围",
        options=["全量样本", "当前过滤样本", "高相似样本"],
        index=0,
        horizontal=True,
        help=(
            "**全量样本** — 全部原始匹配结果，不受任何过滤影响。\n\n"
            "**当前过滤样本** — 应用侧栏「位置过滤」和「相似度过滤」后的样本。\n\n"
            "**高相似样本** — ContextScore ≥ 65 的样本（忽略位置/相似度过滤器）。"
        ),
    )

    # ── Main layout ──────────────────────────────────────────────────────────
    if stats_mode == "全量样本":
        st.caption("统计基于全量原始匹配样本（位置过滤和相似度过滤均不生效）。")
        col_l, col_r = st.columns(2)
        _render_stats(col_l, _get_row("exact"), "Exact Matches")
        _render_stats(col_r, _get_row("near"),  "Near Matches")

    elif stats_mode == "当前过滤样本":
        if not _filter_active:
            st.info("当前侧栏未启用任何过滤器，结果与「全量样本」相同。")
        else:
            active_filters = " + ".join(f for f in [
                pos_filter if pos_filter != "全部样本" else "",
                ctx_filter if ctx_filter != "全部相似度" else "",
            ] if f)
            st.markdown(
                f'<span style="background:#3498db22;color:#3498db;font-weight:bold;'
                f'padding:2px 8px;border-radius:4px">🔍 过滤后样本统计 — {active_filters}</span>',
                unsafe_allow_html=True,
            )
            st.write("")
        filt_exact_stats = compute_inline_stats(disp_exact_df) if not disp_exact_df.empty else {"SampleSize": 0}
        filt_near_stats  = compute_inline_stats(disp_near_df)  if not disp_near_df.empty  else {"SampleSize": 0}
        col_l, col_r = st.columns(2)
        _render_inline_stats(col_l, filt_exact_stats, "Exact Matches（过滤后）")
        _render_inline_stats(col_r, filt_near_stats,  "Near Matches（过滤后）")
        with st.expander("全量样本对照（未过滤基准）"):
            st.caption("以下统计基于全量原始匹配样本，供对照参考。")
            col_l2, col_r2 = st.columns(2)
            _render_stats(col_l2, _get_row("exact"), "Exact Matches（全量）")
            _render_stats(col_r2, _get_row("near"),  "Near Matches（全量）")

    elif stats_mode == "高相似样本":
        high_exact = (
            exact_df[exact_df["ContextLabel"] == "高相似"].reset_index(drop=True)
            if "ContextLabel" in exact_df.columns else pd.DataFrame()
        )
        high_near = (
            near_df[near_df["ContextLabel"] == "高相似"].reset_index(drop=True)
            if "ContextLabel" in near_df.columns else pd.DataFrame()
        )
        st.markdown(
            f'<span style="background:#f1c40f22;color:#c8971f;font-weight:bold;'
            f'padding:2px 8px;border-radius:4px">'
            f'★ 高相似样本 — Exact {len(high_exact)} 条 / Near {len(high_near)} 条</span>',
            unsafe_allow_html=True,
        )
        st.caption("ContextScore ≥ 65 的样本（全量中筛选，不受侧栏过滤影响）。")
        st.write("")
        high_exact_stats = compute_inline_stats(high_exact) if not high_exact.empty else {"SampleSize": 0}
        high_near_stats  = compute_inline_stats(high_near)  if not high_near.empty  else {"SampleSize": 0}
        col_l, col_r = st.columns(2)
        _render_inline_stats(col_l, high_exact_stats, "Exact 高相似")
        _render_inline_stats(col_r, high_near_stats,  "Near 高相似")
        with st.expander("全量样本对照"):
            st.caption("以下统计基于全量原始匹配样本，供对照参考。")
            col_l2, col_r2 = st.columns(2)
            _render_stats(col_l2, _get_row("exact"), "Exact Matches（全量）")
            _render_stats(col_r2, _get_row("near"),  "Near Matches（全量）")

# ─────────────────────────────────────────────────────────────────────────────
# Export current analysis snapshot
# ─────────────────────────────────────────────────────────────────────────────

st.divider()
st.markdown("**Export current analysis snapshot**")

_dvi_now    = st.session_state.get("data_version_info") or get_dataset_version_info()
_snap_now   = st.session_state.get("snapshot_id", "—")
_target_row = get_target_row(coded_df, target_date_str)
_target_code = (
    str(int(_target_row["Code"]))
    if _target_row is not None and pd.notna(_target_row.get("Code"))
    else "—"
)

_export_payload = {
    "target_date":        target_date_str,
    "target_code":        _target_code,
    "snapshot_id":        _snap_now,
    "dataset_timestamps": {
        "raw":   _dvi_now["raw"]["mtime"],
        "feat":  _dvi_now["feat"]["mtime"],
        "coded": _dvi_now["coded"]["mtime"],
    },
    "exact_match_dates": (
        sorted(exact_df["MatchDate"].astype(str).tolist())
        if not exact_df.empty and "MatchDate" in exact_df.columns else []
    ),
    "near_match_dates": (
        sorted(near_df["MatchDate"].astype(str).tolist())
        if not near_df.empty and "MatchDate" in near_df.columns else []
    ),
}

st.download_button(
    label="Download snapshot JSON",
    data=json.dumps(_export_payload, indent=2, ensure_ascii=False),
    file_name=f"analysis_snapshot_{target_date_str}.json",
    mime="application/json",
)
