"""Pure-function validator for the ``confidence_result.v1`` contract
(Step 18E / PR-CONF-1).

Spec source of truth:

- `tasks/record_1_0_architecture_reset_canonical_principles.md` §8 (Branch 5)
- `tasks/record_07c_confidence_system_contract.md` §3 / §9 / §11
- `tasks/record_17i_confidence_layer_rebuild_plan.md` §8 / §11 / §13
- `tasks/record_18a_first_layer_based_implementation_batch_selection.md` §13

Status (per 17I §13 / 18A §11):

- This module is the **Confidence Layer (Branch 5) output contract**
  introduced as PR-CONF-1, the fourth batch of layer-based implementation
  PRs after the 17D ~ 17M nine-branch plans landed.
- It is **not yet wired into any active path**. Producers (notably
  ``services.confidence_evaluator.build_confidence_result``) continue to
  emit ``confidence_system_result.v1`` (the prior internal label);
  alignment to ``confidence_result.v1`` is deferred to PR-CONF-2 /
  PR-CONF-3 / PR-CONF-4 and later batches.

Boundary contract (1.0 / 16A / 16C / 16F / 17I):

- This module is a **pure-function shape validator**. It:
  - Never mutates the input payload.
  - Never raises (returns errors as a plain ``list[str]``); even when the
    input is not a dict, it returns a single error string instead of
    raising ``TypeError``.
  - Never reads files / calls external APIs / imports business modules /
    invokes a language-model client / writes to any DB.
- It **must not** import any of: ``predict``, ``services.projection_orchestrator``,
  ``services.projection_orchestrator_v2``, ``services.projection_entrypoint``,
  ``services.projection_v2_adapter``, ``services.home_terminal_orchestrator``,
  ``services.confidence_evaluator``, ``services.main_projection_layer``,
  ``services.exclusion_layer``, ``services.peer_alignment``,
  ``services.final_decision``, ``services.consistency_layer``,
  ``services.review_orchestrator``, ``services.feature_payload_contract``,
  ``services.projection_result_contract``, ``services.exclusion_result_contract``,
  ``services.standard_projection_payload``, ``ui.*``, ``app``, any DB /
  sqlite, ``yfinance``.
- It **must not** create, infer, or modify any payload field. It also
  **must not** compute ``agreement_status`` / ``conflict_level`` /
  ``combined_confidence`` / calibration / call ``confidence_evaluator``.

Error message shapes (stable; tests rely on the prefix):

    invalid type: payload expected dict
    invalid type: <field> expected <type>
    invalid value: schema_version expected 'confidence_result.v1'
    invalid value: kind expected 'confidence'
    invalid value: symbol expected non-empty string
    invalid value: <block>.level expected one of [...]
    invalid value: <block>.score expected within [0, 1]
    invalid value: agreement_status expected one of [...]
    invalid value: conflict_level expected one of [...]
    invalid value: calibration_status expected one of [...]
    invalid value: non_mutation_confirmations.<key> expected True
    missing section: <section>
    missing field: <block>.<field>
    missing field: non_mutation_confirmations.<key>
    warning: <block>.score expected None when level='unknown'
    forbidden field: <field> at <location>

The ``warning:`` prefix is reserved for non-blocking advisories that
callers can filter out (e.g. a producer emits ``level="unknown"`` with a
residual numeric score from a partial calibration). Strict shape
failures use the other prefixes.

Public API:

- ``CONFIDENCE_RESULT_SCHEMA_VERSION`` — the canonical schema version string.
- ``CONFIDENCE_RESULT_KIND`` — the canonical ``kind`` value (``"confidence"``).
- ``CONFIDENCE_RESULT_SECTIONS`` — the 16 top-level keys, in fixed order.
- ``VALID_CONFIDENCE_LEVELS`` — accepted values for any confidence-block
  ``level`` field (``"high"`` / ``"medium"`` / ``"low"`` / ``"unknown"``).
- ``VALID_AGREEMENT_STATUS`` — accepted values for ``agreement_status``
  (``"aligned"`` / ``"partial_conflict"`` / ``"strong_conflict"`` /
  ``"unknown"``).
- ``VALID_CONFLICT_LEVELS`` — accepted values for ``conflict_level``
  (``"none"`` / ``"low"`` / ``"medium"`` / ``"high"`` / ``"unknown"``).
- ``VALID_CALIBRATION_STATUS`` — accepted values for ``calibration_status``
  (``"ready"`` / ``"not_ready"`` / ``"partial"`` / ``"unknown"``).
- ``FORBIDDEN_FIELDS`` — keys that are never allowed at top level
  (Branch 3 projection fields + Branch 4 exclusion fields + downstream
  system result sections + legacy bridge fields + trading / hard /
  forced / required tokens).
- ``validate_confidence_result(payload)`` — return ``[]`` on success,
  otherwise a list of human-readable error / warning strings.
"""

from __future__ import annotations

from typing import Any


CONFIDENCE_RESULT_SCHEMA_VERSION: str = "confidence_result.v1"

# 1.0 / 07C canonical ``kind`` for this contract.
CONFIDENCE_RESULT_KIND: str = "confidence"

# 16 top-level keys (18A §13 / 17I §8). Order is fixed.
CONFIDENCE_RESULT_SECTIONS: tuple[str, ...] = (
    "schema_version",
    "kind",
    "symbol",
    "ready",
    "projection_confidence",
    "exclusion_confidence",
    "agreement_status",
    "conflict_level",
    "combined_confidence",
    "confidence_factors",
    "calibration_status",
    "calibration_notes",
    "reasoning",
    "warnings",
    "raw_evidence_refs",
    "non_mutation_confirmations",
)

# Confidence-block ``level`` enum (17I §8 / 17I §11).
VALID_CONFIDENCE_LEVELS: tuple[str, ...] = ("high", "medium", "low", "unknown")

# 17I §11.1 — agreement_status enum.
VALID_AGREEMENT_STATUS: tuple[str, ...] = (
    "aligned",
    "partial_conflict",
    "strong_conflict",
    "unknown",
)

# 17I §11.2 — conflict_level enum (5 values; ``medium`` reserved per
# PR-CONF-4 standardization).
VALID_CONFLICT_LEVELS: tuple[str, ...] = (
    "none",
    "low",
    "medium",
    "high",
    "unknown",
)

# 17I §12 — calibration_status enum.
VALID_CALIBRATION_STATUS: tuple[str, ...] = (
    "ready",
    "not_ready",
    "partial",
    "unknown",
)

# 07C §5 / §11 / 17I §8 — Confidence Layer must declare it does not mutate
# upstream system results / feature_payload, and does not generate its
# own projection / exclusion verdicts.
_NON_MUTATION_CONFIRMATIONS_REQUIRED: tuple[str, ...] = (
    "confidence_did_not_mutate_projection_result",
    "confidence_did_not_mutate_exclusion_result",
    "confidence_did_not_mutate_feature_payload",
    "confidence_did_not_generate_projection",
    "confidence_did_not_generate_exclusion",
)

# Required fields inside each confidence block (projection_confidence /
# exclusion_confidence / combined_confidence). 17I §8.2 / §10.
_CONFIDENCE_BLOCK_REQUIRED: tuple[str, ...] = ("level", "score", "reasoning")

# The three confidence blocks (each must satisfy _CONFIDENCE_BLOCK_REQUIRED).
_CONFIDENCE_BLOCKS: tuple[str, ...] = (
    "projection_confidence",
    "exclusion_confidence",
    "combined_confidence",
)

# Forbidden field names at the top level. Anchored to:
#   - 1.0 §6 / §8 (Branch 5 may not output projection / exclusion verdicts /
#     final / trading / hard / forced / required)
#   - 07C §5 / §11 (Confidence must not write back to projection / exclusion)
#   - 17I §8.4 + 18A §13 (forbidden top-level set for confidence_result.v1)
FORBIDDEN_FIELDS: frozenset[str] = frozenset({
    # Branch 3 Projection fields — Confidence must not output them
    "most_likely_state",
    "ranked_states",
    "state_probabilities",
    "predicted_top1",
    "predicted_top2",
    "projection_result",
    # Branch 4 Exclusion fields — Confidence must not output them
    "most_unlikely_state",
    "ranked_unlikely_states",
    "excluded_states",
    "triggered_rules",
    "triggered_rule",
    "exclusion_result",
    "false_exclusion_risk",
    # Downstream system result sections
    "final_report",
    "review_result",
    "evaluation_result",
    # Legacy bridge / cross-system fields (07C §5 / 17I §8.4)
    "final_direction",
    "final_confidence",
    "final_bias",
    "final_projection",
    "primary_projection",
    "peer_adjustment",
    "path_risk",
    # Trading actions / execution
    "trading_action",
    "order",
    "position_action",
    "execution",
    "simulated_trade",
    # Trading directions
    "buy",
    "sell",
    "hold",
    # Forced / hard semantics
    "hard",
    "forced",
    "required",
})


def validate_confidence_result(payload: Any) -> list[str]:
    """Validate ``payload`` against ``confidence_result.v1``.

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

    # Rule 3: every CONFIDENCE_RESULT_SECTIONS key must be present.
    for section in CONFIDENCE_RESULT_SECTIONS:
        if section not in payload:
            errors.append(f"missing section: {section}")

    # Rule 2: schema_version must equal CONFIDENCE_RESULT_SCHEMA_VERSION.
    if "schema_version" in payload:
        if payload["schema_version"] != CONFIDENCE_RESULT_SCHEMA_VERSION:
            errors.append(
                f"invalid value: schema_version expected "
                f"{CONFIDENCE_RESULT_SCHEMA_VERSION!r} "
                f"(got {payload['schema_version']!r})"
            )

    # Rule 4: kind must equal "confidence".
    if "kind" in payload and payload["kind"] != CONFIDENCE_RESULT_KIND:
        errors.append(
            f"invalid value: kind expected {CONFIDENCE_RESULT_KIND!r} "
            f"(got {payload['kind']!r})"
        )

    # Rule 5: symbol must be a non-empty string.
    if "symbol" in payload:
        sym = payload["symbol"]
        if not isinstance(sym, str) or not sym:
            errors.append(
                f"invalid value: symbol expected non-empty string "
                f"(got {sym!r})"
            )

    # Rule 6: ready must be a bool.
    if "ready" in payload and not isinstance(payload["ready"], bool):
        errors.append(
            f"invalid type: ready expected bool "
            f"(got {type(payload['ready']).__name__})"
        )

    # Rules 7-14: validate each of the three confidence blocks.
    for block_name in _CONFIDENCE_BLOCKS:
        if block_name in payload:
            _validate_confidence_block(payload[block_name], block_name, errors)

    # Rule 15: agreement_status must be in VALID_AGREEMENT_STATUS.
    if "agreement_status" in payload:
        ag = payload["agreement_status"]
        if ag not in VALID_AGREEMENT_STATUS:
            errors.append(
                f"invalid value: agreement_status expected one of "
                f"{list(VALID_AGREEMENT_STATUS)!r} (got {ag!r})"
            )

    # Rule 16: conflict_level must be in VALID_CONFLICT_LEVELS.
    if "conflict_level" in payload:
        cl = payload["conflict_level"]
        if cl not in VALID_CONFLICT_LEVELS:
            errors.append(
                f"invalid value: conflict_level expected one of "
                f"{list(VALID_CONFLICT_LEVELS)!r} (got {cl!r})"
            )

    # Rule 17: confidence_factors must be list or dict.
    if "confidence_factors" in payload:
        cf = payload["confidence_factors"]
        if not isinstance(cf, (list, dict)):
            errors.append(
                f"invalid type: confidence_factors expected list or dict "
                f"(got {type(cf).__name__})"
            )

    # Rule 18: calibration_status must be in VALID_CALIBRATION_STATUS.
    if "calibration_status" in payload:
        cs = payload["calibration_status"]
        if cs not in VALID_CALIBRATION_STATUS:
            errors.append(
                f"invalid value: calibration_status expected one of "
                f"{list(VALID_CALIBRATION_STATUS)!r} (got {cs!r})"
            )

    # Rule 19: calibration_notes must be list or str.
    if "calibration_notes" in payload:
        cn = payload["calibration_notes"]
        if not isinstance(cn, (list, str)):
            errors.append(
                f"invalid type: calibration_notes expected list or str "
                f"(got {type(cn).__name__})"
            )

    # Rule 20: top-level reasoning must be str or list.
    if "reasoning" in payload:
        rn = payload["reasoning"]
        if not isinstance(rn, (str, list)):
            errors.append(
                f"invalid type: reasoning expected str or list "
                f"(got {type(rn).__name__})"
            )

    # Rule 21: warnings must be a list.
    if "warnings" in payload and not isinstance(payload["warnings"], list):
        errors.append(
            f"invalid type: warnings expected list "
            f"(got {type(payload['warnings']).__name__})"
        )

    # Rule 22: raw_evidence_refs must be a list.
    if "raw_evidence_refs" in payload and not isinstance(
        payload["raw_evidence_refs"], list
    ):
        errors.append(
            f"invalid type: raw_evidence_refs expected list "
            f"(got {type(payload['raw_evidence_refs']).__name__})"
        )

    # Rule 23 + 24: non_mutation_confirmations must be a dict containing
    # the five required keys, each set to True.
    if "non_mutation_confirmations" in payload:
        nmc = payload["non_mutation_confirmations"]
        if not isinstance(nmc, dict):
            errors.append(
                f"invalid type: non_mutation_confirmations expected dict "
                f"(got {type(nmc).__name__})"
            )
        else:
            for key in _NON_MUTATION_CONFIRMATIONS_REQUIRED:
                if key not in nmc:
                    errors.append(
                        f"missing field: non_mutation_confirmations.{key}"
                    )
                elif nmc[key] is not True:
                    errors.append(
                        f"invalid value: non_mutation_confirmations.{key} "
                        f"expected True (got {nmc[key]!r})"
                    )

    # Forbidden field names at the top level. The validator is read-only
    # (does not write back), so this is the only enforcement point for
    # 18A §13 forbidden tokens.
    _check_forbidden_fields(payload, location="top-level", errors=errors)

    return errors


def _validate_confidence_block(
    block: Any,
    block_name: str,
    errors: list[str],
) -> None:
    """Internal: validate one of the three confidence blocks
    (``projection_confidence`` / ``exclusion_confidence`` /
    ``combined_confidence``).

    Each block must be a dict containing ``level`` (enum), ``score``
    (int/float/None within [0, 1]), and ``reasoning`` (str/list)."""
    if not isinstance(block, dict):
        errors.append(
            f"invalid type: {block_name} expected dict "
            f"(got {type(block).__name__})"
        )
        return

    # Required keys.
    for field in _CONFIDENCE_BLOCK_REQUIRED:
        if field not in block:
            errors.append(f"missing field: {block_name}.{field}")

    # level enum.
    if "level" in block:
        level = block["level"]
        if level not in VALID_CONFIDENCE_LEVELS:
            errors.append(
                f"invalid value: {block_name}.level expected one of "
                f"{list(VALID_CONFIDENCE_LEVELS)!r} (got {level!r})"
            )

    # score: int/float/None, within [0, 1].
    if "score" in block:
        score = block["score"]
        if score is None:
            pass
        elif isinstance(score, bool) or not isinstance(score, (int, float)):
            errors.append(
                f"invalid type: {block_name}.score expected int/float/None "
                f"(got {type(score).__name__})"
            )
        elif score < 0 or score > 1:
            errors.append(
                f"invalid value: {block_name}.score expected within [0, 1] "
                f"(got {score!r})"
            )

    # Cross-field advisory: when level == "unknown", score should be None.
    # Non-blocking warning (callers may filter "warning:" lines).
    if block.get("level") == "unknown" and block.get("score") is not None:
        errors.append(
            f"warning: {block_name}.score expected None when level='unknown' "
            f"(got {block['score']!r})"
        )

    # reasoning: str or list.
    if "reasoning" in block:
        reasoning = block["reasoning"]
        if not isinstance(reasoning, (str, list)):
            errors.append(
                f"invalid type: {block_name}.reasoning expected str or list "
                f"(got {type(reasoning).__name__})"
            )


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
