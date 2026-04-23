from __future__ import annotations

from datetime import date
from typing import Any, Callable


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _clean_text(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text if text else fallback


def _normalize_symbol(symbol: Any) -> str:
    return _clean_text(symbol, fallback="AVGO").upper() or "AVGO"


def _resolve_run_date(run_date: str | None) -> str:
    return _clean_text(run_date, fallback=date.today().isoformat())


def _empty_run(*, symbol: str, run_date: str) -> dict[str, Any]:
    return {
        "kind": "daily_automation_run",
        "ready": False,
        "symbol": symbol,
        "run_date": run_date,
        "run_status": "failed",
        "step_status": {
            "pipeline": "skipped",
            "summary": "skipped",
            "dashboard": "skipped",
        },
        "artifacts": {
            "daily_training_report": None,
            "daily_training_brief": None,
            "dashboard_view": None,
        },
        "headline": {
            "overall_status": "unknown",
            "direction_accuracy": None,
            "active_rule_count": 0,
            "promote_candidate_count": 0,
            "production_candidate_count": 0,
            "drift_candidate_count": 0,
        },
        "summary": "",
        "warnings": [],
    }


def _artifact_status(artifact: dict[str, Any]) -> str:
    return "ok" if artifact.get("ready") is True else "degraded"


def _extend_warnings(
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
    run: dict[str, Any],
    *,
    step: str,
    artifact_key: str,
    artifact: Any,
) -> dict[str, Any] | None:
    if artifact is None:
        return None

    if not isinstance(artifact, dict):
        run["step_status"][step] = "degraded"
        run["artifacts"][artifact_key] = {}
        run["warnings"].append(f"{step}: provided artifact was not a dict; retained as empty degraded artifact.")
        return run["artifacts"][artifact_key]

    run["artifacts"][artifact_key] = artifact
    run["step_status"][step] = _artifact_status(artifact)
    _extend_warnings(run["warnings"], step=step, artifact=artifact)
    return artifact


def _run_builder_step(
    run: dict[str, Any],
    *,
    step: str,
    artifact_key: str,
    builder: Callable[..., dict[str, Any]] | None,
    skip_reason: str,
    kwargs: dict[str, Any],
    failure_as: str = "failed",
) -> dict[str, Any] | None:
    if builder is None:
        run["step_status"][step] = "skipped" if failure_as == "skipped" else "failed"
        run["warnings"].append(f"{step}: {skip_reason}")
        return None

    try:
        artifact = builder(**kwargs)
    except Exception as exc:
        run["step_status"][step] = "failed"
        run["artifacts"][artifact_key] = None
        run["warnings"].append(f"{step}: builder execution failed: {exc}")
        return None

    if not isinstance(artifact, dict):
        run["step_status"][step] = "degraded"
        run["artifacts"][artifact_key] = {}
        run["warnings"].append(f"{step}: builder returned a non-dict artifact; treated as degraded.")
        return run["artifacts"][artifact_key]

    run["artifacts"][artifact_key] = artifact
    run["step_status"][step] = _artifact_status(artifact)
    _extend_warnings(run["warnings"], step=step, artifact=artifact)
    return artifact


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _headline_from_brief(brief: dict[str, Any]) -> dict[str, Any]:
    metrics = _as_dict(brief.get("headline_metrics"))
    return {
        "overall_status": _clean_text(brief.get("overall_status"), fallback="unknown"),
        "direction_accuracy": _safe_float(metrics.get("direction_accuracy")),
        "active_rule_count": _safe_int(metrics.get("active_rule_count")) if "active_rule_count" in metrics else None,
        "promote_candidate_count": _safe_int(metrics.get("promote_candidate_count")) if "promote_candidate_count" in metrics else None,
        "production_candidate_count": None,
        "drift_candidate_count": _safe_int(metrics.get("drift_candidate_count")) if "drift_candidate_count" in metrics else None,
    }


def _headline_from_dashboard(dashboard: dict[str, Any]) -> dict[str, Any]:
    header = _as_dict(dashboard.get("header"))
    cards = _as_dict(dashboard.get("headline_cards"))
    return {
        "overall_status": _clean_text(header.get("overall_status"), fallback="unknown"),
        "direction_accuracy": _safe_float(cards.get("direction_accuracy")),
        "active_rule_count": _safe_int(cards.get("active_rule_count")) if "active_rule_count" in cards else None,
        "promote_candidate_count": _safe_int(cards.get("promote_candidate_count")) if "promote_candidate_count" in cards else None,
        "production_candidate_count": _safe_int(cards.get("production_candidate_count")) if "production_candidate_count" in cards else None,
        "drift_candidate_count": _safe_int(cards.get("drift_candidate_count")) if "drift_candidate_count" in cards else None,
    }


def _headline_from_report(report: dict[str, Any]) -> dict[str, Any]:
    metrics = _as_dict(report.get("headline_metrics"))
    step_status = _as_dict(report.get("step_status"))
    overall_status = "unknown"
    if any(status == "failed" for status in step_status.values()):
        overall_status = "failed"
    elif any(status == "degraded" for status in step_status.values()):
        overall_status = "degraded"
    elif any(status == "skipped" for status in step_status.values()):
        overall_status = "mixed"
    elif step_status:
        overall_status = "healthy"

    return {
        "overall_status": overall_status,
        "direction_accuracy": _safe_float(metrics.get("direction_accuracy")),
        "active_rule_count": _safe_int(metrics.get("active_rule_count")) if "active_rule_count" in metrics else None,
        "promote_candidate_count": _safe_int(metrics.get("promote_candidate_count")) if "promote_candidate_count" in metrics else None,
        "production_candidate_count": None,
        "drift_candidate_count": _safe_int(metrics.get("drift_candidate_count")) if "drift_candidate_count" in metrics else None,
    }


def _build_headline(
    *,
    daily_training_report: dict[str, Any] | None,
    daily_training_brief: dict[str, Any] | None,
    dashboard_view: dict[str, Any] | None,
) -> dict[str, Any]:
    headline = {
        "overall_status": "unknown",
        "direction_accuracy": None,
        "active_rule_count": 0,
        "promote_candidate_count": 0,
        "production_candidate_count": 0,
        "drift_candidate_count": 0,
    }

    report = _as_dict(daily_training_report)
    brief = _as_dict(daily_training_brief)
    dashboard = _as_dict(dashboard_view)

    if report:
        headline.update(_headline_from_report(report))
    if dashboard:
        dashboard_headline = _headline_from_dashboard(dashboard)
        for key, value in dashboard_headline.items():
            if key == "direction_accuracy":
                if value is not None:
                    headline[key] = value
            elif key == "overall_status":
                if value != "unknown":
                    headline[key] = value
            elif value is not None:
                headline[key] = value
        if dashboard_headline["production_candidate_count"] is not None:
            headline["production_candidate_count"] = dashboard_headline["production_candidate_count"]
    if brief:
        brief_headline = _headline_from_brief(brief)
        for key, value in brief_headline.items():
            if key == "direction_accuracy":
                if value is not None:
                    headline[key] = value
            elif key == "overall_status":
                if value != "unknown":
                    headline[key] = value
            elif value is not None:
                headline[key] = value

    for key in (
        "active_rule_count",
        "promote_candidate_count",
        "production_candidate_count",
        "drift_candidate_count",
    ):
        if headline[key] is None:
            headline[key] = 0

    return headline


def _compute_run_status(step_status: dict[str, str]) -> str:
    pipeline_status = step_status.get("pipeline")
    if pipeline_status == "failed":
        return "failed"
    if pipeline_status == "skipped":
        return "failed"
    if all(status == "ok" for status in step_status.values()):
        return "ok"
    if pipeline_status in {"ok", "degraded"}:
        return "partial"
    return "failed"


def _build_summary(run: dict[str, Any]) -> str:
    headline = _as_dict(run.get("headline"))
    step_status = _as_dict(run.get("step_status"))
    parts = [
        f"{run['symbol']} automation run for {run['run_date']} finished with status {run['run_status']}.",
        f"Overall training status={headline.get('overall_status', 'unknown')}.",
        (
            f"Direction accuracy={headline.get('direction_accuracy') if headline.get('direction_accuracy') is not None else 'unavailable'}, "
            f"active rules={headline.get('active_rule_count', 0)}, "
            f"promote candidates={headline.get('promote_candidate_count', 0)}, "
            f"production candidates={headline.get('production_candidate_count', 0)}, "
            f"drift candidates={headline.get('drift_candidate_count', 0)}."
        ),
    ]

    if step_status.get("summary") == "ok":
        parts.append("Usable daily brief was generated.")
    elif step_status.get("summary") in {"degraded", "failed", "skipped"}:
        parts.append(f"Daily brief status={step_status.get('summary')}.")

    if step_status.get("dashboard") == "ok":
        parts.append("Dashboard payload is available.")
    elif step_status.get("dashboard") in {"degraded", "failed", "skipped"}:
        parts.append(f"Dashboard status={step_status.get('dashboard')}.")

    return " ".join(parts)


def run_daily_automation(
    *,
    symbol: str = "AVGO",
    run_date: str | None = None,
    daily_training_report: dict | None = None,
    daily_training_brief: dict | None = None,
    dashboard_view: dict | None = None,
    _pipeline_runner: Callable[..., dict[str, Any]] | None = None,
    _summary_builder: Callable[..., dict[str, Any]] | None = None,
    _dashboard_builder: Callable[..., dict[str, Any]] | None = None,
    max_highlights: int = 5,
    use_active_rule_pool: bool = True,
) -> dict[str, Any]:
    normalized_symbol = _normalize_symbol(symbol)
    resolved_run_date = _resolve_run_date(run_date)
    run = _empty_run(symbol=normalized_symbol, run_date=resolved_run_date)

    pipeline_artifact = _store_existing_artifact(
        run,
        step="pipeline",
        artifact_key="daily_training_report",
        artifact=daily_training_report,
    )
    if pipeline_artifact is None:
        pipeline_artifact = _run_builder_step(
            run,
            step="pipeline",
            artifact_key="daily_training_report",
            builder=_pipeline_runner,
            skip_reason="missing daily_training_report and no _pipeline_runner was provided.",
            kwargs={
                "symbol": normalized_symbol,
                "run_date": resolved_run_date,
                "use_active_rule_pool": use_active_rule_pool,
            },
            failure_as="failed",
        )

    brief_artifact = _store_existing_artifact(
        run,
        step="summary",
        artifact_key="daily_training_brief",
        artifact=daily_training_brief,
    )
    if brief_artifact is None:
        if pipeline_artifact is None:
            run["step_status"]["summary"] = "skipped"
            run["warnings"].append("summary: skipped because daily_training_report is unavailable.")
        else:
            brief_artifact = _run_builder_step(
                run,
                step="summary",
                artifact_key="daily_training_brief",
                builder=_summary_builder,
                skip_reason="missing daily_training_brief and no _summary_builder was provided.",
                kwargs={
                    "daily_training_report": pipeline_artifact,
                    "symbol": normalized_symbol,
                    "max_highlights": max_highlights,
                },
                failure_as="skipped",
            )

    dashboard_artifact = _store_existing_artifact(
        run,
        step="dashboard",
        artifact_key="dashboard_view",
        artifact=dashboard_view,
    )
    if dashboard_artifact is None:
        if pipeline_artifact is None and brief_artifact is None:
            run["step_status"]["dashboard"] = "skipped"
            run["warnings"].append("dashboard: skipped because upstream automation artifacts are unavailable.")
        else:
            dashboard_artifact = _run_builder_step(
                run,
                step="dashboard",
                artifact_key="dashboard_view",
                builder=_dashboard_builder,
                skip_reason="missing dashboard_view and no _dashboard_builder was provided.",
                kwargs={
                    "daily_training_brief": brief_artifact,
                    "active_rule_pool_report": _as_dict(_as_dict(pipeline_artifact).get("artifacts")).get("active_rule_pool_report") if pipeline_artifact else None,
                    "active_rule_pool_export": _as_dict(_as_dict(pipeline_artifact).get("artifacts")).get("active_rule_pool_export") if pipeline_artifact else None,
                    "promotion_report": _as_dict(_as_dict(pipeline_artifact).get("artifacts")).get("active_rule_pool_promotion_report") if pipeline_artifact else None,
                    "promotion_adoption_handoff": None,
                    "drift_report": _as_dict(_as_dict(pipeline_artifact).get("artifacts")).get("active_rule_pool_drift_report") if pipeline_artifact else None,
                    "calibration_report": _as_dict(_as_dict(pipeline_artifact).get("artifacts")).get("active_rule_pool_calibration_report") if pipeline_artifact else None,
                },
                failure_as="skipped",
            )

    run["headline"] = _build_headline(
        daily_training_report=pipeline_artifact,
        daily_training_brief=brief_artifact,
        dashboard_view=dashboard_artifact,
    )
    run["run_status"] = _compute_run_status(_as_dict(run.get("step_status")))
    run["ready"] = run["step_status"].get("pipeline") in {"ok", "degraded"}
    run["summary"] = _build_summary(run)
    return run


def run_scheduled_training_cycle(**kwargs: Any) -> dict[str, Any]:
    return run_daily_automation(**kwargs)
