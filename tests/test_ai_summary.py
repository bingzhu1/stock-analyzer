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

    def _projection_summary_fake(self, sentence_text: str = "明日推演方向偏多。") -> object:
        """Step 12F (RISK-9) — fake LLM that returns the contract JSON shape.

        Each fake reply uses ``transformation=paraphrase`` and references a
        field that exists in the test payload. The legacy wrappers will
        forward this through ``generate_ai_summary``, so the post-check
        passes only when source attribution is well-formed."""
        import json

        body = json.dumps(
            {
                "sentences": [
                    {
                        "sentence": sentence_text,
                        "source_system": "final_report",
                        "source_field": "summary_text",
                        "source_value": "明日方向：偏多",
                        "transformation": "paraphrase",
                    }
                ]
            },
            ensure_ascii=False,
        )

        def _gen(*, input_text: str, instructions: str, **_) -> str:
            return body

        return _gen

    def test_projection_payload_default_does_not_call_llm(self) -> None:
        """Step 12F (RISK-9): the legacy wrapper is opt-in; the default path
        must return an empty string and never invoke the LLM."""
        calls: list = []

        def fake_generator(*, input_text: str, instructions: str, **_) -> str:
            calls.append((input_text, instructions))
            return "AI 推演总结"

        text = build_projection_ai_summary(
            {
                "final_report": {"summary_text": "明日方向：偏多"},
                "final_bias": "bullish",
            },
            text_generator=fake_generator,
        )
        self.assertEqual(text, "")
        self.assertEqual(calls, [])

    def test_projection_payload_opt_in_returns_attributed_summary(self) -> None:
        text = build_projection_ai_summary(
            {
                "final_report": {"summary_text": "明日方向：偏多"},
                "projection_result": {"most_likely_state": "小涨"},
            },
            enable_ai_summary=True,
            text_generator=self._projection_summary_fake("明日推演方向偏多。"),
        )
        self.assertIn("明日推演方向偏多。", text)

    def test_review_payload_default_does_not_call_llm(self) -> None:
        calls: list = []

        def fake_generator(*, input_text: str, instructions: str, **_) -> str:
            calls.append(input_text)
            return "AI 复盘总结"

        text = build_review_ai_summary(
            {
                "final_report": {"summary_text": "复盘文本"},
                "outcome_record": {"direction_correct": 1},
            },
            text_generator=fake_generator,
        )
        self.assertEqual(text, "")
        self.assertEqual(calls, [])

    def test_review_payload_opt_in_returns_attributed_summary(self) -> None:
        import json

        body = json.dumps(
            {
                "sentences": [
                    {
                        "sentence": "上次预测方向已被实际收盘印证。",
                        "source_system": "final_report",
                        "source_field": "summary_text",
                        "source_value": "复盘文本",
                        "transformation": "paraphrase",
                    }
                ]
            },
            ensure_ascii=False,
        )

        def fake_generator(*, input_text: str, instructions: str, **_) -> str:
            return body

        text = build_review_ai_summary(
            {
                "final_report": {"summary_text": "复盘文本"},
                "outcome_record": {"direction_correct": 1},
            },
            enable_ai_summary=True,
            text_generator=fake_generator,
        )
        self.assertIn("上次预测方向已被实际收盘印证。", text)

    def test_projection_explanation_default_does_not_call_llm(self) -> None:
        calls: list = []

        def fake_generator(*, input_text: str, instructions: str, **_) -> str:
            calls.append(input_text)
            return "AI 解释"

        text = build_projection_ai_explanation(
            {"projection_result": {"most_likely_state": "小涨"}},
            text_generator=fake_generator,
        )
        self.assertEqual(text, "")
        self.assertEqual(calls, [])

    def test_compare_explanation_default_does_not_call_llm(self) -> None:
        calls: list = []

        def fake_generator(*, input_text: str, instructions: str, **_) -> str:
            calls.append(input_text)
            return "AI 比较总结"

        text = build_compare_ai_explanation(
            {"compare_result": {"total": 20, "matched": 13, "match_rate": 65.0}},
            text_generator=fake_generator,
        )
        self.assertEqual(text, "")
        self.assertEqual(calls, [])

    def test_risk_explanation_default_does_not_call_llm(self) -> None:
        calls: list = []

        def fake_generator(*, input_text: str, instructions: str, **_) -> str:
            calls.append(input_text)
            return "AI 风险解释"

        text = build_risk_ai_explanation(
            {
                "final_report": {"risk_reminders": ["样本不足"]},
                "confidence_result": {"reliability_warnings": ["样本不足"]},
            },
            text_generator=fake_generator,
        )
        self.assertEqual(text, "")
        self.assertEqual(calls, [])


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
            predict_tab._render_projection_ai_summary_entry_compact(
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
