from __future__ import annotations

from typing import Any


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _clean_text(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text if text else fallback


def _empty_brief(*, symbol: str, run_date: str) -> dict[str, Any]:
    return {
        "kind": "daily_training_brief",
        "ready": False,
        "symbol": symbol,
        "run_date": run_date,
        "overall_status": "degraded",
        "step_overview": {
            "ok": 0,
            "degraded": 0,
            "failed": 0,
            "skipped": 0,
        },
        "headline_metrics": {
            "total_replay_cases": 0,
            "direction_accuracy": None,
            "active_rule_count": 0,
            "promote_candidate_count": 0,
            "drift_candidate_count": 0,
        },
        "top_highlights": [],
        "promotion_watchlist": [],
        "drift_watchlist": [],
        "risk_flags": [],
        "recommended_next_checks": [],
        "summary": "",
        "warnings": [],
    }


def _normalize_symbol(symbol: Any, fallback_symbol: Any = "AVGO") -> str:
    return _clean_text(symbol or fallback_symbol, fallback="AVGO").upper() or "AVGO"


def _format_accuracy(value: Any) -> str:
    try:
        if value is None:
            return "unavailable"
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return "unavailable"


def _build_step_overview(step_status: dict[str, Any]) -> dict[str, int]:
    overview = {
        "ok": 0,
        "degraded": 0,
        "failed": 0,
        "skipped": 0,
    }
    for status in step_status.values():
        text = _clean_text(status).lower()
        if text in overview:
            overview[text] += 1
    return overview


def _overall_status(step_overview: dict[str, int], *, has_valid_step_status: bool) -> str:
    if not has_valid_step_status:
        return "degraded"
    if step_overview["failed"] > 0:
        return "failed"
    if step_overview["degraded"] > 0:
        return "degraded"
    if step_overview["skipped"] > 0:
        return "mixed"
    return "healthy"


def _safe_int_metric(
    metrics: dict[str, Any],
    key: str,
    warnings: list[str],
) -> int:
    value = metrics.get(key, 0)
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        warnings.append(f"daily_training_report.headline_metrics.{key} is invalid; defaulted to 0.")
        return 0


def _safe_float_metric(
    metrics: dict[str, Any],
    key: str,
    warnings: list[str],
) -> float | None:
    value = metrics.get(key)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        warnings.append(f"daily_training_report.headline_metrics.{key} is invalid; defaulted to None.")
        return None


def _extract_headline_metrics(report: dict[str, Any], warnings: list[str]) -> dict[str, Any]:
    metrics = _as_dict(report.get("headline_metrics"))
    return {
        "total_replay_cases": _safe_int_metric(metrics, "total_replay_cases", warnings),
        "direction_accuracy": _safe_float_metric(metrics, "direction_accuracy", warnings),
        "active_rule_count": _safe_int_metric(metrics, "active_rule_count", warnings),
        "promote_candidate_count": _safe_int_metric(metrics, "promote_candidate_count", warnings),
        "drift_candidate_count": _safe_int_metric(metrics, "drift_candidate_count", warnings),
    }


def _promotion_watchlist(report: dict[str, Any], *, max_items: int) -> list[dict[str, Any]]:
    artifacts = _as_dict(report.get("artifacts"))
    promotion_report = _as_dict(artifacts.get("active_rule_pool_promotion_report"))
    promote_candidates = _as_list(promotion_report.get("promote_candidates"))
    rules = _as_list(promotion_report.get("rules"))

    by_title: dict[str, dict[str, Any]] = {}
    for raw_rule in rules:
        rule = _as_dict(raw_rule)
        title = _clean_text(rule.get("title"))
        if title:
            by_title[title] = rule

    watchlist: list[dict[str, Any]] = []
    for raw_candidate in promote_candidates[:max_items]:
        candidate = _as_dict(raw_candidate)
        title = _clean_text(candidate.get("title"), fallback="unknown")
        detail = by_title.get(title, {})
        watchlist.append(
            {
                "rule_id": _clean_text(candidate.get("rule_id") or detail.get("rule_id"), fallback="unknown"),
                "title": title,
                "promotion_confidence": _clean_text(
                    candidate.get("promotion_confidence") or detail.get("promotion_confidence"),
                    fallback="unknown",
                ),
                "notes": _clean_text(
                    candidate.get("notes")
                    or detail.get("notes")
                    or detail.get("promotion_rationale"),
                    fallback="",
                ),
            }
        )
    return watchlist


def _drift_watchlist(report: dict[str, Any], *, max_items: int) -> list[dict[str, Any]]:
    artifacts = _as_dict(report.get("artifacts"))
    drift_report = _as_dict(artifacts.get("active_rule_pool_drift_report"))
    drift_candidates = _as_list(drift_report.get("drift_candidates"))

    watchlist: list[dict[str, Any]] = []
    for raw_candidate in drift_candidates[:max_items]:
        candidate = _as_dict(raw_candidate)
        watchlist.append(
            {
                "rule_id": _clean_text(candidate.get("rule_id"), fallback="unknown"),
                "title": _clean_text(candidate.get("title"), fallback="unknown"),
                "drift_status": _clean_text(candidate.get("drift_status"), fallback="unknown"),
                "recommended_followup": _clean_text(
                    candidate.get("recommended_followup"),
                    fallback="keep_monitoring",
                ),
                "notes": _clean_text(
                    candidate.get("notes") or candidate.get("drift_rationale"),
                    fallback="",
                ),
            }
        )
    return watchlist


def _top_highlights(
    *,
    step_status: dict[str, Any],
    metrics: dict[str, Any],
    max_highlights: int,
) -> list[str]:
    highlights: list[str] = []

    promote_count = metrics["promote_candidate_count"]
    drift_count = metrics["drift_candidate_count"]
    accuracy = metrics["direction_accuracy"]
    active_rule_count = metrics["active_rule_count"]

    if promote_count > 0:
        highlights.append(f"今日训练生成 {promote_count} 条 promote candidates。")
    if drift_count > 0:
        highlights.append(f"发现 {drift_count} 条 drift candidates，需要优先复查。")
    if accuracy is not None:
        highlights.append(f"方向准确率为 {_format_accuracy(accuracy)}。")
    if active_rule_count > 0:
        highlights.append(f"当前 active rule 数量为 {active_rule_count}。")

    for step, status in step_status.items():
        if status == "failed":
            highlights.append(f"{step} 步骤 failed，本次训练可信度受影响。")
        elif status == "degraded":
            highlights.append(f"{step} 步骤 degraded，本次相关结论需要保守解读。")
        if len(highlights) >= max_highlights:
            break

    return highlights[:max_highlights]


def _risk_flags(
    *,
    step_status: dict[str, Any],
    metrics: dict[str, Any],
) -> list[str]:
    risk_flags: list[str] = []

    for step, status in step_status.items():
        if status == "failed":
            risk_flags.append(f"{step} failed，今天的训练结论不能完全按正常流水线理解。")
        elif status == "degraded":
            risk_flags.append(f"{step} degraded，相关输出可信度有限。")

    validation_status = _clean_text(step_status.get("validation"))
    if validation_status in {"skipped", "degraded", "failed"}:
        risk_flags.append("validation 不完整，今天不要过度依赖效果验证相关结论。")

    if metrics["drift_candidate_count"] > 0:
        risk_flags.append(f"存在 {metrics['drift_candidate_count']} 条 drift candidates，active rules 近期稳定性需重点确认。")

    accuracy = metrics["direction_accuracy"]
    try:
        if accuracy is not None and float(accuracy) < 0.5:
            risk_flags.append("方向准确率低于 50%，今天的训练质量偏弱，建议保守解读。")
    except (TypeError, ValueError):
        pass

    deduped: list[str] = []
    for flag in risk_flags:
        if flag not in deduped:
            deduped.append(flag)
    return deduped


def _recommended_next_checks(
    *,
    metrics: dict[str, Any],
    step_status: dict[str, Any],
    promotion_watchlist: list[dict[str, Any]],
    drift_watchlist: list[dict[str, Any]],
) -> list[str]:
    checks: list[str] = []

    if drift_watchlist:
        checks.append("优先复查 drift candidates 的 recent net effect 是否继续恶化。")
    if promotion_watchlist:
        checks.append("检查 promote candidates 是否已有足够 hit_count 与 confidence 支撑正式晋升。")
    if _clean_text(step_status.get("validation")) in {"degraded", "failed", "skipped"}:
        checks.append("由于 validation 不完整，今天不要过度依赖 calibration 与 promotion 结论。")
    if metrics["active_rule_count"] == 0:
        checks.append("active rule 数量为 0，建议先确认 active pool 与 export 上游是否正常。")

    if not checks:
        checks.append("今天的训练结果整体稳定，可优先查看 promote 与 drift 明细是否有新增变化。")

    return checks[:4]


def _build_summary(
    *,
    overall_status: str,
    metrics: dict[str, Any],
    step_overview: dict[str, int],
    top_highlights: list[str],
) -> str:
    parts = [
        f"本次 daily training 整体状态为 {overall_status}。",
        f"共复盘 {metrics['total_replay_cases']} 个样本，方向准确率 {_format_accuracy(metrics['direction_accuracy'])}。",
        f"当前 active rules={metrics['active_rule_count']}，promote candidates={metrics['promote_candidate_count']}，drift candidates={metrics['drift_candidate_count']}。",
        (
            f"步骤概览：ok={step_overview['ok']}，degraded={step_overview['degraded']}，"
            f"failed={step_overview['failed']}，skipped={step_overview['skipped']}。"
        ),
    ]
    if top_highlights:
        parts.append("今日重点：" + " ".join(top_highlights[:3]))
    return " ".join(parts)


def build_daily_training_brief(
    daily_training_report: dict | None = None,
    *,
    symbol: str | None = None,
    max_highlights: int = 5,
) -> dict[str, Any]:
    source_report = _as_dict(daily_training_report)
    brief = _empty_brief(
        symbol=_normalize_symbol(symbol, fallback_symbol=source_report.get("symbol")),
        run_date=_clean_text(source_report.get("run_date"), fallback="unknown"),
    )

    if not source_report:
        brief["warnings"] = ["No daily_training_report was provided for summary generation."]
        brief["summary"] = "缺少 daily_training_report，暂时无法生成每日训练简报。"
        return brief

    step_status = _as_dict(source_report.get("step_status"))
    warnings: list[str] = []
    metrics = _extract_headline_metrics(source_report, warnings)
    promotion_watchlist = _promotion_watchlist(source_report, max_items=max_highlights)
    drift_watchlist = _drift_watchlist(source_report, max_items=max_highlights)
    step_overview = _build_step_overview(step_status)
    overall_status = _overall_status(step_overview, has_valid_step_status=bool(step_status))
    highlights = _top_highlights(
        step_status=step_status,
        metrics=metrics,
        max_highlights=max_highlights,
    )
    risk_flags = _risk_flags(
        step_status=step_status,
        metrics=metrics,
    )
    next_checks = _recommended_next_checks(
        metrics=metrics,
        step_status=step_status,
        promotion_watchlist=promotion_watchlist,
        drift_watchlist=drift_watchlist,
    )

    for raw_warning in _as_list(source_report.get("warnings")):
        text = _clean_text(raw_warning)
        if text:
            warnings.append(text)
    if not step_status:
        warnings.append("daily_training_report.step_status is missing or malformed.")
    if not _as_dict(source_report.get("headline_metrics")):
        warnings.append("daily_training_report.headline_metrics is missing or malformed.")

    brief.update(
        {
            "ready": bool(source_report.get("ready")) or bool(step_status) or bool(metrics["total_replay_cases"]),
            "overall_status": overall_status,
            "step_overview": step_overview,
            "headline_metrics": metrics,
            "top_highlights": highlights,
            "promotion_watchlist": promotion_watchlist,
            "drift_watchlist": drift_watchlist,
            "risk_flags": risk_flags,
            "recommended_next_checks": next_checks,
            "summary": _build_summary(
                overall_status=overall_status,
                metrics=metrics,
                step_overview=step_overview,
                top_highlights=highlights,
            ),
            "warnings": warnings,
        }
    )
    return brief


def summarize_daily_training_report(**kwargs: Any) -> dict[str, Any]:
    return build_daily_training_brief(**kwargs)
