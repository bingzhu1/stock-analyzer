"""V2 payload -> predict.py legacy compatibility adapter (Step 12E-X4-A).

Purpose
-------
Map the fields a V2 orchestrator payload already exposes onto the legacy
``PredictResult``-style compatibility surface that 9+ active importers
depend on (UI tabs, scripts, log_store, V1 orchestrator, review_agent,
contract_replay_writer). This is a STANDALONE pure function. It does
not invoke any active service entry point, does not call out to the V2
chain, does not invoke the aggregator builder, and does not invoke the
confidence-evaluator entry point. It performs no judgment, no
recomputation, and no I/O. It is a building block for later wiring
stages (X4-B / X4-C / X5).

Contract
--------
- Read-only: never mutates ``v2_payload`` or ``fallback_legacy_payload``.
- Pure mapping: every legacy field's value comes from a fixed priority
  chain (see 11E §7 X4 + the Step 12E-X4-A spec). The adapter never
  invents text, never recomputes confidence, never flips direction, and
  never merges exclusion or confidence into projection blocks.
- Deterministic: identical inputs produce identical output.
- Safe defaults: missing fields degrade to ``"unknown"`` /
  ``""`` / ``[]`` / ``{}`` with an explicit ``adapter.default.*``
  source path; the adapter never falls back to a heuristic.
- Source attribution: every entry in ``legacy_fields`` carries a
  parallel entry in ``source_mapping`` with
  ``{legacy_field, source_path, fallback_used, notes}``.

Output schema
-------------
::

    {
        "adapter_kind": "v2_to_predict_legacy_adapter",
        "adapter_version": "v2_to_predict_legacy_adapter.v1",
        "source": "v2_payload",
        "legacy_fields": {...},
        "source_mapping": {...},
        "warnings": [...],
        "non_mutation_confirmations": {
            "v2_payload_mutated": False,
            "fallback_legacy_payload_mutated": False,
        },
    }

Forbidden output
----------------
The result MUST NOT carry ``trading_action`` / ``buy`` / ``sell`` /
``hold`` / ``simulated_trade`` / ``no_trade`` / ``hard_exclusion`` /
``forced_exclusion`` / ``required_decision`` / ``production_promotion``
/ ``_PROTECTION_LAYER_CONNECTED`` / ``modified_*`` / ``corrected_*`` /
``final_report_mutation``. The adapter strips these as a defensive pass
even though no real call path can introduce them.

Design contracts: 07A / 07C / 07D / 11E §7 X4 / 11H.
"""

from __future__ import annotations

from typing import Any


ADAPTER_KIND = "v2_to_predict_legacy_adapter"
ADAPTER_VERSION = "v2_to_predict_legacy_adapter.v1"


_VALID_CONFIDENCE_LEVELS: tuple[str, ...] = ("low", "medium", "high", "unknown")

_FORBIDDEN_RESULT_FIELDS: frozenset[str] = frozenset({
    "hard_exclusion",
    "forced_exclusion",
    "required_decision",
    "trading_action",
    "buy",
    "sell",
    "hold",
    "simulated_trade",
    "no_trade",
    "production_promotion",
    "_PROTECTION_LAYER_CONNECTED",
    "modified_projection",
    "modified_exclusion",
    "modified_confidence",
    "corrected_confidence",
    "final_report_mutation",
})


# ---------------------------------------------------------------------------
# Internal helpers (pure, no side effects)
# ---------------------------------------------------------------------------


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _walk_path(payload: Any, parts: tuple[str, ...]) -> Any:
    """Walk a dotted path through ``payload``. Return ``None`` on any
    missing step (does not raise)."""
    cursor: Any = payload
    for part in parts:
        if not isinstance(cursor, dict):
            return None
        cursor = cursor.get(part)
        if cursor is None:
            return None
    return cursor


def _mapping_entry(
    *,
    legacy_field: str,
    source_path: str,
    fallback_used: bool,
    notes: str,
) -> dict[str, Any]:
    return {
        "legacy_field": legacy_field,
        "source_path": source_path,
        "fallback_used": fallback_used,
        "notes": notes,
    }


def _validate_confidence_level(value: Any) -> str | None:
    """Return the string if it is one of the four allowed levels;
    otherwise None. The adapter never coerces an unrelated value into a
    valid level — it surfaces ``"unknown"`` via the priority chain."""
    if not isinstance(value, str):
        return None
    text = value.strip().lower()
    if text in _VALID_CONFIDENCE_LEVELS:
        return text
    return None


def _resolve_direction(
    v2: dict[str, Any],
    fallback: dict[str, Any],
    warnings: list[str],
) -> tuple[str, str]:
    """Return ``(value, source_path)``. fallback_used is recorded by the
    caller against the source_path string."""
    candidates = (
        ("v2_payload.final_decision.final_direction", _walk_path(v2, ("final_decision", "final_direction"))),
        ("v2_payload.final_decision.direction", _walk_path(v2, ("final_decision", "direction"))),
        ("v2_payload.main_projection.predicted_top1.state",
         _walk_path(v2, ("main_projection", "predicted_top1", "state"))),
        ("v2_payload.main_projection.predicted_state",
         _walk_path(v2, ("main_projection", "predicted_state"))),
    )
    for source_path, value in candidates:
        if isinstance(value, str) and value.strip():
            if source_path.startswith("v2_payload.main_projection"):
                warnings.append(
                    "compat_final_bias sourced from main_projection (final_decision direction missing)."
                )
            return value, source_path

    for fb_key in ("final_bias", "direction"):
        fb_value = fallback.get(fb_key)
        if isinstance(fb_value, str) and fb_value.strip():
            warnings.append(
                f"compat_final_bias sourced from fallback_legacy_payload.{fb_key}."
            )
            return fb_value, f"fallback_legacy_payload.{fb_key}"

    warnings.append("compat_final_bias defaulted to 'unknown' (no source found).")
    return "unknown", "adapter.default.unknown"


def _resolve_confidence(
    v2: dict[str, Any],
    fallback: dict[str, Any],
    warnings: list[str],
) -> tuple[str, str]:
    """Priority: confidence_result.combined_confidence.level >
    final_decision.final_confidence (legacy) > fallback > unknown.

    Invalid levels at any priority degrade to the next priority.
    """
    primary = _walk_path(v2, ("confidence_result", "combined_confidence", "level"))
    valid = _validate_confidence_level(primary)
    if valid is not None:
        return valid, "v2_payload.confidence_result.combined_confidence.level"

    legacy_v2 = _walk_path(v2, ("final_decision", "final_confidence"))
    valid = _validate_confidence_level(legacy_v2)
    if valid is not None:
        warnings.append(
            "compat_final_confidence sourced from final_decision (legacy fallback)."
        )
        return valid, "v2_payload.final_decision.final_confidence"

    for fb_key in ("final_confidence", "confidence"):
        fb_valid = _validate_confidence_level(fallback.get(fb_key))
        if fb_valid is not None:
            warnings.append(
                f"compat_final_confidence sourced from fallback_legacy_payload.{fb_key}."
            )
            return fb_valid, f"fallback_legacy_payload.{fb_key}"

    warnings.append("compat_final_confidence defaulted to 'unknown'.")
    return "unknown", "adapter.default.unknown"


def _resolve_summary(
    v2: dict[str, Any],
    fallback: dict[str, Any],
    warnings: list[str],
) -> tuple[str, str]:
    """Priority: final_report.combined_user_summary > final_decision.summary
    > fallback (prediction_summary / summary) > "" (empty string).
    """
    primary = _walk_path(v2, ("final_report", "combined_user_summary"))
    if isinstance(primary, str) and primary.strip():
        return primary, "v2_payload.final_report.combined_user_summary"

    fd_summary = _walk_path(v2, ("final_decision", "summary"))
    if isinstance(fd_summary, str) and fd_summary.strip():
        warnings.append(
            "compat_prediction_summary sourced from final_decision.summary (final_report missing)."
        )
        return fd_summary, "v2_payload.final_decision.summary"

    for fb_key in ("prediction_summary", "summary"):
        fb_value = fallback.get(fb_key)
        if isinstance(fb_value, str) and fb_value.strip():
            warnings.append(
                f"compat_prediction_summary sourced from fallback_legacy_payload.{fb_key}."
            )
            return fb_value, f"fallback_legacy_payload.{fb_key}"

    warnings.append("compat_prediction_summary defaulted to empty string.")
    return "", "adapter.default.empty"


def _resolve_primary_projection(
    v2: dict[str, Any],
    fallback: dict[str, Any],
    warnings: list[str],
) -> tuple[dict[str, Any], str, bool]:
    """Priority: primary_analysis > main_projection > fallback > {}."""
    primary = v2.get("primary_analysis")
    if isinstance(primary, dict) and primary:
        return primary, "v2_payload.primary_analysis", False

    main = v2.get("main_projection")
    if isinstance(main, dict) and main:
        warnings.append(
            "compat_primary_projection sourced from main_projection (primary_analysis missing)."
        )
        return main, "v2_payload.main_projection", True

    fb_value = fallback.get("primary_projection")
    if isinstance(fb_value, dict) and fb_value:
        warnings.append(
            "compat_primary_projection sourced from fallback_legacy_payload.primary_projection."
        )
        return fb_value, "fallback_legacy_payload.primary_projection", True

    warnings.append("compat_primary_projection defaulted to empty dict.")
    return {}, "adapter.default.empty", True


def _resolve_peer_adjustment(
    v2: dict[str, Any],
    fallback: dict[str, Any],
    warnings: list[str],
) -> tuple[dict[str, Any], str, bool]:
    """Priority: peer_adjustment > fallback > {}."""
    peer = v2.get("peer_adjustment")
    if isinstance(peer, dict) and peer:
        return peer, "v2_payload.peer_adjustment", False

    fb_value = fallback.get("peer_adjustment")
    if isinstance(fb_value, dict) and fb_value:
        warnings.append(
            "compat_peer_adjustment sourced from fallback_legacy_payload.peer_adjustment."
        )
        return fb_value, "fallback_legacy_payload.peer_adjustment", True

    warnings.append("compat_peer_adjustment defaulted to empty dict.")
    return {}, "adapter.default.empty", True


def _resolve_final_projection(
    v2: dict[str, Any],
    fallback: dict[str, Any],
    warnings: list[str],
) -> tuple[dict[str, Any], str, bool]:
    """Priority: final_projection > final_decision (display block) > fallback > {}.

    When ``final_decision`` is used, the adapter passes it through verbatim
    — no new judgment, no merge with exclusion / confidence.
    """
    final_proj = v2.get("final_projection")
    if isinstance(final_proj, dict) and final_proj:
        return final_proj, "v2_payload.final_projection", False

    final_dec = v2.get("final_decision")
    if isinstance(final_dec, dict) and final_dec:
        warnings.append(
            "compat_final_projection used final_decision display block (final_projection missing)."
        )
        return final_dec, "v2_payload.final_decision", True

    fb_value = fallback.get("final_projection")
    if isinstance(fb_value, dict) and fb_value:
        warnings.append(
            "compat_final_projection sourced from fallback_legacy_payload.final_projection."
        )
        return fb_value, "fallback_legacy_payload.final_projection", True

    warnings.append("compat_final_projection defaulted to empty dict.")
    return {}, "adapter.default.empty", True


def _resolve_path_risk(
    v2: dict[str, Any],
    fallback: dict[str, Any],
    warnings: list[str],
) -> tuple[dict[str, Any], str, bool]:
    """Priority: v2.path_risk (dict) > final_decision.risk_level (wrapped)
    > fallback > {}."""
    direct = v2.get("path_risk")
    if isinstance(direct, dict) and direct:
        return direct, "v2_payload.path_risk", False

    risk_level = _walk_path(v2, ("final_decision", "risk_level"))
    if isinstance(risk_level, str) and risk_level.strip():
        warnings.append(
            "compat_path_risk wrapped from final_decision.risk_level."
        )
        return {"risk_level": risk_level}, "v2_payload.final_decision.risk_level", True

    fb_value = fallback.get("path_risk")
    if isinstance(fb_value, dict) and fb_value:
        warnings.append(
            "compat_path_risk sourced from fallback_legacy_payload.path_risk."
        )
        return fb_value, "fallback_legacy_payload.path_risk", True

    warnings.append("compat_path_risk defaulted to empty dict.")
    return {}, "adapter.default.empty", True


def _resolve_factor_list(
    v2: dict[str, Any],
    fallback: dict[str, Any],
    *,
    bucket_key: str,
    legacy_key: str,
    warnings: list[str],
    field_label: str,
) -> tuple[list[Any], str, bool]:
    """Priority: final_decision.decision_factors[<bucket_key>] >
    final_decision[<legacy_key>] > fallback[<legacy_key>] > []."""
    factors = _walk_path(v2, ("final_decision", "decision_factors"))
    if isinstance(factors, dict):
        bucket = factors.get(bucket_key)
        if isinstance(bucket, list):
            return list(bucket), f"v2_payload.final_decision.decision_factors.{bucket_key}", False

    legacy_list = _walk_path(v2, ("final_decision", legacy_key))
    if isinstance(legacy_list, list):
        warnings.append(
            f"compat_{legacy_key} sourced from final_decision.{legacy_key} (legacy list)."
        )
        return list(legacy_list), f"v2_payload.final_decision.{legacy_key}", True

    fb_value = fallback.get(legacy_key)
    if isinstance(fb_value, list):
        warnings.append(
            f"compat_{legacy_key} sourced from fallback_legacy_payload.{legacy_key}."
        )
        return list(fb_value), f"fallback_legacy_payload.{legacy_key}", True

    warnings.append(f"compat_{legacy_key} defaulted to empty list.")
    return [], "adapter.default.empty", True


def _resolve_path_field(
    fallback: dict[str, Any],
    *,
    field: str,
    warnings: list[str],
) -> tuple[str, str, bool]:
    """Scan/path display fields are not surfaced by the V2 chain.
    Priority: fallback > "unknown"."""
    fb_value = fallback.get(field)
    if isinstance(fb_value, str) and fb_value.strip():
        return fb_value, f"fallback_legacy_payload.{field}", True
    warnings.append(
        f"compat_{field} defaulted to 'unknown' (V2 does not surface this field)."
    )
    return "unknown", "adapter.default.unknown", True


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def adapt_v2_payload_to_predict_legacy(
    v2_payload: dict[str, Any] | Any,
    *,
    fallback_legacy_payload: dict[str, Any] | None | Any = None,
) -> dict[str, Any]:
    """Map a V2 payload to the predict.py legacy compatibility surface.

    See module docstring for the full contract. Inputs are never mutated;
    return value is a fresh dict.
    """
    warnings: list[str] = []

    if not isinstance(v2_payload, dict):
        warnings.append(
            "v2_payload is not a dict; falling back to defaults / fallback_legacy_payload."
        )
        v2: dict[str, Any] = {}
    else:
        v2 = v2_payload

    if fallback_legacy_payload is None:
        fallback: dict[str, Any] = {}
    elif not isinstance(fallback_legacy_payload, dict):
        warnings.append(
            "fallback_legacy_payload is not a dict; ignoring it."
        )
        fallback = {}
    else:
        fallback = fallback_legacy_payload

    # ── direction ──────────────────────────────────────────────────────────
    final_bias_value, final_bias_path = _resolve_direction(v2, fallback, warnings)
    final_bias_fb = not final_bias_path.startswith("v2_payload.final_decision.")

    # ── confidence ─────────────────────────────────────────────────────────
    confidence_value, confidence_path = _resolve_confidence(v2, fallback, warnings)
    confidence_fb = (
        confidence_path != "v2_payload.confidence_result.combined_confidence.level"
    )

    # ── summary ────────────────────────────────────────────────────────────
    summary_value, summary_path = _resolve_summary(v2, fallback, warnings)
    summary_fb = summary_path != "v2_payload.final_report.combined_user_summary"

    # ── projection / peer / final / path blocks ────────────────────────────
    primary_value, primary_path, primary_fb = _resolve_primary_projection(v2, fallback, warnings)
    peer_value, peer_path, peer_fb = _resolve_peer_adjustment(v2, fallback, warnings)
    final_proj_value, final_proj_path, final_proj_fb = _resolve_final_projection(v2, fallback, warnings)
    path_risk_value, path_risk_path, path_risk_fb = _resolve_path_risk(v2, fallback, warnings)

    supporting_value, supporting_path, supporting_fb = _resolve_factor_list(
        v2, fallback,
        bucket_key="supporting", legacy_key="supporting_factors",
        warnings=warnings, field_label="compat_supporting_factors",
    )
    conflicting_value, conflicting_path, conflicting_fb = _resolve_factor_list(
        v2, fallback,
        bucket_key="conflicting", legacy_key="conflicting_factors",
        warnings=warnings, field_label="compat_conflicting_factors",
    )

    # ── scan / path display fields (always fallback or unknown) ────────────
    scan_bias_value, scan_bias_path, scan_bias_fb = _resolve_path_field(
        fallback, field="scan_bias", warnings=warnings
    )
    open_tendency_value, open_tendency_path, open_tendency_fb = _resolve_path_field(
        fallback, field="open_tendency", warnings=warnings
    )
    close_tendency_value, close_tendency_path, close_tendency_fb = _resolve_path_field(
        fallback, field="close_tendency", warnings=warnings
    )
    pred_open_value, pred_open_path, pred_open_fb = _resolve_path_field(
        fallback, field="pred_open", warnings=warnings
    )
    pred_path_value, pred_path_path, pred_path_fb = _resolve_path_field(
        fallback, field="pred_path", warnings=warnings
    )
    pred_close_value, pred_close_path, pred_close_fb = _resolve_path_field(
        fallback, field="pred_close", warnings=warnings
    )

    legacy_fields: dict[str, Any] = {
        "final_bias": final_bias_value,
        "direction": final_bias_value,
        "final_confidence": confidence_value,
        "confidence": confidence_value,
        "prediction_summary": summary_value,
        "summary": summary_value,
        "primary_projection": primary_value,
        "peer_adjustment": peer_value,
        "final_projection": final_proj_value,
        "path_risk": path_risk_value,
        "supporting_factors": supporting_value,
        "conflicting_factors": conflicting_value,
        "scan_bias": scan_bias_value,
        "open_tendency": open_tendency_value,
        "close_tendency": close_tendency_value,
        "pred_open": pred_open_value,
        "pred_path": pred_path_value,
        "pred_close": pred_close_value,
    }

    source_mapping: dict[str, dict[str, Any]] = {
        "compat_final_bias": _mapping_entry(
            legacy_field="final_bias",
            source_path=final_bias_path,
            fallback_used=final_bias_fb,
            notes="final_decision.final_direction is the priority-1 source.",
        ),
        "compat_direction": _mapping_entry(
            legacy_field="direction",
            source_path=final_bias_path,
            fallback_used=final_bias_fb,
            notes="alias of compat_final_bias.",
        ),
        "compat_final_confidence": _mapping_entry(
            legacy_field="final_confidence",
            source_path=confidence_path,
            fallback_used=confidence_fb,
            notes="confidence_result.combined_confidence.level is the priority-1 source.",
        ),
        "compat_confidence": _mapping_entry(
            legacy_field="confidence",
            source_path=confidence_path,
            fallback_used=confidence_fb,
            notes="alias of compat_final_confidence.",
        ),
        "compat_prediction_summary": _mapping_entry(
            legacy_field="prediction_summary",
            source_path=summary_path,
            fallback_used=summary_fb,
            notes="final_report.combined_user_summary is the priority-1 source.",
        ),
        "compat_summary": _mapping_entry(
            legacy_field="summary",
            source_path=summary_path,
            fallback_used=summary_fb,
            notes="alias of compat_prediction_summary.",
        ),
        "compat_primary_projection": _mapping_entry(
            legacy_field="primary_projection",
            source_path=primary_path,
            fallback_used=primary_fb,
            notes="primary_analysis is the priority-1 source.",
        ),
        "compat_peer_adjustment": _mapping_entry(
            legacy_field="peer_adjustment",
            source_path=peer_path,
            fallback_used=peer_fb,
            notes="V2 peer_adjustment is the priority-1 source.",
        ),
        "compat_final_projection": _mapping_entry(
            legacy_field="final_projection",
            source_path=final_proj_path,
            fallback_used=final_proj_fb,
            notes="final_projection block is priority-1; final_decision is fallback (display only).",
        ),
        "compat_path_risk": _mapping_entry(
            legacy_field="path_risk",
            source_path=path_risk_path,
            fallback_used=path_risk_fb,
            notes="v2 path_risk dict is priority-1; final_decision.risk_level wrapped is fallback.",
        ),
        "compat_supporting_factors": _mapping_entry(
            legacy_field="supporting_factors",
            source_path=supporting_path,
            fallback_used=supporting_fb,
            notes="final_decision.decision_factors.supporting is priority-1.",
        ),
        "compat_conflicting_factors": _mapping_entry(
            legacy_field="conflicting_factors",
            source_path=conflicting_path,
            fallback_used=conflicting_fb,
            notes="final_decision.decision_factors.conflicting is priority-1.",
        ),
        "compat_scan_bias": _mapping_entry(
            legacy_field="scan_bias",
            source_path=scan_bias_path,
            fallback_used=scan_bias_fb,
            notes="V2 does not surface scan_bias; fallback or unknown.",
        ),
        "compat_open_tendency": _mapping_entry(
            legacy_field="open_tendency",
            source_path=open_tendency_path,
            fallback_used=open_tendency_fb,
            notes="V2 does not surface open_tendency; fallback or unknown.",
        ),
        "compat_close_tendency": _mapping_entry(
            legacy_field="close_tendency",
            source_path=close_tendency_path,
            fallback_used=close_tendency_fb,
            notes="V2 does not surface close_tendency; fallback or unknown.",
        ),
        "compat_pred_open": _mapping_entry(
            legacy_field="pred_open",
            source_path=pred_open_path,
            fallback_used=pred_open_fb,
            notes="V2 does not surface pred_open; fallback or unknown.",
        ),
        "compat_pred_path": _mapping_entry(
            legacy_field="pred_path",
            source_path=pred_path_path,
            fallback_used=pred_path_fb,
            notes="V2 does not surface pred_path; fallback or unknown.",
        ),
        "compat_pred_close": _mapping_entry(
            legacy_field="pred_close",
            source_path=pred_close_path,
            fallback_used=pred_close_fb,
            notes="V2 does not surface pred_close; fallback or unknown.",
        ),
    }

    # Defense in depth: strip any forbidden top-level / legacy_fields keys
    # that might somehow have been introduced upstream. The contract test
    # also pins this from outside.
    for forbidden in _FORBIDDEN_RESULT_FIELDS:
        legacy_fields.pop(forbidden, None)

    result: dict[str, Any] = {
        "adapter_kind": ADAPTER_KIND,
        "adapter_version": ADAPTER_VERSION,
        "source": "v2_payload",
        "legacy_fields": legacy_fields,
        "source_mapping": source_mapping,
        "warnings": warnings,
        "non_mutation_confirmations": {
            "v2_payload_mutated": False,
            "fallback_legacy_payload_mutated": False,
        },
    }
    for forbidden in _FORBIDDEN_RESULT_FIELDS:
        result.pop(forbidden, None)
    return result
