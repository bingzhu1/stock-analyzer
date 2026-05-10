"""Warning card schema, builder, and validator (Step 18W / PR-FINAL-4).

Spec source of truth:

- `tasks/record_1_0_architecture_reset_canonical_principles.md` §8 (Branch 6)
- `tasks/record_17j_final_report_layer_rebuild_plan.md` §9.4 / §13 PR-FINAL-4
- `tasks/record_18s_third_layer_based_implementation_batch_selection.md`
  §4 / §6 / §10

Status (per 17J §13 PR-FINAL-4 / 18S §6):

- This module is a **standalone helper** that defines the canonical
  ``warning_card.v1`` shape and exposes pure-function builder /
  validator helpers. It is the Final Report Layer's standard container
  for risk advisories that today live in scattered shapes:

  - ``briefing_caution_*`` markers attached by ``predict.run_predict``
    (Step 18R / PR-REVIEW-2);
  - ``reliability_warnings`` lists from
    ``services.confidence_evaluator.build_confidence_result``;
  - contradiction / tail-risk cards from
    ``services.big_up_contradiction_card`` /
    ``services.big_down_tail_warning``;
  - flat ``warnings`` strings from ``services.final_decision``.

- It is **not yet wired into any active path**. Producers continue to
  emit their existing shapes; alignment of those producers to
  ``warning_card.v1`` is deferred to a future PR with explicit user
  confirmation.

Boundary contract (1.0 / 16A / 16C / 16F / 17J / 18S):

- Pure functions only. The module:
  - Never mutates inputs (deep-copies mutable ``evidence`` /
    ``metadata`` so the returned card is fully isolated).
  - Never raises (returns errors as ``list[str]``).
  - Never reads files / calls external APIs / imports business modules /
    invokes a language-model client / writes to any DB / runs replay /
    runs calibration / places trades.
- It **must not** import any of: ``services.final_decision``,
  ``services.confidence_evaluator``, ``services.review_orchestrator``,
  ``services.main_projection_layer``, ``services.exclusion_layer``,
  ``services.consistency_layer``, ``services.peer_alignment``,
  ``services.projection_orchestrator``,
  ``services.projection_orchestrator_v2``,
  ``services.projection_entrypoint``,
  ``services.projection_v2_adapter``,
  ``services.home_terminal_orchestrator``,
  ``services.predict_legacy_adapter``,
  ``services.predict_legacy_v2_bridge``,
  ``services.predict_summary``, ``services.ai_summary``,
  ``services.standard_projection_payload``,
  ``services.feature_payload_contract``,
  ``services.projection_result_contract``,
  ``services.exclusion_result_contract``,
  ``services.confidence_result_contract``,
  ``services.final_report_result_contract``,
  ``services.architecture_orchestrator``, ``predict``, ``app``,
  ``ui.*``, any DB / sqlite, ``yfinance``, ``pandas``, ``streamlit``.
- It **must not** compute any trading direction / order / execution. A
  warning card may not carry ``buy`` / ``sell`` / ``hold`` / ``hard`` /
  ``forced`` / ``required`` / ``trading_action`` / ``order`` /
  ``position_action`` / ``execution`` / ``broker_order`` /
  ``live_trade`` / ``active_rule_promotion`` / ``promote_rule`` keys at
  the card top level. ``recommended_action`` must remain descriptive
  only (e.g. ``"display_warning_only"`` /
  ``"review_before_trusting"``); trading or forcing tokens inside
  ``recommended_action`` are rejected as well.

Public API:

- ``WARNING_CARD_SCHEMA_VERSION`` — the canonical schema version
  (``"warning_card.v1"``).
- ``VALID_WARNING_TYPES`` — accepted values for ``type``.
- ``VALID_WARNING_SEVERITIES`` — accepted values for ``severity``.
- ``WARNING_CARD_REQUIRED_FIELDS`` — the canonical 10 required keys, in
  fixed order.
- ``FORBIDDEN_WARNING_CARD_FIELDS`` — keys never allowed at top level.
- ``build_warning_card(...)`` — return a fresh standard dict (no
  validation; deep-copies ``evidence`` / ``metadata``).
- ``validate_warning_card(card)`` — return ``list[str]`` errors; never
  raises; never mutates.
- ``validate_warning_cards(cards)`` — accept a list and validate each
  card; per-card errors are prefixed with ``cards[<i>]:``; never
  raises; never mutates.

Error message shapes (stable; tests rely on the prefix):

    invalid type: card expected dict
    invalid type: cards expected list
    invalid value: schema_version expected 'warning_card.v1'
    invalid value: type expected one of <list>
    invalid value: severity expected one of <list>
    invalid value: <field> expected non-empty string
    invalid type: evidence expected dict, list, or None
    invalid type: metadata expected dict or None
    invalid type: blocking expected bool
    invalid value: recommended_action expected None or non-empty string
    missing field: <field>
    forbidden field: <field> at top-level
    forbidden token in recommended_action: <token>
    cards[<i>]: <inner-error>
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


WARNING_CARD_SCHEMA_VERSION: str = "warning_card.v1"

VALID_WARNING_TYPES: tuple[str, ...] = (
    "contradiction",
    "tail_risk",
    "briefing_caution",
    "calibration",
    "data_quality",
    "system_boundary",
    "unknown",
)

VALID_WARNING_SEVERITIES: tuple[str, ...] = (
    "info",
    "low",
    "medium",
    "high",
    "critical",
    "unknown",
)

WARNING_CARD_REQUIRED_FIELDS: tuple[str, ...] = (
    "schema_version",
    "type",
    "severity",
    "title",
    "message",
    "source_layer",
    "evidence",
    "recommended_action",
    "blocking",
    "metadata",
)

# 1.0 §6 / 17J §11.4 — a warning card may never carry trading direction
# / order / execution semantics or forced-effect tokens. The validator
# rejects these keys at the card top level, mirroring the
# ``final_report_result.v1`` top-level forbidden-field guard.
FORBIDDEN_WARNING_CARD_FIELDS: tuple[str, ...] = (
    "buy",
    "sell",
    "hold",
    "hard",
    "forced",
    "required",
    "trading_action",
    "order",
    "position_action",
    "execution",
    "broker_order",
    "live_trade",
    "active_rule_promotion",
    "promote_rule",
)

# Substrings that must never appear in ``recommended_action``. The
# match is case-insensitive on whole tokens (delimited by characters
# other than letters / digits) so descriptive strings such as
# ``"display_warning_only"`` and ``"review_before_trusting"`` remain
# valid while ``"buy now"`` / ``"must hold"`` /
# ``"forced_review_required"`` are rejected.
_FORBIDDEN_RECOMMENDED_ACTION_TOKENS: tuple[str, ...] = (
    "buy",
    "sell",
    "hold",
    "hard",
    "forced",
    "required",
    "trading_action",
    "order",
    "position_action",
    "execution",
    "broker_order",
    "live_trade",
    "active_rule_promotion",
    "promote_rule",
)


def build_warning_card(
    *,
    warning_type: str,
    severity: str,
    title: str,
    message: str,
    source_layer: str,
    evidence: dict[str, Any] | list[Any] | None = None,
    recommended_action: str | None = None,
    blocking: bool = False,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a fresh ``warning_card.v1`` dict.

    The card is **not validated** here; callers should run
    ``validate_warning_card`` after construction (or accept that an
    out-of-spec card surfaces as errors when the validator is invoked
    downstream). ``evidence`` and ``metadata`` are deep-copied so the
    returned card cannot share mutable state with the caller.
    """
    return {
        "schema_version": WARNING_CARD_SCHEMA_VERSION,
        "type": warning_type,
        "severity": severity,
        "title": title,
        "message": message,
        "source_layer": source_layer,
        "evidence": deepcopy(evidence),
        "recommended_action": recommended_action,
        "blocking": blocking,
        "metadata": deepcopy(metadata),
    }


def validate_warning_card(card: Any) -> list[str]:
    """Validate ``card`` against ``warning_card.v1``.

    Returns ``[]`` on success; otherwise a list of human-readable error
    strings. Never raises. Never mutates ``card``.
    """
    if not isinstance(card, dict):
        return [
            f"invalid type: card expected dict (got {type(card).__name__})"
        ]

    errors: list[str] = []

    for required in WARNING_CARD_REQUIRED_FIELDS:
        if required not in card:
            errors.append(f"missing field: {required}")

    if (
        "schema_version" in card
        and card["schema_version"] != WARNING_CARD_SCHEMA_VERSION
    ):
        errors.append(
            f"invalid value: schema_version expected "
            f"{WARNING_CARD_SCHEMA_VERSION!r} (got {card['schema_version']!r})"
        )

    if "type" in card and card["type"] not in VALID_WARNING_TYPES:
        errors.append(
            f"invalid value: type expected one of "
            f"{list(VALID_WARNING_TYPES)!r} (got {card['type']!r})"
        )

    if "severity" in card and card["severity"] not in VALID_WARNING_SEVERITIES:
        errors.append(
            f"invalid value: severity expected one of "
            f"{list(VALID_WARNING_SEVERITIES)!r} (got {card['severity']!r})"
        )

    for str_field in ("title", "message", "source_layer"):
        if str_field in card:
            value = card[str_field]
            if not isinstance(value, str) or not value:
                errors.append(
                    f"invalid value: {str_field} expected non-empty string "
                    f"(got {value!r})"
                )

    if "evidence" in card:
        evidence = card["evidence"]
        if evidence is not None and not isinstance(evidence, (dict, list)):
            errors.append(
                f"invalid type: evidence expected dict, list, or None "
                f"(got {type(evidence).__name__})"
            )

    if "metadata" in card:
        metadata = card["metadata"]
        if metadata is not None and not isinstance(metadata, dict):
            errors.append(
                f"invalid type: metadata expected dict or None "
                f"(got {type(metadata).__name__})"
            )

    if "blocking" in card and not isinstance(card["blocking"], bool):
        errors.append(
            f"invalid type: blocking expected bool "
            f"(got {type(card['blocking']).__name__})"
        )

    if "recommended_action" in card:
        ra = card["recommended_action"]
        if ra is not None:
            if not isinstance(ra, str) or not ra:
                errors.append(
                    f"invalid value: recommended_action expected None or "
                    f"non-empty descriptive string (got {ra!r})"
                )
            else:
                lowered = ra.lower()
                for token in _FORBIDDEN_RECOMMENDED_ACTION_TOKENS:
                    if _contains_token(lowered, token):
                        errors.append(
                            f"forbidden token in recommended_action: {token}"
                        )

    for key in card:
        if key in FORBIDDEN_WARNING_CARD_FIELDS:
            errors.append(f"forbidden field: {key} at top-level")

    return errors


def validate_warning_cards(cards: Any) -> list[str]:
    """Validate a list of cards.

    Returns ``[]`` on success; otherwise a list of human-readable error
    strings. Per-card errors are prefixed with ``cards[<i>]:`` so
    callers can locate the offending card without scanning the input
    again. Never raises. Never mutates ``cards``.
    """
    if not isinstance(cards, list):
        return [
            f"invalid type: cards expected list (got {type(cards).__name__})"
        ]
    errors: list[str] = []
    for index, card in enumerate(cards):
        for err in validate_warning_card(card):
            errors.append(f"cards[{index}]: {err}")
    return errors


def _contains_token(text: str, token: str) -> bool:
    """Return True when ``token`` appears in ``text`` delimited by
    non-alphanumeric characters on at least one side.

    Used for the ``recommended_action`` token guard. Underscores are
    treated as token boundaries so that compound identifiers like
    ``"forced_review_required"`` still flag the inner ``"forced"`` /
    ``"required"`` tokens, while ``"buyer beware"`` does not flag
    ``"buy"``.
    """
    if not token:
        return False
    n = len(text)
    m = len(token)
    if m == 0 or m > n:
        return False
    start = 0
    while start <= n - m:
        idx = text.find(token, start)
        if idx == -1:
            return False
        before = text[idx - 1] if idx > 0 else ""
        after = text[idx + m] if idx + m < n else ""
        if not before.isalnum() and not after.isalnum():
            return True
        start = idx + 1
    return False
