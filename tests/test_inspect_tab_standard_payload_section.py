"""Tests for the Inspect-tab Standard Payload status section
(Step 18Q / PR-UI-2).

Spec source of truth:

- `tasks/record_1_0_architecture_reset_canonical_principles.md` §8 (Branch 9)
- `tasks/record_17m_ui_presentation_layer_rebuild_plan.md` §8 / §9 / §16
- `tasks/record_18a_first_layer_based_implementation_batch_selection.md` §13
- `tasks/record_18j_second_layer_based_implementation_batch_selection.md` §6 / §11

PR-UI-2 adds a low-risk, display-only section to ``ui/inspect_tab.py``
showing the latest ``contract_payload`` inspector status. The render
helper is pure (takes an inspector_result dict + a fake / real ``st``
object), so these tests can drive every code path without touching a
Streamlit runtime, the DB, or any business module.

This suite verifies:

1.  ``_compute_missing_sections`` returns the expected list when given
    a partial sections_present list.
2.  ``_compute_missing_sections`` returns the canonical contract list
    when sections_present is not a list (defensive).
3.  ``_compute_missing_sections`` returns empty when sections_present is
    full.
4.  ``_render_standard_payload_section`` writes a section header + status
    line for a typical "ok" inspector result.
5.  Renders schema_version when the result dict carries one.
6.  Renders compatibility_mode when present.
7.  Renders missing_sections list when present and non-empty; renders
    "无" when present and empty.
8.  Renders validation_errors list when present and non-empty; renders
    "无" when present and empty.
9.  Renders summary inside an expander when present.
10. Handles ``inspector_result=None`` gracefully (info message, no
    crash).
11. Handles non-dict ``inspector_result`` gracefully (warning, no crash).
12. Renders the friendly status label for "no_records" /
    "missing_contract_payload" / "invalid_json" / "validation_failed".
13. Does not mutate the input dict (deep-copy round-trip).
14. Does not call any DB / Streamlit runtime / business module from
    the helper itself.
15. Module import boundary: ``ui.inspect_tab`` does not import predict,
    main_projection_layer, exclusion_layer, confidence_evaluator,
    final_decision, prediction_store, sqlite3, yfinance.
"""

from __future__ import annotations

import copy
import unittest
from pathlib import Path
from typing import Any

import ui.inspect_tab as inspect_mod
from services.projection_output_contract import CONTRACT_SECTIONS
from ui.inspect_tab import (
    _compute_missing_sections,
    _render_standard_payload_section,
)


_REPO_ROOT = Path(__file__).resolve().parent.parent


def _read(rel: str) -> str:
    return (_REPO_ROOT / rel).read_text(encoding="utf-8")


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

    # Expander forwards any st.* calls made inside the ``with`` block to
    # the owner, mirroring real Streamlit semantics.
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

    # Convenience for tests: gather all text emitted by markdown / caption /
    # info / warning into a single string.
    def text_blob(self) -> str:
        out: list[str] = []
        for event, payload in self.events:
            if event in ("markdown", "caption", "info", "warning"):
                out.append(str(payload))
        return "\n".join(out)


def _ok_inspector_result() -> dict[str, Any]:
    return {
        "prediction_id": "pred-2026-04-21-AVGO",
        "symbol": "AVGO",
        "prediction_for_date": "2026-04-21",
        "status": "ok",
        "validation_errors": [],
        "sections_present": list(CONTRACT_SECTIONS),
        "summary": {section: "ok" for section in CONTRACT_SECTIONS},
    }


# ---------------------------------------------------------------------------
# 1-3. _compute_missing_sections
# ---------------------------------------------------------------------------

class ComputeMissingSectionsTests(unittest.TestCase):
    def test_partial_sections_present_returns_complement(self) -> None:
        present = list(CONTRACT_SECTIONS[:2])
        missing = _compute_missing_sections(present)
        self.assertEqual(missing, list(CONTRACT_SECTIONS[2:]))

    def test_non_list_input_returns_canonical_contract_sections(self) -> None:
        for bad in (None, "string", 42, {}):
            with self.subTest(value=bad):
                missing = _compute_missing_sections(bad)
                self.assertEqual(missing, list(CONTRACT_SECTIONS))

    def test_full_sections_present_returns_empty(self) -> None:
        present = list(CONTRACT_SECTIONS)
        self.assertEqual(_compute_missing_sections(present), [])

    def test_extra_unknown_sections_in_present_are_ignored(self) -> None:
        present = list(CONTRACT_SECTIONS) + ["unknown_extra_section"]
        # Result should still be empty — the function only checks coverage
        # of the canonical contract; extras are not considered missing.
        self.assertEqual(_compute_missing_sections(present), [])

    def test_non_string_entries_in_present_are_ignored(self) -> None:
        # Defensive: None / int / dict mixed into sections_present should
        # not pollute the missing list.
        present = list(CONTRACT_SECTIONS[:1]) + [None, 42, {"key": "val"}]
        missing = _compute_missing_sections(present)
        self.assertEqual(missing, list(CONTRACT_SECTIONS[1:]))


# ---------------------------------------------------------------------------
# 4. Header + status line for ok result
# ---------------------------------------------------------------------------

class RenderHappyPathTests(unittest.TestCase):
    def test_renders_section_header_and_status(self) -> None:
        st = _FakeStreamlit()
        _render_standard_payload_section(_ok_inspector_result(), st)
        text = st.text_blob()
        self.assertIn("Standard Payload 状态", text)
        self.assertIn("Status", text)
        self.assertIn("ok", text)
        self.assertIn("通过 contract validator", text)

    def test_renders_metadata_caption(self) -> None:
        st = _FakeStreamlit()
        _render_standard_payload_section(_ok_inspector_result(), st)
        text = st.text_blob()
        self.assertIn("pred-2026-04-21-AVGO", text)
        self.assertIn("AVGO", text)
        self.assertIn("2026-04-21", text)


# ---------------------------------------------------------------------------
# 5. schema_version
# ---------------------------------------------------------------------------

class SchemaVersionRenderTests(unittest.TestCase):
    def test_schema_version_rendered_when_present(self) -> None:
        st = _FakeStreamlit()
        result = _ok_inspector_result()
        result["schema_version"] = "feature_payload.v1"
        _render_standard_payload_section(result, st)
        text = st.text_blob()
        self.assertIn("schema_version", text)
        self.assertIn("feature_payload.v1", text)

    def test_schema_version_omitted_when_absent(self) -> None:
        st = _FakeStreamlit()
        _render_standard_payload_section(_ok_inspector_result(), st)
        text = st.text_blob()
        self.assertNotIn("schema_version", text)


# ---------------------------------------------------------------------------
# 6. compatibility_mode
# ---------------------------------------------------------------------------

class CompatibilityModeRenderTests(unittest.TestCase):
    def test_compatibility_mode_rendered_when_present(self) -> None:
        st = _FakeStreamlit()
        result = _ok_inspector_result()
        result["compatibility_mode"] = "compatibility_fallback"
        _render_standard_payload_section(result, st)
        text = st.text_blob()
        self.assertIn("compatibility_mode", text)
        self.assertIn("compatibility_fallback", text)

    def test_compatibility_mode_omitted_when_absent(self) -> None:
        st = _FakeStreamlit()
        _render_standard_payload_section(_ok_inspector_result(), st)
        text = st.text_blob()
        self.assertNotIn("compatibility_mode", text)


# ---------------------------------------------------------------------------
# 7. missing_sections
# ---------------------------------------------------------------------------

class MissingSectionsRenderTests(unittest.TestCase):
    def test_non_empty_missing_sections_listed(self) -> None:
        st = _FakeStreamlit()
        result = _ok_inspector_result()
        result["missing_sections"] = ["section_a", "section_b"]
        _render_standard_payload_section(result, st)
        text = st.text_blob()
        self.assertIn("missing_sections", text)
        self.assertIn("section_a", text)
        self.assertIn("section_b", text)

    def test_empty_missing_sections_renders_none_label(self) -> None:
        st = _FakeStreamlit()
        result = _ok_inspector_result()
        result["missing_sections"] = []
        _render_standard_payload_section(result, st)
        text = st.text_blob()
        self.assertIn("missing_sections", text)
        self.assertIn("无", text)


# ---------------------------------------------------------------------------
# 8. validation_errors
# ---------------------------------------------------------------------------

class ValidationErrorsRenderTests(unittest.TestCase):
    def test_non_empty_validation_errors_listed(self) -> None:
        st = _FakeStreamlit()
        result = _ok_inspector_result()
        result["validation_errors"] = [
            "missing field: metadata.symbol",
            "invalid value: schema_version expected ...",
        ]
        _render_standard_payload_section(result, st)
        text = st.text_blob()
        self.assertIn("validation_errors", text)
        self.assertIn("missing field: metadata.symbol", text)
        self.assertIn("invalid value: schema_version expected ...", text)

    def test_empty_validation_errors_renders_none_label(self) -> None:
        st = _FakeStreamlit()
        _render_standard_payload_section(_ok_inspector_result(), st)
        text = st.text_blob()
        self.assertIn("validation_errors", text)
        self.assertIn("无", text)


# ---------------------------------------------------------------------------
# 9. summary expander
# ---------------------------------------------------------------------------

class SummaryExpanderTests(unittest.TestCase):
    def test_summary_rendered_inside_expander(self) -> None:
        st = _FakeStreamlit()
        _render_standard_payload_section(_ok_inspector_result(), st)
        events = st.events
        # An expander_enter must precede a json() and an expander_exit.
        kinds = [e[0] for e in events]
        self.assertIn("expander_enter", kinds)
        self.assertIn("expander_exit", kinds)
        self.assertIn("json", kinds)
        # Order: expander_enter ... json ... expander_exit
        enter_idx = kinds.index("expander_enter")
        json_idx = kinds.index("json")
        exit_idx = kinds.index("expander_exit")
        self.assertLess(enter_idx, json_idx)
        self.assertLess(json_idx, exit_idx)

    def test_summary_omitted_when_absent(self) -> None:
        st = _FakeStreamlit()
        result = _ok_inspector_result()
        result.pop("summary")
        _render_standard_payload_section(result, st)
        kinds = [e[0] for e in st.events]
        self.assertNotIn("json", kinds)


# ---------------------------------------------------------------------------
# 10. None inspector_result
# ---------------------------------------------------------------------------

class NoneInspectorResultTests(unittest.TestCase):
    def test_none_emits_friendly_info_message(self) -> None:
        st = _FakeStreamlit()
        _render_standard_payload_section(None, st)
        text = st.text_blob()
        self.assertIn("Standard Payload 状态", text)
        # Caller hasn't supplied a result yet — surface as info, not error.
        self.assertTrue(
            any(event == "info" for event, _ in st.events),
            msg=f"expected an info() call; got events {st.events}",
        )


# ---------------------------------------------------------------------------
# 11. Non-dict inspector_result
# ---------------------------------------------------------------------------

class NonDictInspectorResultTests(unittest.TestCase):
    def test_non_dict_emits_friendly_warning(self) -> None:
        for bad in ([], "string", 42, True):
            with self.subTest(value=bad):
                st = _FakeStreamlit()
                _render_standard_payload_section(bad, st)
                self.assertTrue(
                    any(event == "warning" for event, _ in st.events),
                    msg=f"expected a warning() call for {bad!r}; got events {st.events}",
                )


# ---------------------------------------------------------------------------
# 12. Status labels for all known statuses
# ---------------------------------------------------------------------------

class StatusLabelsTests(unittest.TestCase):
    def test_each_known_status_has_label(self) -> None:
        for status, label in (
            ("ok", "通过 contract validator"),
            ("no_records", "尚无 prediction 记录"),
            ("missing_contract_payload", "最新记录缺少 contract_payload"),
            ("invalid_json", "contract_payload JSON 解析失败"),
            ("validation_failed", "contract validator 报告问题"),
            ("error", "查验加载异常"),
        ):
            with self.subTest(status=status):
                st = _FakeStreamlit()
                result = {"status": status}
                _render_standard_payload_section(result, st)
                text = st.text_blob()
                self.assertIn(status, text)
                self.assertIn(label, text)

    def test_unknown_status_renders_fallback_label(self) -> None:
        st = _FakeStreamlit()
        _render_standard_payload_section({"status": "weird_new_status"}, st)
        text = st.text_blob()
        self.assertIn("weird_new_status", text)
        self.assertIn("未识别状态", text)


# ---------------------------------------------------------------------------
# 13. No mutation of input
# ---------------------------------------------------------------------------

class NoMutationTests(unittest.TestCase):
    def test_input_unchanged_after_render(self) -> None:
        st = _FakeStreamlit()
        result = _ok_inspector_result()
        result["schema_version"] = "feature_payload.v1"
        result["compatibility_mode"] = "standard"
        result["missing_sections"] = ["a"]
        result["validation_errors"] = ["err"]
        snapshot = copy.deepcopy(result)
        _render_standard_payload_section(result, st)
        self.assertEqual(result, snapshot)

    def test_compute_missing_sections_does_not_mutate_input(self) -> None:
        present = list(CONTRACT_SECTIONS[:2])
        snapshot = list(present)
        _compute_missing_sections(present)
        self.assertEqual(present, snapshot)


# ---------------------------------------------------------------------------
# 14. Pure helper does not call DB / business modules
# ---------------------------------------------------------------------------

class HelperPurityTests(unittest.TestCase):
    """The render helper should be a *pure* function over its input dict
    + the supplied ``st_obj``. It must not call the real Streamlit
    runtime, the DB, or any business module."""

    def test_render_does_not_import_predict_or_business_modules(self) -> None:
        # Ensure that calling _render_standard_payload_section with a fake
        # st_obj does not invoke any business module. We verify by
        # rendering and checking that no event indicates an unexpected
        # external call (the fake st_obj has no DB / business surface).
        st = _FakeStreamlit()
        _render_standard_payload_section(_ok_inspector_result(), st)
        # All events must come from the documented Streamlit-style calls.
        for event, _payload in st.events:
            self.assertIn(
                event,
                (
                    "markdown",
                    "caption",
                    "info",
                    "warning",
                    "json",
                    "expander_enter",
                    "expander_exit",
                ),
                msg=f"unexpected event kind from helper: {event}",
            )

    def test_render_does_not_open_files_or_db(self) -> None:
        # The helper signature is (dict, st_obj) — no path arg, no DB
        # cursor. Verify by inspecting the source for forbidden tokens.
        source = _read("ui/inspect_tab.py")
        # The helper definition must not call sqlite, prediction_store,
        # or open any file.
        helper_start = source.index(
            "def _render_standard_payload_section("
        )
        helper_end = source.index("def _render_stats_block(", helper_start)
        helper_body = source[helper_start:helper_end]
        for forbidden in (
            "sqlite3",
            "prediction_store",
            "main_projection_layer",
            "exclusion_layer",
            "confidence_evaluator",
            "final_decision",
            "run_predict",
            "open(",
        ):
            self.assertNotIn(
                forbidden,
                helper_body,
                msg=f"_render_standard_payload_section body must not contain {forbidden!r}",
            )


# ---------------------------------------------------------------------------
# 15. Module-level import boundary
# ---------------------------------------------------------------------------

class InspectTabModuleImportBoundaryTests(unittest.TestCase):
    """``ui/inspect_tab.py`` must not import any business module / DB at
    the module top level. The pre-existing pattern lazily imports
    ``streamlit`` and ``services.inspect_analysis`` inside
    ``render_inspect_tab``. PR-UI-2 must not break that pattern."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = _read("ui/inspect_tab.py")

    def test_no_predict_top_level_import(self) -> None:
        # Top-level imports are everything before the first `def render_inspect_tab(`.
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
        # Existing pattern: streamlit is imported lazily inside
        # render_inspect_tab. Top-level import of streamlit would couple
        # tab module load to Streamlit availability. Pin the pattern.
        head = self.source.split("def render_inspect_tab(")[0]
        for f in ("import streamlit", "from streamlit"):
            self.assertNotIn(
                f, head,
                msg=f"ui/inspect_tab.py must not contain top-level `{f}`",
            )

    def test_helpers_are_exported_for_testing(self) -> None:
        # Sanity: the new helpers are accessible via the module.
        self.assertTrue(hasattr(inspect_mod, "_compute_missing_sections"))
        self.assertTrue(hasattr(inspect_mod, "_render_standard_payload_section"))


# ---------------------------------------------------------------------------
# Sanity: helper module reference
# ---------------------------------------------------------------------------

class ModuleReferenceTests(unittest.TestCase):
    def test_helpers_live_in_inspect_tab_module(self) -> None:
        self.assertEqual(
            _compute_missing_sections.__module__, "ui.inspect_tab"
        )
        self.assertEqual(
            _render_standard_payload_section.__module__, "ui.inspect_tab"
        )


if __name__ == "__main__":
    unittest.main()
