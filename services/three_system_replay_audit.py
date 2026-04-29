"""Aggregation helpers for the 1005-day three-system replay audit (Task 072).

Pure functions only. The driver script is ``scripts/run_1005_three_system_replay.py``.

Inputs
------
A list of "audit cases" — flat dicts produced by ``build_audit_case`` from a single
historical replay result + the projection_three_systems view of its snapshot.

Outputs
-------
- ``summarize_three_system_audit`` — overall + per-system summary dict
- ``negative_system_rows`` / ``record_02_projection_rows`` / ``confidence_evaluator_rows``
  — per-case rows for CSV export
- ``false_exclusion_rows`` / ``error_rows`` / ``high_confidence_wrong_rows`` — case-level
  filters, each shaped for direct CSV export

The aggregator never raises on malformed input. Missing fields degrade to ``None``
or empty buckets so the script can still produce stable output across 1005 cases.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

from services.state_label import label_state_from_ratio


# ── helpers ──────────────────────────────────────────────────────────────────

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


def _bucket_accuracy(items: list[bool]) -> float | None:
    return sum(items) / len(items) if items else None


def _state_from_close_change(close_change: Any) -> str:
    value = _safe_float(close_change)
    if value is None:
        return "unknown"
    try:
        return label_state_from_ratio(value)
    except (TypeError, ValueError):
        return "unknown"


_FIVE_STATES = ("大涨", "小涨", "震荡", "小跌", "大跌")
_DIRECTIONS = ("偏多", "偏空", "震荡", "中性", "unknown")
_LEVELS = ("high", "medium", "low", "unknown")
_NEGATIVE_STRENGTHS = ("high", "medium", "low", "none")


# ── per-case audit record ────────────────────────────────────────────────────

def build_audit_case(
    *,
    replay_result: dict[str, Any],
    three_systems: dict[str, Any],
) -> dict[str, Any]:
    """Flatten one (replay_result, three_systems) pair into a stable audit record.

    All fields are tolerant: missing or malformed inputs degrade to ``None``,
    empty list, or "unknown" rather than raising.
    """
    replay = _as_dict(replay_result)
    snapshot = _as_dict(replay.get("projection_snapshot"))
    feature_payload = _as_dict(snapshot.get("feature_payload"))
    actual = _as_dict(replay.get("actual_outcome"))
    review = _as_dict(replay.get("review"))

    ts = _as_dict(three_systems)
    negative = _as_dict(ts.get("negative_system"))
    projection = _as_dict(ts.get("record_02_projection_system"))
    confidence = _as_dict(ts.get("confidence_evaluator"))
    neg_conf = _as_dict(confidence.get("negative_system_confidence"))
    proj_conf = _as_dict(confidence.get("projection_system_confidence"))
    overall_conf = _as_dict(confidence.get("overall_confidence"))

    final = _as_dict(snapshot.get("final_decision"))
    main_proj = _as_dict(snapshot.get("main_projection"))
    top1 = _as_dict(main_proj.get("predicted_top1"))
    exclusion = _as_dict(snapshot.get("exclusion_result"))

    excluded_states = [_clean(s) for s in _as_list(negative.get("excluded_states")) if _clean(s)]
    triggered_rule = _clean(exclusion.get("triggered_rule"))

    actual_close_change = actual.get("actual_close_change")
    if actual_close_change is None:
        actual_close_change = actual.get("close_change")
    actual_state = _state_from_close_change(actual_close_change)

    direction_correct = review.get("direction_correct")
    if not isinstance(direction_correct, bool):
        direction_correct = None

    final_direction = _clean(
        snapshot.get("final_direction")
        or final.get("final_direction")
        or final.get("direction")
    ) or "unknown"
    final_top1_state = _clean(top1.get("state")) or "unknown"

    five_state_top1 = final_top1_state if final_top1_state in _FIVE_STATES else "unknown"

    overall_level = _clean(overall_conf.get("level")).lower() or "unknown"
    if overall_level not in _LEVELS:
        overall_level = "unknown"

    neg_level = _clean(neg_conf.get("level")).lower() or "unknown"
    if neg_level not in _LEVELS:
        neg_level = "unknown"

    proj_level = _clean(proj_conf.get("level")).lower() or "unknown"
    if proj_level not in _LEVELS:
        proj_level = "unknown"

    neg_strength = _clean(negative.get("strength")).lower() or "none"
    if neg_strength not in _NEGATIVE_STRENGTHS:
        neg_strength = "none"

    evidence = [_clean(e) for e in _as_list(negative.get("evidence")) if _clean(e)]
    invalidating = [_clean(i) for i in _as_list(negative.get("invalidating_conditions")) if _clean(i)]
    conflicts = [_clean(c) for c in _as_list(confidence.get("conflicts")) if _clean(c)]
    reliability = [_clean(r) for r in _as_list(confidence.get("reliability_warnings")) if _clean(r)]

    five_state_dist = projection.get("five_state_projection")
    if not isinstance(five_state_dist, dict):
        five_state_dist = {}

    historical_summary = _clean(projection.get("historical_sample_summary"))
    peer_summary = _clean(projection.get("peer_market_confirmation"))
    risk_notes = [_clean(n) for n in _as_list(projection.get("risk_notes")) if _clean(n)]

    error_layer = _clean(review.get("error_layer")) or "unknown"
    error_category = _clean(review.get("error_category")) or "unknown"
    rule_candidates_raw = [c for c in _as_list(review.get("rule_candidates")) if isinstance(c, dict)]

    historical = _as_dict(snapshot.get("historical_probability"))
    peer_layer = _as_dict(snapshot.get("peer_adjustment"))
    sample_quality = _clean(historical.get("sample_quality")) or "unknown"
    peer_confirmation = _clean(peer_layer.get("confirmation_level")) or "unknown"

    return {
        "as_of_date": replay.get("as_of_date"),
        "prediction_for_date": replay.get("prediction_for_date"),
        "ready": bool(replay.get("ready")),
        "warnings": [_clean(w) for w in _as_list(replay.get("warnings")) if _clean(w)],
        # negative system
        "negative_excluded": bool(exclusion.get("excluded")),
        "negative_triggered_rule": triggered_rule,
        "negative_excluded_states": excluded_states,
        "negative_strength": neg_strength,
        "negative_evidence_count": len(evidence),
        "negative_evidence": evidence,
        "negative_invalidating_conditions": invalidating,
        "negative_confidence_level": neg_level,
        # 02 projection system
        "final_direction": final_direction,
        "five_state_top1": five_state_top1,
        "five_state_projection": five_state_dist,
        "historical_sample_summary": historical_summary,
        "peer_market_confirmation": peer_summary,
        "projection_risk_note_count": len(risk_notes),
        "projection_risk_notes": risk_notes,
        "historical_sample_quality": sample_quality,
        "peer_confirmation_level": peer_confirmation,
        # confidence evaluator
        "projection_confidence_level": proj_level,
        "overall_confidence_level": overall_level,
        "conflicts": conflicts,
        "reliability_warnings": reliability,
        # actual + review
        "actual_close_change": _safe_float(actual_close_change),
        "actual_state": actual_state,
        "actual_open_label": _clean(actual.get("open_label")) or "unknown",
        "actual_close_label": _clean(actual.get("close_label")) or "unknown",
        "actual_path_label": _clean(actual.get("path_label")) or "unknown",
        "direction_correct": direction_correct,
        "error_layer": error_layer,
        "error_category": error_category,
        "rule_candidates": rule_candidates_raw,
        # structural features flattened from projection_snapshot.feature_payload
        # (Task 107 — calibration / regime slicing inputs; missing payload → all None)
        "pos20": _safe_float(feature_payload.get("pos20")),
        "vol_ratio20": _safe_float(feature_payload.get("vol_ratio20")),
        "upper_shadow_ratio": _safe_float(feature_payload.get("upper_shadow_ratio")),
        "lower_shadow_ratio": _safe_float(feature_payload.get("lower_shadow_ratio")),
        "ret1": _safe_float(feature_payload.get("ret1")),
        "ret3": _safe_float(feature_payload.get("ret3")),
        "ret5": _safe_float(feature_payload.get("ret5")),
        "ret10": _safe_float(feature_payload.get("ret10")),
        "nvda_ret1": _safe_float(feature_payload.get("nvda_ret1")),
        "soxx_ret1": _safe_float(feature_payload.get("soxx_ret1")),
        "qqq_ret1": _safe_float(feature_payload.get("qqq_ret1")),
    }


# ── classification helpers ───────────────────────────────────────────────────

def _is_false_exclusion(case: dict[str, Any]) -> bool:
    if not case.get("negative_excluded"):
        return False
    actual = case.get("actual_state")
    if actual not in _FIVE_STATES:
        return False
    return actual in (case.get("negative_excluded_states") or [])


def _is_high_confidence_wrong(case: dict[str, Any]) -> bool:
    if case.get("overall_confidence_level") != "high":
        return False
    return case.get("direction_correct") is False


# ── per-case CSV row builders ────────────────────────────────────────────────

def negative_system_row(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "as_of_date": case.get("as_of_date"),
        "prediction_for_date": case.get("prediction_for_date"),
        "ready": case.get("ready"),
        "excluded": case.get("negative_excluded"),
        "triggered_rule": case.get("negative_triggered_rule"),
        "excluded_states": "|".join(case.get("negative_excluded_states") or []),
        "strength": case.get("negative_strength"),
        "negative_confidence_level": case.get("negative_confidence_level"),
        "evidence_count": case.get("negative_evidence_count"),
        "actual_state": case.get("actual_state"),
        "false_exclusion": _is_false_exclusion(case),
        "direction_correct": case.get("direction_correct"),
    }


def record_02_projection_row(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "as_of_date": case.get("as_of_date"),
        "prediction_for_date": case.get("prediction_for_date"),
        "ready": case.get("ready"),
        "final_direction": case.get("final_direction"),
        "five_state_top1": case.get("five_state_top1"),
        "actual_state": case.get("actual_state"),
        "five_state_top1_correct": (
            case.get("five_state_top1") == case.get("actual_state")
            if case.get("five_state_top1") in _FIVE_STATES
            and case.get("actual_state") in _FIVE_STATES
            else None
        ),
        "actual_open_label": case.get("actual_open_label"),
        "actual_close_label": case.get("actual_close_label"),
        "actual_path_label": case.get("actual_path_label"),
        "historical_sample_quality": case.get("historical_sample_quality"),
        "peer_confirmation_level": case.get("peer_confirmation_level"),
        "projection_risk_note_count": case.get("projection_risk_note_count"),
        "direction_correct": case.get("direction_correct"),
    }


def confidence_evaluator_row(case: dict[str, Any]) -> dict[str, Any]:
    conflicts = case.get("conflicts") or []
    reliability = case.get("reliability_warnings") or []
    return {
        "as_of_date": case.get("as_of_date"),
        "prediction_for_date": case.get("prediction_for_date"),
        "ready": case.get("ready"),
        "negative_confidence_level": case.get("negative_confidence_level"),
        "projection_confidence_level": case.get("projection_confidence_level"),
        "overall_confidence_level": case.get("overall_confidence_level"),
        "conflict_count": len(conflicts),
        "reliability_warning_count": len(reliability),
        "direction_correct": case.get("direction_correct"),
        "actual_state": case.get("actual_state"),
        "high_confidence_wrong": _is_high_confidence_wrong(case),
    }


def error_case_row(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "as_of_date": case.get("as_of_date"),
        "prediction_for_date": case.get("prediction_for_date"),
        "final_direction": case.get("final_direction"),
        "five_state_top1": case.get("five_state_top1"),
        "actual_state": case.get("actual_state"),
        "overall_confidence_level": case.get("overall_confidence_level"),
        "error_layer": case.get("error_layer"),
        "error_category": case.get("error_category"),
        "negative_excluded": case.get("negative_excluded"),
        "negative_triggered_rule": case.get("negative_triggered_rule"),
        "false_exclusion": _is_false_exclusion(case),
    }


def false_exclusion_row(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "as_of_date": case.get("as_of_date"),
        "prediction_for_date": case.get("prediction_for_date"),
        "triggered_rule": case.get("negative_triggered_rule"),
        "excluded_states": "|".join(case.get("negative_excluded_states") or []),
        "actual_state": case.get("actual_state"),
        "negative_strength": case.get("negative_strength"),
        "negative_confidence": case.get("negative_confidence_level"),
        "evidence": " || ".join(case.get("negative_evidence") or []),
        "invalidating_conditions": " || ".join(case.get("negative_invalidating_conditions") or []),
        "final_direction": case.get("final_direction"),
        "overall_confidence": case.get("overall_confidence_level"),
    }


def high_confidence_wrong_row(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "as_of_date": case.get("as_of_date"),
        "prediction_for_date": case.get("prediction_for_date"),
        "final_direction": case.get("final_direction"),
        "five_state_top1": case.get("five_state_top1"),
        "overall_confidence": case.get("overall_confidence_level"),
        "negative_confidence": case.get("negative_confidence_level"),
        "projection_confidence": case.get("projection_confidence_level"),
        "actual_state": case.get("actual_state"),
        "direction_correct": case.get("direction_correct"),
        "error_category": case.get("error_category"),
        "conflicts": " || ".join(case.get("conflicts") or []),
        "reliability_warnings": " || ".join(case.get("reliability_warnings") or []),
    }


# ── filtered case extractors ─────────────────────────────────────────────────

def filter_false_exclusion_cases(cases: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [false_exclusion_row(c) for c in cases if _is_false_exclusion(c)]


def filter_high_confidence_wrong_cases(cases: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [high_confidence_wrong_row(c) for c in cases if _is_high_confidence_wrong(c)]


def filter_error_cases(cases: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in cases:
        if case.get("direction_correct") is False:
            rows.append(error_case_row(case))
    return rows


# ── aggregation ──────────────────────────────────────────────────────────────

def _empty_dist(keys: tuple[str, ...]) -> dict[str, int]:
    return {key: 0 for key in keys}


def _bump(dist: dict[str, int], key: str, *, fallback: str = "unknown") -> None:
    bucket = key if key in dist else fallback
    dist[bucket] = dist.get(bucket, 0) + 1


def summarize_three_system_audit(cases: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate one batch of audit cases into the Task 072 summary shape.

    All four required statistic blocks are emitted, with empty/None fallbacks
    when no case carries a verdict.
    """
    total = len(cases)
    completed = sum(1 for c in cases if c.get("ready"))
    failed = total - completed

    # ── A. overall ───────────────────────────────────────────────────────────
    judged: list[bool] = []
    by_confidence: dict[str, list[bool]] = {"high": [], "medium": [], "low": [], "unknown": []}
    by_final_direction: dict[str, list[bool]] = {key: [] for key in _DIRECTIONS}
    by_five_state_top1: dict[str, list[bool]] = {key: [] for key in (*_FIVE_STATES, "unknown")}
    error_categories: Counter[str] = Counter()
    rule_candidates: Counter[tuple[str, str]] = Counter()

    # ── B. negative system ───────────────────────────────────────────────────
    negative_triggered = 0
    excl_big_up = 0
    excl_big_down = 0
    excl_none = 0
    negative_strength_dist = _empty_dist(_NEGATIVE_STRENGTHS)
    negative_confidence_dist = _empty_dist(_LEVELS)
    false_exclusion_count = 0

    # ── C. 02 projection ─────────────────────────────────────────────────────
    final_direction_dist = _empty_dist(_DIRECTIONS)
    five_state_top1_dist = _empty_dist((*_FIVE_STATES, "unknown"))
    sample_quality_dist: Counter[str] = Counter()
    peer_confirmation_dist: Counter[str] = Counter()
    five_state_correct = 0
    five_state_judged = 0
    risk_notes_present = 0

    # ── D. confidence evaluator ──────────────────────────────────────────────
    overall_confidence_dist = _empty_dist(_LEVELS)
    projection_confidence_dist = _empty_dist(_LEVELS)
    high_confidence_wrong_count = 0
    neg_high_proj_low = 0
    proj_high_neg_low = 0

    for case in cases:
        if not case.get("ready"):
            continue

        # negative system
        if case.get("negative_excluded"):
            negative_triggered += 1
            triggered_rule = case.get("negative_triggered_rule")
            if triggered_rule == "exclude_big_up":
                excl_big_up += 1
            elif triggered_rule == "exclude_big_down":
                excl_big_down += 1
        else:
            excl_none += 1

        _bump(negative_strength_dist, case.get("negative_strength") or "none", fallback="none")
        _bump(negative_confidence_dist, case.get("negative_confidence_level") or "unknown")

        # 02 projection
        _bump(final_direction_dist, case.get("final_direction") or "unknown")
        _bump(five_state_top1_dist, case.get("five_state_top1") or "unknown")
        sample_quality_dist[case.get("historical_sample_quality") or "unknown"] += 1
        peer_confirmation_dist[case.get("peer_confirmation_level") or "unknown"] += 1
        if case.get("projection_risk_note_count"):
            risk_notes_present += 1

        # confidence
        _bump(overall_confidence_dist, case.get("overall_confidence_level") or "unknown")
        _bump(projection_confidence_dist, case.get("projection_confidence_level") or "unknown")

        # cross-system conflicts
        neg_level = case.get("negative_confidence_level")
        proj_level = case.get("projection_confidence_level")
        if neg_level == "high" and proj_level == "low":
            neg_high_proj_low += 1
        if proj_level == "high" and neg_level == "low":
            proj_high_neg_low += 1

        # outcome-dependent
        direction_correct = case.get("direction_correct")
        if isinstance(direction_correct, bool):
            judged.append(direction_correct)
            by_confidence[case.get("overall_confidence_level") or "unknown"].append(direction_correct)
            final_dir = case.get("final_direction") or "unknown"
            if final_dir in by_final_direction:
                by_final_direction[final_dir].append(direction_correct)
            top1 = case.get("five_state_top1") or "unknown"
            if top1 in by_five_state_top1:
                by_five_state_top1[top1].append(direction_correct)

            if not direction_correct and case.get("overall_confidence_level") == "high":
                high_confidence_wrong_count += 1

        # five-state top1 accuracy
        top1 = case.get("five_state_top1")
        actual = case.get("actual_state")
        if top1 in _FIVE_STATES and actual in _FIVE_STATES:
            five_state_judged += 1
            if top1 == actual:
                five_state_correct += 1

        # false exclusion
        if _is_false_exclusion(case):
            false_exclusion_count += 1

        # error categories
        category = case.get("error_category")
        if isinstance(category, str) and category and category != "unknown":
            error_categories[category] += 1

        # rule candidates: pulled from review.rule_candidates if present in case extras
        for cand in _as_list(case.get("rule_candidates")):
            if not isinstance(cand, dict):
                continue
            rule_id = _clean(cand.get("rule_id"))
            title = _clean(cand.get("title"))
            if rule_id:
                rule_candidates[(rule_id, title)] += 1

    direction_accuracy = _bucket_accuracy(judged)
    accuracy_by_confidence = {
        key: _bucket_accuracy(items) for key, items in by_confidence.items()
    }
    accuracy_by_final_direction = {
        key: _bucket_accuracy(items) for key, items in by_final_direction.items()
    }
    accuracy_by_five_state_top1 = {
        key: _bucket_accuracy(items) for key, items in by_five_state_top1.items()
    }
    five_state_top1_accuracy = (
        five_state_correct / five_state_judged if five_state_judged > 0 else None
    )

    ready_rate = (completed / total) if total > 0 else None

    overall = {
        "total_cases": total,
        "completed_cases": completed,
        "failed_cases": failed,
        "ready_rate": ready_rate,
        "direction_accuracy": direction_accuracy,
        "accuracy_by_confidence": accuracy_by_confidence,
        "accuracy_by_final_direction": accuracy_by_final_direction,
        "accuracy_by_five_state_top1": accuracy_by_five_state_top1,
        "top_error_categories": [
            {"category": cat, "count": cnt}
            for cat, cnt in error_categories.most_common(5)
        ],
        "top_rule_candidates": [
            {"rule_id": rule_id, "title": title, "count": cnt}
            for (rule_id, title), cnt in rule_candidates.most_common(10)
        ],
    }

    negative_block = {
        "triggered_count": negative_triggered,
        "exclude_big_up_count": excl_big_up,
        "exclude_big_down_count": excl_big_down,
        "no_exclusion_count": excl_none,
        "strength_distribution": negative_strength_dist,
        "confidence_distribution": negative_confidence_dist,
        "false_exclusion_count": false_exclusion_count,
    }

    record_02_block = {
        "final_direction_distribution": final_direction_dist,
        "five_state_top1_distribution": five_state_top1_dist,
        "five_state_top1_accuracy": five_state_top1_accuracy,
        "five_state_top1_judged": five_state_judged,
        "historical_sample_quality_distribution": dict(sample_quality_dist),
        "peer_confirmation_distribution": dict(peer_confirmation_dist),
        "risk_notes_present_count": risk_notes_present,
    }

    confidence_block = {
        "overall_confidence_distribution": overall_confidence_dist,
        "projection_confidence_distribution": projection_confidence_dist,
        "negative_confidence_distribution": negative_confidence_dist,
        "high_confidence_wrong_count": high_confidence_wrong_count,
        "negative_high_projection_low": neg_high_proj_low,
        "projection_high_negative_low": proj_high_neg_low,
        "calibration_table": _calibration_table(by_confidence),
    }

    return {
        "kind": "three_system_replay_summary",
        "overall": overall,
        "negative_system": negative_block,
        "record_02_projection_system": record_02_block,
        "confidence_evaluator": confidence_block,
    }


def _calibration_table(by_confidence: dict[str, list[bool]]) -> list[dict[str, Any]]:
    """One row per confidence level: count, correct, accuracy."""
    rows: list[dict[str, Any]] = []
    for level in ("high", "medium", "low", "unknown"):
        items = by_confidence.get(level, [])
        rows.append({
            "level": level,
            "judged_count": len(items),
            "correct_count": sum(1 for x in items if x),
            "accuracy": _bucket_accuracy(items),
        })
    return rows


# ── markdown summary ────────────────────────────────────────────────────────

def _fmt_pct(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value * 100:.2f}%"


def _fmt_dist(dist: dict[str, int]) -> str:
    if not dist:
        return "(empty)"
    return ", ".join(f"{key}={value}" for key, value in dist.items())


def render_summary_markdown(summary: dict[str, Any]) -> str:
    """Build a human-readable markdown summary of the three-system audit."""
    overall = summary.get("overall", {})
    negative = summary.get("negative_system", {})
    record_02 = summary.get("record_02_projection_system", {})
    confidence = summary.get("confidence_evaluator", {})

    lines: list[str] = []
    lines.append("# AVGO 1005-Day Three-System Replay Summary")
    lines.append("")
    lines.append("## A. Overall replay")
    lines.append(f"- total_cases: {overall.get('total_cases', 0)}")
    lines.append(f"- completed_cases: {overall.get('completed_cases', 0)}")
    lines.append(f"- failed_cases: {overall.get('failed_cases', 0)}")
    lines.append(f"- ready_rate: {_fmt_pct(overall.get('ready_rate'))}")
    lines.append(f"- direction_accuracy: {_fmt_pct(overall.get('direction_accuracy'))}")
    lines.append("- accuracy_by_confidence:")
    for level, accuracy in (overall.get("accuracy_by_confidence") or {}).items():
        lines.append(f"  - {level}: {_fmt_pct(accuracy)}")
    lines.append("- top_error_categories:")
    for entry in overall.get("top_error_categories") or []:
        lines.append(f"  - {entry.get('category')}: {entry.get('count')}")
    if not overall.get("top_error_categories"):
        lines.append("  - (none)")

    lines.append("")
    lines.append("## B. Negative system")
    lines.append(f"- triggered_count: {negative.get('triggered_count', 0)}")
    lines.append(f"- exclude_big_up_count: {negative.get('exclude_big_up_count', 0)}")
    lines.append(f"- exclude_big_down_count: {negative.get('exclude_big_down_count', 0)}")
    lines.append(f"- no_exclusion_count: {negative.get('no_exclusion_count', 0)}")
    lines.append(f"- strength_distribution: {_fmt_dist(negative.get('strength_distribution') or {})}")
    lines.append(f"- confidence_distribution: {_fmt_dist(negative.get('confidence_distribution') or {})}")
    lines.append(f"- false_exclusion_count: {negative.get('false_exclusion_count', 0)}")

    lines.append("")
    lines.append("## C. 02 record projection system")
    lines.append(f"- final_direction_distribution: {_fmt_dist(record_02.get('final_direction_distribution') or {})}")
    lines.append(f"- five_state_top1_distribution: {_fmt_dist(record_02.get('five_state_top1_distribution') or {})}")
    lines.append(f"- five_state_top1_accuracy: {_fmt_pct(record_02.get('five_state_top1_accuracy'))} (n={record_02.get('five_state_top1_judged', 0)})")
    lines.append(f"- historical_sample_quality_distribution: {_fmt_dist(record_02.get('historical_sample_quality_distribution') or {})}")
    lines.append(f"- peer_confirmation_distribution: {_fmt_dist(record_02.get('peer_confirmation_distribution') or {})}")
    lines.append(f"- risk_notes_present_count: {record_02.get('risk_notes_present_count', 0)}")

    lines.append("")
    lines.append("## D. Confidence evaluator")
    lines.append(f"- overall_confidence_distribution: {_fmt_dist(confidence.get('overall_confidence_distribution') or {})}")
    lines.append(f"- projection_confidence_distribution: {_fmt_dist(confidence.get('projection_confidence_distribution') or {})}")
    lines.append(f"- negative_confidence_distribution: {_fmt_dist(confidence.get('negative_confidence_distribution') or {})}")
    lines.append(f"- high_confidence_wrong_count: {confidence.get('high_confidence_wrong_count', 0)}")
    lines.append(f"- negative_high_projection_low (conflict): {confidence.get('negative_high_projection_low', 0)}")
    lines.append(f"- projection_high_negative_low (conflict): {confidence.get('projection_high_negative_low', 0)}")
    lines.append("- calibration_table:")
    for row in confidence.get("calibration_table") or []:
        lines.append(
            f"  - {row.get('level')}: judged={row.get('judged_count')}, "
            f"correct={row.get('correct_count')}, accuracy={_fmt_pct(row.get('accuracy'))}"
        )

    lines.append("")
    return "\n".join(lines)
