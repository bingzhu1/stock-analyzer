"""Tests for ``services.feature_payload_adapter`` (Step 18K /
PR-FEATURE-2).

Spec source of truth:

- `tasks/record_1_0_architecture_reset_canonical_principles.md` §8 (Branch 2)
- `tasks/record_17f_feature_layer_rebuild_plan.md` §6 / §13
- `tasks/record_18a_first_layer_based_implementation_batch_selection.md` §13
- `tasks/record_18j_second_layer_based_implementation_batch_selection.md` §7 / §8

PR-FEATURE-2 is a **pure addition** — a new adapter that wires PR-FEATURE-1
(``feature_payload.v1`` validator) into a callable shape. It is not yet
called by any active path. This suite verifies:

1.  ``build_feature_payload_from_parts`` returns dict with ``"payload"``
    and ``"validation_errors"`` keys
2.  valid parts produce a valid ``feature_payload.v1`` and
    ``validation_errors == []``
3.  ``payload.metadata`` contains the 6 required metadata keys with the
    caller-supplied values
4.  the assembled payload passes ``validate_feature_payload``
5.  ``data_window_days != 15`` is passed through unchanged and surfaces
    in ``validation_errors`` as a ``"warning:"`` line
6.  invalid ``price_basis`` is passed through unchanged and surfaces in
    ``validation_errors``
7.  missing ``returns`` required key surfaces in ``validation_errors``
8.  no mutation of input sections (caller-side dicts / lists unchanged
    after the call)
9.  the returned payload deep-copies mutable inputs (mutating returned
    payload does not affect caller-side inputs)
10. adapter does not add forbidden result sections at top level
11. adapter does not add trading / hard / forced fields at top level
12. adapter does not compute returns
13. adapter does not compute position
14. adapter does not compute volume_ratio
15. adapter does not compute peer_alignment
16. module import boundary: the adapter does not import yfinance /
    pandas / sqlite / feature_builder / encoder / scanner / matcher /
    peer_alignment / main_projection_layer / exclusion_layer /
    confidence_evaluator / final_decision / predict / app / ui /
    orchestrator
"""

from __future__ import annotations

import copy
import unittest
from pathlib import Path

import services.feature_payload_adapter as adapter_mod
from services.feature_payload_adapter import build_feature_payload_from_parts
from services.feature_payload_contract import (
    FEATURE_PAYLOAD_SCHEMA_VERSION,
    FEATURE_PAYLOAD_SECTIONS,
    validate_feature_payload,
)


_REPO_ROOT = Path(__file__).resolve().parent.parent


def _read(rel: str) -> str:
    return (_REPO_ROOT / rel).read_text(encoding="utf-8")


def _valid_parts() -> dict:
    """Return a kwargs dict that, when splatted, makes a valid payload."""
    return {
        "symbol": "AVGO",
        "analysis_date": "2026-05-08",
        "target_date": "2026-05-09",
        "data_window_days": 15,
        "window_label": "T-15..T-1",
        "price_basis": "raw",
        "ohlcv_window": [
            {"Date": "2026-05-08", "Open": 100.0, "High": 101.0,
             "Low": 99.5, "Close": 100.5, "Adj Close": 100.5, "Volume": 1000},
        ],
        "returns": {
            "ret1": 0.005,
            "ret3": 0.012,
            "ret5": 0.020,
            "ret10": 0.030,
        },
        "position": {
            "pos15": 0.5,
            "pos20": 0.5,
            "pos30": 0.5,
        },
        "volume": {
            "volume": 1000,
            "volume_ratio": 1.05,
        },
        "candle": {
            "upper_shadow_ratio": 0.10,
            "lower_shadow_ratio": 0.05,
        },
        "peer_alignment": {
            "alignment": "neutral",
            "available_peer_count": 3,
        },
        "code_features": {
            "Code": "44222",
        },
        "data_quality": {
            "missing_fields": [],
            "source": "local_csv",
            "stale_flag": False,
        },
    }


# ---------------------------------------------------------------------------
# 1. Returns dict with payload and validation_errors keys
# ---------------------------------------------------------------------------

class ReturnShapeTests(unittest.TestCase):
    def test_return_is_dict(self) -> None:
        result = build_feature_payload_from_parts(**_valid_parts())
        self.assertIsInstance(result, dict)

    def test_return_has_payload_and_validation_errors_keys(self) -> None:
        result = build_feature_payload_from_parts(**_valid_parts())
        self.assertIn("payload", result)
        self.assertIn("validation_errors", result)

    def test_validation_errors_is_list(self) -> None:
        result = build_feature_payload_from_parts(**_valid_parts())
        self.assertIsInstance(result["validation_errors"], list)


# ---------------------------------------------------------------------------
# 2. Valid parts produce valid payload and empty validation_errors
# ---------------------------------------------------------------------------

class ValidPartsTests(unittest.TestCase):
    def test_valid_parts_produce_empty_validation_errors(self) -> None:
        result = build_feature_payload_from_parts(**_valid_parts())
        self.assertEqual(
            result["validation_errors"],
            [],
            msg=f"unexpected validation_errors: {result['validation_errors']}",
        )

    def test_payload_schema_version_is_v1(self) -> None:
        result = build_feature_payload_from_parts(**_valid_parts())
        self.assertEqual(
            result["payload"]["schema_version"], FEATURE_PAYLOAD_SCHEMA_VERSION
        )
        self.assertEqual(
            result["payload"]["schema_version"], "feature_payload.v1"
        )

    def test_payload_has_all_ten_top_level_sections(self) -> None:
        result = build_feature_payload_from_parts(**_valid_parts())
        for section in FEATURE_PAYLOAD_SECTIONS:
            with self.subTest(section=section):
                self.assertIn(section, result["payload"])


# ---------------------------------------------------------------------------
# 3. metadata contains 6 required keys with caller-supplied values
# ---------------------------------------------------------------------------

class MetadataKeysTests(unittest.TestCase):
    def test_metadata_contains_six_required_keys(self) -> None:
        parts = _valid_parts()
        result = build_feature_payload_from_parts(**parts)
        metadata = result["payload"]["metadata"]
        for key in (
            "symbol",
            "analysis_date",
            "target_date",
            "data_window_days",
            "window_label",
            "price_basis",
        ):
            with self.subTest(key=key):
                self.assertIn(key, metadata)

    def test_metadata_values_match_caller_inputs(self) -> None:
        parts = _valid_parts()
        result = build_feature_payload_from_parts(**parts)
        metadata = result["payload"]["metadata"]
        self.assertEqual(metadata["symbol"], parts["symbol"])
        self.assertEqual(metadata["analysis_date"], parts["analysis_date"])
        self.assertEqual(metadata["target_date"], parts["target_date"])
        self.assertEqual(metadata["data_window_days"], parts["data_window_days"])
        self.assertEqual(metadata["window_label"], parts["window_label"])
        self.assertEqual(metadata["price_basis"], parts["price_basis"])


# ---------------------------------------------------------------------------
# 4. Output payload passes validate_feature_payload
# ---------------------------------------------------------------------------

class ValidatorRoundTripTests(unittest.TestCase):
    def test_assembled_payload_passes_validator(self) -> None:
        result = build_feature_payload_from_parts(**_valid_parts())
        # Direct call of validator on the returned payload should match
        # the embedded validation_errors list.
        direct = validate_feature_payload(result["payload"])
        self.assertEqual(direct, result["validation_errors"])
        self.assertEqual(direct, [])


# ---------------------------------------------------------------------------
# 5. data_window_days != 15 surfaces in validation_errors as a warning
# ---------------------------------------------------------------------------

class DataWindowDaysAdvisoryTests(unittest.TestCase):
    def test_data_window_days_20_emits_warning_through_adapter(self) -> None:
        parts = _valid_parts()
        parts["data_window_days"] = 20
        result = build_feature_payload_from_parts(**parts)
        # Adapter must NOT auto-correct.
        self.assertEqual(result["payload"]["metadata"]["data_window_days"], 20)
        warnings = [
            e for e in result["validation_errors"]
            if e.startswith("warning: metadata.data_window_days")
        ]
        self.assertEqual(len(warnings), 1)


# ---------------------------------------------------------------------------
# 6. Invalid price_basis surfaces in validation_errors
# ---------------------------------------------------------------------------

class PriceBasisErrorPropagationTests(unittest.TestCase):
    def test_invalid_price_basis_surfaces_in_validation_errors(self) -> None:
        parts = _valid_parts()
        parts["price_basis"] = "BAD_BASIS"
        result = build_feature_payload_from_parts(**parts)
        # Adapter must NOT normalize.
        self.assertEqual(
            result["payload"]["metadata"]["price_basis"], "BAD_BASIS"
        )
        matches = [
            e for e in result["validation_errors"]
            if e.startswith("invalid value: metadata.price_basis")
        ]
        self.assertEqual(len(matches), 1)


# ---------------------------------------------------------------------------
# 7. Missing returns key causes validation_errors
# ---------------------------------------------------------------------------

class MissingReturnsKeyTests(unittest.TestCase):
    def test_missing_ret1_surfaces_in_validation_errors(self) -> None:
        parts = _valid_parts()
        parts["returns"] = {
            "ret3": 0.012,
            "ret5": 0.020,
            "ret10": 0.030,
        }
        result = build_feature_payload_from_parts(**parts)
        self.assertIn(
            "missing field: returns.ret1",
            result["validation_errors"],
        )


# ---------------------------------------------------------------------------
# 8. No mutation of input sections
# ---------------------------------------------------------------------------

class NoMutationOfInputTests(unittest.TestCase):
    def test_inputs_unchanged_after_call(self) -> None:
        parts = _valid_parts()
        snapshot = copy.deepcopy(parts)
        build_feature_payload_from_parts(**parts)
        self.assertEqual(parts, snapshot)


# ---------------------------------------------------------------------------
# 9. Returned payload deep-copies mutable inputs
# ---------------------------------------------------------------------------

class DeepCopyTests(unittest.TestCase):
    def test_mutating_returned_payload_does_not_affect_inputs(self) -> None:
        parts = _valid_parts()
        result = build_feature_payload_from_parts(**parts)
        # Mutate every mutable section in the returned payload.
        result["payload"]["ohlcv_window"].append(
            {"Date": "ZZZ", "Open": -1, "High": -1, "Low": -1,
             "Close": -1, "Adj Close": -1, "Volume": 0}
        )
        result["payload"]["returns"]["ret1"] = 999.0
        result["payload"]["position"]["pos15"] = 999.0
        result["payload"]["volume"]["volume"] = 999
        result["payload"]["candle"]["upper_shadow_ratio"] = 999.0
        result["payload"]["peer_alignment"]["alignment"] = "MUTATED"
        result["payload"]["code_features"]["Code"] = "MUTATED"
        result["payload"]["data_quality"]["stale_flag"] = "MUTATED"

        # Inputs must remain unchanged.
        self.assertEqual(len(parts["ohlcv_window"]), 1)
        self.assertEqual(parts["returns"]["ret1"], 0.005)
        self.assertEqual(parts["position"]["pos15"], 0.5)
        self.assertEqual(parts["volume"]["volume"], 1000)
        self.assertEqual(parts["candle"]["upper_shadow_ratio"], 0.10)
        self.assertEqual(parts["peer_alignment"]["alignment"], "neutral")
        self.assertEqual(parts["code_features"]["Code"], "44222")
        self.assertEqual(parts["data_quality"]["stale_flag"], False)

    def test_each_section_has_its_own_object_identity(self) -> None:
        parts = _valid_parts()
        result = build_feature_payload_from_parts(**parts)
        for key in (
            "ohlcv_window",
            "returns",
            "position",
            "volume",
            "candle",
            "peer_alignment",
            "code_features",
            "data_quality",
        ):
            with self.subTest(key=key):
                self.assertIsNot(
                    result["payload"][key],
                    parts[key],
                    msg=f"adapter did not deep-copy {key}",
                )


# ---------------------------------------------------------------------------
# 10. Adapter does not add forbidden result sections at top level
# ---------------------------------------------------------------------------

class ForbiddenResultSectionsTests(unittest.TestCase):
    def test_no_forbidden_result_sections_at_top_level(self) -> None:
        result = build_feature_payload_from_parts(**_valid_parts())
        for forbidden in (
            "projection_result",
            "exclusion_result",
            "confidence_result",
            "final_report",
            "review_result",
            "evaluation_result",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(
                    forbidden,
                    result["payload"],
                    msg=f"adapter accidentally added {forbidden!r} at top level",
                )


# ---------------------------------------------------------------------------
# 11. Adapter does not add trading / hard / forced fields at top level
# ---------------------------------------------------------------------------

class ForbiddenTradingForcedFieldsTests(unittest.TestCase):
    def test_no_forbidden_trading_or_forced_at_top_level(self) -> None:
        result = build_feature_payload_from_parts(**_valid_parts())
        for forbidden in (
            "trading_action",
            "order",
            "position_action",
            "execution",
            "buy",
            "sell",
            "hold",
            "hard",
            "forced",
            "required",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(
                    forbidden,
                    result["payload"],
                    msg=f"adapter accidentally added {forbidden!r} at top level",
                )


# ---------------------------------------------------------------------------
# 12. Adapter does not compute returns
# ---------------------------------------------------------------------------

class NoReturnsComputationTests(unittest.TestCase):
    def test_returns_section_passed_through_unchanged(self) -> None:
        parts = _valid_parts()
        custom_returns = {
            "ret1": 99.0,
            "ret3": 99.0,
            "ret5": 99.0,
            "ret10": 99.0,
        }
        parts["returns"] = copy.deepcopy(custom_returns)
        result = build_feature_payload_from_parts(**parts)
        self.assertEqual(result["payload"]["returns"], custom_returns)

    def test_unknown_returns_keys_are_passed_through(self) -> None:
        # Adapter must NOT strip extra keys; validator decides whether they
        # are allowed.
        parts = _valid_parts()
        parts["returns"]["ret_custom"] = 0.12345
        result = build_feature_payload_from_parts(**parts)
        self.assertEqual(result["payload"]["returns"]["ret_custom"], 0.12345)


# ---------------------------------------------------------------------------
# 13. Adapter does not compute position
# ---------------------------------------------------------------------------

class NoPositionComputationTests(unittest.TestCase):
    def test_position_section_passed_through_unchanged(self) -> None:
        parts = _valid_parts()
        custom_position = {
            "pos15": 99.0,
            "pos20": 99.0,
            "pos30": 99.0,
        }
        parts["position"] = copy.deepcopy(custom_position)
        result = build_feature_payload_from_parts(**parts)
        self.assertEqual(result["payload"]["position"], custom_position)


# ---------------------------------------------------------------------------
# 14. Adapter does not compute volume_ratio
# ---------------------------------------------------------------------------

class NoVolumeRatioComputationTests(unittest.TestCase):
    def test_volume_section_passed_through_unchanged(self) -> None:
        parts = _valid_parts()
        custom_volume = {
            "volume": 999_999,
            "volume_ratio": 99.0,
        }
        parts["volume"] = copy.deepcopy(custom_volume)
        result = build_feature_payload_from_parts(**parts)
        self.assertEqual(result["payload"]["volume"], custom_volume)


# ---------------------------------------------------------------------------
# 15. Adapter does not compute peer_alignment
# ---------------------------------------------------------------------------

class NoPeerAlignmentComputationTests(unittest.TestCase):
    def test_peer_alignment_section_passed_through_unchanged(self) -> None:
        parts = _valid_parts()
        custom_peer = {
            "alignment": "bullish",
            "up_support": "supported",
            "available_peer_count": 0,
            "peer_returns": {"NVDA": None, "SOXX": None, "QQQ": None},
        }
        parts["peer_alignment"] = copy.deepcopy(custom_peer)
        result = build_feature_payload_from_parts(**parts)
        self.assertEqual(result["payload"]["peer_alignment"], custom_peer)

    def test_empty_peer_alignment_is_passed_through(self) -> None:
        parts = _valid_parts()
        parts["peer_alignment"] = {}
        result = build_feature_payload_from_parts(**parts)
        self.assertEqual(result["payload"]["peer_alignment"], {})


# ---------------------------------------------------------------------------
# 16. Module import boundary
# ---------------------------------------------------------------------------

class ImportBoundaryTests(unittest.TestCase):
    """``services.feature_payload_adapter`` must remain a pure assembler
    with zero coupling to data-fetch / business / orchestrator / UI / DB
    modules. The only allowed cross-module reference is
    ``services.feature_payload_contract``."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = _read("services/feature_payload_adapter.py")

    def test_no_data_fetch_or_dataframe_imports(self) -> None:
        forbidden = (
            "import yfinance",
            "from yfinance",
            "import pandas",
            "from pandas",
            "import sqlite3",
            "from sqlite3",
        )
        for f in forbidden:
            self.assertNotIn(
                f,
                self.source,
                msg=f"services.feature_payload_adapter must not contain `{f}`",
            )

    def test_no_root_feature_module_imports(self) -> None:
        # Root-level Feature Layer modules must not be imported by the
        # adapter (encoder.py / scanner.py / matcher.py / feature_builder.py
        # are 1.0 §13 hard-rule modules; data_fetcher.py is the only
        # external-data entry).
        forbidden = (
            "import feature_builder",
            "from feature_builder",
            "import encoder",
            "from encoder",
            "import scanner",
            "from scanner",
            "import matcher",
            "from matcher",
            "import data_fetcher",
            "from data_fetcher",
        )
        for f in forbidden:
            self.assertNotIn(
                f,
                self.source,
                msg=f"services.feature_payload_adapter must not contain `{f}`",
            )

    def test_no_business_module_imports(self) -> None:
        forbidden = (
            "from services.peer_alignment",
            "import services.peer_alignment",
            "from services.data_query",
            "import services.data_query",
            "from services.features_20d",
            "import services.features_20d",
            "from services.regime_features_builder",
            "import services.regime_features_builder",
            "from services.regime_labels_builder",
            "import services.regime_labels_builder",
            "from services.projection_chain_contract",
            "import services.projection_chain_contract",
            "from services.main_projection_layer",
            "import services.main_projection_layer",
            "from services.exclusion_layer",
            "import services.exclusion_layer",
            "from services.confidence_evaluator",
            "import services.confidence_evaluator",
            "from services.final_decision",
            "import services.final_decision",
            "from services.consistency_layer",
            "import services.consistency_layer",
            "from services.review_orchestrator",
            "import services.review_orchestrator",
            "from services.projection_orchestrator",
            "import services.projection_orchestrator",
            "from services.projection_orchestrator_v2",
            "import services.projection_orchestrator_v2",
            "from services.projection_entrypoint",
            "import services.projection_entrypoint",
            "from services.projection_v2_adapter",
            "import services.projection_v2_adapter",
            "from services.home_terminal_orchestrator",
            "import services.home_terminal_orchestrator",
            "from services.predict_legacy_adapter",
            "import services.predict_legacy_adapter",
            "from services.predict_legacy_v2_bridge",
            "import services.predict_legacy_v2_bridge",
        )
        for f in forbidden:
            self.assertNotIn(
                f,
                self.source,
                msg=f"services.feature_payload_adapter must not contain `{f}`",
            )

    def test_no_predict_app_ui_imports(self) -> None:
        forbidden = (
            "import predict",
            "from predict",
            "import app",
            "from app",
            "import ui",
            "from ui",
            "import streamlit",
            "from streamlit",
        )
        for f in forbidden:
            self.assertNotIn(
                f,
                self.source,
                msg=f"services.feature_payload_adapter must not contain `{f}`",
            )

    def test_no_io_or_llm_calls(self) -> None:
        for f in ("open(", "Path(", "requests.", "urllib", "http.client",
                  "openai", "OpenAI", "anthropic", "Anthropic"):
            self.assertNotIn(
                f,
                self.source,
                msg=f"services.feature_payload_adapter must not contain `{f}`",
            )


# ---------------------------------------------------------------------------
# Sanity check on module reference
# ---------------------------------------------------------------------------

class ModuleReferenceTests(unittest.TestCase):
    def test_function_lives_in_module(self) -> None:
        self.assertEqual(
            build_feature_payload_from_parts.__module__,
            "services.feature_payload_adapter",
        )
        self.assertIs(
            adapter_mod.build_feature_payload_from_parts,
            build_feature_payload_from_parts,
        )


if __name__ == "__main__":
    unittest.main()
