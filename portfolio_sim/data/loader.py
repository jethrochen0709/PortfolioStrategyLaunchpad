"""
Downloads and locally caches historical price data via yfinance, so you
only hit the network once per ticker (subsequent runs read the CSV cache).

Requires internet access when you run it (this needs to reach Yahoo Finance),
so run this on your own machine, not inside a sandboxed environment.
"""
import os
import pandas as pd

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")


def get_price_data(ticker: str, start: str, end: str = None, force_refresh: bool = False) -> pd.DataFrame:
    """
    Returns a DataFrame indexed by date with columns Open, High, Low, Close, Volume
    (Close is already split/dividend adjusted).

    ticker: e.g. "SPY", "AAPL", "^GSPC"
    start / end: "YYYY-MM-DD" strings. end=None means through the most recent trading day.
    force_refresh: bypass the cache and re-download.
    """
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(CACHE_DIR, f"{ticker.replace('^', '_')}.csv")

    if not force_refresh and os.path.exists(cache_path):
        df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
    else:
        import yfinance as yf
        df = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)

        if df.empty:
            raise ValueError(
                f"No data returned for ticker '{ticker}'. Check the symbol and date range."
            )
        # yfinance sometimes returns MultiIndex columns for a single ticker - flatten them
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df.to_csv(cache_path)

    df = df.sort_index()
    if start:
        df = df.loc[df.index >= pd.Timestamp(start)]
    if end:
        df = df.loc[df.index <= pd.Timestamp(end)]

    return df
