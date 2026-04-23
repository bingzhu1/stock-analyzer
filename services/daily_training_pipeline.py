from __future__ import annotations

from datetime import date
from typing import Any, Callable


_STEP_NAMES = (
    "replay",
    "rule_scoring",
    "rule_lifecycle",
    "active_pool",
    "active_pool_export",
    "validation",
    "calibration",
    "promotion",
    "drift",
)

_ARTIFACT_KEYS = {
    "replay": "replay_batch_result",
    "rule_scoring": "rule_score_report",
    "rule_lifecycle": "rule_lifecycle_report",
    "active_pool": "active_rule_pool_report",
    "active_pool_export": "active_rule_pool_export",
    "validation": "active_rule_pool_validation_report",
    "calibration": "active_rule_pool_calibration_report",
    "promotion": "active_rule_pool_promotion_report",
    "drift": "active_rule_pool_drift_report",
}


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _clean_text(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text if text else fallback


def _normalize_symbol(symbol: str) -> str:
    return _clean_text(symbol, fallback="AVGO").upper() or "AVGO"


def _default_run_date(run_date: str | None) -> str:
    return _clean_text(run_date, fallback=date.today().isoformat())


def _empty_report(*, symbol: str, run_date: str) -> dict[str, Any]:
    return {
        "kind": "daily_training_report",
        "ready": False,
        "symbol": symbol,
        "run_date": run_date,
        "step_status": {step: "skipped" for step in _STEP_NAMES},
        "artifacts": {artifact_key: None for artifact_key in _ARTIFACT_KEYS.values()},
        "headline_metrics": {
            "total_replay_cases": 0,
            "direction_accuracy": None,
            "active_rule_count": 0,
            "promote_candidate_count": 0,
            "drift_candidate_count": 0,
        },
        "summary": "",
        "warnings": [],
    }


def _artifact_status(artifact: dict[str, Any]) -> str:
    return "ok" if artifact.get("ready") is True else "degraded"


def _extend_step_warnings(
    warnings: list[str],
    *,
    step: str,
    artifact: dict[str, Any] | None,
) -> None:
    if not isinstance(artifact, dict):
        return
    for raw_warning in _as_list(artifact.get("warnings")):
        text = _clean_text(raw_warning)
        if text:
            warnings.append(f"{step}: {text}")


def _store_existing_artifact(
    report: dict[str, Any],
    *,
    step: str,
    artifact_key: str,
    artifact: Any,
) -> dict[str, Any] | None:
    warnings = report["warnings"]

    if artifact is None:
        return None

    if not isinstance(artifact, dict):
        report["step_status"][step] = "degraded"
        report["artifacts"][artifact_key] = {}
        warnings.append(f"{step}: provided artifact was not a dict and was retained as an empty degraded artifact.")
        return report["artifacts"][artifact_key]

    report["artifacts"][artifact_key] = artifact
    report["step_status"][step] = _artifact_status(artifact)
    _extend_step_warnings(warnings, step=step, artifact=artifact)
    return artifact


def _run_builder_step(
    report: dict[str, Any],
    *,
    step: str,
    artifact_key: str,
    builder: Callable[..., dict[str, Any]] | None,
    skip_reason: str,
    kwargs: dict[str, Any],
) -> dict[str, Any] | None:
    warnings = report["warnings"]

    if builder is None:
        report["step_status"][step] = "skipped"
        warnings.append(f"{step}: {skip_reason}")
        return None

    try:
        artifact = builder(**kwargs)
    except Exception as exc:
        report["step_status"][step] = "failed"
        report["artifacts"][artifact_key] = None
        warnings.append(f"{step}: builder execution failed: {exc}")
        return None

    if not isinstance(artifact, dict):
        report["step_status"][step] = "degraded"
        report["artifacts"][artifact_key] = {}
        warnings.append(f"{step}: builder returned a non-dict artifact; treated as degraded.")
        return report["artifacts"][artifact_key]

    report["artifacts"][artifact_key] = artifact
    report["step_status"][step] = _artifact_status(artifact)
    _extend_step_warnings(warnings, step=step, artifact=artifact)
    return artifact


def _extract_total_replay_cases(replay_batch_result: dict[str, Any] | None) -> int:
    replay = _as_dict(replay_batch_result)
    summary = _as_dict(replay.get("summary"))
    value = summary.get("total_cases", replay.get("total_cases", 0))
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _extract_direction_accuracy(
    replay_batch_result: dict[str, Any] | None,
    validation_report: dict[str, Any] | None,
) -> float | None:
    replay = _as_dict(replay_batch_result)
    validation = _as_dict(validation_report)
    summary = _as_dict(replay.get("summary"))

    for value in (
        summary.get("direction_accuracy"),
        validation.get("active_pool_accuracy"),
        validation.get("baseline_accuracy"),
    ):
        try:
            if value is None:
                continue
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _extract_active_rule_count(
    active_pool_report: dict[str, Any] | None,
    active_pool_export: dict[str, Any] | None,
) -> int:
    pool = _as_dict(active_pool_report)
    export = _as_dict(active_pool_export)
    candidates = _as_list(pool.get("active_pool_candidates"))
    if candidates:
        return len(candidates)
    pool_counts = _as_dict(pool.get("pool_counts"))
    try:
        include_count = int(pool_counts.get("include", 0))
    except (TypeError, ValueError):
        include_count = 0
    if include_count > 0:
        return include_count
    try:
        return int(export.get("exported_rule_count", 0))
    except (TypeError, ValueError):
        return 0


def _extract_promote_candidate_count(promotion_report: dict[str, Any] | None) -> int:
    promotion = _as_dict(promotion_report)
    candidates = _as_list(promotion.get("promote_candidates"))
    if candidates:
        return len(candidates)
    try:
        return int(_as_dict(promotion.get("decision_counts")).get("promote_candidate", 0))
    except (TypeError, ValueError):
        return 0


def _extract_drift_candidate_count(drift_report: dict[str, Any] | None) -> int:
    drift = _as_dict(drift_report)
    candidates = _as_list(drift.get("drift_candidates"))
    if candidates:
        return len(candidates)
    try:
        return int(_as_dict(drift.get("status_counts")).get("drift_candidate", 0))
    except (TypeError, ValueError):
        return 0


def _format_percent(value: float | None) -> str:
    if value is None:
        return "unavailable"
    return f"{value * 100:.1f}%"


def _build_summary(report: dict[str, Any]) -> str:
    metrics = _as_dict(report.get("headline_metrics"))
    step_status = _as_dict(report.get("step_status"))

    parts = [
        f"{report['symbol']} daily training for {report['run_date']}.",
        f"Replay cases={metrics.get('total_replay_cases', 0)}.",
        f"Direction accuracy={_format_percent(metrics.get('direction_accuracy'))}.",
        f"Active rules={metrics.get('active_rule_count', 0)}.",
        f"Promote candidates={metrics.get('promote_candidate_count', 0)}.",
        f"Drift candidates={metrics.get('drift_candidate_count', 0)}.",
    ]

    non_ok_steps = [
        f"{step}={status}"
        for step, status in step_status.items()
        if status != "ok"
    ]
    if non_ok_steps:
        parts.append("Step status highlights: " + ", ".join(non_ok_steps[:5]) + ".")
    else:
        parts.append("All daily training steps completed without degradation.")

    return " ".join(parts)


def _compute_ready(report: dict[str, Any]) -> bool:
    step_status = _as_dict(report.get("step_status"))
    usable_management_steps = (
        "active_pool",
        "active_pool_export",
        "validation",
        "calibration",
        "promotion",
        "drift",
    )
    return any(step_status.get(step) == "ok" for step in usable_management_steps)


def run_daily_training_pipeline(
    *,
    replay_batch_result: dict[str, Any] | None = None,
    rule_score_report: dict[str, Any] | None = None,
    rule_lifecycle_report: dict[str, Any] | None = None,
    active_pool_report: dict[str, Any] | None = None,
    active_pool_export: dict[str, Any] | None = None,
    validation_report: dict[str, Any] | None = None,
    calibration_report: dict[str, Any] | None = None,
    promotion_report: dict[str, Any] | None = None,
    drift_report: dict[str, Any] | None = None,
    _replay_runner: Callable[..., dict[str, Any]] | None = None,
    _rule_score_builder: Callable[..., dict[str, Any]] | None = None,
    _rule_lifecycle_builder: Callable[..., dict[str, Any]] | None = None,
    _active_pool_builder: Callable[..., dict[str, Any]] | None = None,
    _active_pool_export_builder: Callable[..., dict[str, Any]] | None = None,
    _validation_builder: Callable[..., dict[str, Any]] | None = None,
    _calibration_builder: Callable[..., dict[str, Any]] | None = None,
    _promotion_builder: Callable[..., dict[str, Any]] | None = None,
    _drift_builder: Callable[..., dict[str, Any]] | None = None,
    symbol: str = "AVGO",
    lookback_days: int = 20,
    recent_window_size: int = 20,
    use_active_rule_pool: bool = True,
    run_date: str | None = None,
) -> dict[str, Any]:
    normalized_symbol = _normalize_symbol(symbol)
    resolved_run_date = _default_run_date(run_date)
    report = _empty_report(symbol=normalized_symbol, run_date=resolved_run_date)

    replay_artifact = _store_existing_artifact(
        report,
        step="replay",
        artifact_key=_ARTIFACT_KEYS["replay"],
        artifact=replay_batch_result,
    )
    if replay_artifact is None:
        replay_artifact = _run_builder_step(
            report,
            step="replay",
            artifact_key=_ARTIFACT_KEYS["replay"],
            builder=_replay_runner,
            skip_reason="missing replay_batch_result and no _replay_runner was provided.",
            kwargs={
                "symbol": normalized_symbol,
                "lookback_days": lookback_days,
                "recent_window_size": recent_window_size,
                "use_active_rule_pool": use_active_rule_pool,
            },
        )

    score_artifact = _store_existing_artifact(
        report,
        step="rule_scoring",
        artifact_key=_ARTIFACT_KEYS["rule_scoring"],
        artifact=rule_score_report,
    )
    if score_artifact is None:
        if replay_artifact is None:
            report["step_status"]["rule_scoring"] = "skipped"
            report["warnings"].append("rule_scoring: missing replay_batch_result; unable to build rule_score_report.")
        else:
            score_artifact = _run_builder_step(
                report,
                step="rule_scoring",
                artifact_key=_ARTIFACT_KEYS["rule_scoring"],
                builder=_rule_score_builder,
                skip_reason="missing rule_score_report and no _rule_score_builder was provided.",
                kwargs={
                    "replay_batch_result": replay_artifact,
                    "symbol": normalized_symbol,
                    "lookback_days": lookback_days,
                },
            )

    lifecycle_artifact = _store_existing_artifact(
        report,
        step="rule_lifecycle",
        artifact_key=_ARTIFACT_KEYS["rule_lifecycle"],
        artifact=rule_lifecycle_report,
    )
    if lifecycle_artifact is None:
        if score_artifact is None:
            report["step_status"]["rule_lifecycle"] = "skipped"
            report["warnings"].append("rule_lifecycle: missing rule_score_report; unable to build lifecycle report.")
        else:
            lifecycle_artifact = _run_builder_step(
                report,
                step="rule_lifecycle",
                artifact_key=_ARTIFACT_KEYS["rule_lifecycle"],
                builder=_rule_lifecycle_builder,
                skip_reason="missing rule_lifecycle_report and no _rule_lifecycle_builder was provided.",
                kwargs={
                    "rule_score_report": score_artifact,
                    "symbol": normalized_symbol,
                },
            )

    active_pool_artifact = _store_existing_artifact(
        report,
        step="active_pool",
        artifact_key=_ARTIFACT_KEYS["active_pool"],
        artifact=active_pool_report,
    )
    if active_pool_artifact is None:
        if lifecycle_artifact is None:
            report["step_status"]["active_pool"] = "skipped"
            report["warnings"].append("active_pool: missing rule_lifecycle_report; unable to build active pool recommendation.")
        else:
            active_pool_artifact = _run_builder_step(
                report,
                step="active_pool",
                artifact_key=_ARTIFACT_KEYS["active_pool"],
                builder=_active_pool_builder,
                skip_reason="missing active_pool_report and no _active_pool_builder was provided.",
                kwargs={
                    "rule_lifecycle_report": lifecycle_artifact,
                    "symbol": normalized_symbol,
                    "use_active_rule_pool": use_active_rule_pool,
                },
            )

    export_artifact = _store_existing_artifact(
        report,
        step="active_pool_export",
        artifact_key=_ARTIFACT_KEYS["active_pool_export"],
        artifact=active_pool_export,
    )
    if export_artifact is None:
        if active_pool_artifact is None:
            report["step_status"]["active_pool_export"] = "skipped"
            report["warnings"].append("active_pool_export: missing active_pool_report; unable to export active pool artifact.")
        else:
            export_artifact = _run_builder_step(
                report,
                step="active_pool_export",
                artifact_key=_ARTIFACT_KEYS["active_pool_export"],
                builder=_active_pool_export_builder,
                skip_reason="missing active_pool_export and no _active_pool_export_builder was provided.",
                kwargs={
                    "active_pool_report": active_pool_artifact,
                    "symbol": normalized_symbol,
                    "run_date": resolved_run_date,
                },
            )

    validation_artifact = _store_existing_artifact(
        report,
        step="validation",
        artifact_key=_ARTIFACT_KEYS["validation"],
        artifact=validation_report,
    )
    if validation_artifact is None:
        validation_artifact = _run_builder_step(
            report,
            step="validation",
            artifact_key=_ARTIFACT_KEYS["validation"],
            builder=_validation_builder,
            skip_reason="missing validation_report and no _validation_builder was provided.",
            kwargs={
                "replay_batch_result": replay_artifact,
                "active_pool_export": export_artifact,
                "active_pool_report": active_pool_artifact,
                "symbol": normalized_symbol,
                "lookback_days": lookback_days,
                "recent_window_size": recent_window_size,
                "use_active_rule_pool": use_active_rule_pool,
            },
        )

    calibration_artifact = _store_existing_artifact(
        report,
        step="calibration",
        artifact_key=_ARTIFACT_KEYS["calibration"],
        artifact=calibration_report,
    )
    if calibration_artifact is None:
        if validation_artifact is None:
            report["step_status"]["calibration"] = "skipped"
            report["warnings"].append("calibration: missing validation_report; unable to build calibration report.")
        else:
            calibration_artifact = _run_builder_step(
                report,
                step="calibration",
                artifact_key=_ARTIFACT_KEYS["calibration"],
                builder=_calibration_builder,
                skip_reason="missing calibration_report and no _calibration_builder was provided.",
                kwargs={
                    "validation_report": validation_artifact,
                    "rule_lifecycle_report": lifecycle_artifact,
                    "rule_score_report": score_artifact,
                    "symbol": normalized_symbol,
                },
            )

    promotion_artifact = _store_existing_artifact(
        report,
        step="promotion",
        artifact_key=_ARTIFACT_KEYS["promotion"],
        artifact=promotion_report,
    )
    if promotion_artifact is None:
        if calibration_artifact is None:
            report["step_status"]["promotion"] = "skipped"
            report["warnings"].append("promotion: missing calibration_report; unable to build promotion report.")
        else:
            promotion_artifact = _run_builder_step(
                report,
                step="promotion",
                artifact_key=_ARTIFACT_KEYS["promotion"],
                builder=_promotion_builder,
                skip_reason="missing promotion_report and no _promotion_builder was provided.",
                kwargs={
                    "calibration_report": calibration_artifact,
                    "validation_report": validation_artifact,
                    "rule_lifecycle_report": lifecycle_artifact,
                    "symbol": normalized_symbol,
                },
            )

    drift_artifact = _store_existing_artifact(
        report,
        step="drift",
        artifact_key=_ARTIFACT_KEYS["drift"],
        artifact=drift_report,
    )
    if drift_artifact is None:
        if validation_artifact is None:
            report["step_status"]["drift"] = "skipped"
            report["warnings"].append("drift: missing validation_report; unable to build drift report.")
        else:
            drift_artifact = _run_builder_step(
                report,
                step="drift",
                artifact_key=_ARTIFACT_KEYS["drift"],
                builder=_drift_builder,
                skip_reason="missing drift_report and no _drift_builder was provided.",
                kwargs={
                    "validation_report": validation_artifact,
                    "recent_window_size": recent_window_size,
                    "symbol": normalized_symbol,
                },
            )

    report["headline_metrics"] = {
        "total_replay_cases": _extract_total_replay_cases(replay_artifact),
        "direction_accuracy": _extract_direction_accuracy(replay_artifact, validation_artifact),
        "active_rule_count": _extract_active_rule_count(active_pool_artifact, export_artifact),
        "promote_candidate_count": _extract_promote_candidate_count(promotion_artifact),
        "drift_candidate_count": _extract_drift_candidate_count(drift_artifact),
    }
    report["ready"] = _compute_ready(report)
    report["summary"] = _build_summary(report)
    return report


def build_daily_training_report(**kwargs: Any) -> dict[str, Any]:
    return run_daily_training_pipeline(**kwargs)
