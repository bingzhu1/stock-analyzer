from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from services.agent_schema import AgentCommand, CommandFilter, build_command_help_text


@dataclass(frozen=True)
class AnalysisContext:
    target_date_str: str
    scan_result: dict[str, Any] | None
    exact_df: pd.DataFrame
    near_df: pd.DataFrame
    summary_df: pd.DataFrame
    disp_exact_df: pd.DataFrame
    disp_near_df: pd.DataFrame

    @property
    def has_analysis(self) -> bool:
        return self.scan_result is not None


@dataclass(frozen=True)
class QueryResult:
    message: str
    table: pd.DataFrame | None = None


_DISPLAY_COLUMNS = [
    "MatchType",
    "MatchDate",
    "MatchCode",
    "ContextScore",
    "ContextLabel",
    "MatchStageLabel",
    "MatchPosLabel",
    "MatchPos30",
    "NextDate",
    "NextOpenChange",
    "NextCloseMove",
    "NextHighMove",
    "NextLowMove",
    "VCodeDiff",
]

_SUPPORTED_SORTS = {
    "ContextScore",
    "MatchDate",
    "NextOpenChange",
    "NextCloseMove",
    "NextHighMove",
    "NextLowMove",
    "MatchPos30",
    "MatchRet5",
    "VCodeDiff",
}

_SUPPORTED_GROUPS = {
    "ContextLabel",
    "NextDayBias",
    "MatchPosLabel",
    "MatchStageLabel",
    "MatchType",
}


def execute_agent_command(command: AgentCommand, context: AnalysisContext) -> QueryResult:
    """Execute a parsed command against read-only analysis outputs."""
    if command.action == "help":
        return _help()
    if command.action == "unsupported":
        return _unsupported(command)
    if not context.has_analysis:
        return QueryResult(
            "Run Analysis first so I have scan and match outputs to query. "
            "For now I can still show help and starter examples."
        )
    if command.action == "summarize_scan":
        return _summarize_scan(context)
    if command.action == "explain_bias":
        return _explain_bias(context)
    if command.action == "compare_matches":
        return _compare_matches(context)
    if command.action == "group_matches":
        return _group_matches(command, context)
    return _show_matches(command, context)


def _help() -> QueryResult:
    return QueryResult(build_command_help_text())


def _unsupported(command: AgentCommand) -> QueryResult:
    reason = command.reason or "I could not map that request to a supported read-only command."
    return QueryResult(
        f"{reason}\n\n"
        "I can only query the current scan/match outputs. Try `help`, "
        "`summarize the current scan result`, or `show top 10 high similarity samples`."
    )


def _summarize_scan(context: AnalysisContext) -> QueryResult:
    sr = context.scan_result or {}
    hist = sr.get("historical_match_summary", {})
    lines = [
        f"Current scan for {context.target_date_str}: "
        f"{str(sr.get('scan_bias', 'neutral')).upper()} / "
        f"{str(sr.get('scan_confidence', 'low')).upper()} confidence.",
        f"Pattern code: {sr.get('avgo_pattern_code', 'n/a')}. "
        f"Exact matches: {hist.get('exact_match_count', 0)}; "
        f"near matches: {hist.get('near_match_count', 0)}.",
        f"Historical outcome: {hist.get('dominant_historical_outcome', 'n/a')}.",
        str(sr.get("notes", "")).strip(),
    ]
    return QueryResult("\n\n".join(line for line in lines if line))


def _explain_bias(context: AnalysisContext) -> QueryResult:
    sr = context.scan_result or {}
    hist = sr.get("historical_match_summary", {})
    rs_5d = sr.get("relative_strength_5d_summary", sr.get("relative_strength_summary", {}))
    rs_same_day = sr.get("relative_strength_same_day_summary", {})

    rows = pd.DataFrame(
        [
            {"Factor": "Gap state", "Value": sr.get("avgo_gap_state", "unknown")},
            {"Factor": "Intraday state", "Value": sr.get("avgo_intraday_state", "unknown")},
            {"Factor": "Volume state", "Value": sr.get("avgo_volume_state", "unknown")},
            {"Factor": "Price/stage state", "Value": sr.get("avgo_price_state", "unknown")},
            {"Factor": "Historical outcome", "Value": hist.get("dominant_historical_outcome", "n/a")},
            {"Factor": "RS confirmation", "Value": sr.get("confirmation_state", "mixed")},
            {"Factor": "5-day RS", "Value": _format_dict(rs_5d)},
            {"Factor": "Same-day RS", "Value": _format_dict(rs_same_day)},
        ]
    )
    message = (
        f"The scan bias is {str(sr.get('scan_bias', 'neutral')).upper()} with "
        f"{str(sr.get('scan_confidence', 'low')).upper()} confidence. The rule-based scan combines "
        "gap, volume, stage, historical outcome, and relative-strength confirmation."
    )
    return QueryResult(message, rows)


def _compare_matches(context: AnalysisContext) -> QueryResult:
    exact = _with_bias(context.exact_df)
    near = _with_bias(context.near_df)
    rows = []
    for label, df in (("exact", exact), ("near", near)):
        rows.append(
            {
                "MatchType": label,
                "Rows": len(df),
                "HighSimilarity": _count_eq(df, "ContextLabel", "高相似"),
                "MediumSimilarity": _count_eq(df, "ContextLabel", "中相似"),
                "BullishCases": _count_eq(df, "NextDayBias", "bullish"),
                "BearishCases": _count_eq(df, "NextDayBias", "bearish"),
                "AvgContextScore": _safe_mean(df, "ContextScore"),
                "AvgNextCloseMovePct": _safe_mean(df, "NextCloseMove", scale=100),
            }
        )
    table = pd.DataFrame(rows)
    return QueryResult("Exact vs near match comparison from the current analysis.", table)


def _show_matches(command: AgentCommand, context: AnalysisContext) -> QueryResult:
    df = _select_matches(command, context)
    df = _apply_filters(df, command.filters)
    df = _apply_sort(df, command.sort_by, command.sort_dir)
    df = df.head(command.limit).reset_index(drop=True)
    table = _display_table(df)
    scope = describe_scope(command.dataset, context)

    if table.empty:
        return QueryResult(f"Scope: {scope}. No rows matched that request.", table)
    return QueryResult(f"Scope: {scope}. Showing {len(table)} matching rows.", table)


def _group_matches(command: AgentCommand, context: AnalysisContext) -> QueryResult:
    group_by = command.group_by or "ContextLabel"
    if group_by not in _SUPPORTED_GROUPS:
        return QueryResult(
            f"Grouping by {group_by} is not supported. Supported groups: "
            + ", ".join(sorted(_SUPPORTED_GROUPS))
        )

    df = _select_matches(command, context)
    df = _apply_filters(df, command.filters)
    df = _with_bias(df)
    if df.empty or group_by not in df.columns:
        scope = describe_scope(command.dataset, context)
        return QueryResult(f"Scope: {scope}. No available rows to group by {group_by}.", pd.DataFrame())

    table = (
        df.groupby(group_by, dropna=False)
        .agg(
            Rows=("MatchDate", "count"),
            AvgContextScore=("ContextScore", "mean"),
            AvgNextCloseMove=("NextCloseMove", "mean"),
        )
        .reset_index()
        .sort_values("Rows", ascending=False)
    )
    if "AvgNextCloseMove" in table.columns:
        table["AvgNextCloseMovePct"] = table["AvgNextCloseMove"] * 100
        table = table.drop(columns=["AvgNextCloseMove"])
    scope = describe_scope(command.dataset, context)
    return QueryResult(f"Scope: {scope}. Grouped matches by {group_by}.", table)


def describe_default_scope(context: AnalysisContext) -> str:
    return describe_scope("current", context)


def describe_scope(dataset: str, context: AnalysisContext) -> str:
    if dataset == "exact":
        return f"exact ({len(context.exact_df)} rows)"
    if dataset == "near":
        return f"near ({len(context.near_df)} rows)"
    if dataset == "all":
        return f"all ({len(context.exact_df) + len(context.near_df)} rows)"
    displayed = len(context.disp_exact_df) + len(context.disp_near_df)
    full = len(context.exact_df) + len(context.near_df)
    if full == displayed:
        return f"displayed ({displayed} rows; no active result filter)"
    return f"displayed ({displayed}/{full} rows after active result filters)"


def _select_matches(command: AgentCommand, context: AnalysisContext) -> pd.DataFrame:
    if command.dataset == "exact":
        return context.exact_df.copy()
    if command.dataset == "near":
        return context.near_df.copy()
    if command.dataset == "all":
        return pd.concat([context.exact_df, context.near_df], ignore_index=True)
    return pd.concat([context.disp_exact_df, context.disp_near_df], ignore_index=True)


def _apply_filters(df: pd.DataFrame, filters: tuple[CommandFilter, ...]) -> pd.DataFrame:
    out = _with_bias(df)
    for filter_item in filters:
        if filter_item.field not in out.columns:
            continue
        series = out[filter_item.field]
        if filter_item.op == "eq":
            out = out[series.astype(str) == str(filter_item.value)]
        elif filter_item.op == "gt":
            out = out[pd.to_numeric(series, errors="coerce") > float(filter_item.value)]
        elif filter_item.op == "lt":
            out = out[pd.to_numeric(series, errors="coerce") < float(filter_item.value)]
        elif filter_item.op == "ge":
            out = out[pd.to_numeric(series, errors="coerce") >= float(filter_item.value)]
        elif filter_item.op == "le":
            out = out[pd.to_numeric(series, errors="coerce") <= float(filter_item.value)]
    return out


def _apply_sort(df: pd.DataFrame, sort_by: str | None, sort_dir: str) -> pd.DataFrame:
    if not sort_by or sort_by not in _SUPPORTED_SORTS or sort_by not in df.columns:
        return df
    return df.sort_values(sort_by, ascending=(sort_dir == "asc"), na_position="last")


def _with_bias(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "NextDayBias" not in out.columns and "NextCloseMove" in out.columns:
        close_move = pd.to_numeric(out["NextCloseMove"], errors="coerce")
        out["NextDayBias"] = close_move.apply(
            lambda value: "bullish" if value > 0 else ("bearish" if value < 0 else "flat")
        )
    return out


def _display_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    cols = [col for col in _DISPLAY_COLUMNS if col in df.columns]
    table = df[cols].copy()
    for col in ["NextOpenChange", "NextCloseMove", "NextHighMove", "NextLowMove"]:
        if col in table.columns:
            table[col] = pd.to_numeric(table[col], errors="coerce") * 100
    return table


def _count_eq(df: pd.DataFrame, column: str, value: str) -> int:
    if df.empty or column not in df.columns:
        return 0
    return int((df[column].astype(str) == value).sum())


def _safe_mean(df: pd.DataFrame, column: str, scale: float = 1.0) -> float | None:
    if df.empty or column not in df.columns:
        return None
    values = pd.to_numeric(df[column], errors="coerce").dropna()
    if values.empty:
        return None
    return round(float(values.mean() * scale), 2)


def _format_dict(values: dict[str, Any]) -> str:
    if not values:
        return "n/a"
    return ", ".join(f"{key.replace('vs_', '').upper()}: {value}" for key, value in values.items())
