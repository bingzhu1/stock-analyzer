"""services/real_regime_label_provider.py — local CSV regime label provider.

Step 3R-3.3C-C-B implementation per Step 3R-3.3C real validation
execution design (commit ``9720e0a``) + checkpoint (``b1d82ee``) +
Step 3R-3.3C-C-A market data source audit checkpoint (``4282058``).

This module is **read-only diagnostics**:
- never reads DB / network; never imports sqlite write paths, network
  clients, market-data clients, trading clients, or production-stack
  modules (see test file for the full forbidden-import list)
- loads four local OHLC CSV files **once** at factory time and keeps
  them in a closure
- builder anti-lookahead is enforced inside
  ``services.regime_labels_builder.build_regime_labels``; this provider
  never reads ``Close`` / ``High`` / ``Low`` rows directly itself
- the ``row`` argument the provider receives from the orchestrator is
  intentionally **ignored** for feature computation: the builder is the
  only feature source. This prevents leaking outcome / W4 / prediction
  fields into the candidate.
- 2026 final-test cutoff is propagated to the builder; the builder
  returns ``final_test_refusal=True`` + all-unknown labels when
  ``as_of_date >= cutoff``.

Public API:
    build_real_regime_label_provider(
        *,
        avgo_csv_path="data/AVGO.csv",
        nvda_csv_path="data/NVDA.csv",
        soxx_csv_path="data/SOXX.csv",
        qqq_csv_path="data/QQQ.csv",
        final_test_cutoff="2026-01-01",
    ) -> Callable[[str, dict | None], dict]
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from services.regime_labels_builder import build_regime_labels


REQUIRED_COLUMNS: tuple[str, ...] = ("Date", "Open", "High", "Low", "Close")
DEFAULT_FINAL_TEST_CUTOFF = "2026-01-01"

DEFAULT_AVGO_CSV_PATH = "data/AVGO.csv"
DEFAULT_NVDA_CSV_PATH = "data/NVDA.csv"
DEFAULT_SOXX_CSV_PATH = "data/SOXX.csv"
DEFAULT_QQQ_CSV_PATH = "data/QQQ.csv"


def _load_market_csv(path: str, *, symbol: str):
    """Load a single OHLC CSV; fail fast on missing file / column / dup date."""
    import pandas as pd

    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(
            f"market data csv missing for {symbol}: {csv_path}"
        )
    df = pd.read_csv(csv_path)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            f"market data csv for {symbol} ({csv_path}) is missing required "
            f"columns: {missing}; required: {list(REQUIRED_COLUMNS)}"
        )
    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date").reset_index(drop=True)
    if df["Date"].duplicated().any():
        raise ValueError(
            f"market data csv for {symbol} ({csv_path}) contains duplicate "
            f"Date entries"
        )
    return df


def build_real_regime_label_provider(
    *,
    avgo_csv_path: str = DEFAULT_AVGO_CSV_PATH,
    nvda_csv_path: str = DEFAULT_NVDA_CSV_PATH,
    soxx_csv_path: str = DEFAULT_SOXX_CSV_PATH,
    qqq_csv_path: str = DEFAULT_QQQ_CSV_PATH,
    final_test_cutoff: str = DEFAULT_FINAL_TEST_CUTOFF,
) -> Callable[..., dict[str, Any]]:
    """Build a regime label provider closed over four locally-loaded CSVs.

    Returned callable signature:

        provider(as_of_date: str, row: dict | None = None) -> dict

    The ``row`` argument is intentionally ignored for feature
    computation; only ``as_of_date`` flows into the builder. This keeps
    the provider isolated from any outcome / replay-jsonl side
    information.
    """
    avgo_df = _load_market_csv(avgo_csv_path, symbol="AVGO")
    nvda_df = _load_market_csv(nvda_csv_path, symbol="NVDA")
    soxx_df = _load_market_csv(soxx_csv_path, symbol="SOXX")
    qqq_df = _load_market_csv(qqq_csv_path, symbol="QQQ")

    peer_dfs = {"NVDA": nvda_df, "SOXX": soxx_df, "QQQ": qqq_df}
    market_dfs = {"QQQ": qqq_df, "SOXX": soxx_df}

    def _provider(
        as_of_date: str,
        row: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        del row  # row is deliberately not consulted; only as_of_date matters
        return build_regime_labels(
            avgo_df,
            peer_dfs=peer_dfs,
            market_dfs=market_dfs,
            as_of_date=as_of_date,
            final_test_cutoff=final_test_cutoff,
        )

    return _provider
