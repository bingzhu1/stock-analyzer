# -*- coding: utf-8 -*-
"""
tests/test_projection_review_closed_loop.py

Focused tests for services/projection_review_closed_loop.py.

Covers:
1. happy_path — snapshot + actual → ready=True, direction_correct=True
2. wrong_direction — predicted up, actual down → error info populated
3. snapshot_missing — no snapshot → ready=False, warnings
4. actual_missing — snapshot present, no actual → ready=False
5. malformed_snapshot — broken fields → stable shape, error_layer=unknown
6. rule_candidate_generation — peer missing / historical insufficient produce candidates
"""

from __future__ import annotations

import pytest

from services.projection_review_closed_loop import (
    build_projection_review,
    save_projection_v2_snapshot,
    run_projection_review,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

def _make_snapshot(
    *,
    final_direction: str = "偏多",
    final_confidence: str = "high",
    peer_ready: bool = True,
    peer_adjustment_text: str = "",
    hist_summary: str = "样本充足",
) -> dict:
    return {
        "symbol": "AVGO",
        "analysis_date": "2026-04-20",
        "prediction_for_date": "2026-04-21",
        "final_direction": final_direction,
        "final_confidence": final_confidence,
        "risk_level": "medium",
        "preflight": {"kind": "projection_rule_preflight", "matched_rules": []},
        "primary_analysis": {
            "kind": "primary_20day_analysis",
            "direction": final_direction,
            "ready": True,
        },
        "peer_adjustment": {
            "kind": "peer_adjustment",
            "ready": peer_ready,
            "adjustment": peer_adjustment_text,
            "summary": peer_adjustment_text or "peer 数据正常",
        },
        "historical_probability": {
            "kind": "historical_probability",
            "ready": True,
            "summary": hist_summary,
            "sample_quality": "sufficient" if "充足" in hist_summary else "insufficient",
        },
        "final_decision": {
            "kind": "final_decision",
            "final_direction": final_direction,
            "final_confidence": final_confidence,
            "risk_level": "medium",
        },
        "trace": [],
    }


def _make_actual(*, close_change: float = 0.02) -> dict:
    actual_close = 200 * (1 + close_change)
    return {
        "actual_open": 200.0,
        "actual_close": actual_close,
        "actual_prev_close": 200.0,
        "actual_close_change": close_change,
        "open_label": "平开",
        "close_label": "收涨" if close_change > 0 else "收跌",
        "path_label": "平开走高" if close_change > 0 else "平开走低",
    }


# ─────────────────────────────────────────────────────────────────────────────
# 1. Happy path
# ─────────────────────────────────────────────────────────────────────────────

class TestHappyPath:
    def test_ready_true(self):
        snapshot = _make_snapshot(final_direction="偏多")
        actual = _make_actual(close_change=0.02)
        review = build_projection_review(snapshot, actual)
        assert review["ready"] is True

    def test_direction_correct_true(self):
        snapshot = _make_snapshot(final_direction="偏多")
        actual = _make_actual(close_change=0.02)
        review = build_projection_review(snapshot, actual)
        assert review["direction_correct"] is True

    def test_predicted_direction_mapped(self):
        snapshot = _make_snapshot(final_direction="偏多")
        actual = _make_actual(close_change=0.02)
        review = build_projection_review(snapshot, actual)
        assert review["predicted_direction"] == "up"

    def test_actual_direction_up(self):
        snapshot = _make_snapshot()
        actual = _make_actual(close_change=0.02)
        review = build_projection_review(snapshot, actual)
        assert review["actual_direction"] == "up"

    def test_kind_field(self):
        review = build_projection_review(_make_snapshot(), _make_actual())
        assert review["kind"] == "projection_review"

    def test_symbol_preserved(self):
        review = build_projection_review(_make_snapshot(), _make_actual())
        assert review["symbol"] == "AVGO"

    def test_no_warnings_on_clean_path(self):
        review = build_projection_review(_make_snapshot(), _make_actual())
        assert review["warnings"] == []

    def test_review_notes_nonempty(self):
        review = build_projection_review(_make_snapshot(), _make_actual())
        assert len(review["review_notes"]) >= 1

    def test_rule_candidates_empty_on_correct(self):
        review = build_projection_review(_make_snapshot(), _make_actual())
        assert review["rule_candidates"] == []

    def test_actual_summary_populated(self):
        review = build_projection_review(_make_snapshot(), _make_actual(close_change=0.02))
        assert review["actual_summary"]["actual_close_change"] == pytest.approx(0.02)

    def test_bearish_correct(self):
        snapshot = _make_snapshot(final_direction="偏空")
        actual = _make_actual(close_change=-0.02)
        review = build_projection_review(snapshot, actual)
        assert review["direction_correct"] is True
        assert review["predicted_direction"] == "down"
        assert review["actual_direction"] == "down"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Wrong direction
# ─────────────────────────────────────────────────────────────────────────────

class TestWrongDirection:
    def test_direction_correct_false(self):
        snapshot = _make_snapshot(final_direction="偏多")
        actual = _make_actual(close_change=-0.03)
        review = build_projection_review(snapshot, actual)
        assert review["direction_correct"] is False

    def test_ready_true_on_wrong_direction(self):
        snapshot = _make_snapshot(final_direction="偏多")
        actual = _make_actual(close_change=-0.03)
        review = build_projection_review(snapshot, actual)
        assert review["ready"] is True

    def test_error_category_populated(self):
        snapshot = _make_snapshot(final_direction="偏多")
        actual = _make_actual(close_change=-0.03)
        review = build_projection_review(snapshot, actual)
        assert review["error_category"] not in ("", None)

    def test_root_cause_summary_populated(self):
        snapshot = _make_snapshot(final_direction="偏多")
        actual = _make_actual(close_change=-0.03)
        review = build_projection_review(snapshot, actual)
        assert len(review["root_cause_summary"]) > 5

    def test_review_notes_include_error(self):
        snapshot = _make_snapshot(final_direction="偏多")
        actual = _make_actual(close_change=-0.03)
        review = build_projection_review(snapshot, actual)
        combined = " ".join(review["review_notes"])
        assert "错误" in combined or "不符" in combined or "wrong" in combined.lower()

    def test_primary_error_layer_when_primary_wrong(self):
        snapshot = _make_snapshot(final_direction="偏多")
        actual = _make_actual(close_change=-0.03)
        review = build_projection_review(snapshot, actual)
        assert review["error_layer"] == "primary"

    def test_high_confidence_wrong_generates_rule(self):
        snapshot = _make_snapshot(final_direction="偏多", final_confidence="high")
        actual = _make_actual(close_change=-0.03)
        review = build_projection_review(snapshot, actual)
        # Should have at least one rule candidate (high_confidence_wrong or primary)
        assert len(review["rule_candidates"]) >= 1

    def test_rule_candidate_has_correct_shape(self):
        snapshot = _make_snapshot(final_direction="偏多", final_confidence="high")
        actual = _make_actual(close_change=-0.03)
        review = build_projection_review(snapshot, actual)
        for rc in review["rule_candidates"]:
            assert "rule_id" in rc
            assert "title" in rc
            assert "category" in rc
            assert "severity" in rc
            assert "message" in rc


# ─────────────────────────────────────────────────────────────────────────────
# 3. Snapshot missing
# ─────────────────────────────────────────────────────────────────────────────

class TestSnapshotMissing:
    def test_ready_false(self):
        review = build_projection_review(None, _make_actual())
        assert review["ready"] is False

    def test_warnings_nonempty(self):
        review = build_projection_review(None, _make_actual())
        assert len(review["warnings"]) >= 1

    def test_shape_stable(self):
        review = build_projection_review(None, _make_actual())
        required = [
            "kind", "symbol", "analysis_date", "prediction_for_date", "ready",
            "predicted_direction", "actual_direction", "direction_correct",
            "predicted_confidence", "actual_summary", "error_layer", "error_category",
            "root_cause_summary", "review_notes", "rule_candidates", "warnings",
        ]
        for key in required:
            assert key in review, f"missing key: {key}"

    def test_no_exception(self):
        build_projection_review(None, None)  # must not raise

    def test_direction_correct_none(self):
        review = build_projection_review(None, _make_actual())
        assert review["direction_correct"] is None

    def test_error_layer_unknown(self):
        review = build_projection_review(None, _make_actual())
        assert review["error_layer"] == "unknown"


# ─────────────────────────────────────────────────────────────────────────────
# 4. Actual outcome missing
# ─────────────────────────────────────────────────────────────────────────────

class TestActualMissing:
    def test_ready_false(self):
        review = build_projection_review(_make_snapshot(), None)
        assert review["ready"] is False

    def test_warnings_mention_no_actual(self):
        review = build_projection_review(_make_snapshot(), None)
        combined = " ".join(review["warnings"])
        assert "实际结果" in combined or "actual" in combined.lower()

    def test_shape_stable(self):
        review = build_projection_review(_make_snapshot(), None)
        required = [
            "kind", "ready", "predicted_direction", "actual_direction",
            "direction_correct", "error_layer", "rule_candidates", "warnings",
        ]
        for key in required:
            assert key in review

    def test_direction_correct_none(self):
        review = build_projection_review(_make_snapshot(), None)
        assert review["direction_correct"] is None

    def test_actual_direction_unknown(self):
        review = build_projection_review(_make_snapshot(), None)
        assert review["actual_direction"] == "unknown"

    def test_review_notes_explain_no_actual(self):
        review = build_projection_review(_make_snapshot(), None)
        combined = " ".join(review["review_notes"])
        assert "实际结果" in combined or "无法" in combined


# ─────────────────────────────────────────────────────────────────────────────
# 5. Malformed snapshot
# ─────────────────────────────────────────────────────────────────────────────

class TestMalformedSnapshot:
    def test_empty_dict_does_not_raise(self):
        review = build_projection_review({}, _make_actual())
        assert isinstance(review, dict)

    def test_empty_dict_shape_stable(self):
        review = build_projection_review({}, _make_actual())
        required = [
            "kind", "ready", "predicted_direction", "actual_direction",
            "direction_correct", "error_layer", "rule_candidates", "warnings",
        ]
        for key in required:
            assert key in review

    def test_none_values_in_fields(self):
        snapshot = {
            "symbol": None,
            "analysis_date": None,
            "prediction_for_date": None,
            "final_direction": None,
            "final_confidence": None,
            "final_decision": None,
            "primary_analysis": None,
            "peer_adjustment": None,
            "historical_probability": None,
        }
        review = build_projection_review(snapshot, _make_actual())
        assert isinstance(review, dict)
        assert "error_layer" in review

    def test_unrecognized_direction_gives_unknown(self):
        snapshot = _make_snapshot()
        snapshot["final_direction"] = "GARBAGE_VALUE"
        review = build_projection_review(snapshot, _make_actual())
        assert review["predicted_direction"] == "unknown"
        assert len(review["warnings"]) >= 1

    def test_error_layer_unknown_when_cannot_detect(self):
        review = build_projection_review({}, _make_actual(close_change=0.02))
        assert review["error_layer"] == "unknown"

    def test_rule_candidates_list(self):
        review = build_projection_review({}, _make_actual())
        assert isinstance(review["rule_candidates"], list)


# ─────────────────────────────────────────────────────────────────────────────
# 6. Rule candidate generation
# ─────────────────────────────────────────────────────────────────────────────

class TestRuleCandidateGeneration:
    def test_peer_missing_generates_rule(self):
        snapshot = _make_snapshot(
            final_direction="偏多",
            final_confidence="high",
            peer_ready=False,
        )
        actual = _make_actual(close_change=-0.03)
        review = build_projection_review(snapshot, actual)
        messages = [rc["message"] for rc in review["rule_candidates"]]
        assert any("peer" in m or "peer" in m.lower() for m in messages)

    def test_peer_missing_rule_category(self):
        snapshot = _make_snapshot(final_direction="偏多", peer_ready=False)
        actual = _make_actual(close_change=-0.03)
        review = build_projection_review(snapshot, actual)
        categories = [rc["category"] for rc in review["rule_candidates"]]
        assert "false_confidence" in categories or "wrong_direction" in categories

    def test_historical_insufficient_generates_rule(self):
        snapshot = _make_snapshot(
            final_direction="偏多",
            final_confidence="high",
            hist_summary="样本不足，insufficient data",
        )
        actual = _make_actual(close_change=-0.03)
        review = build_projection_review(snapshot, actual)
        messages = [rc["message"] for rc in review["rule_candidates"]]
        assert any("historical" in m or "样本" in m for m in messages)

    def test_historical_insufficient_rule_category(self):
        snapshot = _make_snapshot(
            final_direction="偏多",
            final_confidence="high",
            hist_summary="insufficient",
        )
        actual = _make_actual(close_change=-0.03)
        review = build_projection_review(snapshot, actual)
        categories = [rc["category"] for rc in review["rule_candidates"]]
        assert "insufficient_data" in categories

    def test_peer_downgrade_ignored_generates_rule(self):
        snapshot = _make_snapshot(
            final_direction="偏多",
            final_confidence="high",
            peer_adjustment_text="peer 已降级处理",
        )
        actual = _make_actual(close_change=-0.03)
        review = build_projection_review(snapshot, actual)
        messages = " ".join(rc["message"] for rc in review["rule_candidates"])
        assert "peer" in messages or "降" in messages or "downgrade" in messages.lower()

    def test_rule_candidate_ids_are_unique(self):
        snapshot = _make_snapshot(
            final_direction="偏多",
            final_confidence="high",
            peer_ready=False,
            hist_summary="insufficient",
        )
        actual = _make_actual(close_change=-0.03)
        review = build_projection_review(snapshot, actual)
        ids = [rc["rule_id"] for rc in review["rule_candidates"]]
        assert len(ids) == len(set(ids)), "rule_candidate IDs must be unique"

    def test_correct_prediction_no_candidates(self):
        snapshot = _make_snapshot(final_direction="偏多")
        actual = _make_actual(close_change=0.02)
        review = build_projection_review(snapshot, actual)
        assert review["rule_candidates"] == []

    def test_neutral_prediction_no_candidates(self):
        snapshot = _make_snapshot(final_direction="中性")
        actual = _make_actual(close_change=0.02)
        review = build_projection_review(snapshot, actual)
        assert review["rule_candidates"] == []


# ─────────────────────────────────────────────────────────────────────────────
# 7. save_projection_v2_snapshot (DB write — uses real SQLite)
# ─────────────────────────────────────────────────────────────────────────────

class TestSaveSnapshot:
    def test_returns_string_id(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        import services.prediction_store as ps
        monkeypatch.setattr(ps, "DB_PATH", tmp_path / "test.db")
        snapshot = _make_snapshot()
        pid = save_projection_v2_snapshot(snapshot)
        assert isinstance(pid, str)
        assert len(pid) == 36  # UUID4

    def test_missing_prediction_for_date_raises(self):
        snapshot = _make_snapshot()
        del snapshot["prediction_for_date"]
        with pytest.raises(ValueError, match="prediction_for_date"):
            save_projection_v2_snapshot(snapshot)

    def test_snapshot_loadable_after_save(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        import services.prediction_store as ps
        monkeypatch.setattr(ps, "DB_PATH", tmp_path / "test.db")
        snapshot = _make_snapshot()
        pid = save_projection_v2_snapshot(snapshot)
        row = ps.get_prediction(pid)
        assert row is not None
        assert row["symbol"] == "AVGO"


# ─────────────────────────────────────────────────────────────────────────────
# 8. run_projection_review degraded paths (no real DB required)
# ─────────────────────────────────────────────────────────────────────────────

class TestRunProjectionReview:
    def test_missing_snapshot_returns_ready_false(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        import services.prediction_store as ps
        monkeypatch.setattr(ps, "DB_PATH", tmp_path / "empty.db")
        result = run_projection_review("AVGO", "2099-01-01", persist=False)
        assert result["ready"] is False
        assert len(result["warnings"]) >= 1

    def test_no_exception_on_missing_everything(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        import services.prediction_store as ps
        monkeypatch.setattr(ps, "DB_PATH", tmp_path / "empty.db")
        result = run_projection_review("AVGO", "2099-01-01", persist=False)
        assert isinstance(result, dict)

    def test_with_supplied_actual_outcome(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        import services.prediction_store as ps
        monkeypatch.setattr(ps, "DB_PATH", tmp_path / "empty.db")
        actual = _make_actual(close_change=0.02)
        result = run_projection_review(
            "AVGO", "2099-01-01", actual_outcome=actual, persist=False
        )
        # No snapshot found, so still ready=False
        assert result["ready"] is False

    def test_full_round_trip(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        import services.prediction_store as ps
        monkeypatch.setattr(ps, "DB_PATH", tmp_path / "rt.db")
        snapshot = _make_snapshot(final_direction="偏多")
        pid = save_projection_v2_snapshot(snapshot)
        actual = _make_actual(close_change=0.02)
        result = run_projection_review(
            "AVGO", "2026-04-21",
            actual_outcome=actual,
            prediction_id=pid,
            persist=False,
        )
        assert result["ready"] is True
        assert result["direction_correct"] is True
        assert result["symbol"] == "AVGO"


# ─────────────────────────────────────────────────────────────────────────────
# 9. F1 regression — unknown predicted_direction must not produce wrong_direction
# ─────────────────────────────────────────────────────────────────────────────

class TestF1UnknownDirectionRegression:
    """Regression for F1: error_category must not be 'wrong_direction' when
    predicted_direction is 'unknown' (direction_correct is None in that case).
    The two fields must never contradict each other."""

    def test_malformed_snapshot_actual_up_error_category_unknown(self):
        # Empty snapshot → predicted_direction = "unknown"
        actual = _make_actual(close_change=0.02)
        review = build_projection_review({}, actual)
        assert review["predicted_direction"] == "unknown"
        assert review["direction_correct"] is None
        assert review["error_category"] == "unknown", (
            "error_category must be 'unknown' when predicted_direction is 'unknown', "
            f"got {review['error_category']!r}"
        )

    def test_malformed_snapshot_actual_down_error_category_unknown(self):
        actual = _make_actual(close_change=-0.03)
        review = build_projection_review({}, actual)
        assert review["predicted_direction"] == "unknown"
        assert review["direction_correct"] is None
        assert review["error_category"] == "unknown"

    def test_garbage_direction_actual_up_error_category_unknown(self):
        snapshot = _make_snapshot()
        snapshot["final_direction"] = "GARBAGE_VALUE"
        actual = _make_actual(close_change=0.02)
        review = build_projection_review(snapshot, actual)
        assert review["predicted_direction"] == "unknown"
        assert review["direction_correct"] is None
        assert review["error_category"] == "unknown"

    def test_garbage_direction_actual_down_error_category_unknown(self):
        snapshot = _make_snapshot()
        snapshot["final_direction"] = "GARBAGE_VALUE"
        actual = _make_actual(close_change=-0.03)
        review = build_projection_review(snapshot, actual)
        assert review["predicted_direction"] == "unknown"
        assert review["direction_correct"] is None
        assert review["error_category"] == "unknown"

    def test_no_contradiction_direction_correct_none_never_wrong_direction(self):
        # Exhaustive check: whenever direction_correct is None,
        # error_category must never be "wrong_direction"
        cases = [
            ({}, _make_actual(close_change=0.02)),
            ({}, _make_actual(close_change=-0.03)),
            ({"final_direction": "GARBAGE"}, _make_actual(close_change=0.02)),
            (_make_snapshot(final_direction="中性"), _make_actual(close_change=0.02)),
            (_make_snapshot(), _make_actual(close_change=0.0005)),  # flat actual
        ]
        for snap, actual in cases:
            review = build_projection_review(snap, actual)
            if review["direction_correct"] is None:
                assert review["error_category"] != "wrong_direction", (
                    f"Contradiction: direction_correct=None but error_category='wrong_direction'. "
                    f"snapshot={snap!r}, close_change={actual.get('actual_close_change')}"
                )
