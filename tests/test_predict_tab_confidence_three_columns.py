"""Task 103 — three-column confidence output for the predict tab.

Verifies that ``_render_confidence_three_columns`` renders three labeled
columns (A 推演置信度 / B 否定置信度 / C 综合使用建议), separates
projection-side and negative-side confidence, derives the correct usage
suggestion for the four spec'd cases, and degrades gracefully when
``projection_three_systems`` is absent.

Mirrors the fake-streamlit / monkeypatch pattern used by
test_predict_tab_contradiction_card_wiring.py — does not invoke the
full Streamlit AppTest harness.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui import predict_tab


class _Ctx:
    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class FakeStreamlit:
    def __init__(self) -> None:
        self.markdown_calls: list[str] = []
        self.caption_calls: list[str] = []
        self.column_calls: list[int] = []

    def markdown(self, text: str, **_: Any) -> None:
        self.markdown_calls.append(text)

    def caption(self, text: str, **_: Any) -> None:
        self.caption_calls.append(text)

    def columns(self, spec: Any, **_: Any) -> list[_Ctx]:
        n = len(spec) if isinstance(spec, (list, tuple)) else int(spec)
        self.column_calls.append(n)
        return [_Ctx() for _ in range(n)]


def _all_text(fake: FakeStreamlit) -> str:
    return "\n".join(fake.markdown_calls + fake.caption_calls)


def _evaluator(
    *,
    projection_level: str,
    projection_score: float | None,
    negative_level: str,
    negative_score: float | None,
    overall_level: str,
) -> dict[str, Any]:
    return {
        "negative_system_confidence": {
            "score": negative_score,
            "level": negative_level,
            "reasoning": [],
            "risks": [],
        },
        "projection_system_confidence": {
            "score": projection_score,
            "level": projection_level,
            "reasoning": [],
            "risks": [],
        },
        "overall_confidence": {
            "score": None,
            "level": overall_level,
            "reasoning": [],
        },
        "conflicts": [],
        "reliability_warnings": [],
    }


def _three_systems_payload(**eval_kwargs: Any) -> dict[str, Any]:
    return {
        "negative_system": {
            "excluded_states": ["大涨"],
            "strength": "high",
        },
        "record_02_projection_system": {
            "final_direction": "偏多",
            "five_state_top1": "震荡",
            "historical_sample_summary": "近 30 日匹配 12 条历史样本。",
        },
        "confidence_evaluator": _evaluator(**eval_kwargs),
    }


def test_three_columns_render_three_labeled_sections(monkeypatch):
    """A / B / C headers and the section title must all appear; columns(3)
    must be requested exactly once."""
    fake_st = FakeStreamlit()
    monkeypatch.setattr(predict_tab, "st", fake_st)

    predict_result = {
        "final_bias": "bullish",
        "final_confidence": "medium",
        "projection_three_systems": _three_systems_payload(
            projection_level="medium",
            projection_score=0.6,
            negative_level="high",
            negative_score=0.9,
            overall_level="medium",
        ),
    }

    predict_tab._render_confidence_three_columns(predict_result)

    text = _all_text(fake_st)
    assert "置信度评估（三栏）" in text, "section title must be rendered"
    assert "A · 推演置信度" in text, "column A header must be rendered"
    assert "B · 否定置信度" in text, "column B header must be rendered"
    assert "C · 综合使用建议" in text, "column C header must be rendered"
    assert fake_st.column_calls == [3], (
        f"expected exactly one st.columns(3) call, got {fake_st.column_calls}"
    )


def test_projection_and_negative_levels_render_separately(monkeypatch):
    """Projection-side and negative-side confidence values must be
    presented independently — not collapsed into a single blended line."""
    fake_st = FakeStreamlit()
    monkeypatch.setattr(predict_tab, "st", fake_st)

    predict_result = {
        "projection_three_systems": _three_systems_payload(
            projection_level="medium",
            projection_score=0.6,
            negative_level="high",
            negative_score=0.9,
            overall_level="medium",
        ),
    }

    predict_tab._render_confidence_three_columns(predict_result)

    md = "\n".join(fake_st.markdown_calls)
    captions = "\n".join(fake_st.caption_calls)

    # Projection level shows 中, negative level shows 高 — distinct values.
    assert md.count("等级：**中**") >= 1, "projection level (中) must appear"
    assert md.count("等级：**高**") >= 1, "negative level (高) must appear"

    # Both scores must be visible and distinct.
    assert "分数：0.60" in captions, "projection score 0.60 must appear"
    assert "分数：0.90" in captions, "negative score 0.90 must appear"

    # Excluded state from negative_system must surface in column B.
    assert "已排除状态：大涨" in captions

    # Column A specific fields.
    assert "final_direction：偏多" in captions
    assert "five_state_top1：震荡" in captions
    assert "历史样本：近 30 日匹配 12 条历史样本。" in captions


def test_missing_projection_three_systems_degrades_gracefully(monkeypatch):
    """When projection_three_systems is absent, the helper must still
    render three columns with safe placeholders and not raise."""
    fake_st = FakeStreamlit()
    monkeypatch.setattr(predict_tab, "st", fake_st)

    predict_result = {
        "final_bias": "neutral",
        "final_confidence": "low",
    }

    predict_tab._render_confidence_three_columns(predict_result)

    text = _all_text(fake_st)
    assert "A · 推演置信度" in text
    assert "B · 否定置信度" in text
    assert "C · 综合使用建议" in text

    # Negative side has no data → placeholder, no crash.
    assert "已排除状态：—" in text
    assert "触发规则：—" in text

    # Projection level should fall back to the legacy final_confidence (低).
    md = "\n".join(fake_st.markdown_calls)
    assert "等级：**低**" in md, "projection fallback should reflect final_confidence=low"

    # Column C suggestion for proj=low + neg=unknown → '只观察，等待确认。'
    assert "只观察，等待确认。" in text


def test_none_predict_result_does_not_raise(monkeypatch):
    """Defensive: passing None must not raise and must still render
    three columns with placeholders."""
    fake_st = FakeStreamlit()
    monkeypatch.setattr(predict_tab, "st", fake_st)

    predict_tab._render_confidence_three_columns(None)

    text = _all_text(fake_st)
    assert "A · 推演置信度" in text
    assert "B · 否定置信度" in text
    assert "C · 综合使用建议" in text


def test_usage_suggestion_high_high_strong_structure():
    s = predict_tab._derive_confidence_usage_suggestion("high", "high")
    assert s == "可作为较强结构参考，仍需价格确认。"


def test_usage_suggestion_high_low_direction_with_caveat():
    s = predict_tab._derive_confidence_usage_suggestion("high", "low")
    assert s == "方向可参考，但排除信号需复核。"
    # unknown counts as weak per spec ("弱/unknown")
    s2 = predict_tab._derive_confidence_usage_suggestion("high", "unknown")
    assert s2 == "方向可参考，但排除信号需复核。"


def test_usage_suggestion_low_high_exclusion_only():
    s = predict_tab._derive_confidence_usage_suggestion("low", "high")
    assert s == "优先作为排除法参考，不适合重仓押方向。"
    s2 = predict_tab._derive_confidence_usage_suggestion("unknown", "high")
    assert s2 == "优先作为排除法参考，不适合重仓押方向。"


def test_usage_suggestion_both_weak_only_observe():
    s = predict_tab._derive_confidence_usage_suggestion("low", "low")
    assert s == "只观察，等待确认。"
    s2 = predict_tab._derive_confidence_usage_suggestion("unknown", "unknown")
    assert s2 == "只观察，等待确认。"


def test_usage_suggestion_medium_falls_back_to_auxiliary_text():
    """Medium / mixed combinations are not in the four named cases —
    helper must return a conservative auxiliary suggestion rather than
    silently misclassify them."""
    s = predict_tab._derive_confidence_usage_suggestion("medium", "medium")
    assert s == "仅作辅助参考，等待价格信号或样本质量提升后再行动。"
    s2 = predict_tab._derive_confidence_usage_suggestion("medium", "high")
    assert s2 == "仅作辅助参考，等待价格信号或样本质量提升后再行动。"


def test_high_volatility_caution_always_rendered(monkeypatch):
    """Per task spec, the column C block must include a high-volatility
    caution line independent of the level branch chosen."""
    fake_st = FakeStreamlit()
    monkeypatch.setattr(predict_tab, "st", fake_st)

    predict_result = {
        "projection_three_systems": _three_systems_payload(
            projection_level="high",
            projection_score=0.9,
            negative_level="high",
            negative_score=0.9,
            overall_level="high",
        ),
    }
    predict_tab._render_confidence_three_columns(predict_result)

    captions = "\n".join(fake_st.caption_calls)
    assert "若处于高波动环境，尤其谨慎使用「否定大跌」。" in captions


def test_layer2_calls_three_column_helper(monkeypatch):
    """`_render_layer2_conclusion` must invoke the new three-column
    helper exactly once with the predict_result it was passed."""
    captured: dict[str, Any] = {}

    def fake_helper(predict_result):
        captured["predict_result"] = predict_result
        captured["count"] = captured.get("count", 0) + 1

    fake_st = FakeStreamlit()
    monkeypatch.setattr(predict_tab, "st", fake_st)
    monkeypatch.setattr(
        predict_tab,
        "_render_confidence_three_columns",
        fake_helper,
    )

    predict_result = {
        "final_bias": "bullish",
        "final_confidence": "medium",
        "prediction_summary": "测试用 baseline summary",
    }
    predict_tab._render_layer2_conclusion(predict_result, scan_result=None)

    assert captured.get("count") == 1, (
        f"three-column helper expected exactly one call, got {captured.get('count')}"
    )
    assert captured["predict_result"] is predict_result, (
        "helper must receive the same predict_result reference"
    )
