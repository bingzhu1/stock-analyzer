#!/usr/bin/env python3
"""scripts/plan_contract_replay.py — dry-run replay (D, D+1) planner CLI.

Read-only CLI wrapper around services.contract_replay_planner. Prints
the result as JSON to stdout. Never writes files; never modifies the DB;
never calls yfinance or any network.

Usage:
    python3 scripts/plan_contract_replay.py
    python3 scripts/plan_contract_replay.py --start 2024-01-01 --end 2024-06-30
    python3 scripts/plan_contract_replay.py --limit 100
    python3 scripts/plan_contract_replay.py --symbol NVDA
    python3 scripts/plan_contract_replay.py --coded-data-dir /path/to/coded_data
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.contract_replay_planner import plan_contract_replay


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Dry-run enumerate replay (as_of_date, prediction_for_date) pairs from coded_data CSV (read-only).",
    )
    parser.add_argument(
        "--symbol",
        default="AVGO",
        help='Symbol filter (default "AVGO"). Per-symbol; "ALL" is not supported. Case-insensitive.',
    )
    parser.add_argument(
        "--start",
        default=None,
        help="Inclusive start date YYYY-MM-DD. Default: no lower bound.",
    )
    parser.add_argument(
        "--end",
        default=None,
        help="Inclusive end date YYYY-MM-DD. Default: no upper bound.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=30,
        help="Maximum candidate pairs to return (default: 30; non-positive falls back to 30).",
    )
    parser.add_argument(
        "--coded-data-dir",
        default=None,
        help="Path to coded_data directory. Default: ./coded_data relative to CWD.",
    )
    args = parser.parse_args()

    result = plan_contract_replay(
        symbol=args.symbol,
        start_date=args.start,
        end_date=args.end,
        limit=args.limit,
        coded_data_dir=args.coded_data_dir,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
