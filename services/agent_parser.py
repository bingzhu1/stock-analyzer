from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping, Protocol

from services.agent_schema import (
    AgentCommand,
    CommandSchemaError,
    CommandAction,
    CommandFilter,
    DatasetScope,
    MODEL_COMMAND_JSON_SCHEMA,
    SortDirection,
    build_command_help_text,
    coerce_model_command,
)


_MAX_LIMIT = 50
_DEFAULT_LIMIT = 10

_SORT_ALIASES: dict[str, str] = {
    "context score": "ContextScore",
    "similarity score": "ContextScore",
    "similarity": "ContextScore",
    "score": "ContextScore",
    "match date": "MatchDate",
    "date": "MatchDate",
    "next close": "NextCloseMove",
    "close move": "NextCloseMove",
    "next open": "NextOpenChange",
    "open change": "NextOpenChange",
    "next high": "NextHighMove",
    "high move": "NextHighMove",
    "next low": "NextLowMove",
    "low move": "NextLowMove",
    "position": "MatchPos30",
    "pos30": "MatchPos30",
    "ret5": "MatchRet5",
    "vcode": "VCodeDiff",
}

_UNSUPPORTED_PHRASES = (
    "should i buy",
    "should i sell",
    "buy avgo",
    "sell avgo",
    "price target",
    "predict",
    "prediction",
    "forecast",
    "research",
    "wechat",
    "openclaw",
    "execute",
    "run python",
    "call api",
)

_TABLE_INTENT_PHRASES = (
    "show",
    "list",
    "top",
    "sort",
    "filter",
    "only",
    "samples",
    "matches",
    "cases",
    "rows",
)


class CommandParser(Protocol):
    """Parser boundary shared by deterministic and future model parsers."""

    def parse(self, text: str) -> AgentCommand:
        ...


@dataclass(frozen=True)
class ModelParserRequest:
    text: str
    command_schema: dict[str, Any]
    command_help: str


class ModelCommandProvider(Protocol):
    """Provider interface for future structured-output model integrations."""

    def build_command_payload(self, request: ModelParserRequest) -> Mapping[str, Any] | None:
        ...


class DeterministicCommandParser:
    """Small local parser used as the default control path."""

    def parse(self, text: str) -> AgentCommand:
        raw_text = (text or "").strip()
        lowered = raw_text.lower()

        if not lowered:
            return AgentCommand(action="help", raw_text=raw_text)

        if _mentions_any(lowered, _UNSUPPORTED_PHRASES):
            return _unsupported(raw_text, "That request is outside the read-only Control Chat command set.")

        dataset = _parse_dataset(lowered)
        limit = _parse_limit(lowered)
        filters = _parse_filters(lowered)
        sort_by, sort_dir = _parse_sort(lowered)
        group_by = _parse_group_by(lowered)
        action = _parse_action(lowered, group_by)

        if action == "unsupported":
            return _unsupported(raw_text, "I could not map that request to a supported command.")

        if action in ("show_matches", "group_matches") and sort_by is None:
            sort_by = "ContextScore"
            sort_dir = "desc"

        return AgentCommand(
            action=action,
            raw_text=raw_text,
            dataset=dataset,
            filters=tuple(filters),
            sort_by=sort_by,
            sort_dir=sort_dir,
            limit=limit,
            group_by=group_by,
        )


class ModelBackedCommandParser:
    """
    Pluggable model-parser boundary.

    The provider is injected by callers and may later wrap an LLM structured
    output call. This class itself does not make network calls. Every provider
    result is validated by services.agent_schema before it can be returned. If
    validation fails, provider returns unsupported, or provider raises, the
    deterministic parser handles the text instead.
    """

    def __init__(
        self,
        provider: ModelCommandProvider | None = None,
        fallback: CommandParser | None = None,
    ) -> None:
        self.provider = provider
        self.fallback = fallback or DETERMINISTIC_PARSER

    def parse(self, text: str) -> AgentCommand:
        if self.provider is None:
            return self.fallback.parse(text)
        try:
            raw_text = (text or "").strip()
            request = ModelParserRequest(
                text=raw_text,
                command_schema=MODEL_COMMAND_JSON_SCHEMA,
                command_help=build_command_help_text(),
            )
            payload = self.provider.build_command_payload(request)
            command = coerce_model_command(payload, raw_text=raw_text)
        except Exception:
            return self.fallback.parse(text)

        if command.action == "unsupported":
            return self.fallback.parse(text)
        return command


DETERMINISTIC_PARSER = DeterministicCommandParser()
FutureModelCommandParser = ModelBackedCommandParser


def parse_agent_command(text: str, parser: CommandParser | None = None) -> AgentCommand:
    """Parse user text with the deterministic parser unless another parser is supplied."""
    return (parser or DETERMINISTIC_PARSER).parse(text)


def _parse_action(text: str, group_by: str | None) -> CommandAction:
    if _mentions_any(text, ("help", "what can you do", "commands", "examples")):
        return "help"
    if _mentions_any(text, ("summarize", "summary", "scan result", "current scan")):
        return "summarize_scan"
    if _mentions_any(text, (
        "explain bias",
        "explain the bias",
        "explain current bias",
        "explain the current bias",
        "why bias",
        "confidence",
        "explain confidence",
    )):
        return "explain_bias"
    if _mentions_any(text, ("compare exact", "exact vs near", "near vs exact", "compare matches", "match counts")):
        return "compare_matches"
    if group_by is not None or text.startswith("group "):
        return "group_matches"
    if _mentions_any(text, _TABLE_INTENT_PHRASES):
        return "show_matches"
    return "unsupported"


def _parse_dataset(text: str) -> DatasetScope:
    if re.search(r"\bexact\b", text) and not re.search(r"\bnear\b", text):
        return "exact"
    if re.search(r"\bnear\b", text) and not re.search(r"\bexact\b", text):
        return "near"
    if "all samples" in text or "all matches" in text or "exact and near" in text:
        return "all"
    return "current"


def _parse_limit(text: str) -> int:
    match = re.search(r"\b(?:top|first|limit|show)\s+(\d{1,3})\b", text)
    if not match:
        return _DEFAULT_LIMIT
    return max(1, min(_MAX_LIMIT, int(match.group(1))))


def _parse_filters(text: str) -> list[CommandFilter]:
    filters: list[CommandFilter] = []

    if _mentions_any(text, ("high similarity", "high similar", "high context", "高相似")):
        filters.append(CommandFilter("ContextLabel", "eq", "高相似"))
    elif _mentions_any(text, ("medium similarity", "medium similar", "中相似")):
        filters.append(CommandFilter("ContextLabel", "eq", "中相似"))
    elif _mentions_any(text, ("low similarity", "low similar", "低相似")):
        filters.append(CommandFilter("ContextLabel", "eq", "低相似"))

    if _mentions_any(text, ("bullish cases", "bullish samples", "positive cases", "up cases", "winners")):
        filters.append(CommandFilter("NextCloseMove", "gt", 0.0))
    if _mentions_any(text, ("bearish cases", "bearish samples", "negative cases", "down cases", "losers")):
        filters.append(CommandFilter("NextCloseMove", "lt", 0.0))

    if _mentions_any(text, ("low position", "低位")):
        filters.append(CommandFilter("MatchPosLabel", "eq", "低位"))
    elif _mentions_any(text, ("middle position", "mid position", "中位")):
        filters.append(CommandFilter("MatchPosLabel", "eq", "中位"))
    elif _mentions_any(text, ("high position", "高位")):
        filters.append(CommandFilter("MatchPosLabel", "eq", "高位"))

    return filters


def _parse_sort(text: str) -> tuple[str | None, SortDirection]:
    direction: SortDirection = "desc"
    if _mentions_any(text, ("ascending", "asc", "oldest", "lowest")):
        direction = "asc"
    if _mentions_any(text, ("descending", "desc", "newest", "highest", "top")):
        direction = "desc"

    for phrase, column in _SORT_ALIASES.items():
        if phrase in text:
            return column, direction

    sort_match = re.search(r"\bsort by ([a-z0-9 _-]+?)(?:\s+(?:asc|ascending|desc|descending))?$", text)
    if sort_match:
        phrase = sort_match.group(1).strip()
        return _SORT_ALIASES.get(phrase), direction

    return None, direction


def _parse_group_by(text: str) -> str | None:
    if "group by similarity" in text or "group by context" in text or "similarity label" in text:
        return "ContextLabel"
    if "group by bias" in text or "group by outcome" in text or "group by direction" in text:
        return "NextDayBias"
    if "group by position" in text:
        return "MatchPosLabel"
    if "group by stage" in text:
        return "MatchStageLabel"
    if "group by match type" in text or "group by type" in text:
        return "MatchType"
    return None


def _unsupported(raw_text: str, reason: str) -> AgentCommand:
    return AgentCommand(action="unsupported", raw_text=raw_text, reason=reason)


def _mentions_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)
