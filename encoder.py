from __future__ import annotations

from pathlib import Path

import pandas as pd


ENRICHED_DIR = Path("enriched_data")
CODED_DIR = Path("coded_data")
SYMBOLS = ["AVGO", "NVDA", "SOXX", "QQQ"]

REQUIRED_COLUMNS = [
    "Date",
    "Open",
    "High",
    "Low",
    "Close",
    "Volume",
    "PrevClose",
    "MA20_Volume",
    "O_gap",
    "H_up",
    "L_down",
    "C_move",
    "V_ratio",
]

CODE_COLUMNS = ["O_code", "H_code", "L_code", "C_code", "V_code", "Code"]


def get_input_csv_path(symbol: str) -> Path:
    """Return the feature CSV path for one symbol."""
    return ENRICHED_DIR / f"{symbol}_features.csv"


def get_output_csv_path(symbol: str) -> Path:
    """Return the coded CSV path for one symbol."""
    return CODED_DIR / f"{symbol}_coded.csv"


def load_feature_csv(csv_path: Path) -> pd.DataFrame:
    """Read one feature CSV and normalize its columns."""
    if not csv_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {csv_path}")

    df = pd.read_csv(csv_path)

    missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_columns:
        raise ValueError(
            f"Missing required columns in {csv_path}: {', '.join(missing_columns)}"
        )

    df = df[REQUIRED_COLUMNS].copy()
    df["Date"] = pd.to_datetime(df["Date"])

    numeric_columns = [col for col in REQUIRED_COLUMNS if col != "Date"]
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.sort_values("Date").reset_index(drop=True)
    return df


def encode_gap_style(value: float) -> int | pd.NA:
    """Encode values with negative/neutral/positive gap buckets."""
    if pd.isna(value):
        return pd.NA
    if value < -0.02:
        return 1
    if value < -0.005:
        return 2
    if value <= 0.005:
        return 3
    if value <= 0.02:
        return 4
    return 5


def encode_range_style(value: float) -> int | pd.NA:
    """Encode non-negative range values into five levels."""
    if pd.isna(value):
        return pd.NA

    safe_value = max(value, 0)

    if safe_value < 0.005:
        return 1
    if safe_value < 0.015:
        return 2
    if safe_value < 0.03:
        return 3
    if safe_value < 0.05:
        return 4
    return 5


def encode_o_gap(value: float) -> int | pd.NA:
    """Encode O_gap into O_code."""
    return encode_gap_style(value)


def encode_h_up(value: float) -> int | pd.NA:
    """Encode H_up into H_code."""
    return encode_range_style(value)


def encode_l_down(value: float) -> int | pd.NA:
    """Encode L_down into L_code."""
    return encode_range_style(value)


def encode_c_move(value: float) -> int | pd.NA:
    """Encode C_move into C_code."""
    return encode_gap_style(value)


def encode_v_ratio(value: float) -> int | pd.NA:
    """Encode V_ratio into V_code."""
    if pd.isna(value):
        return pd.NA
    if value < 0.70:
        return 1
    if value < 0.90:
        return 2
    if value < 1.10:
        return 3
    if value < 1.50:
        return 4
    return 5


def build_code_string(row: pd.Series) -> str | pd.NA:
    """Join five code columns into one string when all codes are available."""
    code_values = [row["O_code"], row["H_code"], row["L_code"], row["C_code"], row["V_code"]]

    if any(pd.isna(value) for value in code_values):
        return pd.NA

    return "".join(str(int(value)) for value in code_values)


def encode_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Add code columns to one feature dataframe."""
    result = df.copy()

    result["O_code"] = result["O_gap"].apply(encode_o_gap).astype("Int64")
    result["H_code"] = result["H_up"].apply(encode_h_up).astype("Int64")
    result["L_code"] = result["L_down"].apply(encode_l_down).astype("Int64")
    result["C_code"] = result["C_move"].apply(encode_c_move).astype("Int64")
    result["V_code"] = result["V_ratio"].apply(encode_v_ratio).astype("Int64")
    result["Code"] = result.apply(build_code_string, axis=1)

    result["Date"] = result["Date"].dt.strftime("%Y-%m-%d")
    return result[REQUIRED_COLUMNS + CODE_COLUMNS]


def encode_symbol(symbol: str) -> pd.DataFrame:
    """Read one feature file, encode it, and save the result."""
    input_path = get_input_csv_path(symbol)
    df = load_feature_csv(input_path)
    coded_df = encode_dataframe(df)

    CODED_DIR.mkdir(parents=True, exist_ok=True)
    output_path = get_output_csv_path(symbol)
    coded_df.to_csv(output_path, index=False)

    print(f"[CODED] {symbol}: saved {len(coded_df)} rows to {output_path}")
    return coded_df


def batch_encode_all() -> None:
    """Encode all configured symbols one by one."""
    CODED_DIR.mkdir(parents=True, exist_ok=True)

    for symbol in SYMBOLS:
        try:
            encode_symbol(symbol)
        except FileNotFoundError as exc:
            print(f"[MISSING] {symbol}: {exc}")
        except Exception as exc:
            print(f"[ERROR] {symbol}: {exc}")


def main() -> None:
    batch_encode_all()


if __name__ == "__main__":
    main()
