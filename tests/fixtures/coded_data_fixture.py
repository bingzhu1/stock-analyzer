"""Shared fixture: synthesize a coded_data/ directory for projection-chain tests.

Tests that exercise the real Scan + Predict pipeline need
``coded_data/AVGO_coded.csv`` (and the other supported symbols' CSVs) to exist.
The repo does not ship this file, so tests must monkey-patch the two
module-level paths that read it:

    matcher.CODED_FILE                — used by load_coded_avgo()
    services.data_query._CODED_DIR    — used by load_symbol_data()

Both attributes are read at call-time, so patching them after import is enough.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_SUPPORTED_SYMBOLS = ("AVGO", "NVDA", "SOXX", "QQQ")


def _write_synthetic_coded_csv(path: Path, n: int = 60) -> None:
    """Write a minimal coded-CSV with enough rows for 30-day rolling windows."""
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    base = 100.0
    df = pd.DataFrame({
        "Date":      [d.strftime("%Y-%m-%d") for d in dates],
        "Open":      [base + i * 0.5             for i in range(n)],
        "High":      [base + i * 0.5 + 2.0       for i in range(n)],
        "Low":       [base + i * 0.5 - 1.5       for i in range(n)],
        "Close":     [base + i * 0.5 + 0.3       for i in range(n)],
        "Adj Close": [base + i * 0.5 + 0.3       for i in range(n)],
        "Volume":    [1_000_000 + i * 5_000      for i in range(n)],
        "Code":      ["32233"] * n,
    })
    df.to_csv(path, index=False)


def install_synthetic_coded_data() -> dict[str, Any]:
    """Create a tmpdir with synthetic CSVs and patch the two coded-data paths.

    Returns a state dict that must be passed to
    :func:`restore_synthetic_coded_data` from tearDown.
    """
    import matcher
    from services import data_query

    tmpdir = Path(tempfile.mkdtemp(prefix="coded_data_"))
    for symbol in _SUPPORTED_SYMBOLS:
        _write_synthetic_coded_csv(tmpdir / f"{symbol}_coded.csv")

    state: dict[str, Any] = {
        "tmpdir": tmpdir,
        "original_matcher_file": matcher.CODED_FILE,
        "original_dq_dir": data_query._CODED_DIR,
    }
    matcher.CODED_FILE = tmpdir / "AVGO_coded.csv"
    data_query._CODED_DIR = tmpdir
    return state


def restore_synthetic_coded_data(state: dict[str, Any]) -> None:
    """Undo :func:`install_synthetic_coded_data` and remove the tmpdir."""
    import matcher
    from services import data_query

    matcher.CODED_FILE = state["original_matcher_file"]
    data_query._CODED_DIR = state["original_dq_dir"]
    shutil.rmtree(state["tmpdir"], ignore_errors=True)
