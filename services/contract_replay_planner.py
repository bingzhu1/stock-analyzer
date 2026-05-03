"""services/contract_replay_planner.py — read-only replay (D, D+1) planner.

Step 2F-4b: dry-run planner that enumerates which historical
``(as_of_date, prediction_for_date)`` pairs **would** be replayed by a
future writer (Step 2F-4c). It does NOT:

- write any DB row;
- call ``run_predict`` / ``save_prediction`` / ``save_outcome``;
- pull yfinance / hit any network;
- generate ``contract_payload_json``.

Trading-day source is the same per-symbol coded CSV that ``scanner.py``
already consumes (``coded_data/<SYMBOL>_coded.csv``). The planner reads
only the ``Date`` column with stdlib ``csv``; pandas is intentionally not
imported (Step 2 全程 read-only 工具一律 stdlib).

Public API:
    plan_contract_replay(
        symbol="AVGO",
        start_date=None,
        end_date=None,
        limit=30,
        coded_data_dir=None,
    ) -> dict

Status values:
    "ok"                — at least one (D, D+1) pair returned
    "missing_data"      — coded_data directory or per-symbol CSV missing
    "insufficient_data" — < 2 trading days remain after filtering
    "error"             — unexpected internal failure (bad date / unsupported symbol)
"""
from __future__ import annotations

import csv
from datetime import date as _date
from datetime import datetime
from pathlib import Path
from typing import Any


_DEFAULT_LIMIT = 30
_DEFAULT_CODED_SUBDIR = "coded_data"


def _resolve_limit(limit: Any) -> int:
    """Same defensive coercion as the other Step 2 read-only tools."""
    if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        return _DEFAULT_LIMIT
    return limit


def _resolve_symbol(symbol: Any) -> tuple[str, str | None]:
    """Coerce caller-provided symbol.

    Returns ``(symbol, error)``. ``error`` is None on success; otherwise
    the caller should short-circuit with status="error".

    Rules:
      None / non-str / empty / whitespace → "AVGO" (default fallback)
      "ALL" / "all" → unsupported (planner is per-symbol)
      otherwise → strip + upper
    """
    if symbol is None or not isinstance(symbol, str):
        return "AVGO", None
    stripped = symbol.strip().upper()
    if not stripped:
        return "AVGO", None
    if stripped == "ALL":
        return stripped, "symbol='ALL' is not supported; planner is per-symbol"
    return stripped, None


def _resolve_date(value: Any, *, field: str) -> tuple[str | None, str | None]:
    """Parse a YYYY-MM-DD string. Returns ``(parsed_iso, error)``.

    None → (None, None) — meaning "no filter on this side".
    """
    if value is None:
        return None, None
    if not isinstance(value, str) or not value.strip():
        return None, f"{field} must be YYYY-MM-DD or None (got: {value!r})"
    try:
        # fromisoformat handles "YYYY-MM-DD" exactly; reject longer forms
        # by extracting the date component first.
        parsed = _date.fromisoformat(value.strip()[:10])
    except ValueError:
        return None, f"{field}={value!r} is not a valid YYYY-MM-DD date"
    return parsed.isoformat(), None


def _resolve_coded_dir(coded_data_dir: str | Path | None) -> Path:
    if coded_data_dir is None:
        return Path.cwd() / _DEFAULT_CODED_SUBDIR
    return Path(coded_data_dir)


def _read_trading_days(csv_path: Path) -> list[str]:
    """Read the ``Date`` column from a coded CSV.

    Returns a sorted, deduped list of ``YYYY-MM-DD`` strings. Rows whose
    ``Date`` field can't be parsed are silently skipped (defensive).
    """
    seen: set[str] = set()
    with csv_path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None or "Date" not in reader.fieldnames:
            return []
        for row in reader:
            raw = row.get("Date")
            if not isinstance(raw, str) or not raw.strip():
                continue
            head = raw.strip()[:10]
            try:
                parsed = _date.fromisoformat(head)
            except ValueError:
                continue
            seen.add(parsed.isoformat())
    return sorted(seen)


def _build_candidate_pairs(
    trading_days: list[str], limit: int
) -> tuple[list[dict[str, str]], int]:
    """Build ``(as_of, prediction_for)`` pairs in time-ascending order,
    truncated to ``limit``.

    Returns ``(pairs, estimated_pair_count)`` where
    ``estimated_pair_count`` is the count BEFORE truncation.
    """
    estimated = max(0, len(trading_days) - 1)
    pairs: list[dict[str, str]] = []
    for i in range(len(trading_days) - 1):
        pairs.append({
            "as_of_date": trading_days[i],
            "prediction_for_date": trading_days[i + 1],
        })
    if limit > 0:
        pairs = pairs[:limit]
    return pairs, estimated


def _anti_lookahead_check(pairs: list[dict[str, str]]) -> dict[str, Any]:
    """Self-check that every pair satisfies as_of < prediction_for_date.

    This is a **defensive** check on planner output, not a substitute for
    the real anti-lookahead enforcement (which lives in the future writer).
    """
    if not pairs:
        return {
            "all_pairs_satisfy_d_lt_d_plus_1": True,
            "last_available_date": None,
        }
    all_ok = all(
        p["as_of_date"] < p["prediction_for_date"] for p in pairs
    )
    last = max(p["prediction_for_date"] for p in pairs)
    return {
        "all_pairs_satisfy_d_lt_d_plus_1": all_ok,
        "last_available_date": last,
    }


def plan_contract_replay(
    symbol: str = "AVGO",
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = _DEFAULT_LIMIT,
    coded_data_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Dry-run enumerate replay (D, D+1) pairs from a coded CSV.

    Read-only. Never raises; status surfaced via the returned dict.
    Never writes the DB. Never calls yfinance / network.
    """
    requested_limit = _resolve_limit(limit)
    resolved_symbol, symbol_error = _resolve_symbol(symbol)

    base: dict[str, Any] = {
        "symbol": resolved_symbol,
        "requested_limit": requested_limit,
        "start_date": start_date,
        "end_date": end_date,
    }

    if symbol_error is not None:
        return {**base, "status": "error", "error": symbol_error}

    start_iso, start_err = _resolve_date(start_date, field="start_date")
    if start_err is not None:
        return {**base, "status": "error", "error": start_err}
    end_iso, end_err = _resolve_date(end_date, field="end_date")
    if end_err is not None:
        return {**base, "status": "error", "error": end_err}

    if start_iso and end_iso and start_iso > end_iso:
        return {
            **base,
            "status": "error",
            "error": f"start_date={start_iso} is after end_date={end_iso}",
        }

    coded_dir = _resolve_coded_dir(coded_data_dir)
    csv_path = coded_dir / f"{resolved_symbol}_coded.csv"
    data_source_str = str(csv_path)

    if not coded_dir.exists():
        return {
            **base,
            "status": "missing_data",
            "data_source": data_source_str,
            "data_source_status": "missing_dir",
            "trading_days_total": 0,
            "estimated_pair_count": 0,
            "returned_pair_count": 0,
            "candidate_pairs": [],
            "skipped_days": [],
        }
    if not csv_path.exists():
        return {
            **base,
            "status": "missing_data",
            "data_source": data_source_str,
            "data_source_status": "missing_file",
            "trading_days_total": 0,
            "estimated_pair_count": 0,
            "returned_pair_count": 0,
            "candidate_pairs": [],
            "skipped_days": [],
        }

    all_days = _read_trading_days(csv_path)
    skipped_days: list[dict[str, str]] = []

    filtered = all_days
    if start_iso:
        before = len(filtered)
        filtered = [d for d in filtered if d >= start_iso]
        if before != len(filtered):
            skipped_days.append({
                "reason": "before_start_date",
                "count": str(before - len(filtered)),
            })
    if end_iso:
        before = len(filtered)
        filtered = [d for d in filtered if d <= end_iso]
        if before != len(filtered):
            skipped_days.append({
                "reason": "after_end_date",
                "count": str(before - len(filtered)),
            })

    base = {
        **base,
        "data_source": data_source_str,
        "data_source_status": "ok",
        "trading_days_total": len(filtered),
    }

    if len(filtered) < 2:
        return {
            **base,
            "status": "insufficient_data",
            "estimated_pair_count": 0,
            "returned_pair_count": 0,
            "candidate_pairs": [],
            "skipped_days": skipped_days,
        }

    pairs, estimated = _build_candidate_pairs(filtered, requested_limit)

    return {
        **base,
        "status": "ok",
        "estimated_pair_count": estimated,
        "returned_pair_count": len(pairs),
        "candidate_pairs": pairs,
        "skipped_days": skipped_days,
        "anti_lookahead_check": _anti_lookahead_check(pairs),
    }
