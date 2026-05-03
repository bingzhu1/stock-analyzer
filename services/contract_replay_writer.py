"""services/contract_replay_writer.py — replay (D, D+1) writer skeleton.

Step 2F-4c-1: dry-run-only writer skeleton. Wraps
``services.contract_replay_planner.plan_contract_replay`` to produce the
same (D, D+1) candidate pairs, but adds the layer where future writes
**would** happen.

Today this skeleton is intentionally incomplete: the actual
``run_predict + save_prediction(analysis_date_override=D) +
save_outcome(captured_at_override=D+1)`` chain is **NOT** wired. Calling
with ``dry_run=False`` returns status ``"not_implemented_for_write"`` and
writes nothing. Step 2F-4c-2 will fill in the real write logic.

This shape exists so that:
- callers can already plumb the writer into scripts / orchestrators
- the safety bounds (default ``dry_run=True``, hard cap on ``limit``) are
  established and tested before any real write path is attempted
- the planner-result pass-through is contract-tested so 4c-2 only adds
  the actual writes, not the surrounding shape

Public API:
    run_contract_replay(
        symbol="AVGO",
        start_date=None,
        end_date=None,
        limit=30,
        coded_data_dir=None,
        dry_run=True,
        db_path=None,
    ) -> dict

Status values:
    "ok"                          — dry-run completed; would-write count reported
    "missing_data"                — planner could not find data (passthrough)
    "insufficient_data"           — planner had < 2 trading days (passthrough)
    "error"                       — planner / arg validation failed (passthrough)
    "not_implemented_for_write"   — dry_run=False but write path is 4c-2 scope
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from services.contract_replay_planner import plan_contract_replay


_DEFAULT_LIMIT = 30
# Writer is higher-risk than planner (will eventually write DB rows). Cap the
# limit so a fat-fingered ``--limit 5000`` cannot accidentally enumerate a
# huge candidate list. The cap is intentionally tighter than any anticipated
# Step 2F-4c-2 / 4d batch size; raise it deliberately when those steps land.
_LIMIT_HARD_CAP = 50


def _resolve_writer_limit(limit: Any) -> int:
    """Coerce limit to a positive int and clamp to ``_LIMIT_HARD_CAP``.

    Mirrors the planner's defensive checks (bool / non-int / <= 0 → default)
    and adds an upper clamp because the writer can in principle drive real
    DB writes.
    """
    if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        return _DEFAULT_LIMIT
    if limit > _LIMIT_HARD_CAP:
        return _LIMIT_HARD_CAP
    return limit


def run_contract_replay(
    symbol: str = "AVGO",
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = _DEFAULT_LIMIT,
    coded_data_dir: str | Path | None = None,
    *,
    dry_run: bool = True,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Plan + (eventually) write a 30-day replay batch.

    Read-only when ``dry_run=True`` (the default). When
    ``dry_run=False``, the current Step 2F-4c-1 skeleton returns status
    ``"not_implemented_for_write"`` and writes nothing.
    """
    capped_limit = _resolve_writer_limit(limit)

    planner_result = plan_contract_replay(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        limit=capped_limit,
        coded_data_dir=coded_data_dir,
    )

    candidate_pairs: list[dict[str, str]] = planner_result.get(
        "candidate_pairs", []
    )

    base: dict[str, Any] = {
        "symbol": planner_result.get("symbol", symbol),
        "dry_run": bool(dry_run),
        "requested_limit": planner_result.get(
            "requested_limit", capped_limit
        ),
        "planner_status": planner_result.get("status"),
        "candidate_pair_count": len(candidate_pairs),
        "would_write_count": 0,
        "written_prediction_count": 0,
        "written_outcome_count": 0,
        "candidate_pairs": candidate_pairs,
        "planner_result": planner_result,
        "db_path": str(db_path) if db_path is not None else None,
        "notes": [],
    }

    # Passthrough for non-ok planner outcomes — nothing to replay.
    if planner_result.get("status") != "ok":
        passthrough_status = planner_result.get("status", "error")
        return {
            **base,
            "status": passthrough_status,
            "notes": [
                f"planner returned status={passthrough_status!r}; "
                "no candidate pairs available, nothing was written",
            ],
        }

    if dry_run:
        return {
            **base,
            "status": "ok",
            "would_write_count": len(candidate_pairs),
            "notes": [
                "dry_run=True: no prediction/outcome records were written",
                "candidate_pairs were enumerated by plan_contract_replay; "
                "use dry_run=False (CLI: --write) to attempt real writes",
                "real-write logic is currently a Step 2F-4c-1 skeleton "
                "and returns status='not_implemented_for_write'",
            ],
        }

    # dry_run=False but Step 2F-4c-1 deliberately stops here.
    # Real chain (run_predict + save_prediction + save_outcome) is 4c-2 scope.
    return {
        **base,
        "status": "not_implemented_for_write",
        "would_write_count": len(candidate_pairs),
        "notes": [
            "Step 2F-4c-1 is a dry-run-only skeleton; real write logic is "
            "deferred to Step 2F-4c-2",
            "no prediction/outcome records were written",
            "future writes will go through save_prediction("
            "analysis_date_override=D) + save_outcome("
            "captured_at_override=D+1) — never raw INSERT",
        ],
    }
