"""Minimal OpenAI Responses API client for text-only summaries."""

from __future__ import annotations

import json
import os
from typing import Any
from urllib import error, request


OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
DEFAULT_MODEL = "gpt-5.4-mini"


class OpenAIClientError(RuntimeError):
    """Base error for controlled OpenAI summary failures."""


class OpenAIConfigurationError(OpenAIClientError):
    """Raised when OpenAI is not configured for optional AI summaries."""


def _extract_output_text(response_payload: dict[str, Any]) -> str:
    text = response_payload.get("output_text")
    if isinstance(text, str) and text.strip():
        return text.strip()

    chunks: list[str] = []
    for item in response_payload.get("output", []) or []:
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []) or []:
            if not isinstance(content, dict):
                continue
            value = content.get("text")
            if isinstance(value, str):
                chunks.append(value)
    joined = "\n".join(part.strip() for part in chunks if part.strip())
    if joined:
        return joined
    raise OpenAIClientError("OpenAI response did not contain text output.")


def generate_text(
    *,
    input_text: str,
    instructions: str,
    model: str | None = None,
    timeout: int = 45,
) -> str:
    """
    Generate plain text with the OpenAI Responses API.

    Requires OPENAI_API_KEY. OPENAI_MODEL can override the default model.
    Raises controlled OpenAIClientError subclasses on missing config or API failure.
    """
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise OpenAIConfigurationError("OPENAI_API_KEY 未配置，暂时无法生成 AI 总结。")

    selected_model = (model or os.getenv("OPENAI_MODEL", "").strip() or DEFAULT_MODEL)
    body = {
        "model": selected_model,
        "instructions": instructions,
        "input": input_text,
    }
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        OPENAI_RESPONSES_URL,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise OpenAIClientError(f"OpenAI API 调用失败：HTTP {exc.code} {detail}") from exc
    except error.URLError as exc:
        raise OpenAIClientError(f"OpenAI API 网络错误：{exc.reason}") from exc
    except TimeoutError as exc:
        raise OpenAIClientError("OpenAI API 调用超时。") from exc

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise OpenAIClientError("OpenAI API 返回了无法解析的响应。") from exc
    if not isinstance(parsed, dict):
        raise OpenAIClientError("OpenAI API 返回格式异常。")
    return _extract_output_text(parsed)
