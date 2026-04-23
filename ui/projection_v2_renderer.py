from __future__ import annotations

from typing import Any


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _clean_lines(lines: list[str]) -> list[str]:
    return [str(line) for line in lines if str(line).strip()]


def _format_rate(value: Any) -> str:
    try:
        if value is None:
            return "n/a"
        rate = float(value)
    except (TypeError, ValueError):
        return "n/a"
    if rate > 1 and rate <= 100:
        rate = rate / 100
    if rate < 0 or rate > 1:
        return "n/a"
    return f"{rate * 100:.1f}%"


def _rule_line(rule: Any) -> str:
    if isinstance(rule, dict):
        message = str(rule.get("message") or "").strip()
        title = str(rule.get("title") or "").strip()
        rule_id = str(rule.get("rule_id") or "").strip()
        category = str(rule.get("category") or "").strip()
        parts = [part for part in (message, title, rule_id, category) if part]
        return f"命中规则：{' / '.join(parts)}" if parts else "命中规则：未提供详情。"
    text = str(rule).strip()
    return f"命中规则：{text}" if text else "命中规则：未提供详情。"


def build_projection_v2_display(v2_raw: dict[str, Any] | None) -> dict[str, list[str]]:
    v2 = _as_dict(v2_raw)
    preflight = _as_dict(v2.get("preflight"))
    primary = _as_dict(v2.get("primary_analysis"))
    peer = _as_dict(v2.get("peer_adjustment"))
    historical = _as_dict(v2.get("historical_probability"))
    final = _as_dict(v2.get("final_decision"))
    trace = _as_list(v2.get("trace"))

    final_direction = str(final.get("final_direction") or final.get("direction") or "unknown")
    final_confidence = str(final.get("final_confidence") or final.get("confidence") or "unknown")
    risk_level = str(final.get("risk_level") or "unknown")
    final_summary = str(final.get("summary") or "最终结论暂不可用。")
    why_not_more = str(
        final.get("why_not_more_bullish_or_bearish")
        or "当前没有额外的方向约束说明。"
    )

    conclusion = [
        f"最终方向：{final_direction}",
        f"最终置信度：{final_confidence}",
        f"风险等级：{risk_level}",
        f"最终摘要：{final_summary}",
        f"为什么不是更偏多/偏空：{why_not_more}",
    ]

    evidence: list[str] = []

    matched_rules = _as_list(preflight.get("matched_rules"))
    matched_rule_count = len(matched_rules)
    evidence.append(
        "Step 0 历史规则前置："
        + str(preflight.get("summary") or "未接入可用 preflight 信息。")
    )
    evidence.append(f"命中规则数：{matched_rule_count}")
    for rule in matched_rules:
        evidence.append(_rule_line(rule))
    for warning in _as_list(preflight.get("rule_warnings")):
        text = str(warning).strip()
        if text:
            evidence.append(f"规则提醒：{text}")

    preflight_influence = _as_dict(final.get("preflight_influence"))
    influence_summary = str(preflight_influence.get("summary") or "").strip()
    if influence_summary:
        evidence.append(f"规则影响：{influence_summary}")

    evidence.append(
        "Step 1 最近20天主分析："
        + str(primary.get("summary") or "主分析未返回摘要。")
    )
    evidence.append(
        "主分析标签："
        f"direction={primary.get('direction', 'unknown')} / "
        f"confidence={primary.get('confidence', 'unknown')} / "
        f"position={primary.get('position_label', '—')} / "
        f"stage={primary.get('stage_label', '—')} / "
        f"volume={primary.get('volume_state', '—')}"
    )
    for item in _as_list(primary.get("basis")):
        text = str(item).strip()
        if text:
            evidence.append(f"主分析依据：{text}")

    evidence.append(
        "Step 2 peers 修正："
        + str(peer.get("summary") or "未获得 peers 修正摘要。")
    )
    evidence.append(
        "peers 状态："
        f"confirmation={peer.get('confirmation_level', 'unknown')} / "
        f"adjustment={peer.get('adjustment', 'unknown')} / "
        f"adjusted_direction={peer.get('adjusted_direction', '—')} / "
        f"adjusted_confidence={peer.get('adjusted_confidence', '—')}"
    )
    for item in _as_list(peer.get("basis")):
        text = str(item).strip()
        if text:
            evidence.append(f"peers 依据：{text}")

    combined = _as_dict(historical.get("combined_probability"))
    code_match = _as_dict(historical.get("code_match"))
    window_similarity = _as_dict(historical.get("window_similarity"))
    evidence.append(
        "Step 3 历史概率层："
        + str(historical.get("summary") or "历史概率层未返回摘要。")
    )
    evidence.append(
        "历史概率："
        f"sample_count={historical.get('sample_count', 0)} / "
        f"sample_quality={historical.get('sample_quality', 'missing')} / "
        f"historical_bias={historical.get('historical_bias', 'missing')} / "
        f"impact={historical.get('impact', 'missing')}"
    )
    evidence.append(
        "combined_probability："
        f"method={combined.get('method', 'fallback')} / "
        f"up_rate={_format_rate(combined.get('up_rate'))} / "
        f"down_rate={_format_rate(combined.get('down_rate'))} / "
        f"gap_up_rate={_format_rate(combined.get('gap_up_rate'))} / "
        f"strong_close_rate={_format_rate(combined.get('strong_close_rate'))}"
    )
    evidence.append(f"code_match：{code_match.get('summary', '同编码层暂无摘要。')}")
    evidence.append(
        "window_similarity："
        f"{window_similarity.get('summary', '相似窗口层暂无摘要。')}"
    )

    evidence.append("Step 4 最终结论：" + final_summary)
    for item in _as_list(final.get("decision_factors")):
        text = str(item).strip()
        if text:
            evidence.append(f"决策因素：{text}")

    layer_contributions = _as_dict(final.get("layer_contributions"))
    for key in ("primary", "peer", "historical", "preflight"):
        text = str(layer_contributions.get(key) or "").strip()
        if text:
            evidence.append(f"层贡献[{key}]：{text}")

    for item in trace:
        if not isinstance(item, dict):
            continue
        step = str(item.get("step") or "unknown")
        status = str(item.get("status") or "unknown")
        message = str(item.get("message") or "").strip()
        line = f"trace：{step} / {status}"
        if message:
            line += f" / {message}"
        evidence.append(line)

    warnings: list[str] = []
    for source in (v2, preflight, primary, peer, historical, final):
        for warning in _as_list(_as_dict(source).get("warnings")):
            text = str(warning).strip()
            if text:
                warnings.append(text)

    return {
        "conclusion": _clean_lines(conclusion),
        "evidence": _clean_lines(evidence),
        "warnings": _clean_lines(list(dict.fromkeys(warnings))),
    }
