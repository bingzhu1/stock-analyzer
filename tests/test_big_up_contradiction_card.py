"""Task 085 — tests for the big-up exclusion contradiction card.

Spec §测试要求 1-9:

1.  No big-up exclusion → no warning (info card with "未触发").
2.  Big-up exclusion + no flags → high-confidence info card.
3.  macro_contradiction triggered → warning.
4.  earnings_post_window triggered → warning.
5.  sample_invalidation triggered → warning.
6.  Multiple flags (combo) → strong_warning (blocked).
7.  Missing fields → safe degradation, "数据有限" annotation.
8.  Chinese text contains key explanation.
9.  Card does NOT mutate the input row payload.

Tests intentionally avoid streamlit; we exercise the pure logic in
``services.big_up_contradiction_card`` so AppTest is not required.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.big_up_contradiction_card import (
    DEFAULT_CARD_CONFIG,
    FLAG_REASONS_CN,
    build_contradiction_card,
)
from ui import big_up_contradiction_card as ui_card


def _row(**kwargs) -> dict[str, Any]:
    """Default neutral v4-style row with all upstream fields populated."""
    base = {
        "forced_excluded_states": "大涨",
        "actual_state": "大涨",
        "AVGO_T_return": 0.0,
        "AVGO_T_structure": "open=平开|close=平收|path=平开震荡",
        "vol_ratio20": 1.0, "pos20": 50.0, "pos30": 50.0,
        "ret1": 0.0, "ret3": 0.0, "ret5": 0.0,
        "upper_shadow": 0.2, "lower_shadow": 0.2,
        "NVDA_T_return": 0.0, "SOXX_T_return": 0.0, "QQQ_T_return": 0.0,
        "peer_alignment": "neutral",
        "macro_contradicts_big_up_exclusion": False,
        "is_nq_short_term_oversold": False,
        "is_nq_rebound_candidate": False,
        "is_vix_spike": False,
        "macro_risk_support_score": 0,
        "is_market_rebound_candidate": False,
        "is_post_earnings_window": False,
        "is_pre_earnings_window": False,
        "is_near_earnings": False,
        "eps_surprise_last_quarter": None,
        "historical_sample_confidence": "high",
        "historical_match_count": 100,
        "historical_big_up_count": 5,
        "historical_big_up_rate": 0.05,
        "p_大涨": 0.05,
        "score_distribution_zeroed": False,
    }
    base.update(kwargs)
    return base


# ── §1: no big-up exclusion ─────────────────────────────────────────────────

def test_no_big_up_exclusion_shows_info_only():
    res = build_contradiction_card(_row(forced_excluded_states="大跌|小跌"))
    assert res["show_card"] is True       # we still show, just as info
    assert res["variant"] == "info"
    assert res["has_big_up_exclusion"] is False
    assert res["audit_decision"] == "not_excluded"
    assert "未触发大涨否定" in res["header_message"]


def test_no_big_up_exclusion_has_no_triggered_flags():
    res = build_contradiction_card(_row(forced_excluded_states=""))
    assert res["triggered_flags"] == []
    assert res["missing_fields"] == []


# ── §2: big-up + no flags → high-confidence info card ──────────────────────

def test_big_up_excluded_no_flags_shows_high_confidence_info():
    """Default neutral row: 大涨 excluded but no contradiction flag fires."""
    res = build_contradiction_card(_row())
    assert res["has_big_up_exclusion"] is True
    assert res["audit_decision"] == "hard_excluded"
    assert res["variant"] == "info"
    assert res["contradiction_level"] in ("无", "弱")
    assert res["exclusion_confidence"] == "高"
    assert "高置信" in res["header_message"]


# ── §3: macro_contradiction triggered ───────────────────────────────────────

def test_macro_contradiction_triggers_warning():
    """Single macro flag (low macro_score) → soft → warning."""
    res = build_contradiction_card(_row(
        macro_contradicts_big_up_exclusion=True,
        is_nq_rebound_candidate=True,
        macro_risk_support_score=2,    # below macro_score_for_block=4
    ))
    assert res["audit_decision"] == "soft_excluded"
    assert res["variant"] == "warning"
    assert "macro_contradiction_softening" in res["triggered_flags"]
    assert any("宏观反弹" in r for r in res["flag_reasons_cn"])


# ── §4: earnings_post_window triggered ─────────────────────────────────────

def test_earnings_post_window_triggers_warning():
    res = build_contradiction_card(_row(
        is_post_earnings_window=True,
        is_near_earnings=True,
    ))
    assert res["audit_decision"] == "soft_excluded"
    assert res["variant"] == "warning"
    assert "earnings_post_window_softening" in res["triggered_flags"]
    assert any("财报后窗口" in r for r in res["flag_reasons_cn"])


# ── §5: sample_invalidation triggered ──────────────────────────────────────

def test_sample_invalidation_triggers_warning():
    res = build_contradiction_card(_row(
        historical_sample_confidence="missing",
        historical_match_count=0,
        historical_big_up_count=None,
        historical_big_up_rate=None,
        p_大涨=0.001,
        score_distribution_zeroed=True,
    ))
    assert res["audit_decision"] == "soft_excluded"
    assert res["variant"] == "warning"
    assert "sample_confidence_invalidation" in res["triggered_flags"]
    assert any("历史样本" in r for r in res["flag_reasons_cn"])


# ── §6: multiple flags → strong warning (blocked) ──────────────────────────

def test_multiple_flags_strong_warning():
    res = build_contradiction_card(_row(
        macro_contradicts_big_up_exclusion=True,
        is_nq_rebound_candidate=True,
        is_post_earnings_window=True,
        is_near_earnings=True,
    ))
    assert res["audit_decision"] == "blocked_by_audit"
    assert res["variant"] == "strong_warning"
    assert res["contradiction_level"] == "强"
    assert res["exclusion_confidence"] == "极低"
    assert "强反证" in res["header_message"]
    assert "macro_contradiction_softening" in res["triggered_flags"]
    assert "earnings_post_window_softening" in res["triggered_flags"]


# ── §7: missing fields → safe degradation ─────────────────────────────────

def test_missing_all_three_core_fields_marks_data_limited():
    """Even when audit returns hard_excluded by default, missing data
    should be surfaced and the level marked 数据有限."""
    res = build_contradiction_card({
        "forced_excluded_states": "大涨",
        "actual_state": "大涨",
        # No macro / earnings / sample inputs at all.
    })
    assert res["has_big_up_exclusion"] is True
    assert len(res["missing_fields"]) == 3
    assert "数据有限" in res["contradiction_level"]
    assert "数据有限" in res["exclusion_confidence"]


def test_missing_one_field_shown_but_not_data_limited():
    """Spec: data_limited threshold is ≥2 missing core fields."""
    res = build_contradiction_card(_row(
        is_post_earnings_window=None,    # only this one missing
    ))
    # Two of three present (macro_contradicts + sample_confidence are set
    # via _row defaults), so data_limited (≥2 missing) does not trigger.
    assert len(res["missing_fields"]) == 1
    assert "数据有限" not in res["contradiction_level"]


def test_invalid_input_row_is_handled_safely():
    res = build_contradiction_card(None)
    assert res["show_card"] is True
    assert res["variant"] == "info"
    assert res["audit_decision"] == "not_excluded"
    assert "无法读取本次预测结果" in res["header_message"]


def test_strong_warning_downgraded_to_warning_when_data_limited():
    """If a hypothetical row would have produced strong_warning but key
    upstream data is missing, the variant should soften."""
    # Build a row that fires multi-flag combo BUT also lacks ≥2 core sources.
    # Tricky: macro_contradicts requires p_大涨 + macro features; if those are
    # absent, macro flag won't fire. So the realistic missing-data path is:
    # only one flag fires + 2 core sources missing → variant stays warning,
    # but level annotated 数据有限. We assert that path here.
    res = build_contradiction_card({
        "forced_excluded_states": "大涨",
        "actual_state": "大涨",
        "is_post_earnings_window": True,
        "is_near_earnings": True,
        # macro & sample missing
    })
    assert res["audit_decision"] == "soft_excluded"
    assert "数据有限" in res["contradiction_level"]
    assert res["variant"] in ("warning", "info")


# ── §8: chinese text contains key explanation ──────────────────────────────

def test_chinese_text_present_in_explanation():
    res = build_contradiction_card(_row(
        macro_contradicts_big_up_exclusion=True,
        is_nq_rebound_candidate=True,
        is_post_earnings_window=True,
        is_near_earnings=True,
    ))
    explanation = res["chinese_explanation"]
    # Must include some Chinese characters describing the action.
    assert any(c in explanation for c in ("反证", "排除项", "强反证", "低概率"))


def test_flag_reasons_use_chinese_when_known_flag():
    res = build_contradiction_card(_row(
        macro_contradicts_big_up_exclusion=True,
        is_nq_rebound_candidate=True,
    ))
    # Each known flag has a Chinese reason in FLAG_REASONS_CN.
    for line in res["flag_reasons_cn"]:
        # Either matches one of the known mappings or follows the
        # fallback pattern starting with "触发 ".
        if line.startswith("触发"):
            continue
        if line.startswith("反证抵消"):
            continue
        assert line in FLAG_REASONS_CN.values(), line


# ── §9: card does NOT mutate input row ────────────────────────────────────

def test_card_does_not_mutate_input_row():
    row = _row(macro_contradicts_big_up_exclusion=True, is_post_earnings_window=True)
    snapshot = copy.deepcopy(row)
    _ = build_contradiction_card(row)
    assert row == snapshot, "build_contradiction_card mutated its input row!"


# ── extra: variant only one of three valid values ──────────────────────────

def test_variant_is_always_info_warning_or_strong_warning():
    cases = [
        _row(),                                                                  # hard
        _row(is_post_earnings_window=True),                                       # soft
        _row(macro_contradicts_big_up_exclusion=True, is_post_earnings_window=True,
             is_nq_rebound_candidate=True, is_near_earnings=True),                # blocked
        _row(forced_excluded_states="大跌"),                                       # not excluded
    ]
    for row in cases:
        res = build_contradiction_card(row)
        assert res["variant"] in ("info", "warning", "strong_warning"), res["variant"]


# ── extra: counter flag downgrade flows through to UI ─────────────────────

def test_counter_flags_appended_to_reasons():
    """When counter flags fire (e.g., peer_drag), they should still be
    surfaced so the user sees both signs."""
    res = build_contradiction_card(_row(
        macro_contradicts_big_up_exclusion=True,
        is_nq_rebound_candidate=True,
        is_post_earnings_window=True,
        is_near_earnings=True,
        # Force two counters: peer_drag (unsupported + AVGO < peer_avg) +
        # exhaustion (pos20≥95 + upper_shadow≥0.5)
        peer_alignment="unsupported",
        AVGO_T_return=-0.5,
        NVDA_T_return=1.0, SOXX_T_return=1.0, QQQ_T_return=1.0,
        pos20=96.0, pos30=96.0, upper_shadow=0.55,
    ))
    # Counter downgrade should drop blocked → soft per v5 logic
    assert res["audit_decision"] == "soft_excluded"
    # Counter mention should appear
    assert any("反证抵消" in r for r in res["flag_reasons_cn"])


# ──────────────────────────────────────────────────────────────────────────
# Task 088 — cache health integration tests (spec §12 cases 14-19)
# ──────────────────────────────────────────────────────────────────────────


def _row_with_health(*, overall: str, **row_kwargs):
    """Helper: build a card row and graft a synthetic cache-health summary."""
    row = _row(**row_kwargs)
    row["data_health_summary"] = {
        "overall_status": overall,
        "data_limited": overall != "healthy",
        "warnings": [
            {"healthy": [], "stale": ["宏观 数据陈旧"],
             "partial": ["财报 数据缺失"], "missing": [
                 "宏观 数据缺失", "财报 数据缺失", "历史样本 数据缺失",
             ]}.get(overall, [])
        ][0],
        "prediction_date": "2026-04-25",
        "sources": {
            "macro": {"status": "stale" if overall == "stale" else
                       ("missing" if overall in ("partial", "missing") else "healthy"),
                       "latest_date": "2026-04-15", "age_days": 10,
                       "missing_files": ["VIX.csv"] if overall in ("partial", "missing") else [],
                       "stale_files": ["VIX.csv"] if overall == "stale" else [],
                       "note": "test"},
            "earnings": {"status": "healthy" if overall != "missing" else "missing",
                         "latest_date": "2026-06-03", "age_days": None,
                         "missing_files": [], "stale_files": [],
                         "note": "test"},
            "historical": {"status": "healthy" if overall != "missing" else "missing",
                            "latest_date": "2026-04-23", "age_days": 2,
                            "missing_files": [], "stale_files": [],
                            "note": "test"},
        },
    }
    return row


# §14: cache health is propagated into payload from contradiction_card_inputs.

def test_cache_health_summary_forwarded_into_card_payload():
    """When the row carries data_health_summary, the card payload echoes it."""
    row = _row_with_health(overall="healthy")
    res = build_contradiction_card(row)
    assert "data_health_summary" in res
    assert res["data_health_overall_status"] == "healthy"


# §15: stale → suffix "(数据陈旧)" on level + confidence

def test_card_appends_stale_suffix_when_cache_is_stale():
    row = _row_with_health(
        overall="stale",
        macro_contradicts_big_up_exclusion=True,
        is_nq_rebound_candidate=True,
    )
    res = build_contradiction_card(row)
    # contradiction_level / exclusion_confidence get the (数据陈旧) suffix
    assert "数据陈旧" in res["contradiction_level"]
    assert "数据陈旧" in res["exclusion_confidence"]


# §16: partial / missing → suffix "(数据有限)"

def test_card_appends_data_limited_suffix_when_cache_is_partial():
    row = _row_with_health(
        overall="partial",
        macro_contradicts_big_up_exclusion=True,
        is_nq_rebound_candidate=True,
    )
    res = build_contradiction_card(row)
    assert "数据有限" in res["contradiction_level"]
    assert "数据有限" in res["exclusion_confidence"]


def test_card_appends_data_limited_suffix_when_cache_is_missing():
    row = _row_with_health(overall="missing")
    res = build_contradiction_card(row)
    assert "数据有限" in res["contradiction_level"]
    assert "数据有限" in res["exclusion_confidence"]


# §17: strong_warning downgrades to warning when data_limited

def test_strong_warning_downgrades_when_cache_is_stale():
    """Engineer a strong_warning case AND inject stale cache health.

    Card should: keep audit decision, downgrade variant strong→warning,
    append explanation note.
    """
    row = _row_with_health(
        overall="stale",
        macro_contradicts_big_up_exclusion=True,
        is_nq_rebound_candidate=True,
        is_post_earnings_window=True,
        is_near_earnings=True,
    )
    res = build_contradiction_card(row)
    # The combo would normally produce blocked_by_audit + strong_warning.
    assert res["audit_decision"] == "blocked_by_audit"
    # But variant must be downgraded to warning when health says stale.
    assert res["variant"] == "warning"
    assert "降级" in res["chinese_explanation"]


def test_strong_warning_downgrades_when_cache_is_missing():
    row = _row_with_health(
        overall="missing",
        macro_contradicts_big_up_exclusion=True,
        is_nq_rebound_candidate=True,
        is_post_earnings_window=True,
        is_near_earnings=True,
    )
    res = build_contradiction_card(row)
    assert res["audit_decision"] == "blocked_by_audit"
    assert res["variant"] == "warning"


# §18: audit decision is NEVER changed by cache health

def test_cache_health_does_not_change_audit_decision():
    """For each cache health overall, audit decision must match the row's
    base contradiction inputs — health only tweaks UI variant/suffix."""
    base_kwargs = dict(
        macro_contradicts_big_up_exclusion=True,
        is_nq_rebound_candidate=True,
        is_post_earnings_window=True,
        is_near_earnings=True,
    )
    decisions = []
    for overall in ("healthy", "stale", "partial", "missing"):
        row = _row_with_health(overall=overall, **base_kwargs)
        res = build_contradiction_card(row)
        decisions.append(res["audit_decision"])
    # All four should produce the same audit decision (blocked_by_audit).
    assert len(set(decisions)) == 1, decisions
    assert decisions[0] == "blocked_by_audit"


# §19: predict_result fields are not mutated when cache health is appended

def test_card_does_not_mutate_input_row_with_cache_health():
    import copy
    row = _row_with_health(
        overall="stale",
        macro_contradicts_big_up_exclusion=True,
        is_post_earnings_window=True,
    )
    snapshot = copy.deepcopy(row)
    _ = build_contradiction_card(row)
    assert row == snapshot, "build_contradiction_card mutated row when cache health present"


# Extra: warnings list flows through to card payload for renderer

def test_cache_health_warnings_flow_to_payload():
    row = _row_with_health(overall="stale", macro_contradicts_big_up_exclusion=True)
    res = build_contradiction_card(row)
    # The full health summary is forwarded; cache_health_warnings exists.
    assert "cache_health_warnings" in res


# Extra: missing data_health_summary keeps backwards-compat behaviour

def test_no_data_health_summary_keeps_legacy_behaviour():
    row = _row()  # no data_health_summary at all
    res = build_contradiction_card(row)
    # Should not crash; should produce valid card output without health.
    assert res["data_health_overall_status"] == "unknown"
    # Legacy field-level data_limited (≥2 missing fields) still triggers suffix.
    # In neutral _row() all 3 fields present → no suffix.
    assert "数据陈旧" not in res["contradiction_level"]
    assert "数据有限" not in res["contradiction_level"]


def test_big_down_tail_warning_payload_is_added_to_card_payload():
    row = _row(
        forced_excluded_states="大涨|大跌",
        predicted_state="震荡",
        p_大跌=0.03,
        p_大涨=0.02,
        is_high_vol_regime=True,
    )
    res = build_contradiction_card(row)
    tail = res["big_down_tail_warning"]
    assert tail["had_big_down_exclusion"] is True
    assert tail["tail_compression_triggered"] is True
    assert tail["warning_level"] == "strong_warning"


def test_big_down_tail_warning_safely_degrades_when_fields_missing():
    row = _row(
        forced_excluded_states="大涨|大跌",
        predicted_state=None,
        p_大跌=None,
        p_大涨=0.02,
        contradiction_inputs_available=False,
    )
    res = build_contradiction_card(row)
    tail = res["big_down_tail_warning"]
    assert tail["data_limited"] is True
    assert "predicted_state" in tail["missing_fields"]
    assert "p_大跌" in tail["missing_fields"]
    assert tail["warning_level"] == "none"


class _FakeColumn:
    def __init__(self, parent):
        self._parent = parent

    def markdown(self, text: str, **kwargs) -> None:
        self._parent.markdown(text, **kwargs)


class _FakeStreamlit:
    def __init__(self) -> None:
        self.warning_calls: list[str] = []
        self.error_calls: list[str] = []
        self.info_calls: list[str] = []
        self.markdown_calls: list[str] = []
        self.write_calls: list[str] = []
        self.caption_calls: list[str] = []

    def warning(self, text: str, **kwargs) -> None:
        self.warning_calls.append(text)

    def error(self, text: str, **kwargs) -> None:
        self.error_calls.append(text)

    def info(self, text: str, **kwargs) -> None:
        self.info_calls.append(text)

    def markdown(self, text: str, **kwargs) -> None:
        self.markdown_calls.append(text)

    def write(self, text: str, **kwargs) -> None:
        self.write_calls.append(str(text))

    def caption(self, text: str, **kwargs) -> None:
        self.caption_calls.append(text)

    def columns(self, n: int):
        return [_FakeColumn(self) for _ in range(n)]


def test_ui_no_big_down_warning_when_no_big_down_exclusion(monkeypatch: pytest.MonkeyPatch):
    fake_st = _FakeStreamlit()
    monkeypatch.setattr(ui_card, "st", fake_st)
    payload = build_contradiction_card(
        _row(
            forced_excluded_states="大涨",
            predicted_state="小涨",
            p_大跌=0.20,
            p_大涨=0.05,
        )
    )
    ui_card.render_contradiction_card(payload)
    assert not any("大跌侧尾部风险" in text for text in fake_st.warning_calls)
    assert not any("强双尾收缩风险" in text for text in fake_st.error_calls)
    assert any("本次未触发大跌否定" in text for text in fake_st.caption_calls)


def test_ui_shows_big_down_warning_copy(monkeypatch: pytest.MonkeyPatch):
    fake_st = _FakeStreamlit()
    monkeypatch.setattr(ui_card, "st", fake_st)
    payload = build_contradiction_card(
        _row(
            forced_excluded_states="大涨|大跌",
            predicted_state="震荡",
            p_大跌=0.03,
            p_大涨=0.02,
        )
    )
    ui_card.render_contradiction_card(payload)
    assert any("检测到大跌侧尾部风险" in text for text in fake_st.warning_calls)


def test_ui_shows_big_down_strong_warning_copy(monkeypatch: pytest.MonkeyPatch):
    fake_st = _FakeStreamlit()
    monkeypatch.setattr(ui_card, "st", fake_st)
    payload = build_contradiction_card(
        _row(
            forced_excluded_states="大涨|大跌",
            predicted_state="震荡",
            p_大跌=0.03,
            p_大涨=0.02,
            is_high_vol_regime=True,
        )
    )
    ui_card.render_contradiction_card(payload)
    assert any("检测到强双尾收缩风险" in text for text in fake_st.error_calls)
