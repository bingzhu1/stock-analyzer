"""Pure-function validator for the ``exclusion_result.v1`` contract
(Step 18D / PR-EXCL-1).

Spec source of truth:

- `tasks/record_1_0_architecture_reset_canonical_principles.md` §8 (Branch 4)
- `tasks/record_07b_exclusion_system_contract.md` §3 / §9
- `tasks/record_17h_exclusion_layer_rebuild_plan.md` §8 / §10 / §14
- `tasks/record_18a_first_layer_based_implementation_batch_selection.md` §13

Status (per 17H §14 / 18A §11):

- This module is the **Exclusion Layer (Branch 4) output contract**
  introduced as PR-EXCL-1, the third batch of layer-based implementation
  PRs after the 17D ~ 17M nine-branch plans landed.
- It is **not yet wired into any active path**. Producers (notably
  ``services.exclusion_layer.run_exclusion_layer``) continue to emit
  their existing dict shapes (``triggered_rule`` single, no
  ``most_unlikely_state`` / ``ranked_unlikely_states``); alignment to
  ``exclusion_result.v1`` is deferred to PR-EXCL-2 / PR-EXCL-3 / later
  batches.

Boundary contract (1.0 / 16A / 16C / 16F / 17H):

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
  ``services.exclusion_layer``, ``services.peer_alignment``,
  ``services.main_projection_layer``, ``services.confidence_evaluator``,
  ``services.final_decision``, ``services.review_orchestrator``,
  ``services.feature_payload_contract``, ``services.projection_result_contract``,
  ``services.standard_projection_payload``, ``ui.*``, ``app``, any DB /
  sqlite, ``yfinance``.
- It **must not** create, infer, or modify any payload field. It also
  **must not** compute ``false_exclusion_risk`` / ``excluded_states`` /
  ``triggered_rules`` / call ``exclusion_layer`` / call ``peer_alignment``.

Error message shapes (stable; tests rely on the prefix):

    invalid type: payload expected dict
    invalid type: <field> expected <type>
    invalid value: schema_version expected 'exclusion_result.v1'
    invalid value: kind expected 'exclusion'
    invalid value: symbol expected non-empty string
    invalid value: most_unlikely_state expected one of [...] or None
    invalid value: most_unlikely_state may be None only when ready=False
    invalid value: ranked_unlikely_states[i] expected one of [...]
    invalid value: state_impossibility_scores key '<k>' not in [...]
    invalid value: state_impossibility_scores['<k>'] expected within [0, 1]
    invalid value: excluded_states[i] expected one of [...]
    invalid value: triggered_rules[i] expected non-empty string
    invalid value: false_exclusion_risk expected one of [...]
    invalid value: non_mutation_confirmations.<key> expected True
    missing section: <section>
    missing field: non_mutation_confirmations.<key>
    forbidden field: <field> at <location>

Note: Unlike ``projection_result.v1.state_probabilities``, the
``state_impossibility_scores`` field does **not** carry a
``warning: <field> sum expected near 1.0`` advisory. 17H §8.3 / §10
explicitly states that impossibility scores are **not** a probability
distribution and must not be normalized to 1.

Public API:

- ``EXCLUSION_RESULT_SCHEMA_VERSION`` — the canonical schema version string.
- ``EXCLUSION_RESULT_KIND`` — the canonical ``kind`` value (``"exclusion"``).
- ``EXCLUSION_RESULT_SECTIONS`` — the 16 top-level keys, in fixed order.
- ``VALID_STATES`` — the five-state vocabulary
  (``"大涨"`` / ``"小涨"`` / ``"震荡"`` / ``"小跌"`` / ``"大跌"``).
- ``VALID_FALSE_EXCLUSION_RISK`` — accepted values for the risk-level
  enum (``"low"`` / ``"medium"`` / ``"high"`` / ``"unknown"``).
- ``FORBIDDEN_FIELDS`` — keys that are never allowed at top level
  (Branch 3 projection fields + downstream system result sections +
  legacy bridge fields + legacy ``triggered_rule`` single alias +
  trading / hard / forced / required tokens).
- ``validate_exclusion_result(payload)`` — return ``[]`` on success,
  otherwise a list of human-readable error strings.
"""

from __future__ import annotations

from typing import Any


EXCLUSION_RESULT_SCHEMA_VERSION: str = "exclusion_result.v1"

# 1.0 / 07B canonical ``kind`` for this contract.
EXCLUSION_RESULT_KIND: str = "exclusion"

# 16 top-level keys (18A §13 / 17H §8). Order is fixed.
EXCLUSION_RESULT_SECTIONS: tuple[str, ...] = (
    "schema_version",
    "kind",
    "symbol",
    "ready",
    "most_unlikely_state",
    "ranked_unlikely_states",
    "state_impossibility_scores",
    "excluded_states",
    "triggered_rules",
    "false_exclusion_risk",
    "evidence",
    "rationale",
    "warnings",
    "feature_snapshot_ref",
    "peer_alignment_summary",
    "non_mutation_confirmations",
)

# Five-state vocabulary (1.0 §8 / 07B §9 / 17H §8). Fixed order matches the
# project-wide convention (大涨 → 大跌, descending bullishness).
VALID_STATES: tuple[str, ...] = ("大涨", "小涨", "震荡", "小跌", "大跌")

# 17H §10 — false_exclusion_risk enum. ``"unknown"`` is reserved for
# producers that cannot derive a confident self-risk label (e.g. when
# ``ready=False`` or feature data is degraded).
VALID_FALSE_EXCLUSION_RISK: tuple[str, ...] = ("low", "medium", "high", "unknown")

# 07B §3.2 / 17H §8 — Exclusion Layer must declare it does not read
# downstream system outputs nor future outcomes. The producer-side
# (PR-EXCL-2) sets all four to True; the validator only checks shape +
# value.
_NON_MUTATION_CONFIRMATIONS_REQUIRED: tuple[str, ...] = (
    "exclusion_did_not_read_projection",
    "exclusion_did_not_read_confidence",
    "exclusion_did_not_read_final_report",
    "exclusion_did_not_read_future_outcome",
)

# Forbidden field names at the top level. Anchored to:
#   - 1.0 §6 / §8 (Branch 4 may not output projection / confidence / final /
#     trading / hard / forced / required)
#   - 07B §3.2 (Exclusion must not output ``most_likely_state`` etc.)
#   - 17H §8.4 + 18A §13 (forbidden top-level set for exclusion_result.v1)
#
# 18A explicitly recommends forbidding the legacy ``triggered_rule`` single
# alias at top level: producers may keep it inside their internal dict for
# legacy callers (under PR-EXCL-3 migration), but ``exclusion_result.v1``
# carries only the standard ``triggered_rules`` list form.
FORBIDDEN_FIELDS: frozenset[str] = frozenset({
    # Branch 3 Projection fields — Exclusion must not output them
    "most_likely_state",
    "ranked_states",
    "state_probabilities",
    "predicted_top1",
    "predicted_top2",
    # Downstream system result sections
    "projection_result",
    "confidence_result",
    "final_report",
    "review_result",
    "evaluation_result",
    # Legacy bridge / cross-system fields (07B §3.2 / 17H §8.4)
    "final_direction",
    "final_confidence",
    "combined_confidence",
    "agreement_status",
    "conflict_level",
    "final_bias",
    "final_projection",
    "primary_projection",
    # Legacy interim alias — 18A spec recommends forbidding at top level
    "triggered_rule",
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


def validate_exclusion_result(payload: Any) -> list[str]:
    """Validate ``payload`` against ``exclusion_result.v1``.

    Returns ``[]`` on success; otherwise a list of human-readable error
    strings. Never raises. Never mutates ``payload``.

    See module docstring for the full set of error prefixes.
    """
    errors: list[str] = []

    # Rule 1: payload must be a dict.
    if not isinstance(payload, dict):
        return [
            f"invalid type: payload expected dict (got {type(payload).__name__})"
        ]

    # Rule 3: every EXCLUSION_RESULT_SECTIONS key must be present.
    for section in EXCLUSION_RESULT_SECTIONS:
        if section not in payload:
            errors.append(f"missing section: {section}")

    # Rule 2: schema_version must equal EXCLUSION_RESULT_SCHEMA_VERSION.
    if "schema_version" in payload:
        if payload["schema_version"] != EXCLUSION_RESULT_SCHEMA_VERSION:
            errors.append(
                f"invalid value: schema_version expected "
                f"{EXCLUSION_RESULT_SCHEMA_VERSION!r} "
                f"(got {payload['schema_version']!r})"
            )

    # Rule 4: kind must equal "exclusion".
    if "kind" in payload and payload["kind"] != EXCLUSION_RESULT_KIND:
        errors.append(
            f"invalid value: kind expected {EXCLUSION_RESULT_KIND!r} "
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

    # Rule 7: most_unlikely_state must be in VALID_STATES, or None when
    # ready=False (also covers exclusion_layer ``action="allow"`` case).
    if "most_unlikely_state" in payload:
        mus = payload["most_unlikely_state"]
        ready = payload.get("ready")
        if mus is None:
            if ready is not False:
                errors.append(
                    "invalid value: most_unlikely_state may be None only when ready=False"
                )
        elif mus not in VALID_STATES:
            errors.append(
                f"invalid value: most_unlikely_state expected one of "
                f"{list(VALID_STATES)!r} or None (got {mus!r})"
            )

    # Rule 8 + 9: ranked_unlikely_states must be a list whose elements are
    # in VALID_STATES (when non-empty).
    if "ranked_unlikely_states" in payload:
        rus = payload["ranked_unlikely_states"]
        if not isinstance(rus, list):
            errors.append(
                f"invalid type: ranked_unlikely_states expected list "
                f"(got {type(rus).__name__})"
            )
        else:
            for index, element in enumerate(rus):
                if element not in VALID_STATES:
                    errors.append(
                        f"invalid value: ranked_unlikely_states[{index}] "
                        f"expected one of {list(VALID_STATES)!r} "
                        f"(got {element!r})"
                    )

    # Rules 10 + 11 + 12: state_impossibility_scores checks. Note: 17H §8.3
    # / §10 explicitly states impossibility scores are NOT a probability
    # distribution; we do NOT emit a sum-near-1 warning here.
    if "state_impossibility_scores" in payload:
        sis = payload["state_impossibility_scores"]
        if not isinstance(sis, dict):
            errors.append(
                f"invalid type: state_impossibility_scores expected dict "
                f"(got {type(sis).__name__})"
            )
        else:
            # Rule 11: keys must be valid states.
            for key in sis:
                if key not in VALID_STATES:
                    errors.append(
                        f"invalid value: state_impossibility_scores key "
                        f"{key!r} not in {list(VALID_STATES)!r}"
                    )
            # Rule 12: values must be int/float in [0, 1].
            for key, value in sis.items():
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    errors.append(
                        f"invalid type: state_impossibility_scores[{key!r}] "
                        f"expected int/float (got {type(value).__name__})"
                    )
                elif value < 0 or value > 1:
                    errors.append(
                        f"invalid value: state_impossibility_scores[{key!r}] "
                        f"expected within [0, 1] (got {value!r})"
                    )

    # Rules 13 + 14: excluded_states must be a list of valid states.
    if "excluded_states" in payload:
        es = payload["excluded_states"]
        if not isinstance(es, list):
            errors.append(
                f"invalid type: excluded_states expected list "
                f"(got {type(es).__name__})"
            )
        else:
            for index, element in enumerate(es):
                if element not in VALID_STATES:
                    errors.append(
                        f"invalid value: excluded_states[{index}] expected "
                        f"one of {list(VALID_STATES)!r} (got {element!r})"
                    )

    # Rules 15 + 16: triggered_rules must be a list of non-empty strings.
    if "triggered_rules" in payload:
        tr = payload["triggered_rules"]
        if not isinstance(tr, list):
            errors.append(
                f"invalid type: triggered_rules expected list "
                f"(got {type(tr).__name__})"
            )
        else:
            for index, element in enumerate(tr):
                if not isinstance(element, str) or not element:
                    errors.append(
                        f"invalid value: triggered_rules[{index}] expected "
                        f"non-empty string (got {element!r})"
                    )

    # Rule 17: false_exclusion_risk must be in VALID_FALSE_EXCLUSION_RISK.
    if "false_exclusion_risk" in payload:
        fer = payload["false_exclusion_risk"]
        if fer not in VALID_FALSE_EXCLUSION_RISK:
            errors.append(
                f"invalid value: false_exclusion_risk expected one of "
                f"{list(VALID_FALSE_EXCLUSION_RISK)!r} (got {fer!r})"
            )

    # Rule 18: evidence must be dict or list.
    if "evidence" in payload:
        evidence = payload["evidence"]
        if not isinstance(evidence, (dict, list)):
            errors.append(
                f"invalid type: evidence expected dict or list "
                f"(got {type(evidence).__name__})"
            )

    # Rule 19: rationale must be str or list.
    if "rationale" in payload:
        rationale = payload["rationale"]
        if not isinstance(rationale, (str, list)):
            errors.append(
                f"invalid type: rationale expected str or list "
                f"(got {type(rationale).__name__})"
            )

    # Rule 20: warnings must be a list.
    if "warnings" in payload and not isinstance(payload["warnings"], list):
        errors.append(
            f"invalid type: warnings expected list "
            f"(got {type(payload['warnings']).__name__})"
        )

    # Rule 21: feature_snapshot_ref must be str / dict / None.
    if "feature_snapshot_ref" in payload:
        ref = payload["feature_snapshot_ref"]
        if ref is not None and not isinstance(ref, (str, dict)):
            errors.append(
                f"invalid type: feature_snapshot_ref expected str/dict/None "
                f"(got {type(ref).__name__})"
            )

    # Rule 22: peer_alignment_summary must be a dict.
    if "peer_alignment_summary" in payload:
        pas = payload["peer_alignment_summary"]
        if not isinstance(pas, dict):
            errors.append(
                f"invalid type: peer_alignment_summary expected dict "
                f"(got {type(pas).__name__})"
            )

    # Rule 23 + 24: non_mutation_confirmations must be a dict containing
    # the four required keys, each set to True.
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
