"""Pure-function validator for the ``presentation_payload.v1`` contract
(Step 18I / PR-UI-1).

Spec source of truth:

- `tasks/record_1_0_architecture_reset_canonical_principles.md` §8 (Branch 9)
- `tasks/record_17m_ui_presentation_layer_rebuild_plan.md` §8 / §13 / §15
- `tasks/record_18a_first_layer_based_implementation_batch_selection.md` §13

Status (per 17M §15 / 18A §11):

- This module is the **UI / Presentation Layer (Branch 9) view-model
  contract** introduced as PR-UI-1, the eighth and final batch of the
  first-batch contract helper set after the 17D ~ 17M nine-branch plans
  landed.
- It is **not yet wired into any active path**. ``ui/`` tabs (notably
  ``ui/predict_tab.py``, ``ui/home_tab.py``, ``ui/history_tab.py``,
  ``ui/review_tab.py``, ``ui/inspect_tab.py``, ``ui/research_tab.py``,
  ``ui/scan_tab.py``, ``ui/control_tab.py``) continue to render directly
  from upstream dicts; alignment to ``presentation_payload.v1`` is
  deferred to PR-UI-2 / PR-UI-3 / PR-UI-7 and later batches.

Boundary contract (1.0 / 16A / 16C / 16F / 17M):

- This module is a **pure-function shape validator**. It:
  - Never mutates the input payload.
  - Never raises (returns errors as a plain ``list[str]``); even when the
    input is not a dict, it returns a single error string instead of
    raising ``TypeError``.
  - Never reads files / calls external APIs / imports business modules /
    invokes a language-model client / writes to any DB / renders any UI.
- It **must not** import any of: ``predict``, ``services.*``,
  ``ui.home_tab``, ``ui.predict_tab``, ``ui.history_tab``, ``ui.review_tab``,
  ``ui.inspect_tab``, ``ui.research_tab``, ``ui.scan_tab``,
  ``ui.control_tab``, ``ui.command_bar``, ``ui.projection_v2_renderer``,
  ``ui.protection_layer_diagnostics_renderer``, ``ui.soft_metadata_renderer``,
  ``ui.anti_false_exclusion_display``, ``ui.big_up_contradiction_card``,
  ``ui.exclusion_reliability_review``, ``streamlit``, ``app``, any DB /
  sqlite, ``yfinance``.
- It **must not** create, infer, or modify any payload field. It also
  **must not** read ``app.session_state`` / call any business module /
  render any UI / compute any business result.

Note on the location of this module: although it lives under ``ui/`` for
discoverability (Branch 9 owns view-model schemas), it is import-clean of
``streamlit`` and ``ui/*`` tab modules. It is the only ``ui/*`` file that
the post-1.0 contract surface currently exposes for validation; producers
in ``services/*`` may import it without pulling in ``streamlit``.

Error message shapes (stable; tests rely on the prefix):

    invalid type: payload expected dict
    invalid type: <field> expected <type>
    invalid value: schema_version expected 'presentation_payload.v1'
    invalid value: kind expected 'presentation'
    invalid value: page_id expected non-empty string
    invalid value: tab_id expected non-empty string
    invalid value: compatibility_mode expected one of [...]
    invalid value: no_mutation_confirmations.<key> expected True
    missing section: <section>
    missing field: no_mutation_confirmations.<key>
    warning: display_sections[i] dict missing '<key>'
    warning: cards[i] dict missing '<key>'
    forbidden field: <field> at <location>

Public API:

- ``PRESENTATION_PAYLOAD_SCHEMA_VERSION`` — the canonical schema version
  string.
- ``PRESENTATION_PAYLOAD_KIND`` — the canonical ``kind`` value
  (``"presentation"``).
- ``PRESENTATION_PAYLOAD_SECTIONS`` — the 17 top-level keys, in fixed
  order.
- ``VALID_COMPATIBILITY_MODE`` — accepted values for ``compatibility_mode``
  (``"standard"`` / ``"compatibility_fallback"`` / ``"missing_sections"`` /
  ``"unknown"``).
- ``FORBIDDEN_FIELDS`` — keys that are never allowed at top level
  (raw upstream sections + Branch 3/4/5 verdict fields + downstream
  result sections + legacy bridge fields + active-path execution fields +
  trading / hard / forced / required tokens).
- ``validate_presentation_payload(payload)`` — return ``[]`` on success,
  otherwise a list of human-readable error / warning strings.
"""

from __future__ import annotations

from typing import Any


PRESENTATION_PAYLOAD_SCHEMA_VERSION: str = "presentation_payload.v1"

# 1.0 / 17M canonical ``kind`` for this contract.
PRESENTATION_PAYLOAD_KIND: str = "presentation"

# 17 top-level keys (18A §13 / 17M §13). Order is fixed.
PRESENTATION_PAYLOAD_SECTIONS: tuple[str, ...] = (
    "schema_version",
    "kind",
    "page_id",
    "tab_id",
    "source_payload_schema_version",
    "source_payload_ref",
    "display_sections",
    "cards",
    "tables",
    "charts",
    "warnings",
    "missing_sections",
    "compatibility_mode",
    "compatibility_notes",
    "generated_at",
    "raw_payload_ref",
    "no_mutation_confirmations",
)

# 17M §13 — compatibility_mode enum (4 values).
VALID_COMPATIBILITY_MODE: tuple[str, ...] = (
    "standard",
    "compatibility_fallback",
    "missing_sections",
    "unknown",
)

# 17M §13 — recommended (non-strict) keys for each ``display_sections``
# dict item. Producers may add layout-specific keys; the validator emits
# a ``warning:`` advisory when ``id`` / ``title`` / ``content`` is
# missing but does not hard-fail the payload.
_DISPLAY_SECTION_RECOMMENDED_KEYS: tuple[str, ...] = ("id", "title", "content")

# 17M §13 — recommended (non-strict) keys for each ``cards`` dict item.
_CARD_RECOMMENDED_KEYS: tuple[str, ...] = ("id", "title", "body")

# 1.0 §8 (Branch 9) / 17M §13 — UI must declare it does not mutate the
# source payload, does not recompute any business result, does not run
# replay, and does not write to the DB.
_NO_MUTATION_CONFIRMATIONS_REQUIRED: tuple[str, ...] = (
    "ui_did_not_mutate_source_payload",
    "ui_did_not_recompute_projection",
    "ui_did_not_recompute_exclusion",
    "ui_did_not_recompute_confidence",
    "ui_did_not_run_replay",
    "ui_did_not_write_db",
)

# Forbidden field names at the top level. Anchored to:
#   - 1.0 §6 / §8 (Branch 9 may not output raw upstream sections, verdicts,
#     active-path execution fields, or trading / hard / forced / required
#     tokens)
#   - 17M §8.3 + §13 + 18A §13 (forbidden top-level set for
#     presentation_payload.v1)
#
# 18A explicitly forbids legacy passthrough at top level
# (``final_direction`` / ``final_confidence`` / ``final_bias`` /
# ``primary_projection`` / ``final_projection`` / ``peer_adjustment`` /
# ``path_risk``). They may live inside ``source_payload_ref`` /
# ``compatibility_notes`` for the legacy fallback path, but the
# presentation top level itself never carries them.
FORBIDDEN_FIELDS: frozenset[str] = frozenset({
    # Raw upstream payload / result sections — UI carries view-model only
    "feature_payload",
    "projection_result",
    "exclusion_result",
    "confidence_result",
    "final_report",
    "review_result",
    "evaluation_result",
    # Branch 3 Projection verdict fields
    "most_likely_state",
    "ranked_states",
    "state_probabilities",
    "predicted_top1",
    "predicted_top2",
    # Branch 4 Exclusion verdict fields
    "most_unlikely_state",
    "ranked_unlikely_states",
    "excluded_states",
    "triggered_rules",
    "triggered_rule",
    "false_exclusion_risk",
    # Branch 5 Confidence verdict fields
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
    # Active-path execution fields — 18A §13 forbids these at top level
    "run_predict",
    "replay_result",
    "calibration_result",
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
    # Live trading hooks — 18A §13 explicit list
    "live_trade",
    "broker_order",
})


def validate_presentation_payload(payload: Any) -> list[str]:
    """Validate ``payload`` against ``presentation_payload.v1``.

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

    # Rule 3: every PRESENTATION_PAYLOAD_SECTIONS key must be present.
    for section in PRESENTATION_PAYLOAD_SECTIONS:
        if section not in payload:
            errors.append(f"missing section: {section}")

    # Rule 2: schema_version must equal PRESENTATION_PAYLOAD_SCHEMA_VERSION.
    if "schema_version" in payload:
        if payload["schema_version"] != PRESENTATION_PAYLOAD_SCHEMA_VERSION:
            errors.append(
                f"invalid value: schema_version expected "
                f"{PRESENTATION_PAYLOAD_SCHEMA_VERSION!r} "
                f"(got {payload['schema_version']!r})"
            )

    # Rule 4: kind must equal "presentation".
    if "kind" in payload and payload["kind"] != PRESENTATION_PAYLOAD_KIND:
        errors.append(
            f"invalid value: kind expected {PRESENTATION_PAYLOAD_KIND!r} "
            f"(got {payload['kind']!r})"
        )

    # Rule 5: page_id must be non-empty string.
    if "page_id" in payload:
        pid = payload["page_id"]
        if not isinstance(pid, str) or not pid:
            errors.append(
                f"invalid value: page_id expected non-empty string "
                f"(got {pid!r})"
            )

    # Rule 6: tab_id must be non-empty string.
    if "tab_id" in payload:
        tid = payload["tab_id"]
        if not isinstance(tid, str) or not tid:
            errors.append(
                f"invalid value: tab_id expected non-empty string "
                f"(got {tid!r})"
            )

    # Rule 7: source_payload_schema_version must be str or None.
    if "source_payload_schema_version" in payload:
        spsv = payload["source_payload_schema_version"]
        if spsv is not None and not isinstance(spsv, str):
            errors.append(
                f"invalid type: source_payload_schema_version expected str "
                f"or None (got {type(spsv).__name__})"
            )

    # Rule 8: source_payload_ref must be str / dict / None.
    if "source_payload_ref" in payload:
        spr = payload["source_payload_ref"]
        if spr is not None and not isinstance(spr, (str, dict)):
            errors.append(
                f"invalid type: source_payload_ref expected str/dict/None "
                f"(got {type(spr).__name__})"
            )

    # Rules 9 + 10: display_sections must be a list; each dict item should
    # carry ``id`` + ``title`` + ``content`` (advisory only).
    if "display_sections" in payload:
        ds = payload["display_sections"]
        if not isinstance(ds, list):
            errors.append(
                f"invalid type: display_sections expected list "
                f"(got {type(ds).__name__})"
            )
        else:
            for index, item in enumerate(ds):
                if isinstance(item, dict):
                    for key in _DISPLAY_SECTION_RECOMMENDED_KEYS:
                        if key not in item:
                            errors.append(
                                f"warning: display_sections[{index}] dict "
                                f"missing {key!r}"
                            )

    # Rules 11 + 12: cards must be a list; each dict item should carry
    # ``id`` + ``title`` + ``body`` (advisory only).
    if "cards" in payload:
        cards = payload["cards"]
        if not isinstance(cards, list):
            errors.append(
                f"invalid type: cards expected list "
                f"(got {type(cards).__name__})"
            )
        else:
            for index, item in enumerate(cards):
                if isinstance(item, dict):
                    for key in _CARD_RECOMMENDED_KEYS:
                        if key not in item:
                            errors.append(
                                f"warning: cards[{index}] dict missing {key!r}"
                            )

    # Rules 13 / 14 / 15 / 16: tables / charts / warnings / missing_sections
    # must each be a list.
    for list_field in ("tables", "charts", "warnings", "missing_sections"):
        if list_field in payload and not isinstance(payload[list_field], list):
            errors.append(
                f"invalid type: {list_field} expected list "
                f"(got {type(payload[list_field]).__name__})"
            )

    # Rule 17: compatibility_mode must be in VALID_COMPATIBILITY_MODE.
    if "compatibility_mode" in payload:
        cm = payload["compatibility_mode"]
        if cm not in VALID_COMPATIBILITY_MODE:
            errors.append(
                f"invalid value: compatibility_mode expected one of "
                f"{list(VALID_COMPATIBILITY_MODE)!r} (got {cm!r})"
            )

    # Rule 18: compatibility_notes must be list or str.
    if "compatibility_notes" in payload:
        cn = payload["compatibility_notes"]
        if not isinstance(cn, (list, str)):
            errors.append(
                f"invalid type: compatibility_notes expected list or str "
                f"(got {type(cn).__name__})"
            )

    # Rule 19: generated_at must be str or None.
    if "generated_at" in payload:
        ga = payload["generated_at"]
        if ga is not None and not isinstance(ga, str):
            errors.append(
                f"invalid type: generated_at expected str or None "
                f"(got {type(ga).__name__})"
            )

    # Rule 20: raw_payload_ref must be str / dict / None.
    if "raw_payload_ref" in payload:
        rpr = payload["raw_payload_ref"]
        if rpr is not None and not isinstance(rpr, (str, dict)):
            errors.append(
                f"invalid type: raw_payload_ref expected str/dict/None "
                f"(got {type(rpr).__name__})"
            )

    # Rules 21 + 22: no_mutation_confirmations must be a dict containing
    # the six required keys, each set to True.
    if "no_mutation_confirmations" in payload:
        nmc = payload["no_mutation_confirmations"]
        if not isinstance(nmc, dict):
            errors.append(
                f"invalid type: no_mutation_confirmations expected dict "
                f"(got {type(nmc).__name__})"
            )
        else:
            for key in _NO_MUTATION_CONFIRMATIONS_REQUIRED:
                if key not in nmc:
                    errors.append(
                        f"missing field: no_mutation_confirmations.{key}"
                    )
                elif nmc[key] is not True:
                    errors.append(
                        f"invalid value: no_mutation_confirmations.{key} "
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
