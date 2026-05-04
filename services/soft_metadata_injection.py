"""services/soft_metadata_injection.py — read-only sidecar enrichment.

Step 2G-6B.2 implementation of the post-run sidecar enrichment helper
spec'd by Step 2G-6B.1
([`tasks/step_2g6b1_soft_metadata_injection_path_design.md`]
commit `92441e0`). Translates a ``predict_result`` (with its
``contract_payload``) into an **enriched shallow copy** whose canonical
``exclusion_system.extras.soft_metadata`` is filled by calling
``simulate_soft_metadata``.

Design contract (Step 2G-6B.1 §10):
- pure function: never reads DB / CSV / network
- never imports ``services.prediction_store`` / ``yfinance`` /
  ``requests`` / trading APIs / v1 stub trio
- never calls ``build_soft_metadata_baseline`` (no DB read in this layer)
- shallow copy: input dict is NEVER mutated
- canonical write: output's
  ``["contract_payload"]["exclusion_system"]["extras"]["soft_metadata"]``
  is filled
- already-set wins by default: when the canonical slot already has a
  dict, return it unchanged unless ``force=True``
- 04 / 05 / 07 required fields are byte-stable across the call
- ``analysis_date`` is always passed to the simulator so the 2026
  final-test cutoff still applies
- the function never raises; any internal error is surfaced via the
  simulator's ``summary.warnings`` (or by returning the input untouched
  if the input itself is unusable)

Public API:
    enrich_predict_result_with_soft_metadata(
        predict_result, *,
        scan_result=None, research_result=None,
        baseline=None, regime_features=None,
        analysis_date=None, force=False,
        final_test_cutoff="2026-01-01",
    ) -> dict
"""
from __future__ import annotations

from typing import Any

from services.soft_metadata_simulator import (
    DEFAULT_FINAL_TEST_CUTOFF,
    simulate_soft_metadata,
)


# ── helpers ──────────────────────────────────────────────────────────────

def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _shallow_copy_dict(value: Any) -> dict[str, Any]:
    """Return a shallow copy when input is a dict, else fresh empty dict."""
    return dict(value) if isinstance(value, dict) else {}


def _extract_regime_features(
    predict_result: dict,
    scan_result: dict | None = None,
) -> dict | None:
    """Locate ``regime_features`` for the simulator (Step 2G-6B.1 §11.2).

    Search order — first non-empty dict wins:
      1. ``predict_result['regime_features']``
      2. ``predict_result['contract_payload']['exclusion_system']['extras']['regime_features']``
      3. ``scan_result['regime_features']``
      4. ``scan_result['extras']['regime_features']``

    Returns None when no level has a dict; caller passes that None to
    the simulator which will then emit ``signals=[]`` plus a
    ``missing_regime_features`` warning. (Explicit caller-supplied
    ``regime_features=`` argument takes precedence over this fallback —
    that lookup happens in the public entry point, not here.)
    """
    if isinstance(predict_result, dict):
        candidate = predict_result.get("regime_features")
        if isinstance(candidate, dict):
            return candidate
        cp = predict_result.get("contract_payload")
        if isinstance(cp, dict):
            es = cp.get("exclusion_system")
            if isinstance(es, dict):
                extras = es.get("extras")
                if isinstance(extras, dict):
                    candidate = extras.get("regime_features")
                    if isinstance(candidate, dict):
                        return candidate
    if isinstance(scan_result, dict):
        candidate = scan_result.get("regime_features")
        if isinstance(candidate, dict):
            return candidate
        extras = scan_result.get("extras")
        if isinstance(extras, dict):
            candidate = extras.get("regime_features")
            if isinstance(candidate, dict):
                return candidate
    return None


def _resolve_analysis_date(
    predict_result: dict,
    override: str | None,
) -> str | None:
    """Pick ``analysis_date`` for the cutoff check.

    Order: explicit override > predict_result['contract_payload']
    ['current_structure']['analysis_date'] > predict_result['analysis_date'] >
    None.
    """
    if isinstance(override, str) and override.strip():
        return override.strip()
    if isinstance(predict_result, dict):
        cp = predict_result.get("contract_payload")
        if isinstance(cp, dict):
            cs = cp.get("current_structure")
            if isinstance(cs, dict):
                cand = cs.get("analysis_date")
                if isinstance(cand, str) and cand.strip():
                    return cand.strip()
        cand = predict_result.get("analysis_date")
        if isinstance(cand, str) and cand.strip():
            return cand.strip()
    return None


def _extract_existing_soft_metadata(predict_result: dict) -> dict | None:
    """Read the canonical slot's existing soft_metadata, if any."""
    if not isinstance(predict_result, dict):
        return None
    cp = predict_result.get("contract_payload")
    if not isinstance(cp, dict):
        return None
    es = cp.get("exclusion_system")
    if not isinstance(es, dict):
        return None
    extras = es.get("extras")
    if not isinstance(extras, dict):
        return None
    candidate = extras.get("soft_metadata")
    return candidate if isinstance(candidate, dict) else None


# ── public API ──────────────────────────────────────────────────────────

def enrich_predict_result_with_soft_metadata(
    predict_result: dict,
    *,
    scan_result: dict | None = None,
    research_result: dict | None = None,  # noqa: ARG001 — accepted for API stability
    baseline: dict | None = None,
    regime_features: dict | None = None,
    analysis_date: str | None = None,
    force: bool = False,
    final_test_cutoff: str = DEFAULT_FINAL_TEST_CUTOFF,
) -> dict:
    """Sidecar enrichment for ``predict_result``.

    Returns a shallow copy whose
    ``["contract_payload"]["exclusion_system"]["extras"]["soft_metadata"]``
    is filled by ``simulate_soft_metadata``. Input dict is NOT mutated.

    When the canonical slot already has a dict, returns the input
    untouched unless ``force=True``.

    ``research_result`` is accepted for API stability (callers in Predict
    page have it readily available) but is NOT used by the helper —
    the simulator does not consume research output. Reserved for future
    use; documented to avoid breaking caller signatures later.
    """
    if not isinstance(predict_result, dict):
        # Defensive: bad input → return an empty dict so downstream
        # display hooks see ``signals=[]`` and hide the section.
        return {}

    existing = _extract_existing_soft_metadata(predict_result)
    if existing is not None and not force:
        # Already-set wins (Step 2G-6B.1 §10 / §10.1). Still return a
        # shallow copy so the caller can safely mutate the top level.
        return _shallow_copy_dict(predict_result)

    # Build a shallow-copied path down to extras so we can write the
    # soft_metadata key without touching the input dict.
    enriched = dict(predict_result)
    contract_payload = _shallow_copy_dict(enriched.get("contract_payload"))
    exclusion_system = _shallow_copy_dict(contract_payload.get("exclusion_system"))
    extras = _shallow_copy_dict(exclusion_system.get("extras"))

    # Resolve simulator inputs.
    if regime_features is None:
        regime_features = _extract_regime_features(predict_result, scan_result)
    resolved_date = _resolve_analysis_date(predict_result, analysis_date)

    # Carry the simulator's payload contract through: simulate_soft_metadata
    # reads ``payload['final_projection']`` / ``payload['confidence_system']``
    # / ``payload['peer_confirmation_adjustment']`` / etc. The contract
    # payload is the canonical source for those fields; if it's empty
    # (e.g. legacy predict_result without contract), we pass {} and the
    # simulator emits ``signals=[]`` with warnings.
    simulator_payload = contract_payload if contract_payload else {}

    soft_metadata = simulate_soft_metadata(
        simulator_payload,
        regime_features=regime_features,
        baseline=baseline,
        analysis_date=resolved_date,
        final_test_cutoff=final_test_cutoff,
    )

    # Write canonical slot in shallow-copied tree; do NOT touch input.
    extras["soft_metadata"] = soft_metadata
    exclusion_system["extras"] = extras
    contract_payload["exclusion_system"] = exclusion_system
    enriched["contract_payload"] = contract_payload

    return enriched
