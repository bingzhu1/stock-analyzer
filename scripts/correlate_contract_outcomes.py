#!/usr/bin/env python3
"""scripts/correlate_contract_outcomes.py — print outcome × contract hit-rate.

Read-only CLI wrapper around services.contract_outcome_correlation. Prints
the result as JSON to stdout. Never writes files; never modifies the DB.

Usage:
    python3 scripts/correlate_contract_outcomes.py
    python3 scripts/correlate_contract_outcomes.py --limit 100
    python3 scripts/correlate_contract_outcomes.py --db /path/to/avgo_agent.db
    python3 scripts/correlate_contract_outcomes.py --symbol ALL
    python3 scripts/correlate_contract_outcomes.py --symbol NVDA
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.contract_outcome_correlation import correlate_outcomes_with_contract


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Correlate contract field values with outcomes (read-only)."
    )
    parser.add_argument(
        "--db",
        default=None,
        help="Path to the SQLite DB. Defaults to services.prediction_store.DB_PATH.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=30,
        help="Number of most-recent predictions to scan (default: 30; non-positive falls back to 30).",
    )
    parser.add_argument(
        "--symbol",
        default="AVGO",
        help='Symbol filter: "AVGO" (default), "ALL" for no filter, or any ticker. Case-insensitive; empty string falls back to "AVGO".',
    )
    args = parser.parse_args()

    result = correlate_outcomes_with_contract(
        db_path=args.db, limit=args.limit, symbol=args.symbol
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
