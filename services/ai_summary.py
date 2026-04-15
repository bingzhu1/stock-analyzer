"""Optional AI summaries built from existing rule-layer outputs."""

from __future__ import annotations

import json
from typing import Any, Callable

from services.openai_client import generate_text


_PROJECTION_INSTRUCTIONS = """\
你是股票研究系统的中文总结助手。
你只能基于输入 payload 整理自然中文。
不得改写规则层主结论、方向、开盘倾向、收盘倾向、confidence 或风险等级。
如果字段缺失，请明确写“信息不足”，不要猜测。
输出一段简洁中文推演总结，包含：明日基准判断、开盘推演、收盘推演、依据、风险提醒。
"""

_REVIEW_INSTRUCTIONS = """\
你是股票研究系统的中文复盘总结助手。
你只能基于输入 payload 解释 prediction 与 outcome 的关系。
不得改写规则层复盘结论、方向正确性、实际涨跌或已有 review 分类。
如果 prediction 或 outcome 信息不足，请明确说明缺失项，不要猜测。
输出一段简洁中文复盘总结，包含：预测结论、实际结果、偏差原因、下次关注点、风险提醒。
"""

_PROJECTION_EXPLANATION_INSTRUCTIONS = """\
你是股票研究系统的中文解释助手。
你只能基于输入 payload 解释已有规则层推演结果。
不得改写规则层主结论、方向、开盘倾向、收盘倾向、confidence 或风险提醒。
如果用户关注某个方向，请只解释结构化证据如何支持或限制该方向，不要重新预测。
输出简洁中文说明。
"""

_COMPARE_EXPLANATION_INSTRUCTIONS = """\
你是股票研究系统的中文比较结果解释助手。
你只能基于输入 payload 总结已有 compare/stats 结果。
不得改写 total、matched、mismatched、match_rate 或 position distribution。
如果样本不足或字段缺失，请明确提示信息不足。
输出简洁中文说明。
"""

_RISK_EXPLANATION_INSTRUCTIONS = """\
你是股票研究系统的中文风险提醒解释助手。
你只能基于输入 payload 解释已有风险提醒。
不得改写规则层主结论或风险等级。
如果风险提醒为空，请说明当前结构化风险不足，不能自行编造。
输出简洁中文说明。
"""


def _json_payload(payload: dict[str, Any]) -> str:
    return json.dumps(payload or {}, ensure_ascii=False, indent=2, sort_keys=True, default=str)


def _projection_prompt(payload: dict[str, Any]) -> str:
    return (
        "请把下面结构化的规则层推演结果整理为自然中文。再次强调："
        "不要新增事实，不要改写规则层主结论，只做总结解释。\n\n"
        f"payload:\n{_json_payload(payload)}"
    )


def _review_prompt(payload: dict[str, Any]) -> str:
    return (
        "请把下面结构化的预测、实际结果和规则层复盘信息整理为自然中文。再次强调："
        "不要新增事实，不要改写规则层复盘结论，只做总结解释。\n\n"
        f"payload:\n{_json_payload(payload)}"
    )


def _projection_explanation_prompt(payload: dict[str, Any]) -> str:
    return (
        "请解释下面已有规则层推演结果。不要新增事实，不要改写规则层主结论，"
        "不要重新预测。\n\n"
        f"payload:\n{_json_payload(payload)}"
    )


def _compare_explanation_prompt(payload: dict[str, Any]) -> str:
    return (
        "请总结下面已有比较/统计结果。不要新增事实，不要改写统计数值，"
        "不要直接做新的预测。\n\n"
        f"payload:\n{_json_payload(payload)}"
    )


def _risk_explanation_prompt(payload: dict[str, Any]) -> str:
    return (
        "请解释下面已有风险提醒。不要新增事实，不要改写规则层主结论或风险等级，"
        "不要给交易建议。\n\n"
        f"payload:\n{_json_payload(payload)}"
    )


def build_projection_ai_summary(
    payload: dict[str, Any],
    *,
    text_generator: Callable[..., str] = generate_text,
) -> str:
    """Return a plain-text AI projection summary from structured rule results."""
    return text_generator(
        input_text=_projection_prompt(payload),
        instructions=_PROJECTION_INSTRUCTIONS,
    )


def build_review_ai_summary(
    payload: dict[str, Any],
    *,
    text_generator: Callable[..., str] = generate_text,
) -> str:
    """Return a plain-text AI review summary from structured prediction/outcome data."""
    return text_generator(
        input_text=_review_prompt(payload),
        instructions=_REVIEW_INSTRUCTIONS,
    )


def build_projection_ai_explanation(
    payload: dict[str, Any],
    *,
    text_generator: Callable[..., str] = generate_text,
) -> str:
    """Return a plain-text AI explanation for an existing projection result."""
    return text_generator(
        input_text=_projection_explanation_prompt(payload),
        instructions=_PROJECTION_EXPLANATION_INSTRUCTIONS,
    )


def build_compare_ai_explanation(
    payload: dict[str, Any],
    *,
    text_generator: Callable[..., str] = generate_text,
) -> str:
    """Return a plain-text AI explanation for an existing compare result."""
    return text_generator(
        input_text=_compare_explanation_prompt(payload),
        instructions=_COMPARE_EXPLANATION_INSTRUCTIONS,
    )


def build_risk_ai_explanation(
    payload: dict[str, Any],
    *,
    text_generator: Callable[..., str] = generate_text,
) -> str:
    """Return a plain-text AI explanation for existing risk reminders."""
    return text_generator(
        input_text=_risk_explanation_prompt(payload),
        instructions=_RISK_EXPLANATION_INSTRUCTIONS,
    )
