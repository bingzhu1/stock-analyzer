#!/usr/bin/env bash
set -e

python3 -m py_compile app.py
python3 -m py_compile scanner.py
python3 -m py_compile predict.py
python3 -m py_compile encoder.py
python3 -m py_compile matcher.py
python3 -m py_compile feature_builder.py
python3 -m py_compile data_fetcher.py
python3 -m py_compile services/predict_summary.py
python3 -m py_compile services/prediction_store.py
python3 -m py_compile services/outcome_capture.py
python3 -m py_compile services/review_store.py
python3 -m py_compile services/automation_wrapper.py
python3 -m py_compile services/tool_router.py
python3 -m py_compile services/intent_planner.py
python3 -m py_compile services/ai_intent_parser.py
python3 -m py_compile ui/command_bar.py
python3 -m py_compile ui/home_tab.py
python3 -m py_compile ui/predict_tab.py
echo "All compile checks passed."
