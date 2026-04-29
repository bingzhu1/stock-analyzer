"""Wiring batch historical replay cases into the projection record store.

Each replay case from
``services.historical_replay_training.run_historical_replay_for_date`` (or its
batch variant) is persisted as one ``projection_runs`` row plus the five
record blocks (Task 074) via the per-case ``save_projection_run`` orchestrator
defined in ``scripts/save_projection_records_smoke.py`` (Task 075).

This module adds NO new business logic — it only routes batch traffic into
the existing storage path while skipping degraded cases safely.

Public API
----------
build_replay_run_id(symbol, as_of_date, prediction_for_date) -> str
save_replay_case_projection_records(conn, replay_result) -> dict
save_replay_batch_projection_records(conn, batch_result) -> dict

Three-system independence is preserved by construction: every per-case write
goes through the same ``save_projection_run`` orchestrator that Task 075
already verified, which writes to five separate tables and never copies
record_02 fields into sibling blocks.
"""

from __future__ import annotations

import importlib.util
import sqlite3
from pathlib import Path
from typing import Any

from services.projection_three_systems_renderer import build_projection_three_systems


# ── bootstrap: import save_projection_run from scripts/ via importlib ──────

def _load_smoke_module() -> Any:
    """Lazy-import ``scripts/save_projection_records_smoke.py`` once.

    The smoke script's ``save_projection_run`` is the canonical orchestrator
    that calls ``create_projection_run`` + 5× ``save_*``. We reuse it here
    rather than duplicating extractor logic.
    """
    smoke_path = Path(__file__).resolve().parent.parent / "scripts" / "save_projection_records_smoke.py"
    spec = importlib.util.spec_from_file_location(
        "save_projection_records_smoke", smoke_path
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load smoke module from {smoke_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_smoke_module = _load_smoke_module()
_save_projection_run = _smoke_module.save_projection_run


# ── helpers ────────────────────────────────────────────────────────────────

def _normalize_symbol(symbol: Any) -> str:
    text = str(symbol or "").strip().upper()
    return text or "AVGO"


def _clean_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


# ── deterministic run_id ───────────────────────────────────────────────────

def build_replay_run_id(
    symbol: str,
    as_of_date: str,
    prediction_for_date: str,
) -> str:
    """Build a deterministic run_id for one replay case.

    Format::

        {SYMBOL}_{as_of_date}_to_{prediction_for_date}_replay

    Example::

        build_replay_run_id("AVGO", "2026-04-24", "2026-04-27")
        → "AVGO_2026-04-24_to_2026-04-27_replay"
    """
    sym = _normalize_symbol(symbol)
    a = _clean_str(as_of_date)
    p = _clean_str(prediction_for_date)
    return f"{sym}_{a}_to_{p}_replay"


# ── per-case save ──────────────────────────────────────────────────────────

_COMPLETENESS_KEYS = (
    "record_01_structure",
    "record_02_projection",
    "negative_system_records",
    "record_03_confidence",
    "final_summary_records",
)


def _skip(run_id: str | None, reason: str) -> dict[str, Any]:
    return {
        "saved": False,
        "run_id": run_id,
        "skip_reason": reason,
        "completeness": None,
    }


def save_replay_case_projection_records(
    conn: sqlite3.Connection,
    replay_result: dict[str, Any],
) -> dict[str, Any]:
    """Persist one replay case to the projection record store.

    Returns a summary dict with ``saved / run_id / skip_reason / completeness``.
    Never raises on degraded inputs — callers can branch on ``saved``.

    Skip rules:
      - ``replay_result.ready`` is not truthy
      - ``projection_snapshot`` is missing or empty
      - ``as_of_date`` or ``prediction_for_date`` is missing
    """
    case = replay_result if isinstance(replay_result, dict) else {}

    if not case.get("ready"):
        return _skip(None, "replay_result.ready is False")

    snapshot = case.get("projection_snapshot")
    if not isinstance(snapshot, dict) or not snapshot:
        return _skip(None, "projection_snapshot is missing or empty")

    symbol = _normalize_symbol(case.get("symbol"))
    as_of_date = _clean_str(case.get("as_of_date"))
    prediction_for_date = _clean_str(case.get("prediction_for_date"))

    if not as_of_date:
        return _skip(None, "as_of_date is missing")
    if not prediction_for_date:
        return _skip(None, "prediction_for_date is missing")

    three_systems = build_projection_three_systems(snapshot, symbol=symbol)
    run_id = build_replay_run_id(symbol, as_of_date, prediction_for_date)

    saved_id = _save_projection_run(
        conn,
        symbol=symbol,
        as_of_date=as_of_date,
        prediction_for_date=prediction_for_date,
        projection_v2_raw=snapshot,
        three_systems=three_systems,
        run_id=run_id,
        status="complete",
    )

    completeness = {key: True for key in _COMPLETENESS_KEYS}

    return {
        "saved": True,
        "run_id": saved_id,
        "skip_reason": None,
        "completeness": completeness,
    }


# ── batch save ─────────────────────────────────────────────────────────────

def save_replay_batch_projection_records(
    conn: sqlite3.Connection,
    batch_result: dict[str, Any],
) -> dict[str, Any]:
    """Iterate ``batch_result["results"]`` and persist each ready case.

    Per-case exceptions are caught and counted in ``failed_cases``; the
    batch never aborts on a single bad case. Returns counts and the list
    of saved run_ids in the order they were persisted.
    """
    batch = batch_result if isinstance(batch_result, dict) else {}
    raw_results = batch.get("results")
    results = raw_results if isinstance(raw_results, list) else []

    total = len(results)
    saved = 0
    skipped = 0
    failed = 0
    run_ids: list[str] = []

    for case in results:
        try:
            outcome = save_replay_case_projection_records(conn, case)
        except Exception:
            failed += 1
            continue

        if outcome.get("saved"):
            saved += 1
            rid = outcome.get("run_id")
            if rid:
                run_ids.append(str(rid))
        else:
            skipped += 1

    return {
        "total_cases": total,
        "saved_cases": saved,
        "skipped_cases": skipped,
        "failed_cases": failed,
        "run_ids": run_ids,
    }
