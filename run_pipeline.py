from __future__ import annotations

import sys

from data_fetcher import batch_update_all
from encoder import batch_encode_all
from feature_builder import batch_build_features
from matcher import (
    build_near_match_table,
    build_next_day_match_table,
    load_coded_avgo,
    save_match_results,
    save_near_match_results,
)
from stats_reporter import (
    build_stats_summary,
    print_stats_summary,
    save_stats_summary,
)


def run_pipeline(target_date: str) -> None:
    """Run the full local analysis pipeline for one target date."""
    print("[STEP 1] Updating raw data...")
    batch_update_all()

    print("[STEP 2] Building features...")
    batch_build_features()

    print("[STEP 3] Encoding data...")
    batch_encode_all()

    print("[STEP 4] Building match results...")
    coded_df = load_coded_avgo()

    exact_result_df = build_next_day_match_table(coded_df, target_date)
    save_match_results(exact_result_df, target_date)

    near_result_df = build_near_match_table(coded_df, target_date)
    save_near_match_results(near_result_df, target_date)

    print("[STEP 5] Building stats summary...")
    summary_df = build_stats_summary(target_date)
    save_stats_summary(summary_df, target_date)
    print_stats_summary(summary_df)

    print("[DONE] Pipeline finished.")


def main() -> None:
    if len(sys.argv) > 1:
        target_date = sys.argv[1]
    else:
        target_date = "2026-04-08"

    try:
        run_pipeline(target_date)
    except Exception as exc:
        print(f"[ERROR] Pipeline failed: {exc}")


if __name__ == "__main__":
    main()
