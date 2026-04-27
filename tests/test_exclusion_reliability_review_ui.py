from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui import exclusion_reliability_review as ui_review


class _FakeContainer:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeStreamlit:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def markdown(self, text: str, **_: object) -> None:
        self.messages.append(text)

    def caption(self, text: str) -> None:
        self.messages.append(text)

    def write(self, text: object) -> None:
        self.messages.append(str(text))

    def container(self):
        return _FakeContainer()


def test_render_exclusion_reliability_review_outputs_summary_and_entries(monkeypatch):
    fake_st = FakeStreamlit()
    monkeypatch.setattr(ui_review, "st", fake_st)

    payload = {
        "has_exclusion_review": True,
        "summary_cn": "系统原先否定了“大涨”，但新补全证据不支持这个否定。",
        "review_items": [
            {
                "has_exclusion": True,
                "excluded_state": "大涨",
                "has_reliability_concern": True,
                "support_mix": "raw_and_technical",
                "strongest_tier_cn": "强证据",
                "display_summary_cn": "宏观环境更像反弹，不支持继续强排除大涨。",
                "taxonomy_entries": [
                    {
                        "display_tier_cn": "强证据",
                        "title_cn": "宏观反弹条件与“否定大涨”矛盾",
                        "display_cn": "宏观方向和原否定相反。",
                    }
                ],
                "unmapped_source_labels": [],
            }
        ],
    }

    ui_review.render_exclusion_reliability_review(payload)
    text = "\n".join(fake_st.messages)
    assert "否定可靠性解释" in text
    assert "support_mix = raw_and_technical" in text
    assert "宏观反弹条件与“否定大涨”矛盾" in text


def test_render_exclusion_reliability_review_for_supported_item_shows_neutral_copy(monkeypatch):
    fake_st = FakeStreamlit()
    monkeypatch.setattr(ui_review, "st", fake_st)

    payload = {
        "has_exclusion_review": True,
        "summary_cn": "当前没有命中已定义的可靠性下降解释。",
        "review_items": [
            {
                "has_exclusion": True,
                "excluded_state": "大跌",
                "has_reliability_concern": False,
                "support_mix": "supported",
                "strongest_tier_cn": "",
                "display_summary_cn": "系统原先否定了“大跌”，当前没有命中已定义的可靠性下降解释。",
                "taxonomy_entries": [],
                "unmapped_source_labels": [],
            }
        ],
    }

    ui_review.render_exclusion_reliability_review(payload)
    text = "\n".join(fake_st.messages)
    assert "无新增解释" in text
    assert "当前没有命中已定义的可靠性下降解释" in text
