"""services/multi_symbol_view.py

Build a date-aligned multi-symbol view for the data workbench.

Public API
----------
build_aligned_view(symbols, window, fields, *, _loader) -> pd.DataFrame
    Inner-joins data for each symbol on Date, prefixing each value column with
    the symbol name (e.g. AVGO_Close, NVDA_Close).  Tails to `window` rows.
"""
from __future__ import annotations

from typing import Callable

import pandas as pd

from services.data_query import load_symbol_data


def build_aligned_view(
    symbols: list[str],
    window: int = 20,
    fields: list[str] | None = None,
    *,
    _loader: Callable[..., pd.DataFrame] | None = None,
) -> pd.DataFrame:
    """
    Load data for each symbol and inner-join on Date.

    Columns in the result are prefixed with the symbol name, e.g.::

        Date  AVGO_Close  NVDA_Close  AVGO_High  NVDA_High

    Parameters
    ----------
    symbols : list[str]
        Symbols to include.  Duplicate entries are deduplicated.
    window : int
        Number of most-recent aligned rows to return (0 = all).
    fields : list[str] | None
        Fields to include per symbol.  None → default OHLCV.
    _loader : callable, optional
        Injected data loader for tests; defaults to ``load_symbol_data``.

    Returns
    -------
    pd.DataFrame — empty DataFrame when ``symbols`` is empty or no dates align.

    Raises
    ------
    ValueError / FileNotFoundError — propagated from the underlying loader.
    """
    if not symbols:
        return pd.DataFrame()

    loader = _loader or load_symbol_data
    seen: set[str] = set()
    unique_symbols = [s.upper() for s in symbols if s.upper() not in seen and not seen.add(s.upper())]  # type: ignore[func-returns-value]

    # Load full history for each symbol (window=0) so the inner join can align
    # on all available dates before slicing to the requested window.
    dfs: list[pd.DataFrame] = []
    for sym in unique_symbols:
        df = loader(sym, window=0, fields=fields)
        df = df.rename(columns={c: f"{sym}_{c}" for c in df.columns if c != "Date"})
        dfs.append(df)

    if not dfs:
        return pd.DataFrame()

    result = dfs[0]
    for df in dfs[1:]:
        result = result.merge(df, on="Date", how="inner")

    if window > 0:
        result = result.tail(window).reset_index(drop=True)

    return result
