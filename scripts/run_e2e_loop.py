#!/usr/bin/env python3
"""
scripts/run_e2e_loop.py

End-to-end research loop verification.
Runs: scan → predict → save_prediction → capture_outcome → generate_review → run_review_for_prediction
Writes real rows to avgo_agent.db and prints evidence at each step.

Usage: python3 scripts/run_e2e_loop.py
"""
import sys
import os
import json
import sqlite3
import pandas as pd

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ANALYSIS_DATE = "2026-04-20"
PREDICTION_FOR_DATE = "2026-04-21"
SYMBOL = "AVGO"
DB_PATH = "avgo_agent.db"


def load_coded_df() -> pd.DataFrame:
    df = pd.read_csv("coded_data/AVGO_coded.csv")
    df["Date"] = pd.to_datetime(df["Date"])
    return df


def load_match_dfs(target_date: str):
    from matcher import build_next_day_match_table, build_near_match_table
    coded_df = load_coded_df()
    exact_df = build_next_day_match_table(coded_df, target_date)
    near_df = build_near_match_table(coded_df, target_date)
    return exact_df, near_df


def load_summary_df(target_date: str) -> pd.DataFrame:
    from stats_reporter import build_stats_summary
    try:
        return build_stats_summary(target_date)
    except Exception as e:
        print(f"  [warn] summary_df: {e}")
        return pd.DataFrame()


def db_count(table: str) -> int:
    conn = sqlite3.connect(DB_PATH)
    n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    conn.close()
    return n


def db_latest(table: str) -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute(f"SELECT * FROM {table} ORDER BY rowid DESC LIMIT 1").fetchone()
    conn.close()
    return dict(row) if row else None


def show_db_state(label: str):
    print(f"\n  DB state after [{label}]:")
    for t in ("prediction_log", "outcome_log", "review_log", "deterministic_review_log"):
        try:
            print(f"    {t}: {db_count(t)} rows")
        except Exception as e:
            print(f"    {t}: ERROR - {e}")


def main():
    print("=" * 60)
    print("E2E RESEARCH LOOP VERIFICATION")
    print(f"  analysis_date:      {ANALYSIS_DATE}")
    print(f"  prediction_for_date:{PREDICTION_FOR_DATE}")
    print("=" * 60)

    # ── Step 0: Build scan inputs ─────────────────────────────────────────────
    print("\n[Step 0] Loading coded_df and match results…")
    coded_df = load_coded_df()
    print(f"  coded_df rows: {len(coded_df)}")

    print("[Step 0] Building match tables…")
    exact_df, near_df = load_match_dfs(ANALYSIS_DATE)
    print(f"  exact matches: {len(exact_df)}, near matches: {len(near_df)}")

    summary_df = load_summary_df(ANALYSIS_DATE)
    pos_df = pd.DataFrame()
    prev_df = pd.DataFrame()
    mom_df = pd.DataFrame()

    # ── Step 1: Scan ─────────────────────────────────────────────────────────
    print("\n[Step 1] Running scan…")
    from scanner import run_scan
    scan_result = run_scan(
        ANALYSIS_DATE, coded_df, exact_df, near_df,
        summary_df, pos_df, prev_df, mom_df,
        scan_phase="daily",
    )
    print(f"  scan_bias:       {scan_result.get('scan_bias')}")
    print(f"  scan_confidence: {scan_result.get('scan_confidence')}")
    print(f"  avgo_gap_state:  {scan_result.get('avgo_gap_state')}")

    # ── Step 2: Predict ───────────────────────────────────────────────────────
    print("\n[Step 2] Running predict…")
    from predict import run_predict
    predict_result = run_predict(scan_result, research_result=None, symbol=SYMBOL)
    print(f"  final_bias:       {predict_result.get('final_bias')}")
    print(f"  final_confidence: {predict_result.get('final_confidence')}")
    print(f"  open_tendency:    {predict_result.get('open_tendency')}")
    print(f"  close_tendency:   {predict_result.get('close_tendency')}")

    # ── Step 3: Save prediction ───────────────────────────────────────────────
    print("\n[Step 3] Saving prediction to prediction_log…")
    show_db_state("before save")
    from services.prediction_store import save_prediction
    prediction_id = save_prediction(
        symbol=SYMBOL,
        prediction_for_date=PREDICTION_FOR_DATE,
        scan_result=scan_result,
        research_result=None,
        predict_result=predict_result,
        snapshot_id="e2e_test",
    )
    print(f"  prediction_id: {prediction_id}")
    show_db_state("after save")
    row = db_latest("prediction_log")
    if row:
        print(f"  latest prediction_log row:")
        print(f"    id:                 {row['id'][:8]}…")
        print(f"    symbol:             {row['symbol']}")
        print(f"    prediction_for_date:{row['prediction_for_date']}")
        print(f"    final_bias:         {row['final_bias']}")
        print(f"    final_confidence:   {row['final_confidence']}")
        print(f"    status:             {row['status']}")

    # ── Step 4: Capture outcome ───────────────────────────────────────────────
    print("\n[Step 4] Capturing outcome from yfinance…")
    show_db_state("before capture")
    try:
        from services.outcome_capture import capture_outcome
        outcome = capture_outcome(prediction_id)
        print(f"  actual_close:        {outcome.get('actual_close')}")
        print(f"  actual_close_change: {outcome.get('actual_close_change')}")
        print(f"  direction_correct:   {outcome.get('direction_correct')}")
        show_db_state("after capture")
        row = db_latest("outcome_log")
        if row:
            print(f"  latest outcome_log row:")
            print(f"    id:                  {row['id'][:8]}…")
            print(f"    prediction_id:       {row['prediction_id'][:8]}…")
            print(f"    prediction_for_date: {row['prediction_for_date']}")
            print(f"    actual_close:        {row['actual_close']}")
            print(f"    direction_correct:   {row['direction_correct']}")
    except ValueError as e:
        print(f"  [ERROR] {e}")
        print("  Outcome capture failed — market may have been closed or yfinance unavailable.")
        print("  Continuing with remaining steps (review requires outcome)…")
        outcome = None

    # ── Step 5: Generate LLM/rule review ─────────────────────────────────────
    if outcome:
        print("\n[Step 5] Generating review (LLM or rule-based)…")
        show_db_state("before review")
        try:
            from services.review_agent import generate_review
            generate_review(prediction_id)
            show_db_state("after review")
            row = db_latest("review_log")
            if row:
                print(f"  latest review_log row:")
                print(f"    id:             {row['id'][:8]}…")
                print(f"    error_category: {row['error_category']}")
                print(f"    root_cause:     {row['root_cause'][:60] if row['root_cause'] else 'None'}…")
        except Exception as e:
            print(f"  [warn] generate_review: {e}")

        # ── Step 6: Deterministic review (run_review_for_prediction) ─────────
        print("\n[Step 6] Running deterministic review (review_orchestrator)…")
        show_db_state("before det_review")
        try:
            from services.review_orchestrator import run_review_for_prediction
            result = run_review_for_prediction(SYMBOL, PREDICTION_FOR_DATE)
            print(f"  status:         {result.get('status')}")
            if result.get("status") == "ok":
                comp = result.get("comparison", {})
                print(f"  overall_score:  {comp.get('overall_score')}")
                print(f"  correct_count:  {comp.get('correct_count')}/{comp.get('total_count')}")
                print(f"  direction_match:{comp.get('direction_match')}")
            else:
                print(f"  error: {result.get('error')}")
            show_db_state("after det_review")
            row = db_latest("deterministic_review_log")
            if row:
                print(f"  latest deterministic_review_log row:")
                print(f"    id:                  {row['id'][:8]}…")
                print(f"    prediction_id:       {row['prediction_id'][:8]}…")
                print(f"    prediction_for_date: {row['prediction_for_date']}")
                print(f"    overall_score:       {row['overall_score']}")
                print(f"    error_category:      {row['error_category']}")
        except Exception as e:
            print(f"  [ERROR] run_review_for_prediction: {e}")

    # ── Step 7: Rule extraction ───────────────────────────────────────────────
    print("\n[Step 7] Rule extraction from review history…")
    try:
        from services.review_analyzer import summarize_review_history, extract_review_rules
        summary = summarize_review_history(SYMBOL, limit=30)
        rules = extract_review_rules(summary)
        print(f"  record_count:    {summary.get('record_count')}")
        print(f"  overall_accuracy:{summary.get('overall_accuracy')}")
        print(f"  rules extracted: {len(rules)}")
        for r in rules[:3]:
            print(f"    - {r}")
    except Exception as e:
        print(f"  [ERROR] {e}")

    # ── Step 8: Pre-briefing (simulates next-day flow) ────────────────────────
    print("\n[Step 8] Pre-prediction briefing (simulates next-day rule injection)…")
    try:
        from services.pre_prediction_briefing import build_pre_prediction_briefing
        briefing = build_pre_prediction_briefing(SYMBOL, limit=30, max_rules=3)
        print(f"  has_data:        {briefing.get('has_data')}")
        print(f"  record_count:    {briefing.get('record_count')}")
        print(f"  caution_level:   {briefing.get('caution_level')}")
        print(f"  overall_accuracy:{briefing.get('overall_accuracy')}")
        # Show rule injection into predict
        if briefing.get("has_data"):
            print("\n  [P0-3 demo] Applying briefing to predict…")
            predict_result2 = run_predict(scan_result, research_result=None, symbol=SYMBOL, pre_briefing=briefing)
            print(f"    final_confidence (no briefing): {predict_result.get('final_confidence')}")
            print(f"    final_confidence (with briefing): {predict_result2.get('final_confidence')}")
            print(f"    briefing_caution_applied: {predict_result2.get('briefing_caution_applied')}")
            print(f"    briefing_caution_reason: {predict_result2.get('briefing_caution_reason')}")
    except Exception as e:
        print(f"  [ERROR] {e}")

    # ── Final DB state ────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("FINAL DB STATE")
    show_db_state("end of E2E run")

    # Real vs historical count
    try:
        from services.review_store import count_real_vs_historical
        counts = count_real_vs_historical(SYMBOL)
        print(f"\n  deterministic_review_log breakdown for {SYMBOL}:")
        print(f"    real predictions: {counts['real']}")
        print(f"    historical replay:{counts['historical']}")
        print(f"    total:            {counts['total']}")
    except Exception as e:
        print(f"  [warn] count_real_vs_historical: {e}")

    print("\nE2E LOOP COMPLETE.")
    print("=" * 60)


if __name__ == "__main__":
    main()
