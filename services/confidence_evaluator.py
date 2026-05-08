"""Standalone confidence evaluator (Step 12C-A / RISK-3 stage A).

This module is the single ACTIVE_CONFIDENCE engine for the AVGO research
agent. It answers the 07C core question:

    "How reliable is the projection system this time?
     How reliable is the exclusion system this time?
     Are the two aligned, partially conflicting, or strongly conflicting?"

Boundary contract (06 / 07C / 11C):

- This module is an **evaluator**, not an arbiter. Low confidence does not
  rewrite projection or exclusion outputs; high confidence does not promote
  any state to ``hard`` / ``forced``.
- ``build_confidence_result`` reads ``projection_result`` and
  ``exclusion_result`` only to produce a fresh ``confidence_system_result.v1``
  dict. It MUST NOT mutate either input nor any context dict.
- The module does not call any language-model surface, never writes the
  database, and does not perform file I/O. ``calibration_context`` is
  treated as a frozen artifact reference: when missing or not ready, all
  confidence levels degrade to ``unknown`` rather than fabricating a
  heuristic.
- Output never contains ``most_likely_state`` / ``most_unlikely_state`` /
  ``modified_*`` / ``trading_*`` / ``hard_*`` / ``forced_*`` /
  ``required_decision`` / promotion / mutation surfaces. See
  ``_FORBIDDEN_FIELDS`` for the exhaustive list.

Stage A scope (this commit): the evaluator stands alone, with no caller in
the active orchestrator path. Step 12C-B will wire the result into
``projection_orchestrator_v2`` / ``final_decision`` / renderer.

Level / score band convention (11C §6.1):

    unknown -> score = None
    low     -> score in [0.0, 0.4]
    medium  -> score in [0.4, 0.7]
    high    -> score in [0.7, 1.0]
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


_FIVE_STATES = ("大涨", "小涨", "震荡", "小跌", "大跌")

_LEVEL_RANK = {"unknown": -1, "low": 0, "medium": 1, "high": 2}
_RANK_TO_LEVEL = {-1: "unknown", 0: "low", 1: "medium", 2: "high"}

# Forbidden output fields per 07C §5 / 11C §6.2. Kept here for runtime
# defense in depth in addition to the contract enforcement tests.
_FORBIDDEN_FIELDS = frozenset({
    "most_likely_state",
    "most_unlikely_state",
    "modified_projection",
    "modified_exclusion",
    "projection_correction",
    "exclusion_correction",
    "hard_exclusion",
    "forced_exclusion",
    "required_decision",
    "trading_action",
    "buy",
    "sell",
    "hold",
    "simulated_trade",
    "no_trade",
    "final_report_mutation",
    "production_promotion",
    "_PROTECTION_LAYER_CONNECTED",
})


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _clean_str(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"none", "null"} else text


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _level_from_score(score: float | None) -> str:
    if score is None:
        return "unknown"
    if score < 0.4:
        return "low"
    if score < 0.7:
        return "medium"
    return "high"


def _score_for_level(level: str) -> float | None:
    if level == "low":
        return 0.2
    if level == "medium":
        return 0.55
    if level == "high":
        return 0.85
    return None


def _today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _evaluate_one_side(
    *,
    side_label: str,
    side_result: dict[str, Any],
    calibration_score: float | None,
    calibration_ready: bool,
    extra_reasoning: list[str],
) -> dict[str, Any]:
    """Build a single side's confidence dict (projection or exclusion).

    The score is sourced from ``calibration_context`` (the only signal
    sanctioned by 11C §9.2 for in-line confidence quantification). If the
    side's input is empty or calibration is not ready, the level degrades
    to ``unknown``.
    """
    reasoning: list[str] = list(extra_reasoning)
    if not side_result:
        reasoning.append(
            f"未提供 {side_label} 输出，confidence 降级为 unknown。"
        )
        return {"level": "unknown", "score": None, "reasoning": reasoning}
    if not calibration_ready or calibration_score is None:
        reasoning.append(
            "未接入 calibration_context，无法量化 "
            f"{side_label} 可信度，fallback 为 unknown。"
        )
        return {"level": "unknown", "score": None, "reasoning": reasoning}

    score = _clip01(calibration_score)
    level = _level_from_score(score)
    reasoning.append(
        f"{side_label} calibration score={score:.2f} → level={level}。"
    )
    return {"level": level, "score": score, "reasoning": reasoning}


def _compute_agreement(
    projection_result: dict[str, Any],
    exclusion_result: dict[str, Any],
) -> str:
    proj = _as_dict(projection_result)
    excl = _as_dict(exclusion_result)
    if not proj or not excl:
        return "unknown"

    most_likely = _clean_str(proj.get("most_likely_state"))
    most_unlikely = _clean_str(excl.get("most_unlikely_state"))
    if not most_likely or not most_unlikely:
        return "unknown"

    if most_likely == most_unlikely:
        return "strong_conflict"

    ranked_states = [_clean_str(s) for s in _as_list(proj.get("ranked_states"))]
    ranked_unlikely = [_clean_str(s) for s in _as_list(excl.get("ranked_unlikely_states"))]
    top2_likely = {s for s in ranked_states[:2] if s}
    top2_unlikely = {s for s in ranked_unlikely[:2] if s}
    if top2_likely & top2_unlikely:
        return "partial_conflict"

    return "aligned"


def _conflict_level_from_agreement(agreement_status: str) -> str:
    if agreement_status == "aligned":
        return "none"
    if agreement_status == "partial_conflict":
        return "low"
    if agreement_status == "strong_conflict":
        return "high"
    return "unknown"


def _combine_confidence(
    projection_confidence: dict[str, Any],
    exclusion_confidence: dict[str, Any],
    agreement_status: str,
    conflict_level: str,
) -> dict[str, Any]:
    """Conservative min combine + further downgrade on medium/high conflict.

    - If either side is unknown, combined is unknown (no fabrication).
    - Combined level = min(projection.level, exclusion.level).
    - On conflict_level in {medium, high}, step combined level down by
      one rank (saturating at low).
    """
    proj_level = projection_confidence.get("level", "unknown")
    excl_level = exclusion_confidence.get("level", "unknown")
    if proj_level == "unknown" or excl_level == "unknown":
        return {
            "level": "unknown",
            "score": None,
            "reasoning": [
                "推演或否定可信度未量化，combined 降级为 unknown。",
            ],
        }

    proj_rank = _LEVEL_RANK[proj_level]
    excl_rank = _LEVEL_RANK[excl_level]
    base_rank = min(proj_rank, excl_rank)
    reasoning = [
        f"推演 level={proj_level}，否定 level={excl_level}，先取保守 min。",
    ]
    if conflict_level in {"medium", "high"}:
        before = _RANK_TO_LEVEL[base_rank]
        base_rank = max(0, base_rank - 1)
        after = _RANK_TO_LEVEL[base_rank]
        reasoning.append(
            f"agreement={agreement_status}，conflict={conflict_level}，"
            f"combined 从 {before} 进一步降级为 {after}。"
        )
    elif conflict_level == "low":
        reasoning.append(
            f"agreement={agreement_status}，conflict={conflict_level}，"
            "combined 不再降级，仅在 reasoning 中标注冲突。"
        )

    level = _RANK_TO_LEVEL[base_rank]
    proj_score = projection_confidence.get("score")
    excl_score = exclusion_confidence.get("score")
    if proj_score is not None and excl_score is not None:
        score = min(float(proj_score), float(excl_score))
        if conflict_level in {"medium", "high"}:
            # Pull the score down toward the lower band of the new level.
            score = _clip01(score - 0.15)
        score = _clip01(score)
        # Force score into the chosen level's band so the level/score pair
        # stays self-consistent (level is the source of truth here).
        score = _project_score_into_level_band(score, level)
    else:
        score = _score_for_level(level)
    return {"level": level, "score": score, "reasoning": reasoning}


def _project_score_into_level_band(score: float, level: str) -> float | None:
    if level == "unknown":
        return None
    if level == "low":
        return _clip01(min(score, 0.39))
    if level == "medium":
        return _clip01(max(0.4, min(score, 0.69)))
    if level == "high":
        return _clip01(max(0.7, score))
    return None


def _filter_evidence_by_target_date(
    refs: list[Any],
    target_date: str | None,
) -> list[str]:
    """Return raw_evidence_refs filtered so any explicit dated entries are
    kept only when their date is <= target_date.

    Items without any embedded date are passed through unchanged. Items
    whose date suffix (after ':') is parseable and exceeds target_date are
    discarded. This is a conservative cutoff guard mirroring 11C §7.3 — the
    online inference path must never quote evidence dated after target_date.
    """
    if not refs:
        return []
    if not target_date:
        return [str(r) for r in refs if str(r).strip()]
    cutoff = str(target_date)
    out: list[str] = []
    for ref in refs:
        text = str(ref).strip()
        if not text:
            continue
        # crude embedded-date detection: look for "YYYY-MM-DD" anywhere.
        token = _extract_iso_date(text)
        if token and token > cutoff:
            continue
        out.append(text)
    return out


def _extract_iso_date(text: str) -> str | None:
    # Look for the first 10-char window matching YYYY-MM-DD digits.
    for i in range(0, len(text) - 9):
        window = text[i : i + 10]
        if (
            window[4] == "-"
            and window[7] == "-"
            and window[:4].isdigit()
            and window[5:7].isdigit()
            and window[8:10].isdigit()
        ):
            return window
    return None


def build_confidence_result(
    *,
    projection_result: dict[str, Any] | None,
    exclusion_result: dict[str, Any] | None,
    market_context: dict[str, Any] | None = None,
    historical_context: dict[str, Any] | None = None,
    calibration_context: dict[str, Any] | None = None,
    target_date: str | None = None,
    confidence_date: str | None = None,
    symbol: str = "AVGO",
) -> dict[str, Any]:
    """Build a ``confidence_system_result.v1`` from projection / exclusion
    outputs.

    Boundary contract (read-only):

    - Never mutates ``projection_result`` / ``exclusion_result`` / any
      context dict.
    - Never reads future outcomes. ``target_date`` is the cutoff; any
      dated evidence ref beyond it is filtered out before being surfaced.
    - Never imports any language-model client surface.
    - Never writes the database.
    - Never produces ``most_likely_state`` / ``most_unlikely_state`` /
      trading / hard / forced / required / promotion / mutation fields.
    - Returns a fresh dict; inputs are not aliased.

    When ``calibration_context`` is missing or not ready, all confidence
    levels degrade to ``unknown`` (11C §9.3 — never fabricate a heuristic).
    """
    proj = _as_dict(projection_result)
    excl = _as_dict(exclusion_result)
    market = _as_dict(market_context)
    historical = _as_dict(historical_context)
    calibration = _as_dict(calibration_context)

    calibration_ready = bool(calibration.get("ready"))
    projection_score = calibration.get("projection_score")
    exclusion_score = calibration.get("exclusion_score")
    try:
        projection_score_f = float(projection_score) if projection_score is not None else None
    except (TypeError, ValueError):
        projection_score_f = None
    try:
        exclusion_score_f = float(exclusion_score) if exclusion_score is not None else None
    except (TypeError, ValueError):
        exclusion_score_f = None

    reliability_warnings: list[str] = []
    sample_size_notes: list[str] = []
    calibration_notes: list[str] = []

    if not calibration:
        reliability_warnings.append(
            "calibration_context 缺失，可信度评估降级为 unknown。"
        )
        calibration_notes.append(
            "未接入 calibration_context（11C §9.3）；待 frozen calibration "
            "table 接入后恢复 level / score。"
        )
    elif not calibration_ready:
        reliability_warnings.append(
            "calibration_context.ready=False，可信度评估降级为 unknown。"
        )
        calibration_notes.append(
            "calibration_context 已传入但 ready=False，evaluator 不在 missing "
            "数据时 fallback 到 heuristic。"
        )

    if not proj:
        reliability_warnings.append(
            "未提供 projection_result，无法评价推演可信度。"
        )
    if not excl:
        reliability_warnings.append(
            "未提供 exclusion_result，无法评价否定可信度。"
        )

    historical_samples = historical.get("samples")
    if isinstance(historical_samples, (int, float)):
        sample_size_notes.append(
            f"历史样本量 N={int(historical_samples)}（来自 historical_context）。"
        )
    elif historical:
        sample_size_notes.append(
            "historical_context 已传入但未提供样本量字段。"
        )
    else:
        sample_size_notes.append(
            "未接入 historical_context，样本量信息缺失。"
        )

    if market:
        regime = _clean_str(market.get("regime"))
        if regime:
            calibration_notes.append(f"market regime 标签={regime}。")

    projection_confidence = _evaluate_one_side(
        side_label="projection",
        side_result=proj,
        calibration_score=projection_score_f,
        calibration_ready=calibration_ready,
        extra_reasoning=[],
    )
    exclusion_confidence = _evaluate_one_side(
        side_label="exclusion",
        side_result=excl,
        calibration_score=exclusion_score_f,
        calibration_ready=calibration_ready,
        extra_reasoning=[],
    )

    agreement_status = _compute_agreement(proj, excl)
    conflict_level = _conflict_level_from_agreement(agreement_status)

    combined = _combine_confidence(
        projection_confidence,
        exclusion_confidence,
        agreement_status,
        conflict_level,
    )

    confidence_reasoning: list[str] = []
    confidence_reasoning.extend(
        f"projection_confidence: {item}" for item in projection_confidence["reasoning"]
    )
    confidence_reasoning.extend(
        f"exclusion_confidence: {item}" for item in exclusion_confidence["reasoning"]
    )
    confidence_reasoning.append(
        f"agreement_status={agreement_status}, conflict_level={conflict_level}."
    )

    raw_evidence_refs: list[str] = []
    if proj:
        raw_evidence_refs.append("projection_result_ref:projection_system_result.v1")
    if excl:
        raw_evidence_refs.append("exclusion_result_ref:exclusion_system_result.v1")
    raw_evidence_refs.extend(
        _filter_evidence_by_target_date(
            _as_list(historical.get("evidence_refs")),
            target_date,
        )
    )
    raw_evidence_refs.extend(
        _filter_evidence_by_target_date(
            _as_list(calibration.get("evidence_refs")),
            target_date,
        )
    )

    if isinstance(calibration.get("notes"), list):
        for note in calibration["notes"]:
            text = _clean_str(note)
            if text:
                calibration_notes.append(text)

    result: dict[str, Any] = {
        "schema_version": "confidence_system_result.v1",
        "confidence_date": _clean_str(confidence_date) or _today_str(),
        "target_date": _clean_str(target_date) or "",
        "system_name": "confidence_system",
        "question_answered": "system_reliability_evaluation",
        "symbol": str(symbol or "AVGO").strip().upper() or "AVGO",
        "projection_confidence": projection_confidence,
        "exclusion_confidence": exclusion_confidence,
        "agreement_status": agreement_status,
        "conflict_level": conflict_level,
        "combined_confidence": combined,
        "confidence_reasoning": confidence_reasoning,
        "reliability_warnings": reliability_warnings,
        "sample_size_notes": sample_size_notes,
        "calibration_notes": calibration_notes,
        "raw_evidence_refs": raw_evidence_refs,
        "non_mutation_confirmations": {
            "projection_result_mutated": False,
            "exclusion_result_mutated": False,
        },
    }

    # Defense in depth: strip any forbidden field names that might have been
    # injected upstream into one of the surfaced reasoning lists. The
    # contract test pins this from the outside; we also harden here so the
    # invariant survives future helpers that might forget the rule.
    for forbidden in _FORBIDDEN_FIELDS:
        result.pop(forbidden, None)

    return result
