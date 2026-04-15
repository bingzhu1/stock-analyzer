from __future__ import annotations

import os
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.ai_summary import (
    build_compare_ai_explanation,
    build_projection_ai_explanation,
    build_projection_ai_summary,
    build_review_ai_summary,
    build_risk_ai_explanation,
)
from services.openai_client import OpenAIConfigurationError, generate_text


class _FakeOpenAIResponse:
    def __enter__(self) -> "_FakeOpenAIResponse":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self) -> bytes:
        return b'{"output_text": "mocked summary"}'


def _write_test_env(content: str) -> Path:
    env_dir = ROOT / ".tmp_test_env"
    env_dir.mkdir(exist_ok=True)
    env_path = env_dir / ".env"
    env_path.write_text(content, encoding="utf-8")
    return env_path


def _cleanup_test_env() -> None:
    env_path = ROOT / ".tmp_test_env" / ".env"
    if env_path.exists():
        env_path.unlink()
    env_dir = ROOT / ".tmp_test_env"
    if env_dir.exists():
        env_dir.rmdir()


class AISummaryServiceTests(unittest.TestCase):
    def test_openai_client_reports_missing_api_key_safely(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(OpenAIConfigurationError) as ctx:
                generate_text(input_text="hello", instructions="summarize")

        self.assertIn("OPENAI_API_KEY", str(ctx.exception))

    def test_openai_client_uses_existing_environment_key_and_model(self) -> None:
        captured: dict[str, object] = {}

        def fake_urlopen(req, timeout: int):
            captured["authorization"] = req.get_header("Authorization")
            captured["body"] = json.loads(req.data.decode("utf-8"))
            captured["timeout"] = timeout
            return _FakeOpenAIResponse()

        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "env-key",
                "OPENAI_MODEL": "env-model",
            },
            clear=True,
        ), patch("services.openai_client.request.urlopen", side_effect=fake_urlopen):
            text = generate_text(input_text="hello", instructions="summarize", timeout=3)

        self.assertEqual(text, "mocked summary")
        self.assertEqual(captured["authorization"], "Bearer env-key")
        self.assertEqual(captured["body"]["model"], "env-model")
        self.assertEqual(captured["body"]["input"], "hello")
        self.assertEqual(captured["timeout"], 3)

    def test_dotenv_loaded_values_are_visible_to_openai_client(self) -> None:
        captured: dict[str, object] = {}

        def fake_urlopen(req, timeout: int):
            captured["authorization"] = req.get_header("Authorization")
            captured["body"] = json.loads(req.data.decode("utf-8"))
            return _FakeOpenAIResponse()

        env_path = _write_test_env(
                "OPENAI_API_KEY=dotenv-key\nOPENAI_MODEL=dotenv-model\n",
        )
        try:
            with patch.dict(os.environ, {}, clear=True), patch(
                "services.openai_client.request.urlopen",
                side_effect=fake_urlopen,
            ):
                loaded = load_dotenv(dotenv_path=env_path)
                text = generate_text(input_text="hello", instructions="summarize")
        finally:
            _cleanup_test_env()

        self.assertTrue(loaded)
        self.assertEqual(text, "mocked summary")
        self.assertEqual(captured["authorization"], "Bearer dotenv-key")
        self.assertEqual(captured["body"]["model"], "dotenv-model")

    def test_dotenv_does_not_override_existing_environment_by_default(self) -> None:
        captured: dict[str, object] = {}

        def fake_urlopen(req, timeout: int):
            captured["authorization"] = req.get_header("Authorization")
            captured["body"] = json.loads(req.data.decode("utf-8"))
            return _FakeOpenAIResponse()

        env_path = _write_test_env(
                "OPENAI_API_KEY=dotenv-key\nOPENAI_MODEL=dotenv-model\n",
        )
        try:
            with patch.dict(
                os.environ,
                {
                    "OPENAI_API_KEY": "system-key",
                    "OPENAI_MODEL": "system-model",
                },
                clear=True,
            ), patch("services.openai_client.request.urlopen", side_effect=fake_urlopen):
                loaded = load_dotenv(dotenv_path=env_path)
                text = generate_text(input_text="hello", instructions="summarize")
        finally:
            _cleanup_test_env()

        self.assertTrue(loaded)
        self.assertEqual(text, "mocked summary")
        self.assertEqual(captured["authorization"], "Bearer system-key")
        self.assertEqual(captured["body"]["model"], "system-model")

    def test_projection_payload_builds_guarded_prompt(self) -> None:
        captured: dict[str, str] = {}

        def fake_generator(*, input_text: str, instructions: str) -> str:
            captured["input_text"] = input_text
            captured["instructions"] = instructions
            return "AI 推演总结"

        text = build_projection_ai_summary(
            {
                "final_bias": "bullish",
                "readable_summary": {"summary_text": "明日方向：偏多"},
            },
            text_generator=fake_generator,
        )

        self.assertEqual(text, "AI 推演总结")
        self.assertIn('"final_bias": "bullish"', captured["input_text"])
        self.assertIn("明日方向：偏多", captured["input_text"])
        self.assertIn("不要新增事实", captured["instructions"])
        self.assertIn("不得改写规则层主结论", captured["instructions"])

    def test_review_payload_builds_guarded_prompt(self) -> None:
        captured: dict[str, str] = {}

        def fake_generator(*, input_text: str, instructions: str) -> str:
            captured["input_text"] = input_text
            captured["instructions"] = instructions
            return "AI 复盘总结"

        text = build_review_ai_summary(
            {
                "prediction_id": "pid-1",
                "final_bias": "bearish",
                "outcome": {"direction_correct": 1, "actual_close_change": -0.012},
            },
            text_generator=fake_generator,
        )

        self.assertEqual(text, "AI 复盘总结")
        self.assertIn('"prediction_id": "pid-1"', captured["input_text"])
        self.assertIn('"direction_correct": 1', captured["input_text"])
        self.assertIn("不要新增事实", captured["instructions"])
        self.assertIn("不得改写规则层复盘结论", captured["instructions"])

    def test_projection_explanation_prompt_keeps_rule_conclusion_fixed(self) -> None:
        captured: dict[str, str] = {}

        def fake_generator(*, input_text: str, instructions: str) -> str:
            captured["input_text"] = input_text
            captured["instructions"] = instructions
            return "AI 解释"

        text = build_projection_ai_explanation(
            {
                "ai_request": {"focus": "direction", "direction": "偏多"},
                "projection_report": {"direction": "偏多", "confidence": "low"},
            },
            text_generator=fake_generator,
        )

        self.assertEqual(text, "AI 解释")
        self.assertIn('"direction": "偏多"', captured["input_text"])
        self.assertIn("不要新增事实", captured["instructions"])
        self.assertIn("不得改写规则层主结论", captured["instructions"])
        self.assertIn("不要重新预测", captured["input_text"])

    def test_compare_explanation_prompt_uses_existing_stats_only(self) -> None:
        captured: dict[str, str] = {}

        def fake_generator(*, input_text: str, instructions: str) -> str:
            captured["input_text"] = input_text
            captured["instructions"] = instructions
            return "AI 比较总结"

        text = build_compare_ai_explanation(
            {"stats": {"total": 20, "matched": 13, "match_rate": 65.0}},
            text_generator=fake_generator,
        )

        self.assertEqual(text, "AI 比较总结")
        self.assertIn('"matched": 13', captured["input_text"])
        self.assertIn("不得改写 total", captured["instructions"])

    def test_risk_explanation_prompt_does_not_invent_risks(self) -> None:
        captured: dict[str, str] = {}

        def fake_generator(*, input_text: str, instructions: str) -> str:
            captured["input_text"] = input_text
            captured["instructions"] = instructions
            return "AI 风险解释"

        text = build_risk_ai_explanation(
            {"readable_summary": {"risk_reminders": ["样本不足"]}},
            text_generator=fake_generator,
        )

        self.assertEqual(text, "AI 风险解释")
        self.assertIn("样本不足", captured["input_text"])
        self.assertIn("不要新增事实", captured["instructions"])
        self.assertIn("不得改写规则层主结论", captured["instructions"])


class _FakeSpinner:
    def __enter__(self) -> "_FakeSpinner":
        return self

    def __exit__(self, *_: object) -> None:
        return None


class _FakeStreamlit:
    def __init__(self) -> None:
        self.session_state: dict[str, str] = {}
        self.messages: list[tuple[str, str]] = []

    def markdown(self, text: str) -> None:
        self.messages.append(("markdown", text))

    def button(self, label: str, key: str | None = None, disabled: bool = False) -> bool:
        self.messages.append(("button", f"{label}|{key}|{disabled}"))
        return not disabled

    def spinner(self, text: str) -> _FakeSpinner:
        self.messages.append(("spinner", text))
        return _FakeSpinner()

    def warning(self, text: str) -> None:
        self.messages.append(("warning", text))

    def write(self, text: object) -> None:
        self.messages.append(("write", str(text)))

    def caption(self, text: str) -> None:
        self.messages.append(("caption", text))


class AISummaryUITests(unittest.TestCase):
    def test_projection_ai_summary_failure_does_not_crash_ui(self) -> None:
        from ui import predict_tab

        fake_st = _FakeStreamlit()
        with patch.object(predict_tab, "st", fake_st), patch.object(
            predict_tab,
            "build_projection_ai_summary",
            side_effect=OpenAIConfigurationError("OPENAI_API_KEY 未配置，暂时无法生成 AI 总结。"),
        ):
            predict_tab._render_projection_ai_summary_entry(
                {"symbol": "AVGO", "final_bias": "bullish"},
                {"scan_bias": "bullish"},
                None,
            )

        self.assertTrue(
            any(kind == "warning" and "OPENAI_API_KEY" in message for kind, message in fake_st.messages)
        )
        self.assertNotIn("ai_projection_summary_text", fake_st.session_state)


if __name__ == "__main__":
    unittest.main()
