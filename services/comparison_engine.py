"""services/comparison_engine.py

Field-level cross-symbol comparison for the data workbench.

Public API
----------
is_categorical_field(field) -> bool
    True for PosLabel, StageLabel, Code — fields compared by equality.

compare_field(aligned_df, field, sym_a, sym_b) -> pd.DataFrame
    Compare one field between two symbols on an aligned DataFrame.
    Returns a DataFrame with Date, both raw values, directions (numeric) or
    equality (categorical), and a boolean ``match`` column.
"""
from __future__ import annotations

import pandas as pd

# Fields compared by equality rather than direction
_CATEGORICAL_FIELDS: frozenset[str] = frozenset({"PosLabel", "StageLabel", "Code"})

# Minimum absolute percent move to count as "up" or "down"
_DIRECTION_THRESHOLD = 0.005  # 0.5 %


def is_categorical_field(field: str) -> bool:
    """Return True if ``field`` should be compared by equality (not direction)."""
    return field in _CATEGORICAL_FIELDS


def _direction_series(series: pd.Series) -> pd.Series:
    """
    Return a per-row direction string based on day-over-day percent change.

    Values: ``"up"`` / ``"down"`` / ``"flat"`` / ``"—"`` (first row or NaN).
    """
    pct = series.pct_change()
    result = pd.Series("flat", index=series.index, dtype=object)
    result[pct >  _DIRECTION_THRESHOLD] = "up"
    result[pct < -_DIRECTION_THRESHOLD] = "down"
    result[pct.isna()] = "—"
    return result


def compare_field(
    aligned_df: pd.DataFrame,
    field: str,
    sym_a: str,
    sym_b: str,
) -> pd.DataFrame:
    """
    Compare one field between two symbols on an already-aligned DataFrame.

    For **numeric** fields (Open, High, Low, Close, Volume, Pos30, Ret3, Ret5):
    - Computes day-over-day direction for each symbol.
    - ``match`` is True when both have the same non-"—" direction.

    For **categorical** fields (PosLabel, StageLabel, Code):
    - ``match`` is True when both values are equal and non-NaN.

    Parameters
    ----------
    aligned_df : pd.DataFrame
        Output of ``build_aligned_view``; must contain Date,
        ``{sym_a}_{field}``, and ``{sym_b}_{field}`` columns.
    field : str
        The field name (unprefixed).
    sym_a, sym_b : str
        Symbol names matching the column prefixes.

    Returns
    -------
    pd.DataFrame with columns:
        Date, {sym_a}_{field}, {sym_b}_{field},
        [dir_{sym_a}, dir_{sym_b}  — numeric fields only],
        match (bool)

    Raises
    ------
    ValueError — when required columns are absent from ``aligned_df``.
    """
    col_a = f"{sym_a}_{field}"
    col_b = f"{sym_b}_{field}"

    missing = [c for c in (col_a, col_b) if c not in aligned_df.columns]
    if missing:
        raise ValueError(f"字段列未找到: {', '.join(missing)}")

    result = aligned_df[["Date", col_a, col_b]].copy()

    if is_categorical_field(field):
        result["match"] = (
            result[col_a].notna()
            & result[col_b].notna()
            & (result[col_a] == result[col_b])
        )
    else:
        dir_a = _direction_series(result[col_a].astype(float))
        dir_b = _direction_series(result[col_b].astype(float))
        result[f"dir_{sym_a}"] = dir_a
        result[f"dir_{sym_b}"] = dir_b
        result["match"] = (dir_a == dir_b) & (dir_a != "—")

    return result
