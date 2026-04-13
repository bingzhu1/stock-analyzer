"""services/stats_engine.py

Simple summary statistics for cross-symbol comparisons.

Public API
----------
compute_match_stats(comparison_df) -> dict
    Returns matched / mismatched / total / match_rate from a comparison
    DataFrame produced by ``comparison_engine.compare_field``.

distribution_by_label(comparison_df, label_col) -> dict[str, dict]
    Breaks down match stats by a categorical label column.
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
