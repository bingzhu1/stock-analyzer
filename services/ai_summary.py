"""Optional AI summaries built from existing rule-layer outputs.

Boundary contract (06 / 07D / 11F): the AI summary layer is an
**optional source-attributed explanation layer**. It must NEVER:

- Run by default — callers must explicitly opt in via ``enable_ai_summary=True``.
- Generate text without per-sentence source attribution
  (``source_system`` / ``source_field`` / ``source_value`` / ``transformation``).
- Permit ``allow_new_judgment=True`` or ``require_source_attribution=False``.
- Surface trading / hard / forced / required / promotion language. Such
  output triggers a post-check refusal.
- Mutate the input ``payload`` or write back into the three-system / final
  report results.
- Allow any escape-hatch flag that skips the post-check pipeline.

The recommended new API is :func:`generate_ai_summary` which returns a
structured ``ai_summary_result.v1`` dict. The five legacy entry points
(``build_projection_ai_summary`` etc.) remain in place as backward-compat
wrappers that return ``""`` by default; they delegate to
``generate_ai_summary`` and surface its ``summary`` field when explicitly
opted in.

Several legacy prompt constants (``_PROJECTION_INSTRUCTIONS`` etc.) remain
in this module as **dead code** kept only to avoid coupling cleanup with
the boundary fix. The Step 14 cleanup pass will delete them. No live code
path uses them.
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable, Iterable

from services.openai_client import (
    OpenAIClientError,
    OpenAIConfigurationError,
    generate_text,
)


# ---------------------------------------------------------------------------
# Legacy prompt constants — DEAD CODE (kept intentionally for Step 14 cleanup)
# ---------------------------------------------------------------------------

_PROJECTION_INSTRUCTIONS = """\
你是股票研究系统的中文总结助手。
你只能基于输入 payload 整理自然中文。
不要新增事实。
不得改写规则层主结论、方向、开盘倾向、收盘倾向、confidence 或风险等级。
如果字段缺失，请明确写"信息不足"，不要猜测。
输出一段简洁中文推演总结，包含：明日基准判断、开盘推演、收盘推演、依据、风险提醒。
"""

_REVIEW_INSTRUCTIONS = """\
你是股票研究系统的中文复盘总结助手。
你只能基于输入 payload 解释 prediction 与 outcome 的关系。
不要新增事实。
不得改写规则层复盘结论、方向正确性、实际涨跌或已有 review 分类。
如果 prediction 或 outcome 信息不足，请明确说明缺失项，不要猜测。
输出一段简洁中文复盘总结，包含：预测结论、实际结果、偏差原因、下次关注点、风险提醒。
"""

_PROJECTION_EXPLANATION_INSTRUCTIONS = """\
你是股票研究系统的中文解释助手。
你只能基于输入 payload 解释已有规则层推演结果。
不要新增事实。
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
不要新增事实。
不得改写规则层主结论或风险等级。
如果风险提醒为空，请说明当前结构化风险不足，不能自行编造。
输出简洁中文说明。
"""


# ---------------------------------------------------------------------------
# 11F contract constants
# ---------------------------------------------------------------------------

_ALLOWED_SOURCE_SYSTEMS: tuple[str, ...] = (
    "projection_result",
    "exclusion_result",
    "confidence_result",
    "final_report",
)

_ALLOWED_TRANSFORMATIONS: tuple[str, ...] = (
    "paraphrase",
    "compression",
    "translation",
    "formatting",
)

# Trading-language ban (07D §11). Mixed Chinese + English. We use case-
# insensitive substring matching for English so post-check tolerates the
# usual capitalisation variations.
_FORBIDDEN_TERMS_TRADING: tuple[str, ...] = (
    "买入",
    "卖出",
    "持有",
    "加仓",
    "减仓",
    "清仓",
    "满仓",
    "空仓",
    "做多",
    "做空",
    "建仓",
    "平仓",
    "buy",
    "sell",
    "hold",
    "long position",
    "short position",
)

_FORBIDDEN_TERMS_HARD: tuple[str, ...] = (
    "强制",
    "必须",
    "务必",
    "一定",
    "应当",
    "hard",
    "forced",
    "required",
    "production ready",
    "生产可用",
)

_FORBIDDEN_TERMS_OVERRIDE: tuple[str, ...] = (
    "最终改判",
    "推翻原判",
    "修正方向",
    "重新预测",
    "适合操作",
    "建议交易",
    "推荐交易",
    "建议买入",
    "建议卖出",
    "建议持有",
    "推荐买入",
    "推荐卖出",
    "推荐持有",
)


_NON_JUDGMENT_FIELDS: tuple[str, ...] = (
    "introduced_new_prediction",
    "introduced_new_exclusion",
    "introduced_new_confidence",
    "introduced_trading_action",
    "introduced_hard_or_forced",
)


_RESULT_FORBIDDEN_FIELDS: frozenset[str] = frozenset({
    "trading_action",
    "buy",
    "sell",
    "hold",
    "simulated_trade",
    "no_trade",
    "hard_exclusion",
    "forced_exclusion",
    "required_decision",
    "production_promotion",
    "_PROTECTION_LAYER_CONNECTED",
    "final_report_mutation",
    "modified_projection",
    "modified_exclusion",
    "modified_confidence",
    "overridden_most_likely_state",
    "corrected_confidence",
})


# Per-builder allowed source whitelist (11F §7.2).
_BUILDER_ALLOWED_SOURCES: dict[str, tuple[str, ...]] = {
    "projection_summary": ("projection_result", "final_report"),
    "review_summary": ("final_report", "outcome_record"),
    "projection_explanation": ("projection_result",),
    "compare_explanation": ("compare_result",),
    "risk_explanation": ("final_report", "confidence_result"),
}


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _non_judgment_confirmation() -> dict[str, bool]:
    return {field: False for field in _NON_JUDGMENT_FIELDS}


def _empty_result(
    *,
    builder_name: str,
    status: str,
    request_metadata: dict[str, Any],
    warnings: list[str] | None = None,
    policy_violations: list[str] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": "ai_summary_result.v1",
        "system_name": "ai_summary",
        "builder_name": builder_name,
        "status": status,
        "summary": "",
        "sentences": [],
        "source_attribution": [],
        "non_judgment_confirmation": _non_judgment_confirmation(),
        "policy_violations": list(policy_violations or []),
        "warnings": list(warnings or []),
        "request_metadata": dict(request_metadata),
    }
    # Defense in depth: never expose forbidden top-level fields.
    for forbidden in _RESULT_FORBIDDEN_FIELDS:
        payload.pop(forbidden, None)
    return payload


def _filter_payload_by_allowed_sources(
    payload: dict[str, Any] | None,
    allowed: Iterable[str],
) -> dict[str, Any]:
    """Return a fresh dict containing only the whitelisted source keys.

    The helper never mutates ``payload`` — it copies referenced source
    blocks but does not deep-copy them. Callers must not modify the
    returned dict either.
    """
    src = _as_dict(payload)
    return {key: src[key] for key in allowed if key in src and src[key] is not None}


def _build_constrained_prompt(
    allowed_payload: dict[str, Any],
    *,
    builder_name: str,
) -> tuple[str, str]:
    """Return (instructions, input_text). Both are program-built and never
    accept caller-injected text."""
    instructions = (
        "你是股票研究系统的中文总结助手。\n"
        "\n"
        "【硬规则 - 不可违反】\n"
        "1. 你只能基于下面的 ALLOWED_SOURCES 字段改写文本。\n"
        "2. 不得添加任何 ALLOWED_SOURCES 中不存在的事实。\n"
        "3. 不得输出交易建议。禁止使用：买入 / 卖出 / 持有 / 加仓 / 减仓 / 清仓。\n"
        "4. 不得说\"应该\"、\"必须\"、\"务必\"、\"一定\"、\"建议\"、\"推荐\"。\n"
        "5. 不得修改 most_likely / most_unlikely / confidence level / direction。\n"
        "6. 不得重新分类冲突。如果 source 说 strong_conflict，你不能写\"基本一致\"。\n"
        "7. 不得自己重算 confidence。\n"
        "8. 不得说\"hard / forced / required / 强制 / 生产可用\"。\n"
        "9. 不得引用 ALLOWED_SOURCES 之外的\"行业知识\"或\"历史经验\"。\n"
        "10. 如果 ALLOWED_SOURCES 信息不足以支持某句话，请明确写\"信息不足\"。\n"
        "\n"
        "【输出格式 - 严格 JSON】\n"
        "{\n"
        "  \"sentences\": [\n"
        "    {\n"
        "      \"sentence\": \"<中文句子>\",\n"
        "      \"source_system\": \"<projection_result|exclusion_result|confidence_result|final_report>\",\n"
        "      \"source_field\": \"<source 中的字段名>\",\n"
        "      \"source_value\": \"<source 中的字段值，原样或同语义>\",\n"
        "      \"transformation\": \"<paraphrase|compression|translation|formatting>\"\n"
        "    }\n"
        "  ]\n"
        "}\n"
        "不要在 JSON 之外输出任何文字。\n"
    )
    body = json.dumps(allowed_payload or {}, ensure_ascii=False, indent=2, sort_keys=True, default=str)
    input_text = (
        f"【BUILDER】{builder_name}\n"
        f"【ALLOWED_SOURCES】\n{body}\n"
        "【任务】基于上面 ALLOWED_SOURCES，按【输出格式】生成中文总结。\n"
    )
    return instructions, input_text


def _parse_llm_json(raw: str) -> tuple[dict | None, str | None]:
    text = (raw or "").strip()
    if not text:
        return None, "llm_output_empty"
    # Some LLMs wrap JSON in ```json fences. Strip the most common form.
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n", "", text)
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None, "llm_output_not_json"
    if not isinstance(parsed, dict):
        return None, "llm_output_not_dict"
    return parsed, None


def _validate_sentence_attribution(
    sentence: dict,
    *,
    allowed_payload: dict[str, Any],
) -> str | None:
    """Return None if valid; otherwise a violation reason."""
    if not isinstance(sentence, dict):
        return "sentence_not_dict"
    for required in ("sentence", "source_system", "source_field", "source_value", "transformation"):
        if not str(sentence.get(required) or "").strip():
            return f"sentence_missing_field:{required}"
    source_system = str(sentence.get("source_system"))
    if source_system not in _ALLOWED_SOURCE_SYSTEMS:
        return f"source_system_not_allowed:{source_system}"
    transformation = str(sentence.get("transformation"))
    if transformation not in _ALLOWED_TRANSFORMATIONS:
        return f"transformation_not_allowed:{transformation}"
    if source_system not in allowed_payload:
        return f"source_system_not_in_payload:{source_system}"
    return None


def _post_check_forbidden_terms(text: str) -> list[str]:
    violations: list[str] = []
    lower = text.lower()
    for term_group in (
        _FORBIDDEN_TERMS_TRADING,
        _FORBIDDEN_TERMS_HARD,
        _FORBIDDEN_TERMS_OVERRIDE,
    ):
        for term in term_group:
            if not term:
                continue
            if term.isascii() and term.islower():
                if term in lower:
                    violations.append(f"matched_term:{term}")
            else:
                if term in text:
                    violations.append(f"matched_term:{term}")
    return violations


def _make_request_metadata(
    *,
    builder_name: str,
    enable_ai_summary: bool,
    require_source_attribution: bool,
    allow_new_judgment: bool,
    allowed_source_systems: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "builder_name": builder_name,
        "enable_ai_summary": bool(enable_ai_summary),
        "require_source_attribution": bool(require_source_attribution),
        "allow_new_judgment": bool(allow_new_judgment),
        "allowed_source_systems": list(allowed_source_systems),
    }


def generate_ai_summary(
    payload: dict[str, Any] | None,
    *,
    builder_name: str = "projection_summary",
    enable_ai_summary: bool = False,
    require_source_attribution: bool = True,
    allow_new_judgment: bool = False,
    allowed_source_systems: tuple[str, ...] | None = None,
    llm_generate: Callable[..., str] | None = None,
) -> dict[str, Any]:
    """Build a structured ``ai_summary_result.v1`` dict.

    Boundary contract (read-only):

    - ``enable_ai_summary=False`` (default): never call the LLM; return a
      ``status="disabled"`` result.
    - ``allow_new_judgment=True`` or ``require_source_attribution=False``:
      always refuse with ``status="refused_policy_violation"``.
    - LLM output must be JSON of shape
      ``{"sentences": [{sentence, source_system, source_field,
      source_value, transformation}, ...]}``; failure → ``refused_missing_sources``.
    - Each sentence is validated against the allowed_source_systems
      whitelist (and ``_ALLOWED_TRANSFORMATIONS``).
    - Output text is scanned against ``_FORBIDDEN_TERMS_*``; any hit →
      ``status="refused_policy_violation"`` with ``policy_violations``
      populated.
    - On ``OpenAIConfigurationError`` → ``status="llm_unavailable"``.
    - On ``OpenAIClientError`` → ``status="llm_error"``.
    - The result never carries trading / hard / forced / required /
      promotion / mutation fields. ``non_judgment_confirmation`` always
      lists five ``False`` flags.
    - ``payload`` is never mutated.

    Returns a fresh dict every call.
    """
    sources_whitelist = tuple(allowed_source_systems) if allowed_source_systems else (
        _BUILDER_ALLOWED_SOURCES.get(builder_name)
        or _ALLOWED_SOURCE_SYSTEMS
    )
    request_metadata = _make_request_metadata(
        builder_name=builder_name,
        enable_ai_summary=enable_ai_summary,
        require_source_attribution=require_source_attribution,
        allow_new_judgment=allow_new_judgment,
        allowed_source_systems=sources_whitelist,
    )

    # Gate 0: opt-in. Default disabled — never call the LLM.
    if not enable_ai_summary:
        return _empty_result(
            builder_name=builder_name,
            status="disabled",
            request_metadata=request_metadata,
            warnings=["ai_summary 默认关闭；请显式传入 enable_ai_summary=True 才会调用 LLM。"],
        )

    # Gate 1: allow_new_judgment must be False (07D §5).
    if allow_new_judgment:
        return _empty_result(
            builder_name=builder_name,
            status="refused_policy_violation",
            request_metadata=request_metadata,
            policy_violations=["allow_new_judgment must remain False under 07D"],
            warnings=["allow_new_judgment=True 被 07D 契约禁止；请改为 False。"],
        )

    # Gate 2: require_source_attribution must stay True.
    if not require_source_attribution:
        return _empty_result(
            builder_name=builder_name,
            status="refused_policy_violation",
            request_metadata=request_metadata,
            policy_violations=[
                "require_source_attribution must remain True under 07D §10",
            ],
            warnings=["require_source_attribution=False 被 07D §10 契约禁止。"],
        )

    # Gate 3: filter to allowed sources. If nothing remains → refuse.
    allowed_payload = _filter_payload_by_allowed_sources(payload, sources_whitelist)
    if not allowed_payload:
        return _empty_result(
            builder_name=builder_name,
            status="refused_missing_sources",
            request_metadata=request_metadata,
            warnings=[
                "payload 缺少 allowed_source_systems 内的字段；ai_summary 拒绝调用 LLM。",
            ],
        )

    instructions, input_text = _build_constrained_prompt(
        allowed_payload, builder_name=builder_name
    )

    runner = llm_generate if llm_generate is not None else generate_text
    try:
        raw = runner(input_text=input_text, instructions=instructions)
    except OpenAIConfigurationError as exc:
        return _empty_result(
            builder_name=builder_name,
            status="llm_unavailable",
            request_metadata=request_metadata,
            warnings=[f"OPENAI 未配置：{exc}"],
        )
    except OpenAIClientError as exc:
        return _empty_result(
            builder_name=builder_name,
            status="llm_error",
            request_metadata=request_metadata,
            warnings=[f"OPENAI 调用失败：{exc}"],
        )
    except Exception as exc:  # pragma: no cover — defensive
        return _empty_result(
            builder_name=builder_name,
            status="llm_error",
            request_metadata=request_metadata,
            warnings=[f"AI summary 生成失败：{exc}"],
        )

    parsed, parse_reason = _parse_llm_json(raw if isinstance(raw, str) else "")
    if parsed is None:
        return _empty_result(
            builder_name=builder_name,
            status="refused_missing_sources",
            request_metadata=request_metadata,
            warnings=[f"LLM 输出不符合期望 JSON 结构：{parse_reason}"],
        )
    sentences_raw = parsed.get("sentences")
    if not isinstance(sentences_raw, list) or not sentences_raw:
        return _empty_result(
            builder_name=builder_name,
            status="refused_missing_sources",
            request_metadata=request_metadata,
            warnings=["LLM 未返回 sentences 数组。"],
        )

    # Per-sentence attribution validation.
    attribution_violations: list[str] = []
    for index, sentence in enumerate(sentences_raw):
        violation = _validate_sentence_attribution(
            sentence, allowed_payload=allowed_payload
        )
        if violation is not None:
            attribution_violations.append(f"sentence[{index}]:{violation}")
    if attribution_violations:
        return _empty_result(
            builder_name=builder_name,
            status="refused_missing_sources",
            request_metadata=request_metadata,
            warnings=attribution_violations,
        )

    # Post-check forbidden language.
    full_text = " ".join(
        str(s.get("sentence") or "").strip() for s in sentences_raw
    ).strip()
    policy_violations = _post_check_forbidden_terms(full_text)
    if policy_violations:
        return _empty_result(
            builder_name=builder_name,
            status="refused_policy_violation",
            request_metadata=request_metadata,
            policy_violations=policy_violations,
            warnings=["AI 输出命中禁止词，已拒绝。"],
        )

    sanitized_sentences: list[dict[str, str]] = []
    source_attribution: list[dict[str, Any]] = []
    for index, sentence in enumerate(sentences_raw):
        clean = {
            "sentence": str(sentence.get("sentence") or "").strip(),
            "source_system": str(sentence.get("source_system") or ""),
            "source_field": str(sentence.get("source_field") or ""),
            "source_value": sentence.get("source_value"),
            "transformation": str(sentence.get("transformation") or ""),
        }
        sanitized_sentences.append(clean)
        source_attribution.append({
            "sentence_index": index,
            "source_system": clean["source_system"],
            "source_field": clean["source_field"],
        })

    summary_text = " ".join(s["sentence"] for s in sanitized_sentences if s["sentence"])
    result: dict[str, Any] = {
        "schema_version": "ai_summary_result.v1",
        "system_name": "ai_summary",
        "builder_name": builder_name,
        "status": "ok",
        "summary": summary_text,
        "sentences": sanitized_sentences,
        "source_attribution": source_attribution,
        "non_judgment_confirmation": _non_judgment_confirmation(),
        "policy_violations": [],
        "warnings": [],
        "request_metadata": request_metadata,
    }
    for forbidden in _RESULT_FORBIDDEN_FIELDS:
        result.pop(forbidden, None)
    return result


# ---------------------------------------------------------------------------
# Backward-compat wrappers (5 legacy public APIs)
# ---------------------------------------------------------------------------
#
# UI / tool_router callers rely on the original five public names and on a
# string return type. We keep the names and signatures, but the safe-by-
# default behaviour is now ``return ""`` unless the caller explicitly opts
# in via ``enable_ai_summary=True``. When opted in, the functions delegate
# to ``generate_ai_summary`` and surface its ``summary`` field.
# ---------------------------------------------------------------------------


def _legacy_string(
    payload: dict[str, Any],
    *,
    builder_name: str,
    enable_ai_summary: bool,
    text_generator: Callable[..., str],
    require_source_attribution: bool = True,
    allow_new_judgment: bool = False,
) -> str:
    result = generate_ai_summary(
        payload,
        builder_name=builder_name,
        enable_ai_summary=enable_ai_summary,
        require_source_attribution=require_source_attribution,
        allow_new_judgment=allow_new_judgment,
        llm_generate=text_generator,
    )
    return str(result.get("summary") or "")


def build_projection_ai_summary(
    payload: dict[str, Any],
    *,
    enable_ai_summary: bool = False,
    text_generator: Callable[..., str] = generate_text,
) -> str:
    """Backward-compat wrapper. Returns ``""`` by default (opt-in gate)."""
    return _legacy_string(
        payload,
        builder_name="projection_summary",
        enable_ai_summary=enable_ai_summary,
        text_generator=text_generator,
    )


def build_review_ai_summary(
    payload: dict[str, Any],
    *,
    enable_ai_summary: bool = False,
    text_generator: Callable[..., str] = generate_text,
) -> str:
    """Backward-compat wrapper. Returns ``""`` by default (opt-in gate)."""
    return _legacy_string(
        payload,
        builder_name="review_summary",
        enable_ai_summary=enable_ai_summary,
        text_generator=text_generator,
    )


def build_projection_ai_explanation(
    payload: dict[str, Any],
    *,
    enable_ai_summary: bool = False,
    text_generator: Callable[..., str] = generate_text,
) -> str:
    """Backward-compat wrapper. Returns ``""`` by default (opt-in gate)."""
    return _legacy_string(
        payload,
        builder_name="projection_explanation",
        enable_ai_summary=enable_ai_summary,
        text_generator=text_generator,
    )


def build_compare_ai_explanation(
    payload: dict[str, Any],
    *,
    enable_ai_summary: bool = False,
    text_generator: Callable[..., str] = generate_text,
) -> str:
    """Backward-compat wrapper. Returns ``""`` by default (opt-in gate)."""
    return _legacy_string(
        payload,
        builder_name="compare_explanation",
        enable_ai_summary=enable_ai_summary,
        text_generator=text_generator,
    )


def build_risk_ai_explanation(
    payload: dict[str, Any],
    *,
    enable_ai_summary: bool = False,
    text_generator: Callable[..., str] = generate_text,
) -> str:
    """Backward-compat wrapper. Returns ``""`` by default (opt-in gate)."""
    return _legacy_string(
        payload,
        builder_name="risk_explanation",
        enable_ai_summary=enable_ai_summary,
        text_generator=text_generator,
    )
