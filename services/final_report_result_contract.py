"""Pure-function validator for the ``final_report_result.v1`` contract
(Step 18F / PR-FINAL-1).

Spec source of truth:

- `tasks/record_1_0_architecture_reset_canonical_principles.md` §8 (Branch 6)
- `tasks/record_07d_final_report_aggregator_contract.md` §3 / §9 / §11
- `tasks/record_17j_final_report_layer_rebuild_plan.md` §9 / §11 / §15
- `tasks/record_18a_first_layer_based_implementation_batch_selection.md` §13

Status (per 17J §15 / 18A §11):

- This module is the **Final Report Layer (Branch 6) output contract**
  introduced as PR-FINAL-1, the fifth batch of layer-based implementation
  PRs after the 17D ~ 17M nine-branch plans landed.
- It is **not yet wired into any active path**. Producers (notably
  ``services.final_decision.build_final_decision``) continue to emit the
  prior ``final_report_aggregator_result.v1`` shape with legacy
  passthrough fields (``final_direction`` / ``final_confidence``);
  alignment to ``final_report_result.v1`` is deferred to PR-FINAL-2 /
  PR-FINAL-4 and later batches.

Boundary contract (1.0 / 16A / 16C / 16F / 17J):

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
  ``services.final_decision``, ``services.consistency_layer``,
  ``services.projection_chain_contract``, ``services.predict_summary``,
  ``services.ai_summary``, ``services.main_projection_layer``,
  ``services.exclusion_layer``, ``services.peer_alignment``,
  ``services.confidence_evaluator``, ``services.review_orchestrator``,
  ``services.feature_payload_contract``, ``services.projection_result_contract``,
  ``services.exclusion_result_contract``, ``services.confidence_result_contract``,
  ``services.standard_projection_payload``, ``ui.*``, ``app``, any DB /
  sqlite, ``yfinance``.
- It **must not** create, infer, or modify any payload field. It also
  **must not** compute ``final_direction`` / ``final_confidence`` / call
  ``final_decision`` / read ``projection_result`` / ``exclusion_result``
  / ``confidence_result``.

Error message shapes (stable; tests rely on the prefix):

    invalid type: payload expected dict
    invalid type: <field> expected <type>
    invalid value: schema_version expected 'final_report_result.v1'
    invalid value: kind expected 'final_report'
    invalid value: symbol expected non-empty string
    invalid value: non_mutation_confirmations.<key> expected True
    missing section: <section>
    missing field: non_mutation_confirmations.<key>
    warning: warning_cards[i] dict missing 'type'
    warning: warning_cards[i] dict missing 'message'
    forbidden field: <field> at <location>

The ``warning:`` prefix is reserved for non-blocking advisories that
callers can filter out (e.g. a producer emits a partially-formed
warning card without ``type``/``message`` keys). Strict shape failures
use the other prefixes.

Public API:

- ``FINAL_REPORT_RESULT_SCHEMA_VERSION`` — the canonical schema version
  string.
- ``FINAL_REPORT_RESULT_KIND`` — the canonical ``kind`` value
  (``"final_report"``).
- ``FINAL_REPORT_RESULT_SECTIONS`` — the 20 top-level keys, in fixed order.
- ``FORBIDDEN_FIELDS`` — keys that are never allowed at top level
  (raw upstream sections + Branch 3/4/5 verdict fields + downstream
  result sections + legacy bridge fields + trading / hard / forced /
  required tokens).
- ``validate_final_report_result(payload)`` — return ``[]`` on success,
  otherwise a list of human-readable error / warning strings.
"""

from __future__ import annotations

from typing import Any


FINAL_REPORT_RESULT_SCHEMA_VERSION: str = "final_report_result.v1"

# 1.0 / 07D canonical ``kind`` for this contract.
FINAL_REPORT_RESULT_KIND: str = "final_report"

# 20 top-level keys (18A §13 / 17J §11). Order is fixed.
FINAL_REPORT_RESULT_SECTIONS: tuple[str, ...] = (
    "schema_version",
    "kind",
    "symbol",
    "ready",
    "summary",
    "key_points",
    "risks",
    "evidence_summary",
    "projection_summary",
    "exclusion_summary",
    "confidence_summary",
    "conflict_summary",
    "warning_cards",
    "decision_factors",
    "why_not_more",
    "layer_contributions",
    "source_attribution",
    "raw_section_refs",
    "risk_disclosure",
    "non_mutation_confirmations",
)

# 07D §11 / 17J §11 — Final Report Layer must declare it does not mutate
# any upstream system output and does not read future outcomes.
_NON_MUTATION_CONFIRMATIONS_REQUIRED: tuple[str, ...] = (
    "final_report_did_not_mutate_feature_payload",
    "final_report_did_not_mutate_projection_result",
    "final_report_did_not_mutate_exclusion_result",
    "final_report_did_not_mutate_confidence_result",
    "final_report_did_not_read_future_outcome",
)

# 17J §9.4 — recommended (non-strict) keys for each warning_cards dict
# item. Producers may add card-specific keys; the validator emits a
# ``warning:`` advisory when ``type`` or ``message`` is missing but does
# not hard-fail the payload.
_WARNING_CARD_RECOMMENDED_KEYS: tuple[str, ...] = ("type", "message")

# Forbidden field names at the top level. Anchored to:
#   - 1.0 §6 / §8 (Branch 6 may not output raw upstream sections, verdicts,
#     or trading / hard / forced / required tokens)
#   - 07D §5 / §6 / §7 / §8 / §11 (Final Report must not mutate, must not
#     output ``most_likely_state`` / ``most_unlikely_state`` / ``combined_confidence``
#     at top level — those belong inside the corresponding ``*_summary``
#     section)
#   - 17J §11.4 + 18A §13 (forbidden top-level set for final_report_result.v1)
#
# 18A explicitly forbids the legacy ``final_direction`` / ``final_confidence`` /
# ``final_bias`` fields at top level. Producers that still need to expose
# them will do so via a future Bridge adapter, not at the
# ``final_report_result.v1`` top level.
FORBIDDEN_FIELDS: frozenset[str] = frozenset({
    # Raw upstream payload / result sections — Final Report only carries
    # *_summary sections, never the raw upstream payload.
    "feature_payload",
    "projection_result",
    "exclusion_result",
    "confidence_result",
    # Downstream system result sections
    "review_result",
    "evaluation_result",
    # Branch 3 Projection verdict fields (must live inside projection_summary)
    "most_likely_state",
    "ranked_states",
    "state_probabilities",
    "predicted_top1",
    "predicted_top2",
    # Branch 4 Exclusion verdict fields (must live inside exclusion_summary)
    "most_unlikely_state",
    "ranked_unlikely_states",
    "excluded_states",
    "triggered_rules",
    "triggered_rule",
    "false_exclusion_risk",
    # Branch 5 Confidence verdict fields (must live inside confidence_summary)
    "agreement_status",
    "conflict_level",
    "combined_confidence",
    "projection_confidence",
    "exclusion_confidence",
    # Legacy bridge fields — 18A §13 forbids these at top level
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


def validate_final_report_result(payload: Any) -> list[str]:
    """Validate ``payload`` against ``final_report_result.v1``.

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

    # Rule 3: every FINAL_REPORT_RESULT_SECTIONS key must be present.
    for section in FINAL_REPORT_RESULT_SECTIONS:
        if section not in payload:
            errors.append(f"missing section: {section}")

    # Rule 2: schema_version must equal FINAL_REPORT_RESULT_SCHEMA_VERSION.
    if "schema_version" in payload:
        if payload["schema_version"] != FINAL_REPORT_RESULT_SCHEMA_VERSION:
            errors.append(
                f"invalid value: schema_version expected "
                f"{FINAL_REPORT_RESULT_SCHEMA_VERSION!r} "
                f"(got {payload['schema_version']!r})"
            )

    # Rule 4: kind must equal "final_report".
    if "kind" in payload and payload["kind"] != FINAL_REPORT_RESULT_KIND:
        errors.append(
            f"invalid value: kind expected {FINAL_REPORT_RESULT_KIND!r} "
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

    # Rule 7: summary must be str or list.
    if "summary" in payload:
        summary = payload["summary"]
        if not isinstance(summary, (str, list)):
            errors.append(
                f"invalid type: summary expected str or list "
                f"(got {type(summary).__name__})"
            )

    # Rule 8: key_points must be list.
    if "key_points" in payload and not isinstance(payload["key_points"], list):
        errors.append(
            f"invalid type: key_points expected list "
            f"(got {type(payload['key_points']).__name__})"
        )

    # Rule 9: risks must be list.
    if "risks" in payload and not isinstance(payload["risks"], list):
        errors.append(
            f"invalid type: risks expected list "
            f"(got {type(payload['risks']).__name__})"
        )

    # Rule 10: evidence_summary must be dict / list / str.
    if "evidence_summary" in payload:
        es = payload["evidence_summary"]
        if not isinstance(es, (dict, list, str)):
            errors.append(
                f"invalid type: evidence_summary expected dict, list, or str "
                f"(got {type(es).__name__})"
            )

    # Rules 11 / 12 / 13: projection_summary / exclusion_summary /
    # confidence_summary must be dicts.
    for section_name in (
        "projection_summary",
        "exclusion_summary",
        "confidence_summary",
    ):
        if section_name in payload and not isinstance(payload[section_name], dict):
            errors.append(
                f"invalid type: {section_name} expected dict "
                f"(got {type(payload[section_name]).__name__})"
            )

    # Rule 14: conflict_summary must be dict / list / str.
    if "conflict_summary" in payload:
        cs = payload["conflict_summary"]
        if not isinstance(cs, (dict, list, str)):
            errors.append(
                f"invalid type: conflict_summary expected dict, list, or str "
                f"(got {type(cs).__name__})"
            )

    # Rules 15 + 16: warning_cards must be a list; each dict item should
    # carry ``type`` + ``message`` (advisory only).
    if "warning_cards" in payload:
        wc = payload["warning_cards"]
        if not isinstance(wc, list):
            errors.append(
                f"invalid type: warning_cards expected list "
                f"(got {type(wc).__name__})"
            )
        else:
            for index, item in enumerate(wc):
                if isinstance(item, dict):
                    for key in _WARNING_CARD_RECOMMENDED_KEYS:
                        if key not in item:
                            errors.append(
                                f"warning: warning_cards[{index}] dict "
                                f"missing {key!r}"
                            )

    # Rule 17: decision_factors must be list or dict.
    if "decision_factors" in payload:
        df = payload["decision_factors"]
        if not isinstance(df, (list, dict)):
            errors.append(
                f"invalid type: decision_factors expected list or dict "
                f"(got {type(df).__name__})"
            )

    # Rule 18: why_not_more must be list or str.
    if "why_not_more" in payload:
        wnm = payload["why_not_more"]
        if not isinstance(wnm, (list, str)):
            errors.append(
                f"invalid type: why_not_more expected list or str "
                f"(got {type(wnm).__name__})"
            )

    # Rule 19: layer_contributions must be a dict.
    if "layer_contributions" in payload and not isinstance(
        payload["layer_contributions"], dict
    ):
        errors.append(
            f"invalid type: layer_contributions expected dict "
            f"(got {type(payload['layer_contributions']).__name__})"
        )

    # Rule 20: source_attribution must be dict or list.
    if "source_attribution" in payload:
        sa = payload["source_attribution"]
        if not isinstance(sa, (dict, list)):
            errors.append(
                f"invalid type: source_attribution expected dict or list "
                f"(got {type(sa).__name__})"
            )

    # Rule 21: raw_section_refs must be dict or list.
    if "raw_section_refs" in payload:
        rsr = payload["raw_section_refs"]
        if not isinstance(rsr, (dict, list)):
            errors.append(
                f"invalid type: raw_section_refs expected dict or list "
                f"(got {type(rsr).__name__})"
            )

    # Rule 22: risk_disclosure must be str or list.
    if "risk_disclosure" in payload:
        rd = payload["risk_disclosure"]
        if not isinstance(rd, (str, list)):
            errors.append(
                f"invalid type: risk_disclosure expected str or list "
                f"(got {type(rd).__name__})"
            )

    # Rules 23 + 24: non_mutation_confirmations must be a dict containing
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
