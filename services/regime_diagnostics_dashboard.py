"""services/regime_diagnostics_dashboard.py — read-only regime diagnostics.

Aggregates contract-replay rows (``snapshot_id LIKE "replay_<SYMBOL>_%"``)
joined with their latest ``outcome_log`` flag, derives the AVGO 20-day
position metric (``avgo_pos_20d``) and the AVGO − SOXX 20-day return
diff from local ``coded_data/<SYMBOL>_coded.csv`` files, and emits per-
regime diagnostic slices: pos20 quartile bias, R4 signature, confidence
× regime, peer adjustment, soft-signal, monthly accuracy, and a fixed
high-confidence-failure slice list.

Step 3D-1: this is a **diagnostic** tool — NOT a calibration engine, NOT
a confidence-score writer, and NOT a 04/05/07 contract upgrade. The four
0.0 score fields in ``confidence_system`` (``historical_score`` /
``structure_score`` / ``peer_score`` / ``exclusion_penalty``) and
``event_score = None`` are NOT changed by this module. Step 3B's 4×4
lookup table is frozen; this tool only surfaces the regime features that
the lookup attempted to use, plus a few additional decompositions
requested by the Step 2G exclusion re-review.

Public API:
    summarize_regime_diagnostics_dashboard(
        db_path=None, symbol="AVGO", limit=450,
        coded_data_dir=None,
    ) -> dict

Status values:
    "ok"           — at least one valid contract payload scanned
    "no_records"   — no rows under ``snapshot_id LIKE "replay_<SYMBOL>_%"``
    "error"        — internal failure (e.g. DB unreadable)

Read-only guarantees:
- never writes the DB; only ``SELECT`` (no ``init_db`` / ``INSERT`` / ``UPDATE``)
- never writes any file
- never imports ``yfinance`` / ``requests`` / any trading API
- never raises (status surfaced via the dict)
- coded_data CSVs are opened read-only; missing CSVs degrade gracefully
"""
from __future__ import annotations

import csv
import json
import sqlite3
import statistics
from datetime import date as _date
from pathlib import Path
from typing import Any

import services.prediction_store as _ps


_DEFAULT_LIMIT = 450
_PEER_FOR_REGIME = "SOXX"  # avgo − SOXX 20-day return diff
_POS20_WINDOW = 20

# R4 signature thresholds (Step 3B regime-aware design, frozen).
_R4_AVGO_MINUS_SOXX_THRESHOLD = 5.0
_R4_POS20_THRESHOLD = 0.62

# Mirror of contract_calibration_inputs._MIN_RECOMMENDED_PAIRS — same
# heuristic for "calibration_ready" gating; this tool does not implement
# calibration, only flags whether the dataset is large enough.
_MIN_RECOMMENDED_PAIRS = 90

_VALID_CONFIDENCE_LEVELS = ("high", "medium", "low")
_VALID_PEER_ADJUSTMENTS = ("upgrade", "hold", "downgrade")
_VALID_SOFT_SIGNALS = ("none", "high_path_risk", "peer_weaken")


# ── input coercion helpers ────────────────────────────────────────────────

def _resolve_db_path(db_path: str | Path | None) -> Path:
    if db_path is None:
        return Path(_ps.DB_PATH)
    return Path(db_path)


def _resolve_limit(limit: Any) -> int:
    if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        return _DEFAULT_LIMIT
    return limit


def _resolve_symbol(symbol: Any) -> str:
    if not isinstance(symbol, str):
        return "AVGO"
    stripped = symbol.strip().upper()
    return stripped or "AVGO"


def _resolve_coded_data_dir(coded_data_dir: str | Path | None) -> Path:
    if coded_data_dir is None:
        return Path.cwd() / "coded_data"
    return Path(coded_data_dir)


# ── coded CSV reading ─────────────────────────────────────────────────────

def _read_coded_csv(symbol: str, coded_data_dir: Path) -> list[dict[str, Any]]:
    """Read ``coded_data/<SYMBOL>_coded.csv`` into a date-sorted list.

    Returns an empty list when the directory or file is missing, or the
    CSV has no parseable Date column. Rows whose Date can't be parsed
    are skipped silently; duplicate Date values are deduped (last-wins).
    Mirrors ``contract_replay_writer._read_symbol_ohlcv`` semantics but
    is inlined to keep this service standalone (no compute imports).
    """
    csv_path = coded_data_dir / f"{symbol}_coded.csv"
    if not coded_data_dir.exists() or not csv_path.exists():
        return []

    by_date: dict[str, dict[str, Any]] = {}
    try:
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
                    _date.fromisoformat(head)
                except ValueError:
                    continue
                by_date[head] = {**row, "Date": head}
    except OSError:
        return []
    return sorted(by_date.values(), key=lambda r: r["Date"])


def _to_float(value: Any) -> float | None:
    if value in (None, "", "nan", "NaN"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _row_index_for_date(
    rows: list[dict[str, Any]], target_date: str
) -> int | None:
    """Linear search for the row whose Date equals ``target_date``.

    ``rows`` is small enough (≤ ~3000 daily bars) that a linear scan is
    fine and avoids a dict-build cost when the caller only needs one
    lookup per record.
    """
    for i, row in enumerate(rows):
        if row.get("Date") == target_date:
            return i
    return None


def _compute_pos20(
    rows: list[dict[str, Any]], target_date: str
) -> tuple[float | None, str | None]:
    """Position of Close in the rolling 20-day Low/High band at D.

    ``pos20 = (Close_D − rolling_low_20) / (rolling_high_20 − rolling_low_20)``

    Returns ``(value, skip_reason)``:
      - ``(float, None)`` on success
      - ``(None, "missing_date")`` when ``target_date`` not in CSV
      - ``(None, "insufficient_history")`` when fewer than 20 prior bars
      - ``(None, "missing_ohlc")`` when Close / High / Low can't be parsed
      - ``(None, "flat_band")`` when rolling High == rolling Low (zero-div)
    """
    idx = _row_index_for_date(rows, target_date)
    if idx is None:
        return None, "missing_date"
    if idx < _POS20_WINDOW - 1:
        return None, "insufficient_history"

    window = rows[idx - (_POS20_WINDOW - 1) : idx + 1]
    highs: list[float] = []
    lows: list[float] = []
    for r in window:
        h = _to_float(r.get("High"))
        l = _to_float(r.get("Low"))
        if h is None or l is None:
            return None, "missing_ohlc"
        highs.append(h)
        lows.append(l)
    close_d = _to_float(rows[idx].get("Close"))
    if close_d is None:
        return None, "missing_ohlc"

    high_max = max(highs)
    low_min = min(lows)
    band = high_max - low_min
    if band <= 0:
        return None, "flat_band"
    return (close_d - low_min) / band, None


def _compute_nday_return(
    rows: list[dict[str, Any]], target_date: str, n: int = _POS20_WINDOW
) -> float | None:
    """``(Close_D / Close_{D-n} − 1) × 100`` (percent), or None.

    Anti-lookahead: only reads rows at index ≤ target_idx.
    """
    idx = _row_index_for_date(rows, target_date)
    if idx is None or idx < n:
        return None
    c_now = _to_float(rows[idx].get("Close"))
    c_prev = _to_float(rows[idx - n].get("Close"))
    if c_now is None or c_prev is None or c_prev == 0:
        return None
    return (c_now - c_prev) / c_prev * 100.0


# ── DB fetch ─────────────────────────────────────────────────────────────

def _fetch_replay_rows(
    db_path: Path, symbol_filter: str, limit: int
) -> list[dict[str, Any]]:
    """SELECT-only fetch of replay predictions joined with latest outcome.

    Uses ``snapshot_id LIKE "replay_<SYMBOL>_%"`` (escaped) and orders by
    ``analysis_date DESC, rowid DESC`` so the newest replay row sorts
    first. The outcome is selected via correlated subquery (mirrors
    ``contract_outcome_correlation``) so each prediction appears once.
    """
    pattern = f"replay_{symbol_filter}_%"
    sql = """
        SELECT p.id                    AS id,
               p.symbol                AS symbol,
               p.analysis_date         AS analysis_date,
               p.prediction_for_date   AS prediction_for_date,
               p.snapshot_id           AS snapshot_id,
               p.contract_payload_json AS contract_payload_json,
               (SELECT o.direction_correct
                  FROM outcome_log o
                 WHERE o.prediction_id = p.id
                 ORDER BY o.captured_at DESC, o.rowid DESC
                 LIMIT 1) AS direction_correct,
               (SELECT o.actual_close
                  FROM outcome_log o
                 WHERE o.prediction_id = p.id
                 ORDER BY o.captured_at DESC, o.rowid DESC
                 LIMIT 1) AS actual_close,
               (SELECT o.actual_prev_close
                  FROM outcome_log o
                 WHERE o.prediction_id = p.id
                 ORDER BY o.captured_at DESC, o.rowid DESC
                 LIMIT 1) AS actual_prev_close
          FROM prediction_log p
         WHERE p.snapshot_id LIKE ?
         ORDER BY p.analysis_date DESC, p.rowid DESC
         LIMIT ?
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(sql, (pattern, limit)).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


# ── payload extraction ───────────────────────────────────────────────────

def _parse_payload(raw: Any) -> dict | None:
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    return payload if isinstance(payload, dict) else None


def _direction_label(direction_correct: Any) -> str:
    if direction_correct is None:
        return "pending"
    return "correct" if direction_correct else "wrong"


def _is_actual_up(actual_close: Any, actual_prev_close: Any) -> bool | None:
    c = _to_float(actual_close)
    p = _to_float(actual_prev_close)
    if c is None or p is None:
        return None
    return c > p


def _build_record(row: dict[str, Any], payload: dict) -> dict[str, Any]:
    """Project one valid (row, payload) pair into a flat record."""
    cs = payload.get("confidence_system") or {}
    cs_extras = cs.get("extras") if isinstance(cs.get("extras"), dict) else {}
    es = payload.get("exclusion_system") or {}
    es_extras = es.get("extras") if isinstance(es.get("extras"), dict) else {}
    pa = payload.get("peer_confirmation_adjustment") or {}
    fp = payload.get("final_projection") or {}

    # Soft-signal preference: confidence_system.extras.soft_signal first
    # (Step 2C-3b self-published), fall back to exclusion_system.extras.
    soft_signal = cs_extras.get("soft_signal")
    if soft_signal not in _VALID_SOFT_SIGNALS:
        soft_signal = es_extras.get("soft_signal")
    if soft_signal not in _VALID_SOFT_SIGNALS:
        soft_signal = None

    confidence_level = cs.get("confidence_level")
    if confidence_level not in _VALID_CONFIDENCE_LEVELS:
        confidence_level = None

    peer_adjustment = pa.get("peer_adjustment")
    if peer_adjustment not in _VALID_PEER_ADJUSTMENTS:
        peer_adjustment = None

    primary_score_raw = cs_extras.get("primary_score_raw")
    if isinstance(primary_score_raw, bool) or not isinstance(
        primary_score_raw, (int, float)
    ):
        primary_score_raw = None

    peer_confirm_count = cs_extras.get("peer_confirm_count")
    if isinstance(peer_confirm_count, bool) or not isinstance(
        peer_confirm_count, int
    ):
        peer_confirm_count = None

    direction_correct = row.get("direction_correct")
    actual_up = _is_actual_up(
        row.get("actual_close"), row.get("actual_prev_close")
    )

    return {
        "prediction_id": row.get("id"),
        "analysis_date": row.get("analysis_date"),
        "prediction_for_date": row.get("prediction_for_date"),
        "final_direction": fp.get("final_direction"),
        "confidence_level": confidence_level,
        "primary_score_raw": primary_score_raw,
        "peer_adjustment": peer_adjustment,
        "peer_confirm_count": peer_confirm_count,
        "soft_signal": soft_signal,
        "direction_correct_label": _direction_label(direction_correct),
        "direction_correct_raw": direction_correct,
        "actual_up": actual_up,
        # Filled in later from coded CSV (None on lookup failure).
        "pos20": None,
        "pos20_skip_reason": None,
        "avgo_minus_soxx_20d": None,
    }


# ── per-slice accuracy helpers ────────────────────────────────────────────

def _empty_bucket() -> dict[str, Any]:
    return {
        "samples": 0,
        "paired": 0,
        "correct": 0,
        "wrong": 0,
        "pending": 0,
        "accuracy": None,
    }


def _accumulate_bucket(bucket: dict[str, Any], rec: dict[str, Any]) -> None:
    bucket["samples"] += 1
    label = rec["direction_correct_label"]
    if label == "correct":
        bucket["correct"] += 1
        bucket["paired"] += 1
    elif label == "wrong":
        bucket["wrong"] += 1
        bucket["paired"] += 1
    else:
        bucket["pending"] += 1


def _finalize_accuracy(bucket: dict[str, Any]) -> None:
    paired = bucket["correct"] + bucket["wrong"]
    bucket["accuracy"] = (bucket["correct"] / paired) if paired > 0 else None


def _bias_rates(records: list[dict[str, Any]]) -> dict[str, Any]:
    """predicted_bullish_rate vs actual_up_rate over paired records.

    "Bullish" = ``final_direction == "偏多"``. "Up" = actual_close >
    actual_prev_close. Both rates are computed over the paired subset
    (``correct`` + ``wrong``); ``pending`` rows are excluded so the two
    rates share the same denominator. Returns a triple-None shape when
    no paired rows exist.
    """
    paired = [
        r for r in records if r["direction_correct_label"] in ("correct", "wrong")
    ]
    if not paired:
        return {
            "paired": 0,
            "predicted_bullish_rate": None,
            "actual_up_rate": None,
            "bias_gap": None,
        }
    bullish = sum(1 for r in paired if r["final_direction"] == "偏多")
    actual_up = sum(1 for r in paired if r["actual_up"] is True)
    pb = bullish / len(paired)
    au = actual_up / len(paired)
    return {
        "paired": len(paired),
        "predicted_bullish_rate": pb,
        "actual_up_rate": au,
        "bias_gap": pb - au,
    }


# ── pos20 quartile bias ──────────────────────────────────────────────────

def _compute_pos20_quartile_bias(
    records: list[dict[str, Any]], warnings: list[str]
) -> list[dict[str, Any]]:
    """Bucket records by pos20 quartile and report bias rates per bucket.

    Quartile cut points come from ``statistics.quantiles(values, n=4)``
    over the records that have a real pos20 value. When fewer than 4
    valid pos20 values exist, returns ``[]`` and pushes a warning.
    """
    pos_records = [r for r in records if r["pos20"] is not None]
    if len(pos_records) < 4:
        warnings.append(
            f"insufficient pos20 samples for quartile bias: "
            f"have {len(pos_records)}, need ≥ 4"
        )
        return []

    values = sorted(r["pos20"] for r in pos_records)
    cuts = statistics.quantiles(values, n=4)
    q1, q2, q3 = cuts[0], cuts[1], cuts[2]

    # Bucket assignment: lower-inclusive on Q2/Q3/Q4 boundaries to avoid
    # duplicate counting; Q1 is everything ≤ q1.
    def _bucket_of(v: float) -> str:
        if v <= q1:
            return "Q1"
        if v <= q2:
            return "Q2"
        if v <= q3:
            return "Q3"
        return "Q4"

    boundaries = {
        "Q1": f"<= {q1:.4f}",
        "Q2": f"({q1:.4f}, {q2:.4f}]",
        "Q3": f"({q2:.4f}, {q3:.4f}]",
        "Q4": f"> {q3:.4f}",
    }

    buckets: dict[str, list[dict[str, Any]]] = {b: [] for b in boundaries}
    for r in pos_records:
        buckets[_bucket_of(r["pos20"])].append(r)

    out: list[dict[str, Any]] = []
    for label in ("Q1", "Q2", "Q3", "Q4"):
        members = buckets[label]
        bucket = _empty_bucket()
        for r in members:
            _accumulate_bucket(bucket, r)
        _finalize_accuracy(bucket)
        bias = _bias_rates(members)
        out.append({
            "bucket": label,
            "boundary": boundaries[label],
            **bucket,
            "predicted_bullish_rate": bias["predicted_bullish_rate"],
            "actual_up_rate": bias["actual_up_rate"],
            "bias_gap": bias["bias_gap"],
        })
    return out


# ── R4 signature ─────────────────────────────────────────────────────────

def _is_r4_record(rec: dict[str, Any]) -> bool:
    """R4 = strong-momentum bullish-call slice.

    Conditions (all required):
      - ``avgo_minus_soxx_20d > 5``
      - ``pos20 > 0.62``
      - ``final_direction == "偏多"``
      - ``confidence_level == "high"`` OR ``primary_score_raw > 2``
    """
    diff = rec["avgo_minus_soxx_20d"]
    pos = rec["pos20"]
    if diff is None or pos is None:
        return False
    if diff <= _R4_AVGO_MINUS_SOXX_THRESHOLD:
        return False
    if pos <= _R4_POS20_THRESHOLD:
        return False
    if rec["final_direction"] != "偏多":
        return False
    if rec["confidence_level"] == "high":
        return True
    psr = rec["primary_score_raw"]
    return isinstance(psr, (int, float)) and not isinstance(psr, bool) and psr > 2


def _compute_r4_signature(records: list[dict[str, Any]]) -> dict[str, Any]:
    matched = [r for r in records if _is_r4_record(r)]
    bucket = _empty_bucket()
    for r in matched:
        _accumulate_bucket(bucket, r)
    _finalize_accuracy(bucket)
    bias = _bias_rates(matched)
    high_conf_count = sum(1 for r in matched if r["confidence_level"] == "high")
    # "downgrade_candidate" = matched + high confidence + paired + bias_gap > 0.
    # We pick at-record level: matched & confidence_level=high & wrong.
    # Both definitions are rough; we use the per-record one because it's
    # more actionable for Step 2G review.
    downgrade_candidate_count = sum(
        1 for r in matched
        if r["confidence_level"] == "high"
        and r["direction_correct_label"] == "wrong"
    )
    return {
        **bucket,
        "predicted_bullish_rate": bias["predicted_bullish_rate"],
        "actual_up_rate": bias["actual_up_rate"],
        "bias_gap": bias["bias_gap"],
        "high_confidence_count": high_conf_count,
        "downgrade_candidate_count": downgrade_candidate_count,
        "thresholds": {
            "avgo_minus_soxx_20d": _R4_AVGO_MINUS_SOXX_THRESHOLD,
            "pos20": _R4_POS20_THRESHOLD,
        },
    }


# ── confidence × regime ──────────────────────────────────────────────────

def _compute_confidence_by_regime(
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    """confidence_level overall + confidence × pos20 quartile slices."""
    overall: dict[str, dict[str, Any]] = {}
    for level in _VALID_CONFIDENCE_LEVELS:
        bucket = _empty_bucket()
        for r in records:
            if r["confidence_level"] == level:
                _accumulate_bucket(bucket, r)
        _finalize_accuracy(bucket)
        overall[level] = bucket

    # confidence × pos20 quartile cross. We re-derive quartiles here
    # rather than threading them through; if there aren't enough pos20
    # samples we emit empty cross sections + the explicit slices.
    pos_records = [r for r in records if r["pos20"] is not None]
    cross: dict[str, dict[str, dict[str, Any]]] = {}
    if len(pos_records) >= 4:
        cuts = statistics.quantiles(
            sorted(r["pos20"] for r in pos_records), n=4
        )
        q1, q2, q3 = cuts[0], cuts[1], cuts[2]

        def _q(v: float) -> str:
            if v <= q1:
                return "Q1"
            if v <= q2:
                return "Q2"
            if v <= q3:
                return "Q3"
            return "Q4"

        for level in _VALID_CONFIDENCE_LEVELS:
            cross[level] = {}
            for label in ("Q1", "Q2", "Q3", "Q4"):
                bucket = _empty_bucket()
                for r in pos_records:
                    if r["confidence_level"] != level:
                        continue
                    if _q(r["pos20"]) != label:
                        continue
                    _accumulate_bucket(bucket, r)
                _finalize_accuracy(bucket)
                cross[level][label] = bucket

    # Two explicit slices (independent of quartile binning), for Step 2G:
    # pos20 > 0.62 (R4 pos cutoff) and pos20 > 0.75 (a stricter Q4 proxy).
    def _slice(predicate) -> dict[str, Any]:
        bucket = _empty_bucket()
        members = [r for r in records if predicate(r)]
        for r in members:
            _accumulate_bucket(bucket, r)
        _finalize_accuracy(bucket)
        return bucket

    explicit_slices = {
        "pos20_gt_0_62_high": _slice(
            lambda r: r["pos20"] is not None
            and r["pos20"] > _R4_POS20_THRESHOLD
            and r["confidence_level"] == "high"
        ),
        "pos20_gt_0_75_high": _slice(
            lambda r: r["pos20"] is not None
            and r["pos20"] > 0.75
            and r["confidence_level"] == "high"
        ),
    }

    return {
        "overall": overall,
        "by_pos20_quartile": cross,
        "explicit_slices": explicit_slices,
    }


# ── peer adjustment summary ──────────────────────────────────────────────

def _compute_peer_adjustment_summary(
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    by_label: dict[str, dict[str, Any]] = {}
    for label in _VALID_PEER_ADJUSTMENTS:
        bucket = _empty_bucket()
        for r in records:
            if r["peer_adjustment"] == label:
                _accumulate_bucket(bucket, r)
        _finalize_accuracy(bucket)
        by_label[label] = bucket

    by_confirm: dict[str, dict[str, Any]] = {}
    for count in (0, 1, 2, 3):
        bucket = _empty_bucket()
        for r in records:
            if r["peer_confirm_count"] == count:
                _accumulate_bucket(bucket, r)
        _finalize_accuracy(bucket)
        by_confirm[str(count)] = bucket

    return {
        "by_peer_adjustment": by_label,
        "by_peer_confirm_count": by_confirm,
    }


# ── soft signal summary ──────────────────────────────────────────────────

def _compute_soft_signal_summary(
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    out: dict[str, dict[str, Any]] = {}
    for label in _VALID_SOFT_SIGNALS:
        bucket = _empty_bucket()
        for r in records:
            if r["soft_signal"] == label:
                _accumulate_bucket(bucket, r)
        _finalize_accuracy(bucket)
        out[label] = bucket
    return out


# ── monthly accuracy ─────────────────────────────────────────────────────

def _month_key(date_str: Any) -> str | None:
    if not isinstance(date_str, str) or len(date_str) < 7:
        return None
    head = date_str[:7]
    try:
        _date.fromisoformat(head + "-01")
    except ValueError:
        return None
    return head


def _compute_monthly_accuracy(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    months: dict[str, list[dict[str, Any]]] = {}
    for r in records:
        key = _month_key(r["prediction_for_date"])
        if key is None:
            continue
        months.setdefault(key, []).append(r)

    out: list[dict[str, Any]] = []
    for key in sorted(months):
        members = months[key]
        bucket = _empty_bucket()
        for r in members:
            _accumulate_bucket(bucket, r)
        _finalize_accuracy(bucket)
        bias = _bias_rates(members)
        out.append({
            "month": key,
            **bucket,
            "predicted_bullish_rate": bias["predicted_bullish_rate"],
            "actual_up_rate": bias["actual_up_rate"],
            "bias_gap": bias["bias_gap"],
        })
    return out


# ── high confidence failure slices ───────────────────────────────────────

def _slice_with_bias(
    records: list[dict[str, Any]], predicate, name: str,
) -> dict[str, Any]:
    members = [r for r in records if predicate(r)]
    bucket = _empty_bucket()
    for r in members:
        _accumulate_bucket(bucket, r)
    _finalize_accuracy(bucket)
    bias = _bias_rates(members)
    return {
        "slice": name,
        **bucket,
        "predicted_bullish_rate": bias["predicted_bullish_rate"],
        "actual_up_rate": bias["actual_up_rate"],
        "bias_gap": bias["bias_gap"],
    }


def _compute_high_confidence_failure_slices(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        _slice_with_bias(
            records,
            lambda r: r["confidence_level"] == "high",
            "confidence_high",
        ),
        _slice_with_bias(
            records,
            lambda r: r["pos20"] is not None
            and r["confidence_level"] == "high"
            and 0.5 < r["pos20"] <= 0.75,
            "pos20_q3_and_high",
        ),
        _slice_with_bias(
            records,
            lambda r: r["pos20"] is not None
            and r["confidence_level"] == "high"
            and r["pos20"] > 0.75,
            "pos20_q4_and_high",
        ),
        _slice_with_bias(
            records,
            _is_r4_record,
            "r4_signature",
        ),
        _slice_with_bias(
            records,
            lambda r: r["final_direction"] == "偏多"
            and r["confidence_level"] == "high"
            and r["pos20"] is not None
            and r["pos20"] > _R4_POS20_THRESHOLD,
            "bullish_high_pos20_gt_0_62",
        ),
    ]


# ── time range ───────────────────────────────────────────────────────────

def _compute_time_range(records: list[dict[str, Any]]) -> dict[str, Any]:
    dates = [
        r["analysis_date"] for r in records
        if isinstance(r["analysis_date"], str) and r["analysis_date"]
    ]
    if not dates:
        return {"analysis_date_min": None, "analysis_date_max": None}
    return {
        "analysis_date_min": min(dates),
        "analysis_date_max": max(dates),
    }


# ── public entry point ──────────────────────────────────────────────────

def summarize_regime_diagnostics_dashboard(
    db_path: str | Path | None = None,
    symbol: str = "AVGO",
    limit: int = _DEFAULT_LIMIT,
    *,
    coded_data_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Aggregate regime diagnostics over the most-recent N replay rows.

    Read-only. Never mutates the DB. Always returns a dict; never raises.

    ``coded_data_dir`` is keyword-only and defaults to ``cwd/coded_data``.
    Tests inject a tmp_path here; the CLI does not expose it (it expects
    the writer's default layout).
    """
    db = _resolve_db_path(db_path)
    requested_limit = _resolve_limit(limit)
    sym = _resolve_symbol(symbol)
    coded_dir = _resolve_coded_data_dir(coded_data_dir)
    warnings: list[str] = []

    try:
        rows = _fetch_replay_rows(db, sym, requested_limit)
    except Exception as exc:
        return {
            "status": "error",
            "error": f"db_read_failed: {exc}",
            "symbol": sym,
        }

    if not rows:
        return {
            "status": "no_records",
            "symbol": sym,
            "records_scanned": 0,
            "valid_payloads": 0,
            "paired_outcomes": 0,
            "pending_outcomes": 0,
            "calibration_ready": False,
            "time_range": {
                "analysis_date_min": None,
                "analysis_date_max": None,
            },
            "pos20_quartile_bias": [],
            "r4_signature": {},
            "confidence_by_regime": {},
            "peer_adjustment_summary": {},
            "soft_signal_summary": {},
            "monthly_accuracy": [],
            "high_confidence_failure_slices": [],
            "warnings": warnings,
        }

    avgo_csv = _read_coded_csv(sym, coded_dir)
    soxx_csv = _read_coded_csv(_PEER_FOR_REGIME, coded_dir)
    if not avgo_csv:
        warnings.append(
            f"coded_data CSV missing or unreadable for {sym}; "
            "pos20 / R4 will be empty"
        )
    if not soxx_csv:
        warnings.append(
            f"coded_data CSV missing or unreadable for {_PEER_FOR_REGIME}; "
            "avgo_minus_soxx_20d will be None"
        )

    records: list[dict[str, Any]] = []
    skipped_payloads = 0
    pos20_skip_counts: dict[str, int] = {}

    for row in rows:
        payload = _parse_payload(row.get("contract_payload_json"))
        if payload is None:
            skipped_payloads += 1
            continue
        rec = _build_record(row, payload)

        analysis_date = rec["analysis_date"]
        if isinstance(analysis_date, str) and analysis_date:
            if avgo_csv:
                pos, reason = _compute_pos20(avgo_csv, analysis_date)
                rec["pos20"] = pos
                rec["pos20_skip_reason"] = reason
                if reason is not None:
                    pos20_skip_counts[reason] = (
                        pos20_skip_counts.get(reason, 0) + 1
                    )
            if avgo_csv and soxx_csv:
                avgo_ret = _compute_nday_return(avgo_csv, analysis_date)
                soxx_ret = _compute_nday_return(soxx_csv, analysis_date)
                if avgo_ret is not None and soxx_ret is not None:
                    rec["avgo_minus_soxx_20d"] = avgo_ret - soxx_ret

        records.append(rec)

    if pos20_skip_counts:
        warnings.append(
            "pos20 skipped: " + ", ".join(
                f"{k}={v}" for k, v in sorted(pos20_skip_counts.items())
            )
        )
    if skipped_payloads:
        warnings.append(
            f"{skipped_payloads} payload(s) skipped (missing or invalid JSON)"
        )

    paired_outcomes = sum(
        1 for r in records
        if r["direction_correct_label"] in ("correct", "wrong")
    )
    pending_outcomes = sum(
        1 for r in records if r["direction_correct_label"] == "pending"
    )

    return {
        "status": "ok",
        "symbol": sym,
        "records_scanned": len(rows),
        "valid_payloads": len(records),
        "paired_outcomes": paired_outcomes,
        "pending_outcomes": pending_outcomes,
        "calibration_ready": paired_outcomes >= _MIN_RECOMMENDED_PAIRS,
        "time_range": _compute_time_range(records),
        "pos20_quartile_bias": _compute_pos20_quartile_bias(records, warnings),
        "r4_signature": _compute_r4_signature(records),
        "confidence_by_regime": _compute_confidence_by_regime(records),
        "peer_adjustment_summary": _compute_peer_adjustment_summary(records),
        "soft_signal_summary": _compute_soft_signal_summary(records),
        "monthly_accuracy": _compute_monthly_accuracy(records),
        "high_confidence_failure_slices":
            _compute_high_confidence_failure_slices(records),
        "warnings": warnings,
    }
