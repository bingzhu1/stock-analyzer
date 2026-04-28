from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui import predict_tab


def test_predict_tab_exclusion_reliability_wrapper_builds_and_renders(monkeypatch):
    calls: dict[str, object] = {}

    def fake_build(predict_result, *, prediction_date=None):
        calls["predict_result"] = dict(predict_result)
        calls["prediction_date"] = prediction_date
        return {"row": "ok"}

    def fake_render(row):
        calls["row"] = row

    class FakeStreamlit:
        def __init__(self):
            self.caption_calls: list[str] = []

        def caption(self, text: str) -> None:
            self.caption_calls.append(text)

    fake_st = FakeStreamlit()
    monkeypatch.setattr(predict_tab, "st", fake_st)
    monkeypatch.setattr(predict_tab, "build_contradiction_card_payload", fake_build)
    monkeypatch.setattr(predict_tab, "render_exclusion_reliability_review_for_row", fake_render)

    predict_result = {
        "analysis_date": "2026-04-25",
        "predicted_state": "震荡",
        "forced_excluded_states": "大涨|大跌",
    }
    predict_tab._render_exclusion_reliability_review(predict_result)

    assert calls["prediction_date"] == "2026-04-25"
    assert calls["row"] == {"row": "ok"}
    assert fake_st.caption_calls == []
