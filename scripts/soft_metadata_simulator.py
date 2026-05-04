#!/usr/bin/env python3
"""scripts/soft_metadata_simulator.py — read-only sidecar CLI.

CLI wrapper around services.soft_metadata_simulator. Prints the sidecar
JSON to stdout. Never writes files; never modifies the DB. This is a
**diagnostic** sidecar — not a calibration engine, not a confidence-score
writer, not a trade decision tool.

Usage:
    # Build baseline only (no payload to simulate):
    python3 scripts/soft_metadata_simulator.py --symbol AVGO --limit 450

    # Simulate a single payload from a JSON string:
    python3 scripts/soft_metadata_simulator.py --payload-json '{"current_structure": {...}, ...}'

    # Simulate a single payload from a file:
    python3 scripts/soft_metadata_simulator.py --payload-file /path/to/payload.json

    # Override DB / coded_data location:
    python3 scripts/soft_metadata_simulator.py --db avgo_agent.db --coded-data-dir ./coded_data
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.soft_metadata_simulator import (
    DEFAULT_FINAL_TEST_CUTOFF,
    build_soft_metadata_baseline,
    simulate_soft_metadata,
)
from services.regime_diagnostics_dashboard import (
    _read_coded_csv as _dashboard_read_csv,
    _compute_pos20 as _dashboard_compute_pos20,
    _compute_nday_return as _dashboard_compute_nday_return,
    _PEER_FOR_REGIME,
    _resolve_coded_data_dir as _dashboard_resolve_coded_dir,
)


def _load_payload(args: argparse.Namespace) -> dict | None:
    if args.payload_json:
        return json.loads(args.payload_json)
    if args.payload_file:
        with open(args.payload_file, "r", encoding="utf-8") as fh:
            return json.load(fh)
    return None


def _regime_features_for_payload(
    payload: dict,
    coded_data_dir: str | None,
    symbol: str,
) -> dict | None:
    """Compute pos20 + avgo_minus_soxx_20d at the payload's analysis_date.

    CLI helper only — the simulator core does not read CSV. Returns None
    when CSV / dates are missing; the simulator will then emit a
    ``missing_regime_features`` warning.
    """
    cs = payload.get("current_structure") or {}
    adate = cs.get("analysis_date")
    if not isinstance(adate, str) or not adate:
        return None
    coded_dir = _dashboard_resolve_coded_dir(coded_data_dir)
    avgo = _dashboard_read_csv(symbol, coded_dir)
    soxx = _dashboard_read_csv(_PEER_FOR_REGIME, coded_dir)
    if not avgo:
        return None
    pos20, _reason = _dashboard_compute_pos20(avgo, adate)
    diff = None
    if soxx:
        a = _dashboard_compute_nday_return(avgo, adate)
        s = _dashboard_compute_nday_return(soxx, adate)
        if a is not None and s is not None:
            diff = a - s
    return {"pos20": pos20, "avgo_minus_soxx_20d": diff}


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build the soft_metadata.v1 sidecar for a single contract "
            "payload (read-only)."
        ),
    )
    parser.add_argument("--db", default=None,
                        help="SQLite DB path (default: services.prediction_store.DB_PATH)")
    parser.add_argument("--symbol", default="AVGO",
                        help='Symbol filter for baseline (default: "AVGO")')
    parser.add_argument("--limit", type=int, default=450,
                        help="Number of recent replay rows to scan when "
                             "building the baseline (default: 450)")
    parser.add_argument("--coded-data-dir", default=None,
                        help="Override coded_data CSV directory (default: <cwd>/coded_data)")
    parser.add_argument("--payload-json", default=None,
                        help="Inline JSON contract_payload to simulate")
    parser.add_argument("--payload-file", default=None,
                        help="Path to a JSON contract_payload file to simulate")
    parser.add_argument("--no-baseline", action="store_true",
                        help="Skip baseline build (simulator runs with baseline=None)")
    parser.add_argument("--analysis-date", default=None,
                        help="Override analysis_date for the cutoff check")
    parser.add_argument("--final-test-cutoff", default=DEFAULT_FINAL_TEST_CUTOFF,
                        help=f"Refuse signals when analysis_date >= cutoff "
                             f"(default: {DEFAULT_FINAL_TEST_CUTOFF})")
    args = parser.parse_args()

    payload = _load_payload(args)

    baseline = None
    if not args.no_baseline:
        baseline = build_soft_metadata_baseline(
            db_path=args.db, symbol=args.symbol, limit=args.limit,
            coded_data_dir=args.coded_data_dir,
        )

    if payload is None:
        # No payload to simulate — return baseline as the top-level output.
        result = {
            "mode": "baseline_only",
            "baseline": baseline,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 0

    regime_features = _regime_features_for_payload(
        payload, args.coded_data_dir, args.symbol,
    )
    sidecar = simulate_soft_metadata(
        payload,
        regime_features=regime_features,
        baseline=baseline,
        analysis_date=args.analysis_date,
        final_test_cutoff=args.final_test_cutoff,
    )
    print(json.dumps(sidecar, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
