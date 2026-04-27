from __future__ import annotations

from pathlib import Path

import pandas as pd


DATA_DIR = Path("data")
ENRICHED_DIR = Path("enriched_data")
SYMBOLS = ["AVGO", "NVDA", "SOXX", "QQQ"]

BASE_COLUMNS = ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
# Required subset of BASE_COLUMNS (Adj Close is optional)
_REQUIRED_BASE = ["Date", "Open", "High", "Low", "Close", "Volume"]
FEATURE_COLUMNS = [
    "PrevClose",
    "MA20_Volume",
    "O_gap",
    "H_up",
    "L_down",
    "C_move",
    "V_ratio",
    "PrevAdjClose",
    "C_adj",
]


def get_input_csv_path(symbol: str) -> Path:
    """Return the raw CSV path for one symbol."""
    return DATA_DIR / f"{symbol}.csv"


def get_output_csv_path(symbol: str) -> Path:
    """Return the output feature CSV path for one symbol."""
    return ENRICHED_DIR / f"{symbol}_features.csv"


def load_price_csv(csv_path: Path) -> pd.DataFrame:
    """Read one OHLCV CSV and normalize its columns."""
    if not csv_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {csv_path}")

    df = pd.read_csv(csv_path)

    # Only the non-optional base columns are required; Adj Close is optional
    missing_columns = [col for col in _REQUIRED_BASE if col not in df.columns]
    if missing_columns:
        raise ValueError(
            f"Missing required columns in {csv_path}: {', '.join(missing_columns)}"
        )

    available_base = [col for col in BASE_COLUMNS if col in df.columns]
    df = df[available_base].copy()
    df["Date"] = pd.to_datetime(df["Date"])

    for col in ["Open", "High", "Low", "Close", "Volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "Adj Close" in df.columns:
        df["Adj Close"] = pd.to_numeric(df["Adj Close"], errors="coerce")

    df = df.sort_values("Date").reset_index(drop=True)
    return df


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate basic daily features for later analysis."""
    result = df.copy()

    # Use Adj Close for adjusted-return calculations when available;
    # fall back to raw Close so older CSVs without Adj Close still work.
    has_adj = "Adj Close" in result.columns and result["Adj Close"].notna().any()
    adj_close_series = result["Adj Close"] if has_adj else result["Close"]

    result["PrevClose"] = result["Close"].shift(1)
    result["PrevAdjClose"] = adj_close_series.shift(1)
    result["MA20_Volume"] = result["Volume"].shift(1).rolling(20).mean()

    # O_gap: intraday/overnight structure — always raw price (Open vs prev raw Close)
    result["O_gap"] = (result["Open"] - result["PrevClose"]) / result["PrevClose"]
    # Intraday structure — always raw OHLC
    result["H_up"] = (result["High"] - result["Open"]) / result["Open"]
    result["L_down"] = (result["Open"] - result["Low"]) / result["Open"]
    result["C_move"] = (result["Close"] - result["Open"]) / result["Open"]
    result["V_ratio"] = result["Volume"] / result["MA20_Volume"]
    # Adjusted daily return for C_code encoding
    result["C_adj"] = (adj_close_series - result["PrevAdjClose"]) / result["PrevAdjClose"]

    result["Date"] = result["Date"].dt.strftime("%Y-%m-%d")
    available_base = [col for col in BASE_COLUMNS if col in result.columns]
    return result[available_base + FEATURE_COLUMNS]


def build_features_for_csv(csv_path: str | Path) -> pd.DataFrame:
    """Build features for one CSV file and save the result."""
    input_path = Path(csv_path)
    symbol = input_path.stem.upper()

    df = load_price_csv(input_path)
    feature_df = build_features(df)

    ENRICHED_DIR.mkdir(parents=True, exist_ok=True)
    output_path = get_output_csv_path(symbol)
    feature_df.to_csv(output_path, index=False)

    print(f"[FEATURES] {symbol}: saved {len(feature_df)} rows to {output_path}")
    return feature_df


def build_features_for_symbol(symbol: str) -> pd.DataFrame:
    """Build features for one configured symbol."""
    input_path = get_input_csv_path(symbol)
    return build_features_for_csv(input_path)


def batch_build_features() -> None:
    """Build feature files for all configured symbols."""
    ENRICHED_DIR.mkdir(parents=True, exist_ok=True)

    for symbol in SYMBOLS:
        try:
            build_features_for_symbol(symbol)
        except FileNotFoundError as exc:
            print(f"[MISSING] {symbol}: {exc}")
        except Exception as exc:
            print(f"[ERROR] {symbol}: {exc}")


def main() -> None:
    batch_build_features()


if __name__ == "__main__":
    main()
