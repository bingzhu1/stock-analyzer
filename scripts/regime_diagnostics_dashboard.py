#!/usr/bin/env python3
"""scripts/regime_diagnostics_dashboard.py — diagnostic CLI.

Read-only CLI wrapper around services.regime_diagnostics_dashboard.
Prints the result as JSON to stdout. Never writes files; never modifies
the DB. This is a **diagnostic** tool — not a calibration engine, not a
confidence-score writer.

Usage:
    python3 scripts/regime_diagnostics_dashboard.py
    python3 scripts/regime_diagnostics_dashboard.py --symbol AVGO --limit 450
    python3 scripts/regime_diagnostics_dashboard.py --db avgo_agent.db --symbol AVGO --limit 450
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.regime_diagnostics_dashboard import (
    summarize_regime_diagnostics_dashboard,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only regime diagnostics over replay rows in "
            "prediction_log + outcome_log."
        ),
    )
    parser.add_argument(
        "--db",
        default=None,
        help=(
            "Path to the SQLite DB. Defaults to "
            "services.prediction_store.DB_PATH."
        ),
    )
    parser.add_argument(
        "--symbol",
        default="AVGO",
        help='Symbol to diagnose (default: "AVGO").',
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=450,
        help=(
            "Number of most-recent replay rows to scan (default: 450; "
            "non-positive falls back to 450)."
        ),
    )
    parser.add_argument(
        "--coded-data-dir",
        default=None,
        help=(
            "Override coded_data CSV directory. Defaults to "
            "<cwd>/coded_data. Useful for tests; production replay code "
            "uses the same default."
        ),
    )
    args = parser.parse_args()

    result = summarize_regime_diagnostics_dashboard(
        db_path=args.db,
        symbol=args.symbol,
        limit=args.limit,
        coded_data_dir=args.coded_data_dir,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
