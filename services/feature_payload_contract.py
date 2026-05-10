"""Pure-function validator for the ``feature_payload.v1`` contract
(Step 18B / PR-FEATURE-1).

Spec source of truth:

- `tasks/record_1_0_architecture_reset_canonical_principles.md` §8 (Branch 2)
- `tasks/record_17f_feature_layer_rebuild_plan.md` §6 / §13
- `tasks/record_18a_first_layer_based_implementation_batch_selection.md` §13

Status (per 17F §13 / 18A §10 / §13):

- This module is the **Feature Layer (Branch 2) output contract** introduced
  as PR-FEATURE-1, the first batch of layer-based implementation PRs after
  the 17D ~ 17M nine-branch plans landed.
- It is **not yet wired into any active path**. Producers (services such as
  ``projection_chain_contract.build_feature_payload_from_recent_window``,
  ``home_terminal_orchestrator``, ``projection_orchestrator_v2``) continue
  to emit their existing dict shapes; alignment to ``feature_payload.v1``
  is deferred to later batches.

Boundary contract (1.0 / 16A / 16C / 16F / 17F):

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
  ``services.review_orchestrator``, ``ui.*``, ``app``, any DB / sqlite,
  ``yfinance``.
- It **must not** create, infer, or modify any payload field. It also
  **must not** compute returns / position / volume_ratio / 15d window /
  peer_alignment — those belong to the producing modules in the Feature
  Layer (encoder / feature_builder / regime_features_builder /
  peer_alignment / projection_chain_contract).

Error message shapes (stable; tests rely on the prefix):

    invalid type: payload expected dict
    invalid value: schema_version expected 'feature_payload.v1'
    invalid value: metadata.price_basis expected one of ['adj', 'dual', 'raw']
    missing section: <section>
    section is not a dict: <section>
    section is not a list: ohlcv_window
    missing field: <section>.<field>
    warning: metadata.data_window_days expected 15
    forbidden field: <field> at <location>

The ``warning:`` prefix is reserved for non-blocking advisories that
callers can filter out (e.g. the legacy 20-day window during the 17F
15-day migration). Strict shape failures use the other prefixes.

Public API:

- ``FEATURE_PAYLOAD_SCHEMA_VERSION`` — the canonical schema version string.
- ``FEATURE_PAYLOAD_SECTIONS`` — the 10 top-level keys, in fixed order.
- ``RECOMMENDED_DATA_WINDOW_DAYS`` — the 1.0 / 07A standard window (15).
- ``ALLOWED_PRICE_BASIS`` — accepted values for ``metadata.price_basis``.
- ``FORBIDDEN_FIELDS`` — keys that are never allowed at top level
  (system result sections + trading / hard / forced / required tokens).
- ``validate_feature_payload(payload)`` — return ``[]`` on success,
  otherwise a list of human-readable error / warning strings.
"""

from __future__ import annotations

from typing import Any


FEATURE_PAYLOAD_SCHEMA_VERSION: str = "feature_payload.v1"

# 10 top-level keys (17F §6 / 18A §13.3). Order is fixed.
FEATURE_PAYLOAD_SECTIONS: tuple[str, ...] = (
    "schema_version",
    "metadata",
    "ohlcv_window",
    "returns",
    "position",
    "volume",
    "candle",
    "peer_alignment",
    "code_features",
    "data_quality",
)

# 1.0 §5 rule 9 / 07A §3.1 standard window. 17F §6 marks the current 20-day
# implementation as legacy / compatibility; this validator emits a "warning:"
# line (not a hard error) when data_window_days != 15 so 20-day callers can
# observe but not block.
RECOMMENDED_DATA_WINDOW_DAYS: int = 15

# 17E §8.2 raw / adj close double-track contract. 17F §13 PR-FEATURE-3
# (raw / adj price basis tagging) is the producer-side counterpart.
ALLOWED_PRICE_BASIS: frozenset[str] = frozenset({"raw", "adj", "dual"})

# Required keys inside ``metadata`` (18A §13).
_METADATA_REQUIRED: tuple[str, ...] = (
    "symbol",
    "analysis_date",
    "target_date",
    "data_window_days",
    "window_label",
    "price_basis",
)

# Required keys inside the four numeric feature sections (18A §13).
_RETURNS_REQUIRED: tuple[str, ...] = ("ret1", "ret3", "ret5", "ret10")
_POSITION_REQUIRED: tuple[str, ...] = ("pos15", "pos20", "pos30")
_VOLUME_REQUIRED: tuple[str, ...] = ("volume", "volume_ratio")
_CANDLE_REQUIRED: tuple[str, ...] = ("upper_shadow_ratio", "lower_shadow_ratio")
_DATA_QUALITY_REQUIRED: tuple[str, ...] = ("missing_fields", "source", "stale_flag")

# Sections that must be ``dict`` (everything except ``schema_version`` and
# ``ohlcv_window``; ``ohlcv_window`` is a list of bar rows, see §8 spec).
_DICT_SECTIONS: tuple[str, ...] = (
    "metadata",
    "returns",
    "position",
    "volume",
    "candle",
    "peer_alignment",
    "code_features",
    "data_quality",
)

# Forbidden field names at the top level. Anchored to:
#   - 1.0 §6 / §13 (Branch 2 may not output predictions / verdicts / trading)
#   - 17F §6 (Feature Layer禁止字段)
#   - 18A §13.4 (forbidden top-level set for feature_payload.v1)
#
# Match is exact-key only; ``feature_payload.v1`` carries features alone,
# never a verdict, a trading direction, or a forced-decision marker.
FORBIDDEN_FIELDS: frozenset[str] = frozenset({
    # System result sections — feature_payload only carries features
    "projection_result",
    "exclusion_result",
    "confidence_result",
    "final_report",
    "review_result",
    "evaluation_result",
    # Trading actions / execution
    "trading_action",
    "order",
    "position_action",
    "execution",
    # Trading directions
    "buy",
    "sell",
    "hold",
    # Forced / hard semantics
    "hard",
    "forced",
    "required",
})


def validate_feature_payload(payload: Any) -> list[str]:
    """Validate ``payload`` against ``feature_payload.v1``.

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

    # Rule 3: every FEATURE_PAYLOAD_SECTIONS key must be present.
    for section in FEATURE_PAYLOAD_SECTIONS:
        if section not in payload:
            errors.append(f"missing section: {section}")

    # Rule 2: schema_version must equal FEATURE_PAYLOAD_SCHEMA_VERSION.
    if "schema_version" in payload:
        if payload["schema_version"] != FEATURE_PAYLOAD_SCHEMA_VERSION:
            errors.append(
                f"invalid value: schema_version expected "
                f"{FEATURE_PAYLOAD_SCHEMA_VERSION!r} "
                f"(got {payload['schema_version']!r})"
            )

    # Rules 4 / 9–14: every dict-typed section must be a dict.
    for section in _DICT_SECTIONS:
        if section in payload and not isinstance(payload[section], dict):
            errors.append(f"section is not a dict: {section}")

    # Rule 8: ohlcv_window must be a list.
    if "ohlcv_window" in payload and not isinstance(payload["ohlcv_window"], list):
        errors.append("section is not a list: ohlcv_window")

    # Rules 5 + 6 + 7: metadata required keys + data_window_days advisory +
    # price_basis enum.
    metadata = payload.get("metadata")
    if isinstance(metadata, dict):
        for key in _METADATA_REQUIRED:
            if key not in metadata:
                errors.append(f"missing field: metadata.{key}")
        dwd = metadata.get("data_window_days")
        if dwd is not None and dwd != RECOMMENDED_DATA_WINDOW_DAYS:
            errors.append(
                f"warning: metadata.data_window_days expected "
                f"{RECOMMENDED_DATA_WINDOW_DAYS} (got {dwd!r})"
            )
        pb = metadata.get("price_basis")
        if pb is not None and pb not in ALLOWED_PRICE_BASIS:
            errors.append(
                f"invalid value: metadata.price_basis expected one of "
                f"{sorted(ALLOWED_PRICE_BASIS)!r} (got {pb!r})"
            )

    # Rule 9: returns required keys.
    _check_required_fields(payload, "returns", _RETURNS_REQUIRED, errors)
    # Rule 10: position required keys.
    _check_required_fields(payload, "position", _POSITION_REQUIRED, errors)
    # Rule 11: volume required keys.
    _check_required_fields(payload, "volume", _VOLUME_REQUIRED, errors)
    # Rule 12: candle required keys.
    _check_required_fields(payload, "candle", _CANDLE_REQUIRED, errors)
    # Rule 15: data_quality required keys.
    _check_required_fields(
        payload, "data_quality", _DATA_QUALITY_REQUIRED, errors
    )

    # Forbidden field names at the top level. The validator is read-only
    # (does not write back), so this is the only enforcement point for
    # 18A §13.4 forbidden tokens.
    _check_forbidden_fields(payload, location="top-level", errors=errors)

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
