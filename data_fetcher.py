from __future__ import annotations

from pathlib import Path

import pandas as pd
import yfinance as yf


DATA_DIR = Path("data")
SYMBOLS = {
    "AVGO": "2016-05-18",
    "NVDA": "2016-05-18",
    "SOXX": "2016-05-18",
    "QQQ": "2016-05-18",
}
KEEP_COLUMNS = ["Date", "Open", "High", "Low", "Close", "Volume"]


def get_csv_path(symbol: str) -> Path:
    """Return the local CSV path for one symbol."""
    return DATA_DIR / f"{symbol}.csv"


def clean_price_data(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only daily OHLCV fields and normalize the Date column."""
    if df.empty:
        return pd.DataFrame(columns=KEEP_COLUMNS)

    cleaned = df.reset_index().copy()

    if "Date" not in cleaned.columns:
        first_col = cleaned.columns[0]
        cleaned = cleaned.rename(columns={first_col: "Date"})

    cleaned["Date"] = pd.to_datetime(cleaned["Date"]).dt.strftime("%Y-%m-%d")

    available_columns = [col for col in KEEP_COLUMNS if col in cleaned.columns]
    cleaned = cleaned[available_columns]

    if "Volume" in cleaned.columns:
        cleaned["Volume"] = cleaned["Volume"].fillna(0).astype("int64")

    for col in ["Open", "High", "Low", "Close"]:
        if col in cleaned.columns:
            cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce")

    cleaned = cleaned.dropna(subset=["Date", "Open", "High", "Low", "Close"])
    cleaned = cleaned.drop_duplicates(subset=["Date"])
    cleaned = cleaned.sort_values("Date").reset_index(drop=True)

    return cleaned[KEEP_COLUMNS]


def fetch_history_from_yahoo(symbol: str, start_date: str) -> pd.DataFrame:
    """Download daily history from Yahoo Finance."""
    ticker = yf.Ticker(symbol)
    df = ticker.history(
        start=start_date,
        interval="1d",
        auto_adjust=False,
        actions=False,
    )
    return clean_price_data(df)


def download_full_history(symbol: str, start_date: str) -> pd.DataFrame:
    """Download full history and save it to a local CSV."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    df = fetch_history_from_yahoo(symbol, start_date)
    csv_path = get_csv_path(symbol)
    df.to_csv(csv_path, index=False)

    print(f"[FULL] {symbol}: saved {len(df)} rows to {csv_path}")
    return df


def update_local_csv(symbol: str) -> pd.DataFrame:
    """Create the CSV if missing, otherwise append only new rows."""
    csv_path = get_csv_path(symbol)
    start_date = SYMBOLS[symbol]

    if not csv_path.exists():
        return download_full_history(symbol, start_date)

    local_df = pd.read_csv(csv_path)
    if local_df.empty:
        return download_full_history(symbol, start_date)

    local_df["Date"] = pd.to_datetime(local_df["Date"]).dt.strftime("%Y-%m-%d")
    last_date = pd.to_datetime(local_df["Date"]).max()
    next_date = (last_date + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    today = pd.Timestamp.today().normalize()

    if pd.to_datetime(next_date) >= today:
        print(f"[SKIP] {symbol}: already up to date through {last_date.strftime('%Y-%m-%d')}")
        return local_df

    new_df = fetch_history_from_yahoo(symbol, next_date)

    if new_df.empty:
        print(f"[UPDATE] {symbol}: added 0 new rows, total {len(local_df)} rows")
        return local_df

    combined_df = pd.concat([local_df, new_df], ignore_index=True)
    combined_df = clean_price_data(combined_df)
    combined_df.to_csv(csv_path, index=False)

    added_rows = len(combined_df) - len(local_df)
    print(
        f"[UPDATE] {symbol}: added {max(added_rows, 0)} new rows, "
        f"total {len(combined_df)} rows"
    )
    return combined_df


def batch_update_all() -> None:
    """Update all configured symbols one by one."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    for symbol in SYMBOLS:
        try:
            update_local_csv(symbol)
        except Exception as exc:
            print(f"[ERROR] {symbol}: {exc}")


def main() -> None:
    batch_update_all()


if __name__ == "__main__":
    main()
