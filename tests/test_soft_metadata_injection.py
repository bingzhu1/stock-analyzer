"""Tests for services/soft_metadata_injection.py (Step 2G-6B.2)."""
from __future__ import annotations

import sys
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.soft_metadata_injection import (
    _extract_regime_features,
    enrich_predict_result_with_soft_metadata,
)


# ── fixtures ────────────────────────────────────────────────────────────

def _bullish_payload(analysis_date: str = "2024-01-08") -> dict:
    """Minimal valid contract_payload structure."""
    return {
        "current_structure": {
            "symbol": "AVGO", "analysis_date": analysis_date,
            "prediction_for_date": "2024-01-09",
            "data_window_days": 20,
            "current_price": 100.0, "previous_close": 99.0,
            "volume": 1_000_000, "turnover": 1.0e8,
            "structure_label": "bullish", "short_summary": "",
        },
        "avgo_primary_projection": {
            "primary_direction": "偏多", "open_projection": "高开",
            "intraday_path_projection": "高走",
            "close_projection": "收涨", "five_state_projection": "小涨",
            "historical_sample_count": 0, "key_evidence": [],
            "primary_confidence_raw": "high",
        },
        "peer_confirmation_adjustment": {
            "peer_symbols": ["NVDA", "SOXX", "QQQ"],
            "nvda_signal": "neutral", "soxx_signal": "neutral",
            "qqq_signal": "neutral", "peer_alignment": "insufficient",
            "peer_adjustment": "upgrade", "adjusted_direction": "偏多",
            "adjustment_reason": "",
        },
        "exclusion_system": {
            "exclusion_level": "none", "exclusion_sources": [],
            "exclusion_reasons": [], "forced_exclusion": False,
            "anti_false_exclusion_triggered": False,
            "extras": {
                "conflicting_factors_count": 0, "conflicting_factors": [],
                "path_risk_level": "unknown",
                "peer_path_risk_direction": "neutral",
                "peer_path_risk_reasons": [],
                "soft_signal": "none",
            },
        },
        "confidence_system": {
            "historical_score": 0.0, "structure_score": 0.0,
            "peer_score": 0.0, "exclusion_penalty": 0.0,
            "event_score": None, "total_confidence": 0.5,
            "confidence_level": "high", "confidence_reason": "",
            "extras": {
                "primary_score_raw": 2.7,
                "primary_confidence_raw": "high",
                "peer_confirm_count": 1, "peer_oppose_count": 0,
                "peer_adjusted_confidence": "high",
                "final_confidence": "high",
                "probability_bucket": "55–70%",
                "conflicting_factors_count": 0,
                "path_risk_level": "unknown",
                "soft_signal": "none",
            },
        },
        "final_projection": {
            "final_direction": "偏多", "final_open_projection": "高开",
            "final_intraday_path": "高走", "final_close_projection": "收涨",
            "final_five_state": "小涨", "probability_bucket": "55–70%",
            "key_price_levels": {}, "final_one_sentence": "",
        },
        "simulated_trade": {
            "trade_action": "no_trade", "trade_direction": "none",
            "entry_condition": "", "stop_loss_condition": "",
            "take_profit_condition": "", "suggested_position_size": "0%",
            "no_trade_reason": "<test>",
        },
        "review_payload": {
            "prediction_id": "", "predicted_open_type": "高开",
            "predicted_path_type": "高走", "predicted_close_type": "收涨",
            "predicted_five_state": "小涨", "predicted_confidence": "high",
            "review_ready_fields": [],
        },
    }


def _predict_result(analysis_date: str = "2024-01-08") -> dict:
    return {
        "symbol": "AVGO", "analysis_date": analysis_date,
        "final_bias": "bullish", "final_confidence": "high",
        "contract_payload": _bullish_payload(analysis_date),
    }


def _r4_features() -> dict:
    return {"pos20": 0.81, "avgo_minus_soxx_20d": 7.3}


def _existing_soft_metadata() -> dict:
    return {
        "schema_version": "soft_metadata.v1",
        "metrics_source": "regime_diagnostics_dashboard_v1",
        "metrics_window": {
            "analysis_date_min": None, "analysis_date_max": None,
            "paired_total": 0, "db_snapshot_id": None,
        },
        "metrics_computed_at": "2025-12-31T00:00:00",
        "signals": [],
        "summary": {
            "has_overextension_signal": False,
            "max_severity": "none",
            "hard_exclusion_allowed": False,
            "signal_count": 0,
            "primary_signal": None,
            "warnings": ["existing_marker"],
        },
    }


# ── core helper behavior ────────────────────────────────────────────────

class InputImmutabilityTests(unittest.TestCase):
    def test_input_predict_result_is_not_mutated(self) -> None:
        pr = _predict_result()
        snapshot = deepcopy(pr)
        enrich_predict_result_with_soft_metadata(
            pr, regime_features=_r4_features(),
        )
        self.assertEqual(pr, snapshot)

    def test_returned_dict_is_distinct_from_input(self) -> None:
        pr = _predict_result()
        out = enrich_predict_result_with_soft_metadata(
            pr, regime_features=_r4_features(),
        )
        self.assertIsNot(out, pr)
        self.assertIsNot(out["contract_payload"], pr["contract_payload"])
        self.assertIsNot(
            out["contract_payload"]["exclusion_system"],
            pr["contract_payload"]["exclusion_system"],
        )

    def test_non_dict_input_returns_empty_dict(self) -> None:
        self.assertEqual(
            enrich_predict_result_with_soft_metadata("not a dict"),  # type: ignore[arg-type]
            {},
        )
        self.assertEqual(
            enrich_predict_result_with_soft_metadata(None),  # type: ignore[arg-type]
            {},
        )


class CanonicalWriteTests(unittest.TestCase):
    def test_canonical_slot_filled_after_enrichment(self) -> None:
        out = enrich_predict_result_with_soft_metadata(
            _predict_result(), regime_features=_r4_features(),
        )
        sm = out["contract_payload"]["exclusion_system"]["extras"]["soft_metadata"]
        self.assertEqual(sm["schema_version"], "soft_metadata.v1")
        self.assertFalse(sm["summary"]["hard_exclusion_allowed"])

    def test_existing_canonical_not_overwritten_by_default(self) -> None:
        pr = _predict_result()
        pr["contract_payload"]["exclusion_system"]["extras"]["soft_metadata"] = _existing_soft_metadata()
        out = enrich_predict_result_with_soft_metadata(
            pr, regime_features=_r4_features(),
        )
        sm = out["contract_payload"]["exclusion_system"]["extras"]["soft_metadata"]
        self.assertIn("existing_marker", sm["summary"]["warnings"])

    def test_force_true_overwrites_existing(self) -> None:
        pr = _predict_result()
        pr["contract_payload"]["exclusion_system"]["extras"]["soft_metadata"] = _existing_soft_metadata()
        out = enrich_predict_result_with_soft_metadata(
            pr, regime_features=_r4_features(), force=True,
        )
        sm = out["contract_payload"]["exclusion_system"]["extras"]["soft_metadata"]
        self.assertNotIn("existing_marker", sm["summary"]["warnings"])
        # Fresh enrichment should produce R4 entry
        names = [s["name"] for s in sm["signals"]]
        self.assertIn("r4_overextension", names)

    def test_missing_contract_payload_creates_layers_safely(self) -> None:
        pr = {"symbol": "AVGO"}  # no contract_payload at all
        out = enrich_predict_result_with_soft_metadata(
            pr, regime_features=_r4_features(),
            analysis_date="2024-01-08",
        )
        sm = out["contract_payload"]["exclusion_system"]["extras"]["soft_metadata"]
        self.assertEqual(sm["schema_version"], "soft_metadata.v1")
        self.assertEqual(pr, {"symbol": "AVGO"})  # input unchanged

    def test_missing_extras_creates_extras_dict(self) -> None:
        pr = {
            "contract_payload": {
                "exclusion_system": {
                    "exclusion_level": "none",
                    # no "extras" key at all
                }
            }
        }
        snapshot = deepcopy(pr)
        out = enrich_predict_result_with_soft_metadata(
            pr, regime_features=_r4_features(),
            analysis_date="2024-01-08",
        )
        self.assertIn(
            "soft_metadata",
            out["contract_payload"]["exclusion_system"]["extras"],
        )
        self.assertEqual(pr, snapshot)


# ── required fields are byte-stable ─────────────────────────────────────

class RequiredFieldsByteStableTests(unittest.TestCase):
    """The 04 / 05 / 07 required fields must NOT change under enrichment."""

    def _required_subset(self, pr: dict) -> dict:
        cp = pr["contract_payload"]
        return {
            "exclusion_required": {
                k: cp["exclusion_system"][k]
                for k in ("exclusion_level", "exclusion_sources",
                          "exclusion_reasons", "forced_exclusion",
                          "anti_false_exclusion_triggered")
            },
            "confidence_scores": {
                k: cp["confidence_system"][k]
                for k in ("historical_score", "structure_score",
                          "peer_score", "exclusion_penalty",
                          "event_score", "confidence_level",
                          "total_confidence", "confidence_reason")
            },
            "simulated_trade": dict(cp["simulated_trade"]),
            "final_projection": dict(cp["final_projection"]),
        }

    def test_exclusion_required_fields_unchanged(self) -> None:
        pr = _predict_result()
        before = self._required_subset(pr)
        out = enrich_predict_result_with_soft_metadata(
            pr, regime_features=_r4_features(),
        )
        after = self._required_subset(out)
        self.assertEqual(before, after)

    def test_existing_extras_other_keys_preserved(self) -> None:
        # The existing exclusion_system.extras has soft_signal /
        # path_risk_level etc. — they must remain after enrichment.
        pr = _predict_result()
        original_extras = dict(
            pr["contract_payload"]["exclusion_system"]["extras"]
        )
        out = enrich_predict_result_with_soft_metadata(
            pr, regime_features=_r4_features(),
        )
        out_extras = out["contract_payload"]["exclusion_system"]["extras"]
        for key, value in original_extras.items():
            self.assertEqual(out_extras[key], value)

    def test_force_does_not_touch_required_fields(self) -> None:
        pr = _predict_result()
        pr["contract_payload"]["exclusion_system"]["extras"]["soft_metadata"] = _existing_soft_metadata()
        before = self._required_subset(pr)
        out = enrich_predict_result_with_soft_metadata(
            pr, regime_features=_r4_features(), force=True,
        )
        after = self._required_subset(out)
        self.assertEqual(before, after)


# ── simulator passthrough ──────────────────────────────────────────────

class SimulatorPassthroughTests(unittest.TestCase):
    def test_baseline_passed_through(self) -> None:
        sentinel_baseline = {"metrics_source": "regime_diagnostics_dashboard_v1",
                             "marker": "test"}
        with patch(
            "services.soft_metadata_injection.simulate_soft_metadata"
        ) as sim:
            sim.return_value = {"schema_version": "soft_metadata.v1",
                                "signals": [], "summary": {
                                    "has_overextension_signal": False,
                                    "max_severity": "none",
                                    "hard_exclusion_allowed": False,
                                    "signal_count": 0,
                                    "primary_signal": None,
                                    "warnings": [],
                                }}
            enrich_predict_result_with_soft_metadata(
                _predict_result(),
                regime_features=_r4_features(),
                baseline=sentinel_baseline,
            )
        self.assertEqual(sim.call_count, 1)
        kwargs = sim.call_args.kwargs
        self.assertIs(kwargs["baseline"], sentinel_baseline)

    def test_analysis_date_passed_through(self) -> None:
        with patch(
            "services.soft_metadata_injection.simulate_soft_metadata"
        ) as sim:
            sim.return_value = {"schema_version": "soft_metadata.v1",
                                "signals": [], "summary": {
                                    "has_overextension_signal": False,
                                    "max_severity": "none",
                                    "hard_exclusion_allowed": False,
                                    "signal_count": 0,
                                    "primary_signal": None,
                                    "warnings": [],
                                }}
            enrich_predict_result_with_soft_metadata(
                _predict_result(analysis_date="2025-08-01"),
                regime_features=_r4_features(),
            )
        kwargs = sim.call_args.kwargs
        self.assertEqual(kwargs["analysis_date"], "2025-08-01")

    def test_analysis_date_override_takes_precedence(self) -> None:
        with patch(
            "services.soft_metadata_injection.simulate_soft_metadata"
        ) as sim:
            sim.return_value = {"schema_version": "soft_metadata.v1",
                                "signals": [], "summary": {
                                    "has_overextension_signal": False,
                                    "max_severity": "none",
                                    "hard_exclusion_allowed": False,
                                    "signal_count": 0,
                                    "primary_signal": None,
                                    "warnings": [],
                                }}
            enrich_predict_result_with_soft_metadata(
                _predict_result(analysis_date="2024-01-08"),
                regime_features=_r4_features(),
                analysis_date="2026-06-01",
            )
        kwargs = sim.call_args.kwargs
        self.assertEqual(kwargs["analysis_date"], "2026-06-01")

    def test_2026_analysis_date_emits_refusal_warning(self) -> None:
        out = enrich_predict_result_with_soft_metadata(
            _predict_result(analysis_date="2026-03-15"),
            regime_features=_r4_features(),
        )
        sm = out["contract_payload"]["exclusion_system"]["extras"]["soft_metadata"]
        self.assertIn("final_test_range_refusal", sm["summary"]["warnings"])
        self.assertEqual(sm["signals"], [])

    def test_final_test_cutoff_passed_through(self) -> None:
        with patch(
            "services.soft_metadata_injection.simulate_soft_metadata"
        ) as sim:
            sim.return_value = {"schema_version": "soft_metadata.v1",
                                "signals": [], "summary": {
                                    "has_overextension_signal": False,
                                    "max_severity": "none",
                                    "hard_exclusion_allowed": False,
                                    "signal_count": 0,
                                    "primary_signal": None,
                                    "warnings": [],
                                }}
            enrich_predict_result_with_soft_metadata(
                _predict_result(),
                regime_features=_r4_features(),
                final_test_cutoff="2025-01-01",
            )
        kwargs = sim.call_args.kwargs
        self.assertEqual(kwargs["final_test_cutoff"], "2025-01-01")


# ── regime_features extraction ─────────────────────────────────────────

class RegimeFeaturesExtractionTests(unittest.TestCase):
    def test_explicit_kwarg_wins_over_predict_result(self) -> None:
        pr = _predict_result()
        pr["regime_features"] = {"pos20": 0.5, "avgo_minus_soxx_20d": 1.0}
        with patch(
            "services.soft_metadata_injection.simulate_soft_metadata"
        ) as sim:
            sim.return_value = {"schema_version": "soft_metadata.v1",
                                "signals": [], "summary": {
                                    "has_overextension_signal": False,
                                    "max_severity": "none",
                                    "hard_exclusion_allowed": False,
                                    "signal_count": 0,
                                    "primary_signal": None,
                                    "warnings": [],
                                }}
            enrich_predict_result_with_soft_metadata(
                pr, regime_features=_r4_features(),
            )
        self.assertEqual(
            sim.call_args.kwargs["regime_features"],
            _r4_features(),
        )

    def test_predict_result_top_level_fallback(self) -> None:
        pr = _predict_result()
        pr["regime_features"] = _r4_features()
        out = enrich_predict_result_with_soft_metadata(pr)
        sm = out["contract_payload"]["exclusion_system"]["extras"]["soft_metadata"]
        names = [s["name"] for s in sm["signals"]]
        self.assertIn("r4_overextension", names)

    def test_contract_extras_regime_features_fallback(self) -> None:
        pr = _predict_result()
        pr["contract_payload"]["exclusion_system"]["extras"]["regime_features"] = _r4_features()
        out = enrich_predict_result_with_soft_metadata(pr)
        sm = out["contract_payload"]["exclusion_system"]["extras"]["soft_metadata"]
        names = [s["name"] for s in sm["signals"]]
        self.assertIn("r4_overextension", names)

    def test_scan_result_regime_features_fallback(self) -> None:
        pr = _predict_result()
        scan = {"regime_features": _r4_features()}
        out = enrich_predict_result_with_soft_metadata(pr, scan_result=scan)
        sm = out["contract_payload"]["exclusion_system"]["extras"]["soft_metadata"]
        names = [s["name"] for s in sm["signals"]]
        self.assertIn("r4_overextension", names)

    def test_scan_result_extras_regime_features_fallback(self) -> None:
        pr = _predict_result()
        scan = {"extras": {"regime_features": _r4_features()}}
        out = enrich_predict_result_with_soft_metadata(pr, scan_result=scan)
        sm = out["contract_payload"]["exclusion_system"]["extras"]["soft_metadata"]
        names = [s["name"] for s in sm["signals"]]
        self.assertIn("r4_overextension", names)

    def test_no_features_anywhere_yields_empty_signals_with_warning(self) -> None:
        out = enrich_predict_result_with_soft_metadata(_predict_result())
        sm = out["contract_payload"]["exclusion_system"]["extras"]["soft_metadata"]
        self.assertEqual(sm["signals"], [])
        self.assertTrue(any(
            "missing_regime_features" in w
            for w in sm["summary"]["warnings"]
        ))

    def test_extract_regime_features_search_order(self) -> None:
        # Direct unit test on the helper.
        pr = {"regime_features": {"a": 1}}
        scan = {"regime_features": {"b": 2}}
        self.assertEqual(_extract_regime_features(pr, scan), {"a": 1})

        pr2 = {
            "contract_payload": {
                "exclusion_system": {
                    "extras": {"regime_features": {"c": 3}}
                }
            }
        }
        self.assertEqual(_extract_regime_features(pr2, None), {"c": 3})

        scan_only = {"extras": {"regime_features": {"d": 4}}}
        self.assertEqual(_extract_regime_features({}, scan_only), {"d": 4})

        self.assertIsNone(_extract_regime_features({}, None))


# ── isolation: no DB / no baseline build / no network / no trading ───

class IsolationTests(unittest.TestCase):
    def test_does_not_call_build_soft_metadata_baseline(self) -> None:
        with patch(
            "services.soft_metadata_simulator.build_soft_metadata_baseline"
        ) as bs:
            enrich_predict_result_with_soft_metadata(
                _predict_result(), regime_features=_r4_features(),
            )
        bs.assert_not_called()

    def test_does_not_call_prediction_store(self) -> None:
        with patch("services.prediction_store.save_prediction") as sp, \
             patch("services.prediction_store._get_conn") as gc:
            enrich_predict_result_with_soft_metadata(
                _predict_result(), regime_features=_r4_features(),
            )
        sp.assert_not_called()
        gc.assert_not_called()

    def test_module_does_not_import_forbidden(self) -> None:
        import ast
        import services.soft_metadata_injection as mod
        tree = ast.parse(Path(mod.__file__).read_text(encoding="utf-8"))
        forbidden_modules = {
            "yfinance", "requests",
            "longbridge", "broker", "paper_trade",
            "sqlite3",
            "services.prediction_store",
            "services.regime_diagnostics_dashboard",  # baseline build path
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


if __name__ == "__main__":
    unittest.main()
