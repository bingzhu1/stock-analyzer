"""Contract enforcement tests for Step 12F (RISK-9) AI summary opt-in gate
+ source attribution + post-check.

These tests pin the AI summary boundary:

1. AI summary is **disabled by default**: callers that do not pass
   ``enable_ai_summary=True`` MUST NOT trigger an LLM call. The result
   schema reports ``status="disabled"`` and ``summary=""``.
2. ``allow_new_judgment=True`` always refuses with ``refused_policy_violation``.
3. ``require_source_attribution=False`` always refuses with
   ``refused_policy_violation``.
4. Source attribution is enforced **per sentence**: each sentence must
   carry ``source_system`` / ``source_field`` / ``source_value`` /
   ``transformation``; failure → ``refused_missing_sources``.
5. Post-check blocks trading language (buy/sell/hold/买入/卖出/持有/...)
   → ``refused_policy_violation`` with ``policy_violations`` list.
6. Post-check blocks hard/forced/required language (强制/必须/...) →
   ``refused_policy_violation``.
7. Post-check blocks recommendation / direction-change language
   (推荐买入/最终改判/...) → ``refused_policy_violation``.
8. Output schema contains ``non_judgment_confirmation`` with five false
   fields and never carries trading / hard / forced / required / promotion
   / mutation / `_PROTECTION_LAYER_CONNECTED` fields.
9. LLM availability errors return ``status="llm_unavailable"`` (key
   missing) or ``status="llm_error"`` (call failure); the result is still
   a well-formed dict and ``summary=""``.
10. The module never mutates the input ``payload``.
11. Static check: no helper bypasses the post-check / writes back to
    final_report or the three system results.

Design contracts: 06 / 07D / 11F / 11H.
"""

from __future__ import annotations

import ast
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


_FORBIDDEN_OUTPUT_FIELDS = (
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
)


def _payload_with_sources() -> dict:
    return {
        "projection_result": {
            "schema_version": "projection_system_result.v1",
            "most_likely_state": "小涨",
            "ranked_states": ["小涨", "震荡", "大涨", "小跌", "大跌"],
        },
        "exclusion_result": {
            "schema_version": "exclusion_system_result.v1",
            "most_unlikely_state": "大跌",
        },
        "confidence_result": {
            "schema_version": "confidence_system_result.v1",
            "combined_confidence": {"level": "medium"},
            "agreement_status": "aligned",
            "conflict_level": "none",
        },
        "final_report": {
            "schema_version": "final_report_aggregator_result.v1",
            "final_direction": "偏多",
            "final_confidence": "medium",
        },
    }


def _llm_returns_json(sentences: list[dict]):
    body = json.dumps({"sentences": sentences}, ensure_ascii=False)

    def _generator(*, input_text: str, instructions: str, **_):
        return body

    return _generator


def _safe_sentence(*, source_system: str = "projection_result",
                   source_field: str = "most_likely_state",
                   source_value: str = "小涨",
                   sentence: str = "明日最可能小幅上涨。",
                   transformation: str = "paraphrase") -> dict:
    return {
        "sentence": sentence,
        "source_system": source_system,
        "source_field": source_field,
        "source_value": source_value,
        "transformation": transformation,
    }


# ---------------------------------------------------------------------------
# Default disabled gate
# ---------------------------------------------------------------------------


class DisabledByDefaultTests(unittest.TestCase):
    def test_ai_summary_disabled_by_default(self) -> None:
        from services.ai_summary import generate_ai_summary

        result = generate_ai_summary(_payload_with_sources())
        self.assertEqual(result["status"], "disabled")
        self.assertEqual(result["summary"], "")
        self.assertEqual(result["schema_version"], "ai_summary_result.v1")
        self.assertEqual(result["system_name"], "ai_summary")

    def test_ai_summary_does_not_call_llm_when_disabled(self) -> None:
        from services.ai_summary import generate_ai_summary

        calls: list = []

        def _spy(*, input_text: str, instructions: str, **_):
            calls.append((input_text, instructions))
            return "{}"

        result = generate_ai_summary(
            _payload_with_sources(),
            llm_generate=_spy,
        )
        self.assertEqual(result["status"], "disabled")
        self.assertEqual(calls, [])


class GateRefusalsTests(unittest.TestCase):
    def test_allow_new_judgment_must_be_false(self) -> None:
        from services.ai_summary import generate_ai_summary

        result = generate_ai_summary(
            _payload_with_sources(),
            enable_ai_summary=True,
            allow_new_judgment=True,
        )
        self.assertEqual(result["status"], "refused_policy_violation")
        self.assertEqual(result["summary"], "")

    def test_require_source_attribution_must_be_true(self) -> None:
        from services.ai_summary import generate_ai_summary

        result = generate_ai_summary(
            _payload_with_sources(),
            enable_ai_summary=True,
            require_source_attribution=False,
        )
        self.assertEqual(result["status"], "refused_policy_violation")
        self.assertEqual(result["summary"], "")


class MissingSourcesTests(unittest.TestCase):
    def test_ai_summary_refuses_missing_sources_when_payload_empty(self) -> None:
        from services.ai_summary import generate_ai_summary

        result = generate_ai_summary(
            {},
            enable_ai_summary=True,
        )
        self.assertEqual(result["status"], "refused_missing_sources")
        self.assertEqual(result["summary"], "")

    def test_ai_summary_refuses_when_llm_returns_plain_text(self) -> None:
        from services.ai_summary import generate_ai_summary

        def _plain_text(*, input_text: str, instructions: str, **_):
            return "LLM 自由发挥的中文文本，没有结构化 JSON。"

        result = generate_ai_summary(
            _payload_with_sources(),
            enable_ai_summary=True,
            llm_generate=_plain_text,
        )
        self.assertEqual(result["status"], "refused_missing_sources")
        self.assertEqual(result["summary"], "")

    def test_ai_summary_refuses_when_sentence_missing_attribution(self) -> None:
        from services.ai_summary import generate_ai_summary

        # Sentence is missing source_field
        bad_sentence = {
            "sentence": "明日最可能小幅上涨。",
            "source_system": "projection_result",
            "source_value": "小涨",
            "transformation": "paraphrase",
        }
        result = generate_ai_summary(
            _payload_with_sources(),
            enable_ai_summary=True,
            llm_generate=_llm_returns_json([bad_sentence]),
        )
        self.assertEqual(result["status"], "refused_missing_sources")
        self.assertEqual(result["summary"], "")

    def test_ai_summary_refuses_unknown_source_system(self) -> None:
        from services.ai_summary import generate_ai_summary

        sentence = _safe_sentence(source_system="raw_market_data")
        result = generate_ai_summary(
            _payload_with_sources(),
            enable_ai_summary=True,
            llm_generate=_llm_returns_json([sentence]),
        )
        self.assertEqual(result["status"], "refused_missing_sources")
        self.assertEqual(result["summary"], "")

    def test_ai_summary_refuses_unknown_transformation(self) -> None:
        from services.ai_summary import generate_ai_summary

        sentence = _safe_sentence(transformation="inference")
        result = generate_ai_summary(
            _payload_with_sources(),
            enable_ai_summary=True,
            llm_generate=_llm_returns_json([sentence]),
        )
        self.assertEqual(result["status"], "refused_missing_sources")
        self.assertEqual(result["summary"], "")


class PostCheckTests(unittest.TestCase):
    def test_postcheck_blocks_trading_buy(self) -> None:
        from services.ai_summary import generate_ai_summary

        sentence = _safe_sentence(sentence="建议买入 AVGO。")
        result = generate_ai_summary(
            _payload_with_sources(),
            enable_ai_summary=True,
            llm_generate=_llm_returns_json([sentence]),
        )
        self.assertEqual(result["status"], "refused_policy_violation")
        self.assertEqual(result["summary"], "")
        self.assertTrue(result["policy_violations"])

    def test_postcheck_blocks_trading_english(self) -> None:
        from services.ai_summary import generate_ai_summary

        sentence = _safe_sentence(sentence="Recommendation: buy and hold.")
        result = generate_ai_summary(
            _payload_with_sources(),
            enable_ai_summary=True,
            llm_generate=_llm_returns_json([sentence]),
        )
        self.assertEqual(result["status"], "refused_policy_violation")

    def test_postcheck_blocks_sell(self) -> None:
        from services.ai_summary import generate_ai_summary

        sentence = _safe_sentence(sentence="建议卖出。")
        result = generate_ai_summary(
            _payload_with_sources(),
            enable_ai_summary=True,
            llm_generate=_llm_returns_json([sentence]),
        )
        self.assertEqual(result["status"], "refused_policy_violation")

    def test_postcheck_blocks_hard_forced_required(self) -> None:
        from services.ai_summary import generate_ai_summary

        for forbidden_sentence in (
            "投资者必须卖出。",
            "强制持有 AVGO。",
            "This is required for production.",
        ):
            sentence = _safe_sentence(sentence=forbidden_sentence)
            result = generate_ai_summary(
                _payload_with_sources(),
                enable_ai_summary=True,
                llm_generate=_llm_returns_json([sentence]),
            )
            self.assertEqual(
                result["status"],
                "refused_policy_violation",
                msg=f"forbidden_sentence={forbidden_sentence!r}",
            )

    def test_postcheck_blocks_recommendation_and_direction_change(self) -> None:
        from services.ai_summary import generate_ai_summary

        for sentence_text in (
            "推荐买入。",
            "最终改判为偏空。",
            "推翻原判。",
        ):
            sentence = _safe_sentence(sentence=sentence_text)
            result = generate_ai_summary(
                _payload_with_sources(),
                enable_ai_summary=True,
                llm_generate=_llm_returns_json([sentence]),
            )
            self.assertEqual(
                result["status"],
                "refused_policy_violation",
                msg=f"sentence={sentence_text!r}",
            )


class NonJudgmentConfirmationTests(unittest.TestCase):
    def test_non_judgment_confirmation_always_present_and_false(self) -> None:
        from services.ai_summary import generate_ai_summary

        # Disabled path
        result = generate_ai_summary(_payload_with_sources())
        confirmations = result["non_judgment_confirmation"]
        for field in (
            "introduced_new_prediction",
            "introduced_new_exclusion",
            "introduced_new_confidence",
            "introduced_trading_action",
            "introduced_hard_or_forced",
        ):
            self.assertIn(field, confirmations)
            self.assertIs(confirmations[field], False)

        # Enabled / ok path
        sentence = _safe_sentence()
        result = generate_ai_summary(
            _payload_with_sources(),
            enable_ai_summary=True,
            llm_generate=_llm_returns_json([sentence]),
        )
        for field in (
            "introduced_new_prediction",
            "introduced_new_exclusion",
            "introduced_new_confidence",
            "introduced_trading_action",
            "introduced_hard_or_forced",
        ):
            self.assertIs(result["non_judgment_confirmation"][field], False)


class LLMErrorTests(unittest.TestCase):
    def test_llm_unavailable_returns_status_when_key_missing(self) -> None:
        from services.ai_summary import generate_ai_summary
        from services.openai_client import OpenAIConfigurationError

        def _no_key(*, input_text: str, instructions: str, **_):
            raise OpenAIConfigurationError("OPENAI_API_KEY 未配置。")

        result = generate_ai_summary(
            _payload_with_sources(),
            enable_ai_summary=True,
            llm_generate=_no_key,
        )
        self.assertEqual(result["status"], "llm_unavailable")
        self.assertEqual(result["summary"], "")
        self.assertTrue(result["warnings"])

    def test_llm_error_returns_status(self) -> None:
        from services.ai_summary import generate_ai_summary
        from services.openai_client import OpenAIClientError

        def _broken(*, input_text: str, instructions: str, **_):
            raise OpenAIClientError("API 调用失败。")

        result = generate_ai_summary(
            _payload_with_sources(),
            enable_ai_summary=True,
            llm_generate=_broken,
        )
        self.assertEqual(result["status"], "llm_error")
        self.assertEqual(result["summary"], "")


class HappyPathTests(unittest.TestCase):
    def test_ai_summary_returns_ok_with_attributed_sentences(self) -> None:
        from services.ai_summary import generate_ai_summary

        sentence = _safe_sentence()
        result = generate_ai_summary(
            _payload_with_sources(),
            enable_ai_summary=True,
            llm_generate=_llm_returns_json([sentence]),
        )
        self.assertEqual(result["status"], "ok")
        self.assertIn("明日最可能小幅上涨", result["summary"])
        self.assertEqual(len(result["sentences"]), 1)
        self.assertEqual(result["sentences"][0]["source_system"], "projection_result")
        self.assertGreater(len(result["source_attribution"]), 0)

    def test_no_forbidden_fields_in_output(self) -> None:
        from services.ai_summary import generate_ai_summary

        for path in (
            ("disabled",),
            ("enabled_ok",),
            ("enabled_refused",),
        ):
            if path == ("disabled",):
                result = generate_ai_summary(_payload_with_sources())
            elif path == ("enabled_ok",):
                result = generate_ai_summary(
                    _payload_with_sources(),
                    enable_ai_summary=True,
                    llm_generate=_llm_returns_json([_safe_sentence()]),
                )
            else:
                result = generate_ai_summary(
                    _payload_with_sources(),
                    enable_ai_summary=True,
                    llm_generate=_llm_returns_json(
                        [_safe_sentence(sentence="建议买入。")]
                    ),
                )
            for forbidden in _FORBIDDEN_OUTPUT_FIELDS:
                self.assertNotIn(forbidden, result, msg=f"{path} {forbidden}")


class NoMutationTests(unittest.TestCase):
    def test_does_not_mutate_payload(self) -> None:
        from services.ai_summary import generate_ai_summary

        payload = _payload_with_sources()
        snapshot = copy.deepcopy(payload)
        generate_ai_summary(
            payload,
            enable_ai_summary=True,
            llm_generate=_llm_returns_json([_safe_sentence()]),
        )
        self.assertEqual(payload, snapshot)


class StaticBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module_path = ROOT / "services" / "ai_summary.py"
        self.source = self.module_path.read_text(encoding="utf-8")
        self.tree = ast.parse(self.source)

    def test_module_does_not_write_back_to_three_systems_or_final_report(self) -> None:
        # No assignments like `payload["projection_result"][...] = ...`
        # or `final_report[...] = ...` from inside the module body.
        for forbidden in (
            'payload["projection_result"]',
            'payload["exclusion_result"]',
            'payload["confidence_result"]',
            'payload["final_report"]',
        ):
            self.assertNotIn(
                f"{forbidden} =",
                self.source,
                msg=f"ai_summary must not write back to {forbidden}",
            )

    def test_module_does_not_expose_bypass_flag(self) -> None:
        # Refuse to allow any "bypass" / "unsafe_mode" escape hatch
        for forbidden in ("bypass_postcheck", "unsafe_mode"):
            self.assertNotIn(forbidden, self.source)

    def test_module_imports_openai_client_only_for_text_generator_default(self) -> None:
        # generate_text is imported as the default text_generator. The
        # module must not import any other OpenAI surface that would
        # bypass the gate.
        forbidden = ("openai.ChatCompletion", "openai.Completion")
        for term in forbidden:
            self.assertNotIn(term, self.source)


class LegacyWrapperBackwardCompatTests(unittest.TestCase):
    """The 5 legacy public functions remain, but default to disabled (no LLM
    call, empty string return). UI and tool_router callers see "" instead
    of an LLM error/string."""

    def test_legacy_projection_summary_default_returns_empty_string(self) -> None:
        from services.ai_summary import build_projection_ai_summary

        out = build_projection_ai_summary({"final_bias": "bullish"})
        self.assertEqual(out, "")

    def test_legacy_review_summary_default_returns_empty_string(self) -> None:
        from services.ai_summary import build_review_ai_summary

        out = build_review_ai_summary({"prediction_id": "x"})
        self.assertEqual(out, "")

    def test_legacy_projection_explanation_default_returns_empty_string(self) -> None:
        from services.ai_summary import build_projection_ai_explanation

        out = build_projection_ai_explanation({"projection_report": {"direction": "偏多"}})
        self.assertEqual(out, "")

    def test_legacy_compare_explanation_default_returns_empty_string(self) -> None:
        from services.ai_summary import build_compare_ai_explanation

        out = build_compare_ai_explanation({"stats": {"total": 20}})
        self.assertEqual(out, "")

    def test_legacy_risk_explanation_default_returns_empty_string(self) -> None:
        from services.ai_summary import build_risk_ai_explanation

        out = build_risk_ai_explanation({"readable_summary": {"risk_reminders": []}})
        self.assertEqual(out, "")

    def test_legacy_default_does_not_call_llm(self) -> None:
        from services.ai_summary import build_projection_ai_summary

        calls: list = []

        def _spy(*, input_text: str, instructions: str, **_):
            calls.append((input_text, instructions))
            return "{}"

        out = build_projection_ai_summary(
            {"final_bias": "bullish"},
            text_generator=_spy,
        )
        self.assertEqual(out, "")
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
