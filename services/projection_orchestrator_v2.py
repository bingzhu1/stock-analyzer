"""Projection v2 orchestration skeleton.

This module hardens the command-facing projection flow into fixed stages while
reusing the existing projection orchestrator. It does not change scanner,
predict, matching, or projection scoring rules.
"""

from __future__ import annotations

from typing import Any, Callable

from services.final_decision import build_final_decision
from services.historical_probability import build_historical_probability
from services.peer_adjustment import build_peer_adjustment
from services.projection_orchestrator import build_projection_orchestrator_result
from services.projection_chain_contract import (
    build_feature_payload_from_recent_window,
    build_unified_projection_payload,
)
from services.exclusion_layer import run_exclusion_layer
from services.main_projection_layer import build_main_projection_layer
from services.consistency_layer import build_consistency_layer
from services.primary_20day_analysis import build_primary_20day_analysis
from services.projection_rule_preflight import build_projection_rule_preflight


_PEER_SYMBOLS = ["NVDA", "SOXX", "QQQ"]
_STEP_ORDER = (
    "preflight",
    "primary_analysis",
    "peer_adjustment",
    "historical_probability",
    "final_decision",
)


def _empty_status() -> dict[str, str]:
    return {step: "skipped" for step in _STEP_ORDER} | {"final_decision": "failed"}


def _trace(trace: list[dict[str, str]], step: str, status: str, message: str) -> None:
    trace.append({"step": step, "status": status, "message": message})


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _clean_str(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"none", "null"} else text


_EMPTY_PREFLIGHT: dict[str, Any] = {
    "kind": "projection_rule_preflight",
    "ready": True,
    "matched_rules": [],
    "rule_warnings": [],
    "rule_adjustments": [],
    "summary": "当前未接入历史规则或未命中规则。",
    "warnings": [],
    "source_counts": {"memory_items": 0, "review_items": 0, "matched_rule_count": 0},
}


def _build_feature_payload(
    *,
    symbol: str,
    primary_analysis: dict[str, Any],
    scan_result: dict[str, Any],
) -> dict[str, Any]:
    primary = _as_dict(primary_analysis)
    scan = _as_dict(scan_result)
    features = _as_dict(primary.get("features"))
    recent_window = scan.get("avgo_recent_20")
    if not isinstance(recent_window, list):
        recent_window = []

    feature_payload = build_feature_payload_from_recent_window(
        recent_window=recent_window,
        symbol=symbol,
        target_ctx={
            "ret5": features.get("ret_5d"),
        },
        feature_overrides={
            # Keep the new chain key names stable even when the legacy source
            # only provides a 5-day volume ratio.
            "pos20": features.get("pos_20d"),
            "vol_ratio20": features.get("vol_ratio_5d"),
        },
    )
    return feature_payload


def _build_standardized_chain(
    *,
    symbol: str,
    primary_analysis: dict[str, Any],
    scan_result: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    historical_match_result = _as_dict(_as_dict(scan_result).get("historical_match_summary"))
    feature_payload = _build_feature_payload(
        symbol=symbol,
        primary_analysis=primary_analysis,
        scan_result=scan_result,
    )
    exclusion_result = run_exclusion_layer(feature_payload)
    main_projection = build_main_projection_layer(
        current_20day_features=feature_payload,
        exclusion_result=exclusion_result,
        historical_match_result=historical_match_result,
        peer_alignment=_as_dict(exclusion_result.get("peer_alignment")),
        symbol=symbol,
    )
    consistency = build_consistency_layer(
        exclusion_result=exclusion_result,
        main_projection_result=main_projection,
        peer_alignment=_as_dict(exclusion_result.get("peer_alignment")),
        historical_match_result=historical_match_result,
        symbol=symbol,
    )
    return feature_payload, exclusion_result, main_projection, consistency


def _build_preflight(
    *,
    symbol: str,
    target_date: str | None,
    lookback_days: int,
    warnings: list[str],
    trace: list[dict[str, str]],
    rule_preflight_builder: Callable[..., dict[str, Any]],
) -> tuple[str, dict[str, Any]]:
    try:
        result = rule_preflight_builder(
            symbol=symbol,
            target_date=target_date,
            lookback_days=lookback_days,
        )
    except Exception as exc:
        message = f"preflight 失败：{exc}"
        warnings.append(message)
        _trace(trace, "preflight", "skipped", message)
        return "skipped", dict(_EMPTY_PREFLIGHT)

    result = _as_dict(result)
    preflight_warnings = [str(w) for w in result.get("warnings", []) if str(w).strip()]
    warnings.extend(preflight_warnings)

    if not result.get("ready"):
        message = str(result.get("summary") or "preflight 未返回可用结果，已按安全降级跳过。")
        if message not in warnings:
            warnings.append(message)
        _trace(trace, "preflight", "skipped", message)
        return "skipped", result or dict(_EMPTY_PREFLIGHT)

    matched = len(result.get("matched_rules") or [])
    summary = str(result.get("summary") or (
        f"preflight 完成，命中 {matched} 条历史提醒。" if matched else "当前未接入历史规则或未命中规则。"
    ))
    _trace(trace, "preflight", "success", summary)
    return "success", result


def _build_primary_analysis(
    legacy_result: dict[str, Any],
    *,
    symbol: str,
    lookback_days: int,
    target_date: str | None,
    warnings: list[str],
    trace: list[dict[str, str]],
    primary_analysis_builder: Callable[..., dict[str, Any]],
) -> tuple[str, dict[str, Any]]:
    try:
        result = primary_analysis_builder(
            symbol=symbol,
            lookback_days=lookback_days,
            target_date=target_date,
        )
    except Exception as exc:
        message = f"primary_analysis 失败：{exc}"
        warnings.append(message)
        _trace(trace, "primary_analysis", "failed", message)
        return "failed", {
            "kind": "primary_20day_analysis",
            "symbol": symbol,
            "direction": "unavailable",
            "confidence": "low",
            "summary": message,
            "basis": [],
            "lookback_days": lookback_days,
        }

    if not isinstance(result, dict) or not result.get("ready"):
        message = str(
            _as_dict(result).get("summary")
            or "primary_analysis 失败：最近20天主分析不可用。"
        )
        warnings.append(message)
        _trace(trace, "primary_analysis", "failed", message)
        return "failed", _as_dict(result) or {
            "kind": "primary_20day_analysis",
            "symbol": symbol,
            "direction": "unknown",
            "confidence": "unknown",
            "summary": message,
            "basis": [],
            "lookback_days": lookback_days,
        }

    report = _as_dict(legacy_result.get("projection_report"))
    if report:
        result = dict(result)
        result["legacy_projection_report"] = report
    _trace(trace, "primary_analysis", "success", "AVGO 最近窗口主分析完成。")
    return "success", result


def _build_peer_adjustment(
    scan_result: dict[str, Any],
    *,
    primary_analysis: dict[str, Any],
    symbol: str,
    include_peers: bool,
    warnings: list[str],
    trace: list[dict[str, str]],
    peer_adjustment_builder: Callable[..., dict[str, Any]],
) -> tuple[str, dict[str, Any]]:
    if not include_peers:
        message = "peer_adjustment 已按参数关闭。"
        result = peer_adjustment_builder(
            primary_analysis=primary_analysis,
            peer_snapshot=None,
            symbol=symbol,
            peer_symbols=list(_PEER_SYMBOLS),
        )
        result = dict(result)
        result["summary"] = "peer_adjustment 已按参数关闭，未获 peers 确认。"
        result["warnings"] = list(dict.fromkeys([*result.get("warnings", []), message]))
        warnings.append(message)
        _trace(trace, "peer_adjustment", "skipped", message)
        return "skipped", result

    try:
        result = peer_adjustment_builder(
            primary_analysis=primary_analysis,
            peer_snapshot=scan_result,
            symbol=symbol,
            peer_symbols=list(_PEER_SYMBOLS),
        )
    except Exception as exc:
        message = f"peer_adjustment 失败：{exc}"
        warnings.append(message)
        _trace(trace, "peer_adjustment", "skipped", message)
        return "skipped", build_peer_adjustment(
            primary_analysis=primary_analysis,
            peer_snapshot=None,
            symbol=symbol,
            peer_symbols=list(_PEER_SYMBOLS),
        )

    result = _as_dict(result)
    if not result.get("ready"):
        result_warnings = [str(item) for item in result.get("warnings", []) if str(item).strip()]
        message = str(result.get("summary") or "peer_adjustment 缺少 NVDA / SOXX / QQQ 对照数据，已降级。")
        warnings.extend(result_warnings or [message])
        _trace(trace, "peer_adjustment", "skipped", message)
        return "skipped", result

    summary = str(result.get("summary") or "peer_adjustment 完成。")
    _trace(trace, "peer_adjustment", "success", summary)
    return "success", result


def _build_historical_probability(
    scan_result: dict[str, Any],
    *,
    primary_analysis: dict[str, Any],
    symbol: str,
    target_date: str | None,
    include_history_prob: bool,
    warnings: list[str],
    trace: list[dict[str, str]],
    historical_probability_builder: Callable[..., dict[str, Any]],
) -> tuple[str, dict[str, Any]]:
    if not include_history_prob:
        message = "historical_probability 已按参数关闭。"
        result = historical_probability_builder(
            primary_analysis=primary_analysis,
            symbol=symbol,
            historical_summary=None,
            context_features=scan_result,
            coded_history=_as_dict(scan_result).get("coded_history"),
            feature_history=_as_dict(scan_result).get("feature_history"),
            as_of_date=target_date,
        )
        result = dict(result)
        result["summary"] = "historical_probability 已按参数关闭，未获得历史概率支持。"
        result["warnings"] = list(dict.fromkeys([*result.get("warnings", []), message]))
        warnings.append(message)
        _trace(trace, "historical_probability", "skipped", message)
        return "skipped", result

    try:
        result = historical_probability_builder(
            primary_analysis=primary_analysis,
            symbol=symbol,
            historical_summary=_as_dict(scan_result.get("historical_match_summary")),
            context_features=scan_result,
            coded_history=_as_dict(scan_result).get("coded_history"),
            feature_history=_as_dict(scan_result).get("feature_history"),
            as_of_date=target_date,
        )
    except Exception as exc:
        message = f"historical_probability 失败：{exc}"
        warnings.append(message)
        _trace(trace, "historical_probability", "skipped", message)
        return "skipped", build_historical_probability(
            primary_analysis=primary_analysis,
            symbol=symbol,
            historical_summary=None,
            context_features=scan_result,
            coded_history=_as_dict(scan_result).get("coded_history"),
            feature_history=_as_dict(scan_result).get("feature_history"),
            as_of_date=target_date,
        )

    result = _as_dict(result)
    if not result.get("ready"):
        result_warnings = [str(item) for item in result.get("warnings", []) if str(item).strip()]
        message = str(result.get("summary") or "historical_probability 未接入或样本不足，已降级。")
        warnings.extend(result_warnings or [message])
        _trace(trace, "historical_probability", "skipped", message)
        return "skipped", result

    result_warnings = [str(item) for item in result.get("warnings", []) if str(item).strip()]
    warnings.extend(result_warnings)
    summary = str(result.get("summary") or "historical_probability 完成。")
    _trace(trace, "historical_probability", "success", summary)
    return "success", result


def _build_final_decision(
    *,
    primary_status: str,
    primary_analysis: dict[str, Any],
    peer_status: str,
    peer_adjustment: dict[str, Any],
    historical_status: str,
    historical_probability: dict[str, Any],
    preflight: dict[str, Any],
    symbol: str,
    warnings: list[str],
    trace: list[dict[str, str]],
    final_decision_builder: Callable[..., dict[str, Any]],
) -> tuple[str, dict[str, Any]]:
    try:
        result = final_decision_builder(
            primary_analysis=primary_analysis,
            peer_adjustment=peer_adjustment,
            historical_probability=historical_probability,
            preflight=preflight,
            symbol=symbol,
        )
    except Exception as exc:
        message = f"final_decision 失败：{exc}"
        warnings.append(message)
        _trace(trace, "final_decision", "failed", message)
        return "failed", build_final_decision(
            primary_analysis={"ready": False, "direction": "unknown", "confidence": "unknown"},
            peer_adjustment=peer_adjustment,
            historical_probability=historical_probability,
            preflight=preflight,
            symbol=symbol,
        )

    result = _as_dict(result)
    result_warnings = [str(item) for item in result.get("warnings", []) if str(item).strip()]
    warnings.extend(result_warnings)
    if primary_status != "success" or not result.get("ready"):
        message = str(result.get("summary") or "final_decision 失败：主分析不可用，不能伪造完整结论。")
        _trace(trace, "final_decision", "failed", message)
        return "failed", result

    summary = str(result.get("summary") or "final_decision 已综合主分析、peer 修正和历史概率层。")
    _trace(trace, "final_decision", "success", summary)
    return "success", result


def run_projection_v2(
    *,
    symbol: str = "AVGO",
    lookback_days: int = 20,
    target_date: str | None = None,
    include_peers: bool = True,
    include_history_prob: bool = True,
    _projection_runner: Callable[..., dict[str, Any]] = build_projection_orchestrator_result,
    _primary_analysis_builder: Callable[..., dict[str, Any]] = build_primary_20day_analysis,
    _peer_adjustment_builder: Callable[..., dict[str, Any]] = build_peer_adjustment,
    _historical_probability_builder: Callable[..., dict[str, Any]] = build_historical_probability,
    _final_decision_builder: Callable[..., dict[str, Any]] = build_final_decision,
    _rule_preflight_builder: Callable[..., dict[str, Any]] = build_projection_rule_preflight,
) -> dict[str, Any]:
    """Run the fixed projection v2 orchestration chain."""
    normalized_symbol = str(symbol or "AVGO").strip().upper() or "AVGO"
    warnings: list[str] = []
    trace: list[dict[str, str]] = []
    step_status = _empty_status()
    legacy_result: dict[str, Any] = {}
    feature_payload: dict[str, Any] = {"symbol": normalized_symbol}
    exclusion_result: dict[str, Any] = {
        "excluded": False,
        "action": "allow",
        "triggered_rule": None,
        "reasons": ["主推演标准化链未运行，排除层保持安全降级。"],
        "peer_alignment": {},
        "feature_snapshot": {},
    }
    main_projection: dict[str, Any] = {
        "predicted_top1": {"state": None, "probability": None},
        "predicted_top2": {"state": None, "probability": None},
        "state_probabilities": {},
        "rationale": ["主推演标准化链未运行。"],
    }
    consistency: dict[str, Any] = {
        "consistency_flag": "unknown",
        "consistency_score": 0.0,
        "conflict_reasons": ["主推演标准化链未运行，一致性校验未完成。"],
        "summary": "标准化一致性链未运行，已安全降级。",
    }
    historical_match_result: dict[str, Any] = {}

    try:
        legacy_result = _projection_runner(
            symbol=normalized_symbol,
            lookback_days=lookback_days,
        )
    except Exception as exc:
        message = f"primary_analysis 失败：{exc}"
        warnings.append(message)
        _trace(trace, "preflight", "skipped", "preflight 未执行：主链路入口失败。")
        _trace(trace, "primary_analysis", "failed", message)
        preflight = dict(_EMPTY_PREFLIGHT)
        primary = {
            "direction": "unavailable",
            "confidence": "low",
            "summary": message,
            "basis": [],
            "lookback_days": lookback_days,
        }
        peer = build_peer_adjustment(
            primary_analysis={"ready": False, "direction": "unknown", "confidence": "unknown"},
            peer_snapshot=None,
            symbol=normalized_symbol,
            peer_symbols=list(_PEER_SYMBOLS),
        )
        historical = build_historical_probability(
            primary_analysis={"ready": False, "direction": "unknown", "confidence": "unknown"},
            symbol=normalized_symbol,
            historical_summary=None,
            context_features=None,
        )
        final_status, final = _build_final_decision(
            primary_status="failed",
            primary_analysis=primary,
            peer_status="skipped",
            peer_adjustment=peer,
            historical_status="skipped",
            historical_probability=historical,
            preflight=preflight,
            symbol=normalized_symbol,
            warnings=warnings,
            trace=trace,
            final_decision_builder=_final_decision_builder,
        )
        step_status.update({
            "preflight": "skipped",
            "primary_analysis": "failed",
            "peer_adjustment": "skipped",
            "historical_probability": "skipped",
            "final_decision": final_status,
        })
        return build_unified_projection_payload(
            kind="projection_v2_report",
            symbol=normalized_symbol,
            ready=False,
            feature_payload=feature_payload,
            exclusion_result=exclusion_result,
            main_projection=main_projection,
            consistency=consistency,
            historical_match_result=historical_match_result,
            prediction_log_id=None,
            extra={
                "lookback_days": lookback_days,
                "target_date": target_date,
                "preflight": preflight,
                "primary_analysis": primary,
                "peer_adjustment": peer,
                "historical_probability": historical,
                "final_decision": final,
                "warnings": list(dict.fromkeys(warnings)),
                "trace": trace,
                "step_status": step_status,
            },
        )

    preflight_status, preflight = _build_preflight(
        symbol=normalized_symbol,
        target_date=target_date,
        lookback_days=lookback_days,
        warnings=warnings,
        trace=trace,
        rule_preflight_builder=_rule_preflight_builder,
    )
    primary_status, primary = _build_primary_analysis(
        legacy_result,
        symbol=normalized_symbol,
        lookback_days=lookback_days,
        target_date=target_date,
        warnings=warnings,
        trace=trace,
        primary_analysis_builder=_primary_analysis_builder,
    )
    scan_result = _as_dict(legacy_result.get("scan_result"))
    peer_status, peer = _build_peer_adjustment(
        scan_result,
        primary_analysis=primary,
        symbol=normalized_symbol,
        include_peers=include_peers,
        warnings=warnings,
        trace=trace,
        peer_adjustment_builder=_peer_adjustment_builder,
    )
    historical_status, historical = _build_historical_probability(
        scan_result,
        primary_analysis=primary,
        symbol=normalized_symbol,
        target_date=target_date,
        include_history_prob=include_history_prob,
        warnings=warnings,
        trace=trace,
        historical_probability_builder=_historical_probability_builder,
    )
    final_status, final = _build_final_decision(
        primary_status=primary_status,
        primary_analysis=primary,
        peer_status=peer_status,
        peer_adjustment=peer,
        historical_status=historical_status,
        historical_probability=historical,
        preflight=preflight,
        symbol=normalized_symbol,
        warnings=warnings,
        trace=trace,
        final_decision_builder=_final_decision_builder,
    )
    step_status.update({
        "preflight": preflight_status,
        "primary_analysis": primary_status,
        "peer_adjustment": peer_status,
        "historical_probability": historical_status,
        "final_decision": final_status,
    })
    ready = primary_status == "success" and final_status == "success"
    feature_payload, exclusion_result, main_projection, consistency = _build_standardized_chain(
        symbol=normalized_symbol,
        primary_analysis=primary,
        scan_result=scan_result,
    )
    historical_match_result = _as_dict(scan_result.get("historical_match_summary"))
    return build_unified_projection_payload(
        kind="projection_v2_report",
        symbol=normalized_symbol,
        ready=ready,
        feature_payload=feature_payload,
        exclusion_result=exclusion_result,
        main_projection=main_projection,
        consistency=consistency,
        historical_match_result=historical_match_result,
        prediction_log_id=None,
        extra={
            "lookback_days": lookback_days,
            "target_date": primary.get("target_date") or target_date,
            "preflight": preflight,
            "primary_analysis": primary,
            "peer_adjustment": peer,
            "historical_probability": historical,
            "final_decision": final,
            "warnings": list(dict.fromkeys(warnings)),
            "trace": trace,
            "step_status": step_status,
        },
    )


orchestrate_projection_v2 = run_projection_v2
