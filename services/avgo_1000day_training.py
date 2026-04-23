from __future__ import annotations

from collections import Counter
from typing import Any, Callable


def _training_log(message: str) -> None:
    print(f"[training] {message}", flush=True)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _clean_text(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text if text else fallback


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_symbol(symbol: str) -> str:
    return _clean_text(symbol, fallback="AVGO").upper() or "AVGO"


def _empty_distribution(*, kind: str) -> dict[str, int]:
    if kind == "confidence":
        return {"high": 0, "medium": 0, "low": 0, "unknown": 0}
    return {"low": 0, "medium": 0, "high": 0, "unknown": 0}


def _empty_report(*, symbol: str, num_cases: int) -> dict[str, Any]:
    return {
        "kind": "avgo_1000day_training_report",
        "ready": False,
        "symbol": symbol,
        "num_cases_requested": num_cases,
        "num_cases_built": 0,
        "date_range": {
            "start_as_of_date": None,
            "end_as_of_date": None,
            "end_prediction_for_date": None,
        },
        "replay_summary": {
            "total_cases": 0,
            "completed_cases": 0,
            "failed_cases": 0,
            "direction_accuracy": None,
            "confidence_distribution": _empty_distribution(kind="confidence"),
            "risk_distribution": _empty_distribution(kind="risk"),
        },
        "rule_growth": {
            "rule_score_report": None,
            "rule_lifecycle_report": None,
            "active_rule_pool_report": None,
            "active_rule_pool_export": None,
            "validation_report": None,
            "calibration_report": None,
            "promotion_report": None,
            "adoption_handoff": None,
            "drift_report": None,
        },
        "headline_findings": [],
        "rule_insights": {
            "top_effective_rules": [],
            "top_harmful_rules": [],
            "promote_candidates": [],
            "production_candidates": [],
            "drift_candidates": [],
        },
        "summary": "",
        "warnings": [],
    }


def _resolve_default_replay_runner() -> Callable[..., dict[str, Any]]:
    from services.historical_replay_training import run_historical_replay_batch

    return run_historical_replay_batch


def _resolve_default_rule_score_builder() -> Callable[..., dict[str, Any]]:
    from services.rule_scoring import build_rule_score_report

    return build_rule_score_report


def _resolve_default_rule_lifecycle_builder() -> Callable[..., dict[str, Any]]:
    from services.rule_lifecycle import build_rule_lifecycle_report

    return build_rule_lifecycle_report


def _resolve_default_active_pool_builder() -> Callable[..., dict[str, Any]]:
    from services.active_rule_pool import build_active_rule_pool_report

    return build_active_rule_pool_report


def _resolve_default_active_pool_export_builder() -> Callable[..., dict[str, Any]]:
    from services.active_rule_pool_export import build_active_rule_pool_export

    return build_active_rule_pool_export


def _resolve_default_validation_builder() -> Callable[..., dict[str, Any]]:
    from services.active_rule_pool_validation import build_active_rule_pool_validation_report

    return build_active_rule_pool_validation_report


def _resolve_default_calibration_builder() -> Callable[..., dict[str, Any]]:
    from services.active_rule_pool_calibration import build_active_rule_pool_calibration_report

    return build_active_rule_pool_calibration_report


def _resolve_default_promotion_builder() -> Callable[..., dict[str, Any]]:
    from services.active_rule_pool_promotion import build_active_rule_pool_promotion_report

    return build_active_rule_pool_promotion_report


def _resolve_default_adoption_builder() -> Callable[..., dict[str, Any]]:
    from services.promotion_adoption_gate import build_promotion_adoption_handoff

    return build_promotion_adoption_handoff


def _resolve_default_drift_builder() -> Callable[..., dict[str, Any]]:
    from services.active_rule_pool_drift import build_active_rule_pool_drift_report

    return build_active_rule_pool_drift_report


def _default_trading_days_provider(*, symbol: str, minimum_days: int) -> list[str]:
    import yfinance as yf

    ticker = yf.Ticker(symbol)
    history = ticker.history(period="10y", interval="1d")
    if history.empty:
        return []

    dates: list[str] = []
    seen: set[str] = set()
    index = history.index
    if getattr(index, "tz", None) is not None:
        index = index.tz_localize(None)

    for raw_date in index:
        date_text = raw_date.strftime("%Y-%m-%d")
        if date_text in seen:
            continue
        seen.add(date_text)
        dates.append(date_text)

    dates.sort()
    if minimum_days > 0:
        return dates[-minimum_days:]
    return dates


def _normalize_trading_days(days: list[Any]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()

    for raw_day in days:
        day = _clean_text(raw_day)
        if not day or day in seen:
            continue
        seen.add(day)
        normalized.append(day)

    normalized.sort()
    return normalized


def _build_date_pairs_from_days(days: list[str], *, num_cases: int) -> list[tuple[str, str]]:
    if num_cases <= 0 or len(days) < 2:
        return []

    trimmed = days[-(num_cases + 1) :]
    return [
        (trimmed[index], trimmed[index + 1])
        for index in range(len(trimmed) - 1)
    ]


def _date_range_from_pairs(date_pairs: list[tuple[str, str]]) -> dict[str, str | None]:
    if not date_pairs:
        return {
            "start_as_of_date": None,
            "end_as_of_date": None,
            "end_prediction_for_date": None,
        }

    return {
        "start_as_of_date": date_pairs[0][0],
        "end_as_of_date": date_pairs[-1][0],
        "end_prediction_for_date": date_pairs[-1][1],
    }


def _date_range_from_replay_results(results: list[dict[str, Any]]) -> dict[str, str | None]:
    pairs: list[tuple[str, str]] = []
    for raw_result in results:
        result = _as_dict(raw_result)
        as_of_date = _clean_text(result.get("as_of_date"))
        prediction_for_date = _clean_text(result.get("prediction_for_date"))
        if as_of_date and prediction_for_date:
            pairs.append((as_of_date, prediction_for_date))
    pairs.sort()
    return _date_range_from_pairs(pairs)


def _valid_replay_results(results: list[Any]) -> list[dict[str, Any]]:
    valid_results: list[dict[str, Any]] = []
    for raw_result in results:
        result = _as_dict(raw_result)
        as_of_date = _clean_text(result.get("as_of_date"))
        prediction_for_date = _clean_text(result.get("prediction_for_date"))
        if not as_of_date or not prediction_for_date:
            continue
        valid_results.append(result)
    return valid_results


def _distribution_from_results(
    results: list[dict[str, Any]],
    *,
    kind: str,
) -> dict[str, int]:
    distribution = _empty_distribution(kind=kind)

    for raw_result in results:
        result = _as_dict(raw_result)
        snapshot = _as_dict(result.get("projection_snapshot"))
        final_decision = _as_dict(snapshot.get("final_decision"))
        if kind == "confidence":
            bucket = _clean_text(final_decision.get("final_confidence")).lower()
            if bucket not in distribution:
                bucket = "unknown"
        else:
            bucket = _clean_text(final_decision.get("risk_level")).lower()
            if bucket not in distribution:
                bucket = "unknown"
        distribution[bucket] += 1

    return distribution


def _replay_summary_from_batch(replay_batch_result: dict[str, Any]) -> dict[str, Any]:
    replay = _as_dict(replay_batch_result)
    summary = _as_dict(replay.get("summary"))
    results = _as_list(replay.get("results"))

    total_cases = _as_int(summary.get("total_cases"), default=len(results))
    completed_cases = _as_int(
        summary.get("completed_cases"),
        default=sum(1 for item in results if _as_dict(item).get("ready") is True),
    )
    failed_cases = _as_int(summary.get("failed_cases"), default=max(total_cases - completed_cases, 0))

    return {
        "total_cases": total_cases,
        "completed_cases": completed_cases,
        "failed_cases": failed_cases,
        "direction_accuracy": _as_float(summary.get("direction_accuracy")),
        "confidence_distribution": _distribution_from_results(results, kind="confidence"),
        "risk_distribution": _distribution_from_results(results, kind="risk"),
    }


def _top_review_counter(
    results: list[dict[str, Any]],
    *,
    field: str,
) -> list[tuple[str, int]]:
    counter: Counter[str] = Counter()
    for raw_result in results:
        review = _as_dict(_as_dict(raw_result).get("review"))
        label = _clean_text(review.get(field))
        if label:
            counter[label] += 1
    return counter.most_common(3)


def _extend_prefixed_warnings(
    warnings: list[str],
    *,
    prefix: str,
    artifact: dict[str, Any] | None,
) -> None:
    for raw_warning in _as_list(_as_dict(artifact).get("warnings")):
        text = _clean_text(raw_warning)
        if text:
            warnings.append(f"{prefix}: {text}")


def _call_builder(
    warnings: list[str],
    *,
    label: str,
    builder: Callable[..., dict[str, Any]] | None,
    kwargs: dict[str, Any],
) -> dict[str, Any] | None:
    if builder is None:
        warnings.append(f"{label}: no builder available.")
        return None

    try:
        artifact = builder(**kwargs)
    except Exception as exc:
        warnings.append(f"{label}: builder execution failed: {exc}")
        return None

    if not isinstance(artifact, dict):
        warnings.append(f"{label}: builder returned a non-dict artifact; treated as missing.")
        return None

    _extend_prefixed_warnings(warnings, prefix=label, artifact=artifact)
    return artifact


def _effective_rules_from_score(rule_score_report: dict[str, Any] | None) -> list[dict[str, Any]]:
    score = _as_dict(rule_score_report)
    top_promising = _as_list(score.get("top_promising_rules"))
    if top_promising:
        return top_promising[:5]
    rules = [
        rule
        for rule in _as_list(score.get("rules"))
        if _clean_text(_as_dict(rule).get("recommended_status")).lower() in {"promising", "watchlist"}
    ]
    rules.sort(
        key=lambda item: (
            -_as_int(_as_dict(item).get("hit_count")),
            -(_as_float(_as_dict(item).get("net_score")) or 0.0),
            _clean_text(_as_dict(item).get("title")),
        )
    )
    return rules[:5]


def _harmful_rules_from_score(rule_score_report: dict[str, Any] | None) -> list[dict[str, Any]]:
    score = _as_dict(rule_score_report)
    top_risky = _as_list(score.get("top_risky_rules"))
    if top_risky:
        return top_risky[:5]
    rules = [
        rule
        for rule in _as_list(score.get("rules"))
        if _clean_text(_as_dict(rule).get("recommended_status")).lower() == "risky"
    ]
    rules.sort(
        key=lambda item: (
            -_as_int(_as_dict(item).get("harmful_count")),
            -(_as_float(_as_dict(item).get("harm_rate")) or 0.0),
            _clean_text(_as_dict(item).get("title")),
        )
    )
    return rules[:5]


def _build_headline_findings(
    *,
    replay_summary: dict[str, Any],
    error_layers: list[tuple[str, int]],
    error_categories: list[tuple[str, int]],
    promote_candidates: list[dict[str, Any]],
    production_candidates: list[dict[str, Any]],
    drift_candidates: list[dict[str, Any]],
    warnings: list[str],
) -> list[str]:
    findings: list[str] = []
    findings.append(
        "最近训练样本 "
        f"{replay_summary.get('completed_cases', 0)}/{replay_summary.get('total_cases', 0)} 已完成复盘。"
    )

    accuracy = _as_float(replay_summary.get("direction_accuracy"))
    if accuracy is not None:
        findings.append(f"整体方向准确率约为 {accuracy * 100:.1f}%。")

    if promote_candidates:
        findings.append(f"当前有 {len(promote_candidates)} 条 promote candidates 值得继续跟踪。")
    if production_candidates:
        findings.append(f"当前有 {len(production_candidates)} 条 production candidates 接近正式 adoption review。")
    if drift_candidates:
        findings.append(f"检测到 {len(drift_candidates)} 条 drift candidates，需要重点复查 recent net effect。")
    if error_layers:
        findings.append(f"最常见错误层为 {error_layers[0][0]}（{error_layers[0][1]} 次）。")
    if error_categories:
        findings.append(f"最常见错误类别为 {error_categories[0][0]}（{error_categories[0][1]} 次）。")
    if warnings and len(findings) < 3:
        findings.append("本次 1000 天训练存在部分降级或失败样本，解读时需要结合 warnings。")

    return findings[:5]


def _build_summary(
    *,
    symbol: str,
    num_cases_built: int,
    replay_summary: dict[str, Any],
    promote_candidates: list[dict[str, Any]],
    production_candidates: list[dict[str, Any]],
    drift_candidates: list[dict[str, Any]],
    warnings: list[str],
) -> str:
    accuracy = _as_float(replay_summary.get("direction_accuracy"))
    accuracy_text = "unavailable" if accuracy is None else f"{accuracy * 100:.1f}%"

    parts = [
        f"{symbol} long-horizon replay training built {num_cases_built} case(s).",
        (
            f"Replay completed {replay_summary.get('completed_cases', 0)} case(s), "
            f"failed {replay_summary.get('failed_cases', 0)} case(s), "
            f"direction accuracy {accuracy_text}."
        ),
        (
            f"Promote candidates={len(promote_candidates)}, "
            f"production candidates={len(production_candidates)}, "
            f"drift candidates={len(drift_candidates)}."
        ),
    ]
    if num_cases_built <= 0:
        parts.append("No usable historical date pairs were available, so the report is degraded.")
    elif warnings:
        parts.append("Some replay or rule-growth stages degraded; review warnings before using this as a production-facing summary.")
    else:
        parts.append("Replay and downstream rule-growth summaries completed without major degradation.")
    return " ".join(parts)


def _compute_ready(
    *,
    num_cases_built: int,
    replay_summary: dict[str, Any],
    rule_growth: dict[str, Any],
) -> bool:
    if num_cases_built <= 0:
        return False
    completed_cases = _as_int(replay_summary.get("completed_cases"))
    if completed_cases <= 0 and _as_int(replay_summary.get("total_cases")) <= 0:
        return False
    return any(isinstance(value, dict) for value in rule_growth.values()) or completed_cases > 0


def _skip_step(
    warnings: list[str],
    *,
    label: str,
    reason: str,
) -> None:
    warnings.append(f"{label}: skipped because {reason}")
    _training_log(f"{label}: skipped ({reason})")


def run_avgo_1000day_replay_training(
    *,
    symbol: str = "AVGO",
    lookback_days: int = 20,
    num_cases: int = 1000,
    date_pairs: list[tuple[str, str]] | None = None,
    replay_batch_result: dict | None = None,
    _trading_days_provider: Callable[..., list[str]] | None = None,
    _replay_runner: Callable[..., dict[str, Any]] | None = None,
    _rule_score_builder: Callable[..., dict[str, Any]] | None = None,
    _rule_lifecycle_builder: Callable[..., dict[str, Any]] | None = None,
    _active_pool_builder: Callable[..., dict[str, Any]] | None = None,
    _active_pool_export_builder: Callable[..., dict[str, Any]] | None = None,
    _validation_builder: Callable[..., dict[str, Any]] | None = None,
    _calibration_builder: Callable[..., dict[str, Any]] | None = None,
    _promotion_builder: Callable[..., dict[str, Any]] | None = None,
    _adoption_builder: Callable[..., dict[str, Any]] | None = None,
    _drift_builder: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    normalized_symbol = _normalize_symbol(symbol)
    report = _empty_report(symbol=normalized_symbol, num_cases=num_cases)
    warnings: list[str] = report["warnings"]

    _training_log(
        f"starting {normalized_symbol} 1000-day training (requested_cases={num_cases}, lookback_days={lookback_days})"
    )

    replay_runner = _replay_runner or _resolve_default_replay_runner()
    rule_score_builder = _rule_score_builder or _resolve_default_rule_score_builder()
    rule_lifecycle_builder = _rule_lifecycle_builder or _resolve_default_rule_lifecycle_builder()
    active_pool_builder = _active_pool_builder or _resolve_default_active_pool_builder()
    active_pool_export_builder = _active_pool_export_builder or _resolve_default_active_pool_export_builder()
    validation_builder = _validation_builder
    calibration_builder = _calibration_builder or _resolve_default_calibration_builder()
    promotion_builder = _promotion_builder or _resolve_default_promotion_builder()
    adoption_builder = _adoption_builder or _resolve_default_adoption_builder()
    drift_builder = _drift_builder or _resolve_default_drift_builder()

    replay_batch = _as_dict(replay_batch_result) if isinstance(replay_batch_result, dict) else None
    built_date_pairs = list(date_pairs or [])

    if replay_batch is None:
        if not built_date_pairs:
            _training_log("building date pairs")
            trading_days_provider = _trading_days_provider or _default_trading_days_provider
            try:
                trading_days = _normalize_trading_days(
                    trading_days_provider(
                        symbol=normalized_symbol,
                        minimum_days=max(num_cases + 1, 2),
                    )
                )
            except Exception as exc:
                warnings.append(f"trading_days_provider failed: {exc}")
                trading_days = []

            built_date_pairs = _build_date_pairs_from_days(trading_days, num_cases=num_cases)
            _training_log(f"built {len(built_date_pairs)} date pair(s)")
            if len(built_date_pairs) < num_cases:
                warnings.append(
                    f"Only built {len(built_date_pairs)} date pair(s) for {normalized_symbol}; fewer than requested {num_cases}."
                )

        report["num_cases_built"] = len(built_date_pairs)
        report["date_range"] = _date_range_from_pairs(built_date_pairs)

        if built_date_pairs:
            _training_log(f"running replay batch for {len(built_date_pairs)} case(s)")
            replay_batch = _call_builder(
                warnings,
                label="replay",
                builder=replay_runner,
                kwargs={
                    "symbol": normalized_symbol,
                    "date_pairs": built_date_pairs,
                    "lookback_days": lookback_days,
                },
            )
        else:
            _training_log("building date pairs yielded no usable samples")
            warnings.append("No valid historical date pairs were available for replay training.")
            replay_batch = None
    else:
        _training_log("using provided replay batch result")
        raw_replay_results = _as_list(replay_batch.get("results"))
        replay_results = _valid_replay_results(raw_replay_results)
        report["num_cases_built"] = len(replay_results)
        report["date_range"] = _date_range_from_replay_results(replay_results)
        if not replay_results:
            warnings.append(
                "replay: provided replay_batch_result contained no valid replay results; built case count kept at 0."
            )

    if replay_batch is not None:
        _extend_prefixed_warnings(warnings, prefix="replay", artifact=replay_batch)

    replay_results = _valid_replay_results(_as_list(_as_dict(replay_batch).get("results")))
    if replay_batch is not None and not replay_results:
        report["replay_summary"] = _empty_report(symbol=normalized_symbol, num_cases=num_cases)["replay_summary"]
    else:
        report["replay_summary"] = _replay_summary_from_batch(_as_dict(replay_batch))

    rule_growth = report["rule_growth"]
    _training_log("building rule score report")
    rule_growth["rule_score_report"] = _call_builder(
        warnings,
        label="rule_scoring",
        builder=rule_score_builder,
        kwargs={"replay_results": replay_results},
    )
    _training_log("building lifecycle report")
    rule_growth["rule_lifecycle_report"] = _call_builder(
        warnings,
        label="rule_lifecycle",
        builder=rule_lifecycle_builder,
        kwargs={"rule_score_report": rule_growth["rule_score_report"]},
    )
    _training_log("building active pool report")
    rule_growth["active_rule_pool_report"] = _call_builder(
        warnings,
        label="active_pool",
        builder=active_pool_builder,
        kwargs={"lifecycle_report": rule_growth["rule_lifecycle_report"]},
    )
    _training_log("building active pool export")
    rule_growth["active_rule_pool_export"] = _call_builder(
        warnings,
        label="active_pool_export",
        builder=active_pool_export_builder,
        kwargs={"active_rule_pool_report": rule_growth["active_rule_pool_report"]},
    )
    if validation_builder is None:
        _skip_step(
            warnings,
            label="validation",
            reason="no paired baseline vs active-pool validation input or explicit validation builder was provided",
        )
        rule_growth["validation_report"] = None
    else:
        _training_log("running validation")
        rule_growth["validation_report"] = _call_builder(
            warnings,
            label="validation",
            builder=validation_builder,
            kwargs={
                "baseline_results": replay_results,
                "active_pool_results": None,
                "active_rule_pool_export": rule_growth["active_rule_pool_export"],
                "symbol": normalized_symbol,
            },
        )

    if rule_growth["validation_report"] is None:
        _skip_step(warnings, label="calibration", reason="validation report is unavailable")
        _skip_step(warnings, label="promotion", reason="calibration report is unavailable")
        _skip_step(warnings, label="adoption", reason="promotion report is unavailable")
        _skip_step(warnings, label="drift", reason="validation report is unavailable")
    else:
        _training_log("building calibration report")
        rule_growth["calibration_report"] = _call_builder(
            warnings,
            label="calibration",
            builder=calibration_builder,
            kwargs={
                "validation_report": rule_growth["validation_report"],
                "rule_lifecycle_report": rule_growth["rule_lifecycle_report"],
                "rule_score_report": rule_growth["rule_score_report"],
            },
        )
        if rule_growth["calibration_report"] is None:
            _skip_step(warnings, label="promotion", reason="calibration report is unavailable")
            _skip_step(warnings, label="adoption", reason="promotion report is unavailable")
        else:
            _training_log("building promotion report")
            rule_growth["promotion_report"] = _call_builder(
                warnings,
                label="promotion",
                builder=promotion_builder,
                kwargs={
                    "calibration_report": rule_growth["calibration_report"],
                    "validation_report": rule_growth["validation_report"],
                    "lifecycle_report": rule_growth["rule_lifecycle_report"],
                },
            )
            if rule_growth["promotion_report"] is None:
                _skip_step(warnings, label="adoption", reason="promotion report is unavailable")
            else:
                _training_log("building adoption handoff")
                rule_growth["adoption_handoff"] = _call_builder(
                    warnings,
                    label="adoption",
                    builder=adoption_builder,
                    kwargs={
                        "promotion_report": rule_growth["promotion_report"],
                        "promotion_execution_bridge": None,
                        "calibration_report": rule_growth["calibration_report"],
                    },
                )

        _training_log("building drift report")
        rule_growth["drift_report"] = _call_builder(
            warnings,
            label="drift",
            builder=drift_builder,
            kwargs={"validation_report": rule_growth["validation_report"]},
        )

    error_layers = _top_review_counter(replay_results, field="error_layer")
    error_categories = _top_review_counter(replay_results, field="error_category")
    promote_candidates = _as_list(_as_dict(rule_growth["promotion_report"]).get("promote_candidates"))
    production_candidates = _as_list(_as_dict(rule_growth["adoption_handoff"]).get("production_candidates"))
    drift_candidates = _as_list(_as_dict(rule_growth["drift_report"]).get("drift_candidates"))

    report["rule_insights"] = {
        "top_effective_rules": _effective_rules_from_score(rule_growth["rule_score_report"]),
        "top_harmful_rules": _harmful_rules_from_score(rule_growth["rule_score_report"]),
        "promote_candidates": promote_candidates[:5],
        "production_candidates": production_candidates[:5],
        "drift_candidates": drift_candidates[:5],
    }
    _training_log("building headline findings and summary")
    report["headline_findings"] = _build_headline_findings(
        replay_summary=report["replay_summary"],
        error_layers=error_layers,
        error_categories=error_categories,
        promote_candidates=promote_candidates,
        production_candidates=production_candidates,
        drift_candidates=drift_candidates,
        warnings=warnings,
    )
    report["summary"] = _build_summary(
        symbol=normalized_symbol,
        num_cases_built=report["num_cases_built"],
        replay_summary=report["replay_summary"],
        promote_candidates=promote_candidates,
        production_candidates=production_candidates,
        drift_candidates=drift_candidates,
        warnings=warnings,
    )
    report["ready"] = _compute_ready(
        num_cases_built=report["num_cases_built"],
        replay_summary=report["replay_summary"],
        rule_growth=rule_growth,
    )
    _training_log(f"training complete (ready={report['ready']}, built_cases={report['num_cases_built']})")
    return report


def build_avgo_1000day_rule_summary(**kwargs: Any) -> dict[str, Any]:
    return run_avgo_1000day_replay_training(**kwargs)
