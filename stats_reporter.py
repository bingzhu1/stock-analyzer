from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


MATCH_RESULTS_DIR = Path("match_results")
STATS_RESULTS_DIR = Path("stats_results")

MATCH_REQUIRED_COLUMNS = [
    "TargetDate",
    "TargetCode",
    "MatchType",
    "NextOpenChange",
    "NextHighMove",
    "NextLowMove",
    "NextCloseMove",
]

SUMMARY_COLUMNS = [
    "TargetDate",
    "TargetCode",
    "MatchType",
    "SampleSize",
    "AvgNextOpenChange",
    "MedianNextOpenChange",
    "PositiveNextOpenChangeRate",
    "AvgNextHighMove",
    "MedianNextHighMove",
    "HighMoveOver1PctRate",
    "HighMoveOver2PctRate",
    "AvgNextLowMove",
    "MedianNextLowMove",
    "LowMoveOver1PctRate",
    "LowMoveOver2PctRate",
    "AvgNextCloseMove",
    "MedianNextCloseMove",
    "PositiveNextCloseMoveRate",
    "NegativeNextCloseMoveRate",
    "DominantNextDayBias",
]


def get_exact_match_path(target_date: str) -> Path:
    safe_date = pd.to_datetime(target_date).strftime("%Y-%m-%d")
    return MATCH_RESULTS_DIR / f"AVGO_exact_matches_{safe_date}.csv"


def get_near_match_path(target_date: str) -> Path:
    safe_date = pd.to_datetime(target_date).strftime("%Y-%m-%d")
    return MATCH_RESULTS_DIR / f"AVGO_near_matches_{safe_date}.csv"


def get_summary_output_path(target_date: str) -> Path:
    safe_date = pd.to_datetime(target_date).strftime("%Y-%m-%d")
    return STATS_RESULTS_DIR / f"AVGO_stats_summary_{safe_date}.csv"


def load_match_file(csv_path: str | Path) -> pd.DataFrame:
    """Load one match result file and normalize numeric columns."""
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Match result file not found: {path}")

    df = pd.read_csv(path)

    if df.empty:
        return pd.DataFrame(columns=MATCH_REQUIRED_COLUMNS)

    missing_columns = [col for col in MATCH_REQUIRED_COLUMNS if col not in df.columns]
    if missing_columns:
        raise ValueError(
            f"Missing required columns in {path}: {', '.join(missing_columns)}"
        )

    df = df.copy()
    numeric_columns = [
        "NextOpenChange",
        "NextHighMove",
        "NextLowMove",
        "NextCloseMove",
    ]
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def get_bias_label(
    sample_size: int,
    positive_close_rate: float | pd.NA,
    negative_close_rate: float | pd.NA,
) -> str:
    """Return a simple neutral bias label based on sample stats."""
    if sample_size < 3:
        return "insufficient_sample"
    if pd.notna(positive_close_rate) and positive_close_rate >= 0.6:
        return "up_bias"
    if pd.notna(negative_close_rate) and negative_close_rate >= 0.6:
        return "down_bias"
    return "mixed"


def summarize_match_df(df: pd.DataFrame, match_type: str) -> dict:
    """Summarize one match result dataframe."""
    summary = {column: pd.NA for column in SUMMARY_COLUMNS}
    summary["MatchType"] = match_type

    if df.empty:
        summary["SampleSize"] = 0
        summary["DominantNextDayBias"] = "insufficient_sample"
        return summary

    sample_size = len(df)
    target_date = df.iloc[0]["TargetDate"] if "TargetDate" in df.columns else pd.NA
    target_code = df.iloc[0]["TargetCode"] if "TargetCode" in df.columns else pd.NA

    positive_open_rate = (df["NextOpenChange"] > 0).mean()
    high_over_1_rate = (df["NextHighMove"] >= 0.01).mean()
    high_over_2_rate = (df["NextHighMove"] >= 0.02).mean()
    low_over_1_rate = (df["NextLowMove"] >= 0.01).mean()
    low_over_2_rate = (df["NextLowMove"] >= 0.02).mean()
    positive_close_rate = (df["NextCloseMove"] > 0).mean()
    negative_close_rate = (df["NextCloseMove"] < 0).mean()

    summary.update(
        {
            "TargetDate": target_date,
            "TargetCode": target_code,
            "SampleSize": sample_size,
            "AvgNextOpenChange": df["NextOpenChange"].mean(),
            "MedianNextOpenChange": df["NextOpenChange"].median(),
            "PositiveNextOpenChangeRate": positive_open_rate,
            "AvgNextHighMove": df["NextHighMove"].mean(),
            "MedianNextHighMove": df["NextHighMove"].median(),
            "HighMoveOver1PctRate": high_over_1_rate,
            "HighMoveOver2PctRate": high_over_2_rate,
            "AvgNextLowMove": df["NextLowMove"].mean(),
            "MedianNextLowMove": df["NextLowMove"].median(),
            "LowMoveOver1PctRate": low_over_1_rate,
            "LowMoveOver2PctRate": low_over_2_rate,
            "AvgNextCloseMove": df["NextCloseMove"].mean(),
            "MedianNextCloseMove": df["NextCloseMove"].median(),
            "PositiveNextCloseMoveRate": positive_close_rate,
            "NegativeNextCloseMoveRate": negative_close_rate,
            "DominantNextDayBias": get_bias_label(
                sample_size, positive_close_rate, negative_close_rate
            ),
        }
    )

    return summary


def build_stats_summary(target_date: str) -> pd.DataFrame:
    """Build a two-row summary table for exact and near match results."""
    safe_date = pd.to_datetime(target_date).strftime("%Y-%m-%d")

    summary_rows = []
    file_configs = [
        ("exact", get_exact_match_path(safe_date)),
        ("near", get_near_match_path(safe_date)),
    ]

    for match_type, file_path in file_configs:
        try:
            df = load_match_file(file_path)
            summary_row = summarize_match_df(df, match_type)
            if pd.isna(summary_row["TargetDate"]):
                summary_row["TargetDate"] = safe_date
            summary_rows.append(summary_row)
        except FileNotFoundError:
            print(f"[MISSING] {match_type} file not found: {file_path}")
            summary_rows.append(
                {
                    "TargetDate": safe_date,
                    "TargetCode": pd.NA,
                    "MatchType": match_type,
                    "SampleSize": 0,
                    "AvgNextOpenChange": pd.NA,
                    "MedianNextOpenChange": pd.NA,
                    "PositiveNextOpenChangeRate": pd.NA,
                    "AvgNextHighMove": pd.NA,
                    "MedianNextHighMove": pd.NA,
                    "HighMoveOver1PctRate": pd.NA,
                    "HighMoveOver2PctRate": pd.NA,
                    "AvgNextLowMove": pd.NA,
                    "MedianNextLowMove": pd.NA,
                    "LowMoveOver1PctRate": pd.NA,
                    "LowMoveOver2PctRate": pd.NA,
                    "AvgNextCloseMove": pd.NA,
                    "MedianNextCloseMove": pd.NA,
                    "PositiveNextCloseMoveRate": pd.NA,
                    "NegativeNextCloseMoveRate": pd.NA,
                    "DominantNextDayBias": "insufficient_sample",
                }
            )

    summary_df = pd.DataFrame(summary_rows)
    return summary_df[SUMMARY_COLUMNS]


def save_stats_summary(summary_df: pd.DataFrame, target_date: str) -> Path:
    """Save the summary dataframe to stats_results."""
    STATS_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    output_path = get_summary_output_path(target_date)
    summary_df.to_csv(output_path, index=False)

    print(f"[SAVED] Stats summary saved to {output_path}")
    return output_path


def print_stats_summary(summary_df: pd.DataFrame) -> None:
    """Print a short terminal summary for exact and near rows."""
    for _, row in summary_df.iterrows():
        header = str(row["MatchType"]).upper()
        print(f"[{header}]")
        print(f"sample size: {row['SampleSize']}")
        print(f"avg next close move: {row['AvgNextCloseMove']}")
        print(f"positive close rate: {row['PositiveNextCloseMoveRate']}")
        print(f"bias: {row['DominantNextDayBias']}")
        print()


def main() -> None:
    if len(sys.argv) > 1:
        target_date = sys.argv[1]
    else:
        target_date = "2026-04-08"

    try:
        summary_df = build_stats_summary(target_date)
        save_stats_summary(summary_df, target_date)
        print_stats_summary(summary_df)
    except Exception as exc:
        print(f"[ERROR] {exc}")


if __name__ == "__main__":
    main()
