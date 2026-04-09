from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


CODED_FILE = Path("coded_data/AVGO_coded.csv")
MATCH_RESULTS_DIR = Path("match_results")
REQUIRED_COLUMNS = [
    "Date",
    "Open",
    "High",
    "Low",
    "Close",
    "Volume",
    "Code",
]

RESULT_COLUMNS = [
    "TargetDate",
    "TargetCode",
    "MatchDate",
    "MatchCode",
    "MatchType",
    "NextDate",
    "NextOpen",
    "NextHigh",
    "NextLow",
    "NextClose",
    "NextVolume",
    "NextOpenChange",
    "NextHighMove",
    "NextLowMove",
    "NextCloseMove",
    "VCodeDiff",
]


def load_coded_avgo() -> pd.DataFrame:
    """Load AVGO coded data and normalize basic column types."""
    if not CODED_FILE.exists():
        raise FileNotFoundError(f"Input CSV not found: {CODED_FILE}")

    df = pd.read_csv(CODED_FILE, dtype={"Code": "string"})

    missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_columns:
        raise ValueError(
            f"Missing required columns in {CODED_FILE}: {', '.join(missing_columns)}"
        )

    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"])

    for col in ["Open", "High", "Low", "Close", "Volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["Code"] = df["Code"].astype("string")
    df = df.sort_values("Date").reset_index(drop=True)
    return df


def get_code_for_date(df: pd.DataFrame, target_date: str) -> str:
    """Return the exact code for one target date."""
    target_ts = pd.to_datetime(target_date)
    matched_rows = df[df["Date"] == target_ts]

    if matched_rows.empty:
        raise ValueError(f"Target date not found in AVGO data: {target_date}")

    target_code = matched_rows.iloc[0]["Code"]
    if pd.isna(target_code) or str(target_code).strip() == "":
        raise ValueError(f"Target date has empty Code and cannot be matched: {target_date}")

    return str(target_code)


def split_code(code_str: str) -> list[int] | None:
    """Split a 5-digit code string into five integers."""
    if pd.isna(code_str):
        return None

    code_text = str(code_str).strip()
    if not code_text:
        return None

    if code_text.endswith(".0"):
        integer_part, decimal_part = code_text.split(".", maxsplit=1)
        if decimal_part and set(decimal_part) == {"0"}:
            code_text = integer_part

    if len(code_text) != 5 or not code_text.isdigit():
        return None

    return [int(char) for char in code_text]


def find_exact_code_matches(
    df: pd.DataFrame, target_code: str, target_date: str
) -> pd.DataFrame:
    """Find all other dates whose code exactly matches the target code."""
    target_ts = pd.to_datetime(target_date)

    matches = df[(df["Code"] == target_code) & (df["Date"] != target_ts)].copy()
    matches = matches.sort_values("Date").reset_index(drop=True)
    return matches


def find_near_code_matches(
    df: pd.DataFrame, target_code: str, target_date: str
) -> pd.DataFrame:
    """Find dates with the same first four code digits and close V_code."""
    target_parts = split_code(target_code)
    if target_parts is None:
        raise ValueError(f"Invalid target code: {target_code}")

    target_ts = pd.to_datetime(target_date)
    records = []

    for _, row in df.iterrows():
        if row["Date"] == target_ts:
            continue

        match_parts = split_code(row["Code"])
        if match_parts is None:
            continue

        same_first_four = match_parts[:4] == target_parts[:4]
        v_code_diff = abs(match_parts[4] - target_parts[4])

        if same_first_four and v_code_diff <= 1:
            row_dict = row.to_dict()
            row_dict["VCodeDiff"] = v_code_diff
            records.append(row_dict)

    matches = pd.DataFrame(records)
    if matches.empty:
        return pd.DataFrame(columns=list(df.columns) + ["VCodeDiff"])

    matches = matches.sort_values("Date").reset_index(drop=True)
    return matches


def build_match_result_table(
    df: pd.DataFrame,
    matches: pd.DataFrame,
    target_date: str,
    target_code: str,
    match_type: str,
) -> pd.DataFrame:
    """Build the next-day result table from a matched date list."""
    if matches.empty:
        return pd.DataFrame(columns=RESULT_COLUMNS)

    records = []

    for _, match_row in matches.iterrows():
        match_index_list = df.index[df["Date"] == match_row["Date"]].tolist()
        if not match_index_list:
            continue

        match_index = match_index_list[0]
        next_index = match_index + 1

        if next_index >= len(df):
            continue

        next_row = df.iloc[next_index]
        match_close = match_row["Close"]
        next_open = next_row["Open"]

        record = {
            "TargetDate": pd.to_datetime(target_date).strftime("%Y-%m-%d"),
            "TargetCode": target_code,
            "MatchDate": match_row["Date"].strftime("%Y-%m-%d"),
            "MatchCode": str(match_row["Code"]),
            "MatchType": match_type,
            "NextDate": next_row["Date"].strftime("%Y-%m-%d"),
            "NextOpen": next_row["Open"],
            "NextHigh": next_row["High"],
            "NextLow": next_row["Low"],
            "NextClose": next_row["Close"],
            "NextVolume": next_row["Volume"],
            "NextOpenChange": (next_open - match_close) / match_close,
            "NextHighMove": (next_row["High"] - next_open) / next_open,
            "NextLowMove": (next_open - next_row["Low"]) / next_open,
            "NextCloseMove": (next_row["Close"] - next_open) / next_open,
            "VCodeDiff": match_row.get("VCodeDiff", pd.NA),
        }
        records.append(record)

    result_df = pd.DataFrame(records)
    if result_df.empty:
        return pd.DataFrame(columns=RESULT_COLUMNS)

    result_df = result_df.sort_values("MatchDate").reset_index(drop=True)
    return result_df[RESULT_COLUMNS]


def build_next_day_match_table(df: pd.DataFrame, target_date: str) -> pd.DataFrame:
    """Build the next-day table for exact historical code matches."""
    target_code = get_code_for_date(df, target_date)
    matches = find_exact_code_matches(df, target_code, target_date)

    if matches.empty:
        print(f"[INFO] No exact code matches found for {target_date} with code {target_code}")
        return pd.DataFrame(columns=RESULT_COLUMNS)

    result_df = build_match_result_table(df, matches, target_date, target_code, "exact")

    if result_df.empty:
        print("[INFO] Exact matches exist, but none have a next trading day to use.")

    return result_df


def build_near_match_table(df: pd.DataFrame, target_date: str) -> pd.DataFrame:
    """Build the next-day table for near historical code matches."""
    target_code = get_code_for_date(df, target_date)
    matches = find_near_code_matches(df, target_code, target_date)

    if matches.empty:
        print(f"[INFO] No near code matches found for {target_date} with code {target_code}")
        return pd.DataFrame(columns=RESULT_COLUMNS)

    result_df = build_match_result_table(df, matches, target_date, target_code, "near")

    if result_df.empty:
        print("[INFO] Near matches exist, but none have a next trading day to use.")

    return result_df


def save_match_results(result_df: pd.DataFrame, target_date: str) -> Path:
    """Save exact match results to the match_results directory."""
    MATCH_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    safe_date = pd.to_datetime(target_date).strftime("%Y-%m-%d")
    output_path = MATCH_RESULTS_DIR / f"AVGO_exact_matches_{safe_date}.csv"
    result_df.to_csv(output_path, index=False)

    print(f"[SAVED] Exact match results saved to {output_path}")
    return output_path


def save_near_match_results(result_df: pd.DataFrame, target_date: str) -> Path:
    """Save near match results to the match_results directory."""
    MATCH_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    safe_date = pd.to_datetime(target_date).strftime("%Y-%m-%d")
    output_path = MATCH_RESULTS_DIR / f"AVGO_near_matches_{safe_date}.csv"
    result_df.to_csv(output_path, index=False)

    print(f"[SAVED] Near match results saved to {output_path}")
    return output_path


def main() -> None:
    if len(sys.argv) > 1:
        target_date = sys.argv[1]
    else:
        target_date = "2026-04-08"

    try:
        df = load_coded_avgo()

        exact_result_df = build_next_day_match_table(df, target_date)
        save_match_results(exact_result_df, target_date)

        near_result_df = build_near_match_table(df, target_date)
        save_near_match_results(near_result_df, target_date)
    except Exception as exc:
        print(f"[ERROR] {exc}")


if __name__ == "__main__":
    main()
