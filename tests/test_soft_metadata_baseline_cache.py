"""Tests for ui/soft_metadata_baseline_cache.py (Step 2G-6B.6)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.soft_metadata_baseline_cache import (
    CACHE_KEY,
    ERROR_KEY,
    ensure_soft_metadata_baseline_cached,
)


def _stub_baseline() -> dict:
    return {
        "metrics_source": "regime_diagnostics_dashboard_v1",
        "metrics_window": {
            "analysis_date_min": "2023-01-03",
            "analysis_date_max": "2024-08-02",
            "paired_total": 286, "db_snapshot_id": None,
        },
        "metrics_computed_at": "2026-05-04T00:00:00",
        "r4_overextension": {
            "samples": 36, "paired": 34,
            "accuracy": 0.324, "bias_gap": 0.676,
            "false_exclusion_rate": 0.3235, "net_benefit": 0.0219,
        },
        "bullish_high_pos20_residual": {
            "samples": 47, "paired": 47,
            "accuracy": 0.489, "bias_gap": 0.511,
            "false_exclusion_rate": 0.489, "net_benefit": -0.001,
        },
        "holdout_status": "FAIL",
        "warnings": [],
    }


class CacheBehaviorTests(unittest.TestCase):
    def test_cache_miss_calls_builder_and_stores_result(self) -> None:
        state: dict = {}
        with patch(
            "ui.soft_metadata_baseline_cache.build_soft_metadata_baseline",
            return_value=_stub_baseline(),
        ) as mock_build:
            result = ensure_soft_metadata_baseline_cached(session_state=state)
        mock_build.assert_called_once()
        self.assertIs(result, state[CACHE_KEY])
        self.assertEqual(result["metrics_source"], "regime_diagnostics_dashboard_v1")

    def test_cache_hit_does_not_call_builder(self) -> None:
        state = {CACHE_KEY: _stub_baseline()}
        with patch(
            "ui.soft_metadata_baseline_cache.build_soft_metadata_baseline",
            return_value=_stub_baseline(),
        ) as mock_build:
            result = ensure_soft_metadata_baseline_cached(session_state=state)
        mock_build.assert_not_called()
        self.assertIs(result, state[CACHE_KEY])

    def test_builder_exception_records_error_and_returns_none(self) -> None:
        state: dict = {}
        with patch(
            "ui.soft_metadata_baseline_cache.build_soft_metadata_baseline",
            side_effect=RuntimeError("db unavailable"),
        ):
            result = ensure_soft_metadata_baseline_cached(session_state=state)
        self.assertIsNone(result)
        self.assertNotIn(CACHE_KEY, state)
        self.assertIn(ERROR_KEY, state)
        self.assertIn("db unavailable", state[ERROR_KEY])

    def test_non_dict_builder_return_does_not_cache(self) -> None:
        state: dict = {}
        with patch(
            "ui.soft_metadata_baseline_cache.build_soft_metadata_baseline",
            return_value="not a dict",
        ):
            result = ensure_soft_metadata_baseline_cached(session_state=state)
        self.assertIsNone(result)
        self.assertNotIn(CACHE_KEY, state)

    def test_session_state_none_outside_streamlit_does_not_crash(self) -> None:
        # When called without a Streamlit context AND no explicit
        # session_state, the helper should still return a baseline (no
        # caching) without crashing.
        with patch(
            "ui.soft_metadata_baseline_cache._resolve_session_state",
            return_value=None,
        ), patch(
            "ui.soft_metadata_baseline_cache.build_soft_metadata_baseline",
            return_value=_stub_baseline(),
        ) as mock_build:
            result = ensure_soft_metadata_baseline_cached()
        self.assertIsNotNone(result)
        mock_build.assert_called_once()

    def test_symbol_and_limit_passed_to_builder(self) -> None:
        state: dict = {}
        with patch(
            "ui.soft_metadata_baseline_cache.build_soft_metadata_baseline",
            return_value=_stub_baseline(),
        ) as mock_build:
            ensure_soft_metadata_baseline_cached(
                symbol="NVDA", limit=100, session_state=state,
            )
        kwargs = mock_build.call_args.kwargs
        self.assertEqual(kwargs["symbol"], "NVDA")
        self.assertEqual(kwargs["limit"], 100)


class IsolationTests(unittest.TestCase):
    def test_module_does_not_import_forbidden(self) -> None:
        import ast
        import ui.soft_metadata_baseline_cache as mod
        tree = ast.parse(Path(mod.__file__).read_text(encoding="utf-8"))
        forbidden_modules = {
            "yfinance", "requests",
            "longbridge", "broker", "paper_trade",
            "sqlite3",
            "services.prediction_store",
            "services.confidence_engine",
            "services.contradiction_engine",
            "services.risk_model",
            "confidence_engine", "contradiction_engine", "risk_model",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn(alias.name, forbidden_modules)
            elif isinstance(node, ast.ImportFrom):
                self.assertNotIn(node.module, forbidden_modules)

    def test_does_not_call_prediction_store_directly(self) -> None:
        state: dict = {}
        with patch(
            "ui.soft_metadata_baseline_cache.build_soft_metadata_baseline",
            return_value=_stub_baseline(),
        ), patch("services.prediction_store.save_prediction") as sp, \
             patch("services.prediction_store._get_conn") as gc:
            ensure_soft_metadata_baseline_cached(session_state=state)
        sp.assert_not_called()
        gc.assert_not_called()


if __name__ == "__main__":
    unittest.main()
