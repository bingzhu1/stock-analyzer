"""
services/inspect_analysis.py

查验分析 MVP — 对"当前这类情况，历史上准不准"进行最小反查。

Public API
----------
inspect_by_consistency(symbol, window) -> dict
    按一致性分组：
      consistent_stats   — consistency_passed==True 子集的统计
      inconsistent_stats — consistency_passed==False 或有冲突的子集
    含 top1_hit_rate / exclusion_hit_rate / sample_count

inspect_with_filter(symbol, window, **filters) -> dict
    任意条件过滤（consistency、direction、confidence、exclusion_action）

inspect_current(current_snapshot, symbol, window) -> dict
    传入当前推演的关键字段，自动匹配历史相似情况

核心数据结构（每条 joined record）
----------------------------------
prediction_for_date     str         目标日期
predicted_state         str         五状态预测
actual_state            str|None    实际五状态
state_match             bool|None   Top1 是否命中
direction               str|None    偏多 / 偏空 / 中性
direction_correct       bool|None   方向是否正确
confidence              str|None    high / medium / low
exclusion_action        str|None    allow / exclude
exclusion_triggered_rule str|None   规则名
exclusion_hit           bool|None   排除是否命中
consistency_passed      bool|None   一致性校验是否通过
consistency_conflicts   list[str]   冲突描述列表
actual_close_change_pct float|None  实际涨跌幅（%）

输出结构（所有公开函数共用 _make_stats_block 基础形状）
-------------------------------------------------------
sample_count        int         有效配对样本数
top1_hit_rate       float|None  Top1 命中率
top1_hit_count      int         Top1 命中次数
exclusion_total     int         排除层触发次数
exclusion_hit_rate  float|None  排除命中率
exclusion_hit_count int         排除命中次数
exclusion_miss_rate float|None  误杀率
exclusion_miss_count int        误杀次数
summary             str         中文摘要
notes               list[str]   补充说明
warnings            list[str]   非致命问题
"""

from __future__ import annotations

from typing import Any

from services.log_store import read_outcome_log, read_prediction_log

_ALL_STATES  = frozenset(("大涨", "小涨", "震荡", "小跌", "大跌"))
_DEFAULT_WIN = 20


# ── join ─────────────────────────────────────────────────────────────────────

def _safe_bool(v: Any) -> bool | None:
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, int):
        return bool(v)
    return None


def _exclusion_hit(rule: str | None, actual: str | None) -> bool | None:
    if not rule or not actual:
        return None
    if rule == "exclude_big_up":
        return actual != "大涨"
    if rule == "exclude_big_down":
        return actual != "大跌"
    return None


def _join_full(symbol: str, window: int) -> tuple[list[dict[str, Any]], list[str]]:
    """
    Join prediction_log + outcome_log.
    Returns (records, warnings).

    Includes consistency_passed + consistency_conflicts (not in review_center).
    Returns newest-first, clipped to *window* paired records.
    """
    warnings: list[str] = []

    preds    = read_prediction_log(symbol=symbol, limit=window * 5)
    outcomes = read_outcome_log(limit=window * 5)

    out_by_pid: dict[str, dict] = {}
    for o in outcomes:
        pid = o.get("prediction_log_id")
        if pid and pid not in out_by_pid:
            out_by_pid[pid] = o

    paired: list[dict[str, Any]] = []
    unpaired = 0
    for p in preds:
        pid = p.get("log_id")
        if not pid:
            continue
        o = out_by_pid.get(pid)
        if o is None:
            unpaired += 1
            continue

        actual  = o.get("actual_state")
        rule    = p.get("exclusion_triggered_rule")
        paired.append({
            "prediction_for_date":      p.get("prediction_for_date"),
            "predicted_state":          p.get("predicted_state"),
            "actual_state":             actual,
            "state_match":              _safe_bool(o.get("state_match")),
            "direction":                p.get("direction"),
            "direction_correct":        _safe_bool(o.get("direction_correct")),
            "confidence":               p.get("confidence"),
            "exclusion_action":         p.get("exclusion_action"),
            "exclusion_triggered_rule": rule,
            "exclusion_hit":            _exclusion_hit(rule, actual),
            "consistency_passed":       _safe_bool(p.get("consistency_passed")),
            "consistency_conflicts":    p.get("consistency_conflicts") or [],
            "actual_close_change_pct":  o.get("actual_close_change_pct"),
        })
        if len(paired) >= window:
            break

    if unpaired:
        warnings.append(
            f"{unpaired} 条推演暂无结果数据（outcome 未写入或 prediction_log_id 不匹配）。"
        )
    if not paired:
        warnings.append("没有找到同时有推演和结果的配对记录，无法生成查验分析。")
    return paired, warnings


# ── stats engine ─────────────────────────────────────────────────────────────

def _pct(num: int, den: int) -> float | None:
    return round(num / den, 4) if den else None


def _make_stats_block(
    records: list[dict[str, Any]],
    *,
    label: str = "",
) -> dict[str, Any]:
    """Compute the standard stats block from a list of joined records."""
    n = len(records)
    if n == 0:
        return {
            "sample_count":        0,
            "top1_hit_rate":       None,
            "top1_hit_count":      0,
            "exclusion_total":     0,
            "exclusion_hit_rate":  None,
            "exclusion_hit_count": 0,
            "exclusion_miss_rate": None,
            "exclusion_miss_count":0,
            "label":               label,
        }

    top1_hits = sum(1 for r in records if r.get("state_match") is True)

    excl_recs  = [r for r in records if r.get("exclusion_action") == "exclude"]
    excl_hits  = sum(1 for r in excl_recs if r.get("exclusion_hit") is True)
    excl_misses= sum(1 for r in excl_recs if r.get("exclusion_hit") is False)
    excl_judged = excl_hits + excl_misses

    return {
        "sample_count":        n,
        "top1_hit_rate":       _pct(top1_hits, n),
        "top1_hit_count":      top1_hits,
        "exclusion_total":     len(excl_recs),
        "exclusion_hit_rate":  _pct(excl_hits, excl_judged),
        "exclusion_hit_count": excl_hits,
        "exclusion_miss_rate": _pct(excl_misses, excl_judged),
        "exclusion_miss_count":excl_misses,
        "label":               label,
    }


def _fmt_rate(rate: float | None) -> str:
    return f"{rate * 100:.1f}%" if rate is not None else "—"


def _summary_for_block(block: dict[str, Any], context: str = "") -> str:
    n    = block["sample_count"]
    r1   = _fmt_rate(block["top1_hit_rate"])
    excl = block["exclusion_total"]
    rexc = _fmt_rate(block["exclusion_hit_rate"])
    label = block.get("label") or context
    if n == 0:
        return f"{label}：样本为空，无法计算。"
    excl_part = f"，排除命中率 {rexc}（{block['exclusion_hit_count']}/{excl} 次触发）" if excl else ""
    return f"{label}（n={n}）：Top1 命中率 {r1}（{block['top1_hit_count']}/{n}）{excl_part}。"


# ── public API ────────────────────────────────────────────────────────────────

def inspect_by_consistency(
    symbol: str = "AVGO",
    window: int = _DEFAULT_WIN,
) -> dict[str, Any]:
    """
    按一致性校验结果分组，分别计算统计。

    三项核心指标：
      1. 一致样本主推演准确率  → consistent_stats.top1_hit_rate
      2. 不一致样本主推演准确率 → inconsistent_stats.top1_hit_rate
      3. 不一致样本排除命中率  → inconsistent_stats.exclusion_hit_rate

    consistent    : consistency_passed == True
    inconsistent  : consistency_passed == False 或 None（含校验未运行）
    unknown       : consistency_passed 字段缺失（单独统计，辅助诊断）
    """
    records, warnings = _join_full(symbol, window)
    notes: list[str] = []

    consistent   = [r for r in records if r.get("consistency_passed") is True]
    inconsistent = [r for r in records if r.get("consistency_passed") is False]
    unknown      = [r for r in records if r.get("consistency_passed") is None]

    if unknown:
        notes.append(
            f"{len(unknown)} 条记录缺少 consistency_passed 字段"
            "（可能是旧日志或校验层未运行），已单独归类为 unknown，不计入一致 / 不一致统计。"
        )
    if not consistent and not inconsistent:
        warnings.append("所有记录均缺少一致性字段，无法按一致性分组。")

    c_block  = _make_stats_block(consistent,   label="一致样本")
    ic_block = _make_stats_block(inconsistent, label="不一致样本")
    u_block  = _make_stats_block(unknown,      label="一致性未知样本")

    summary_parts = [_summary_for_block(c_block), _summary_for_block(ic_block)]
    if unknown:
        summary_parts.append(_summary_for_block(u_block))
    summary = "  ".join(summary_parts)

    # 诊断建议
    if c_block["top1_hit_rate"] is not None and ic_block["top1_hit_rate"] is not None:
        diff = c_block["top1_hit_rate"] - ic_block["top1_hit_rate"]
        if diff > 0.1:
            notes.append(
                f"一致样本命中率比不一致样本高 {diff*100:.1f}pp，"
                "建议在 orchestrator 中对不一致情况加注警告或降低置信度。"
            )
        elif diff < -0.1:
            notes.append(
                f"不一致样本命中率反而比一致样本高 {-diff*100:.1f}pp，"
                "可能说明一致性校验规则需要重新校准。"
            )

    return {
        "symbol":             symbol,
        "window":             window,
        "total_sample_count": len(records),
        "consistent_stats":   c_block,
        "inconsistent_stats": ic_block,
        "unknown_stats":      u_block,
        "summary":            summary,
        "notes":              notes,
        "warnings":           warnings,
    }


def inspect_with_filter(
    symbol: str = "AVGO",
    window: int = _DEFAULT_WIN,
    *,
    consistency: bool | None = None,        # True/False/None = any
    direction: str | None = None,           # "偏多" / "偏空" / "中性" / None = any
    confidence: str | None = None,          # "high" / "medium" / "low" / None = any
    exclusion_action: str | None = None,    # "allow" / "exclude" / None = any
) -> dict[str, Any]:
    """
    任意条件过滤后计算统计。条件为 None 表示不过滤该维度（AND 组合）。

    Parameters
    ----------
    symbol          : 标的，默认 "AVGO"
    window          : 最多取最近 window 条配对记录
    consistency     : True = 仅一致样本；False = 仅不一致；None = 全部
    direction       : 方向过滤（"偏多" / "偏空" / "中性"）
    confidence      : 置信度过滤
    exclusion_action: 排除层结果过滤

    Returns
    -------
    dict with sample_count, top1_hit_rate, exclusion_hit_rate,
    summary, notes, warnings.
    """
    records, warnings = _join_full(symbol, window)

    # Apply filters
    if consistency is not None:
        records = [r for r in records if r.get("consistency_passed") is consistency]
    if direction is not None:
        records = [r for r in records if r.get("direction") == direction]
    if confidence is not None:
        records = [r for r in records if r.get("confidence") == confidence]
    if exclusion_action is not None:
        records = [r for r in records if r.get("exclusion_action") == exclusion_action]

    # Build filter description for summary
    filter_parts: list[str] = []
    if consistency is not None:
        filter_parts.append("一致" if consistency else "不一致")
    if direction:
        filter_parts.append(direction)
    if confidence:
        filter_parts.append({"high": "高置信度", "medium": "中置信度", "low": "低置信度"}.get(confidence, confidence))
    if exclusion_action:
        filter_parts.append("排除层触发" if exclusion_action == "exclude" else "排除层未触发")
    filter_desc = "、".join(filter_parts) if filter_parts else "全部"

    block = _make_stats_block(records, label=filter_desc)
    summary = _summary_for_block(block)

    notes: list[str] = []
    if block["sample_count"] < 5:
        notes.append(f"当前过滤条件下样本数仅 {block['sample_count']} 条，结论置信度较低。")

    return {
        "symbol":               symbol,
        "window":               window,
        "filter_desc":          filter_desc,
        **block,
        "summary":              summary,
        "notes":                notes,
        "warnings":             warnings,
    }


def inspect_current(
    current_snapshot: dict[str, Any],
    symbol: str = "AVGO",
    window: int = _DEFAULT_WIN,
) -> dict[str, Any]:
    """
    以当前推演的关键特征为输入，找历史上"类似情况"的准确率。

    current_snapshot 可包含（缺失字段不参与过滤）：
      consistency_passed   bool       一致性是否通过
      consistency_flag     str        "consistent" / "mixed" / "conflict"
      direction            str        "偏多" / "偏空" / "中性"
      confidence           str        "high" / "medium" / "low"
      exclusion_action     str        "allow" / "exclude"

    匹配规则（优先级从高到低，逐渐放宽）：
      Level 1：全字段匹配（最严格）
      Level 2：仅 consistency + direction 匹配
      Level 3：仅 consistency 匹配
      Level 4：全部记录（兜底）
    """
    records, warnings = _join_full(symbol, window)
    notes: list[str] = []

    # Extract filter params from snapshot
    snap_consistency = _safe_bool(current_snapshot.get("consistency_passed"))
    snap_flag        = str(current_snapshot.get("consistency_flag") or "").strip()
    snap_direction   = str(current_snapshot.get("direction") or "").strip() or None
    snap_confidence  = str(current_snapshot.get("confidence") or "").strip() or None
    snap_excl_action = str(current_snapshot.get("exclusion_action") or "").strip() or None

    # Derive consistency_passed from flag if not directly available
    if snap_consistency is None and snap_flag in ("consistent",):
        snap_consistency = True
    elif snap_consistency is None and snap_flag in ("conflict",):
        snap_consistency = False

    def _apply(recs, *, cons, direction, confidence, excl):
        out = list(recs)
        if cons is not None:
            out = [r for r in out if r.get("consistency_passed") is cons]
        if direction:
            out = [r for r in out if r.get("direction") == direction]
        if confidence:
            out = [r for r in out if r.get("confidence") == confidence]
        if excl:
            out = [r for r in out if r.get("exclusion_action") == excl]
        return out

    level1 = _apply(records, cons=snap_consistency, direction=snap_direction,
                    confidence=snap_confidence, excl=snap_excl_action)
    level2 = _apply(records, cons=snap_consistency, direction=snap_direction,
                    confidence=None, excl=None)
    level3 = _apply(records, cons=snap_consistency, direction=None,
                    confidence=None, excl=None)

    # Choose most specific level with at least 3 samples
    if len(level1) >= 3:
        selected, match_level = level1, "全字段匹配"
    elif len(level2) >= 3:
        selected, match_level = level2, "一致性+方向匹配"
        notes.append("全字段匹配样本不足 3 条，已放宽至仅匹配一致性 + 方向。")
    elif len(level3) >= 3:
        selected, match_level = level3, "仅一致性匹配"
        notes.append("进一步放宽条件，仅按一致性过滤。")
    else:
        selected, match_level = records, "兜底（全部记录）"
        notes.append("条件匹配样本不足，已使用全部记录作为参考。请谨慎解读结论。")

    block   = _make_stats_block(selected, label=match_level)
    summary = _summary_for_block(block, context=f"当前情况历史类比（{match_level}）")

    if block["sample_count"] < 5:
        notes.append(f"参考样本仅 {block['sample_count']} 条，置信度较低。")

    return {
        "symbol":       symbol,
        "window":       window,
        "match_level":  match_level,
        "filter_used": {
            "consistency_passed": snap_consistency,
            "direction":          snap_direction,
            "confidence":         snap_confidence,
            "exclusion_action":   snap_excl_action,
        },
        **block,
        "summary":      summary,
        "notes":        notes,
        "warnings":     warnings,
    }
