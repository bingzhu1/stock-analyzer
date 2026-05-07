"""services/continuous_smoothing_candidate_v2.py — false-exclusion-risk-aware sidecar.

Step 3R-3.3F-A implementation per Step 3R-3.3F v2 candidate design
(commit ``b16fce9``) + checkpoint (``7eda5b4``).

This module is **read-only diagnostics**:

- never reads DB / CSV / network
- never imports ``services.continuous_smoothing_candidate`` (v1),
  ``yfinance``, ``requests``, ``urllib``, ``urllib3``, ``httpx``, trading
  APIs (``longbridge`` / ``broker`` / ``paper_trade``),
  ``services.prediction_store``, ``services.outcome_capture``,
  ``predict``, ``scanner``, ``streamlit`` — see the test file for the
  full forbidden-import list
- never mutates input ``regime_labels`` dict
- never raises (always returns a dict; missing data → ``risk_bucket="abstain"``
  with a populated ``abstain_reason``)
- 2026 final-test cutoff: ``as_of_date >= final_test_cutoff`` →
  ``risk_bucket="abstain"`` + ``final_test_refusal=True`` +
  ``abstain_reason="final_test_range_refusal"`` + warning
- propagates ``regime_labels.final_test_refusal=True`` → same abstain
  payload (with `final_test_refusal=True`)

risk_score semantics (locked by Step 3R-3.3F design §8 / checkpoint §9):

    risk_score = P̂(prediction will be wrong | features)

A high score means the helper believes excluding this prediction is
reasonable. A high score combined with the prediction actually being
correct is a **false exclusion** — the helper's mistake. This semantic
must align with the adapter mapping
(``replay_validation_record_adapter``):

- ``risk_bucket ∈ {high, extreme}`` → adapter ``candidate_triggered=True``
- ``risk_bucket ∈ {abstain, low, medium}`` → adapter ``candidate_triggered=False``

The eight feature families (§5 of the design) are deterministic
**engineering defaults**. They are NOT optimized, NOT validated, and
NOT fitted to the v1 fail baseline. Bucket boundaries and the
trigger-support threshold below are also engineering defaults; they
are deliberately chosen NOT to mirror v1 boundaries. The helper does
NOT claim pass / fail; validation reports are produced separately
under Step 3R-4 protocol via ``services.regime_validation_helper``.

Public API:
    build_continuous_smoothing_candidate_v2(
        regime_labels,
        *,
        as_of_date=None,
        final_test_cutoff="2026-01-01",
    ) -> dict

Output schema: ``continuous_smoothing_candidate_v2.v1``
"""
from __future__ import annotations

import math
from typing import Any


SCHEMA_VERSION = "continuous_smoothing_candidate_v2.v1"
CANDIDATE_NAME = "continuous_smoothing_v2"
DEFAULT_FINAL_TEST_CUTOFF = "2026-01-01"

FEATURE_FAMILY_KEYS: tuple[str, ...] = (
    "trend_continuation_protection",
    "peer_confirmation_strength",
    "overextension_without_confirmation",
    "reversal_pressure",
    "regime_stability",
    "monthly_shock_context",
    "trigger_support",
    "calibration_context",
)

ALLOWED_RISK_BUCKETS: frozenset[str] = frozenset(
    {"abstain", "low", "medium", "high", "extreme"}
)

# Per-row inputs the helper reads from regime_labels.raw_features.
_RAW_FEATURE_KEYS: tuple[str, ...] = (
    "pos20",
    "avgo_minus_soxx_20d",
    "peer_5d_aligned_pct",
    "qqq_60d_slope_per_month",
    "qqq_60d_drawdown",
    "soxx_60d_slope_per_month",
    "monthly_max_abs_daily_return",
    "monthly_return_pct",
)

# Engineering default; not from v1 baseline.
_MIN_TRIGGER_SUPPORT_FOR_DECISION = 0.5

# Bucket boundaries on risk_score (sigmoid of the family-sum composite).
# Engineering defaults; deliberately chosen NOT to mirror v1 (0.35/0.60/0.80).
_BUCKET_LOW_MAX = 0.33
_BUCKET_MEDIUM_MAX = 0.55
_BUCKET_HIGH_MAX = 0.75


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


def _bucket_from_score(risk_score: float) -> str:
    if risk_score < _BUCKET_LOW_MAX:
        return "low"
    if risk_score < _BUCKET_MEDIUM_MAX:
        return "medium"
    if risk_score < _BUCKET_HIGH_MAX:
        return "high"
    return "extreme"


# ── feature families (deterministic engineering heuristics) ──────────────


def _f_trend_continuation_protection(
    *,
    qqq_slope: float | None,
    soxx_slope: float | None,
    qqq_drawdown: float | None,
    avgo_minus_soxx_20d: float | None,
) -> float:
    """Negative when AVGO is outperforming inside a confirmed bull regime.

    Negative values pull risk_score DOWN — protecting strong-trend
    continuation rows from being marked as "prediction will be wrong".
    """
    if (
        qqq_slope is None
        or soxx_slope is None
        or qqq_drawdown is None
        or avgo_minus_soxx_20d is None
    ):
        return 0.0
    if (
        qqq_slope > 0.012
        and soxx_slope > 0.012
        and qqq_drawdown < 0.05
        and avgo_minus_soxx_20d >= 0.0
    ):
        return -0.4
    if qqq_slope > 0.008 and avgo_minus_soxx_20d >= 0.0:
        return -0.2
    return 0.0


def _f_peer_confirmation_strength(
    *,
    peer_5d_aligned_pct: float | None,
) -> float:
    """Negative when peers strongly confirm direction."""
    if peer_5d_aligned_pct is None:
        return 0.0
    if peer_5d_aligned_pct >= 0.75:
        return -0.3
    if peer_5d_aligned_pct >= 0.50:
        return -0.15
    return 0.0


def _f_overextension_without_confirmation(
    *,
    pos20: float | None,
    avgo_minus_soxx_20d: float | None,
    peer_5d_aligned_pct: float | None,
    qqq_slope: float | None,
    qqq_drawdown: float | None,
) -> float:
    """Positive when prices are extended but neither peers nor trend confirm."""
    if pos20 is None or avgo_minus_soxx_20d is None:
        return 0.0
    high_pos = pos20 >= 0.65
    high_outperform = avgo_minus_soxx_20d >= 0.025
    low_peer = peer_5d_aligned_pct is not None and peer_5d_aligned_pct < 0.50
    weak_trend = (
        (qqq_slope is not None and qqq_slope < 0.008)
        or (qqq_drawdown is not None and qqq_drawdown > 0.05)
    )
    extension_count = int(high_pos) + int(high_outperform)
    confirmation_lacking = bool(low_peer or weak_trend)
    if extension_count >= 2 and confirmation_lacking:
        return 0.5
    if extension_count == 1 and confirmation_lacking:
        return 0.25
    return 0.0


def _f_reversal_pressure(
    *,
    qqq_slope: float | None,
    soxx_slope: float | None,
    qqq_drawdown: float | None,
    avgo_minus_soxx_20d: float | None,
) -> float:
    """Positive when market shows reversal-pressure features."""
    if qqq_drawdown is not None and qqq_drawdown >= 0.10:
        return 0.4
    if (
        qqq_slope is not None
        and soxx_slope is not None
        and qqq_slope < 0.0
        and soxx_slope < 0.0
    ):
        return 0.3
    if (
        qqq_drawdown is not None
        and qqq_drawdown >= 0.05
        and avgo_minus_soxx_20d is not None
        and avgo_minus_soxx_20d < 0.0
    ):
        return 0.2
    return 0.0


def _f_regime_stability(
    *,
    monthly_max_abs_daily_return: float | None,
) -> float:
    """Negative for stable regimes; positive for high-volatility regimes."""
    if monthly_max_abs_daily_return is None:
        return 0.0
    if monthly_max_abs_daily_return >= 0.07:
        return 0.2
    if monthly_max_abs_daily_return < 0.03:
        return -0.1
    return 0.0


def _f_monthly_shock_context(
    *,
    monthly_max_abs_daily_return: float | None,
    qqq_drawdown: float | None,
) -> float:
    """Positive when shock coincides with drawdown context."""
    if monthly_max_abs_daily_return is None:
        return 0.0
    shock = monthly_max_abs_daily_return >= 0.07
    reversal_combo = shock and (
        qqq_drawdown is not None and qqq_drawdown >= 0.05
    )
    if reversal_combo:
        return 0.3
    if shock:
        return 0.1
    return 0.0


def _trigger_support_score(
    feature_values: dict[str, float | None],
) -> float:
    """Fraction of required raw inputs that resolved to finite floats."""
    if not feature_values:
        return 0.0
    available = sum(1 for v in feature_values.values() if v is not None)
    return available / float(len(feature_values))


def _calibration_context_descriptor() -> dict[str, Any]:
    return {
        "method": "fixed_sigmoid_over_family_sum",
        "anchored_via": "engineering_default_per_family",
        "fitted_to_v1_baseline": False,
        "fitted_to_outcome_data": False,
        "trigger_support_threshold": _MIN_TRIGGER_SUPPORT_FOR_DECISION,
        "bucket_boundaries": {
            "low_max": _BUCKET_LOW_MAX,
            "medium_max": _BUCKET_MEDIUM_MAX,
            "high_max": _BUCKET_HIGH_MAX,
        },
    }


def _abstain_payload(
    *,
    as_of_date: str,
    data_cutoff_date: str,
    abstain_reason: str,
    warnings: list[str],
    final_test_refusal: bool,
    trigger_support: float | None,
    family_values: dict[str, Any] | None = None,
    raw_inputs: dict[str, float | None] | None = None,
) -> dict[str, Any]:
    if family_values is None:
        family_values = {
            k: None
            for k in FEATURE_FAMILY_KEYS
            if k != "calibration_context"
        }
        family_values["calibration_context"] = (
            _calibration_context_descriptor()
        )
    if raw_inputs is None:
        raw_inputs = {k: None for k in _RAW_FEATURE_KEYS}
    features_used = dict(family_values)
    features_used["raw_inputs"] = dict(raw_inputs)
    return {
        "schema_version": SCHEMA_VERSION,
        "as_of_date": as_of_date,
        "data_cutoff_date": data_cutoff_date,
        "candidate_name": CANDIDATE_NAME,
        "risk_score": None,
        "risk_bucket": "abstain",
        "abstain_reason": abstain_reason,
        "trigger_support": trigger_support,
        "features_used": features_used,
        "warnings": list(warnings),
        "final_test_refusal": bool(final_test_refusal),
    }


# ── public API ───────────────────────────────────────────────────────────


def build_continuous_smoothing_candidate_v2(
    regime_labels: dict[str, Any],
    *,
    as_of_date: str | None = None,
    final_test_cutoff: str = DEFAULT_FINAL_TEST_CUTOFF,
) -> dict[str, Any]:
    """Build a `continuous_smoothing_candidate_v2.v1` dict.

    Pure read-only — see module docstring for full constraints.

    risk_score = P̂(prediction will be wrong | features)
    """
    warnings: list[str] = []

    # Resolve as_of_date (explicit arg > regime_labels.as_of_date).
    if as_of_date is None and isinstance(regime_labels, dict):
        cand = regime_labels.get("as_of_date")
        if isinstance(cand, str):
            as_of_date = cand
    if not isinstance(as_of_date, str) or not as_of_date:
        warnings.append("missing_as_of_date")
        return _abstain_payload(
            as_of_date=as_of_date if isinstance(as_of_date, str) else "",
            data_cutoff_date="",
            abstain_reason="missing_as_of_date",
            warnings=warnings,
            final_test_refusal=False,
            trigger_support=None,
        )
    data_cutoff_date = as_of_date

    # Final-test cutoff (own as_of_date >= cutoff).
    if _is_within_final_test_range(as_of_date, final_test_cutoff):
        warnings.append("final_test_range_refusal")
        return _abstain_payload(
            as_of_date=as_of_date,
            data_cutoff_date=data_cutoff_date,
            abstain_reason="final_test_range_refusal",
            warnings=warnings,
            final_test_refusal=True,
            trigger_support=None,
        )

    # Propagate regime_labels.final_test_refusal=True.
    if (
        isinstance(regime_labels, dict)
        and regime_labels.get("final_test_refusal")
    ):
        warnings.append("regime_labels_final_test_refusal_propagated")
        return _abstain_payload(
            as_of_date=as_of_date,
            data_cutoff_date=data_cutoff_date,
            abstain_reason="final_test_range_refusal",
            warnings=warnings,
            final_test_refusal=True,
            trigger_support=None,
        )

    # Read raw_features.
    raw_features = (
        regime_labels.get("raw_features")
        if isinstance(regime_labels, dict)
        else None
    )
    if not isinstance(raw_features, dict):
        warnings.append("missing_raw_features")
        return _abstain_payload(
            as_of_date=as_of_date,
            data_cutoff_date=data_cutoff_date,
            abstain_reason="missing_raw_features",
            warnings=warnings,
            final_test_refusal=False,
            trigger_support=0.0,
        )

    feature_values: dict[str, float | None] = {}
    for key in _RAW_FEATURE_KEYS:
        feature_values[key] = _safe_float(raw_features.get(key))

    trigger_support = _trigger_support_score(feature_values)

    f_continuation = _f_trend_continuation_protection(
        qqq_slope=feature_values["qqq_60d_slope_per_month"],
        soxx_slope=feature_values["soxx_60d_slope_per_month"],
        qqq_drawdown=feature_values["qqq_60d_drawdown"],
        avgo_minus_soxx_20d=feature_values["avgo_minus_soxx_20d"],
    )
    f_peer = _f_peer_confirmation_strength(
        peer_5d_aligned_pct=feature_values["peer_5d_aligned_pct"],
    )
    f_overext = _f_overextension_without_confirmation(
        pos20=feature_values["pos20"],
        avgo_minus_soxx_20d=feature_values["avgo_minus_soxx_20d"],
        peer_5d_aligned_pct=feature_values["peer_5d_aligned_pct"],
        qqq_slope=feature_values["qqq_60d_slope_per_month"],
        qqq_drawdown=feature_values["qqq_60d_drawdown"],
    )
    f_reversal = _f_reversal_pressure(
        qqq_slope=feature_values["qqq_60d_slope_per_month"],
        soxx_slope=feature_values["soxx_60d_slope_per_month"],
        qqq_drawdown=feature_values["qqq_60d_drawdown"],
        avgo_minus_soxx_20d=feature_values["avgo_minus_soxx_20d"],
    )
    f_stability = _f_regime_stability(
        monthly_max_abs_daily_return=feature_values[
            "monthly_max_abs_daily_return"
        ],
    )
    f_shock = _f_monthly_shock_context(
        monthly_max_abs_daily_return=feature_values[
            "monthly_max_abs_daily_return"
        ],
        qqq_drawdown=feature_values["qqq_60d_drawdown"],
    )

    family_values: dict[str, Any] = {
        "trend_continuation_protection": f_continuation,
        "peer_confirmation_strength": f_peer,
        "overextension_without_confirmation": f_overext,
        "reversal_pressure": f_reversal,
        "regime_stability": f_stability,
        "monthly_shock_context": f_shock,
        "trigger_support": trigger_support,
        "calibration_context": _calibration_context_descriptor(),
    }

    if trigger_support < _MIN_TRIGGER_SUPPORT_FOR_DECISION:
        warnings.append("low_trigger_support")
        return _abstain_payload(
            as_of_date=as_of_date,
            data_cutoff_date=data_cutoff_date,
            abstain_reason="low_trigger_support",
            warnings=warnings,
            final_test_refusal=False,
            trigger_support=trigger_support,
            family_values=family_values,
            raw_inputs=feature_values,
        )

    raw_composite = (
        f_continuation
        + f_peer
        + f_overext
        + f_reversal
        + f_stability
        + f_shock
    )
    risk_score = _sigmoid(raw_composite)
    risk_bucket = _bucket_from_score(risk_score)

    features_used = dict(family_values)
    features_used["raw_inputs"] = dict(feature_values)

    return {
        "schema_version": SCHEMA_VERSION,
        "as_of_date": as_of_date,
        "data_cutoff_date": data_cutoff_date,
        "candidate_name": CANDIDATE_NAME,
        "risk_score": risk_score,
        "risk_bucket": risk_bucket,
        "abstain_reason": None,
        "trigger_support": trigger_support,
        "features_used": features_used,
        "warnings": list(warnings),
        "final_test_refusal": False,
    }
