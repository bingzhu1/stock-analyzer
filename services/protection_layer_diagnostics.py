"""services/protection_layer_diagnostics.py — read-only sidecar.

Step 2G-8A.1 implementation per Step 2G-8A design (commit ``b4c1919``)
+ checkpoint (``8c56696``). Pure-function helper that builds the
``protection_layer_diagnostics.v1`` sidecar, surfacing two baseline
guards (`holdout_stability_guard` + `net_benefit_guard`) so Predict /
Review / dashboard can show "保护层诊断详情" alongside the
existing ``anti_false_exclusion_display.v1`` finding list.

Design contract (Step 2G-8A §5 / §10 / §11):
- pure function: never reads DB / CSV / network; never imports
  ``services.prediction_store`` / simulator / yfinance / requests /
  trading APIs / v1 stub trio
- never mutates input
- always returns a dict; never raises
- ``diagnostic_connected`` is **always** ``True`` (v1 spec strong
  invariant) — but ``hard_gate_connected`` /
  ``required_field_connected`` /
  ``protection_layer_connected_for_gate`` are **always** ``False``
  (v1 spec strong invariants — sidecar 接入 ≠ Step 2G-7C dashboard
  Gate 5 自动 pass)
- ``summary.hard_upgrade_blocked`` / ``summary.display_only`` are
  **always** ``True`` in v1 (sidecar 仍是 display-only)
- never produces forbidden copy (Step 2G-8A §9 — same 19-token list
  as ``ui/anti_false_exclusion_display.py``)

Public API:
    build_protection_layer_diagnostics(
        anti_false_exclusion_summary=None, *, soft_metadata=None,
    ) -> dict
    build_protection_layer_diagnostics_from_dashboard(summary) -> dict
"""
from __future__ import annotations

from typing import Any


SCHEMA_VERSION = "protection_layer_diagnostics.v1"

# Guard names (Step 2G-8A §3 / §4).
GUARD_HOLDOUT_STABILITY = "holdout_stability_guard"
GUARD_NET_BENEFIT = "net_benefit_guard"

# Mirror Step 2G-3 / 2G-4.5 / 2G-7 / 2G-7A / 2G-7C net-benefit gate.
_NB_GATE = 0.05

# Required-next-step label (sidecar-level only — Step 2G-8B / 2G-8C
# range; not an ``04 required`` field).
_REQUIRED_NEXT_STEP = "narrower_candidate_research"


# ── helpers ──────────────────────────────────────────────────────────────

def _is_real_number(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    return isinstance(value, (int, float))


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _find_signal(signals: list[Any], name: str) -> dict | None:
    for s in signals:
        if isinstance(s, dict) and s.get("name") == name:
            return s
    return None


def _r4_metrics_from_dashboard(summary: dict) -> dict[str, Any]:
    """Extract R4 holdout_status / net_benefit from a dashboard summary
    (the dict returned by ``summarize_anti_false_exclusion_dashboard``).

    Accepts both shapes the design allows:
    - full dashboard: ``summary["soft_metadata_summary"]["r4_overextension"]``
    - bare candidate map: ``summary["r4_overextension"]``
    Returns ``{}`` when neither is present.
    """
    sms = summary.get("soft_metadata_summary")
    candidate = None
    if isinstance(sms, dict):
        candidate = sms.get("r4_overextension")
    if not isinstance(candidate, dict):
        candidate = summary.get("r4_overextension")
    if not isinstance(candidate, dict):
        return {}
    return {
        "holdout_status": candidate.get("holdout_status"),
        "net_benefit": candidate.get("net_benefit"),
    }


def _r4_metrics_from_soft_metadata(soft_metadata: dict) -> dict[str, Any]:
    """Extract R4 holdout_status / net_benefit from a ``soft_metadata.v1``
    payload (signals list with ``historical_metrics_in_sample``).
    Returns ``{}`` when no R4 signal is present.
    """
    signals = _safe_list(soft_metadata.get("signals"))
    r4 = _find_signal(signals, "r4_overextension")
    if r4 is None:
        return {}
    metrics = _safe_dict(r4.get("historical_metrics_in_sample"))
    return {
        "holdout_status": r4.get("holdout_status"),
        "net_benefit": metrics.get("net_benefit"),
    }


def _collect_warnings(*sources: Any) -> list[str]:
    """Pass through ``final_test_range_refusal`` (and any other string
    warning) from the inputs. Deduplicates while preserving order.
    """
    seen: set[str] = set()
    out: list[str] = []
    for src in sources:
        for w in _safe_list(src):
            if isinstance(w, str) and w and w not in seen:
                seen.add(w)
                out.append(w)
    return out


# ── per-guard builders ──────────────────────────────────────────────────

def _maybe_holdout_stability_guard(holdout_status: Any) -> dict | None:
    if holdout_status != "FAIL":
        return None
    return {
        "name": GUARD_HOLDOUT_STABILITY,
        "status": "blocking",
        "reason": "holdout_status_FAIL",
        "evidence": {"holdout_status": "FAIL"},
        "message": "跨窗口验证未通过，当前只允许复盘提示。",
    }


def _maybe_net_benefit_guard(net_benefit: Any) -> dict | None:
    if not _is_real_number(net_benefit):
        return None
    if float(net_benefit) >= _NB_GATE:
        return None
    return {
        "name": GUARD_NET_BENEFIT,
        "status": "blocking",
        "reason": "net_benefit_below_gate",
        "evidence": {
            "net_benefit": float(net_benefit),
            "threshold": _NB_GATE,
        },
        "message": "净收益不足，当前只允许复盘提示。",
    }


# ── public API: build ───────────────────────────────────────────────────

def build_protection_layer_diagnostics(
    anti_false_exclusion_summary: dict | None = None,
    *,
    soft_metadata: dict | None = None,
) -> dict[str, Any]:
    """Build the ``protection_layer_diagnostics.v1`` sidecar.

    Pure function. Always returns a dict; never raises. The four
    connection flags are spec-locked (see module docstring), and so are
    ``summary.hard_upgrade_blocked`` / ``summary.display_only`` (always
    ``True`` in v1).

    Inputs (optional, additive):
    - ``anti_false_exclusion_summary``: a dict shaped like the output
      of ``services.anti_false_exclusion_dashboard
      .summarize_anti_false_exclusion_dashboard`` — read-only, for R4
      holdout_status / net_benefit
    - ``soft_metadata``: a ``soft_metadata.v1`` payload (signals list)
      — read-only fallback path when the dashboard summary is absent

    When both are provided, the dashboard summary wins for any field it
    surfaces; the soft_metadata fallback fills the rest.
    """
    afx = anti_false_exclusion_summary if isinstance(
        anti_false_exclusion_summary, dict
    ) else {}
    sm = soft_metadata if isinstance(soft_metadata, dict) else {}

    dash_metrics = _r4_metrics_from_dashboard(afx) if afx else {}
    sm_metrics = _r4_metrics_from_soft_metadata(sm) if sm else {}

    holdout_status = dash_metrics.get("holdout_status")
    if holdout_status is None:
        holdout_status = sm_metrics.get("holdout_status")

    net_benefit = dash_metrics.get("net_benefit")
    if not _is_real_number(net_benefit):
        net_benefit = sm_metrics.get("net_benefit")

    warnings = _collect_warnings(
        afx.get("warnings") if afx else None,
        _safe_dict(sm.get("summary")).get("warnings") if sm else None,
    )

    guards: list[dict] = []
    g1 = _maybe_holdout_stability_guard(holdout_status)
    if g1 is not None:
        guards.append(g1)
    g2 = _maybe_net_benefit_guard(net_benefit)
    if g2 is not None:
        guards.append(g2)

    have_any_metric = (
        holdout_status is not None or _is_real_number(net_benefit)
    )
    if not have_any_metric and "missing_metrics" not in warnings:
        warnings.append("missing_metrics")

    return {
        "schema_version": SCHEMA_VERSION,
        # ── 4 connection flags (v1 spec strong invariants) ────────────
        "diagnostic_connected": True,
        "hard_gate_connected": False,
        "required_field_connected": False,
        "protection_layer_connected_for_gate": False,
        # ── guards ────────────────────────────────────────────────────
        "guards": guards,
        # ── summary ───────────────────────────────────────────────────
        "summary": {
            "hard_upgrade_blocked": True,
            "display_only": True,
            "blocking_guard_count": sum(
                1 for g in guards if g.get("status") == "blocking"
            ),
            "required_next_step": _REQUIRED_NEXT_STEP,
        },
        "warnings": warnings,
    }


def build_protection_layer_diagnostics_from_dashboard(
    summary: dict,
) -> dict[str, Any]:
    """Convenience wrapper: build the sidecar directly from a
    ``summarize_anti_false_exclusion_dashboard`` output. Pure function;
    never re-queries DB or re-runs the dashboard service.
    """
    return build_protection_layer_diagnostics(
        anti_false_exclusion_summary=summary,
    )
