"""Historical replay training framework.

Runs the full projection v2 chain against historical dates and compares
predictions to actual outcomes, generating reviews and training statistics.

No-future-leak contract
-----------------------
For replay date T (as_of_date):
  - _projection_runner is called with target_date=as_of_date (sees only data ≤ T)
  - _outcome_fetcher is called after projection completes, for prediction_for_date (T+1)
  - The actual outcome is never passed to the projection step

Public API
----------
run_historical_replay_for_date(...)  → single-date replay result
run_historical_replay_batch(...)     → batch replay result
summarize_replay_results(...)        → aggregate statistics from batch results
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Callable


# ── output shape constants ────────────────────────────────────────────────────

_EMPTY_SUMMARY: dict[str, Any] = {
    "total_cases": 0,
    "completed_cases": 0,
    "failed_cases": 0,
    "direction_accuracy": None,
    "accuracy_by_confidence": {"high": None, "medium": None, "low": None},
    "top_error_categories": [],
    "top_rule_candidates": [],
}


# ── helpers ───────────────────────────────────────────────────────────────────

def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _replay_log(message: str) -> None:
    print(f"[training] {message}", flush=True)


def _replay_degraded_result(
    *,
    symbol: str,
    as_of_date: str,
    prediction_for_date: str,
    warnings: list[str],
    projection_snapshot: dict[str, Any] | None = None,
    actual_outcome: dict[str, Any] | None = None,
    review: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "kind": "historical_replay_result",
        "symbol": symbol,
        "as_of_date": as_of_date,
        "prediction_for_date": prediction_for_date,
        "ready": False,
        "projection_snapshot": projection_snapshot or {},
        "actual_outcome": actual_outcome or {},
        "review": review or {},
        "warnings": warnings,
    }


# ── single-date replay ────────────────────────────────────────────────────────

def run_historical_replay_for_date(
    *,
    symbol: str = "AVGO",
    as_of_date: str,
    prediction_for_date: str,
    lookback_days: int = 20,
    _projection_runner: Callable[..., dict[str, Any]] | None = None,
    _outcome_fetcher: Callable[..., dict[str, Any]] | None = None,
    _review_builder: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run one historical replay for (as_of_date → prediction_for_date).

    Step 1: Run projection v2 with target_date=as_of_date (no future data).
    Step 2: Fetch actual outcome for prediction_for_date (after projection).
    Step 3: Build review comparing snapshot vs actual outcome.

    Parameters
    ----------
    symbol              : ticker symbol (default AVGO)
    as_of_date          : T — date we replay from; projection sees only data ≤ T
    prediction_for_date : T+1 — date whose actual result we compare against
    lookback_days       : window passed to projection v2
    _projection_runner  : injectable for testing (default: run_projection_v2)
    _outcome_fetcher    : injectable for testing (default: capture_actual_outcome)
    _review_builder     : injectable for testing (default: build_projection_review)
    """
    if _projection_runner is None:
        from services.projection_orchestrator_v2 import run_projection_v2
        _projection_runner = run_projection_v2
    if _outcome_fetcher is None:
        from services.outcome_capture import capture_actual_outcome
        _outcome_fetcher = capture_actual_outcome
    if _review_builder is None:
        from services.projection_review_closed_loop import build_projection_review
        _review_builder = build_projection_review

    normalized_symbol = str(symbol or "AVGO").strip().upper() or "AVGO"
    warnings: list[str] = []

    # ── Step 1: projection (must run before outcome fetch — no-future-leak) ──
    projection_snapshot: dict[str, Any] = {}
    try:
        projection_snapshot = _safe_dict(_projection_runner(
            symbol=normalized_symbol,
            lookback_days=lookback_days,
            target_date=as_of_date,
        ))
    except Exception as exc:
        warnings.append(f"projection 失败 ({as_of_date})：{exc}")
        return _replay_degraded_result(
            symbol=normalized_symbol,
            as_of_date=as_of_date,
            prediction_for_date=prediction_for_date,
            warnings=warnings,
        )

    if not projection_snapshot.get("ready"):
        warnings.append(
            f"projection 未就绪 ({as_of_date})："
            + str(projection_snapshot.get("warnings") or "数据不足或链路降级。")
        )
        return _replay_degraded_result(
            symbol=normalized_symbol,
            as_of_date=as_of_date,
            prediction_for_date=prediction_for_date,
            warnings=warnings,
            projection_snapshot=projection_snapshot,
        )

    # Inject prediction_for_date into snapshot for review builder compatibility
    snapshot_for_review = dict(projection_snapshot)
    snapshot_for_review["prediction_for_date"] = prediction_for_date
    snapshot_for_review.setdefault("symbol", normalized_symbol)

    # ── Step 2: actual outcome fetch (after projection — no-future-leak) ─────
    actual_outcome: dict[str, Any] = {}
    try:
        actual_outcome = _safe_dict(_outcome_fetcher(normalized_symbol, prediction_for_date))
    except Exception as exc:
        warnings.append(f"实际结果获取失败 ({prediction_for_date})：{exc}")
        review = _safe_dict(_review_builder(snapshot_for_review, None))
        return _replay_degraded_result(
            symbol=normalized_symbol,
            as_of_date=as_of_date,
            prediction_for_date=prediction_for_date,
            warnings=warnings,
            projection_snapshot=projection_snapshot,
            actual_outcome={},
            review=review,
        )

    # ── Step 3: review ────────────────────────────────────────────────────────
    review: dict[str, Any] = {}
    try:
        review = _safe_dict(_review_builder(snapshot_for_review, actual_outcome))
    except Exception as exc:
        warnings.append(f"review 生成失败 ({as_of_date})：{exc}")

    return {
        "kind": "historical_replay_result",
        "symbol": normalized_symbol,
        "as_of_date": as_of_date,
        "prediction_for_date": prediction_for_date,
        "ready": True,
        "projection_snapshot": projection_snapshot,
        "actual_outcome": actual_outcome,
        "review": review,
        "warnings": warnings,
    }


# ── batch replay ──────────────────────────────────────────────────────────────

def run_historical_replay_batch(
    *,
    symbol: str = "AVGO",
    date_pairs: list[tuple[str, str]],
    lookback_days: int = 20,
    _projection_runner: Callable[..., dict[str, Any]] | None = None,
    _outcome_fetcher: Callable[..., dict[str, Any]] | None = None,
    _review_builder: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run replay for a list of (as_of_date, prediction_for_date) pairs.

    Parameters
    ----------
    date_pairs : list of (as_of_date, prediction_for_date) tuples
                 e.g. [("2024-01-10", "2024-01-11"), ("2024-01-11", "2024-01-12")]

    Single-date failures are caught individually — the batch never aborts early.
    """
    normalized_symbol = str(symbol or "AVGO").strip().upper() or "AVGO"
    warnings: list[str] = []

    if not date_pairs:
        return {
            "kind": "historical_replay_batch",
            "symbol": normalized_symbol,
            "start_date": None,
            "end_date": None,
            "ready": True,
            "results": [],
            "summary": dict(_EMPTY_SUMMARY),
            "warnings": ["date_pairs 为空，未执行任何 replay。"],
        }

    start_date = date_pairs[0][0]
    end_date = date_pairs[-1][0]
    results: list[dict[str, Any]] = []
    total_cases = len(date_pairs)
    progress_interval = 50 if total_cases >= 200 else 10

    _replay_log(
        f"replay batch started for {normalized_symbol} with {total_cases} case(s) ({start_date} -> {end_date})"
    )

    for index, (as_of_date, prediction_for_date) in enumerate(date_pairs, start=1):
        try:
            result = run_historical_replay_for_date(
                symbol=normalized_symbol,
                as_of_date=as_of_date,
                prediction_for_date=prediction_for_date,
                lookback_days=lookback_days,
                _projection_runner=_projection_runner,
                _outcome_fetcher=_outcome_fetcher,
                _review_builder=_review_builder,
            )
        except Exception as exc:
            result = _replay_degraded_result(
                symbol=normalized_symbol,
                as_of_date=as_of_date,
                prediction_for_date=prediction_for_date,
                warnings=[f"replay 意外失败：{exc}"],
            )
            warnings.append(f"replay {as_of_date} 意外失败：{exc}")

        results.append(result)
        if index % progress_interval == 0 or index == total_cases:
            _replay_log(f"replay batch progress: {index}/{total_cases} cases processed")

    summary = summarize_replay_results(results)
    _replay_log(
        f"replay batch completed: completed={summary['completed_cases']}, failed={summary['failed_cases']}"
    )

    return {
        "kind": "historical_replay_batch",
        "symbol": normalized_symbol,
        "start_date": start_date,
        "end_date": end_date,
        "ready": True,
        "results": results,
        "summary": summary,
        "warnings": warnings,
    }


# ── aggregation ───────────────────────────────────────────────────────────────

def summarize_replay_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate training statistics from a list of replay results.

    Parameters
    ----------
    results : list of run_historical_replay_for_date() outputs

    Returns
    -------
    {
        "total_cases": int,
        "completed_cases": int,
        "failed_cases": int,
        "direction_accuracy": float | None,
        "accuracy_by_confidence": {"high": float|None, "medium": float|None, "low": float|None},
        "top_error_categories": [{"category": str, "count": int}, ...],
        "top_rule_candidates": [{"rule_id": str, "title": str, "count": int}, ...],
    }
    """
    if not results:
        return dict(_EMPTY_SUMMARY)

    total = len(results)
    completed = sum(1 for r in results if r.get("ready"))
    failed = total - completed

    # direction accuracy across completed replays with a definite review verdict
    correct_total = 0
    judged_total = 0
    conf_buckets: dict[str, list[bool]] = {"high": [], "medium": [], "low": []}

    error_category_counter: Counter[str] = Counter()
    rule_counter: Counter[tuple[str, str]] = Counter()  # (rule_id, title)

    for r in results:
        if not r.get("ready"):
            continue
        review = _safe_dict(r.get("review"))
        if not review:
            continue

        direction_correct = review.get("direction_correct")
        if isinstance(direction_correct, bool):
            judged_total += 1
            if direction_correct:
                correct_total += 1

            # confidence bucket
            conf = str(review.get("predicted_confidence") or "").strip().lower()
            if conf in conf_buckets:
                conf_buckets[conf].append(direction_correct)

        # error categories (only for wrong predictions)
        error_cat = str(review.get("error_category") or "").strip()
        if error_cat and error_cat not in {"unknown", ""}:
            error_category_counter[error_cat] += 1

        # rule candidates
        for candidate in review.get("rule_candidates") or []:
            if not isinstance(candidate, dict):
                continue
            rule_id = str(candidate.get("rule_id") or "").strip()
            title = str(candidate.get("title") or "").strip()
            if rule_id:
                rule_counter[(rule_id, title)] += 1

    direction_accuracy = (correct_total / judged_total) if judged_total > 0 else None

    def _bucket_accuracy(items: list[bool]) -> float | None:
        return sum(items) / len(items) if items else None

    accuracy_by_confidence = {
        "high": _bucket_accuracy(conf_buckets["high"]),
        "medium": _bucket_accuracy(conf_buckets["medium"]),
        "low": _bucket_accuracy(conf_buckets["low"]),
    }

    top_error_categories = [
        {"category": cat, "count": cnt}
        for cat, cnt in error_category_counter.most_common(5)
    ]

    top_rule_candidates = [
        {"rule_id": rule_id, "title": title, "count": cnt}
        for (rule_id, title), cnt in rule_counter.most_common(10)
    ]

    return {
        "total_cases": total,
        "completed_cases": completed,
        "failed_cases": failed,
        "direction_accuracy": direction_accuracy,
        "accuracy_by_confidence": accuracy_by_confidence,
        "top_error_categories": top_error_categories,
        "top_rule_candidates": top_rule_candidates,
    }
