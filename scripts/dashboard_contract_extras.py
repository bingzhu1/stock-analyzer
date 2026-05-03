#!/usr/bin/env python3
"""scripts/dashboard_contract_extras.py — print contract extras dashboard.

Read-only CLI wrapper around services.contract_payload_extras_dashboard.
Prints the result as JSON to stdout. Never writes files; never modifies the DB.

Usage:
    python3 scripts/dashboard_contract_extras.py
    python3 scripts/dashboard_contract_extras.py --limit 50
    python3 scripts/dashboard_contract_extras.py --symbol ALL
    python3 scripts/dashboard_contract_extras.py --symbol NVDA --limit 100
    python3 scripts/dashboard_contract_extras.py --db /path/to/avgo_agent.db
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.contract_payload_extras_dashboard import (
    summarize_contract_extras_dashboard,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate contract 04 / 05 / 07 extras across recent predictions (read-only).",
    )
    parser.add_argument(
        "--db",
        default=None,
        help="Path to the SQLite DB. Defaults to services.prediction_store.DB_PATH.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Number of most-recent predictions to scan (default: 20; non-positive falls back to 20).",
    )
    parser.add_argument(
        "--symbol",
        default="AVGO",
        help='Symbol filter: "AVGO" (default), "ALL" for no filter, or any ticker. Case-insensitive; empty string falls back to "AVGO".',
    )
    args = parser.parse_args()

    result = summarize_contract_extras_dashboard(
        db_path=args.db, limit=args.limit, symbol=args.symbol
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
