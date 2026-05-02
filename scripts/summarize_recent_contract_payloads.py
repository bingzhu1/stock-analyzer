#!/usr/bin/env python3
"""scripts/summarize_recent_contract_payloads.py — print contract field trend.

Read-only CLI wrapper around services.contract_payload_trend. Prints the
aggregation result as JSON to stdout. Never writes files; never modifies the DB.

Usage:
    python3 scripts/summarize_recent_contract_payloads.py
    python3 scripts/summarize_recent_contract_payloads.py --limit 30
    python3 scripts/summarize_recent_contract_payloads.py --db /path/to/avgo_agent.db
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.contract_payload_trend import summarize_recent_contract_payloads


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize the most recent N predictions' contract payloads (read-only)."
    )
    parser.add_argument(
        "--db",
        default=None,
        help="Path to the SQLite DB. Defaults to services.prediction_store.DB_PATH.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Number of most-recent rows to scan (default: 10; non-positive falls back to 10).",
    )
    args = parser.parse_args()

    result = summarize_recent_contract_payloads(db_path=args.db, limit=args.limit)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
