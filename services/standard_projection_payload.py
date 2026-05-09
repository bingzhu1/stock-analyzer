"""Pure-function validator for the ``standard_projection_payload.v1``
contract (Step 17A / PR-B).

Spec source of truth:

- `tasks/record_1_0_architecture_reset_canonical_principles.md` §8 / §10
- `tasks/record_16c_target_dataflow_contract_decision.md` §5 / §6
- `tasks/record_16i_core_chain_rebuild_execution_plan.md` §6

Status (per 16I §6 / §16):

- This module is the **new architecture foundation** introduced as PR-B.
- It is **not yet wired into any active path**. PR-F (16I) will wire the
  future ``services.architecture_orchestrator`` to assemble payloads and
  self-check via ``validate_standard_projection_payload``.

Boundary contract (1.0 / 16A / 16C / 16F):

- This module is a **pure-function shape validator**. It:
  - Never mutates the input payload.
  - Never raises (returns errors as a plain ``list[str]``); even when the
    input is not a dict, it returns a single error string instead of
    raising ``TypeError``.
  - Never reads files / calls external APIs / imports business modules /
    invokes a language-model client / writes to any DB.
- It **must not** import any of: ``predict``, ``services.projection_orchestrator``,
  ``services.projection_orchestrator_v2``, ``services.home_terminal_orchestrator``,
  ``services.main_projection_layer``, ``services.exclusion_layer``,
  ``services.confidence_evaluator``, ``services.final_decision``,
  ``ui.*``, any DB / sqlite, ``yfinance``.
- It **must not** create, infer, or modify any payload field. It also
  **must not** write to ``compatibility_metadata`` (that section belongs
  to the future ``architecture_orchestrator`` + Bridge layer).

Error message shapes (stable; tests rely on the prefix):

    invalid type: payload expected dict
    invalid value: schema_version expected 'standard_projection_payload.v1'
    missing section: <section>
    section is not a dict: <section>
    missing field: <section>.<field>
    invalid type: <section>.<field> expected <type>
    warning: metadata.data_window_days expected 15
    forbidden field: <field> at <location>

The ``warning:`` prefix is reserved for non-blocking advisories that
callers can filter out (e.g. the legacy 20-day window during the 16C
15-day migration). Strict shape failures use the other prefixes.

Public API:

- ``SCHEMA_VERSION`` — the canonical schema version string.
- ``STANDARD_PAYLOAD_SECTIONS`` — the 10 top-level keys, in fixed order.
- ``RECOMMENDED_DATA_WINDOW_DAYS`` — the 1.0 / 07A standard window (15).
- ``FORBIDDEN_FIELDS`` — keys that are never allowed at top level or
  inside ``final_report`` (trading / hard / forced / required / order /
  position / execution / etc.).
- ``validate_standard_projection_payload(payload)`` — return ``[]`` on
  success, otherwise a list of human-readable error / warning strings.
"""

from __future__ import annotations

from typing import Any


SCHEMA_VERSION: str = "standard_projection_payload.v1"

# 10 top-level keys (16C §5.2 / 16I §6.2). Order is fixed.
STANDARD_PAYLOAD_SECTIONS: tuple[str, ...] = (
    "schema_version",
    "metadata",
    "feature_payload",
    "projection_result",
    "exclusion_result",
    "confidence_result",
    "final_report",
    "review_stub",
    "evaluation_stub",
    "compatibility_metadata",
)

# 1.0 / 07A §3.1 standard window. 16C §3.3 marked the current 20-day
# implementation as legacy / compatibility; PR-B emits a "warning:" line
# (not a hard error) when data_window_days != 15 so 20-day callers can
# observe but not block.
RECOMMENDED_DATA_WINDOW_DAYS: int = 15

# Required keys inside ``metadata`` (16C §5.3 + 16I §6.2). Note: some
# values (like ``symbol``) carry semantic meaning enforced elsewhere;
# the contract validator only checks presence + container type.
_METADATA_REQUIRED: tuple[str, ...] = (
    "symbol",
    "analysis_date",
    "target_date",
    "data_window_days",
    "non_mutation_confirmations",
)

# Required keys inside each three-system / final_report section (16C §6).
_PROJECTION_RESULT_REQUIRED: tuple[str, ...] = (
    "most_likely_state",
    "ranked_states",
    "state_probabilities",
    "evidence",
    "raw_score",
)
_EXCLUSION_RESULT_REQUIRED: tuple[str, ...] = (
    "most_unlikely_state",
    "excluded_states",
    "false_exclusion_risk",
    "evidence",
    "triggered_rules",
)
_CONFIDENCE_RESULT_REQUIRED: tuple[str, ...] = (
    "projection_confidence",
    "exclusion_confidence",
    "agreement_status",
    "conflict_level",
    "combined_confidence",
    "calibration_notes",
)
_FINAL_REPORT_REQUIRED: tuple[str, ...] = (
    "summary",
    "key_points",
    "risks",
    "evidence_summary",
)

# Sections required to be ``dict`` (everything except ``schema_version``).
_DICT_SECTIONS: tuple[str, ...] = tuple(
    s for s in STANDARD_PAYLOAD_SECTIONS if s != "schema_version"
)

# Forbidden field names (16I §6.2 — anchored to 1.0 §6 / §13 / 07D §5 /
# 07C §5 ``_FORBIDDEN_FIELDS``). Checked at top-level and inside
# ``final_report``. Match is exact-key only; a key whose name **contains**
# a forbidden token (e.g. ``hard_exclusion``) is also caught via the
# explicit prefix list below.
FORBIDDEN_FIELDS: frozenset[str] = frozenset({
    # Trading actions
    "buy",
    "sell",
    "hold",
    "trading_action",
    "simulated_trade",
    "no_trade",
    # Order / position / execution
    "order",
    "position",
    "execution",
    # Hard / forced / required (bare keys per user spec)
    "hard",
    "forced",
    "required",
    # Common prefixed variants
    "hard_exclusion",
    "forced_exclusion",
    "required_decision",
    # Promotion / protection (永久 OFFLINE per 1.0 §13)
    "production_promotion",
    "_PROTECTION_LAYER_CONNECTED",
})


def validate_standard_projection_payload(payload: Any) -> list[str]:
    """Validate ``payload`` against ``standard_projection_payload.v1``.

    Returns ``[]`` on success; otherwise a list of human-readable error
    or warning strings. Never raises. Never mutates ``payload``.

    See module docstring for the full set of error / warning prefixes.
    """
    errors: list[str] = []

    # Rule 1: payload must be a dict.
    if not isinstance(payload, dict):
        return [
            f"invalid type: payload expected dict (got {type(payload).__name__})"
        ]

    # Rule 3: every STANDARD_PAYLOAD_SECTIONS key must be present.
    for section in STANDARD_PAYLOAD_SECTIONS:
        if section not in payload:
            errors.append(f"missing section: {section}")

    # Rule 2: schema_version must equal SCHEMA_VERSION (only meaningful
    # if the section is present).
    if "schema_version" in payload:
        if payload["schema_version"] != SCHEMA_VERSION:
            errors.append(
                f"invalid value: schema_version expected "
                f"{SCHEMA_VERSION!r} (got {payload['schema_version']!r})"
            )

    # Rules 4 / 7–14: every non-schema_version section must be a dict.
    for section in _DICT_SECTIONS:
        if section in payload and not isinstance(payload[section], dict):
            errors.append(f"section is not a dict: {section}")

    # Rule 5 + 6: metadata required keys + data_window_days advisory.
    metadata = payload.get("metadata")
    if isinstance(metadata, dict):
        for key in _METADATA_REQUIRED:
            if key not in metadata:
                errors.append(f"missing field: metadata.{key}")
        # Rule 6: data_window_days SHOULD equal RECOMMENDED_DATA_WINDOW_DAYS;
        # not a hard error — emit a "warning:" line that callers may filter.
        dwd = metadata.get("data_window_days")
        if dwd is not None and dwd != RECOMMENDED_DATA_WINDOW_DAYS:
            errors.append(
                f"warning: metadata.data_window_days expected "
                f"{RECOMMENDED_DATA_WINDOW_DAYS} (got {dwd!r})"
            )

    # Rule 15: projection_result required keys.
    _check_required_fields(
        payload, "projection_result", _PROJECTION_RESULT_REQUIRED, errors
    )
    # Rule 16: exclusion_result required keys.
    _check_required_fields(
        payload, "exclusion_result", _EXCLUSION_RESULT_REQUIRED, errors
    )
    # Rule 17: confidence_result required keys.
    _check_required_fields(
        payload, "confidence_result", _CONFIDENCE_RESULT_REQUIRED, errors
    )
    # Rule 18: final_report required keys.
    _check_required_fields(
        payload, "final_report", _FINAL_REPORT_REQUIRED, errors
    )

    # Rules 19 / 20 are enforced by NOT writing back to payload (read-only
    # API). Below we only check forbidden field names appearing at top
    # level or inside final_report.
    _check_forbidden_fields(payload, location="top-level", errors=errors)
    final_report = payload.get("final_report")
    if isinstance(final_report, dict):
        _check_forbidden_fields(
            final_report, location="final_report", errors=errors
        )

    return errors


def _check_required_fields(
    payload: dict[str, Any],
    section_name: str,
    required: tuple[str, ...],
    errors: list[str],
) -> None:
    """Internal: append ``missing field: <section>.<field>`` for each
    missing required key in the named section. No-op if the section is
    not a dict (already reported by the section type check)."""
    section = payload.get(section_name)
    if not isinstance(section, dict):
        return
    for field in required:
        if field not in section:
            errors.append(f"missing field: {section_name}.{field}")


def _check_forbidden_fields(
    container: dict[str, Any],
    *,
    location: str,
    errors: list[str],
) -> None:
    """Internal: append ``forbidden field: <field> at <location>`` for
    every key in ``container`` that is in ``FORBIDDEN_FIELDS``."""
    for key in container:
        if key in FORBIDDEN_FIELDS:
            errors.append(f"forbidden field: {key} at {location}")
