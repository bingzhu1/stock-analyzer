"""services/stats_engine.py

Simple summary statistics for cross-symbol comparisons.

Public API
----------
compute_match_stats(comparison_df) -> dict
    Returns matched / mismatched / total / match_rate from a comparison
    DataFrame produced by ``comparison_engine.compare_field``.

distribution_by_label(comparison_df, label_col) -> dict[str, dict]
    Breaks down match stats by a categorical label column.

position_distribution(comparison_df, aligned_df, symbol) -> dict
    Counts high / mid / low position days among matched rows.
    Label source priority: {symbol}_PosLabel → {symbol}_Pos30 (bucketed).
"""
from __future__ import annotations

import pandas as pd


def compute_match_stats(comparison_df: pd.DataFrame) -> dict:
    """
    Compute aggregate match statistics from a comparison DataFrame.

    Parameters
    ----------
    comparison_df : pd.DataFrame
        Must contain a boolean ``match`` column (output of
        ``comparison_engine.compare_field``).

    Returns
    -------
    dict with keys:
        total (int), matched (int), mismatched (int),
        match_rate (float, 0–100 rounded to 1 dp)
    """
    if comparison_df.empty or "match" not in comparison_df.columns:
        return {"total": 0, "matched": 0, "mismatched": 0, "match_rate": 0.0}

    valid = comparison_df["match"].notna()
    total     = int(valid.sum())
    matched   = int(comparison_df.loc[valid, "match"].sum())
    mismatched = total - matched
    match_rate = round(matched / total * 100, 1) if total > 0 else 0.0

    return {
        "total":      total,
        "matched":    matched,
        "mismatched": mismatched,
        "match_rate": match_rate,
    }


def distribution_by_label(
    comparison_df: pd.DataFrame,
    label_col: str,
) -> dict[str, dict]:
    """
    Break down match stats by a categorical label column.

    Parameters
    ----------
    comparison_df : pd.DataFrame
        Must contain ``match`` and ``label_col`` columns.
    label_col : str
        Name of the label column to group by (e.g. ``AVGO_PosLabel``).

    Returns
    -------
    dict[label_value, {"total", "matched", "mismatched", "match_rate"}]
    Empty dict when ``label_col`` is absent.
    """
    if "match" not in comparison_df.columns or label_col not in comparison_df.columns:
        return {}

    result: dict[str, dict] = {}
    for label, group in comparison_df.groupby(label_col, dropna=False):
        key = str(label) if not pd.isna(label) else "—"
        result[key] = compute_match_stats(group)
    return result


def position_distribution(
    comparison_df: pd.DataFrame,
    aligned_df: pd.DataFrame,
    symbol: str,
) -> dict:
    """
    Count high / mid / low position days among matched rows only.

    Label source priority
    ---------------------
    1. ``{symbol}_PosLabel`` — string labels "高位" / "中位" / "低位"
    2. ``{symbol}_Pos30``    — numeric percentile; bucketed:
                               >= 67 → "高位", 34–66 → "中位", <= 33 → "低位"

    Parameters
    ----------
    comparison_df : pd.DataFrame
        Must contain ``Date`` and boolean ``match`` columns.
    aligned_df : pd.DataFrame
        Must contain ``Date`` and the position column(s) for ``symbol``.
    symbol : str
        Symbol whose position distribution to compute (e.g. ``"AVGO"``).

    Returns
    -------
    dict with keys:
        高位, 中位, 低位 (int),
        total_matched (int) — equals 高位 + 中位 + 低位 by construction,
        label_source ("PosLabel" | "Pos30" | "none")
    """
    _EMPTY: dict = {
        "高位": 0, "中位": 0, "低位": 0,
        "total_matched": 0, "label_source": "none",
    }

    if comparison_df.empty or "match" not in comparison_df.columns:
        return dict(_EMPTY)

    if "Date" not in comparison_df.columns or "Date" not in aligned_df.columns:
        return dict(_EMPTY)

    matched = comparison_df[comparison_df["match"] == True]
    if matched.empty:
        return dict(_EMPTY)

    pos_label_col = f"{symbol}_PosLabel"
    pos30_col     = f"{symbol}_Pos30"

    if pos_label_col in aligned_df.columns:
        label_source = "PosLabel"
        merged = matched[["Date"]].merge(
            aligned_df[["Date", pos_label_col]], on="Date", how="left"
        )
        labels = merged[pos_label_col].fillna("")

    elif pos30_col in aligned_df.columns:
        label_source = "Pos30"
        merged = matched[["Date"]].merge(
            aligned_df[["Date", pos30_col]], on="Date", how="left"
        )
        pos30  = pd.to_numeric(merged[pos30_col], errors="coerce")
        labels = pd.Series("中位", index=merged.index, dtype=object)
        labels[pos30 >= 67] = "高位"
        labels[pos30 <= 33] = "低位"
        labels[pos30.isna()] = ""

    else:
        return dict(_EMPTY)

    high = int((labels == "高位").sum())
    mid  = int((labels == "中位").sum())
    low  = int((labels == "低位").sum())

    return {
        "高位":          high,
        "中位":          mid,
        "低位":          low,
        "total_matched": high + mid + low,
        "label_source":  label_source,
    }
