from __future__ import annotations

import os
from pathlib import Path

# Ensure the working directory is always the repo root so that all relative
# paths used by the core modules (data/, enriched_data/, etc.) resolve correctly
# regardless of where `streamlit run` is invoked from.
os.chdir(Path(__file__).parent)

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
        return "高开高走" if close_move >= 0 else "高开低走"
    if ot == "低开":
        return "低开高走" if close_move >= 0 else "低开低走"
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
                match_date  = str(row.get("MatchDate",  ""))
                next_date   = str(row.get("NextDate",   ""))
                match_code  = str(row.get("MatchCode",  ""))
                t2_date     = str(row.get("T2Date", "")) or None
                structure   = str(row.get("次日日内结构", "—"))
                t2_struct   = str(row.get("T2结构",      "—"))
                vcode_diff  = row.get("VCodeDiff", None)

                # Compact caption: code + optional VCodeDiff
                caption_parts = [f"`{match_code}`"]
                if vcode_diff is not None and pd.notna(vcode_diff):
                    caption_parts.append(f"VDiff={int(vcode_diff)}")
                st.caption("  ".join(caption_parts))

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


def _render_match_tables(df: pd.DataFrame, has_vcode_diff: bool = False) -> None:
    """
    Render three focused sub-tabs for a match result dataframe.
    All tables share the same row order; MatchDate is the left anchor column
    in every sub-tab so rows visually align when switching between them.

      Sub-tab A  匹配日数据  — MatchDate full OHLCV + forward structure labels
      Sub-tab B  次日 T+1   — T+1 full OHLCV + moves + structure
      Sub-tab C  后天 T+2   — T+2 full OHLCV + moves + structure
    """
    # ── Pattern distribution bar chart (always visible, above sub-tabs) ──────
    st.markdown("**次日走势分布（T+1）**")
    render_pattern_bar_chart(df)

    # ── Three sub-tabs ────────────────────────────────────────────────────────
    sub_a, sub_b, sub_c = st.tabs(["匹配日数据", "次日 T+1", "后天 T+2"])

    # ── Section A: 匹配日数据 ─────────────────────────────────────────────────
    with sub_a:
        st.caption(
            "匹配日（MatchDate）的完整 OHLCV，以及 T+1 / T+2 走势标签供快速核对。"
        )
        cols_a = ["MatchDate", "MatchCode"]
        if has_vcode_diff:
            cols_a.append("VCodeDiff")
        cols_a += [
            "MatchOpen", "MatchHigh", "MatchLow", "MatchClose",
            "MatchVolume", "MatchTurnover",
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
    run_clicked = st.button("Run Analysis", type="primary", use_container_width=True)
    st.divider()
    st.caption("Data source: Yahoo Finance (yfinance)")

# ─────────────────────────────────────────────────────────────────────────────
# Pipeline execution
# ─────────────────────────────────────────────────────────────────────────────

if run_clicked:
    target_date_str = target_date.strftime("%Y-%m-%d")
    run_error: str | None = None

    # Each step runs inside its own spinner so the user sees progress.
    with st.spinner("Step 1 / 5  —  Fetching price data from Yahoo Finance…"):
        try:
            batch_update_all()
        except Exception as exc:
            run_error = f"Data fetch failed: {exc}"

    if not run_error:
        with st.spinner("Step 2 / 5  —  Building features…"):
            try:
                batch_build_features()
            except Exception as exc:
                run_error = f"Feature build failed: {exc}"

    if not run_error:
        with st.spinner("Step 3 / 5  —  Encoding…"):
            try:
                batch_encode_all()
            except Exception as exc:
                run_error = f"Encoding failed: {exc}"

    if not run_error:
        with st.spinner("Step 4 / 5  —  Matching historical patterns…"):
            try:
                coded_df = load_coded_avgo()
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
            except Exception as exc:
                run_error = f"Matching failed: {exc}"

    if not run_error:
        with st.spinner("Step 5 / 5  —  Computing statistics…"):
            try:
                summary_df = build_stats_summary(target_date_str)
                save_stats_summary(summary_df, target_date_str)
            except Exception as exc:
                run_error = f"Stats failed: {exc}"

    if run_error:
        st.error(run_error)
    else:
        st.success(f"Analysis complete for {target_date_str}")
        st.session_state.update(
            target_date_str=target_date_str,
            coded_df=coded_df,
            exact_df=exact_df,
            near_df=near_df,
            summary_df=summary_df,
        )

# ─────────────────────────────────────────────────────────────────────────────
# Guard — nothing to show until first run completes
# ─────────────────────────────────────────────────────────────────────────────

if "target_date_str" not in st.session_state:
    st.info("Select a target date in the sidebar and click **Run Analysis** to begin.")
    st.stop()

target_date_str: str     = st.session_state["target_date_str"]
coded_df: pd.DataFrame   = st.session_state["coded_df"]
exact_df: pd.DataFrame   = st.session_state["exact_df"]
near_df: pd.DataFrame    = st.session_state["near_df"]
summary_df: pd.DataFrame = st.session_state["summary_df"]

# ─────────────────────────────────────────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────────────────────────────────────────

tab1, tab2, tab3, tab4 = st.tabs([
    "Target Day",
    f"Exact Matches  ({len(exact_df)})",
    f"Near Matches  ({len(near_df)})",
    "Stats Summary",
])

# ── Tab 1: Target Day ─────────────────────────────────────────────────────────

with tab1:
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

# ── Tab 2: Exact Matches ──────────────────────────────────────────────────────

with tab2:
    st.subheader("Exact Code Matches")
    st.caption(
        "Historical AVGO days whose 5-digit code is identical to the target day."
    )
    if exact_df.empty:
        st.info("No exact matches found for this date.")
    else:
        labeled_exact = add_pattern_labels(exact_df)
        _render_match_tables(labeled_exact, has_vcode_diff=False)

        with st.expander(f"逐笔 K 线预览（共 {len(labeled_exact)} 条）"):
            render_mini_cards(labeled_exact, coded_df)

# ── Tab 3: Near Matches ───────────────────────────────────────────────────────

with tab3:
    st.subheader("Near Code Matches")
    st.caption(
        "Historical AVGO days with identical O / H / L / C codes and volume code "
        "within ±1. **VCodeDiff = 0** = identical volume; **1** = adjacent."
    )
    if near_df.empty:
        st.info("No near matches found for this date.")
    else:
        labeled_near = add_pattern_labels(near_df)

        # Sort by strongest similarity first (VCodeDiff 0 before 1), then date.
        if "VCodeDiff" in labeled_near.columns:
            labeled_near = labeled_near.sort_values(
                ["VCodeDiff", "MatchDate"]
            ).reset_index(drop=True)

        _render_match_tables(labeled_near, has_vcode_diff=True)

        with st.expander(f"逐笔 K 线预览（共 {len(labeled_near)} 条）"):
            render_mini_cards(labeled_near, coded_df)

# ── Tab 4: Stats Summary ──────────────────────────────────────────────────────

with tab4:
    st.subheader("Next-Day Statistics")
    st.caption("Aggregated from Exact and Near match tables above.")

    def _get_row(mtype: str) -> pd.Series | None:
        rows = summary_df[summary_df["MatchType"] == mtype]
        return rows.iloc[0] if not rows.empty else None

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

            sections = [
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

            for section_title, fields in sections:
                st.markdown(f"**{section_title}**")
                lines = [
                    f"- {lbl}: **{fmt_pct(row.get(col, pd.NA))}**"
                    for lbl, col in fields
                ]
                st.markdown("\n".join(lines))
                st.write("")

    col_l, col_r = st.columns(2)
    _render_stats(col_l, _get_row("exact"), "Exact Matches")
    _render_stats(col_r, _get_row("near"), "Near Matches")
