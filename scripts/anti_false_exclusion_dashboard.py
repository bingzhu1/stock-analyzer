#!/usr/bin/env python3
"""scripts/anti_false_exclusion_dashboard.py — read-only aggregate CLI.

Read-only CLI wrapper around
``services.anti_false_exclusion_dashboard.summarize_anti_false_exclusion_dashboard``.
Prints the aggregate JSON to stdout. Never writes files; never modifies
the DB.

Usage:
    python3 scripts/anti_false_exclusion_dashboard.py
    python3 scripts/anti_false_exclusion_dashboard.py --symbol AVGO --limit 450
    python3 scripts/anti_false_exclusion_dashboard.py --db avgo_agent.db --symbol AVGO --limit 450
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.anti_false_exclusion_dashboard import (
    summarize_anti_false_exclusion_dashboard,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only aggregate dashboard for anti-false-exclusion "
            "diagnostics: R4 / residual baseline metrics + survival cases "
            "+ hard-gate 6-item pass/fail."
        ),
    )
    parser.add_argument(
        "--db", default=None,
        help="SQLite DB path (default: services.prediction_store.DB_PATH)",
    )
    parser.add_argument(
        "--symbol", default="AVGO",
        help='Symbol filter (default: "AVGO")',
    )
    parser.add_argument(
        "--limit", type=int, default=450,
        help="Number of recent replay rows to scan when building the "
             "baseline (default: 450)",
    )
    args = parser.parse_args()

    result = summarize_anti_false_exclusion_dashboard(
        db_path=args.db, symbol=args.symbol, limit=args.limit,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
