"""
services/review_center.py

复盘中心 MVP — 基于 log_store.py 的 JSONL 日志做最小统计。

Public API
----------
compute_review_stats(symbol, window) -> dict
    主入口：读取最近 window 条有结果的记录，输出四项核心统计。

build_review_detail(symbol, window) -> list[dict]
    逐条明细：按时间倒序返回每条推演的预测 vs 实际对比。

字段说明（compute_review_stats 输出）
--------------------------------------
sample_count          int        有完整结果（prediction + outcome）的样本数
top1_hit_rate         float|None Top1 命中率 = state_match==True 占比
top1_hit_count        int        Top1 命中次数
top2_coverage_rate    float|None Top2 覆盖率（实际结果在前两高概率状态内）
top2_coverage_count   int        Top2 覆盖次数
top2_note             str        Top2 降级说明（有时 state_probabilities 为空）
exclusion_total       int        排除层共触发次数（exclusion_action=="exclude"）
exclusion_hit_rate    float|None 排除命中率（排除的状态确实未发生）
exclusion_hit_count   int        排除命中次数
exclusion_miss_rate   float|None 误杀率（排除的状态其实发生了）
exclusion_miss_count  int        误杀次数
warnings              list[str]  非致命问题说明

五状态映射
----------
大涨 / 小涨  → 多方 (bullish)
震荡         → 中性 (neutral)
小跌 / 大跌  → 空方 (bearish)

排除命中 / 误杀 定义
---------------------
当 exclusion_triggered_rule == "exclude_big_up"：
  命中 = actual_state != "大涨"  （排除有效，大涨未发生）
  误杀 = actual_state == "大涨"  （排除错误，大涨其实发生了）

当 exclusion_triggered_rule == "exclude_big_down"：
  命中 = actual_state != "大跌"
  误杀 = actual_state == "大跌"
"""

from __future__ import annotations

from typing import Any

from services.log_store import read_outcome_log, read_prediction_log

_ALL_STATES = ("大涨", "小涨", "震荡", "小跌", "大跌")
_REVIEW_WINDOW = 20   # default: most recent 20 paired records


# ── helpers ───────────────────────────────────────────────────────────────────

def _top2_states(state_probabilities: dict | None, predicted_state: str | None) -> list[str]:
    """
    Return the two highest-probability states from state_probabilities.
    Falls back to [predicted_state] when the dict is missing or empty.
    """
    probs = state_probabilities if isinstance(state_probabilities, dict) else {}
    # Only consider canonical five states
    valid = {s: float(v) for s, v in probs.items() if s in _ALL_STATES and v is not None}
    if len(valid) >= 2:
        ranked = sorted(valid, key=lambda s: valid[s], reverse=True)
        return ranked[:2]
    if predicted_state and predicted_state in _ALL_STATES:
        return [predicted_state]
    return []


def _exclusion_hit(triggered_rule: str | None, actual_state: str | None) -> bool | None:
    """
    True  → 排除命中（被排除的极端状态确实未发生）
    False → 误杀（被排除的极端状态其实发生了）
    None  → 无法判断（actual_state 缺失）
    """
    if not triggered_rule or not actual_state:
        return None
    if triggered_rule == "exclude_big_up":
        return actual_state != "大涨"
    if triggered_rule in ("exclude_big_down", "exclude_big_down"):
        return actual_state != "大跌"
    # Unknown rule — cannot classify
    return None


def _pct(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator, 4)


def _safe_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    return None


# ── join: prediction + outcome ────────────────────────────────────────────────

def _join_logs(symbol: str, window: int) -> tuple[list[dict[str, Any]], list[str]]:
    """
    Join prediction_log and outcome_log on prediction_log_id.

    Returns (paired_records, warnings).

    Each paired_record contains:
        prediction_for_date, predicted_state, state_probabilities,
        exclusion_action, exclusion_triggered_rule,
        actual_state, state_match, direction_correct
    """
    warnings: list[str] = []

    # Read more predictions than needed; we'll filter to those with outcomes
    preds = read_prediction_log(symbol=symbol, limit=window * 5)
    outcomes = read_outcome_log(limit=window * 5)

    # Index outcomes by prediction_log_id for O(1) lookup
    outcome_by_pred_id: dict[str, dict] = {}
    for o in outcomes:
        pid = o.get("prediction_log_id")
        if pid and pid not in outcome_by_pred_id:
            outcome_by_pred_id[pid] = o

    paired: list[dict[str, Any]] = []
    unpaired = 0
    for pred in preds:
        pred_id = pred.get("log_id")
        if not pred_id:
            continue
        outcome = outcome_by_pred_id.get(pred_id)
        if outcome is None:
            unpaired += 1
            continue
        paired.append({
            "prediction_for_date":      pred.get("prediction_for_date"),
            "predicted_state":          pred.get("predicted_state"),
            "state_probabilities":      pred.get("state_probabilities") or {},
            "direction":                pred.get("direction"),
            "confidence":               pred.get("confidence"),
            "exclusion_action":         pred.get("exclusion_action"),
            "exclusion_triggered_rule": pred.get("exclusion_triggered_rule"),
            "consistency_passed":       pred.get("consistency_passed"),
            "actual_state":             outcome.get("actual_state"),
            "actual_close_change_pct":  outcome.get("actual_close_change_pct"),
            "state_match":              _safe_bool(outcome.get("state_match")),
            "direction_correct":        _safe_bool(outcome.get("direction_correct")),
        })
        if len(paired) >= window:
            break

    if unpaired > 0:
        warnings.append(
            f"{unpaired} 条推演记录暂无结果数据（outcome 尚未写入或 prediction_log_id 未对应）。"
        )
    if not paired:
        warnings.append("没有找到同时有推演和结果的配对记录，无法生成统计。")

    return paired, warnings


# ── public API ────────────────────────────────────────────────────────────────

def compute_review_stats(
    symbol: str = "AVGO",
    window: int = _REVIEW_WINDOW,
) -> dict[str, Any]:
    """
    读取最近 window 条有完整结果的推演，输出四项核心统计。

    Parameters
    ----------
    symbol : str
        目标标的，默认 "AVGO"。
    window : int
        最近 N 条有结果的记录，默认 20。

    Returns
    -------
    dict with fields documented in module docstring.
    """
    paired, warnings = _join_logs(symbol, window)
    n = len(paired)

    if n == 0:
        return {
            "symbol":               symbol,
            "window":               window,
            "sample_count":         0,
            "top1_hit_rate":        None,
            "top1_hit_count":       0,
            "top2_coverage_rate":   None,
            "top2_coverage_count":  0,
            "top2_note":            "样本为空，无法计算。",
            "exclusion_total":      0,
            "exclusion_hit_rate":   None,
            "exclusion_hit_count":  0,
            "exclusion_miss_rate":  None,
            "exclusion_miss_count": 0,
            "warnings":             warnings,
        }

    # ── Top1 命中率 ────────────────────────────────────────────────────────────
    top1_hits = sum(1 for r in paired if r["state_match"] is True)
    top1_rate = _pct(top1_hits, n)

    # ── Top2 覆盖率 ────────────────────────────────────────────────────────────
    top2_hits = 0
    top2_degraded = 0   # records where state_probabilities was empty
    for r in paired:
        top2 = _top2_states(r["state_probabilities"], r["predicted_state"])
        if len(top2) < 2:
            top2_degraded += 1
        actual = r["actual_state"]
        if actual and actual in top2:
            top2_hits += 1

    top2_rate = _pct(top2_hits, n)
    top2_note = ""
    if top2_degraded > 0:
        top2_note = (
            f"{top2_degraded}/{n} 条记录缺少 state_probabilities，"
            "Top2 已降级为仅含 Top1（predicted_state）参与覆盖判断。"
        )

    # ── 排除命中率 / 误杀率 ────────────────────────────────────────────────────
    excluded_records = [
        r for r in paired if r.get("exclusion_action") == "exclude"
    ]
    excl_total = len(excluded_records)
    excl_hits  = 0
    excl_misses = 0

    for r in excluded_records:
        hit = _exclusion_hit(r.get("exclusion_triggered_rule"), r.get("actual_state"))
        if hit is True:
            excl_hits += 1
        elif hit is False:
            excl_misses += 1
        # None → 无法判断，不计入分子分母（分母用可判断数量）

    # 分母只计 actual_state 有值的排除记录
    excl_judged = excl_hits + excl_misses
    excl_hit_rate  = _pct(excl_hits,   excl_judged)
    excl_miss_rate = _pct(excl_misses, excl_judged)

    if excl_total == 0:
        warnings.append("最近记录中排除层未触发过，排除命中率 / 误杀率无法计算。")

    return {
        "symbol":               symbol,
        "window":               window,
        "sample_count":         n,
        "top1_hit_rate":        top1_rate,
        "top1_hit_count":       top1_hits,
        "top2_coverage_rate":   top2_rate,
        "top2_coverage_count":  top2_hits,
        "top2_note":            top2_note,
        "exclusion_total":      excl_total,
        "exclusion_hit_rate":   excl_hit_rate,
        "exclusion_hit_count":  excl_hits,
        "exclusion_miss_rate":  excl_miss_rate,
        "exclusion_miss_count": excl_misses,
        "warnings":             warnings,
    }


def build_review_detail(
    symbol: str = "AVGO",
    window: int = _REVIEW_WINDOW,
) -> list[dict[str, Any]]:
    """
    返回逐条推演 vs 实际的对比明细（最新在前）。

    每条包含：
        prediction_for_date   — 预测目标日期
        predicted_state       — 预测五状态
        actual_state          — 实际五状态
        state_match           — Top1 是否命中
        top2_states           — Top2 候选状态列表
        top2_covered          — 实际是否在 Top2 内
        direction             — 方向（偏多 / 偏空 / 中性）
        direction_correct     — 方向是否正确
        confidence            — 置信度
        exclusion_action      — allow / exclude
        exclusion_triggered_rule — 排除规则名
        exclusion_hit         — 排除是否命中（True/False/None）
        actual_close_change_pct — 实际涨跌幅（%）
    """
    paired, _ = _join_logs(symbol, window)
    detail: list[dict[str, Any]] = []
    for r in paired:
        top2 = _top2_states(r["state_probabilities"], r["predicted_state"])
        actual = r.get("actual_state")
        top2_covered = bool(actual and actual in top2)
        excl_hit = _exclusion_hit(r.get("exclusion_triggered_rule"), actual)
        detail.append({
            "prediction_for_date":      r.get("prediction_for_date"),
            "predicted_state":          r.get("predicted_state"),
            "actual_state":             actual,
            "state_match":              r.get("state_match"),
            "top2_states":              top2,
            "top2_covered":             top2_covered,
            "direction":                r.get("direction"),
            "direction_correct":        r.get("direction_correct"),
            "confidence":               r.get("confidence"),
            "exclusion_action":         r.get("exclusion_action"),
            "exclusion_triggered_rule": r.get("exclusion_triggered_rule"),
            "exclusion_hit":            excl_hit,
            "actual_close_change_pct":  r.get("actual_close_change_pct"),
        })
    return detail


def format_review_summary(stats: dict[str, Any]) -> str:
    """
    将 compute_review_stats() 输出格式化为可读中文摘要字符串。
    供命令行或日志输出使用，不依赖 UI 框架。
    """
    def _fmt_rate(rate: float | None) -> str:
        return f"{rate * 100:.1f}%" if rate is not None else "—"

    n   = stats.get("sample_count", 0)
    sym = stats.get("symbol", "AVGO")
    win = stats.get("window", 20)

    lines = [
        f"【复盘中心 — {sym} 最近 {win} 条有结果记录，实际样本 {n} 条】",
        f"  Top1 命中率    : {_fmt_rate(stats.get('top1_hit_rate'))}  "
        f"（{stats.get('top1_hit_count', 0)}/{n}）",
        f"  Top2 覆盖率    : {_fmt_rate(stats.get('top2_coverage_rate'))}  "
        f"（{stats.get('top2_coverage_count', 0)}/{n}）",
    ]
    if stats.get("top2_note"):
        lines.append(f"    ↳ {stats['top2_note']}")

    excl = stats.get("exclusion_total", 0)
    lines.append(
        f"  排除命中率     : {_fmt_rate(stats.get('exclusion_hit_rate'))}  "
        f"（{stats.get('exclusion_hit_count', 0)}/{excl} 次触发）"
    )
    lines.append(
        f"  误杀率         : {_fmt_rate(stats.get('exclusion_miss_rate'))}  "
        f"（{stats.get('exclusion_miss_count', 0)}/{excl} 次触发）"
    )

    for w in stats.get("warnings", []):
        lines.append(f"  ⚠ {w}")

    return "\n".join(lines)
