"""Task 075 — Smoke wiring from projection v2 + three-system renderer
to the local projection record store.

Storage wiring only — no projection / exclusion / confidence / final-decision
rule changes. The projection v2 chain is invoked for its raw output; the
three-system renderer reshapes it; this script extracts the fields each
record block needs and writes them via Task 074's
``services.projection_record_store`` API.

Three-system independence is preserved end-to-end: each ``save_*`` helper
writes only to its own table, and the final-summary block stores a
*derived* conflict / usage view that does not duplicate any subsystem's
raw output.

Public helpers (importable from tests)
--------------------------------------
extract_record_01_payload(projection_v2_raw)
extract_record_02_fields(projection_v2_raw, three_systems)
extract_negative_fields(projection_v2_raw, three_systems)
extract_confidence_fields(three_systems)
extract_final_summary_fields(three_systems)
derive_conflict_level(conflict_count)
save_projection_run(conn, *, symbol, as_of_date, projection_v2_raw,
                    three_systems, prediction_for_date=None,
                    run_id=None, status="complete")

CLI
---
    python3 scripts/save_projection_records_smoke.py [--symbol AVGO]
                                                     [--lookback-days 20]
                                                     [--target-date YYYY-MM-DD]
                                                     [--run-id ID]
                                                     [--db-path PATH]
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.projection_record_store import (
    create_projection_run,
    list_projection_runs,
    load_projection_run,
    save_final_summary_record,
    save_negative_system_record,
    save_record_01_structure,
    save_record_02_projection,
    save_record_03_confidence,
)


DEFAULT_SYMBOL = "AVGO"
DEFAULT_LOOKBACK_DAYS = 20
DEFAULT_DB_PATH = ROOT / "data" / "market_data.db"


# ── helpers ────────────────────────────────────────────────────────────────

def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _clean(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"none", "null"} else text


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None


def _log(message: str) -> None:
    print(f"[task075] {message}", flush=True)


# ── extractors ─────────────────────────────────────────────────────────────

def extract_record_01_payload(projection_v2_raw: dict[str, Any]) -> dict[str, Any]:
    """Pull the structure block fields from projection_v2_raw.

    Returned payload includes ``primary_analysis`` basics, the encoder's
    ``feature_payload``, current ``step_status``, and any chain-level
    warnings — enough for a future investigator to reconstruct what the
    structure layer saw.
    """
    v2 = _as_dict(projection_v2_raw)
    primary = _as_dict(v2.get("primary_analysis"))
    feature_payload = _as_dict(v2.get("feature_payload"))

    return {
        "primary_analysis": {
            "ready": bool(primary.get("ready")),
            "direction": _clean(primary.get("direction")) or None,
            "confidence": _clean(primary.get("confidence")) or None,
            "position_label": _clean(primary.get("position_label")) or None,
            "stage_label": _clean(primary.get("stage_label")) or None,
            "volume_state": _clean(primary.get("volume_state")) or None,
            "summary": _clean(primary.get("summary")) or None,
            "lookback_days": _safe_int(primary.get("lookback_days")),
            "warnings": [_clean(w) for w in _as_list(primary.get("warnings")) if _clean(w)],
        },
        "feature_payload": feature_payload,
        "step_status": _as_dict(v2.get("step_status")),
        "warnings": [_clean(w) for w in _as_list(v2.get("warnings")) if _clean(w)],
    }


def extract_record_02_fields(
    projection_v2_raw: dict[str, Any],
    three_systems: dict[str, Any],
) -> dict[str, Any]:
    """Extract record_02_projection fields; ``payload`` is the full
    record_02_projection_system block from the renderer.
    """
    v2 = _as_dict(projection_v2_raw)
    main_proj = _as_dict(v2.get("main_projection"))
    final = _as_dict(v2.get("final_decision"))
    top1 = _as_dict(main_proj.get("predicted_top1"))
    distribution_raw = main_proj.get("state_probabilities")
    distribution = _as_dict(distribution_raw) if distribution_raw else {}

    record_02_payload = _as_dict(_as_dict(three_systems).get("record_02_projection_system"))

    return {
        "five_state_top1": _clean(top1.get("state")) or None,
        "final_direction": (
            _clean(v2.get("final_direction"))
            or _clean(final.get("final_direction"))
            or _clean(final.get("direction"))
            or None
        ),
        "five_state_distribution": distribution,
        "payload": record_02_payload,
    }


def _exclusion_type_from_rule(triggered_rule: str | None) -> str:
    rule = _clean(triggered_rule)
    if rule == "exclude_big_up":
        return "exclude_big_up"
    if rule == "exclude_big_down":
        return "exclude_big_down"
    return "none"


def extract_negative_fields(
    projection_v2_raw: dict[str, Any],
    three_systems: dict[str, Any],
) -> dict[str, Any]:
    """Extract negative_system fields from the renderer's negative block
    plus the v2 raw exclusion_result.triggered_rule.
    """
    negative_payload = _as_dict(_as_dict(three_systems).get("negative_system"))
    exclusion_result = _as_dict(_as_dict(projection_v2_raw).get("exclusion_result"))

    excluded_states = [
        _clean(s)
        for s in _as_list(negative_payload.get("excluded_states"))
        if _clean(s)
    ]
    triggered_rule = _clean(exclusion_result.get("triggered_rule")) or None
    strength = _clean(negative_payload.get("strength")).lower() or "none"

    return {
        "excluded_states": excluded_states,
        "exclusion_type": _exclusion_type_from_rule(triggered_rule),
        "strength": strength,
        "triggered_rule": triggered_rule,
        "payload": negative_payload,
    }


def extract_confidence_fields(three_systems: dict[str, Any]) -> dict[str, Any]:
    """Extract confidence_evaluator fields; ``payload`` is the full block."""
    confidence_payload = _as_dict(_as_dict(three_systems).get("confidence_evaluator"))
    overall = _as_dict(confidence_payload.get("overall_confidence"))
    negative_conf = _as_dict(confidence_payload.get("negative_system_confidence"))
    projection_conf = _as_dict(confidence_payload.get("projection_system_confidence"))

    return {
        "overall_score": _safe_float(overall.get("score")),
        "confidence_band": _clean(overall.get("level")) or None,
        "negative_confidence_level": _clean(negative_conf.get("level")) or None,
        "projection_confidence_level": _clean(projection_conf.get("level")) or None,
        "payload": confidence_payload,
    }


def derive_conflict_level(conflict_count: int) -> str:
    """0 → "none", 1 → "minor", 2+ → "major"."""
    try:
        count = int(conflict_count)
    except (TypeError, ValueError):
        count = 0
    if count <= 0:
        return "none"
    if count == 1:
        return "minor"
    return "major"


def _build_usage_advice(
    *,
    final_direction: str | None,
    overall_band: str | None,
    conflict_level: str,
) -> str:
    direction_text = final_direction or "unknown"
    band_text = overall_band or "unknown"
    base = f"主推演方向 {direction_text}，整体置信度 {band_text}。"
    if conflict_level == "major":
        return base + "三系统出现多项冲突，建议谨慎采纳。"
    if conflict_level == "minor":
        return base + "存在轻微冲突，参考时保留弹性。"
    return base + "三系统一致，按主推演结论参考。"


def extract_final_summary_fields(three_systems: dict[str, Any]) -> dict[str, Any]:
    """Build the final-summary derived view.

    The payload is intentionally compact — it carries conflict_level,
    conflict_count, usage_advice, the three confidence bands, and the
    raw conflicts list. It does NOT copy record_02's distribution or
    negative_system's evidence. This preserves three-system independence
    at the storage level: anyone reading final_summary cannot reconstruct
    record_02 from it.
    """
    ts = _as_dict(three_systems)
    confidence = _as_dict(ts.get("confidence_evaluator"))
    overall = _as_dict(confidence.get("overall_confidence"))
    negative_conf = _as_dict(confidence.get("negative_system_confidence"))
    projection_conf = _as_dict(confidence.get("projection_system_confidence"))
    record_02 = _as_dict(ts.get("record_02_projection_system"))

    conflicts = [_clean(c) for c in _as_list(confidence.get("conflicts")) if _clean(c)]
    conflict_count = len(conflicts)
    conflict_level = derive_conflict_level(conflict_count)

    overall_band = _clean(overall.get("level")) or None
    final_direction_text = _clean(record_02.get("main_projection")) or None
    # The renderer's record_02 main_projection is a sentence; the v2 raw
    # final_decision.final_direction is the canonical short string. Prefer
    # the canonical short form by stripping common prefixes; fall back to None.
    if final_direction_text and "方向" in final_direction_text:
        # heuristic: extract the short direction token after "方向"
        try:
            after = final_direction_text.split("方向", 1)[1]
            short = after.strip().split("，")[0].strip().strip("。")
            final_direction_text = short or None
        except (IndexError, AttributeError):
            pass

    usage_advice = _build_usage_advice(
        final_direction=final_direction_text,
        overall_band=overall_band,
        conflict_level=conflict_level,
    )

    payload: dict[str, Any] = {
        "conflict_level": conflict_level,
        "conflict_count": conflict_count,
        "usage_advice": usage_advice,
        "negative_band": _clean(negative_conf.get("level")) or None,
        "projection_band": _clean(projection_conf.get("level")) or None,
        "overall_band": overall_band,
        "conflicts": conflicts,
    }

    return {
        "conflict_level": conflict_level,
        "usage_advice": usage_advice,
        "payload": payload,
    }


# ── orchestration ──────────────────────────────────────────────────────────

def save_projection_run(
    conn: sqlite3.Connection,
    *,
    symbol: str,
    as_of_date: str,
    projection_v2_raw: dict[str, Any],
    three_systems: dict[str, Any],
    prediction_for_date: str | None = None,
    run_id: str | None = None,
    status: str = "complete",
) -> str:
    """Persist all five record blocks for one (symbol, as_of_date) run.

    Returns the run_id. Idempotent on (run_id) — re-calling with the same
    inputs replaces every block in place.
    """
    final_run_id = create_projection_run(
        conn,
        symbol=symbol,
        as_of_date=as_of_date,
        prediction_for_date=prediction_for_date,
        status=status,
        run_id=run_id,
    )

    # record_01_structure
    record_01_payload = extract_record_01_payload(projection_v2_raw)
    primary = _as_dict(record_01_payload.get("primary_analysis"))
    save_record_01_structure(
        conn,
        run_id=final_run_id,
        symbol=symbol,
        as_of_date=as_of_date,
        lookback_days=primary.get("lookback_days"),
        payload=record_01_payload,
    )

    # record_02_projection
    record_02 = extract_record_02_fields(projection_v2_raw, three_systems)
    save_record_02_projection(
        conn,
        run_id=final_run_id,
        five_state_top1=record_02["five_state_top1"],
        final_direction=record_02["final_direction"],
        five_state_distribution=record_02["five_state_distribution"],
        payload=record_02["payload"],
    )

    # negative_system_record
    negative = extract_negative_fields(projection_v2_raw, three_systems)
    save_negative_system_record(
        conn,
        run_id=final_run_id,
        excluded_states=negative["excluded_states"],
        exclusion_type=negative["exclusion_type"],
        strength=negative["strength"],
        triggered_rule=negative["triggered_rule"],
        payload=negative["payload"],
    )

    # record_03_confidence
    confidence = extract_confidence_fields(three_systems)
    save_record_03_confidence(
        conn,
        run_id=final_run_id,
        overall_score=confidence["overall_score"],
        confidence_band=confidence["confidence_band"],
        negative_confidence_level=confidence["negative_confidence_level"],
        projection_confidence_level=confidence["projection_confidence_level"],
        payload=confidence["payload"],
    )

    # final_summary_record
    final_summary = extract_final_summary_fields(three_systems)
    save_final_summary_record(
        conn,
        run_id=final_run_id,
        conflict_level=final_summary["conflict_level"],
        usage_advice=final_summary["usage_advice"],
        payload=final_summary["payload"],
    )

    return final_run_id


# ── CLI helpers ────────────────────────────────────────────────────────────

def _resolve_target_date(target_date: str | None) -> str:
    if target_date:
        return target_date
    return date.today().isoformat()


def _print_compact_summary(loaded_run: dict[str, Any]) -> None:
    run = _as_dict(loaded_run.get("run"))
    record_02 = _as_dict(loaded_run.get("record_02_projection"))
    negative = _as_dict(loaded_run.get("negative_system"))
    confidence = _as_dict(loaded_run.get("record_03_confidence"))
    final_summary = _as_dict(loaded_run.get("final_summary"))

    _log(f"run_id: {loaded_run.get('run_id')}")
    _log(f"  symbol={run.get('symbol')}, as_of_date={run.get('as_of_date')}, "
         f"prediction_for_date={run.get('prediction_for_date')}, "
         f"status={run.get('status')}")
    _log(f"  record_02_projection : top1={record_02.get('five_state_top1')}, "
         f"final_direction={record_02.get('final_direction')}")
    _log(f"  negative_system      : excluded={negative.get('excluded_states_json')}, "
         f"strength={negative.get('strength')}, type={negative.get('exclusion_type')}")
    _log(f"  record_03_confidence : overall={confidence.get('confidence_band')}, "
         f"score={confidence.get('overall_score')}, "
         f"negative={confidence.get('negative_confidence_level')}, "
         f"projection={confidence.get('projection_confidence_level')}")
    _log(f"  final_summary        : conflict_level={final_summary.get('conflict_level')}, "
         f"usage_advice={final_summary.get('usage_advice')}")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Task 075 — projection record wiring smoke (live AVGO run + persist + reload)"
    )
    parser.add_argument("--symbol", default=DEFAULT_SYMBOL)
    parser.add_argument("--lookback-days", type=int, default=DEFAULT_LOOKBACK_DAYS)
    parser.add_argument("--target-date", default=None,
                        help="YYYY-MM-DD; defaults to today")
    parser.add_argument("--run-id", default=None,
                        help="optional run_id; auto-generated if not given")
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    from services.projection_orchestrator_v2 import run_projection_v2
    from services.projection_three_systems_renderer import build_projection_three_systems

    args = _parse_args(argv)
    symbol = str(args.symbol).strip().upper()
    as_of_date = _resolve_target_date(args.target_date)

    _log(f"running projection v2 for {symbol} (lookback={args.lookback_days}, target={as_of_date})")
    projection_v2_raw = run_projection_v2(
        symbol=symbol,
        lookback_days=args.lookback_days,
        target_date=args.target_date,
    )
    _log(f"projection ready={projection_v2_raw.get('ready')}")

    three_systems = build_projection_three_systems(projection_v2_raw, symbol=symbol)
    _log(f"three_systems ready={three_systems.get('ready')}")

    args.db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(args.db_path))
    try:
        run_id = save_projection_run(
            conn,
            symbol=symbol,
            as_of_date=as_of_date,
            projection_v2_raw=projection_v2_raw,
            three_systems=three_systems,
            run_id=args.run_id,
            status="complete",
        )
        _log(f"saved run_id={run_id}")

        loaded = load_projection_run(conn, run_id)
        _print_compact_summary(loaded)

        _log(f"recent runs for {symbol}:")
        for entry in list_projection_runs(conn, symbol=symbol, limit=5):
            comp = entry.get("completeness", {})
            comp_str = ",".join(k for k, v in comp.items() if v)
            _log(f"  {entry.get('run_id')} {entry.get('as_of_date')} "
                 f"status={entry.get('status')} blocks=[{comp_str}]")
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
