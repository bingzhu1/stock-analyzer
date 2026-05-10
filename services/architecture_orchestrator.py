"""Architecture orchestrator ownership skeleton (Step 18V / PR-ARCH-1).

Spec source of truth:

- `tasks/record_1_0_architecture_reset_canonical_principles.md` §8 / §10
- `tasks/record_16i_core_chain_rebuild_execution_plan.md` PR-F
- `tasks/record_17j_final_report_layer_rebuild_plan.md` §13 PR-FINAL-7
- `tasks/record_18s_third_layer_based_implementation_batch_selection.md`
  §4 / §6 / §10

Status (per 17J §13 PR-FINAL-7 / 18S §10):

- This module is a **skeleton-only** declaration of ownership for the
  future ``architecture_orchestrator``. It does **not** assemble any
  layer, does **not** call any active producer, does **not** import any
  business / orchestrator / UI / DB module.
- 17J §13 PR-FINAL-7 classifies ``architecture_orchestrator`` as an
  ``ASSEMBLY_ORCHESTRATION_LAYER`` / ``TEMP_FUTURE_ORCHESTRATOR``.
  Per 1.0 §8 it is **not** part of the nine-branch canonical
  architecture; it is the connecting tissue that future PRs may use to
  wire Data → Feature → Projection → Exclusion → Confidence →
  Final Report into a single call site.
- The actual wire-in is **deferred** to a future batch (later than 18Z)
  with explicit user confirmation. PR-ARCH-1 only pins the ownership
  contract so reviewers can detect any premature wire-in attempts.

Boundary contract (1.0 / 16A / 16C / 16F / 17J / 18S):

- This module is a **pure-function skeleton**. It:
  - Exposes ``get_architecture_orchestrator_contract()`` returning a
    fresh, isolated dict that documents the orchestrator's ownership
    surface and its forbidden actions.
  - Exposes ``validate_architecture_orchestrator_contract(contract)``
    that returns ``list[str]`` errors when the contract dict mutates
    away from the skeleton invariants. Never raises; never mutates.
  - Never reads files / calls external APIs / imports business modules /
    invokes a language-model client / writes to any DB / runs replay /
    runs calibration / places trades.
- It **must not** import any of: ``data_fetcher``, ``feature_builder``,
  ``scanner``, ``matcher``, ``encoder``, ``services.feature_payload_adapter``,
  ``services.projection_result_adapter``,
  ``services.exclusion_result_adapter``,
  ``services.main_projection_layer``, ``services.exclusion_layer``,
  ``services.peer_alignment``, ``services.confidence_evaluator``,
  ``services.final_decision``, ``services.consistency_layer``,
  ``services.review_orchestrator``,
  ``services.projection_orchestrator``,
  ``services.projection_orchestrator_v2``,
  ``services.projection_entrypoint``,
  ``services.projection_v2_adapter``,
  ``services.home_terminal_orchestrator``,
  ``services.prediction_store``, ``services.market_data_store``,
  any contract / adapter / orchestrator / UI / DB / yfinance / pandas /
  streamlit / external LLM SDK / broker / OMS module, ``predict``,
  ``app``, ``ui.*``.
- It **must not** define ``run`` / ``orchestrate`` / ``execute`` /
  ``main`` entry points that could be wired by accident. The skeleton
  has no execution surface.

Public API (skeleton only):

- ``ARCHITECTURE_ORCHESTRATOR_VERSION`` — canonical skeleton version
  string.
- ``ARCHITECTURE_ORCHESTRATOR_STATUS`` — fixed string ``"skeleton_only"``;
  any wire-in PR must change this constant via a separate, explicit
  PR + user confirmation.
- ``ALLOWED_LAYER_SEQUENCE`` — the canonical 9-layer sequence the
  future orchestrator may walk (Data → Feature → Projection → Exclusion
  → Confidence → Final Report → Review/Learning → Evaluation →
  Presentation).
- ``FORBIDDEN_ACTIVE_PATH_ACTIONS`` — actions the skeleton must never
  invoke (``run_predict`` / ``call_main_projection_layer`` etc.).
- ``FORBIDDEN_OUTPUT_FIELDS`` — top-level keys that any future
  orchestrator output must reject.
- ``get_architecture_orchestrator_contract()`` — returns a fresh
  ownership-contract dict (deep copies of all mutable sequences).
- ``validate_architecture_orchestrator_contract(contract)`` — returns
  errors as ``list[str]``; never raises.

Why a skeleton (not a real implementation):

Per 18S §10, ``architecture_orchestrator`` wire-in must wait until
PR-EVAL-2 (holdout guard) + PR-DATA-1 (data layer boundary) + further
adapter active wiring are all in place. Wiring without those guards
would ship a pipeline that can quietly read holdout data, write the
DB, or call legacy orchestrators in mixed states. PR-ARCH-1 carves out
the ownership doc + contract surface now so the future wire-in PR has a
designated home and a contract test that fails the moment any of the
forbidden invariants flips.
"""

from __future__ import annotations

from typing import Any


ARCHITECTURE_ORCHESTRATOR_VERSION: str = "architecture_orchestrator.skeleton.v1"

ARCHITECTURE_ORCHESTRATOR_STATUS: str = "skeleton_only"

# 1.0 §8 nine-branch canonical sequence. The ninth branch (Presentation)
# may either consume from the orchestrator's combined output or take its
# input directly from each upstream layer; the skeleton only documents
# the canonical ordering, it does not enforce a particular delivery path.
ALLOWED_LAYER_SEQUENCE: tuple[str, ...] = (
    "data",
    "feature",
    "projection",
    "exclusion",
    "confidence",
    "final_report",
    "review_learning",
    "evaluation",
    "presentation",
)

# 18S §4 / §6 — the skeleton must NOT invoke any of these actions.
# These are the call surfaces the future wire-in PR will gate on
# explicit user confirmation + completion of PR-EVAL-2 / PR-DATA-1 /
# adapter active wiring. Skeleton-only PRs are forbidden from using them.
FORBIDDEN_ACTIVE_PATH_ACTIONS: tuple[str, ...] = (
    "run_predict",
    "call_main_projection_layer",
    "call_exclusion_layer",
    "call_confidence_evaluator",
    "call_final_decision",
    "call_review_orchestrator",
    "call_projection_orchestrator",
    "call_home_terminal_orchestrator",
    "write_db",
    "write_logs",
    "run_replay",
    "run_calibration",
    "run_holdout",
    "place_trade",
)

# 1.0 §6 / §13 — the orchestrator's eventual output must never carry
# any of these top-level keys. The skeleton pins these as a contract
# constant so the future wire-in PR cannot quietly relax the guard.
FORBIDDEN_OUTPUT_FIELDS: tuple[str, ...] = (
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
    "simulated_trade",
    "live_trade",
    "broker_order",
    "active_rule_promotion",
    "promote_rule",
)


_CONTRACT_NOTES: tuple[str, ...] = (
    "PR-ARCH-1 (Step 18V): skeleton-only declaration; no wire-in.",
    "Wire-in is deferred until PR-EVAL-2 (holdout guard) + PR-DATA-1 "
    "(data layer boundary) + further adapter active wiring complete.",
    "1.0 §12 / 17D §11 — wire-in requires explicit user confirmation and "
    "must not auto-unlock 3R-5 / 3R-6.",
    "17J §13 PR-FINAL-7 classifies architecture_orchestrator as "
    "ASSEMBLY_ORCHESTRATION_LAYER / TEMP_FUTURE_ORCHESTRATOR; not part of "
    "the nine-branch canonical architecture.",
)


def get_architecture_orchestrator_contract() -> dict[str, Any]:
    """Return a fresh ownership-contract dict for the architecture
    orchestrator skeleton.

    The returned dict is **isolated**: each call materialises new list
    instances so a caller mutating the returned dict cannot affect the
    next caller's contract.
    """
    return {
        "version": ARCHITECTURE_ORCHESTRATOR_VERSION,
        "status": ARCHITECTURE_ORCHESTRATOR_STATUS,
        "allowed_layer_sequence": list(ALLOWED_LAYER_SEQUENCE),
        "forbidden_active_path_actions": list(FORBIDDEN_ACTIVE_PATH_ACTIONS),
        "forbidden_output_fields": list(FORBIDDEN_OUTPUT_FIELDS),
        "active_path_connected": False,
        "db_write_enabled": False,
        "trading_enabled": False,
        "replay_enabled": False,
        "calibration_enabled": False,
        "holdout_run_enabled": False,
        "notes": list(_CONTRACT_NOTES),
    }


def validate_architecture_orchestrator_contract(
    contract: Any,
) -> list[str]:
    """Validate ``contract`` against the skeleton invariants.

    Returns ``[]`` on success; otherwise a list of human-readable error
    strings. Never raises. Never mutates ``contract``.

    Error message shapes (stable; tests rely on the prefix):

        invalid type: contract expected dict
        invalid value: version expected '<canonical>'
        invalid value: status expected 'skeleton_only'
        invalid value: <flag> expected False
        invalid value: allowed_layer_sequence expected <canonical>
        missing forbidden_active_path_actions entry: <action>
        missing forbidden_output_fields entry: <field>
        forbidden field: <field> at top-level

    The ``<flag> expected False`` rule covers ``active_path_connected``
    / ``db_write_enabled`` / ``trading_enabled`` / ``replay_enabled`` /
    ``calibration_enabled`` / ``holdout_run_enabled``.
    """
    if not isinstance(contract, dict):
        return [
            f"invalid type: contract expected dict (got "
            f"{type(contract).__name__})"
        ]

    errors: list[str] = []

    version = contract.get("version")
    if version != ARCHITECTURE_ORCHESTRATOR_VERSION:
        errors.append(
            f"invalid value: version expected "
            f"{ARCHITECTURE_ORCHESTRATOR_VERSION!r} (got {version!r})"
        )

    status = contract.get("status")
    if status != ARCHITECTURE_ORCHESTRATOR_STATUS:
        errors.append(
            f"invalid value: status expected "
            f"{ARCHITECTURE_ORCHESTRATOR_STATUS!r} (got {status!r})"
        )

    for flag in (
        "active_path_connected",
        "db_write_enabled",
        "trading_enabled",
        "replay_enabled",
        "calibration_enabled",
        "holdout_run_enabled",
    ):
        value = contract.get(flag)
        if value is not False:
            errors.append(
                f"invalid value: {flag} expected False (got {value!r})"
            )

    sequence = contract.get("allowed_layer_sequence")
    if not isinstance(sequence, list) or tuple(sequence) != ALLOWED_LAYER_SEQUENCE:
        errors.append(
            f"invalid value: allowed_layer_sequence expected "
            f"{list(ALLOWED_LAYER_SEQUENCE)!r} (got {sequence!r})"
        )

    actions = contract.get("forbidden_active_path_actions")
    if not isinstance(actions, list):
        errors.append(
            f"invalid type: forbidden_active_path_actions expected list "
            f"(got {type(actions).__name__})"
        )
    else:
        action_set = set(actions)
        for required in FORBIDDEN_ACTIVE_PATH_ACTIONS:
            if required not in action_set:
                errors.append(
                    f"missing forbidden_active_path_actions entry: {required}"
                )

    fields = contract.get("forbidden_output_fields")
    if not isinstance(fields, list):
        errors.append(
            f"invalid type: forbidden_output_fields expected list "
            f"(got {type(fields).__name__})"
        )
    else:
        field_set = set(fields)
        for required in FORBIDDEN_OUTPUT_FIELDS:
            if required not in field_set:
                errors.append(
                    f"missing forbidden_output_fields entry: {required}"
                )

    # Top-level guard: even though the skeleton's own
    # get_architecture_orchestrator_contract() never inserts these
    # keys, a future wire-in PR could mistakenly add them. Catch the
    # leak at the contract surface.
    for key in contract:
        if key in FORBIDDEN_OUTPUT_FIELDS:
            errors.append(f"forbidden field: {key} at top-level")

    return errors
