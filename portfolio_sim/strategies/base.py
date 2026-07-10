"""
Base class for all strategies. To build your own, subclass Strategy and
implement on_data() - it's called once per trading day.

Example skeleton:

    class MyStrategy(Strategy):
        name = "MyStrategy"

        def __init__(self, ticker="SPY", some_param=10):
            super().__init__(ticker=ticker, some_param=some_param)
            self.ticker = ticker
            self.some_param = some_param

        def on_data(self, date, history, portfolio):
            df = history.get(self.ticker)
            if df is None or len(df) < 2:
                return
            price = df["Close"].iloc[-1]
            # ... your logic here, then e.g.:
            # portfolio.buy(date, self.ticker, price, dollar_amount=100)
"""
from abc import ABC, abstractmethod
from typing import Dict
import pandas as pd


class Strategy(ABC):
    name = "BaseStrategy"

    # Optional friendlier UI label. Internal strategy selection still uses name.
    display_name = ""

    # Mark custom/personal strategies as True. Names ending in "JCCustom" are
    # also treated as custom by the registry.
    is_custom = False

    # Short human-readable description shown in the UI.
    description = ""

    # Describes each constructor parameter so UIs and test harnesses can
    # auto-generate controls/default kwargs.
    # Supported "type" values:
    #   "ticker" - text input for a ticker symbol
    #   "text"   - plain text input
    #   "number" - numeric input (uses min/max/step/default)
    #   "percent"- slider shown as 0-100%, passed to __init__ as a 0-1 fraction
    #   "select" - dropdown (needs an "options" list)
    # Example:
    #   param_spec = {
    #       "ticker": {"label": "Ticker", "type": "ticker", "default": "SPY"},
    #       "drop_pct": {"label": "Drop %", "type": "percent", "default": 5.0,
    #                    "min": 1.0, "max": 50.0, "step": 0.5},
    #   }
    param_spec: dict = {}

    def __init__(self, **params):
        self.params = params

    def setup(self, tickers, portfolio):
        """Called once before the backtest starts. Override if you need to
        initialize state based on the tickers involved."""
        pass

    @abstractmethod
    def on_data(self, date: pd.Timestamp, history: Dict[str, pd.DataFrame], portfolio):
        """
        date: current date being processed
        history: dict of ticker -> DataFrame containing all data up to and
                 including `date` (never any future data)
        portfolio: the live Portfolio - call portfolio.buy()/portfolio.sell()
                   to act. Do not mutate portfolio.cash/positions directly.
        """
        raise NotImplementedError
