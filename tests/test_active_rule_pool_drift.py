"""Tests for services/active_rule_pool_drift.py — Task 063."""

from __future__ import annotations

import pytest

from services.active_rule_pool_drift import (
    build_active_rule_pool_drift_report,
    analyze_active_rule_pool_drift,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _overall_rule(
    rule_id: str = "r1",
    title: str = "Rule One",
    hit_count: int = 10,
    net_effect: float = 2.0,
    notes: str = "",
) -> dict:
    return {
        "rule_id": rule_id,
        "title": title,
        "hit_count": hit_count,
        "net_effect": net_effect,
        "notes": notes,
    }


def _recent_rule(
    rule_id: str = "r1",
    title: str = "Rule One",
    hit_count: int = 5,
    net_effect: float = 2.0,
) -> dict:
    return {"rule_id": rule_id, "title": title, "hit_count": hit_count, "net_effect": net_effect}


def _validation_report(rules: list) -> dict:
    return {
        "kind": "active_rule_pool_validation_report",
        "ready": True,
        "rule_effects": rules,
    }


# ---------------------------------------------------------------------------
# Test 1: happy path — shape complete
# ---------------------------------------------------------------------------

def test_happy_path_shape():
    overall = [
        _overall_rule("r1", net_effect=2.0, hit_count=10),
        _overall_rule("r2", net_effect=1.0, hit_count=8),
    ]
    recent = [
        _recent_rule("r1", hit_count=5, net_effect=2.0),
        _recent_rule("r2", hit_count=4, net_effect=0.0),
    ]
    report = build_active_rule_pool_drift_report(
        validation_report=_validation_report(overall),
        recent_rule_effects=recent,
    )

    required_keys = {
        "kind", "ready", "total_rules", "status_counts",
        "rules", "drift_candidates", "stable_rules", "improving_rules", "unclear_rules",
        "summary", "warnings",
    }
    assert required_keys.issubset(set(report.keys()))
    assert report["kind"] == "active_rule_pool_drift_report"
    assert report["ready"] is True
    assert report["total_rules"] == 2
    assert set(report["status_counts"].keys()) == {"stable", "drift_candidate", "improving", "unclear"}
    assert sum(report["status_counts"].values()) == 2
    assert isinstance(report["summary"], str) and len(report["summary"]) > 0
    assert isinstance(report["warnings"], list)
    # All rules must have required keys and non-empty rationale
    for r in report["rules"]:
        assert "drift_status" in r
        assert "drift_rationale" in r and r["drift_rationale"]
        assert "recommended_followup" in r


# ---------------------------------------------------------------------------
# Test 2: overall positive, recent negative → drift_candidate
# ---------------------------------------------------------------------------

def test_drift_candidate_recent_negative():
    overall = [_overall_rule("r1", net_effect=3.0, hit_count=10)]
    recent = [_recent_rule("r1", hit_count=5, net_effect=-1.0)]
    report = build_active_rule_pool_drift_report(
        validation_report=_validation_report(overall),
        recent_rule_effects=recent,
    )
    r = report["rules"][0]
    assert r["drift_status"] == "drift_candidate"
    assert r["drift_rationale"]
    assert r["recommended_followup"] in {"review_for_downgrade", "review_for_removal"}
    assert report["status_counts"]["drift_candidate"] == 1
    assert len(report["drift_candidates"]) == 1


def test_drift_candidate_recent_dropped():
    # overall=3.0, recent=1.5 → drop of 1.5 ≥ threshold → drift
    overall = [_overall_rule("r1", net_effect=3.0, hit_count=10)]
    recent = [_recent_rule("r1", hit_count=5, net_effect=1.5)]
    report = build_active_rule_pool_drift_report(
        validation_report=_validation_report(overall),
        recent_rule_effects=recent,
    )
    assert report["rules"][0]["drift_status"] == "drift_candidate"


# ---------------------------------------------------------------------------
# Test 3: overall and recent close → stable
# ---------------------------------------------------------------------------

def test_stable_when_recent_close():
    overall = [_overall_rule("r1", net_effect=2.0, hit_count=10)]
    recent = [_recent_rule("r1", hit_count=5, net_effect=2.0)]
    report = build_active_rule_pool_drift_report(
        validation_report=_validation_report(overall),
        recent_rule_effects=recent,
    )
    r = report["rules"][0]
    assert r["drift_status"] == "stable"
    assert r["recommended_followup"] == "retain"
    assert report["status_counts"]["stable"] == 1


# ---------------------------------------------------------------------------
# Test 4: recent clearly better → improving
# ---------------------------------------------------------------------------

def test_improving_when_recent_better():
    overall = [_overall_rule("r1", net_effect=1.0, hit_count=10)]
    recent = [_recent_rule("r1", hit_count=5, net_effect=3.0)]
    report = build_active_rule_pool_drift_report(
        validation_report=_validation_report(overall),
        recent_rule_effects=recent,
    )
    r = report["rules"][0]
    assert r["drift_status"] == "improving"
    assert r["recommended_followup"] == "keep_monitoring"
    assert report["status_counts"]["improving"] == 1


# ---------------------------------------------------------------------------
# Test 5: recent_hit_count too low → unclear
# ---------------------------------------------------------------------------

def test_unclear_when_recent_hit_count_low():
    overall = [_overall_rule("r1", net_effect=2.0, hit_count=10)]
    recent = [_recent_rule("r1", hit_count=2, net_effect=-5.0)]  # hit_count < 3
    report = build_active_rule_pool_drift_report(
        validation_report=_validation_report(overall),
        recent_rule_effects=recent,
    )
    r = report["rules"][0]
    assert r["drift_status"] == "unclear"
    assert r["recommended_followup"] == "keep_monitoring"


def test_unclear_when_no_recent_data():
    overall = [_overall_rule("r1", net_effect=2.0, hit_count=10)]
    # No recent_rule_effects provided at all
    report = build_active_rule_pool_drift_report(
        validation_report=_validation_report(overall),
        recent_rule_effects=None,
    )
    r = report["rules"][0]
    assert r["drift_status"] == "unclear"
    assert r["drift_rationale"]


# ---------------------------------------------------------------------------
# Test 6: drift_candidate followup logic
# ---------------------------------------------------------------------------

def test_drift_candidate_review_for_removal():
    # recent_net_effect < -1.0 → review_for_removal
    overall = [_overall_rule("r1", net_effect=4.0, hit_count=10)]
    recent = [_recent_rule("r1", hit_count=5, net_effect=-2.0)]
    report = build_active_rule_pool_drift_report(
        validation_report=_validation_report(overall),
        recent_rule_effects=recent,
    )
    assert report["rules"][0]["recommended_followup"] == "review_for_removal"


def test_drift_candidate_review_for_downgrade():
    # recent dropped but still ≥ -1.0 → review_for_downgrade
    overall = [_overall_rule("r1", net_effect=4.0, hit_count=10)]
    recent = [_recent_rule("r1", hit_count=5, net_effect=0.0)]
    report = build_active_rule_pool_drift_report(
        validation_report=_validation_report(overall),
        recent_rule_effects=recent,
    )
    assert report["rules"][0]["recommended_followup"] == "review_for_downgrade"


def test_stable_followup_is_retain():
    overall = [_overall_rule("r1", net_effect=2.0)]
    recent = [_recent_rule("r1", hit_count=5, net_effect=2.5)]
    report = build_active_rule_pool_drift_report(
        validation_report=_validation_report(overall),
        recent_rule_effects=recent,
    )
    assert report["rules"][0]["recommended_followup"] == "retain"


def test_unclear_followup_is_keep_monitoring():
    overall = [_overall_rule("r1", net_effect=2.0)]
    report = build_active_rule_pool_drift_report(
        validation_report=_validation_report(overall),
        recent_rule_effects=None,
    )
    assert report["rules"][0]["recommended_followup"] == "keep_monitoring"


# ---------------------------------------------------------------------------
# Test 8: validation_report missing → ready=False, warnings non-empty
# ---------------------------------------------------------------------------

def test_missing_validation_report():
    report = build_active_rule_pool_drift_report(validation_report=None)
    assert report["kind"] == "active_rule_pool_drift_report"
    assert report["ready"] is False
    assert len(report["warnings"]) > 0
    assert report["total_rules"] == 0
    assert isinstance(report["summary"], str)


# ---------------------------------------------------------------------------
# Test 9: empty rule_effects → counts all 0, summary readable
# ---------------------------------------------------------------------------

def test_empty_rule_effects():
    report = build_active_rule_pool_drift_report(
        validation_report=_validation_report([])
    )
    assert report["ready"] is True
    assert report["total_rules"] == 0
    assert all(v == 0 for v in report["status_counts"].values())
    assert isinstance(report["summary"], str) and len(report["summary"]) > 0


# ---------------------------------------------------------------------------
# Test 10: malformed rule → no crash, not drift_candidate
# ---------------------------------------------------------------------------

def test_malformed_rule_no_crash():
    malformed = {"rule_id": "r_bad"}  # missing hit_count, net_effect
    recent = [_recent_rule("r_bad", hit_count=5, net_effect=-3.0)]
    report = build_active_rule_pool_drift_report(
        validation_report=_validation_report([malformed]),
        recent_rule_effects=recent,
    )
    assert report["ready"] is True
    assert report["total_rules"] == 1
    r = report["rules"][0]
    # overall_net_effect defaults to 0.0 — not > 0 — so cannot be drift_candidate
    assert r["drift_status"] != "drift_candidate"
    assert r["drift_rationale"]


# ---------------------------------------------------------------------------
# Test 11: sublists and status_counts consistency
# ---------------------------------------------------------------------------

def test_sublists_and_counts_consistent():
    overall = [
        _overall_rule("r1", net_effect=3.0, hit_count=10),  # → drift
        _overall_rule("r2", net_effect=2.0, hit_count=8),   # → stable
        _overall_rule("r3", net_effect=1.0, hit_count=6),   # → improving
        _overall_rule("r4", net_effect=1.5, hit_count=7),   # → unclear (no recent)
    ]
    recent = [
        _recent_rule("r1", hit_count=5, net_effect=-1.0),   # drift
        _recent_rule("r2", hit_count=4, net_effect=2.0),    # stable
        _recent_rule("r3", hit_count=3, net_effect=2.5),    # improving (1.5 gain)
        # r4 has no recent entry
    ]
    report = build_active_rule_pool_drift_report(
        validation_report=_validation_report(overall),
        recent_rule_effects=recent,
    )

    sc = report["status_counts"]
    assert sc["drift_candidate"] == len(report["drift_candidates"])
    assert sc["stable"] == len(report["stable_rules"])
    assert sc["improving"] == len(report["improving_rules"])
    assert sc["unclear"] == len(report["unclear_rules"])
    assert sum(sc.values()) == report["total_rules"] == 4
    assert "drift_candidate" in report["summary"] or "drift" in report["summary"]


# ---------------------------------------------------------------------------
# Alias test
# ---------------------------------------------------------------------------

def test_alias_function():
    overall = [_overall_rule("r1")]
    r1 = build_active_rule_pool_drift_report(
        validation_report=_validation_report(overall)
    )
    r2 = analyze_active_rule_pool_drift(
        validation_report=_validation_report(overall)
    )
    assert r1["kind"] == r2["kind"]
    assert r1["total_rules"] == r2["total_rules"]
    assert r1["status_counts"] == r2["status_counts"]
