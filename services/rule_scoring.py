from __future__ import annotations

from collections import Counter
from typing import Any


_MAX_SAMPLE_REVIEWS = 3


def _empty_report() -> dict[str, Any]:
    return {
        "kind": "rule_score_report",
        "ready": False,
        "total_reviews": 0,
        "total_rule_hits": 0,
        "rules": [],
        "top_promising_rules": [],
        "top_risky_rules": [],
        "summary": "",
        "warnings": [],
    }


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _clean_text(value: Any, fallback: str = "unknown") -> str:
    text = str(value or "").strip()
    return text if text else fallback


def _normalize_rule_key(candidate: dict[str, Any]) -> tuple[str, str, str]:
    title = _clean_text(candidate.get("title"))
    category = _clean_text(candidate.get("category"))
    return (
        f"{category.lower()}::{title.lower()}",
        title,
        category,
    )


def _record_status(direction_correct: Any) -> str:
    if direction_correct is True:
        return "effective"
    if direction_correct is False:
        return "harmful"
    return "neutral"


def _recommended_status(
    *,
    hit_count: int,
    effective_count: int,
    harmful_count: int,
    effectiveness_rate: float | None,
    harm_rate: float | None,
) -> str:
    if hit_count <= 1:
        return "candidate"
    if harmful_count > effective_count and (harm_rate or 0.0) >= 0.5:
        return "risky"
    if effective_count > harmful_count and (effectiveness_rate or 0.0) >= 0.6:
        return "promising"
    return "watchlist"


def _build_notes(
    *,
    hit_count: int,
    effective_count: int,
    harmful_count: int,
    neutral_count: int,
    recommended_status: str,
) -> str:
    return (
        f"命中 {hit_count} 次，其中有效 {effective_count} 次、"
        f"有害 {harmful_count} 次、中性 {neutral_count} 次；"
        f"当前建议列为 {recommended_status}。"
    )


def _append_sample_review(
    bucket: dict[str, Any],
    *,
    source_review: dict[str, Any],
    replay_result: dict[str, Any] | None,
    candidate: dict[str, Any],
) -> None:
    if len(bucket["sample_reviews"]) >= _MAX_SAMPLE_REVIEWS:
        return

    sample = {
        "as_of_date": _clean_text(_as_dict(replay_result).get("as_of_date"), fallback="unknown"),
        "prediction_for_date": _clean_text(
            _as_dict(replay_result).get("prediction_for_date"),
            fallback="unknown",
        ),
        "direction_correct": source_review.get("direction_correct"),
        "error_category": _clean_text(source_review.get("error_category")),
        "message": _clean_text(candidate.get("message")),
    }
    bucket["sample_reviews"].append(sample)


def _iter_review_records(
    replay_results: list[dict[str, Any]] | None,
    reviews: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    for replay in replay_results or []:
        replay_dict = _as_dict(replay)
        review = _as_dict(replay_dict.get("review"))
        records.append(
            {
                "review": review,
                "replay_result": replay_dict,
            }
        )

    for review in reviews or []:
        records.append(
            {
                "review": _as_dict(review),
                "replay_result": None,
            }
        )

    return records


def _build_bias_sources(rules: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    sources: list[dict[str, Any]] = []
    actions: list[str] = []

    if not rules:
        return sources, actions

    most_hit = max(rules, key=lambda rule: (rule["hit_count"], rule["net_score"], rule["rule_key"]))
    if most_hit["hit_count"] >= 3:
        sources.append(
            {
                "title": "高频命中规则值得优先复核",
                "evidence": (
                    f"规则 {most_hit['title']} 命中 {most_hit['hit_count']} 次，"
                    "说明它已经足够高频，适合作为后续 lifecycle 评估样本。"
                ),
                "severity": "medium",
            }
        )
        actions.append("Prioritize the most frequently hit rules for deeper manual validation before promotion.")

    risky_rules = [rule for rule in rules if rule["recommended_status"] == "risky"]
    if risky_rules:
        top_risky = risky_rules[0]
        sources.append(
            {
                "title": "部分规则可能在拖累方向判断",
                "evidence": (
                    f"规则 {top_risky['title']} 的 harmful_count={top_risky['harmful_count']}，"
                    f"effective_count={top_risky['effective_count']}，harm_rate={top_risky['harm_rate']}。"
                ),
                "severity": "high",
            }
        )
        actions.append("Review risky rules first and keep them out of any active-rule promotion path.")

    promising_rules = [rule for rule in rules if rule["recommended_status"] == "promising"]
    if promising_rules:
        top_promising = promising_rules[0]
        sources.append(
            {
                "title": "部分规则已显示出初步有效性",
                "evidence": (
                    f"规则 {top_promising['title']} 的 effectiveness_rate="
                    f"{top_promising['effectiveness_rate']}，net_score={top_promising['net_score']}。"
                ),
                "severity": "medium",
            }
        )
        actions.append("Keep promising rules on a watchlist and gather more hits before considering activation.")

    if not actions:
        actions.append("Collect more replay reviews so rule scoring has enough evidence to separate signal from noise.")

    return sources[:3], actions[:3]


def build_rule_score_report(
    replay_results: list[dict[str, Any]] | None = None,
    reviews: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    report = _empty_report()
    warnings: list[str] = []

    records = _iter_review_records(replay_results, reviews)
    report["total_reviews"] = len(records)

    if not records:
        report["summary"] = "缺少 replay/review 输入，暂时无法建立规则长期表现评分。"
        report["warnings"] = ["No replay_results or reviews were provided for rule scoring."]
        return report

    aggregates: dict[str, dict[str, Any]] = {}
    malformed_hits = 0

    for record in records:
        review = _as_dict(record.get("review"))
        replay_result = record.get("replay_result")
        direction_correct = review.get("direction_correct")
        candidates = _as_list(review.get("rule_candidates"))

        for candidate_value in candidates:
            candidate = _as_dict(candidate_value)
            if not candidate:
                malformed_hits += 1
                continue

            rule_key, title, category = _normalize_rule_key(candidate)
            bucket = aggregates.setdefault(
                rule_key,
                {
                    "rule_key": rule_key,
                    "title": title,
                    "category": category,
                    "hit_count": 0,
                    "effective_count": 0,
                    "harmful_count": 0,
                    "neutral_count": 0,
                    "sample_reviews": [],
                    "_messages": Counter(),
                },
            )

            bucket["hit_count"] += 1
            status = _record_status(direction_correct)
            bucket[f"{status}_count"] += 1
            message = _clean_text(candidate.get("message"))
            bucket["_messages"][message] += 1
            _append_sample_review(
                bucket,
                source_review=review,
                replay_result=replay_result if isinstance(replay_result, dict) else None,
                candidate=candidate,
            )

    if malformed_hits:
        warnings.append(f"Skipped {malformed_hits} malformed rule candidate entries.")

    if not aggregates:
        report["ready"] = True
        report["summary"] = "当前 review 中没有可评分的 rule_candidates，尚无法区分有效规则和噪音规则。"
        warnings.append("No rule_candidates were found in the provided reviews.")
        report["warnings"] = warnings
        return report

    rules: list[dict[str, Any]] = []
    total_rule_hits = 0

    for bucket in aggregates.values():
        hit_count = bucket["hit_count"]
        effective_count = bucket["effective_count"]
        harmful_count = bucket["harmful_count"]
        neutral_count = bucket["neutral_count"]
        total_rule_hits += hit_count

        effectiveness_rate = round(effective_count / hit_count, 4) if hit_count else None
        harm_rate = round(harmful_count / hit_count, 4) if hit_count else None
        net_score = float(effective_count - harmful_count)
        recommended_status = _recommended_status(
            hit_count=hit_count,
            effective_count=effective_count,
            harmful_count=harmful_count,
            effectiveness_rate=effectiveness_rate,
            harm_rate=harm_rate,
        )
        dominant_message = bucket["_messages"].most_common(1)[0][0] if bucket["_messages"] else "unknown"

        rules.append(
            {
                "rule_key": bucket["rule_key"],
                "title": bucket["title"],
                "category": bucket["category"],
                "hit_count": hit_count,
                "effective_count": effective_count,
                "harmful_count": harmful_count,
                "neutral_count": neutral_count,
                "effectiveness_rate": effectiveness_rate,
                "harm_rate": harm_rate,
                "net_score": net_score,
                "sample_reviews": bucket["sample_reviews"],
                "recommended_status": recommended_status,
                "notes": (
                    f"{_build_notes(
                        hit_count=hit_count,
                        effective_count=effective_count,
                        harmful_count=harmful_count,
                        neutral_count=neutral_count,
                        recommended_status=recommended_status,
                    )} 主导 message: {dominant_message}"
                ),
            }
        )

    rules.sort(
        key=lambda row: (
            -row["net_score"],
            -row["hit_count"],
            row["harm_rate"] if row["harm_rate"] is not None else 1.0,
            row["rule_key"],
        )
    )

    top_promising = [
        rule for rule in rules if rule["recommended_status"] == "promising"
    ][:3]
    top_risky = sorted(
        [rule for rule in rules if rule["recommended_status"] == "risky"],
        key=lambda row: (-row["harmful_count"], row["net_score"], -row["hit_count"], row["rule_key"]),
    )[:3]

    sources, actions = _build_bias_sources(rules)

    if not sources:
        warnings.append("Rule scoring evidence is still thin; treat current statuses as provisional.")

    summary_parts = [
        f"共分析 {report['total_reviews']} 条 review，累计 {total_rule_hits} 次规则命中。",
        f"promising={len(top_promising)}，risky={len(top_risky)}。",
    ]
    if rules:
        top_rule = rules[0]
        summary_parts.append(
            f"当前净分最高的规则是 {top_rule['title']}（net_score={top_rule['net_score']}，hit_count={top_rule['hit_count']}）。"
        )

    report.update(
        {
            "ready": True,
            "total_rule_hits": total_rule_hits,
            "rules": rules,
            "top_promising_rules": top_promising,
            "top_risky_rules": top_risky,
            "summary": " ".join(summary_parts),
            "warnings": warnings,
        }
    )

    if actions:
        report["summary"] = f"{report['summary']} 下一步建议：{' '.join(actions)}"

    return report


analyze_rule_scores = build_rule_score_report
