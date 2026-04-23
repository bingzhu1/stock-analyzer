"""Tests for services/promotion_execution_bridge.py — Task 062."""

from __future__ import annotations

import pytest

from services.promotion_execution_bridge import (
    build_promotion_execution_bridge,
    export_promotion_execution_candidates,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_promotion_rule(
    rule_id: str = "rule_001",
    title: str = "Strong Rule",
    category: str = "momentum",
    promotion_decision: str = "promote_candidate",
    promotion_confidence: str = "high",
    promotion_rationale: str = "meets all criteria",
    hit_count: int = 10,
    net_effect: float = 2.0,
    severity: str = "medium",
    effect: str = "lower_confidence",
    message: str = "Rule message text",
    **kwargs,
) -> dict:
    rule = {
        "rule_id": rule_id,
        "title": title,
        "category": category,
        "promotion_decision": promotion_decision,
        "promotion_confidence": promotion_confidence,
        "promotion_rationale": promotion_rationale,
        "hit_count": hit_count,
        "net_effect": net_effect,
        "severity": severity,
        "effect": effect,
        "message": message,
    }
    rule.update(kwargs)
    return rule


def _make_promotion_report(rules: list) -> dict:
    return {
        "kind": "active_rule_pool_promotion_report",
        "ready": True,
        "rules": rules,
    }


# ---------------------------------------------------------------------------
# Test 1: happy path — shape complete
# ---------------------------------------------------------------------------

def test_happy_path_shape():
    rules = [
        _make_promotion_rule(rule_id="r1", promotion_decision="promote_candidate"),
        _make_promotion_rule(rule_id="r2", promotion_decision="keep_active_observe"),
        _make_promotion_rule(rule_id="r3", promotion_decision="hold_back"),
        _make_promotion_rule(rule_id="r4", promotion_decision="do_not_promote"),
    ]
    report = build_promotion_execution_bridge(
        promotion_report=_make_promotion_report(rules)
    )

    required_keys = {
        "kind", "ready", "bridge_name", "version_tag", "execution_enabled",
        "total_input_rules", "promotable_rule_count",
        "promotable_rules", "held_back_rules", "execution_bridge_rules",
        "summary", "warnings",
    }
    assert required_keys.issubset(set(report.keys()))
    assert report["kind"] == "promotion_execution_bridge"
    assert report["ready"] is True
    assert report["total_input_rules"] == 4
    assert report["promotable_rule_count"] == 1
    assert len(report["promotable_rules"]) == 1
    assert len(report["held_back_rules"]) == 3
    assert len(report["execution_bridge_rules"]) == 1
    assert isinstance(report["summary"], str) and len(report["summary"]) > 0
    assert isinstance(report["warnings"], list)


# ---------------------------------------------------------------------------
# Test 2: promote_candidate enters promotable_rules and execution_bridge_rules
# ---------------------------------------------------------------------------

def test_promote_candidate_enters_bridge():
    rule = _make_promotion_rule(
        rule_id="r1",
        title="Good Rule",
        promotion_decision="promote_candidate",
        promotion_confidence="high",
        severity="medium",
        effect="lower_confidence",
        message="Some message",
    )
    report = build_promotion_execution_bridge(
        promotion_report=_make_promotion_report([rule])
    )

    assert report["promotable_rule_count"] == 1
    p = report["promotable_rules"][0]
    assert p["promotion_decision"] == "promote_candidate"
    assert p["promotion_confidence"] == "high"
    assert p["title"] == "Good Rule"

    assert len(report["execution_bridge_rules"]) == 1
    br = report["execution_bridge_rules"][0]
    assert set(br.keys()) == {"rule_id", "title", "category", "severity", "message", "effect"}
    assert br["title"] == "Good Rule"
    assert br["severity"] == "medium"
    assert br["effect"] == "lower_confidence"

    assert len(report["held_back_rules"]) == 0


# ---------------------------------------------------------------------------
# Test 3: non-promote decisions do not enter bridge
# ---------------------------------------------------------------------------

def test_non_promote_decisions_held_back():
    rules = [
        _make_promotion_rule(rule_id="r1", promotion_decision="keep_active_observe"),
        _make_promotion_rule(rule_id="r2", promotion_decision="hold_back"),
        _make_promotion_rule(rule_id="r3", promotion_decision="do_not_promote"),
    ]
    report = build_promotion_execution_bridge(
        promotion_report=_make_promotion_report(rules)
    )

    assert report["promotable_rule_count"] == 0
    assert len(report["promotable_rules"]) == 0
    assert len(report["execution_bridge_rules"]) == 0
    assert len(report["held_back_rules"]) == 3
    for hb in report["held_back_rules"]:
        assert hb["reason"] == "not_promoted"
        assert "rule_id" in hb


# ---------------------------------------------------------------------------
# Test 4: held_back_rules list is correct
# ---------------------------------------------------------------------------

def test_held_back_rules_correct():
    rules = [
        _make_promotion_rule(rule_id="r1", promotion_decision="promote_candidate"),
        _make_promotion_rule(rule_id="r2", promotion_decision="hold_back"),
    ]
    report = build_promotion_execution_bridge(
        promotion_report=_make_promotion_report(rules)
    )

    assert len(report["held_back_rules"]) == 1
    assert report["held_back_rules"][0]["rule_id"] == "r2"
    assert report["held_back_rules"][0]["reason"] == "not_promoted"


# ---------------------------------------------------------------------------
# Test 5: deterministic rule_id across multiple calls
# ---------------------------------------------------------------------------

def test_deterministic_bridge_rule_id():
    rule = _make_promotion_rule(rule_id="r_stable", title="Stable Rule", promotion_decision="promote_candidate")
    report1 = build_promotion_execution_bridge(promotion_report=_make_promotion_report([rule]))
    report2 = build_promotion_execution_bridge(promotion_report=_make_promotion_report([rule]))

    id1 = report1["execution_bridge_rules"][0]["rule_id"]
    id2 = report2["execution_bridge_rules"][0]["rule_id"]
    assert id1 == id2
    # Stable upstream rule_id is passed through unchanged
    assert id1 == "r_stable"


def test_deterministic_bridge_rule_id_generated():
    # When rule_id is unknown, generated id must be stable
    rule = _make_promotion_rule(rule_id="unknown", title="No ID Rule", promotion_decision="promote_candidate")
    report1 = build_promotion_execution_bridge(promotion_report=_make_promotion_report([rule]))
    report2 = build_promotion_execution_bridge(promotion_report=_make_promotion_report([rule]))

    id1 = report1["execution_bridge_rules"][0]["rule_id"]
    id2 = report2["execution_bridge_rules"][0]["rule_id"]
    assert id1 == id2
    assert id1.startswith("peb-")


# ---------------------------------------------------------------------------
# Test 6: promotion_report missing → ready=False, warnings non-empty
# ---------------------------------------------------------------------------

def test_missing_promotion_report():
    report = build_promotion_execution_bridge(promotion_report=None)

    assert report["kind"] == "promotion_execution_bridge"
    assert report["ready"] is False
    assert len(report["warnings"]) > 0
    assert report["total_input_rules"] == 0
    assert report["promotable_rules"] == []
    assert report["execution_bridge_rules"] == []
    assert isinstance(report["summary"], str)


# ---------------------------------------------------------------------------
# Test 7: empty rules list → promotable_rule_count=0, summary readable
# ---------------------------------------------------------------------------

def test_empty_rules():
    report = build_promotion_execution_bridge(
        promotion_report=_make_promotion_report([])
    )

    assert report["ready"] is True
    assert report["total_input_rules"] == 0
    assert report["promotable_rule_count"] == 0
    assert report["promotable_rules"] == []
    assert report["execution_bridge_rules"] == []
    assert isinstance(report["summary"], str) and len(report["summary"]) > 0


# ---------------------------------------------------------------------------
# Test 8: promote_candidate with missing fields — no crash, conservative output
# ---------------------------------------------------------------------------

def test_malformed_promote_candidate_no_crash():
    malformed = {
        "rule_id": "r_bad",
        "promotion_decision": "promote_candidate",
        # title, hit_count, net_effect, severity, effect, message all absent
    }
    report = build_promotion_execution_bridge(
        promotion_report=_make_promotion_report([malformed])
    )

    assert report["ready"] is True
    assert report["promotable_rule_count"] == 1
    p = report["promotable_rules"][0]
    assert p["title"] == "unknown"
    assert p["hit_count"] == 0
    assert p["net_effect"] == 0.0
    assert p["severity"] == "unknown"
    assert p["effect"] == "unknown"
    assert p["message"] == "unknown"
    # execution_bridge_rules also generated
    assert len(report["execution_bridge_rules"]) == 1


# ---------------------------------------------------------------------------
# Test 9: execution_enabled reflects enable_execution_bridge parameter
# ---------------------------------------------------------------------------

def test_execution_gate_disabled():
    rules = [_make_promotion_rule(promotion_decision="promote_candidate")]
    report = build_promotion_execution_bridge(
        promotion_report=_make_promotion_report(rules),
        enable_execution_bridge=False,
    )
    assert report["execution_enabled"] is False
    # artifact still produced
    assert report["promotable_rule_count"] == 1
    assert len(report["execution_bridge_rules"]) == 1


def test_execution_gate_enabled():
    rules = [_make_promotion_rule(promotion_decision="promote_candidate")]
    report = build_promotion_execution_bridge(
        promotion_report=_make_promotion_report(rules),
        enable_execution_bridge=True,
    )
    assert report["execution_enabled"] is True
    # same artifact regardless
    assert report["promotable_rule_count"] == 1
    assert len(report["execution_bridge_rules"]) == 1


# ---------------------------------------------------------------------------
# Test 10: summary and consistency checks
# ---------------------------------------------------------------------------

def test_summary_and_consistency():
    rules = [
        _make_promotion_rule(rule_id="r1", promotion_decision="promote_candidate"),
        _make_promotion_rule(rule_id="r2", promotion_decision="promote_candidate"),
        _make_promotion_rule(rule_id="r3", promotion_decision="hold_back"),
    ]
    report = build_promotion_execution_bridge(
        promotion_report=_make_promotion_report(rules),
        bridge_name="test_bridge",
    )

    assert report["promotable_rule_count"] == len(report["promotable_rules"])
    assert report["promotable_rule_count"] == len(report["execution_bridge_rules"])
    assert len(report["held_back_rules"]) == 1
    assert report["total_input_rules"] == 3
    assert "test_bridge" in report["summary"]
    assert "2" in report["summary"]  # promotable count mentioned


# ---------------------------------------------------------------------------
# Alias test
# ---------------------------------------------------------------------------

def test_alias_function():
    rules = [_make_promotion_rule()]
    r1 = build_promotion_execution_bridge(promotion_report=_make_promotion_report(rules))
    r2 = export_promotion_execution_candidates(promotion_report=_make_promotion_report(rules))
    assert r1["kind"] == r2["kind"]
    assert r1["promotable_rule_count"] == r2["promotable_rule_count"]
    assert r1["execution_bridge_rules"] == r2["execution_bridge_rules"]
