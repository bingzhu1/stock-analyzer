#!/usr/bin/env python3
"""scripts/summarize_confidence_calibration_inputs.py — diagnostic CLI.

Read-only CLI wrapper around services.contract_calibration_inputs.
Prints the result as JSON to stdout. Never writes files; never modifies the DB.
This is a **diagnostic** tool — not a calibration engine.

Usage:
    python3 scripts/summarize_confidence_calibration_inputs.py
    python3 scripts/summarize_confidence_calibration_inputs.py --limit 100
    python3 scripts/summarize_confidence_calibration_inputs.py --symbol ALL
    python3 scripts/summarize_confidence_calibration_inputs.py --symbol NVDA --limit 50
    python3 scripts/summarize_confidence_calibration_inputs.py --db /path/to/avgo_agent.db
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.contract_calibration_inputs import (
    summarize_confidence_calibration_inputs,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate confidence-calibration inputs from prediction_log + outcome_log (read-only).",
    )
    parser.add_argument(
        "--db",
        default=None,
        help="Path to the SQLite DB. Defaults to services.prediction_store.DB_PATH.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Number of most-recent predictions to scan (default: 50; non-positive falls back to 50).",
    )
    parser.add_argument(
        "--symbol",
        default="AVGO",
        help='Symbol filter: "AVGO" (default), "ALL" for no filter, or any ticker. Case-insensitive; empty string falls back to "AVGO".',
    )
    args = parser.parse_args()

    result = summarize_confidence_calibration_inputs(
        db_path=args.db, limit=args.limit, symbol=args.symbol
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
