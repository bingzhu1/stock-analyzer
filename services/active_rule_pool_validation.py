"""Validate whether enabling active rule pool improves projection outcomes."""

from __future__ import annotations

from collections import Counter
from typing import Any


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _clean_text(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text if text else fallback


def _empty_confidence_distribution() -> dict[str, int]:
    return {
        "high": 0,
        "medium": 0,
        "low": 0,
        "unknown": 0,
    }


def _empty_risk_distribution() -> dict[str, int]:
    return {
        "low": 0,
        "medium": 0,
        "high": 0,
        "unknown": 0,
    }


def _empty_report() -> dict[str, Any]:
    return {
        "kind": "active_rule_pool_validation_report",
        "ready": False,
        "total_cases": 0,
        "comparable_cases": 0,
        "baseline_accuracy": None,
        "active_pool_accuracy": None,
        "accuracy_delta": None,
        "baseline_confidence_distribution": _empty_confidence_distribution(),
        "active_pool_confidence_distribution": _empty_confidence_distribution(),
        "baseline_risk_distribution": _empty_risk_distribution(),
        "active_pool_risk_distribution": _empty_risk_distribution(),
        "changed_cases": 0,
        "improved_cases": 0,
        "worsened_cases": 0,
        "neutral_cases": 0,
        "rule_effects": [],
        "top_helpful_rules": [],
        "top_unhelpful_rules": [],
        "summary": "",
        "warnings": [],
    }


def _safe_rate(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator / denominator, 4)


def _confidence_bucket(value: Any) -> str:
    text = _clean_text(value).lower()
    if text in {"high", "medium", "low"}:
        return text
    return "unknown"


def _risk_bucket(value: Any) -> str:
    text = _clean_text(value).lower()
    if text in {"low", "medium", "high"}:
        return text
    return "unknown"


def _preflight_from_result(result: dict[str, Any]) -> dict[str, Any]:
    snapshot = _as_dict(result.get("projection_snapshot"))
    return (
        _as_dict(snapshot.get("preflight"))
        or _as_dict(snapshot.get("rule_preflight"))
        or _as_dict(result.get("preflight"))
        or _as_dict(result.get("rule_preflight"))
    )


def _final_decision_from_result(result: dict[str, Any]) -> dict[str, Any]:
    snapshot = _as_dict(result.get("projection_snapshot"))
    return _as_dict(snapshot.get("final_decision")) or _as_dict(result.get("final_decision"))


def _case_key(result: dict[str, Any]) -> tuple[str, str] | None:
    snapshot = _as_dict(result.get("projection_snapshot"))
    as_of_date = _clean_text(result.get("as_of_date") or snapshot.get("analysis_date"))
    prediction_for_date = _clean_text(
        result.get("prediction_for_date") or snapshot.get("prediction_for_date")
    )
    if not as_of_date or not prediction_for_date:
        return None
    return as_of_date, prediction_for_date


def _extract_active_rule_hits(result: dict[str, Any]) -> list[dict[str, str]]:
    preflight = _preflight_from_result(result)
    hits: list[dict[str, str]] = []
    seen_keys: set[tuple[str, str]] = set()

    for raw_rule in _as_list(preflight.get("matched_rules")):
        rule = _as_dict(raw_rule)
        sources = [str(source).strip() for source in _as_list(rule.get("sources")) if str(source).strip()]
        if "active_pool" not in sources:
            continue
        rule_id = _clean_text(rule.get("rule_id"), fallback="unknown")
        title = _clean_text(rule.get("title"), fallback=rule_id)
        key = (rule_id, title)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        hits.append({"rule_id": rule_id, "title": title})

    return hits


def _extract_case(result: dict[str, Any]) -> dict[str, Any]:
    final = _final_decision_from_result(result)
    preflight = _preflight_from_result(result)
    review = _as_dict(result.get("review"))

    return {
        "final_direction": _clean_text(final.get("final_direction") or result.get("final_direction")),
        "final_confidence": _confidence_bucket(
            final.get("final_confidence") or result.get("final_confidence")
        ),
        "risk_level": _risk_bucket(final.get("risk_level") or result.get("risk_level")),
        "direction_correct": review.get("direction_correct"),
        "active_pool_used": bool(preflight.get("active_pool_used")),
        "active_pool_matches": int(_as_dict(preflight.get("source_counts")).get("active_pool_matches") or 0),
        "matched_rule_count": len(_as_list(preflight.get("matched_rules"))),
        "active_rule_hits": _extract_active_rule_hits(result),
    }


def _is_changed(baseline_case: dict[str, Any], active_case: dict[str, Any]) -> bool:
    comparable_fields = (
        "final_direction",
        "final_confidence",
        "risk_level",
        "active_pool_used",
        "active_pool_matches",
        "matched_rule_count",
    )
    return any(baseline_case.get(field) != active_case.get(field) for field in comparable_fields)


def _iter_indexed_results(results: list[dict[str, Any]] | None) -> dict[tuple[str, str], dict[str, Any]]:
    indexed: dict[tuple[str, str], dict[str, Any]] = {}
    for item in results or []:
        if not isinstance(item, dict):
            continue
        key = _case_key(item)
        if key is None or key in indexed:
            continue
        indexed[key] = item
    return indexed


def _distribution_report(counter: Counter[str], *, kind: str) -> dict[str, int]:
    if kind == "confidence":
        base = _empty_confidence_distribution()
    else:
        base = _empty_risk_distribution()
    for bucket in base:
        base[bucket] = counter.get(bucket, 0)
    return base


def _build_rule_notes(
    *,
    hit_count: int,
    improved_case_count: int,
    worsened_case_count: int,
    changed_case_count: int,
) -> str:
    if changed_case_count <= 0:
        return f"命中 {hit_count} 次，但当前没有观察到与结果变化直接相关的 paired case。"
    if improved_case_count > worsened_case_count:
        return (
            f"命中 {hit_count} 次，出现在 {changed_case_count} 个 changed cases 中，"
            f"其中 improved {improved_case_count} 次、worsened {worsened_case_count} 次。"
        )
    if worsened_case_count > improved_case_count:
        return (
            f"命中 {hit_count} 次，出现在 {changed_case_count} 个 changed cases 中，"
            f"其中 worsened {worsened_case_count} 次，高于 improved {improved_case_count} 次。"
        )
    return (
        f"命中 {hit_count} 次，出现在 {changed_case_count} 个 changed cases 中，"
        f"improved 与 worsened 都为 {improved_case_count} 次，当前更像中性影响。"
    )


def _summary(
    *,
    comparable_cases: int,
    baseline_accuracy: float | None,
    active_pool_accuracy: float | None,
    accuracy_delta: float | None,
    changed_cases: int,
    improved_cases: int,
    worsened_cases: int,
    neutral_cases: int,
    top_helpful_rules: list[dict[str, Any]],
    top_unhelpful_rules: list[dict[str, Any]],
    baseline_confidence_distribution: dict[str, int],
    active_confidence_distribution: dict[str, int],
    baseline_risk_distribution: dict[str, int],
    active_risk_distribution: dict[str, int],
) -> str:
    if comparable_cases <= 0:
        return "baseline 和 active-pool-enabled 结果当前无法按 as_of_date + prediction_for_date 对齐，暂时无法验证 active pool 的真实净效果。"

    parts = [f"共对齐 {comparable_cases} 个 paired cases。"]
    if baseline_accuracy is not None and active_pool_accuracy is not None and accuracy_delta is not None:
        parts.append(
            "方向准确率从 "
            f"{baseline_accuracy * 100:.1f}% 变为 {active_pool_accuracy * 100:.1f}% "
            f"(delta {accuracy_delta * 100:+.1f}pct)。"
        )
    else:
        parts.append("当前可判定的 direction_correct 样本不足，准确率对比证据有限。")

    parts.append(
        f"changed={changed_cases}，improved={improved_cases}，worsened={worsened_cases}，neutral={neutral_cases}。"
    )

    if active_confidence_distribution["low"] > baseline_confidence_distribution["low"]:
        parts.append("启用 active pool 后低置信度样本增加，说明系统有更保守的倾向。")
    if active_risk_distribution["high"] > baseline_risk_distribution["high"]:
        parts.append("同时高风险样本也有所增加，需要区分这是有效降温还是无效保守。")

    if top_helpful_rules:
        parts.append("当前最偏正向的规则相关样本集中在：" + "、".join(
            rule["title"] for rule in top_helpful_rules[:3]
        ) + "。")
    if top_unhelpful_rules:
        parts.append("当前最需要警惕的规则相关样本集中在：" + "、".join(
            rule["title"] for rule in top_unhelpful_rules[:3]
        ) + "。")
    return " ".join(parts)


def build_active_rule_pool_validation_report(
    *,
    baseline_results: list[dict[str, Any]] | None = None,
    active_pool_results: list[dict[str, Any]] | None = None,
    active_rule_pool_export: dict[str, Any] | None = None,
    symbol: str = "AVGO",
) -> dict[str, Any]:
    del active_rule_pool_export, symbol  # Reserved for future validation context.

    report = _empty_report()
    warnings: list[str] = []

    if not isinstance(baseline_results, list):
        report["summary"] = "缺少 baseline_results，暂时无法验证 active rule pool 接回 Step 0 后的真实效果。"
        report["warnings"] = ["缺少 baseline_results，active pool validation 已降级。"]
        return report

    if not isinstance(active_pool_results, list):
        report["summary"] = "缺少 active_pool_results，暂时无法比较 active pool 开关前后的 paired outcomes。"
        report["warnings"] = ["缺少 active_pool_results，active pool validation 已降级。"]
        return report

    baseline_index = _iter_indexed_results(baseline_results)
    active_index = _iter_indexed_results(active_pool_results)
    report["total_cases"] = len(baseline_results) + len(active_pool_results)

    comparable_keys = sorted(set(baseline_index) & set(active_index))
    report["comparable_cases"] = len(comparable_keys)
    report["ready"] = True

    if not comparable_keys:
        report["summary"] = "baseline 和 active-pool-enabled 输入都存在，但当前没有可对齐的 paired cases。"
        warnings.append("No comparable cases were found across baseline_results and active_pool_results.")
        report["warnings"] = warnings
        return report

    baseline_conf_counter: Counter[str] = Counter()
    active_conf_counter: Counter[str] = Counter()
    baseline_risk_counter: Counter[str] = Counter()
    active_risk_counter: Counter[str] = Counter()

    baseline_judged = 0
    baseline_correct = 0
    active_judged = 0
    active_correct = 0

    changed_cases = 0
    improved_cases = 0
    worsened_cases = 0
    neutral_cases = 0

    rule_buckets: dict[tuple[str, str], dict[str, Any]] = {}

    for key in comparable_keys:
        baseline_case = _extract_case(baseline_index[key])
        active_case = _extract_case(active_index[key])

        baseline_conf_counter[baseline_case["final_confidence"]] += 1
        active_conf_counter[active_case["final_confidence"]] += 1
        baseline_risk_counter[baseline_case["risk_level"]] += 1
        active_risk_counter[active_case["risk_level"]] += 1

        if isinstance(baseline_case["direction_correct"], bool):
            baseline_judged += 1
            baseline_correct += int(baseline_case["direction_correct"])
        if isinstance(active_case["direction_correct"], bool):
            active_judged += 1
            active_correct += int(active_case["direction_correct"])

        changed = _is_changed(baseline_case, active_case)
        if changed:
            changed_cases += 1

        if baseline_case["direction_correct"] is False and active_case["direction_correct"] is True:
            improved_cases += 1
            outcome = "improved"
        elif baseline_case["direction_correct"] is True and active_case["direction_correct"] is False:
            worsened_cases += 1
            outcome = "worsened"
        else:
            neutral_cases += 1
            outcome = "neutral"

        for hit in active_case["active_rule_hits"]:
            rule_key = (hit["rule_id"], hit["title"])
            bucket = rule_buckets.setdefault(
                rule_key,
                {
                    "rule_id": hit["rule_id"],
                    "title": hit["title"],
                    "hit_count": 0,
                    "changed_case_count": 0,
                    "improved_case_count": 0,
                    "worsened_case_count": 0,
                    "net_effect": 0.0,
                    "notes": "",
                },
            )
            bucket["hit_count"] += 1
            if changed:
                bucket["changed_case_count"] += 1
            if outcome == "improved":
                bucket["improved_case_count"] += 1
            elif outcome == "worsened":
                bucket["worsened_case_count"] += 1

    report["baseline_accuracy"] = _safe_rate(baseline_correct, baseline_judged)
    report["active_pool_accuracy"] = _safe_rate(active_correct, active_judged)
    if report["baseline_accuracy"] is not None and report["active_pool_accuracy"] is not None:
        report["accuracy_delta"] = round(
            report["active_pool_accuracy"] - report["baseline_accuracy"], 4
        )

    report["baseline_confidence_distribution"] = _distribution_report(
        baseline_conf_counter,
        kind="confidence",
    )
    report["active_pool_confidence_distribution"] = _distribution_report(
        active_conf_counter,
        kind="confidence",
    )
    report["baseline_risk_distribution"] = _distribution_report(
        baseline_risk_counter,
        kind="risk",
    )
    report["active_pool_risk_distribution"] = _distribution_report(
        active_risk_counter,
        kind="risk",
    )

    report["changed_cases"] = changed_cases
    report["improved_cases"] = improved_cases
    report["worsened_cases"] = worsened_cases
    report["neutral_cases"] = neutral_cases

    rule_effects: list[dict[str, Any]] = []
    for bucket in rule_buckets.values():
        bucket["net_effect"] = float(
            bucket["improved_case_count"] - bucket["worsened_case_count"]
        )
        bucket["notes"] = _build_rule_notes(
            hit_count=bucket["hit_count"],
            improved_case_count=bucket["improved_case_count"],
            worsened_case_count=bucket["worsened_case_count"],
            changed_case_count=bucket["changed_case_count"],
        )
        rule_effects.append(bucket)

    rule_effects.sort(
        key=lambda item: (
            -item["hit_count"],
            -item["net_effect"],
            item["rule_id"],
        )
    )
    report["rule_effects"] = rule_effects

    helpful_rules = [rule for rule in rule_effects if rule["net_effect"] > 0]
    helpful_rules.sort(
        key=lambda item: (-item["net_effect"], -item["hit_count"], item["rule_id"])
    )
    report["top_helpful_rules"] = helpful_rules[:5]

    unhelpful_rules = [rule for rule in rule_effects if rule["net_effect"] < 0]
    unhelpful_rules.sort(
        key=lambda item: (item["net_effect"], -item["hit_count"], item["rule_id"])
    )
    report["top_unhelpful_rules"] = unhelpful_rules[:5]

    report["summary"] = _summary(
        comparable_cases=report["comparable_cases"],
        baseline_accuracy=report["baseline_accuracy"],
        active_pool_accuracy=report["active_pool_accuracy"],
        accuracy_delta=report["accuracy_delta"],
        changed_cases=changed_cases,
        improved_cases=improved_cases,
        worsened_cases=worsened_cases,
        neutral_cases=neutral_cases,
        top_helpful_rules=report["top_helpful_rules"],
        top_unhelpful_rules=report["top_unhelpful_rules"],
        baseline_confidence_distribution=report["baseline_confidence_distribution"],
        active_confidence_distribution=report["active_pool_confidence_distribution"],
        baseline_risk_distribution=report["baseline_risk_distribution"],
        active_risk_distribution=report["active_pool_risk_distribution"],
    )
    report["warnings"] = warnings
    return report


def analyze_active_rule_pool_effectiveness(
    *,
    baseline_results: list[dict[str, Any]] | None = None,
    active_pool_results: list[dict[str, Any]] | None = None,
    active_rule_pool_export: dict[str, Any] | None = None,
    symbol: str = "AVGO",
) -> dict[str, Any]:
    return build_active_rule_pool_validation_report(
        baseline_results=baseline_results,
        active_pool_results=active_pool_results,
        active_rule_pool_export=active_rule_pool_export,
        symbol=symbol,
    )
