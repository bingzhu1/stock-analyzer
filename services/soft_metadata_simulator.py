"""services/soft_metadata_simulator.py — read-only soft metadata sidecar.

Step 2G-5 implementation of the ``exclusion_system.extras.soft_metadata``
sidecar specified by Step 2G-4.5 (commit 18936f2). Emits the
``soft_metadata.v1`` schema with two active candidates
(``r4_overextension`` / ``bullish_high_pos20_residual``) and the
removed-candidate enforcement spelled out in the schema review checkpoint.

Step 2G-4.5 §10 / §12 contract:
- read-only: ``simulate_soft_metadata`` is a pure function (no DB / CSV /
  network); ``build_soft_metadata_baseline`` is a SELECT-only DB reader
  that delegates to ``services.regime_diagnostics_dashboard`` for the
  full record loop and then computes the bullish_high_pos20 residual
  by re-using the dashboard's private helpers
- never mutates the DB, never writes files, never raises (status / warnings
  surfaced via the returned dict)
- never imports ``yfinance`` / ``requests`` / ``longbridge`` / ``broker`` /
  ``paper_trade``
- never imports the v1 stub trio (``confidence_engine`` /
  ``contradiction_engine`` / ``risk_model``)
- R4 thresholds are imported from
  ``services.regime_diagnostics_dashboard`` — never redefined locally
  (Step 2G-4.5 Blocker 4; tested via ``assert ... is ...``)
- removed candidates (``bullish_peer_upgrade_overextension`` /
  ``peer_weaken_metadata_only`` / ``high_path_risk_metadata_only`` /
  ``peer_path_lower_bullish``) are NOT emitted in ``signals[i].name``
  (Step 2G-4.5 Blocker 6 / 7)
- severity enum is ``{"low", "medium"}`` only — no ``"high"`` / ``"hard"``
  (Step 2G-4.5 Blocker 8)
- ``summary.hard_exclusion_allowed`` is ALWAYS ``False`` (Step 2G-4.5 §9.4)
- ``analysis_date >= final_test_cutoff`` (default ``"2026-01-01"``) refuses
  to emit signals (Step 2G-4.5 §13 / §10.8.3)

Public API:
    simulate_soft_metadata(payload, *, regime_features=None, baseline=None,
                           analysis_date=None, final_test_cutoff="2026-01-01")
    build_soft_metadata_baseline(db_path=None, symbol="AVGO", limit=450,
                                 *, coded_data_dir=None)

Schema returned (soft_metadata.v1) — see Step 2G-4.5 §5.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# R4 threshold constants imported from the regime diagnostics dashboard
# (Step 2G-4.5 Blocker 4). Tests enforce identity via ``is`` to prevent
# silent drift if the dashboard's thresholds ever change.
from services.regime_diagnostics_dashboard import (
    _R4_AVGO_MINUS_SOXX_THRESHOLD,
    _R4_POS20_THRESHOLD,
    _is_r4_record as _dashboard_is_r4_record,  # re-used in baseline residual
    _read_coded_csv as _dashboard_read_csv,
    _compute_pos20 as _dashboard_compute_pos20,
    _compute_nday_return as _dashboard_compute_nday_return,
    _PEER_FOR_REGIME,
    _resolve_coded_data_dir as _dashboard_resolve_coded_dir,
    summarize_regime_diagnostics_dashboard,
)


SCHEMA_VERSION = "soft_metadata.v1"
METRICS_SOURCE = "regime_diagnostics_dashboard_v1"
HOLDOUT_STATUS = "FAIL"  # Step 3A-4 / 3B-1 holdout FAIL — frozen for v1
DEFAULT_FINAL_TEST_CUTOFF = "2026-01-01"

# Severity enum (Step 2G-4.5 Blocker 8 — no "high" / "hard")
SEVERITY_LOW = "low"
SEVERITY_MEDIUM = "medium"
SEVERITY_NONE = "none"  # only valid as summary.max_severity when signals=[]
_VALID_SEVERITIES = frozenset({SEVERITY_LOW, SEVERITY_MEDIUM})

# Active candidate enum (Step 2G-4.5 §6.1)
ACTIVE_SIGNAL_NAMES = frozenset({
    "r4_overextension",
    "bullish_high_pos20_residual",
})

# Severity classification thresholds (Step 2G-4.5 §8.1, strict <, > only)
_SEVERITY_ACC_BOUND = 0.45
_SEVERITY_GAP_BOUND = 0.50

_HARD_FORBIDDEN_FE_GATE = 0.10
_HARD_FORBIDDEN_NB_GATE = 0.05


# ── helpers ──────────────────────────────────────────────────────────────

def _now_iso() -> str:
    """ISO 8601 UTC timestamp at second precision."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _to_float(value: Any) -> float | None:
    if value in (None, "", "nan", "NaN"):
        return None
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_real_number(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    return isinstance(value, (int, float))


def _classify_severity(metrics: dict[str, Any] | None) -> str:
    """Pure severity classifier (Step 2G-4.5 §8.1).

    Returns ``"low"`` when ``accuracy >= 0.45`` AND ``bias_gap <= 0.50``,
    else ``"medium"``. Strict ``<`` / ``>`` at the boundaries (Step
    2G-4.5 §8 / §10.4.2-3). When metrics are missing or partial, default
    to ``"medium"`` — the candidate fired, so we err toward the more
    cautious bucket; the missing metrics are surfaced via ``warnings``
    elsewhere.
    """
    if not isinstance(metrics, dict):
        return SEVERITY_MEDIUM
    acc = metrics.get("accuracy")
    gap = metrics.get("bias_gap")
    if not _is_real_number(acc) or not _is_real_number(gap):
        return SEVERITY_MEDIUM
    if acc < _SEVERITY_ACC_BOUND or gap > _SEVERITY_GAP_BOUND:
        return SEVERITY_MEDIUM
    return SEVERITY_LOW


def _normalize_peer_subtype(value: Any) -> str:
    """Map peer_adjustment to the four-value enum used in trigger_context."""
    if value in ("upgrade", "hold", "downgrade"):
        return value
    return "unknown"


def _matched_or_branch(confidence_level: Any, primary_score_raw: Any) -> str:
    """Identify which OR-branch of R4 fired (Step 2G-4.5 §10.2.6-7)."""
    high = confidence_level == "high"
    psr_pass = (
        _is_real_number(primary_score_raw) and float(primary_score_raw) > 2
    )
    if high and psr_pass:
        return "both"
    if high:
        return "confidence_high"
    if psr_pass:
        return "primary_score_raw_gt_2"
    return "none"  # caller should not have fired R4 at all


def _hard_forbidden_breakdown_for_r4(
    metrics: dict[str, Any] | None,
) -> list[str]:
    """Per-condition reason list (Step 2G-4.5 §5)."""
    out: list[str] = []
    if isinstance(metrics, dict):
        fer = metrics.get("false_exclusion_rate")
        if _is_real_number(fer) and float(fer) > _HARD_FORBIDDEN_FE_GATE:
            out.append(
                f"false_exclusion_rate={float(fer):.4f} > {_HARD_FORBIDDEN_FE_GATE}"
            )
        nb = metrics.get("net_benefit")
        if _is_real_number(nb) and float(nb) < _HARD_FORBIDDEN_NB_GATE:
            out.append(
                f"net_benefit={float(nb):.4f} < {_HARD_FORBIDDEN_NB_GATE}"
            )
    out.append("anti_false_exclusion_not_connected")
    return out


def _empty_metrics_window() -> dict[str, Any]:
    return {
        "analysis_date_min": None,
        "analysis_date_max": None,
        "paired_total": 0,
        "db_snapshot_id": None,
    }


# ── candidate triggers ───────────────────────────────────────────────────

def _extract_features(
    payload: dict, regime_features: dict | None
) -> dict[str, Any]:
    """Pull the trigger-relevant fields out of the contract payload + the
    caller-supplied regime_features dict. Returns a single flat dict."""
    fp = _safe_dict(payload.get("final_projection"))
    cs = _safe_dict(payload.get("confidence_system"))
    cs_x = _safe_dict(cs.get("extras"))
    pa = _safe_dict(payload.get("peer_confirmation_adjustment"))

    rf = regime_features if isinstance(regime_features, dict) else {}
    pos20 = _to_float(rf.get("pos20"))
    diff = _to_float(rf.get("avgo_minus_soxx_20d"))

    return {
        "final_direction": fp.get("final_direction"),
        "confidence_level": cs.get("confidence_level"),
        "primary_score_raw": cs_x.get("primary_score_raw"),
        "peer_adjustment": pa.get("peer_adjustment"),
        "pos20": pos20,
        "avgo_minus_soxx_20d": diff,
    }


def _r4_triggered(features: dict[str, Any]) -> bool:
    """R4 trigger predicate — mirrors regime_diagnostics_dashboard._is_r4_record."""
    diff = features["avgo_minus_soxx_20d"]
    pos = features["pos20"]
    if diff is None or pos is None:
        return False
    if diff <= _R4_AVGO_MINUS_SOXX_THRESHOLD:
        return False
    if pos <= _R4_POS20_THRESHOLD:
        return False
    if features["final_direction"] != "偏多":
        return False
    if features["confidence_level"] == "high":
        return True
    psr = features["primary_score_raw"]
    return _is_real_number(psr) and float(psr) > 2


def _bullish_high_pos20_triggered(features: dict[str, Any]) -> bool:
    """bullish_high_pos20 superset trigger (R4-residual decided separately)."""
    pos = features["pos20"]
    if pos is None or pos <= _R4_POS20_THRESHOLD:
        return False
    if features["final_direction"] != "偏多":
        return False
    return features["confidence_level"] == "high"


def _build_r4_signal(
    features: dict[str, Any],
    baseline: dict | None,
) -> dict[str, Any]:
    metrics = _safe_dict((baseline or {}).get("r4_overextension")) or None
    severity = _classify_severity(metrics)
    return {
        "name": "r4_overextension",
        "display_label": "高位跑赢同行后的偏多过热",
        "severity": severity,
        "dedup_group": "bullish_overextension",
        "raw_features": {
            "avgo_minus_soxx_20d": features["avgo_minus_soxx_20d"],
            "pos20": features["pos20"],
        },
        "trigger_context": {
            "final_direction": features["final_direction"],
            "confidence_level": features["confidence_level"],
            "primary_score_raw": features["primary_score_raw"],
            "matched_or_branch": _matched_or_branch(
                features["confidence_level"], features["primary_score_raw"]
            ),
            "peer_subtype": _normalize_peer_subtype(features["peer_adjustment"]),
        },
        "historical_metrics_in_sample": metrics if metrics else {},
        "holdout_status": HOLDOUT_STATUS,
        "recommended_action": "review_only",
        "hard_forbidden_primary_reason": "false_exclusion_rate_too_high",
        "hard_forbidden_breakdown": _hard_forbidden_breakdown_for_r4(metrics),
    }


def _build_residual_signal(
    features: dict[str, Any],
    baseline: dict | None,
) -> dict[str, Any]:
    metrics = _safe_dict((baseline or {}).get("bullish_high_pos20_residual")) or None
    severity = _classify_severity(metrics)
    return {
        "name": "bullish_high_pos20_residual",
        "display_label": "高位偏多 + 高置信（剔除 R4 后残差）",
        "severity": severity,
        "dedup_group": "bullish_overextension",
        "raw_features": {
            "pos20": features["pos20"],
        },
        "trigger_context": {
            "final_direction": features["final_direction"],
            "confidence_level": features["confidence_level"],
            "peer_subtype": _normalize_peer_subtype(features["peer_adjustment"]),
        },
        "historical_metrics_in_sample": metrics if metrics else {},
        "holdout_status": HOLDOUT_STATUS,
        "recommended_action": "review_only",
        "hard_forbidden_primary_reason": "false_exclusion_rate_too_high",
        "hard_forbidden_breakdown": _hard_forbidden_breakdown_for_r4(metrics),
    }


# ── summary builders ────────────────────────────────────────────────────

def _max_severity(signals: list[dict[str, Any]]) -> str:
    if not signals:
        return SEVERITY_NONE
    rank = {SEVERITY_LOW: 0, SEVERITY_MEDIUM: 1}
    return max(
        (s["severity"] for s in signals if s.get("severity") in rank),
        key=lambda x: rank[x],
        default=SEVERITY_NONE,
    )


def _build_summary(
    signals: list[dict[str, Any]], warnings: list[str]
) -> dict[str, Any]:
    return {
        "has_overextension_signal": len(signals) > 0,
        "max_severity": _max_severity(signals),
        "hard_exclusion_allowed": False,  # Step 2G-4.5 §9.4 invariant
        "signal_count": len(signals),
        "primary_signal": signals[0]["name"] if signals else None,
        "warnings": list(warnings),
    }


def _shell(
    metrics_window: dict[str, Any],
    metrics_computed_at: str,
    signals: list[dict[str, Any]],
    warnings: list[str],
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "metrics_source": METRICS_SOURCE,
        "metrics_window": metrics_window,
        "metrics_computed_at": metrics_computed_at,
        "signals": signals,
        "summary": _build_summary(signals, warnings),
    }


# ── analysis_date resolution ────────────────────────────────────────────

def _resolve_analysis_date(
    payload: dict, override: str | None
) -> str | None:
    if isinstance(override, str) and override.strip():
        return override.strip()
    cs = _safe_dict(payload.get("current_structure"))
    candidate = cs.get("analysis_date")
    if isinstance(candidate, str) and candidate.strip():
        return candidate.strip()
    return None


def _is_within_final_test_range(
    analysis_date: str | None, cutoff: str
) -> bool:
    """True iff analysis_date >= cutoff (string compare on YYYY-MM-DD)."""
    if not isinstance(analysis_date, str):
        return False
    return analysis_date[:10] >= cutoff[:10]


# ── public API: simulate ────────────────────────────────────────────────

def simulate_soft_metadata(
    payload: dict,
    *,
    regime_features: dict | None = None,
    baseline: dict | None = None,
    analysis_date: str | None = None,
    final_test_cutoff: str = DEFAULT_FINAL_TEST_CUTOFF,
) -> dict[str, Any]:
    """Build the ``soft_metadata.v1`` sidecar for a single contract payload.

    Pure function: never reads DB / CSV / network. ``regime_features`` is
    a caller-injected dict with ``{"pos20": float, "avgo_minus_soxx_20d":
    float}`` (the simulator can't compute these from a payload alone —
    the payload doesn't carry them). When ``regime_features`` is None or
    missing either field, R4 / residual signals can't be evaluated and a
    warning is emitted.

    ``baseline`` is the caller-injected historical metrics dict from
    ``build_soft_metadata_baseline``. When None, signals can still emit
    but ``historical_metrics_in_sample`` will be ``{}``.

    ``analysis_date`` overrides the date pulled from
    ``payload['current_structure']['analysis_date']``; used to enforce the
    final-test cutoff (Step 2G-4.5 §13).
    """
    if not isinstance(payload, dict):
        return _shell(
            metrics_window=_empty_metrics_window(),
            metrics_computed_at=_now_iso(),
            signals=[],
            warnings=["invalid_payload_type"],
        )

    metrics_window = _safe_dict((baseline or {}).get("metrics_window")) \
        or _empty_metrics_window()
    metrics_computed_at = (
        (baseline or {}).get("metrics_computed_at") or _now_iso()
    )

    warnings: list[str] = []
    if baseline is None:
        warnings.append("missing_baseline")

    resolved_date = _resolve_analysis_date(payload, analysis_date)

    # Step 2G-4.5 §13 / §10.8.3: refuse signals on / after final-test cutoff.
    if _is_within_final_test_range(resolved_date, final_test_cutoff):
        warnings.append("final_test_range_refusal")
        return _shell(metrics_window, metrics_computed_at, [], warnings)

    features = _extract_features(payload, regime_features)
    if features["pos20"] is None or features["avgo_minus_soxx_20d"] is None:
        # Either pos20 or the SOXX diff is missing — neither active
        # candidate can be evaluated. Emit a warning naming the gap and
        # return an empty signals list.
        missing: list[str] = []
        if features["pos20"] is None:
            missing.append("pos20")
        if features["avgo_minus_soxx_20d"] is None:
            missing.append("avgo_minus_soxx_20d")
        warnings.append(
            "missing_regime_features: " + ", ".join(missing)
        )
        return _shell(metrics_window, metrics_computed_at, [], warnings)

    if (
        baseline is not None
        and not isinstance(baseline.get("r4_overextension"), dict)
    ):
        warnings.append("missing_baseline_metrics: r4_overextension")
    if (
        baseline is not None
        and not isinstance(
            baseline.get("bullish_high_pos20_residual"), dict
        )
    ):
        warnings.append(
            "missing_baseline_metrics: bullish_high_pos20_residual"
        )

    signals: list[dict[str, Any]] = []
    r4_hit = _r4_triggered(features)
    if r4_hit:
        signals.append(_build_r4_signal(features, baseline))
    elif _bullish_high_pos20_triggered(features):
        # residual = bullish_high_pos20 ∧ NOT R4 (Step 2G-4.5 §6.1 / §9)
        signals.append(_build_residual_signal(features, baseline))

    # Hard upper bound (Step 2G-4.5 §9.3); v1 has at most 1 signal in
    # practice because the two candidates share a dedup_group.
    if len(signals) > 3:
        signals = signals[:3]

    return _shell(metrics_window, metrics_computed_at, signals, warnings)


# ── public API: baseline builder ─────────────────────────────────────────

def _empty_baseline() -> dict[str, Any]:
    return {
        "metrics_source": METRICS_SOURCE,
        "metrics_window": _empty_metrics_window(),
        "metrics_computed_at": _now_iso(),
        "r4_overextension": None,
        "bullish_high_pos20_residual": None,
        "holdout_status": HOLDOUT_STATUS,
        "warnings": [],
    }


def _r4_baseline_from_dashboard(
    diag: dict[str, Any],
) -> dict[str, Any] | None:
    """Extract R4 historical metrics from a dashboard summary dict.

    Returns None when the R4 section is missing or has no paired records
    — the simulator will then emit ``historical_metrics_in_sample = {}``
    plus a ``missing_baseline_metrics`` warning.
    """
    r4 = _safe_dict(diag.get("r4_signature"))
    if not r4 or not r4.get("paired"):
        return None
    fer = _to_float(r4.get("accuracy"))  # 偏多-only slice → false_exclusion = accuracy
    nb = _net_benefit_from_dashboard(diag, candidate_paired=r4.get("paired"),
                                     candidate_correct=r4.get("correct"))
    return {
        "samples": r4.get("samples"),
        "paired": r4.get("paired"),
        "accuracy": r4.get("accuracy"),
        "bias_gap": r4.get("bias_gap"),
        "false_exclusion_rate": fer,
        "net_benefit": nb,
    }


def _net_benefit_from_dashboard(
    diag: dict[str, Any],
    candidate_paired: Any,
    candidate_correct: Any,
) -> float | None:
    """Counterfactual net_benefit = (post-exclusion acc) − (baseline acc).

    Baseline correct count is derived by summing ``confidence_by_regime.overall``
    buckets (which together cover every record with a normalized confidence
    level). When any inputs are missing or denominators are zero, returns
    None and the caller will surface a warning.
    """
    if not _is_real_number(candidate_paired) or not _is_real_number(candidate_correct):
        return None
    overall = _safe_dict(
        _safe_dict(diag.get("confidence_by_regime")).get("overall")
    )
    base_correct = 0
    base_paired = 0
    for level_bucket in overall.values():
        b = _safe_dict(level_bucket)
        c = b.get("correct"); w = b.get("wrong")
        if _is_real_number(c) and _is_real_number(w):
            base_correct += int(c)
            base_paired += int(c) + int(w)
    if base_paired == 0:
        return None
    base_acc = base_correct / base_paired
    post_paired = base_paired - int(candidate_paired)
    post_correct = base_correct - int(candidate_correct)
    if post_paired <= 0:
        return None
    post_acc = post_correct / post_paired
    return post_acc - base_acc


def _residual_baseline_from_db(
    db_path: str | Path | None,
    symbol: str,
    limit: int,
    coded_data_dir: str | Path | None,
    diag: dict[str, Any],
) -> tuple[dict[str, Any] | None, list[str]]:
    """Compute bullish_high_pos20_residual = bullish + high + pos20>0.62 − R4.

    Re-uses the dashboard's private CSV / pos20 / R4 helpers so the
    arithmetic exactly matches what the dashboard would emit. Returns
    ``(metrics_dict | None, warnings)``. Reads DB SELECT-only.
    """
    import json
    import sqlite3

    import services.prediction_store as _ps  # local import — avoids module-level coupling

    warnings: list[str] = []
    db = Path(db_path) if db_path is not None else Path(_ps.DB_PATH)
    pattern = f"replay_{symbol}_%"
    sql = """
        SELECT p.id, p.analysis_date, p.contract_payload_json,
               (SELECT o.direction_correct FROM outcome_log o
                 WHERE o.prediction_id = p.id
                 ORDER BY o.captured_at DESC, o.rowid DESC LIMIT 1) AS dc,
               (SELECT o.actual_close FROM outcome_log o
                 WHERE o.prediction_id = p.id
                 ORDER BY o.captured_at DESC, o.rowid DESC LIMIT 1) AS ac,
               (SELECT o.actual_prev_close FROM outcome_log o
                 WHERE o.prediction_id = p.id
                 ORDER BY o.captured_at DESC, o.rowid DESC LIMIT 1) AS apc
          FROM prediction_log p
         WHERE p.snapshot_id LIKE ?
         ORDER BY p.analysis_date DESC, p.rowid DESC
         LIMIT ?
    """
    try:
        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(sql, (pattern, limit)).fetchall()
        conn.close()
    except Exception as exc:
        warnings.append(f"residual_db_read_failed: {exc}")
        return None, warnings

    coded_dir = _dashboard_resolve_coded_dir(coded_data_dir)
    avgo_csv = _dashboard_read_csv(symbol, coded_dir)
    soxx_csv = _dashboard_read_csv(_PEER_FOR_REGIME, coded_dir)
    if not avgo_csv or not soxx_csv:
        warnings.append("residual_skipped: coded_data_csv_missing")
        return None, warnings

    samples = paired = correct = wrong = 0
    for row in rows:
        try:
            payload = json.loads(row["contract_payload_json"]) if row["contract_payload_json"] else None
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(payload, dict):
            continue
        fp = _safe_dict(payload.get("final_projection"))
        cs = _safe_dict(payload.get("confidence_system"))
        cs_x = _safe_dict(cs.get("extras"))

        if fp.get("final_direction") != "偏多":
            continue
        if cs.get("confidence_level") != "high":
            continue
        adate = row["analysis_date"]
        if not isinstance(adate, str) or not adate:
            continue
        pos, _ = _dashboard_compute_pos20(avgo_csv, adate)
        if pos is None or pos <= _R4_POS20_THRESHOLD:
            continue
        avgo_ret = _dashboard_compute_nday_return(avgo_csv, adate)
        soxx_ret = _dashboard_compute_nday_return(soxx_csv, adate)
        diff = (avgo_ret - soxx_ret) if (
            avgo_ret is not None and soxx_ret is not None
        ) else None

        # R4 needs (high ∨ psr>2). High confidence is true here, so R4
        # additionally requires diff > threshold.
        is_r4 = diff is not None and diff > _R4_AVGO_MINUS_SOXX_THRESHOLD
        if is_r4:
            continue  # exclude R4 to get residual

        samples += 1
        dc = row["dc"]
        if dc is None:
            continue
        paired += 1
        if dc:
            correct += 1
        else:
            wrong += 1

    if paired == 0:
        return None, warnings
    accuracy = correct / paired
    bias_gap = 1.0 - accuracy  # bullish-only slice → pbull=1.0 → gap = 1−aup
    fer = accuracy  # bullish slice: false_exclusion_rate equals accuracy
    nb = _net_benefit_from_dashboard(
        diag, candidate_paired=paired, candidate_correct=correct
    )
    return {
        "samples": samples,
        "paired": paired,
        "accuracy": accuracy,
        "bias_gap": bias_gap,
        "false_exclusion_rate": fer,
        "net_benefit": nb,
    }, warnings


def build_soft_metadata_baseline(
    db_path: str | Path | None = None,
    symbol: str = "AVGO",
    limit: int = 450,
    *,
    coded_data_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Read-only baseline builder.

    Calls ``summarize_regime_diagnostics_dashboard`` for the R4 metrics,
    then computes the bullish_high_pos20 residual via a small SELECT-only
    DB pass (reusing the dashboard's private CSV / pos20 / SOXX helpers
    so arithmetic stays consistent). Always returns a dict; never raises.
    """
    warnings: list[str] = []
    diag = summarize_regime_diagnostics_dashboard(
        db_path=db_path, symbol=symbol, limit=limit,
        coded_data_dir=coded_data_dir,
    )
    if diag.get("status") == "error":
        out = _empty_baseline()
        out["warnings"].append(f"baseline_error: {diag.get('error')}")
        return out
    if diag.get("status") == "no_records":
        out = _empty_baseline()
        out["warnings"].append("baseline_no_records")
        return out

    r4_metrics = _r4_baseline_from_dashboard(diag)
    if r4_metrics is None:
        warnings.append("r4_baseline_unavailable")

    residual_metrics, residual_warnings = _residual_baseline_from_db(
        db_path=db_path, symbol=symbol, limit=limit,
        coded_data_dir=coded_data_dir, diag=diag,
    )
    warnings.extend(residual_warnings)
    if residual_metrics is None and "residual_skipped: coded_data_csv_missing" not in residual_warnings:
        warnings.append("residual_baseline_unavailable")

    time_range = _safe_dict(diag.get("time_range"))
    return {
        "metrics_source": METRICS_SOURCE,
        "metrics_window": {
            "analysis_date_min": time_range.get("analysis_date_min"),
            "analysis_date_max": time_range.get("analysis_date_max"),
            "paired_total": diag.get("paired_outcomes", 0),
            "db_snapshot_id": None,
        },
        "metrics_computed_at": _now_iso(),
        "r4_overextension": r4_metrics,
        "bullish_high_pos20_residual": residual_metrics,
        "holdout_status": HOLDOUT_STATUS,
        "warnings": warnings,
    }
