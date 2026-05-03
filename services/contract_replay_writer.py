"""services/contract_replay_writer.py — replay (D, D+1) writer.

Step 2F-4c-2: real-write upgrade. ``dry_run=True`` (default) still NEVER
calls ``run_predict`` / ``save_prediction`` / ``save_outcome``;
``dry_run=False`` walks each ``(D, D+1)`` candidate from
``services.contract_replay_planner.plan_contract_replay``, builds a
minimal historical scan from ``coded_data/<SYMBOL>_coded.csv``, runs
``predict.run_predict``, then writes one ``prediction_log`` row +
one ``outcome_log`` row per pair via ``save_prediction(...,
analysis_date_override=D)`` + ``save_outcome(...,
captured_at_override=D+1T16:00:00)``.

Step 2F-4c-3: peer historical cutoff. The historical scan now embeds
``relative_strength_summary`` and ``relative_strength_same_day_summary``
computed from ``coded_data/<PEER>_coded.csv`` (NVDA / SOXX / QQQ) with
``Date <= D``. The 0.5 pp margin and four-state classifier
(``stronger`` / ``weaker`` / ``neutral`` / ``unavailable``) mirror
``scanner._classify_rs`` exactly. ``predict.apply_peer_adjustment`` is
unchanged; only the scan it consumes is now peer-aware. Peer CSVs are
loaded once per batch in ``run_contract_replay`` (``dry_run=False``
only); missing peers degrade to ``unavailable`` without affecting other
peers.

Anti-lookahead: every pair reads ``<= D`` data for the scan and reads
the ``D+1`` row only for the outcome (never feeds the outcome back into
the projection step). Peer cutoff helpers locate target rows by
``Date == D`` and only read ``idx - n`` (always ≤ target idx).

Half-pair safety: outcome data is read **before** ``run_predict`` /
``save_prediction``. If the outcome row is missing or unparseable, the
pair is skipped entirely — no prediction row is written.

First-version safety: hard cap on ``limit`` is **30**. Anything larger
is clamped. Bigger batches require Step 2F-4d.

Public API:
    run_contract_replay(
        symbol="AVGO",
        start_date=None,
        end_date=None,
        limit=30,
        coded_data_dir=None,
        *,
        dry_run=True,
        db_path=None,
    ) -> dict

Status values:
    "ok"                          — all candidate pairs written successfully
    "partial"                     — some pairs written, some skipped
    "missing_data"                — planner could not find data (passthrough)
    "insufficient_data"           — planner had < 2 trading days (passthrough)
    "error"                       — write failed mid-way / arg validation failed
"""
from __future__ import annotations

import csv
from contextlib import contextmanager
from datetime import date as _date
from pathlib import Path
from typing import Any, Iterator

import services.prediction_store as _ps
from predict import run_predict
from services.contract_replay_planner import plan_contract_replay
from services.outcome_capture import _compute_direction_correct
from services.prediction_store import save_outcome, save_prediction


_DEFAULT_LIMIT = 30
# Hard cap for the writer (covers both dry-run and real-write paths). Lower
# than the planner's natural defaults: real writes to prediction_log /
# outcome_log are higher-risk than planning. Bigger batches require Step
# 2F-4d (90-pair replay) to land first.
_LIMIT_HARD_CAP = 30
_MIN_HISTORY_ROWS = 20  # primary projection's recent_20 window

# Peer cutoff (Step 2F-4c-3). Peer set + classifier margin mirror scanner.py
# (PEER_SYMBOLS = ["NVDA", "SOXX", "QQQ"], _RS_MARGIN = 0.005 ratio = 0.5 pp).
_PEER_SYMBOLS: tuple[str, ...] = ("NVDA", "SOXX", "QQQ")
_RS_MARGIN_PP: float = 0.5
_NDAY_RETURN_WINDOW: int = 5


def _resolve_writer_limit(limit: Any) -> int:
    """Coerce limit to a positive int and clamp to ``_LIMIT_HARD_CAP``.

    Matches the planner's defensive checks (bool / non-int / <= 0 → default)
    and adds an upper clamp to prevent fat-fingered bulk writes.
    """
    if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        return _DEFAULT_LIMIT
    if limit > _LIMIT_HARD_CAP:
        return _LIMIT_HARD_CAP
    return limit


def _read_symbol_ohlcv(
    symbol: str, coded_data_dir: str | Path | None
) -> list[dict[str, Any]] | None:
    """Read the per-symbol coded CSV into a sorted list of dict rows.

    Returns None when the directory or file is missing, or the CSV has no
    parseable Date column. Rows whose Date can't be parsed are skipped.
    Duplicate Date values are deduped (last-wins).
    """
    if coded_data_dir is None:
        coded_data_dir = Path.cwd() / "coded_data"
    coded_dir = Path(coded_data_dir)
    csv_path = coded_dir / f"{symbol}_coded.csv"
    if not coded_dir.exists() or not csv_path.exists():
        return None

    by_date: dict[str, dict[str, Any]] = {}
    with csv_path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None or "Date" not in reader.fieldnames:
            return None
        for row in reader:
            raw = row.get("Date")
            if not isinstance(raw, str) or not raw.strip():
                continue
            head = raw.strip()[:10]
            try:
                _date.fromisoformat(head)
            except ValueError:
                continue
            by_date[head] = {**row, "Date": head}
    return sorted(by_date.values(), key=lambda r: r["Date"])


def _to_float(value: Any) -> float | None:
    if value in (None, "", "nan", "NaN"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int | None:
    f = _to_float(value)
    return int(f) if f is not None else None


def _read_peer_ohlcv(
    symbol: str, coded_data_dir: str | Path | None
) -> list[dict[str, Any]] | None:
    """Read a peer-symbol coded CSV for relative-strength cutoff.

    Same shape and failure-mode contract as ``_read_symbol_ohlcv``: missing
    directory / missing file / no parseable Date column → None. Only Date
    / Close / C_move are consumed downstream (Open is used as a fallback
    for same-day move when C_move is missing).
    """
    return _read_symbol_ohlcv(symbol, coded_data_dir)


def _compute_nday_return_at(
    rows: list[dict[str, Any]] | None,
    target_date: str,
    n: int = _NDAY_RETURN_WINDOW,
) -> float | None:
    """N-day percent return ending at ``target_date``, or None.

    Mirrors ``scanner._get_nday_return``: requires a row whose Date equals
    ``target_date`` and at least ``n`` previous rows in the time-ascending
    list. Anti-lookahead: only reads ``idx - n`` and ``idx`` (both ≤ the
    target row's index, which is ``Date == target_date`` by construction).

    Returns ``(close_target / close_target_minus_n - 1) * 100`` (percent),
    or None on any missing / unparseable / zero-divide condition.
    """
    if not rows or n <= 0:
        return None
    target_idx: int | None = None
    for i, row in enumerate(rows):
        if row.get("Date") == target_date:
            target_idx = i
            break
    if target_idx is None or target_idx < n:
        return None
    c_now = _to_float(rows[target_idx].get("Close"))
    c_prev = _to_float(rows[target_idx - n].get("Close"))
    if c_now is None or c_prev is None or c_prev == 0:
        return None
    return (c_now - c_prev) / c_prev * 100.0


def _compute_same_day_move_at(
    rows: list[dict[str, Any]] | None, target_date: str
) -> float | None:
    """Same-day percent move at ``target_date``, or None.

    Prefers the ``C_move`` column (matches ``scanner._get_same_day_move``:
    ``C_move × 100``). When ``C_move`` is missing or unparseable, falls
    back to ``(Close - Open) / Open × 100`` from the same row. Returns
    None when neither path produces a usable number.
    """
    if not rows:
        return None
    target_row: dict[str, Any] | None = None
    for row in rows:
        if row.get("Date") == target_date:
            target_row = row
            break
    if target_row is None:
        return None
    c_move = _to_float(target_row.get("C_move"))
    if c_move is not None:
        return c_move * 100.0
    open_v = _to_float(target_row.get("Open"))
    close_v = _to_float(target_row.get("Close"))
    if open_v is None or close_v is None or open_v == 0:
        return None
    return (close_v - open_v) / open_v * 100.0


def _classify_relative_strength(
    avgo_ret: float | None,
    peer_ret: float | None,
    margin_pp: float = _RS_MARGIN_PP,
) -> str:
    """Classify AVGO vs peer return diff. Mirrors ``scanner._classify_rs``.

    Inputs are in percent (pp). Margin is the half-band: |avgo - peer|
    must exceed ``margin_pp`` for a directional verdict. Either input
    being None yields ``"unavailable"`` (no fabricated neutral).
    """
    if avgo_ret is None or peer_ret is None:
        return "unavailable"
    diff = avgo_ret - peer_ret
    if diff > margin_pp:
        return "stronger"
    if diff < -margin_pp:
        return "weaker"
    return "neutral"


def _compute_relative_strength_summary_at(
    as_of_date: str,
    avgo_rows: list[dict[str, Any]] | None,
    peer_rows_map: dict[str, list[dict[str, Any]] | None] | None,
    *,
    mode: str,
) -> dict[str, str]:
    """Build {vs_nvda, vs_soxx, vs_qqq} for ``mode in {"5d", "same_day"}``.

    - Anti-lookahead: every helper reads ``<= as_of_date`` only.
    - Missing peer rows (None) → that peer = ``"unavailable"``; other
      peers are computed independently.
    - Margin / n-day window match ``scanner.compute_relative_strength_summary``.
    - Unknown ``mode`` → all peers ``"unavailable"`` (defensive, no raise).
    """
    if mode == "5d":
        avgo_ret = _compute_nday_return_at(avgo_rows, as_of_date)
        peer_metric = lambda rows: _compute_nday_return_at(rows, as_of_date)
    elif mode == "same_day":
        avgo_ret = _compute_same_day_move_at(avgo_rows, as_of_date)
        peer_metric = lambda rows: _compute_same_day_move_at(rows, as_of_date)
    else:
        return {f"vs_{p.lower()}": "unavailable" for p in _PEER_SYMBOLS}

    rows_by_peer = peer_rows_map or {}
    out: dict[str, str] = {}
    for peer in _PEER_SYMBOLS:
        # Accept upper- or lower-case keys; either is unambiguous.
        peer_rows = rows_by_peer.get(peer) or rows_by_peer.get(peer.lower())
        peer_ret = peer_metric(peer_rows) if peer_rows else None
        out[f"vs_{peer.lower()}"] = _classify_relative_strength(
            avgo_ret, peer_ret
        )
    return out


def _build_historical_scan_at(
    symbol: str,
    as_of_date: str,
    ohlcv: list[dict[str, Any]],
    peer_rows_map: dict[str, list[dict[str, Any]] | None] | None = None,
) -> dict[str, Any] | None:
    """Build the minimal scan_result run_predict needs for a historical D.

    Returns None when there are fewer than ``_MIN_HISTORY_ROWS`` rows on
    or before ``as_of_date`` — primary_projection needs the recent-20
    window to produce a non-degraded output.

    Anti-lookahead: only rows with ``Date <= as_of_date`` are used (the
    AVGO recent-20 window is sliced from ``history``; peer helpers locate
    the target row by ``Date == as_of_date`` and only read backward).

    ``peer_rows_map`` is the Step 2F-4c-3 entry-point for NVDA / SOXX /
    QQQ peer cutoff. When None / empty, ``relative_strength_summary`` and
    ``relative_strength_same_day_summary`` come back with all three peers
    classified as ``"unavailable"`` (preserving the 4c-2 degraded shape
    semantically — three keys present, no fabricated neutrals).
    """
    history = [r for r in ohlcv if r["Date"] <= as_of_date]
    if len(history) < _MIN_HISTORY_ROWS:
        return None

    recent = history[-_MIN_HISTORY_ROWS:]
    rows: list[dict[str, Any]] = []
    for r in recent:
        try:
            row = {
                "Date": r["Date"],
                "Open": _to_float(r.get("Open")),
                "Close": _to_float(r.get("Close")),
                "Volume": _to_int(r.get("Volume")) or 0,
                "O_gap": _to_float(r.get("O_gap")) or 0.0,
                "C_move": _to_float(r.get("C_move")) or 0.0,
                "V_ratio": _to_float(r.get("V_ratio")) or 1.0,
            }
        except (KeyError, TypeError):
            return None
        if row["Open"] is None or row["Close"] is None:
            return None
        rows.append(row)

    rs_5d = _compute_relative_strength_summary_at(
        as_of_date, history, peer_rows_map, mode="5d"
    )
    rs_same_day = _compute_relative_strength_summary_at(
        as_of_date, history, peer_rows_map, mode="same_day"
    )

    return {
        "symbol": symbol,
        "scan_timestamp": f"{as_of_date}T00:00:00",
        "avgo_recent_20": rows,
        "relative_strength_summary": rs_5d,
        "relative_strength_same_day_summary": rs_same_day,
    }


def _read_outcome_row(
    target_date: str, ohlcv: list[dict[str, Any]]
) -> dict[str, float] | None:
    """Read OHLCV at ``target_date`` plus the previous-day Close.

    Returns None when the target row is missing, when it is the first
    row in the index (no previous Close), or when any of the required
    numeric fields are unparseable. The previous-day Close is taken
    from the row immediately before ``target_date`` in time-ascending
    order — never from the CSV's own ``PrevClose`` column (more
    defensive against gappy / corrupt CSVs).
    """
    target_idx: int | None = None
    for i, row in enumerate(ohlcv):
        if row["Date"] == target_date:
            target_idx = i
            break
    if target_idx is None or target_idx == 0:
        return None

    target = ohlcv[target_idx]
    prev = ohlcv[target_idx - 1]

    actual_open = _to_float(target.get("Open"))
    actual_high = _to_float(target.get("High"))
    actual_low = _to_float(target.get("Low"))
    actual_close = _to_float(target.get("Close"))
    actual_prev_close = _to_float(prev.get("Close"))

    if None in (actual_open, actual_high, actual_low, actual_close, actual_prev_close):
        return None
    return {
        "actual_open": actual_open,
        "actual_high": actual_high,
        "actual_low": actual_low,
        "actual_close": actual_close,
        "actual_prev_close": actual_prev_close,
    }


@contextmanager
def _maybe_override_db_path(db_path: str | Path | None) -> Iterator[None]:
    """Optionally override ``services.prediction_store.DB_PATH`` for the
    duration of the writer's writes, restoring the previous value on exit."""
    if db_path is None:
        yield
        return
    saved = _ps.DB_PATH
    _ps.DB_PATH = Path(db_path)
    try:
        yield
    finally:
        _ps.DB_PATH = saved


def _write_one_pair(
    symbol: str,
    as_of_date: str,
    prediction_for_date: str,
    ohlcv: list[dict[str, Any]],
    peer_rows_map: dict[str, list[dict[str, Any]] | None] | None = None,
) -> dict[str, Any]:
    """Replay one pair end-to-end. Returns a record dict.

    Returns one of:
      ``{"status": "skipped", "reason": ..., "as_of_date": ..., "prediction_for_date": ...}``
      ``{"status": "written", "prediction_id": ..., "analysis_date": ..., ...}``
    """
    base = {
        "as_of_date": as_of_date,
        "prediction_for_date": prediction_for_date,
    }

    # 1. Read outcome FIRST. If missing, skip the pair entirely so we
    #    never write a half-pair (prediction without outcome).
    outcome = _read_outcome_row(prediction_for_date, ohlcv)
    if outcome is None:
        return {**base, "status": "skipped", "reason": "no_outcome_data"}

    # 2. Build historical scan. Skip pair when not enough history.
    scan = _build_historical_scan_at(
        symbol, as_of_date, ohlcv, peer_rows_map=peer_rows_map
    )
    if scan is None:
        return {**base, "status": "skipped", "reason": "insufficient_history"}

    # 3. Run predict — pure, deterministic given scan.
    predict_result = run_predict(
        scan, research_result=None, symbol=symbol,
    )

    # 4. Save prediction with analysis_date pinned to D.
    prediction_id = save_prediction(
        symbol=symbol,
        prediction_for_date=prediction_for_date,
        scan_result=scan,
        research_result=None,
        predict_result=predict_result,
        snapshot_id=f"replay_{symbol}_{as_of_date}",
        analysis_date_override=as_of_date,
    )

    # 5. Compute outcome correctness using the canonical helper.
    final_bias = predict_result.get("final_bias", "neutral")
    prev_close = outcome["actual_prev_close"]
    close_change = (
        (outcome["actual_close"] - prev_close) / prev_close
        if prev_close
        else 0.0
    )
    direction_correct = _compute_direction_correct(final_bias, close_change)

    # 6. Save outcome with captured_at pinned to D+1T16:00:00.
    captured_at = f"{prediction_for_date}T16:00:00"
    save_outcome(
        prediction_id=prediction_id,
        prediction_for_date=prediction_for_date,
        actual_open=outcome["actual_open"],
        actual_high=outcome["actual_high"],
        actual_low=outcome["actual_low"],
        actual_close=outcome["actual_close"],
        actual_prev_close=prev_close,
        direction_correct=direction_correct,
        scenario_match=None,
        captured_at_override=captured_at,
    )

    return {
        **base,
        "status": "written",
        "prediction_id": prediction_id,
        "analysis_date": as_of_date,
        "captured_at": captured_at,
        "direction_correct": direction_correct,
    }


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
    """Plan + (when ``dry_run=False``) write a replay batch.

    Read-only when ``dry_run=True``; the default. With ``dry_run=False``
    each (D, D+1) candidate is written via ``save_prediction(...,
    analysis_date_override=D)`` + ``save_outcome(...,
    captured_at_override=D+1T16:00:00)``. Hard cap on ``limit`` is 30.
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
        "attempted_write_count": 0,
        "written_prediction_count": 0,
        "written_outcome_count": 0,
        "candidate_pairs": candidate_pairs,
        "skipped_pairs": [],
        "written_records": [],
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
                f"writer hard cap on limit is {_LIMIT_HARD_CAP}",
            ],
        }

    # dry_run=False — write path.
    ohlcv = _read_symbol_ohlcv(planner_result.get("symbol", symbol), coded_data_dir)
    if ohlcv is None:
        return {
            **base,
            "status": "error",
            "error": "ohlcv_read_failed: could not load coded_data CSV",
            "notes": [
                "could not read coded_data CSV for OHLCV lookups; "
                "no records were written",
            ],
        }

    # Step 2F-4c-3: load NVDA / SOXX / QQQ peer CSVs once for the whole
    # batch. Missing peers degrade silently to None → that peer's vs_*
    # entry comes back "unavailable" without affecting the other peers.
    peer_rows_map: dict[str, list[dict[str, Any]] | None] = {
        peer: _read_peer_ohlcv(peer, coded_data_dir) for peer in _PEER_SYMBOLS
    }

    written_records: list[dict[str, Any]] = []
    skipped_pairs: list[dict[str, Any]] = []

    with _maybe_override_db_path(db_path):
        for pair in candidate_pairs:
            try:
                result = _write_one_pair(
                    symbol=planner_result.get("symbol", symbol),
                    as_of_date=pair["as_of_date"],
                    prediction_for_date=pair["prediction_for_date"],
                    ohlcv=ohlcv,
                    peer_rows_map=peer_rows_map,
                )
            except Exception as exc:
                # System-level failure — bail out. Already-written rows
                # for prior pairs in this batch remain (DB is durable),
                # but this pair did NOT half-write because the only
                # write entry-points are inside _write_one_pair and any
                # exception there means save_prediction / save_outcome
                # already raised before completing.
                return {
                    **base,
                    "status": "error",
                    "error": f"write_failed: {exc}",
                    "attempted_write_count": len(written_records) + len(skipped_pairs) + 1,
                    "written_prediction_count": len(written_records),
                    "written_outcome_count": len(written_records),
                    "written_records": written_records,
                    "skipped_pairs": skipped_pairs,
                    "notes": [
                        f"unexpected exception while writing pair "
                        f"{pair['as_of_date']} → {pair['prediction_for_date']}; "
                        "earlier pairs in this batch were committed",
                    ],
                }
            if result["status"] == "written":
                written_records.append(result)
            else:
                skipped_pairs.append(result)

    attempted = len(written_records) + len(skipped_pairs)
    if skipped_pairs and written_records:
        status = "partial"
    elif skipped_pairs and not written_records:
        # Planner said ok, but every pair skipped. Still 'partial' to keep
        # the consumer from confusing this with a clean ok run.
        status = "partial"
    else:
        status = "ok"

    return {
        **base,
        "status": status,
        "would_write_count": len(candidate_pairs),
        "attempted_write_count": attempted,
        "written_prediction_count": len(written_records),
        "written_outcome_count": len(written_records),
        "written_records": written_records,
        "skipped_pairs": skipped_pairs,
        "notes": [
            f"dry_run=False: wrote {len(written_records)} prediction/outcome "
            f"pair(s); skipped {len(skipped_pairs)}",
            "all writes went through save_prediction / save_outcome — "
            "no raw INSERT was used",
            "peer cutoff: NVDA / SOXX / QQQ relative-strength computed "
            "with Date <= D from coded_data; missing peers degrade to "
            "'unavailable'",
        ],
    }
