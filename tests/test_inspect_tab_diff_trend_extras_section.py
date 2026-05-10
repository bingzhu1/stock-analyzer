"""Tests for the Inspect-tab contract_payload diff / trend / extras
display sections (Step 18Y / PR-UI-3).

Spec source of truth:

- `tasks/record_1_0_architecture_reset_canonical_principles.md` §8 (Branch 9)
- `tasks/record_17m_ui_presentation_layer_rebuild_plan.md` §8 / §9 / §16
- `tasks/record_18s_third_layer_based_implementation_batch_selection.md`
  §4 / §6 / §10

PR-UI-3 adds three low-risk, display-only sections to
``ui/inspect_tab.py`` showing the latest read-only diagnostics from the
contract_payload backend tools (diff / trend / extras dashboard). Each
render helper is pure — takes the backend dict + a fake / real ``st``
object — so these tests can drive every code path without touching a
Streamlit runtime, the DB, or any business module.

This suite verifies (numbers correspond to the user spec):

1. Diff section renders header / status / changed_fields when present.
2. Diff section handles ``None`` gracefully (info, no crash).
3. Diff section handles non-dict input gracefully (warning, no crash).
4. Diff section does not mutate input.
5. Diff section renders failed_side / error / validation_errors when
   the backend reports a failure status.
6. Diff section renders ``not_enough_records`` status with
   ``available_records`` caption.

7. Trend section renders header / status / counts / sample_count when
   present.
8. Trend section handles ``None`` gracefully.
9. Trend section handles non-dict input gracefully.
10. Trend section does not mutate input.
11. Trend section renders skipped_records when present.
12. Trend section renders field_distributions / numeric_stats /
    latest_values inside expanders when present.

13. Extras section renders header / status / counts / symbol_filter
    when present.
14. Extras section handles ``None`` gracefully.
15. Extras section handles non-dict input gracefully.
16. Extras section does not mutate input.
17. Extras section renders latest_snapshot / extras_distributions
    inside expanders when present.
18. Extras section renders error caption on ``error`` status.

19. Status labels: each documented status produces the friendly label;
    unknown status renders the fallback label.
20. All three render helpers only emit documented Streamlit-style
    events (markdown / caption / info / warning / json /
    expander_enter / expander_exit).
21. Helper module references stay inside ``ui.inspect_tab``.
22. Module-level import boundary unchanged: ``ui/inspect_tab.py`` does
    not import predict / app / main_projection_layer / exclusion_layer
    / confidence_evaluator / final_decision / prediction_store /
    sqlite3 / yfinance at the top level; lazy imports happen only
    inside ``render_inspect_tab``.
23. New helper bodies do not contain DB / business / forbidden tokens.
"""

from __future__ import annotations

import copy
import unittest
from pathlib import Path
from typing import Any

import ui.inspect_tab as inspect_mod
from ui.inspect_tab import (
    _DIFF_STATUS_LABELS,
    _EXTRAS_STATUS_LABELS,
    _TREND_STATUS_LABELS,
    _render_contract_payload_diff_section,
    _render_contract_payload_extras_section,
    _render_contract_payload_trend_section,
)


_REPO_ROOT = Path(__file__).resolve().parent.parent


def _read(rel: str) -> str:
    return (_REPO_ROOT / rel).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Fake Streamlit substitute (parallel to the 18Q test pattern).
# ---------------------------------------------------------------------------

class _FakeExpander:
    """Minimal ``st.expander`` substitute supporting context-manager use."""

    def __init__(self, label: str, owner: "_FakeStreamlit") -> None:
        self.label = label
        self._owner = owner

    def __enter__(self) -> "_FakeExpander":
        self._owner.events.append(("expander_enter", self.label))
        return self

    def __exit__(self, *exc: object) -> None:
        self._owner.events.append(("expander_exit", self.label))

    def __getattr__(self, name: str) -> Any:
        return getattr(self._owner, name)


class _FakeStreamlit:
    """Captures all Streamlit-style calls without rendering."""

    def __init__(self) -> None:
        self.events: list[tuple[str, Any]] = []

    def markdown(self, body: str, **_: Any) -> None:
        self.events.append(("markdown", body))

    def caption(self, body: str) -> None:
        self.events.append(("caption", body))

    def info(self, body: str) -> None:
        self.events.append(("info", body))

    def warning(self, body: str) -> None:
        self.events.append(("warning", body))

    def json(self, value: Any) -> None:
        self.events.append(("json", value))

    def expander(self, label: str) -> _FakeExpander:
        return _FakeExpander(label, self)

    def text_blob(self) -> str:
        out: list[str] = []
        for event, payload in self.events:
            if event in ("markdown", "caption", "info", "warning"):
                out.append(str(payload))
        return "\n".join(out)


# ---------------------------------------------------------------------------
# Sample backend results (mirroring real shapes from
# services/contract_payload_diff.py / contract_payload_trend.py /
# contract_payload_extras_dashboard.py).
# ---------------------------------------------------------------------------

def _ok_diff_result() -> dict[str, Any]:
    return {
        "latest_prediction_id": "pred-2026-04-21-AVGO",
        "previous_prediction_id": "pred-2026-04-20-AVGO",
        "symbol": "AVGO",
        "status": "ok",
        "changed_fields": [
            "final_projection.final_direction",
            "confidence_system.confidence_level",
        ],
        "summary": {
            "final_direction": {"from": "偏多", "to": "中性"},
            "confidence_level": {"from": "high", "to": "medium"},
        },
    }


def _ok_trend_result() -> dict[str, Any]:
    return {
        "requested_limit": 10,
        "records_scanned": 7,
        "valid_payloads": 6,
        "invalid_payloads": 1,
        "skipped_records": [
            {"prediction_id": "pred-bad-1", "reason": "validation_failed"},
        ],
        "status": "ok",
        "field_distributions": {
            "final_projection.final_direction": {"偏多": 4, "中性": 2},
        },
        "numeric_stats": {
            "confidence_system.total_confidence": {
                "min": 0.4, "max": 0.9, "mean": 0.65,
            },
        },
        "latest_values": {
            "final_projection.final_direction": "偏多",
        },
    }


def _ok_extras_result() -> dict[str, Any]:
    return {
        "requested_limit": 20,
        "records_scanned": 5,
        "valid_payloads": 5,
        "invalid_payloads": 0,
        "skipped_records": [],
        "symbol_filter": "AVGO",
        "status": "ok",
        "latest_snapshot": {
            "prediction_id": "pred-2026-04-21-AVGO",
            "prediction_for_date": "2026-04-21",
            "final_direction": "偏多",
        },
        "extras_distributions": {
            "exclusion_system.extras.soft_signal": {"on": 3, "off": 2},
        },
    }


# ---------------------------------------------------------------------------
# 1 / 5 / 6. Diff section happy path / failure paths
# ---------------------------------------------------------------------------

class DiffSectionRenderTests(unittest.TestCase):
    def test_renders_header_status_changed_fields(self) -> None:
        st = _FakeStreamlit()
        _render_contract_payload_diff_section(_ok_diff_result(), st)
        text = st.text_blob()
        self.assertIn("最近两次 contract_payload diff", text)
        self.assertIn("ok", text)
        self.assertIn("已比对最近两次 contract_payload", text)
        self.assertIn("changed_fields", text)
        self.assertIn("final_projection.final_direction", text)

    def test_renders_metadata_caption(self) -> None:
        st = _FakeStreamlit()
        _render_contract_payload_diff_section(_ok_diff_result(), st)
        text = st.text_blob()
        self.assertIn("pred-2026-04-21-AVGO", text)
        self.assertIn("pred-2026-04-20-AVGO", text)
        self.assertIn("AVGO", text)

    def test_renders_summary_inside_expander(self) -> None:
        st = _FakeStreamlit()
        _render_contract_payload_diff_section(_ok_diff_result(), st)
        kinds = [e[0] for e in st.events]
        self.assertIn("expander_enter", kinds)
        self.assertIn("json", kinds)
        self.assertIn("expander_exit", kinds)

    def test_empty_changed_fields_renders_none_label(self) -> None:
        st = _FakeStreamlit()
        result = _ok_diff_result()
        result["changed_fields"] = []
        _render_contract_payload_diff_section(result, st)
        text = st.text_blob()
        self.assertIn("changed_fields", text)
        self.assertIn("无", text)

    def test_failed_side_and_error_rendered(self) -> None:
        st = _FakeStreamlit()
        result = {
            "latest_prediction_id": "pred-x",
            "previous_prediction_id": "pred-y",
            "symbol": "AVGO",
            "status": "invalid_json",
            "failed_side": "latest",
            "error": "Expecting value: line 1 column 1 (char 0)",
        }
        _render_contract_payload_diff_section(result, st)
        text = st.text_blob()
        self.assertIn("invalid_json", text)
        self.assertIn("failed_side", text)
        self.assertIn("latest", text)
        self.assertIn("error", text)
        self.assertIn("Expecting value", text)

    def test_validation_failed_renders_validation_errors(self) -> None:
        st = _FakeStreamlit()
        result = {
            "latest_prediction_id": "pred-x",
            "previous_prediction_id": "pred-y",
            "symbol": "AVGO",
            "status": "validation_failed",
            "failed_side": "latest",
            "validation_errors": [
                "missing field: final_projection.final_direction",
            ],
        }
        _render_contract_payload_diff_section(result, st)
        text = st.text_blob()
        self.assertIn("validation_failed", text)
        self.assertIn("validation_errors", text)
        self.assertIn(
            "missing field: final_projection.final_direction", text
        )

    def test_not_enough_records_renders_available_records(self) -> None:
        st = _FakeStreamlit()
        result = {"status": "not_enough_records", "available_records": 1}
        _render_contract_payload_diff_section(result, st)
        text = st.text_blob()
        self.assertIn("not_enough_records", text)
        self.assertIn("available_records", text)
        self.assertIn("1", text)


# ---------------------------------------------------------------------------
# 2 / 3 / 4. Diff section None / non-dict / no-mutation
# ---------------------------------------------------------------------------

class DiffSectionDefensiveTests(unittest.TestCase):
    def test_none_emits_friendly_info(self) -> None:
        st = _FakeStreamlit()
        _render_contract_payload_diff_section(None, st)
        kinds = [e[0] for e in st.events]
        self.assertIn("info", kinds)

    def test_non_dict_emits_friendly_warning(self) -> None:
        for bad in ([], "string", 42, True):
            with self.subTest(value=bad):
                st = _FakeStreamlit()
                _render_contract_payload_diff_section(bad, st)
                kinds = [e[0] for e in st.events]
                self.assertIn("warning", kinds)

    def test_does_not_mutate_input(self) -> None:
        st = _FakeStreamlit()
        result = _ok_diff_result()
        snapshot = copy.deepcopy(result)
        _render_contract_payload_diff_section(result, st)
        self.assertEqual(result, snapshot)


# ---------------------------------------------------------------------------
# 7 / 11 / 12. Trend section happy path / skipped / expanders
# ---------------------------------------------------------------------------

class TrendSectionRenderTests(unittest.TestCase):
    def test_renders_header_status_counts(self) -> None:
        st = _FakeStreamlit()
        _render_contract_payload_trend_section(_ok_trend_result(), st)
        text = st.text_blob()
        self.assertIn("contract_payload 近期 trend", text)
        self.assertIn("ok", text)
        self.assertIn("已聚合最近若干条 contract_payload", text)
        self.assertIn("requested_limit", text)
        self.assertIn("records_scanned", text)
        self.assertIn("valid_payloads", text)
        self.assertIn("invalid_payloads", text)

    def test_renders_field_distributions_in_expander(self) -> None:
        st = _FakeStreamlit()
        _render_contract_payload_trend_section(_ok_trend_result(), st)
        kinds = [e[0] for e in st.events]
        self.assertIn("expander_enter", kinds)
        self.assertIn("json", kinds)
        text = st.text_blob()
        self.assertIn("field_distributions", text)

    def test_renders_numeric_stats_in_expander(self) -> None:
        st = _FakeStreamlit()
        _render_contract_payload_trend_section(_ok_trend_result(), st)
        text = st.text_blob()
        self.assertIn("numeric_stats", text)

    def test_renders_latest_values_in_expander(self) -> None:
        st = _FakeStreamlit()
        _render_contract_payload_trend_section(_ok_trend_result(), st)
        text = st.text_blob()
        self.assertIn("latest_values", text)

    def test_renders_skipped_records_when_present(self) -> None:
        st = _FakeStreamlit()
        _render_contract_payload_trend_section(_ok_trend_result(), st)
        text = st.text_blob()
        self.assertIn("skipped_records", text)
        self.assertIn("pred-bad-1", text)
        self.assertIn("validation_failed", text)

    def test_no_records_status_renders_label(self) -> None:
        st = _FakeStreamlit()
        result = {
            "status": "no_records",
            "requested_limit": 10,
            "records_scanned": 0,
        }
        _render_contract_payload_trend_section(result, st)
        text = st.text_blob()
        self.assertIn("no_records", text)
        self.assertIn("尚无 prediction 记录", text)

    def test_error_status_renders_error_text(self) -> None:
        st = _FakeStreamlit()
        result = {"status": "error", "error": "db_read_failed: missing"}
        _render_contract_payload_trend_section(result, st)
        text = st.text_blob()
        self.assertIn("error", text)
        self.assertIn("db_read_failed: missing", text)


# ---------------------------------------------------------------------------
# 8 / 9 / 10. Trend section None / non-dict / no-mutation
# ---------------------------------------------------------------------------

class TrendSectionDefensiveTests(unittest.TestCase):
    def test_none_emits_friendly_info(self) -> None:
        st = _FakeStreamlit()
        _render_contract_payload_trend_section(None, st)
        kinds = [e[0] for e in st.events]
        self.assertIn("info", kinds)

    def test_non_dict_emits_friendly_warning(self) -> None:
        for bad in ([], "string", 42, True):
            with self.subTest(value=bad):
                st = _FakeStreamlit()
                _render_contract_payload_trend_section(bad, st)
                kinds = [e[0] for e in st.events]
                self.assertIn("warning", kinds)

    def test_does_not_mutate_input(self) -> None:
        st = _FakeStreamlit()
        result = _ok_trend_result()
        snapshot = copy.deepcopy(result)
        _render_contract_payload_trend_section(result, st)
        self.assertEqual(result, snapshot)


# ---------------------------------------------------------------------------
# 13 / 17 / 18. Extras section happy path / expanders / error
# ---------------------------------------------------------------------------

class ExtrasSectionRenderTests(unittest.TestCase):
    def test_renders_header_status_counts(self) -> None:
        st = _FakeStreamlit()
        _render_contract_payload_extras_section(_ok_extras_result(), st)
        text = st.text_blob()
        self.assertIn("contract_payload extras dashboard", text)
        self.assertIn("ok", text)
        self.assertIn("已聚合最近若干条 contract extras", text)
        self.assertIn("symbol_filter", text)
        self.assertIn("AVGO", text)
        self.assertIn("requested_limit", text)
        self.assertIn("records_scanned", text)

    def test_renders_latest_snapshot_in_expander(self) -> None:
        st = _FakeStreamlit()
        _render_contract_payload_extras_section(_ok_extras_result(), st)
        kinds = [e[0] for e in st.events]
        self.assertIn("expander_enter", kinds)
        self.assertIn("json", kinds)
        text = st.text_blob()
        self.assertIn("latest_snapshot", text)

    def test_renders_extras_distributions_in_expander(self) -> None:
        st = _FakeStreamlit()
        _render_contract_payload_extras_section(_ok_extras_result(), st)
        text = st.text_blob()
        self.assertIn("extras_distributions", text)

    def test_no_valid_payloads_renders_label(self) -> None:
        st = _FakeStreamlit()
        result = {
            "status": "no_valid_payloads",
            "symbol_filter": "AVGO",
            "requested_limit": 20,
            "records_scanned": 3,
            "valid_payloads": 0,
            "invalid_payloads": 3,
            "skipped_records": [
                {"prediction_id": "pred-bad-2", "reason": "missing_contract_payload"},
            ],
        }
        _render_contract_payload_extras_section(result, st)
        text = st.text_blob()
        self.assertIn("no_valid_payloads", text)
        self.assertIn("扫描的记录中没有可用的 contract_payload", text)
        self.assertIn("skipped_records", text)
        self.assertIn("pred-bad-2", text)

    def test_error_status_renders_error_text(self) -> None:
        st = _FakeStreamlit()
        result = {
            "status": "error",
            "error": "db_read_failed: missing",
            "symbol_filter": "AVGO",
        }
        _render_contract_payload_extras_section(result, st)
        text = st.text_blob()
        self.assertIn("error", text)
        self.assertIn("db_read_failed: missing", text)


# ---------------------------------------------------------------------------
# 14 / 15 / 16. Extras section None / non-dict / no-mutation
# ---------------------------------------------------------------------------

class ExtrasSectionDefensiveTests(unittest.TestCase):
    def test_none_emits_friendly_info(self) -> None:
        st = _FakeStreamlit()
        _render_contract_payload_extras_section(None, st)
        kinds = [e[0] for e in st.events]
        self.assertIn("info", kinds)

    def test_non_dict_emits_friendly_warning(self) -> None:
        for bad in ([], "string", 42, True):
            with self.subTest(value=bad):
                st = _FakeStreamlit()
                _render_contract_payload_extras_section(bad, st)
                kinds = [e[0] for e in st.events]
                self.assertIn("warning", kinds)

    def test_does_not_mutate_input(self) -> None:
        st = _FakeStreamlit()
        result = _ok_extras_result()
        snapshot = copy.deepcopy(result)
        _render_contract_payload_extras_section(result, st)
        self.assertEqual(result, snapshot)


# ---------------------------------------------------------------------------
# 19. Status label coverage for all three sections
# ---------------------------------------------------------------------------

class StatusLabelCoverageTests(unittest.TestCase):
    def test_each_diff_status_has_label(self) -> None:
        for status, label in _DIFF_STATUS_LABELS.items():
            with self.subTest(status=status):
                st = _FakeStreamlit()
                _render_contract_payload_diff_section({"status": status}, st)
                text = st.text_blob()
                self.assertIn(status, text)
                self.assertIn(label, text)

    def test_unknown_diff_status_renders_fallback(self) -> None:
        st = _FakeStreamlit()
        _render_contract_payload_diff_section({"status": "weird_diff_status"}, st)
        text = st.text_blob()
        self.assertIn("weird_diff_status", text)
        self.assertIn("未识别状态", text)

    def test_each_trend_status_has_label(self) -> None:
        for status, label in _TREND_STATUS_LABELS.items():
            with self.subTest(status=status):
                st = _FakeStreamlit()
                _render_contract_payload_trend_section({"status": status}, st)
                text = st.text_blob()
                self.assertIn(status, text)
                self.assertIn(label, text)

    def test_unknown_trend_status_renders_fallback(self) -> None:
        st = _FakeStreamlit()
        _render_contract_payload_trend_section(
            {"status": "weird_trend_status"}, st
        )
        text = st.text_blob()
        self.assertIn("weird_trend_status", text)
        self.assertIn("未识别状态", text)

    def test_each_extras_status_has_label(self) -> None:
        for status, label in _EXTRAS_STATUS_LABELS.items():
            with self.subTest(status=status):
                st = _FakeStreamlit()
                _render_contract_payload_extras_section(
                    {"status": status}, st
                )
                text = st.text_blob()
                self.assertIn(status, text)
                self.assertIn(label, text)

    def test_unknown_extras_status_renders_fallback(self) -> None:
        st = _FakeStreamlit()
        _render_contract_payload_extras_section(
            {"status": "weird_extras_status"}, st
        )
        text = st.text_blob()
        self.assertIn("weird_extras_status", text)
        self.assertIn("未识别状态", text)


# ---------------------------------------------------------------------------
# 20. Helpers only emit documented Streamlit-style events
# ---------------------------------------------------------------------------

_ALLOWED_EVENT_KINDS = (
    "markdown",
    "caption",
    "info",
    "warning",
    "json",
    "expander_enter",
    "expander_exit",
)


class HelperEventKindBoundaryTests(unittest.TestCase):
    def _assert_only_allowed(self, st: _FakeStreamlit, *, label: str) -> None:
        for kind, _ in st.events:
            self.assertIn(
                kind, _ALLOWED_EVENT_KINDS,
                msg=f"unexpected event kind from {label}: {kind}",
            )

    def test_diff_section_emits_only_allowed_events(self) -> None:
        st = _FakeStreamlit()
        _render_contract_payload_diff_section(_ok_diff_result(), st)
        self._assert_only_allowed(st, label="diff section")

    def test_trend_section_emits_only_allowed_events(self) -> None:
        st = _FakeStreamlit()
        _render_contract_payload_trend_section(_ok_trend_result(), st)
        self._assert_only_allowed(st, label="trend section")

    def test_extras_section_emits_only_allowed_events(self) -> None:
        st = _FakeStreamlit()
        _render_contract_payload_extras_section(_ok_extras_result(), st)
        self._assert_only_allowed(st, label="extras section")


# ---------------------------------------------------------------------------
# 21. Helper module references
# ---------------------------------------------------------------------------

class HelperModuleReferenceTests(unittest.TestCase):
    def test_helpers_live_in_inspect_tab_module(self) -> None:
        for fn in (
            _render_contract_payload_diff_section,
            _render_contract_payload_trend_section,
            _render_contract_payload_extras_section,
        ):
            with self.subTest(helper=fn.__name__):
                self.assertEqual(fn.__module__, "ui.inspect_tab")

    def test_helpers_exported_for_testing(self) -> None:
        for name in (
            "_render_contract_payload_diff_section",
            "_render_contract_payload_trend_section",
            "_render_contract_payload_extras_section",
            "_DIFF_STATUS_LABELS",
            "_TREND_STATUS_LABELS",
            "_EXTRAS_STATUS_LABELS",
        ):
            with self.subTest(name=name):
                self.assertTrue(
                    hasattr(inspect_mod, name),
                    msg=f"ui.inspect_tab missing `{name}`",
                )


# ---------------------------------------------------------------------------
# 22. Module-level import boundary unchanged
# ---------------------------------------------------------------------------

class InspectTabModuleImportBoundaryTests(unittest.TestCase):
    """``ui/inspect_tab.py`` must not import any business module / DB at
    the module top level. Lazy imports of streamlit, ``services.inspect_analysis``,
    ``services.contract_payload_inspector``, ``services.contract_payload_diff``,
    ``services.contract_payload_trend``,
    ``services.contract_payload_extras_dashboard`` happen inside
    ``render_inspect_tab`` only."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = _read("ui/inspect_tab.py")

    def test_no_predict_top_level_import(self) -> None:
        head = self.source.split("def render_inspect_tab(")[0]
        for f in (
            "import predict",
            "from predict",
            "import app",
            "from app",
        ):
            self.assertNotIn(
                f, head,
                msg=f"ui/inspect_tab.py must not contain top-level `{f}`",
            )

    def test_no_business_module_top_level_import(self) -> None:
        head = self.source.split("def render_inspect_tab(")[0]
        for f in (
            "from services.main_projection_layer",
            "import services.main_projection_layer",
            "from services.exclusion_layer",
            "import services.exclusion_layer",
            "from services.confidence_evaluator",
            "import services.confidence_evaluator",
            "from services.final_decision",
            "import services.final_decision",
            "from services.prediction_store",
            "import services.prediction_store",
            "from services.projection_orchestrator",
            "import services.projection_orchestrator",
            "from services.home_terminal_orchestrator",
            "import services.home_terminal_orchestrator",
            "from services.review_orchestrator",
            "import services.review_orchestrator",
            "from services.contract_payload_diff",
            "import services.contract_payload_diff",
            "from services.contract_payload_trend",
            "import services.contract_payload_trend",
            "from services.contract_payload_extras_dashboard",
            "import services.contract_payload_extras_dashboard",
        ):
            self.assertNotIn(
                f, head,
                msg=f"ui/inspect_tab.py must not contain top-level `{f}`",
            )

    def test_no_sqlite_or_yfinance_anywhere(self) -> None:
        for f in (
            "import sqlite3",
            "from sqlite3",
            "import yfinance",
            "from yfinance",
        ):
            self.assertNotIn(
                f, self.source,
                msg=f"ui/inspect_tab.py must not contain `{f}`",
            )

    def test_no_streamlit_top_level_import(self) -> None:
        head = self.source.split("def render_inspect_tab(")[0]
        for f in ("import streamlit", "from streamlit"):
            self.assertNotIn(
                f, head,
                msg=f"ui/inspect_tab.py must not contain top-level `{f}`",
            )


# ---------------------------------------------------------------------------
# 23. New helper bodies do not contain forbidden tokens
# ---------------------------------------------------------------------------

class HelperBodyForbiddenTokenTests(unittest.TestCase):
    """Source-level scan: each new render helper body must not contain
    DB / business / forbidden trading / orchestrator tokens. The
    backend backend modules with these tokens are reached only by
    ``render_inspect_tab`` (the wiring layer), not by the helpers."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = _read("ui/inspect_tab.py")

    def _slice_helper(self, start_marker: str, end_marker: str) -> str:
        start = self.source.index(start_marker)
        end = self.source.index(end_marker, start)
        return self.source[start:end]

    def _assert_no_forbidden(self, body: str, *, label: str) -> None:
        for forbidden in (
            "sqlite3",
            "prediction_store",
            "main_projection_layer",
            "exclusion_layer",
            "confidence_evaluator",
            "final_decision",
            "run_predict",
            "open(",
            '"buy"',
            "'buy'",
            '"sell"',
            "'sell'",
            '"hold"',
            "'hold'",
            '"hard"',
            "'hard'",
            '"forced"',
            "'forced'",
            '"required"',
            "'required'",
            '"trading_action"',
            "'trading_action'",
        ):
            with self.subTest(label=label, forbidden=forbidden):
                self.assertNotIn(
                    forbidden, body,
                    msg=f"{label} body must not contain {forbidden!r}",
                )

    def test_diff_section_body_clean(self) -> None:
        body = self._slice_helper(
            "def _render_contract_payload_diff_section(",
            "def _render_contract_payload_trend_section(",
        )
        self._assert_no_forbidden(body, label="_render_contract_payload_diff_section")

    def test_trend_section_body_clean(self) -> None:
        body = self._slice_helper(
            "def _render_contract_payload_trend_section(",
            "def _render_contract_payload_extras_section(",
        )
        self._assert_no_forbidden(body, label="_render_contract_payload_trend_section")

    def test_extras_section_body_clean(self) -> None:
        body = self._slice_helper(
            "def _render_contract_payload_extras_section(",
            "def _render_stats_block(",
        )
        self._assert_no_forbidden(body, label="_render_contract_payload_extras_section")


if __name__ == "__main__":
    unittest.main()
