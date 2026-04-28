"""Task 094 — live-wiring test for the exclusion-reliability review.

Verifies that the live predict-tab layer-3 evidence section invokes
``predict_tab._render_exclusion_reliability_review(predict_result)``
exactly once with the same ``predict_result`` that was passed into
``_render_layer3_evidence``.

Avoids the full Streamlit AppTest harness; uses a minimal fake
streamlit + monkeypatch instead, so the test is fast and deterministic.
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
    """Minimal context manager usable for ``with`` blocks."""

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class FakeStreamlit:
    def __init__(self) -> None:
        self.markdown_calls: list[str] = []
        self.caption_calls: list[str] = []
        self.write_calls: list[str] = []
        self.json_calls: list[Any] = []
        self.expander_labels: list[str] = []
        self.button_calls: list[tuple[Any, ...]] = []
        self.session_state: dict[str, Any] = {}

    def markdown(self, text: str, **_: Any) -> None:
        self.markdown_calls.append(text)

    def caption(self, text: str, **_: Any) -> None:
        self.caption_calls.append(text)

    def write(self, text: Any, **_: Any) -> None:
        self.write_calls.append(str(text))

    def json(self, obj: Any, **_: Any) -> None:
        self.json_calls.append(obj)

    def button(self, *args: Any, **_: Any) -> bool:
        self.button_calls.append(args)
        return False

    def expander(self, label: str, **_: Any) -> _Ctx:
        self.expander_labels.append(label)
        return _Ctx()

    def columns(self, count: int) -> list[_Ctx]:
        return [_Ctx() for _ in range(count)]


def test_layer3_evidence_invokes_exclusion_reliability_review_once(monkeypatch):
    received: list[Any] = []

    def fake_wrapper(predict_result):
        received.append(predict_result)

    fake_st = FakeStreamlit()
    monkeypatch.setattr(predict_tab, "st", fake_st)
    monkeypatch.setattr(
        predict_tab,
        "_render_exclusion_reliability_review",
        fake_wrapper,
    )

    predict_result = {
        "analysis_date": "2026-04-25",
        "predicted_state": "震荡",
        "forced_excluded_states": "大涨|大跌",
        "symbol": "AVGO",
    }
    scan_result = {
        "scan_bias": "neutral",
        "scan_confidence": "medium",
        "avgo_gap_state": "flat",
        "avgo_intraday_state": "range",
        "confirmation_state": "mixed",
        "historical_match_summary": {
            "exact_match_count": 3,
            "near_match_count": 5,
            "dominant_historical_outcome": "neutral",
        },
    }

    predict_tab._render_layer3_evidence(predict_result, scan_result, None)

    assert len(received) == 1, "wrapper should be invoked exactly once"
    assert received[0] is predict_result, (
        "wrapper should receive the same predict_result object passed into "
        "_render_layer3_evidence (no mutation, no copy)"
    )
    assert "生成 AI 推演总结（可选）" in fake_st.expander_labels, (
        "AI summary expander must still be rendered before the wrapper call"
    )
    assert "推演原始数据（调试用）" in fake_st.expander_labels, (
        "raw-JSON debug expander must still be rendered after the wrapper call"
    )


def test_wrapper_call_sits_between_ai_expander_and_raw_json_expander(monkeypatch):
    """Confirm ordering: AI summary expander → wrapper → raw-JSON expander."""
    events: list[str] = []

    def fake_wrapper(predict_result):
        events.append("wrapper")

    class OrderingFakeSt(FakeStreamlit):
        def expander(self, label: str, **kwargs: Any) -> _Ctx:
            events.append(f"expander:{label}")
            return super().expander(label, **kwargs)

    fake_st = OrderingFakeSt()
    monkeypatch.setattr(predict_tab, "st", fake_st)
    monkeypatch.setattr(
        predict_tab,
        "_render_exclusion_reliability_review",
        fake_wrapper,
    )

    predict_tab._render_layer3_evidence({"symbol": "AVGO"}, {}, None)

    ai_idx = events.index("expander:生成 AI 推演总结（可选）")
    raw_idx = events.index("expander:推演原始数据（调试用）")
    wrapper_idx = events.index("wrapper")

    assert ai_idx < wrapper_idx < raw_idx, (
        f"expected order AI-expander → wrapper → raw-JSON-expander, "
        f"got {events[ai_idx:raw_idx + 1]}"
    )
