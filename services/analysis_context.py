from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

import pandas as pd


ANALYSIS_STATE_KEYS = (
    "target_date_str",
    "coded_df",
    "exact_df",
    "near_df",
    "summary_df",
    "pos_df",
    "prev_df",
    "mom_df",
    "scan_result",
    "research_result",
    "target_row",
    "target_code",
    "target_ctx",
    "match_context",
    "analysis_error",
    "saved_prediction_id",
    "saved_prediction_date",
    "ai_projection_summary_text",
    "ai_review_summary_text",
)

COMMAND_STATE_PREFIXES = ("cn_cmd_",)


def reset_analysis_context_state(
    state: MutableMapping[str, Any],
    target_date_str: str,
) -> None:
    """Clear analysis/session artifacts before starting a new target-date run."""
    for key in ANALYSIS_STATE_KEYS:
        state.pop(key, None)

    for key in list(state.keys()):
        if any(str(key).startswith(prefix) for prefix in COMMAND_STATE_PREFIXES):
            state.pop(key, None)

    state["target_date_str"] = target_date_str
    state["target_code"] = "—"
    state["analysis_error"] = None


def validate_target_code_for_analysis(
    coded_df: pd.DataFrame,
    target_date_str: str,
) -> tuple[pd.Series | None, str, str | None]:
    """Return target row/code or a user-facing validation error."""
    if coded_df.empty or "Date" not in coded_df.columns:
        return (
            None,
            "—",
            f"当前数据中找不到 {target_date_str}，无法生成历史匹配。请刷新数据或选择已有交易日。",
        )

    target_ts = pd.to_datetime(target_date_str)
    dates = pd.to_datetime(coded_df["Date"], errors="coerce")
    rows = coded_df[dates == target_ts]
    if rows.empty:
        return (
            None,
            "—",
            f"当前数据中找不到 {target_date_str}，无法生成历史匹配。请刷新数据或选择已有交易日。",
        )

    row = rows.iloc[0]
    raw_code = row.get("Code", pd.NA)
    code = _normalize_code(raw_code)
    if not code:
        return (
            row,
            "—",
            f"{target_date_str} 的 5-Digit Code 为空，暂时无法匹配历史样本。请先刷新/编码数据，或选择已有完整编码的交易日。",
        )

    return row, code, None


def friendly_analysis_error(stage: str, exc: Exception, target_date_str: str) -> str:
    """Convert known low-level analysis errors into stable user-facing text."""
    message = str(exc)
    if "Target date has empty Code" in message:
        return (
            f"{target_date_str} 的 5-Digit Code 为空，暂时无法匹配历史样本。"
            "请先刷新/编码数据，或选择已有完整编码的交易日。"
        )
    if "Target date not found" in message:
        return f"当前数据中找不到 {target_date_str}，无法生成历史匹配。请刷新数据或选择已有交易日。"
    return f"{stage} failed: {message}"


def _normalize_code(raw_code: Any) -> str:
    if pd.isna(raw_code):
        return ""

    code = str(raw_code).strip()
    if not code or code.lower() in {"nan", "none", "<na>"}:
        return ""

    if code.endswith(".0"):
        integer_part, decimal_part = code.split(".", maxsplit=1)
        if decimal_part and set(decimal_part) == {"0"}:
            code = integer_part

    return code
