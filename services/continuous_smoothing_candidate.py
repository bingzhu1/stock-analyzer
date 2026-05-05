"""services/continuous_smoothing_candidate.py — pure read-only candidate generator.

Step 3R-3.1 implementation per Step 3R-3 design (commit ``65fe411``) +
checkpoint (``596e013``). Computes ``continuous_smoothing_candidate.v1``
from ``regime_labels.v1`` raw_features (the output of
``services.regime_labels_builder.build_regime_labels``).

This module is **read-only diagnostics**:
- never reads DB / CSV / network; never imports ``yfinance`` /
  ``requests`` / trading APIs / ``services.prediction_store`` /
  ``predict`` / ``scanner`` / ``streamlit``
- never mutates input ``regime_labels`` dict
- never raises (always returns a dict; missing data → ``risk_score=None``
  + ``risk_bucket="unknown"`` + warning string)
- 2026 final-test cutoff: ``as_of_date >= final_test_cutoff`` →
  ``final_test_refusal=True`` + ``risk_score=None`` + warning
  ``final_test_range_refusal``; also propagates when input
  ``regime_labels.final_test_refusal=True``
- v1 coefficients are **design seed** (not validated); the helper does
  NOT claim pass / fail — validation reports are produced separately
  under Step 3R-4 protocol via ``services.regime_validation_helper``

Public API:
    build_continuous_smoothing_candidate(
        regime_labels,
        *,
        as_of_date=None,
        final_test_cutoff="2026-01-01",
    ) -> dict
"""
from __future__ import annotations

import math
from typing import Any


SCHEMA_VERSION = "continuous_smoothing_candidate.v1"
CANDIDATE_NAME = "continuous_smoothing_v1"
DEFAULT_FINAL_TEST_CUTOFF = "2026-01-01"

# ── seed coefficients ────────────────────────────────────────────────────
# Step 3R-3 design §5: shape only. These are NOT validated coefficients.
SEED_COEFFICIENTS: dict[str, float] = {
    "pos20": 1.2,
    "avgo_minus_soxx_20d": 1.0,
    "peer_5d_aligned_pct": -0.8,
    "market_trend_strength": -0.7,
    "monthly_shock": 0.5,
}

_REQUIRED_RAW_FEATURE_KEYS: tuple[str, ...] = (
    "pos20",
    "avgo_minus_soxx_20d",
    "peer_5d_aligned_pct",
    "qqq_60d_slope_per_month",
    "qqq_60d_drawdown",
    "soxx_60d_slope_per_month",
    "monthly_max_abs_daily_return",
    "monthly_return_pct",
)


# ── helpers ──────────────────────────────────────────────────────────────


def _safe_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if f != f:  # NaN
        return None
    return f


def _is_within_final_test_range(date_str: Any, cutoff: str) -> bool:
    if not isinstance(date_str, str):
        return False
    return date_str >= cutoff


def _sigmoid(z: float) -> float:
    if z >= 0:
        ez = math.exp(-z)
        return 1.0 / (1.0 + ez)
    ez = math.exp(z)
    return ez / (1.0 + ez)


def _compute_market_trend_strength(
    qqq_slope: float | None,
    soxx_slope: float | None,
    qqq_drawdown: float | None,
) -> float | None:
    if qqq_slope is None or soxx_slope is None or qqq_drawdown is None:
        return None
    # Precedence: strong_bull → bull → weak → neutral
    if qqq_slope > 0.015 and soxx_slope > 0.015 and qqq_drawdown < 0.05:
        return 1.0
    if qqq_slope > 0.01 or soxx_slope > 0.01:
        return 0.6
    if qqq_drawdown > 0.10 or (qqq_slope < -0.005 and soxx_slope < -0.005):
        return -0.5
    return 0.0


def _compute_monthly_shock(
    monthly_max_abs_daily_return: float | None,
    monthly_return_pct: float | None,
) -> float | None:
    if monthly_max_abs_daily_return is None and monthly_return_pct is None:
        return None
    if monthly_max_abs_daily_return is not None and monthly_max_abs_daily_return >= 0.08:
        return 1.0
    if monthly_return_pct is not None and monthly_return_pct >= 0.12:
        return 0.5
    return 0.0


def _bucket_risk_score(risk_score: float | None) -> str:
    if risk_score is None:
        return "unknown"
    if risk_score < 0.35:
        return "low"
    if risk_score < 0.60:
        return "medium"
    if risk_score < 0.80:
        return "high"
    return "extreme"


def _refusal_payload(
    *,
    as_of_date: str,
    data_cutoff_date: str,
    warnings: list[str],
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "as_of_date": as_of_date,
        "data_cutoff_date": data_cutoff_date,
        "candidate_name": CANDIDATE_NAME,
        "risk_score": None,
        "adjustment_score": None,
        "risk_bucket": "unknown",
        "features_used": {
            "pos20": None,
            "avgo_minus_soxx_20d": None,
            "peer_5d_aligned_pct": None,
            "market_trend_strength": None,
            "monthly_shock": None,
            "seed_coefficients": dict(SEED_COEFFICIENTS),
        },
        "warnings": list(warnings),
        "final_test_refusal": True,
    }


# ── public API ───────────────────────────────────────────────────────────


def build_continuous_smoothing_candidate(
    regime_labels: dict[str, Any],
    *,
    as_of_date: str | None = None,
    final_test_cutoff: str = DEFAULT_FINAL_TEST_CUTOFF,
) -> dict[str, Any]:
    """Build a `continuous_smoothing_candidate.v1` dict.

    Pure read-only — see module docstring for full constraints.

    The seed coefficients (`SEED_COEFFICIENTS`) are design-stage values
    from Step 3R-3 §5; they are NOT validated and the helper does NOT
    claim pass / fail.
    """
    warnings: list[str] = []

    # Resolve as_of_date: explicit arg > regime_labels["as_of_date"]
    if as_of_date is None:
        as_of_date = regime_labels.get("as_of_date") if isinstance(regime_labels, dict) else None
    if not isinstance(as_of_date, str):
        as_of_date = ""
    data_cutoff_date = as_of_date

    # Final-test cutoff
    if _is_within_final_test_range(as_of_date, final_test_cutoff):
        warnings.append("final_test_range_refusal")
        return _refusal_payload(
            as_of_date=as_of_date,
            data_cutoff_date=data_cutoff_date,
            warnings=warnings,
        )

    # Propagate regime_labels.final_test_refusal
    if isinstance(regime_labels, dict) and regime_labels.get("final_test_refusal"):
        warnings.append("regime_labels_final_test_refusal_propagated")
        return _refusal_payload(
            as_of_date=as_of_date,
            data_cutoff_date=data_cutoff_date,
            warnings=warnings,
        )

    # Read raw_features
    raw_features = (
        regime_labels.get("raw_features") if isinstance(regime_labels, dict) else None
    )
    if not isinstance(raw_features, dict):
        warnings.append("missing_required_feature:raw_features")
        return {
            "schema_version": SCHEMA_VERSION,
            "as_of_date": as_of_date,
            "data_cutoff_date": data_cutoff_date,
            "candidate_name": CANDIDATE_NAME,
            "risk_score": None,
            "adjustment_score": None,
            "risk_bucket": "unknown",
            "features_used": {
                "pos20": None,
                "avgo_minus_soxx_20d": None,
                "peer_5d_aligned_pct": None,
                "market_trend_strength": None,
                "monthly_shock": None,
                "seed_coefficients": dict(SEED_COEFFICIENTS),
            },
            "warnings": list(warnings),
            "final_test_refusal": False,
        }

    feature_values: dict[str, float | None] = {}
    missing_keys: list[str] = []
    for key in _REQUIRED_RAW_FEATURE_KEYS:
        v = _safe_float(raw_features.get(key))
        feature_values[key] = v
        if v is None:
            missing_keys.append(key)

    market_trend_strength = _compute_market_trend_strength(
        qqq_slope=feature_values["qqq_60d_slope_per_month"],
        soxx_slope=feature_values["soxx_60d_slope_per_month"],
        qqq_drawdown=feature_values["qqq_60d_drawdown"],
    )
    monthly_shock = _compute_monthly_shock(
        monthly_max_abs_daily_return=feature_values["monthly_max_abs_daily_return"],
        monthly_return_pct=feature_values["monthly_return_pct"],
    )

    if missing_keys:
        for k in missing_keys:
            warnings.append(f"missing_required_feature:{k}")
        return {
            "schema_version": SCHEMA_VERSION,
            "as_of_date": as_of_date,
            "data_cutoff_date": data_cutoff_date,
            "candidate_name": CANDIDATE_NAME,
            "risk_score": None,
            "adjustment_score": None,
            "risk_bucket": "unknown",
            "features_used": {
                "pos20": feature_values["pos20"],
                "avgo_minus_soxx_20d": feature_values["avgo_minus_soxx_20d"],
                "peer_5d_aligned_pct": feature_values["peer_5d_aligned_pct"],
                "market_trend_strength": market_trend_strength,
                "monthly_shock": monthly_shock,
                "seed_coefficients": dict(SEED_COEFFICIENTS),
            },
            "warnings": list(warnings),
            "final_test_refusal": False,
        }

    # All features present — compute risk_score.
    z = (
        SEED_COEFFICIENTS["pos20"] * feature_values["pos20"]
        + SEED_COEFFICIENTS["avgo_minus_soxx_20d"] * feature_values["avgo_minus_soxx_20d"]
        + SEED_COEFFICIENTS["peer_5d_aligned_pct"] * feature_values["peer_5d_aligned_pct"]
        + SEED_COEFFICIENTS["market_trend_strength"] * (market_trend_strength or 0.0)
        + SEED_COEFFICIENTS["monthly_shock"] * (monthly_shock or 0.0)
    )
    risk_score = _sigmoid(z)
    risk_bucket = _bucket_risk_score(risk_score)
    adjustment_score = risk_score - 0.5

    return {
        "schema_version": SCHEMA_VERSION,
        "as_of_date": as_of_date,
        "data_cutoff_date": data_cutoff_date,
        "candidate_name": CANDIDATE_NAME,
        "risk_score": risk_score,
        "adjustment_score": adjustment_score,
        "risk_bucket": risk_bucket,
        "features_used": {
            "pos20": feature_values["pos20"],
            "avgo_minus_soxx_20d": feature_values["avgo_minus_soxx_20d"],
            "peer_5d_aligned_pct": feature_values["peer_5d_aligned_pct"],
            "market_trend_strength": market_trend_strength,
            "monthly_shock": monthly_shock,
            "seed_coefficients": dict(SEED_COEFFICIENTS),
        },
        "warnings": list(warnings),
        "final_test_refusal": False,
    }
