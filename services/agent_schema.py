from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


CommandAction = Literal[
    "summarize_scan",
    "explain_bias",
    "compare_matches",
    "show_matches",
    "group_matches",
    "help",
    "unsupported",
]

DatasetScope = Literal["all", "exact", "near", "current"]
SortDirection = Literal["asc", "desc"]


@dataclass(frozen=True)
class CommandFilter:
    field: str
    op: Literal["eq", "gt", "lt", "ge", "le"]
    value: str | float


@dataclass(frozen=True)
class AgentCommand:
    action: CommandAction
    raw_text: str
    dataset: DatasetScope = "current"
    filters: tuple[CommandFilter, ...] = field(default_factory=tuple)
    sort_by: str | None = None
    sort_dir: SortDirection = "desc"
    limit: int = 10
    group_by: str | None = None
    reason: str | None = None


@dataclass(frozen=True)
class CommandSpec:
    action: CommandAction
    label: str
    description: str
    examples: tuple[str, ...]


SUPPORTED_SCOPES: tuple[tuple[str, str], ...] = (
    ("displayed", "default; exact + near rows after active sidebar filters"),
    ("exact", "all exact-code matches"),
    ("near", "all near-code matches"),
    ("all", "all exact + near rows before sidebar result filters"),
)

SUPPORTED_FILTERS: tuple[tuple[str, str], ...] = (
    ("similarity", "high / medium / low similarity"),
    ("direction", "bullish / bearish cases from NextCloseMove"),
    ("position", "low / middle / high position when MatchPosLabel exists"),
)

SUPPORTED_SORTS: tuple[tuple[str, str], ...] = (
    ("context score", "ContextScore"),
    ("match date", "MatchDate"),
    ("next close", "NextCloseMove"),
    ("next open", "NextOpenChange"),
    ("next high", "NextHighMove"),
    ("next low", "NextLowMove"),
    ("position", "MatchPos30"),
    ("ret5", "MatchRet5"),
    ("vcode", "VCodeDiff"),
)
SUPPORTED_SORT_COLUMNS: tuple[str, ...] = tuple(column for _, column in SUPPORTED_SORTS)

SUPPORTED_GROUPS: tuple[tuple[str, str], ...] = (
    ("similarity label", "ContextLabel"),
    ("bias / direction", "NextDayBias"),
    ("position", "MatchPosLabel"),
    ("stage", "MatchStageLabel"),
    ("match type", "MatchType"),
)
SUPPORTED_GROUP_COLUMNS: tuple[str, ...] = tuple(column for _, column in SUPPORTED_GROUPS)

ALLOWED_ACTIONS: tuple[str, ...] = (
    "summarize_scan",
    "explain_bias",
    "compare_matches",
    "show_matches",
    "group_matches",
    "help",
    "unsupported",
)
ALLOWED_DATASETS: tuple[str, ...] = ("current", "exact", "near", "all")
ALLOWED_SORT_DIRS: tuple[str, ...] = ("asc", "desc")
ALLOWED_FILTER_OPS: tuple[str, ...] = ("eq", "gt", "lt", "ge", "le")

COMMAND_SPECS: tuple[CommandSpec, ...] = (
    CommandSpec(
        action="summarize_scan",
        label="Summarize scan",
        description="Summarize the current ScanResult.",
        examples=("summarize the current scan result",),
    ),
    CommandSpec(
        action="explain_bias",
        label="Explain bias",
        description="Explain current bias and confidence from scan factors.",
        examples=("explain the current bias",),
    ),
    CommandSpec(
        action="compare_matches",
        label="Compare matches",
        description="Compare exact and near match counts and simple outcomes.",
        examples=("compare exact and near matches",),
    ),
    CommandSpec(
        action="show_matches",
        label="Show matches",
        description="Show rows with optional scope, filters, sort, and top-N limit.",
        examples=(
            "show top 10 high similarity samples",
            "sort by context score descending",
            "show only bullish cases",
        ),
    ),
    CommandSpec(
        action="group_matches",
        label="Group matches",
        description="Group rows by a supported label.",
        examples=("group by similarity label",),
    ),
)

STARTER_EXAMPLES: tuple[str, ...] = tuple(
    example for spec in COMMAND_SPECS for example in spec.examples
)

MODEL_COMMAND_JSON_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": ["action", "dataset", "filters", "sort_by", "sort_dir", "limit", "group_by"],
    "properties": {
        "action": {
            "type": "string",
            "enum": [
                *ALLOWED_ACTIONS,
            ],
        },
        "dataset": {"type": "string", "enum": [*ALLOWED_DATASETS]},
        "filters": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["field", "op", "value"],
                "properties": {
                    "field": {"type": "string"},
                    "op": {"type": "string", "enum": [*ALLOWED_FILTER_OPS]},
                    "value": {"type": ["string", "number"]},
                },
            },
        },
        "sort_by": {"type": ["string", "null"], "enum": [None, *SUPPORTED_SORT_COLUMNS]},
        "sort_dir": {"type": "string", "enum": [*ALLOWED_SORT_DIRS]},
        "limit": {"type": "integer", "minimum": 1, "maximum": 50},
        "group_by": {"type": ["string", "null"], "enum": [None, *SUPPORTED_GROUP_COLUMNS]},
        "reason": {"type": ["string", "null"]},
    },
}

_REQUIRED_MODEL_FIELDS = {"action", "dataset", "filters", "sort_by", "sort_dir", "limit", "group_by"}
_OPTIONAL_MODEL_FIELDS = {"reason"}
_ALLOWED_MODEL_FIELDS = _REQUIRED_MODEL_FIELDS | _OPTIONAL_MODEL_FIELDS


class CommandSchemaError(ValueError):
    """Raised when a model-produced command does not match agent_schema."""


def coerce_model_command(payload: Any, raw_text: str) -> AgentCommand:
    """
    Validate and coerce a model-produced dict into AgentCommand.

    This intentionally uses local checks instead of a jsonschema dependency. The
    accepted shape mirrors MODEL_COMMAND_JSON_SCHEMA and is strict enough that
    query_executor can safely consume the returned AgentCommand.
    """
    if not isinstance(payload, dict):
        raise CommandSchemaError("model output must be an object")

    keys = set(payload)
    missing = sorted(_REQUIRED_MODEL_FIELDS - keys)
    if missing:
        raise CommandSchemaError("model output missing fields: " + ", ".join(missing))

    extra = sorted(keys - _ALLOWED_MODEL_FIELDS)
    if extra:
        raise CommandSchemaError("model output has unsupported fields: " + ", ".join(extra))

    action = _require_str_choice(payload["action"], ALLOWED_ACTIONS, "action")
    dataset = _require_str_choice(payload["dataset"], ALLOWED_DATASETS, "dataset")
    sort_dir = _require_str_choice(payload["sort_dir"], ALLOWED_SORT_DIRS, "sort_dir")
    sort_by = _coerce_optional_choice(payload["sort_by"], SUPPORTED_SORT_COLUMNS, "sort_by")
    group_by = _coerce_optional_choice(payload["group_by"], SUPPORTED_GROUP_COLUMNS, "group_by")
    limit = _coerce_limit(payload["limit"])
    filters = tuple(_coerce_filter(item, index) for index, item in enumerate(payload["filters"]))
    reason = payload.get("reason")
    if reason is not None and not isinstance(reason, str):
        raise CommandSchemaError("reason must be a string or null")
    _validate_action_shape(action, sort_by, group_by)

    return AgentCommand(
        action=action,  # type: ignore[arg-type]
        raw_text=raw_text,
        dataset=dataset,  # type: ignore[arg-type]
        filters=filters,
        sort_by=sort_by,
        sort_dir=sort_dir,  # type: ignore[arg-type]
        limit=limit,
        group_by=group_by,
        reason=reason,
    )


def _require_str_choice(value: Any, choices: tuple[str, ...], field_name: str) -> str:
    if not isinstance(value, str):
        raise CommandSchemaError(f"{field_name} must be a string")
    if value not in choices:
        raise CommandSchemaError(f"{field_name} has unsupported value: {value}")
    return value


def _coerce_optional_choice(value: Any, choices: tuple[str, ...], field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise CommandSchemaError(f"{field_name} must be a string or null")
    if value not in choices:
        raise CommandSchemaError(f"{field_name} has unsupported value: {value}")
    return value


def _coerce_limit(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise CommandSchemaError("limit must be an integer")
    if value < 1 or value > 50:
        raise CommandSchemaError("limit must be between 1 and 50")
    return value


def _coerce_filter(value: Any, index: int) -> CommandFilter:
    if not isinstance(value, dict):
        raise CommandSchemaError(f"filters[{index}] must be an object")
    keys = set(value)
    required = {"field", "op", "value"}
    if keys != required:
        raise CommandSchemaError(f"filters[{index}] must contain exactly field, op, value")
    field = value["field"]
    op = value["op"]
    filter_value = value["value"]
    if not isinstance(field, str) or not field:
        raise CommandSchemaError(f"filters[{index}].field must be a non-empty string")
    op = _require_str_choice(op, ALLOWED_FILTER_OPS, f"filters[{index}].op")
    if isinstance(filter_value, bool) or not isinstance(filter_value, (str, int, float)):
        raise CommandSchemaError(f"filters[{index}].value must be a string or number")
    return CommandFilter(field=field, op=op, value=filter_value)


def _validate_action_shape(action: str, sort_by: str | None, group_by: str | None) -> None:
    if action == "group_matches" and group_by is None:
        raise CommandSchemaError("group_matches requires group_by")
    if action != "group_matches" and group_by is not None:
        raise CommandSchemaError(f"{action} does not support group_by")
    if action not in ("show_matches", "group_matches") and sort_by is not None:
        raise CommandSchemaError(f"{action} does not support sort_by")


def build_command_help_text() -> str:
    """Return concise user-facing help derived from the command schema."""
    command_lines = [
        f"- {spec.label}: {spec.description}"
        for spec in COMMAND_SPECS
    ]
    scope_lines = [f"- `{name}`: {desc}" for name, desc in SUPPORTED_SCOPES]
    filter_lines = [f"- {name}: {desc}" for name, desc in SUPPORTED_FILTERS]
    sort_lines = [f"- `{name}` -> `{column}`" for name, column in SUPPORTED_SORTS]
    group_lines = [f"- `{name}` -> `{column}`" for name, column in SUPPORTED_GROUPS]
    example_lines = [f"- `{example}`" for example in STARTER_EXAMPLES]

    return "\n\n".join(
        [
            "Supported read-only commands:",
            "\n".join(command_lines),
            "Scopes:",
            "\n".join(scope_lines),
            "Filters:",
            "\n".join(filter_lines),
            "Sort fields:",
            "\n".join(sort_lines),
            "Group fields:",
            "\n".join(group_lines),
            "Examples:",
            "\n".join(example_lines),
        ]
    )
