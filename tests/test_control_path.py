from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.agent_parser import ModelBackedCommandParser, ModelParserRequest, parse_agent_command
from services.agent_schema import MODEL_COMMAND_JSON_SCHEMA, coerce_model_command

try:
    import pandas as pd
    from services.query_executor import AnalysisContext, execute_agent_command
except ModuleNotFoundError:
    pd = None
    AnalysisContext = None
    execute_agent_command = None

HAS_PANDAS = pd is not None


class StaticModelProvider:
    def __init__(self, payload):
        self.payload = payload
        self.requests: list[ModelParserRequest] = []

    def build_command_payload(self, request: ModelParserRequest):
        self.requests.append(request)
        return self.payload


def _sample_context(scan_result: dict | None = None) -> AnalysisContext:
    assert pd is not None
    assert AnalysisContext is not None
    exact_df = pd.DataFrame(
        [
            {
                "MatchType": "exact",
                "MatchDate": "2025-01-02",
                "MatchCode": "33345",
                "ContextScore": 82.0,
                "ContextLabel": "高相似",
                "NextCloseMove": 0.031,
            },
            {
                "MatchType": "exact",
                "MatchDate": "2025-02-03",
                "MatchCode": "33345",
                "ContextScore": 41.0,
                "ContextLabel": "中相似",
                "NextCloseMove": -0.012,
            },
        ]
    )
    near_df = pd.DataFrame(
        [
            {
                "MatchType": "near",
                "MatchDate": "2025-03-04",
                "MatchCode": "33344",
                "ContextScore": 67.0,
                "ContextLabel": "高相似",
                "NextCloseMove": 0.005,
                "VCodeDiff": 1,
            }
        ]
    )
    return AnalysisContext(
        target_date_str="2026-04-08",
        scan_result=scan_result,
        exact_df=exact_df,
        near_df=near_df,
        summary_df=pd.DataFrame(),
        disp_exact_df=exact_df,
        disp_near_df=near_df,
    )


class ControlPathTests(unittest.TestCase):
    def test_parser_maps_top_high_similarity(self) -> None:
        command = parse_agent_command("show top 10 high similarity samples")
        self.assertEqual(command.action, "show_matches")
        self.assertEqual(command.limit, 10)
        self.assertEqual(command.sort_by, "ContextScore")
        self.assertEqual(command.sort_dir, "desc")
        self.assertEqual(command.filters[0].field, "ContextLabel")
        self.assertEqual(command.filters[0].value, "高相似")

    def test_parser_maps_compare(self) -> None:
        command = parse_agent_command("compare exact and near matches")
        self.assertEqual(command.action, "compare_matches")
        self.assertEqual(command.dataset, "all")

    def test_schema_exposes_structured_output_contract(self) -> None:
        action_schema = MODEL_COMMAND_JSON_SCHEMA["properties"]["action"]
        self.assertIn("show_matches", action_schema["enum"])
        self.assertIn("unsupported", action_schema["enum"])

    def test_parser_marks_unsupported_prediction_request(self) -> None:
        command = parse_agent_command("predict tomorrow and tell me whether to buy")
        self.assertEqual(command.action, "unsupported")
        self.assertIn("outside", command.reason or "")

    def test_parser_marks_ambiguous_request_unsupported(self) -> None:
        command = parse_agent_command("do something smart with this")
        self.assertEqual(command.action, "unsupported")
        self.assertIn("could not map", command.reason or "")

    def test_model_command_coercion_accepts_valid_output(self) -> None:
        command = coerce_model_command(
            {
                "action": "show_matches",
                "dataset": "near",
                "filters": [{"field": "ContextLabel", "op": "eq", "value": "高相似"}],
                "sort_by": "ContextScore",
                "sort_dir": "desc",
                "limit": 7,
                "group_by": None,
            },
            raw_text="model output",
        )
        self.assertEqual(command.action, "show_matches")
        self.assertEqual(command.dataset, "near")
        self.assertEqual(command.limit, 7)

    def test_model_parser_uses_valid_model_output(self) -> None:
        provider = StaticModelProvider(
            {
                "action": "group_matches",
                "dataset": "all",
                "filters": [],
                "sort_by": None,
                "sort_dir": "desc",
                "limit": 10,
                "group_by": "ContextLabel",
            }
        )
        parser = ModelBackedCommandParser(
            provider=provider
        )
        command = parser.parse("please organize this")
        self.assertEqual(command.action, "group_matches")
        self.assertEqual(command.dataset, "all")
        self.assertEqual(command.group_by, "ContextLabel")
        self.assertEqual(provider.requests[0].text, "please organize this")
        self.assertIn("properties", provider.requests[0].command_schema)
        self.assertIn("Supported read-only commands", provider.requests[0].command_help)

    def test_model_parser_falls_back_on_invalid_output(self) -> None:
        parser = ModelBackedCommandParser(
            provider=StaticModelProvider(
                {
                    "action": "show_matches",
                    "dataset": "current",
                    "filters": [],
                    "sort_by": "NotAColumn",
                    "sort_dir": "desc",
                    "limit": 10,
                    "group_by": None,
                }
            )
        )
        command = parser.parse("summarize the current scan result")
        self.assertEqual(command.action, "summarize_scan")

    def test_model_parser_falls_back_on_partial_output(self) -> None:
        parser = ModelBackedCommandParser(provider=StaticModelProvider({"action": "show_matches"}))
        command = parser.parse("show top 10 high similarity samples")
        self.assertEqual(command.action, "show_matches")
        self.assertEqual(command.limit, 10)

    def test_model_parser_falls_back_on_unsupported_output(self) -> None:
        parser = ModelBackedCommandParser(
            provider=StaticModelProvider(
                {
                    "action": "unsupported",
                    "dataset": "current",
                    "filters": [],
                    "sort_by": None,
                    "sort_dir": "desc",
                    "limit": 10,
                    "group_by": None,
                    "reason": "model could not decide",
                }
            )
        )
        command = parser.parse("explain the current bias")
        self.assertEqual(command.action, "explain_bias")

    def test_model_parser_falls_back_when_provider_raises(self) -> None:
        class RaisingProvider:
            def build_command_payload(self, request: ModelParserRequest) -> dict:
                raise RuntimeError("provider failed")

        parser = ModelBackedCommandParser(provider=RaisingProvider())
        command = parser.parse("compare exact and near matches")
        self.assertEqual(command.action, "compare_matches")

    def test_model_parser_falls_back_on_action_shape_error(self) -> None:
        parser = ModelBackedCommandParser(
            provider=StaticModelProvider(
                {
                    "action": "group_matches",
                    "dataset": "current",
                    "filters": [],
                    "sort_by": None,
                    "sort_dir": "desc",
                    "limit": 10,
                    "group_by": None,
                }
            )
        )
        command = parser.parse("show top 10 high similarity samples")
        self.assertEqual(command.action, "show_matches")

    def test_executor_requires_analysis_for_data_queries(self) -> None:
        if not HAS_PANDAS:
            self.skipTest("pandas is not installed in this Python environment")
        assert execute_agent_command is not None
        command = parse_agent_command("show top 10 high similarity samples")
        result = execute_agent_command(command, _sample_context(scan_result=None))
        self.assertIn("Run Analysis first", result.message)
        self.assertIsNone(result.table)

    def test_executor_replies_to_unsupported_without_analysis(self) -> None:
        if not HAS_PANDAS:
            self.skipTest("pandas is not installed in this Python environment")
        assert execute_agent_command is not None
        command = parse_agent_command("should I buy AVGO tomorrow")
        result = execute_agent_command(command, _sample_context(scan_result=None))
        self.assertIn("supported read-only command", result.message)
        self.assertIsNone(result.table)

    def test_executor_filters_bullish_cases(self) -> None:
        if not HAS_PANDAS:
            self.skipTest("pandas is not installed in this Python environment")
        assert execute_agent_command is not None
        scan_result = {
            "scan_bias": "bullish",
            "scan_confidence": "medium",
            "historical_match_summary": {},
        }
        command = parse_agent_command("show only bullish cases")
        result = execute_agent_command(command, _sample_context(scan_result=scan_result))
        self.assertIsNotNone(result.table)
        assert result.table is not None
        self.assertEqual(len(result.table), 2)
        self.assertTrue((result.table["NextCloseMove"] > 0).all())

    def test_executor_groups_by_similarity(self) -> None:
        if not HAS_PANDAS:
            self.skipTest("pandas is not installed in this Python environment")
        assert execute_agent_command is not None
        scan_result = {
            "scan_bias": "neutral",
            "scan_confidence": "low",
            "historical_match_summary": {},
        }
        command = parse_agent_command("group by similarity label")
        result = execute_agent_command(command, _sample_context(scan_result=scan_result))
        self.assertIsNotNone(result.table)
        assert result.table is not None
        self.assertEqual(set(result.table["ContextLabel"]), {"高相似", "中相似"})


if __name__ == "__main__":
    unittest.main()
