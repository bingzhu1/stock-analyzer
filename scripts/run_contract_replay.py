#!/usr/bin/env python3
"""scripts/run_contract_replay.py — replay (D, D+1) writer CLI (skeleton).

Step 2F-4c-1: thin CLI wrapper around
``services.contract_replay_writer.run_contract_replay``. Defaults to
``dry_run=True`` (no DB writes). The current skeleton returns
``status="not_implemented_for_write"`` when ``--write`` is supplied;
real write logic lands in Step 2F-4c-2.

Prints the result as JSON to stdout. Never modifies files. Never calls
yfinance / network.

Usage (all dry-run by default):
    python3 scripts/run_contract_replay.py
    python3 scripts/run_contract_replay.py --start 2024-01-01 --end 2024-01-31
    python3 scripts/run_contract_replay.py --limit 50

Real-write attempt (currently a stub):
    python3 scripts/run_contract_replay.py --write
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.contract_replay_writer import (
    _DEFAULT_LIMIT,
    _LIMIT_HARD_CAP,
    run_contract_replay,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a contract replay batch (Step 2F-4c-1: dry-run skeleton).",
    )
    parser.add_argument(
        "--symbol",
        default="AVGO",
        help='Symbol filter (default "AVGO"). Per-symbol; "ALL" is rejected by the planner.',
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
        default=_DEFAULT_LIMIT,
        help=(
            f"Maximum candidate pairs (default {_DEFAULT_LIMIT}; "
            f"hard cap {_LIMIT_HARD_CAP})."
        ),
    )
    parser.add_argument(
        "--coded-data-dir",
        default=None,
        help="Path to coded_data directory. Default: ./coded_data relative to CWD.",
    )
    parser.add_argument(
        "--db",
        default=None,
        help="Path to the SQLite DB. Defaults to services.prediction_store.DB_PATH (only used by 4c-2 real-write path).",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Disable dry-run and attempt real writes. Currently returns "
             "not_implemented_for_write (Step 2F-4c-1 skeleton); use 4c-2 "
             "once that lands.",
    )
    args = parser.parse_args()

    result = run_contract_replay(
        symbol=args.symbol,
        start_date=args.start,
        end_date=args.end,
        limit=args.limit,
        coded_data_dir=args.coded_data_dir,
        dry_run=not args.write,
        db_path=args.db,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
