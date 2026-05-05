"""scripts/run_real_continuous_smoothing_validation.py — real-run input wrapper.

Step 3R-3.3C-B implementation per Step 3R-3.3C design (commit
``226e354``) + checkpoint (``d2773aa``) + Step 3R-3.3C-A W1-W3 source
audit checkpoint (``1280060``).

This module assembles **inputs** for the validation pipeline: a list
of W1-W3 paired rows loaded from sqlite (read-only), a list of W4
replay rows loaded from a jsonl file, and a W4 manifest dict loaded
from a JSON file. It does **not** execute the validation pipeline.
``--prepare-inputs-only`` is the only CLI mode supported in v1; the
real execution step is intentionally not exposed here.

Read-only constraints:
- never writes DB; opens sqlite via ``mode=ro`` URI only
- never imports DB write paths, network clients, market-data clients,
  trading clients, or production-stack modules (see test file for the
  full forbidden-import list)
- never imports the dry-run orchestrator module;
  ``build_real_validation_inputs`` only assembles inputs and returns
  them
- never mutates input rows / manifest dict
- 2026 final-test cutoff: filtered out at every loader (DB + jsonl)
- DB guard: caller can fingerprint the DB before / after a future run
  and assert it has not changed
- No threshold sweep, no seed override

Public API:
    get_db_fingerprint(db_path) -> dict
    assert_db_unchanged(before, after) -> None
    load_w1_w3_rows_from_db(db_path, *, final_test_cutoff="2026-01-01") -> list[dict]
    load_w4_rows_from_jsonl(jsonl_path, *, final_test_cutoff="2026-01-01") -> list[dict]
    load_w4_manifest(path) -> dict
    build_static_regime_label_provider(*, regime_labels_template) -> Callable
    build_real_validation_inputs(*, db_path, w4_jsonl_path, w4_manifest_path,
                                 final_test_cutoff="2026-01-01") -> dict
    main(argv=None) -> int                # CLI entry; --prepare-inputs-only only

CLI:
    python3 scripts/run_real_continuous_smoothing_validation.py \\
        --prepare-inputs-only \\
        --db-path <path/to/db> \\
        --w4-jsonl <path/to/replay_results.jsonl> \\
        --w4-manifest <path/to/validation_manifest.json>

Without ``--prepare-inputs-only`` the CLI exits nonzero with a refusal
message.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable


BUNDLE_SCHEMA_VERSION = "real_validation_input_bundle.v1"
DEFAULT_FINAL_TEST_CUTOFF = "2026-01-01"
DEFAULT_SYMBOL = "AVGO"

# Fixed window boundaries (must match Step 3R-4.3A adapter DEFAULT_WINDOWS).
W1_START = "2023-01-03"
W1_END = "2023-08-31"
W2_START = "2023-09-01"
W2_END = "2024-02-29"
W3_START = "2024-03-01"
W3_END = "2024-08-02"

DB_SOURCE_TAG = "avgo_agent.db"
W4_SOURCE_TAG = "w4_jsonl"


# ── DB guard ─────────────────────────────────────────────────────────────


def get_db_fingerprint(db_path: str) -> dict[str, Any]:
    """Return a stat-based fingerprint of ``db_path``.

    Used to assert the DB has not changed across a real run.
    """
    p = Path(db_path)
    if not p.exists():
        return {
            "path": str(p),
            "exists": False,
            "mtime_ns": None,
            "size_bytes": None,
        }
    st = p.stat()
    return {
        "path": str(p),
        "exists": True,
        "mtime_ns": int(st.st_mtime_ns),
        "size_bytes": int(st.st_size),
    }


def assert_db_unchanged(before: dict[str, Any], after: dict[str, Any]) -> None:
    """Raise ``RuntimeError`` if mtime_ns or size_bytes differ.

    ``path``/``exists`` are not load-bearing for change detection; only
    mtime + size are.
    """
    if before.get("mtime_ns") != after.get("mtime_ns"):
        raise RuntimeError(
            "db_modified:mtime_ns_changed:"
            f"before={before.get('mtime_ns')!r},after={after.get('mtime_ns')!r}"
        )
    if before.get("size_bytes") != after.get("size_bytes"):
        raise RuntimeError(
            "db_modified:size_bytes_changed:"
            f"before={before.get('size_bytes')!r},after={after.get('size_bytes')!r}"
        )


# ── DB → W1-W3 row loader ────────────────────────────────────────────────


def _open_readonly(db_path: str) -> sqlite3.Connection:
    """Open ``db_path`` in read-only mode using URI form."""
    abs_path = os.path.abspath(db_path)
    uri = f"file:{abs_path}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def load_w1_w3_rows_from_db(
    db_path: str,
    *,
    final_test_cutoff: str = DEFAULT_FINAL_TEST_CUTOFF,
    symbol: str = DEFAULT_SYMBOL,
) -> list[dict[str, Any]]:
    """Read paired AVGO rows in W1-W3 from a read-only sqlite connection.

    Returned dicts conform to the ``replay_validation_records`` adapter
    row schema:

    - ``as_of_date`` (str) ← ``prediction_log.analysis_date``
    - ``prediction_for_date`` (str) ← ``prediction_log.prediction_for_date``
    - ``direction_correct`` (bool) ← ``bool(outcome_log.direction_correct)``
    - ``actual_close_change`` (float | None) ← direct
    - ``ready`` (bool) — always ``True`` (join already filters on
      ``direction_correct IS NOT NULL``)
    - ``source`` (str) — ``"avgo_agent.db"``

    Filters applied:
    - ``prediction_log.symbol = symbol``
    - ``outcome_log.direction_correct IS NOT NULL``
    - ``W1_START <= analysis_date <= W3_END``
    - ``analysis_date < final_test_cutoff``
    - ``prediction_for_date < final_test_cutoff``
    - ``prediction_for_date > analysis_date``  (anti-lookahead)
    """
    sql = """
        SELECT p.analysis_date,
               p.prediction_for_date,
               o.direction_correct,
               o.actual_close_change
          FROM prediction_log p
          JOIN outcome_log o ON o.prediction_id = p.id
         WHERE p.symbol = ?
           AND o.direction_correct IS NOT NULL
           AND p.analysis_date >= ?
           AND p.analysis_date <= ?
           AND p.analysis_date < ?
           AND p.prediction_for_date < ?
           AND p.prediction_for_date > p.analysis_date
         ORDER BY p.analysis_date, p.prediction_for_date
    """
    params = (
        symbol,
        W1_START,
        W3_END,
        final_test_cutoff,
        final_test_cutoff,
    )
    conn = _open_readonly(db_path)
    try:
        cur = conn.execute(sql, params)
        rows: list[dict[str, Any]] = []
        for analysis_date, pred_for, dc_int, change in cur:
            rows.append(
                {
                    "as_of_date": analysis_date,
                    "prediction_for_date": pred_for,
                    "direction_correct": bool(dc_int),
                    "actual_close_change": (
                        float(change) if change is not None else None
                    ),
                    "ready": True,
                    "source": DB_SOURCE_TAG,
                }
            )
        return rows
    finally:
        conn.close()


# ── W4 jsonl + manifest loaders ──────────────────────────────────────────


def load_w4_rows_from_jsonl(
    jsonl_path: str,
    *,
    final_test_cutoff: str = DEFAULT_FINAL_TEST_CUTOFF,
) -> list[dict[str, Any]]:
    """Read W4 replay rows from a jsonl file; filter final-test rows.

    Each surviving row is a deep copy of the on-disk dict with a
    ``source = "w4_jsonl"`` tag added. Original fields are preserved
    untouched.
    """
    rows: list[dict[str, Any]] = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                continue
            as_of = row.get("as_of_date")
            pred_for = row.get("prediction_for_date")
            if isinstance(as_of, str) and as_of >= final_test_cutoff:
                continue
            if isinstance(pred_for, str) and pred_for >= final_test_cutoff:
                continue
            enriched = deepcopy(row)
            enriched["source"] = W4_SOURCE_TAG
            rows.append(enriched)
    return rows


def load_w4_manifest(path: str) -> dict[str, Any]:
    """Read W4 manifest JSON file as a plain dict.

    Schema validation is intentionally NOT performed here; the dict is
    handed downstream to the adapter / helper which already contain the
    8-check W4 manifest gate.
    """
    with open(path, encoding="utf-8") as f:
        manifest = json.load(f)
    if not isinstance(manifest, dict):
        raise ValueError(
            f"w4 manifest at {path!r} is not a JSON object: {type(manifest).__name__}"
        )
    return manifest


# ── static regime_label_provider factory (mock-friendly) ─────────────────


def build_static_regime_label_provider(
    *,
    regime_labels_template: dict[str, Any],
) -> Callable[[str, dict[str, Any]], dict[str, Any]]:
    """Build a callable ``provider(as_of_date, row) -> regime_labels.v1``
    that returns a deep copy of the template with ``as_of_date`` and
    ``data_cutoff_date`` set to the row's ``as_of_date``.

    This is a **mock-friendly** factory only — it does NOT compute
    regime labels from market data. Real Step 3R-3.3C-C execution must
    inject a real provider that wraps ``services.regime_labels_builder``.
    """
    if not isinstance(regime_labels_template, dict):
        raise ValueError("regime_labels_template must be a dict")
    template = deepcopy(regime_labels_template)

    def _provider(as_of_date: str, _row: dict[str, Any]) -> dict[str, Any]:
        out = deepcopy(template)
        out["as_of_date"] = as_of_date
        out["data_cutoff_date"] = as_of_date
        return out

    return _provider


# ── input bundle assembler ───────────────────────────────────────────────


def _surface_w4_manifest_status(manifest: dict[str, Any]) -> str:
    """Cheap surface check; the authoritative gate is in adapter / helper."""
    if not isinstance(manifest, dict):
        return "error"
    if manifest.get("status") != "ok":
        return "error"
    if manifest.get("final_test_touched") is True:
        return "error"
    return "ok"


def build_real_validation_inputs(
    *,
    db_path: str,
    w4_jsonl_path: str,
    w4_manifest_path: str,
    final_test_cutoff: str = DEFAULT_FINAL_TEST_CUTOFF,
    symbol: str = DEFAULT_SYMBOL,
) -> dict[str, Any]:
    """Assemble the input bundle for a real W1-W4 validation run.

    Does **not** call the orchestrator; only loads + tags inputs and
    returns the bundle dict.
    """
    db_fingerprint = get_db_fingerprint(db_path)
    w1_w3_rows = load_w1_w3_rows_from_db(
        db_path,
        final_test_cutoff=final_test_cutoff,
        symbol=symbol,
    )
    w4_rows = load_w4_rows_from_jsonl(
        w4_jsonl_path,
        final_test_cutoff=final_test_cutoff,
    )
    w4_manifest = load_w4_manifest(w4_manifest_path)
    w4_manifest_status = _surface_w4_manifest_status(w4_manifest)

    warnings: list[str] = []
    if not w1_w3_rows:
        warnings.append("w1_w3_rows_empty")
    if not w4_rows:
        warnings.append("w4_rows_empty")
    if w4_manifest_status != "ok":
        warnings.append("w4_manifest_surface_status_not_ok")

    return {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "db_path": str(Path(db_path)),
        "db_fingerprint": db_fingerprint,
        "w1_w3_rows": w1_w3_rows,
        "w4_jsonl_path": str(Path(w4_jsonl_path)),
        "w4_rows": w4_rows,
        "w4_manifest_path": str(Path(w4_manifest_path)),
        "w4_manifest": w4_manifest,
        "final_test_cutoff": final_test_cutoff,
        "w4_manifest_status": w4_manifest_status,
        "warnings": warnings,
    }


# ── CLI ──────────────────────────────────────────────────────────────────


def _build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_real_continuous_smoothing_validation",
        description=(
            "Step 3R-3.3C-B real W1-W4 validation input wrapper. "
            "v1 only supports --prepare-inputs-only; real execution is "
            "deferred to Step 3R-3.3C-C and is intentionally not exposed."
        ),
    )
    parser.add_argument(
        "--prepare-inputs-only",
        action="store_true",
        help="Required: assemble + summarize input bundle without running.",
    )
    parser.add_argument("--db-path", default=None)
    parser.add_argument("--w4-jsonl", default=None)
    parser.add_argument("--w4-manifest", default=None)
    parser.add_argument(
        "--final-test-cutoff", default=DEFAULT_FINAL_TEST_CUTOFF
    )
    parser.add_argument("--symbol", default=DEFAULT_SYMBOL)
    return parser


def _summarize_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": bundle["schema_version"],
        "db_path": bundle["db_path"],
        "db_fingerprint": bundle["db_fingerprint"],
        "w1_w3_row_count": len(bundle["w1_w3_rows"]),
        "w4_jsonl_path": bundle["w4_jsonl_path"],
        "w4_row_count": len(bundle["w4_rows"]),
        "w4_manifest_path": bundle["w4_manifest_path"],
        "w4_manifest_status": bundle["w4_manifest_status"],
        "final_test_cutoff": bundle["final_test_cutoff"],
        "warnings": list(bundle["warnings"]),
    }


def main(argv: list[str] | None = None) -> int:
    parser = _build_cli_parser()
    args = parser.parse_args(argv)

    if not args.prepare_inputs_only:
        print(
            "Step 3R-3.3C-B: real validation execution is not enabled in "
            "this script. Pass --prepare-inputs-only to compute the input "
            "bundle metadata only.",
            file=sys.stderr,
        )
        return 2

    missing = [
        name
        for name, value in (
            ("--db-path", args.db_path),
            ("--w4-jsonl", args.w4_jsonl),
            ("--w4-manifest", args.w4_manifest),
        )
        if not value
    ]
    if missing:
        print(
            "Missing required arguments with --prepare-inputs-only: "
            + ", ".join(missing),
            file=sys.stderr,
        )
        return 2

    bundle = build_real_validation_inputs(
        db_path=args.db_path,
        w4_jsonl_path=args.w4_jsonl,
        w4_manifest_path=args.w4_manifest,
        final_test_cutoff=args.final_test_cutoff,
        symbol=args.symbol,
    )
    summary = _summarize_bundle(bundle)
    json.dump(summary, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
