from __future__ import annotations

from pathlib import Path

import pandas as pd


DATA_DIR = Path("data")
ENRICHED_DIR = Path("enriched_data")
SYMBOLS = ["AVGO", "NVDA", "SOXX", "QQQ"]

BASE_COLUMNS = ["Date", "Open", "High", "Low", "Close", "Volume"]
FEATURE_COLUMNS = [
    "PrevClose",
    "MA20_Volume",
    "O_gap",
    "H_up",
    "L_down",
    "C_move",
    "V_ratio",
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

    missing_columns = [col for col in BASE_COLUMNS if col not in df.columns]
    if missing_columns:
        raise ValueError(
            f"Missing required columns in {csv_path}: {', '.join(missing_columns)}"
        )

    df = df[BASE_COLUMNS].copy()
    df["Date"] = pd.to_datetime(df["Date"])

    for col in ["Open", "High", "Low", "Close", "Volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.sort_values("Date").reset_index(drop=True)
    return df


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate basic daily features for later analysis."""
    result = df.copy()

    result["PrevClose"] = result["Close"].shift(1)
    result["MA20_Volume"] = result["Volume"].shift(1).rolling(20).mean()

    result["O_gap"] = (result["Open"] - result["PrevClose"]) / result["PrevClose"]
    result["H_up"] = (result["High"] - result["Open"]) / result["Open"]
    result["L_down"] = (result["Open"] - result["Low"]) / result["Open"]
    result["C_move"] = (result["Close"] - result["Open"]) / result["Open"]
    result["V_ratio"] = result["Volume"] / result["MA20_Volume"]

    result["Date"] = result["Date"].dt.strftime("%Y-%m-%d")
    return result[BASE_COLUMNS + FEATURE_COLUMNS]


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
