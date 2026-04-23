# -*- coding: utf-8 -*-
"""
services/projection_review_closed_loop.py

Closed-loop: projection v2 snapshot → actual outcome → review → rule candidates.

Public API
----------
save_projection_v2_snapshot(snapshot) -> str
    Persist a projection v2 result snapshot. Returns prediction_id.

build_projection_review(snapshot, actual_outcome) -> dict
    Pure function. Build a structured review from snapshot + actual outcome.
    Does NOT write to DB. Safe to call in tests without DB.

run_projection_review(symbol, prediction_for_date, ...) -> dict
    Orchestration: load snapshot → build review → persist → return review.

Rule candidate format matches Step 0 matched_rules:
    {rule_id, title, category, severity, message}
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from services.prediction_store import (
    get_outcome_for_prediction,
    get_prediction,
    get_prediction_by_date,
    save_prediction,
    save_review,
    update_prediction_status,
)

_FLAT_THRESHOLD = 0.001  # same threshold as outcome_capture

_DIRECTION_MAP = {
    "偏多": "up",
    "偏空": "down",
    "中性": "neutral",
}

_RULE_TEMPLATES: dict[str, dict[str, str]] = {
    "peer_missing": {
        "category": "false_confidence",
        "severity": "high",
        "message": "当 peer 数据缺失时，不应给出 high confidence 结论。",
        "title": "历史复盘提醒：peer 缺失时过度自信",
    },
    "historical_insufficient": {
        "category": "insufficient_data",
        "severity": "medium",
        "message": "当 historical 样本不足时，不应把 final risk 设为 low。",
        "title": "历史复盘提醒：historical 样本不足",
    },
    "peer_downgrade_ignored": {
        "category": "false_confidence",
        "severity": "high",
        "message": "peer 修正已降级时，final 置信度仍保持 high，需要重新评估聚合逻辑。",
        "title": "历史复盘提醒：peer 降级被忽略",
    },
    "primary_wrong_direction": {
        "category": "wrong_direction",
        "severity": "high",
        "message": "主分析方向错误，需要复核 primary 分析层的输入假设。",
        "title": "历史复盘提醒：primary 方向错误",
    },
    "high_confidence_wrong": {
        "category": "false_confidence",
        "severity": "high",
        "message": "高置信度预测出错，高位确认信号存疑时需谨慎对待偏多结论。",
        "title": "历史复盘提醒：高置信度预测方向错误",
    },
}


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_str(value: Any, fallback: str = "unknown") -> str:
    text = str(value or "").strip()
    return text if text else fallback


def _map_predicted_direction(final_direction: str) -> str:
    return _DIRECTION_MAP.get(str(final_direction or "").strip(), "unknown")


def _map_actual_direction(close_change: float | None) -> str:
    if close_change is None:
        return "unknown"
    if close_change > _FLAT_THRESHOLD:
        return "up"
    if close_change < -_FLAT_THRESHOLD:
        return "down"
    return "flat"


def _compute_direction_correct(
    predicted: str, actual: str
) -> bool | None:
    if predicted == "neutral" or actual in ("flat", "unknown"):
        return None
    if predicted == "unknown":
        return None
    return predicted == actual


def _detect_error_layer(
    snapshot: dict[str, Any],
    predicted_direction: str,
    actual_direction: str,
) -> str:
    if predicted_direction == actual_direction:
        return "unknown"
    if predicted_direction == "neutral":
        return "unknown"

    peer = _as_dict(snapshot.get("peer_adjustment"))
    historical = _as_dict(snapshot.get("historical_probability"))
    final = _as_dict(snapshot.get("final_decision"))
    primary = _as_dict(snapshot.get("primary_analysis"))

    final_confidence = _as_str(final.get("final_confidence")).lower()
    peer_ready = peer.get("ready", True)

    hist_summary = str(historical.get("summary") or historical.get("sample_quality") or "")
    if "insufficient" in hist_summary.lower() and final_confidence == "high":
        return "historical"

    if not peer_ready and final_confidence in ("high", "medium"):
        return "peer"

    peer_adjustment_text = str(peer.get("adjustment") or peer.get("summary") or "")
    if ("降" in peer_adjustment_text or "downgrade" in peer_adjustment_text.lower()) \
            and final_confidence == "high":
        return "final"

    primary_dir = str(primary.get("direction") or "")
    if (primary_dir == "偏多" and actual_direction == "down") or \
            (primary_dir == "偏空" and actual_direction == "up"):
        return "primary"

    return "unknown"


def _detect_error_category(
    error_layer: str,
    predicted_direction: str,
    actual_direction: str,
    final_confidence: str,
) -> str:
    if predicted_direction == actual_direction:
        return "correct"
    if predicted_direction in ("neutral", "unknown") or actual_direction in ("flat", "unknown"):
        return "unknown"
    if error_layer in ("peer", "final") and final_confidence == "high":
        return "false_confidence"
    if error_layer == "historical":
        return "insufficient_data"
    if error_layer == "primary":
        return "wrong_direction"
    return "wrong_direction"


def _build_root_cause_summary(
    error_layer: str,
    error_category: str,
    snapshot: dict[str, Any],
    predicted_direction: str,
    actual_direction: str,
) -> str:
    if predicted_direction == actual_direction:
        return "预测方向正确，无需分析根因。"
    if actual_direction == "unknown":
        return "实际结果未知，无法确定根因。"

    peer = _as_dict(snapshot.get("peer_adjustment"))
    historical = _as_dict(snapshot.get("historical_probability"))
    final = _as_dict(snapshot.get("final_decision"))

    final_confidence = _as_str(final.get("final_confidence"))

    if error_layer == "historical":
        hist_summary = str(historical.get("summary") or "")
        return (
            f"historical 层样本不足（{hist_summary[:80]}），"
            f"但 final 层仍给出 {final_confidence} 置信度，导致结论过于乐观。"
        )
    if error_layer == "peer":
        peer_summary = str(peer.get("summary") or "peer 数据不可用")
        return (
            f"peer 层未就绪（{peer_summary[:80]}），"
            f"final 层在无 peer 确认下给出 {final_confidence} 置信度，需降级处理。"
        )
    if error_layer == "final":
        return (
            f"peer 层已降级，但 final 层聚合时仍维持 {final_confidence} 置信度，"
            "聚合逻辑过度乐观，需要重新校准。"
        )
    if error_layer == "primary":
        primary = _as_dict(snapshot.get("primary_analysis"))
        primary_dir = str(primary.get("direction") or "unknown")
        return (
            f"primary 分析方向为 {primary_dir}，与实际方向（{actual_direction}）相反，"
            "primary 层输入假设或信号解读存在问题。"
        )
    return (
        f"预测方向 {predicted_direction} 与实际方向 {actual_direction} 不符，"
        "根因层次暂时无法精确定位。"
    )


def _generate_rule_candidates(
    error_layer: str,
    error_category: str,
    snapshot: dict[str, Any],
    direction_correct: bool | None,
) -> list[dict[str, str]]:
    if direction_correct is True or direction_correct is None:
        return []

    candidates: list[dict[str, str]] = []
    peer = _as_dict(snapshot.get("peer_adjustment"))
    historical = _as_dict(snapshot.get("historical_probability"))
    final = _as_dict(snapshot.get("final_decision"))

    peer_ready = peer.get("ready", True)
    hist_summary = str(historical.get("summary") or historical.get("sample_quality") or "")
    final_confidence = _as_str(final.get("final_confidence")).lower()
    peer_adj_text = str(peer.get("adjustment") or peer.get("summary") or "")

    if not peer_ready:
        tpl = _RULE_TEMPLATES["peer_missing"]
        candidates.append({
            "rule_id": f"review-rc-{uuid.uuid4().hex[:8]}",
            "title": tpl["title"],
            "category": tpl["category"],
            "severity": tpl["severity"],
            "message": tpl["message"],
        })

    if "insufficient" in hist_summary.lower():
        tpl = _RULE_TEMPLATES["historical_insufficient"]
        candidates.append({
            "rule_id": f"review-rc-{uuid.uuid4().hex[:8]}",
            "title": tpl["title"],
            "category": tpl["category"],
            "severity": tpl["severity"],
            "message": tpl["message"],
        })

    if ("降" in peer_adj_text or "downgrade" in peer_adj_text.lower()) \
            and final_confidence == "high":
        tpl = _RULE_TEMPLATES["peer_downgrade_ignored"]
        candidates.append({
            "rule_id": f"review-rc-{uuid.uuid4().hex[:8]}",
            "title": tpl["title"],
            "category": tpl["category"],
            "severity": tpl["severity"],
            "message": tpl["message"],
        })

    if error_layer == "primary":
        tpl = _RULE_TEMPLATES["primary_wrong_direction"]
        candidates.append({
            "rule_id": f"review-rc-{uuid.uuid4().hex[:8]}",
            "title": tpl["title"],
            "category": tpl["category"],
            "severity": tpl["severity"],
            "message": tpl["message"],
        })

    if final_confidence == "high" and direction_correct is False and not candidates:
        tpl = _RULE_TEMPLATES["high_confidence_wrong"]
        candidates.append({
            "rule_id": f"review-rc-{uuid.uuid4().hex[:8]}",
            "title": tpl["title"],
            "category": tpl["category"],
            "severity": tpl["severity"],
            "message": tpl["message"],
        })

    return candidates


def _build_review_notes(
    direction_correct: bool | None,
    error_layer: str,
    error_category: str,
    predicted_direction: str,
    actual_direction: str,
    final_confidence: str,
) -> list[str]:
    notes: list[str] = []
    if direction_correct is True:
        notes.append(f"预测方向正确（预测 {predicted_direction}，实际 {actual_direction}）。")
    elif direction_correct is False:
        notes.append(
            f"预测方向错误（预测 {predicted_direction}，实际 {actual_direction}）。"
        )
        notes.append(f"错误层次初步判断：{error_layer}。")
        notes.append(f"错误分类：{error_category}。")
        if final_confidence in ("high", "medium"):
            notes.append(
                f"最终置信度为 {final_confidence}，与实际结果不符，需关注置信度校准。"
            )
    else:
        notes.append("预测为中性或实际结果变动过小，方向判断不适用。")
    return notes


# ─────────────────────────────────────────────────────────────────────────────
# Public: save snapshot
# ─────────────────────────────────────────────────────────────────────────────

def save_projection_v2_snapshot(snapshot: dict[str, Any]) -> str:
    """
    Persist a projection v2 result snapshot to prediction_log.

    Maps v2 fields into the existing prediction_store schema.
    The full snapshot is stored as predict_result_json for later review.

    Returns the prediction_id (UUID4).
    """
    symbol = str(snapshot.get("symbol") or "AVGO").strip().upper() or "AVGO"
    prediction_for_date = str(snapshot.get("prediction_for_date") or "").strip()
    if not prediction_for_date:
        raise ValueError("snapshot must include 'prediction_for_date'")

    final = _as_dict(snapshot.get("final_decision"))
    final_direction = str(
        snapshot.get("final_direction")
        or final.get("final_direction")
        or final.get("final_bias")
        or "unknown"
    )
    final_confidence = str(
        snapshot.get("final_confidence")
        or final.get("final_confidence")
        or "unknown"
    )

    predict_result = {
        "final_bias": final_direction,
        "final_confidence": final_confidence,
        "risk_level": snapshot.get("risk_level") or final.get("risk_level") or "unknown",
        "preflight": snapshot.get("preflight"),
        "primary_analysis": snapshot.get("primary_analysis"),
        "peer_adjustment": snapshot.get("peer_adjustment"),
        "historical_probability": snapshot.get("historical_probability"),
        "final_decision": snapshot.get("final_decision"),
        "trace": snapshot.get("trace"),
        "_snapshot_kind": "projection_v2",
    }

    return save_prediction(
        symbol=symbol,
        prediction_for_date=prediction_for_date,
        scan_result=None,
        research_result=None,
        predict_result=predict_result,
        snapshot_id=str(snapshot.get("analysis_date") or datetime.now().date().isoformat()),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Public: pure review builder
# ─────────────────────────────────────────────────────────────────────────────

def build_projection_review(
    snapshot: dict[str, Any] | None,
    actual_outcome: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Pure function. Build a structured review from snapshot + actual outcome.

    Supports all degraded scenarios:
    - snapshot is None or missing fields → ready=False, shape stable
    - actual_outcome is None → ready=False, "尚无实际结果，无法复盘"
    - malformed snapshot fields → error_layer=unknown, does not raise

    Returns a stable dict (never raises).
    """
    warnings: list[str] = []

    if snapshot is None:
        warnings.append("找不到 projection snapshot，无法生成 review。")
        return {
            "kind": "projection_review",
            "symbol": "unknown",
            "analysis_date": None,
            "prediction_for_date": None,
            "ready": False,
            "predicted_direction": "unknown",
            "actual_direction": "unknown",
            "direction_correct": None,
            "predicted_confidence": "unknown",
            "actual_summary": {},
            "error_layer": "unknown",
            "error_category": "unknown",
            "root_cause_summary": "snapshot 缺失，无法复盘。",
            "review_notes": [],
            "rule_candidates": [],
            "warnings": warnings,
        }

    symbol = str(snapshot.get("symbol") or "AVGO").strip().upper() or "AVGO"
    analysis_date = snapshot.get("analysis_date")
    prediction_for_date = snapshot.get("prediction_for_date")

    # Extract final decision fields defensively
    final = _as_dict(snapshot.get("final_decision"))
    raw_final_direction = str(
        snapshot.get("final_direction")
        or final.get("final_direction")
        or final.get("final_bias")
        or ""
    ).strip()
    final_confidence = _as_str(
        snapshot.get("final_confidence") or final.get("final_confidence")
    )
    predicted_direction = _map_predicted_direction(raw_final_direction)

    if predicted_direction == "unknown" and raw_final_direction:
        warnings.append(f"final_direction 值无法识别：{raw_final_direction!r}，已降级为 unknown。")

    # Actual outcome
    if actual_outcome is None:
        warnings.append("尚无实际结果，无法复盘。")
        return {
            "kind": "projection_review",
            "symbol": symbol,
            "analysis_date": analysis_date,
            "prediction_for_date": prediction_for_date,
            "ready": False,
            "predicted_direction": predicted_direction,
            "actual_direction": "unknown",
            "direction_correct": None,
            "predicted_confidence": final_confidence,
            "actual_summary": {},
            "error_layer": "unknown",
            "error_category": "unknown",
            "root_cause_summary": "尚无实际结果，无法复盘。",
            "review_notes": ["尚无实际结果，无法复盘。"],
            "rule_candidates": [],
            "warnings": warnings,
        }

    close_change = actual_outcome.get("actual_close_change")
    if close_change is None:
        close_change = actual_outcome.get("close_change")

    actual_direction = _map_actual_direction(
        float(close_change) if close_change is not None else None
    )
    direction_correct = _compute_direction_correct(predicted_direction, actual_direction)

    actual_summary = {
        "actual_open": actual_outcome.get("actual_open"),
        "actual_close": actual_outcome.get("actual_close"),
        "actual_close_change": close_change,
        "open_label": actual_outcome.get("open_label"),
        "close_label": actual_outcome.get("close_label"),
        "path_label": actual_outcome.get("path_label"),
    }

    error_layer = _detect_error_layer(snapshot, predicted_direction, actual_direction)
    error_category = _detect_error_category(
        error_layer, predicted_direction, actual_direction, final_confidence
    )
    root_cause_summary = _build_root_cause_summary(
        error_layer, error_category, snapshot, predicted_direction, actual_direction
    )
    review_notes = _build_review_notes(
        direction_correct, error_layer, error_category,
        predicted_direction, actual_direction, final_confidence,
    )
    rule_candidates = _generate_rule_candidates(
        error_layer, error_category, snapshot, direction_correct
    )

    return {
        "kind": "projection_review",
        "symbol": symbol,
        "analysis_date": analysis_date,
        "prediction_for_date": prediction_for_date,
        "ready": True,
        "predicted_direction": predicted_direction,
        "actual_direction": actual_direction,
        "direction_correct": direction_correct,
        "predicted_confidence": final_confidence,
        "actual_summary": actual_summary,
        "error_layer": error_layer,
        "error_category": error_category,
        "root_cause_summary": root_cause_summary,
        "review_notes": review_notes,
        "rule_candidates": rule_candidates,
        "warnings": warnings,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Public: orchestration entry point
# ─────────────────────────────────────────────────────────────────────────────

def run_projection_review(
    symbol: str,
    prediction_for_date: str,
    *,
    actual_outcome: dict[str, Any] | None = None,
    prediction_id: str | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """
    Load a projection v2 snapshot and generate a review.

    Steps:
      1. Load snapshot from prediction_store (by prediction_id or date)
      2. If actual_outcome not provided, try to load from outcome_log
      3. Build review via build_projection_review()
      4. Persist review to review_log (if persist=True and review is ready)
      5. Return review dict

    Never raises — degraded results have ready=False with warnings.
    """
    snapshot: dict[str, Any] | None = None
    actual: dict[str, Any] | None = actual_outcome

    # Load snapshot
    try:
        if prediction_id:
            row = get_prediction(prediction_id)
        else:
            row = get_prediction_by_date(
                str(symbol or "AVGO").strip().upper() or "AVGO",
                prediction_for_date,
            )
        if row:
            raw_predict = row.get("predict_result_json") or "{}"
            try:
                predict_result = json.loads(raw_predict)
            except (json.JSONDecodeError, TypeError):
                predict_result = {}
            snapshot = {
                "symbol": row.get("symbol"),
                "analysis_date": row.get("analysis_date"),
                "prediction_for_date": row.get("prediction_for_date"),
                "final_direction": predict_result.get("final_bias") or row.get("final_bias"),
                "final_confidence": predict_result.get("final_confidence") or row.get("final_confidence"),
                "risk_level": predict_result.get("risk_level"),
                "preflight": predict_result.get("preflight"),
                "primary_analysis": predict_result.get("primary_analysis"),
                "peer_adjustment": predict_result.get("peer_adjustment"),
                "historical_probability": predict_result.get("historical_probability"),
                "final_decision": predict_result.get("final_decision"),
                "trace": predict_result.get("trace"),
                "_prediction_id": row.get("id"),
            }
            resolved_prediction_id = row.get("id")
        else:
            resolved_prediction_id = prediction_id
    except Exception:
        snapshot = None
        resolved_prediction_id = prediction_id

    # Load actual outcome from DB if not supplied
    if actual is None and resolved_prediction_id:
        try:
            actual = get_outcome_for_prediction(resolved_prediction_id) or None
        except Exception:
            actual = None

    review = build_projection_review(snapshot, actual)

    # Persist if review is ready
    if persist and review.get("ready") and resolved_prediction_id:
        try:
            save_review(
                prediction_id=resolved_prediction_id,
                error_category=review.get("error_category") or "unknown",
                root_cause=review.get("root_cause_summary") or "",
                confidence_note=str(review.get("predicted_confidence") or ""),
                watch_for_next_time="; ".join(
                    c.get("message", "") for c in review.get("rule_candidates", [])
                ),
                review_json=json.dumps(review, ensure_ascii=False),
            )
            update_prediction_status(resolved_prediction_id, "review_generated")
        except Exception:
            review.setdefault("warnings", []).append(
                "review 已生成但持久化失败，请检查 prediction_id 是否有效。"
            )

    return review
