import json
from services.avgo_1000day_training import run_avgo_1000day_replay_training

report = run_avgo_1000day_replay_training(
    symbol="AVGO",
    lookback_days=20,
    num_cases=1000,
)

with open("avgo_1000day_training_report.json", "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print("ready:", report.get("ready"))
print("num_cases_requested:", report.get("num_cases_requested"))
print("num_cases_built:", report.get("num_cases_built"))

date_range = report.get("date_range", {})
print("start_as_of_date:", date_range.get("start_as_of_date"))
print("end_as_of_date:", date_range.get("end_as_of_date"))
print("end_prediction_for_date:", date_range.get("end_prediction_for_date"))

replay_summary = report.get("replay_summary", {})
print("total_cases:", replay_summary.get("total_cases"))
print("completed_cases:", replay_summary.get("completed_cases"))
print("failed_cases:", replay_summary.get("failed_cases"))
print("direction_accuracy:", replay_summary.get("direction_accuracy"))

print("headline_findings:")
for x in report.get("headline_findings", []):
    print("-", x)

rule_insights = report.get("rule_insights", {})
print("top_effective_rules:", len(rule_insights.get("top_effective_rules", [])))
print("top_harmful_rules:", len(rule_insights.get("top_harmful_rules", [])))
print("promote_candidates:", len(rule_insights.get("promote_candidates", [])))
print("production_candidates:", len(rule_insights.get("production_candidates", [])))
print("drift_candidates:", len(rule_insights.get("drift_candidates", [])))

print("saved to avgo_1000day_training_report.json")
