#!/usr/bin/env python3
"""scripts/diff_latest_contract_payloads.py — print diff of two latest contracts.

Read-only CLI wrapper around services.contract_payload_diff. Prints the
diff result as JSON to stdout. Never writes files; never modifies the DB.

Usage:
    python3 scripts/diff_latest_contract_payloads.py
    python3 scripts/diff_latest_contract_payloads.py --db /path/to/avgo_agent.db
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.contract_payload_diff import diff_latest_contract_payloads


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Diff the contract payloads of the two most recent predictions (read-only)."
    )
    parser.add_argument(
        "--db",
        default=None,
        help="Path to the SQLite DB. Defaults to services.prediction_store.DB_PATH.",
    )
    args = parser.parse_args()

    result = diff_latest_contract_payloads(db_path=args.db)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
