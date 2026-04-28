"""Task 096 — wiring tests for the big-up contradiction card UI.

Two cases:

1. Wrapper plumbing — confirms `_render_contradiction_card(predict_result)`
   chains through `build_contradiction_card_payload` →
   `build_contradiction_card` → `render_contradiction_card`, with no
   direct `st.caption` call on the wrapper path and no input mutation.

2. Live wiring — confirms `_render_layer3_evidence(predict_result, …)`
   invokes both the existing PR-F exclusion-reliability wrapper and the
   new PR-G contradiction-card wrapper exactly once each, with the
   correct ordering relative to the surrounding expanders.

Avoids the full Streamlit AppTest harness; uses a minimal fake
streamlit + monkeypatch instead.
"""

from __future__ import annotations

import copy
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


def test_contradiction_card_wrapper_chains_payload_to_renderer(monkeypatch):
    """`_render_contradiction_card` must thread predict_result through
    the adapter, builder, and renderer in order, without mutating the
    input or emitting a direct ``st.caption`` on the wrapper path."""
    calls: dict[str, Any] = {}

    def fake_adapter(predict_result, *, prediction_date=None):
        calls["adapter_predict_result"] = predict_result
        calls["adapter_prediction_date"] = prediction_date
        return {"row": "synthetic"}

    def fake_builder(row):
        calls["builder_row"] = row
        return {"payload": "synthetic"}

    def fake_renderer(payload):
        calls["renderer_payload"] = payload

    fake_st = FakeStreamlit()
    monkeypatch.setattr(predict_tab, "st", fake_st)
    monkeypatch.setattr(predict_tab, "build_contradiction_card_payload", fake_adapter)
    monkeypatch.setattr(predict_tab, "build_contradiction_card", fake_builder)
    monkeypatch.setattr(predict_tab, "render_contradiction_card", fake_renderer)

    predict_result = {
        "analysis_date": "2026-04-25",
        "predicted_state": "震荡",
        "forced_excluded_states": "大涨|大跌",
    }
    snapshot = copy.deepcopy(predict_result)

    predict_tab._render_contradiction_card(predict_result)

    # Adapter received the original predict_result with prediction_date
    # extracted from analysis_date.
    assert calls["adapter_predict_result"] is predict_result, (
        "adapter must receive the original predict_result object"
    )
    assert calls["adapter_prediction_date"] == "2026-04-25", (
        "adapter must receive prediction_date extracted from analysis_date"
    )

    # Builder received the adapter's row.
    assert calls["builder_row"] == {"row": "synthetic"}, (
        "builder must receive the row produced by the adapter"
    )

    # Renderer received the builder's payload.
    assert calls["renderer_payload"] == {"payload": "synthetic"}, (
        "renderer must receive the payload produced by the builder"
    )

    # No direct st.caption on the wrapper path. The renderer (faked)
    # produces visible output; the wrapper itself does not.
    assert fake_st.caption_calls == [], (
        "wrapper must not call st.caption directly on the happy path"
    )

    # Input not mutated.
    assert predict_result == snapshot, (
        "_render_contradiction_card must not mutate predict_result"
    )


def test_layer3_evidence_invokes_both_wrappers_in_order(monkeypatch):
    """`_render_layer3_evidence` must invoke the PR-F wrapper and the
    new PR-G wrapper exactly once each, with the same predict_result
    object, in the order:
        AI summary expander → exclusion reliability wrapper →
        contradiction card wrapper → raw JSON debug expander.
    """
    events: list[str] = []
    received_for_pr_f: list[Any] = []
    received_for_pr_g: list[Any] = []

    def fake_pr_f(predict_result):
        received_for_pr_f.append(predict_result)
        events.append("pr_f_wrapper")

    def fake_pr_g(predict_result):
        received_for_pr_g.append(predict_result)
        events.append("pr_g_wrapper")

    class OrderingFakeSt(FakeStreamlit):
        def expander(self, label: str, **kwargs: Any) -> _Ctx:
            events.append(f"expander:{label}")
            return super().expander(label, **kwargs)

    fake_st = OrderingFakeSt()
    monkeypatch.setattr(predict_tab, "st", fake_st)
    monkeypatch.setattr(
        predict_tab,
        "_render_exclusion_reliability_review",
        fake_pr_f,
    )
    monkeypatch.setattr(
        predict_tab,
        "_render_contradiction_card",
        fake_pr_g,
    )

    predict_result = {
        "analysis_date": "2026-04-25",
        "predicted_state": "震荡",
        "forced_excluded_states": "大涨|大跌",
        "symbol": "AVGO",
    }

    predict_tab._render_layer3_evidence(predict_result, {}, None)

    # Each wrapper invoked exactly once.
    assert len(received_for_pr_f) == 1, (
        f"PR-F wrapper expected exactly one call, got {len(received_for_pr_f)}"
    )
    assert len(received_for_pr_g) == 1, (
        f"PR-G wrapper expected exactly one call, got {len(received_for_pr_g)}"
    )

    # Both received the same predict_result object (no copy, no mutation).
    assert received_for_pr_f[0] is predict_result
    assert received_for_pr_g[0] is predict_result

    # Ordering: AI expander → PR-F wrapper → PR-G wrapper → raw-JSON expander.
    ai_label = "expander:生成 AI 推演总结（可选）"
    raw_label = "expander:推演原始数据（调试用）"

    assert ai_label in events, f"AI summary expander must be opened: {events}"
    assert raw_label in events, f"raw-JSON expander must be opened: {events}"
    assert "pr_f_wrapper" in events, f"PR-F wrapper must be invoked: {events}"
    assert "pr_g_wrapper" in events, f"PR-G wrapper must be invoked: {events}"

    ai_idx = events.index(ai_label)
    pr_f_idx = events.index("pr_f_wrapper")
    pr_g_idx = events.index("pr_g_wrapper")
    raw_idx = events.index(raw_label)

    assert ai_idx < pr_f_idx < pr_g_idx < raw_idx, (
        f"expected order AI → PR-F → PR-G → raw-JSON, got {events}"
    )
