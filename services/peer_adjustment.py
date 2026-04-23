"""Independent projection v2 peer adjustment layer.

This module only turns existing scanner peer summaries into a stable Step 2
adjustment. It does not fetch peer data or change scanner / predict rules.
"""

from __future__ import annotations

from typing import Any


DEFAULT_PEER_SYMBOLS = ["NVDA", "SOXX", "QQQ"]
_MISSING_VALUES = {"", "none", "null", "unavailable"}


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _clean_label(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() in _MISSING_VALUES else text.lower()


def _confidence_down(confidence: str) -> str:
    return {"high": "medium", "medium": "low", "low": "low"}.get(confidence, "unknown")


def _confidence_up(confidence: str) -> str:
    return {"low": "medium", "medium": "high", "high": "high"}.get(confidence, "unknown")


def _primary_direction(primary_analysis: dict[str, Any]) -> str:
    direction = str(primary_analysis.get("direction") or "unknown").strip()
    return direction if direction in {"偏多", "偏空", "中性"} else "unknown"


def _primary_confidence(primary_analysis: dict[str, Any]) -> str:
    confidence = str(primary_analysis.get("confidence") or "unknown").strip().lower()
    return confidence if confidence in {"high", "medium", "low"} else "unknown"


def _snapshot(peer_snapshot: dict[str, Any] | None) -> dict[str, Any]:
    source = _as_dict(peer_snapshot)
    return {
        "confirmation_state": source.get("confirmation_state"),
        "relative_strength_5d_summary": _as_dict(
            source.get("relative_strength_5d_summary")
            or source.get("relative_strength_summary")
        ),
        "relative_strength_same_day_summary": _as_dict(
            source.get("relative_strength_same_day_summary")
        ),
    }


def _has_peer_data(snapshot: dict[str, Any], peer_symbols: list[str]) -> bool:
    for source_key in ("relative_strength_5d_summary", "relative_strength_same_day_summary"):
        summary = _as_dict(snapshot.get(source_key))
        for peer in peer_symbols:
            if _clean_label(summary.get(f"vs_{peer.lower()}")):
                return True
    return False


def _vote_for_layer(primary_direction: str, relative_strength: str) -> str:
    if not relative_strength:
        return "missing"
    if relative_strength == "neutral":
        return "neutral"
    if primary_direction == "偏多":
        if relative_strength == "stronger":
            return "confirm"
        if relative_strength == "weaker":
            return "oppose"
    if primary_direction == "偏空":
        if relative_strength == "weaker":
            return "confirm"
        if relative_strength == "stronger":
            return "oppose"
    return "mixed"


def _combine_votes(votes: set[str]) -> str:
    directional = votes - {"missing"}
    if not directional:
        return "missing"
    if "confirm" in directional and "oppose" in directional:
        return "mixed"
    if "confirm" in directional:
        return "confirm"
    if "oppose" in directional:
        return "oppose"
    if directional == {"neutral"}:
        return "neutral"
    return "mixed"


def _peer_votes(
    *,
    primary_direction: str,
    snapshot: dict[str, Any],
    peer_symbols: list[str],
) -> tuple[list[dict[str, str]], int, int, int, int]:
    rs_5d = _as_dict(snapshot.get("relative_strength_5d_summary"))
    rs_day = _as_dict(snapshot.get("relative_strength_same_day_summary"))
    rows: list[dict[str, str]] = []
    confirm_count = 0
    oppose_count = 0
    mixed_count = 0
    neutral_count = 0

    for peer in peer_symbols:
        key = f"vs_{peer.lower()}"
        five_day = _clean_label(rs_5d.get(key)) or "unavailable"
        same_day = _clean_label(rs_day.get(key)) or "unavailable"
        peer_vote = _combine_votes({
            _vote_for_layer(primary_direction, "" if five_day == "unavailable" else five_day),
            _vote_for_layer(primary_direction, "" if same_day == "unavailable" else same_day),
        })
        if peer_vote == "confirm":
            confirm_count += 1
        elif peer_vote == "oppose":
            oppose_count += 1
        elif peer_vote == "mixed":
            mixed_count += 1
        elif peer_vote == "neutral":
            neutral_count += 1
        rows.append({
            "peer": peer,
            "five_day": five_day,
            "same_day": same_day,
            "vote": peer_vote,
        })
    return rows, confirm_count, oppose_count, mixed_count, neutral_count


def _basis(rows: list[dict[str, str]], confirm_count: int, oppose_count: int, mixed_count: int, neutral_count: int) -> list[str]:
    lines = [
        f"{row['peer']}: 5日={row['five_day']}, 当日={row['same_day']}, vote={row['vote']}"
        for row in rows
    ]
    lines.append(
        f"peer votes: confirm={confirm_count}, oppose={oppose_count}, mixed={mixed_count}, neutral={neutral_count}."
    )
    return lines


def _missing_result(
    *,
    symbol: str,
    peer_symbols: list[str],
    primary_direction: str,
    primary_confidence: str,
    snapshot: dict[str, Any],
    warning: str,
    summary: str = "未获 peers 确认，peer_adjustment 已降级。",
) -> dict[str, Any]:
    return {
        "kind": "peer_adjustment",
        "symbol": symbol,
        "peer_symbols": peer_symbols,
        "ready": False,
        "confirmation_level": "missing",
        "adjustment": "missing",
        "adjusted_direction": primary_direction,
        "adjusted_confidence": primary_confidence,
        "summary": summary,
        "basis": ["未获 peers 确认。"],
        "warnings": [warning],
        "peer_snapshot": snapshot,
    }


def build_peer_adjustment(
    *,
    primary_analysis: dict[str, Any],
    peer_snapshot: dict[str, Any] | None = None,
    symbol: str = "AVGO",
    peer_symbols: list[str] | None = None,
) -> dict[str, Any]:
    """Build a stable NVDA / SOXX / QQQ adjustment around primary_analysis."""
    normalized_symbol = str(symbol or "AVGO").strip().upper() or "AVGO"
    normalized_peers = list(peer_symbols or DEFAULT_PEER_SYMBOLS)
    snapshot = _snapshot(peer_snapshot)
    primary = _as_dict(primary_analysis)
    primary_direction = _primary_direction(primary)
    primary_confidence = _primary_confidence(primary)

    if not primary.get("ready") or primary_direction == "unknown":
        return {
            "kind": "peer_adjustment",
            "symbol": normalized_symbol,
            "peer_symbols": normalized_peers,
            "ready": False,
            "confirmation_level": "unknown",
            "adjustment": "unknown",
            "adjusted_direction": "unknown",
            "adjusted_confidence": "unknown",
            "summary": "主分析不可用，peer_adjustment 不能形成完整修正。",
            "basis": ["primary_analysis 不可用。"],
            "warnings": ["peer_adjustment 不可用：缺少可用 primary_analysis。"],
            "peer_snapshot": snapshot,
        }

    if not _has_peer_data(snapshot, normalized_peers):
        return _missing_result(
            symbol=normalized_symbol,
            peer_symbols=normalized_peers,
            primary_direction=primary_direction,
            primary_confidence=primary_confidence,
            snapshot=snapshot,
            warning="peer_adjustment 缺少 NVDA / SOXX / QQQ 可用对照数据。",
        )

    rows, confirm_count, oppose_count, mixed_count, neutral_count = _peer_votes(
        primary_direction=primary_direction,
        snapshot=snapshot,
        peer_symbols=normalized_peers,
    )

    adjusted_direction = primary_direction
    adjusted_confidence = primary_confidence
    confirmation_level = "partial"
    adjustment = "no_change"

    if primary_direction in {"偏多", "偏空"}:
        if confirm_count >= 2:
            confirmation_level = "confirmed"
            adjustment = "reinforce_bullish" if primary_direction == "偏多" else "reinforce_bearish"
            adjusted_confidence = _confidence_up(primary_confidence)
        elif oppose_count >= 2:
            confirmation_level = "weak"
            adjustment = "downgrade"
            adjusted_confidence = _confidence_down(primary_confidence)
            if primary_confidence == "low":
                adjusted_direction = "中性"
        else:
            confirmation_level = "partial"
            adjustment = "downgrade" if mixed_count or oppose_count else "no_change"
            adjusted_confidence = _confidence_down(primary_confidence) if adjustment == "downgrade" else primary_confidence
    else:
        confirmation_level = "partial"
        adjustment = "no_change"
        adjusted_direction = "中性"
        adjusted_confidence = primary_confidence

    if adjustment == "reinforce_bullish":
        summary = "peers 支持主分析偏多，修正为强化偏多。"
    elif adjustment == "reinforce_bearish":
        summary = "peers 支持主分析偏空，修正为强化偏空。"
    elif adjustment == "downgrade":
        summary = "peers 未充分确认主分析方向，peer_adjustment 已下调置信度。"
    else:
        summary = "peers 未改变主分析方向，peer_adjustment 保持 no_change。"

    return {
        "kind": "peer_adjustment",
        "symbol": normalized_symbol,
        "peer_symbols": normalized_peers,
        "ready": True,
        "confirmation_level": confirmation_level,
        "adjustment": adjustment,
        "adjusted_direction": adjusted_direction,
        "adjusted_confidence": adjusted_confidence,
        "summary": summary,
        "basis": _basis(rows, confirm_count, oppose_count, mixed_count, neutral_count),
        "warnings": [],
        "peer_snapshot": snapshot,
    }
