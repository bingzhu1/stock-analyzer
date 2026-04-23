"""Tests for services/active_rule_pool_promotion.py — Task 061."""

from __future__ import annotations

import pytest

from services.active_rule_pool_promotion import (
    build_active_rule_pool_promotion_report,
    analyze_active_rule_pool_promotion,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_rule(
    rule_id: str = "rule_001",
    title: str = "Test Rule",
    category: str = "momentum",
    calibration_decision: str = "retain",
    hit_count: int = 8,
    improved_case_count: int = 5,
    worsened_case_count: int = 2,
    net_effect: float = 1.5,
    notes: str = "",
    **kwargs,
) -> dict:
    rule = {
        "rule_id": rule_id,
        "title": title,
        "category": category,
        "calibration_decision": calibration_decision,
        "hit_count": hit_count,
        "improved_case_count": improved_case_count,
        "worsened_case_count": worsened_case_count,
        "net_effect": net_effect,
        "notes": notes,
    }
    rule.update(kwargs)
    return rule


def _make_calibration_report(rules: list) -> dict:
    return {
        "kind": "active_rule_pool_calibration_report",
        "ready": True,
        "rules": rules,
    }


# ---------------------------------------------------------------------------
# Test 1: happy path shape
# ---------------------------------------------------------------------------

def test_happy_path_shape():
    rules = [
        _make_rule(rule_id="r1", calibration_decision="retain", hit_count=6, net_effect=1.2, improved_case_count=4, worsened_case_count=1),
        _make_rule(rule_id="r2", calibration_decision="observe", hit_count=3, net_effect=0.1, improved_case_count=2, worsened_case_count=1),
        _make_rule(rule_id="r3", calibration_decision="downgrade", hit_count=5, net_effect=-0.5, improved_case_count=2, worsened_case_count=3),
        _make_rule(rule_id="r4", calibration_decision="remove_candidate", hit_count=7, net_effect=-2.0, improved_case_count=1, worsened_case_count=5),
    ]
    report = build_active_rule_pool_promotion_report(calibration_report=_make_calibration_report(rules))

    assert report["kind"] == "active_rule_pool_promotion_report"
    assert report["ready"] is True
    assert report["total_rules"] == 4
    assert "decision_counts" in report
    assert set(report["decision_counts"].keys()) == {"promote_candidate", "keep_active_observe", "hold_back", "do_not_promote"}
    assert sum(report["decision_counts"].values()) == 4
    assert "rules" in report
    assert len(report["rules"]) == 4
    assert "promote_candidates" in report
    assert "keep_active_observe_rules" in report
    assert "hold_back_rules" in report
    assert "do_not_promote_rules" in report
    assert isinstance(report["summary"], str) and len(report["summary"]) > 0
    assert isinstance(report["warnings"], list)

    # verify sublist counts match decision_counts
    assert len(report["promote_candidates"]) == report["decision_counts"]["promote_candidate"]
    assert len(report["keep_active_observe_rules"]) == report["decision_counts"]["keep_active_observe"]
    assert len(report["hold_back_rules"]) == report["decision_counts"]["hold_back"]
    assert len(report["do_not_promote_rules"]) == report["decision_counts"]["do_not_promote"]

    # All rules must have required keys
    required_keys = {
        "rule_id", "title", "category", "calibration_decision",
        "hit_count", "improved_case_count", "worsened_case_count", "net_effect",
        "promotion_decision", "promotion_rationale", "promotion_confidence", "notes",
    }
    for rule in report["rules"]:
        assert required_keys.issubset(set(rule.keys())), f"Missing keys in rule: {rule}"
        assert rule["promotion_rationale"], "promotion_rationale must be non-empty"


# ---------------------------------------------------------------------------
# Test 2: retain + strong signal → promote_candidate
# ---------------------------------------------------------------------------

def test_retain_strong_promotes():
    rule = _make_rule(
        rule_id="r1",
        calibration_decision="retain",
        hit_count=7,
        net_effect=2.0,
        improved_case_count=5,
        worsened_case_count=1,
    )
    report = build_active_rule_pool_promotion_report(calibration_report=_make_calibration_report([rule]))

    assert report["ready"] is True
    assert report["total_rules"] == 1
    assert report["decision_counts"]["promote_candidate"] == 1
    assert report["decision_counts"]["keep_active_observe"] == 0
    r = report["rules"][0]
    assert r["promotion_decision"] == "promote_candidate"
    assert r["promotion_rationale"]
    assert r["promotion_confidence"] in {"medium", "high"}


# ---------------------------------------------------------------------------
# Test 3: observe → keep_active_observe
# ---------------------------------------------------------------------------

def test_observe_keeps_active():
    rule = _make_rule(
        rule_id="r2",
        calibration_decision="observe",
        hit_count=3,
        net_effect=0.3,
        improved_case_count=2,
        worsened_case_count=1,
    )
    report = build_active_rule_pool_promotion_report(calibration_report=_make_calibration_report([rule]))

    assert report["ready"] is True
    assert report["decision_counts"]["keep_active_observe"] == 1
    r = report["rules"][0]
    assert r["promotion_decision"] == "keep_active_observe"
    assert r["promotion_rationale"]
    assert r["promotion_confidence"] == "low"


# ---------------------------------------------------------------------------
# Test 4: retain but hit_count < 5 → keep_active_observe
# ---------------------------------------------------------------------------

def test_retain_weak_keeps_active():
    rule = _make_rule(
        rule_id="r3",
        calibration_decision="retain",
        hit_count=3,
        net_effect=1.0,
        improved_case_count=2,
        worsened_case_count=1,
    )
    report = build_active_rule_pool_promotion_report(calibration_report=_make_calibration_report([rule]))

    assert report["ready"] is True
    assert report["decision_counts"]["keep_active_observe"] == 1
    r = report["rules"][0]
    assert r["promotion_decision"] == "keep_active_observe"
    assert r["promotion_rationale"]
    assert r["promotion_confidence"] == "low"


# ---------------------------------------------------------------------------
# Test 5: downgrade → hold_back
# ---------------------------------------------------------------------------

def test_downgrade_holds_back():
    rule = _make_rule(
        rule_id="r4",
        calibration_decision="downgrade",
        hit_count=5,
        net_effect=-0.3,
        improved_case_count=2,
        worsened_case_count=3,
    )
    report = build_active_rule_pool_promotion_report(calibration_report=_make_calibration_report([rule]))

    assert report["ready"] is True
    assert report["decision_counts"]["hold_back"] == 1
    r = report["rules"][0]
    assert r["promotion_decision"] == "hold_back"
    assert r["promotion_rationale"]
    assert r["promotion_confidence"] == "low"


# ---------------------------------------------------------------------------
# Test 6: recalibrate → hold_back
# ---------------------------------------------------------------------------

def test_recalibrate_holds_back():
    rule = _make_rule(
        rule_id="r5",
        calibration_decision="recalibrate",
        hit_count=6,
        net_effect=0.5,
        improved_case_count=4,
        worsened_case_count=2,
    )
    report = build_active_rule_pool_promotion_report(calibration_report=_make_calibration_report([rule]))

    assert report["ready"] is True
    assert report["decision_counts"]["hold_back"] == 1
    r = report["rules"][0]
    assert r["promotion_decision"] == "hold_back"
    assert r["promotion_rationale"]
    assert r["promotion_confidence"] == "low"


# ---------------------------------------------------------------------------
# Test 7: remove_candidate → do_not_promote
# ---------------------------------------------------------------------------

def test_remove_candidate_do_not_promote():
    rule = _make_rule(
        rule_id="r6",
        calibration_decision="remove_candidate",
        hit_count=8,
        net_effect=-3.0,
        improved_case_count=1,
        worsened_case_count=6,
    )
    report = build_active_rule_pool_promotion_report(calibration_report=_make_calibration_report([rule]))

    assert report["ready"] is True
    assert report["decision_counts"]["do_not_promote"] == 1
    r = report["rules"][0]
    assert r["promotion_decision"] == "do_not_promote"
    assert r["promotion_rationale"]
    # remove_candidate with hit_count>=5 → high confidence
    assert r["promotion_confidence"] == "high"


# ---------------------------------------------------------------------------
# Test 8: high confidence
# ---------------------------------------------------------------------------

def test_high_confidence():
    rule = _make_rule(
        rule_id="r7",
        calibration_decision="retain",
        hit_count=12,
        net_effect=2.5,
        improved_case_count=9,
        worsened_case_count=2,
    )
    report = build_active_rule_pool_promotion_report(calibration_report=_make_calibration_report([rule]))

    assert report["ready"] is True
    r = report["rules"][0]
    assert r["promotion_decision"] == "promote_candidate"
    assert r["promotion_confidence"] == "high"
    assert r["promotion_rationale"]


# ---------------------------------------------------------------------------
# Test 9: missing calibration_report → ready=False, warnings non-empty
# ---------------------------------------------------------------------------

def test_missing_calibration_report():
    report = build_active_rule_pool_promotion_report(calibration_report=None)

    assert report["kind"] == "active_rule_pool_promotion_report"
    assert report["ready"] is False
    assert len(report["warnings"]) > 0
    assert report["total_rules"] == 0
    assert report["rules"] == []
    assert report["promote_candidates"] == []
    assert isinstance(report["summary"], str)


# ---------------------------------------------------------------------------
# Test 10: empty rules list → total_rules=0, counts=0, readable summary
# ---------------------------------------------------------------------------

def test_empty_rules():
    report = build_active_rule_pool_promotion_report(
        calibration_report=_make_calibration_report([])
    )

    assert report["kind"] == "active_rule_pool_promotion_report"
    assert report["ready"] is True
    assert report["total_rules"] == 0
    assert all(v == 0 for v in report["decision_counts"].values())
    assert report["rules"] == []
    assert isinstance(report["summary"], str) and len(report["summary"]) > 0


# ---------------------------------------------------------------------------
# Test 11: malformed rule (missing fields) → no crash, not promoted
# ---------------------------------------------------------------------------

def test_malformed_rule_no_crash():
    # Rule with no hit_count, no net_effect — bare minimum
    malformed_rule = {
        "rule_id": "r_bad",
        "title": "Incomplete Rule",
        "calibration_decision": "retain",
        # hit_count and net_effect are intentionally absent
    }
    report = build_active_rule_pool_promotion_report(
        calibration_report=_make_calibration_report([malformed_rule])
    )

    assert report["ready"] is True
    assert report["total_rules"] == 1
    r = report["rules"][0]
    # Missing hit_count defaults to 0 (<5), so should NOT be promote_candidate
    assert r["promotion_decision"] != "promote_candidate"
    assert r["promotion_rationale"], "promotion_rationale must be non-empty"
    assert r["promotion_confidence"] in {"low", "medium", "high"}


# ---------------------------------------------------------------------------
# Alias test
# ---------------------------------------------------------------------------

def test_alias_function():
    rules = [_make_rule()]
    result1 = build_active_rule_pool_promotion_report(calibration_report=_make_calibration_report(rules))
    result2 = analyze_active_rule_pool_promotion(calibration_report=_make_calibration_report(rules))
    assert result1["kind"] == result2["kind"]
    assert result1["total_rules"] == result2["total_rules"]
    assert result1["decision_counts"] == result2["decision_counts"]
