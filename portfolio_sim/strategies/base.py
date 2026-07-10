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
    #   "ticker"     - text input for a ticker symbol
    #   "text"       - plain text input
    #   "number"     - numeric input (uses min/max/step/default)
    #   "percent"    - slider shown as 0-100%, passed to __init__ as a 0-1 fraction
    #   "select"     - dropdown (needs an "options" list)
    #   "allocation" - editable ticker/value table for splitting a purchase
    #                  across multiple tickers (see below)
    # Example:
    #   param_spec = {
    #       "ticker": {"label": "Ticker", "type": "ticker", "default": "SPY"},
    #       "drop_pct": {"label": "Drop %", "type": "percent", "default": 5.0,
    #                    "min": 1.0, "max": 50.0, "step": 0.5},
    #   }
    #
    # Diversifying a purchase across multiple tickers:
    #   Add an "allocation" param (dict of ticker -> value, defaults to putting
    #   100 into your strategy's main "ticker") plus an "allocation_mode"
    #   select param ("percent" or "dollar"):
    #       "allocation": {"label": "Buy allocation", "type": "allocation",
    #                      "default": {"SPY": 100.0}},
    #       "allocation_mode": {"label": "Allocation mode", "type": "select",
    #                           "options": ["percent", "dollar"], "default": "percent"},
    #   In "percent" mode, values are weights (need not sum to exactly 100 -
    #   they're normalized) applied against whatever dollar amount your
    #   strategy is about to invest. In "dollar" mode, each value is a fixed
    #   dollar amount bought for that ticker directly, independent of any
    #   other buy-amount parameter. Then in on_data(), call
    #   self.buy_allocation(date, portfolio, history, total_amount) instead of
    #   portfolio.buy(...) directly - see buy_allocation()/sell_allocation()
    #   below. The signal that decides *when* to trade can still be based on
    #   a single reference "ticker" - allocation only controls *what gets
    #   bought* once the signal fires.
    param_spec: dict = {}

    def __init__(self, **params):
        self.params = params
        # Convenience defaults so buy_allocation()/sell_allocation() work even
        # for strategies that don't declare an "allocation" param at all.
        if not hasattr(self, "allocation"):
            self.allocation = None
        if not hasattr(self, "allocation_mode"):
            self.allocation_mode = "percent"

    def setup(self, tickers, portfolio):
        """Called once before the backtest starts. Override if you need to
        initialize state based on the tickers involved."""
        pass

    def _resolve_allocation_amounts(self, prices: Dict[str, float], total_amount):
        """Turns self.allocation + self.allocation_mode into a dict of
        ticker -> dollar amount to buy, restricted to tickers we actually
        have a price for today."""
        allocation = self.allocation or {}
        amounts = {}
        if self.allocation_mode == "dollar":
            for ticker, value in allocation.items():
                if ticker in prices and value:
                    amounts[ticker] = float(value)
        else:
            weight_sum = sum(v for v in allocation.values() if v) or 0
            if weight_sum <= 0 or total_amount is None or total_amount <= 0:
                return amounts
            for ticker, value in allocation.items():
                if ticker in prices and value:
                    amounts[ticker] = total_amount * (float(value) / weight_sum)
        return amounts

    def buy_allocation(self, date, portfolio, history: Dict[str, pd.DataFrame], total_amount=None):
        """Buys across every ticker in self.allocation, split by weight
        (percent mode, against total_amount) or by fixed dollar value
        (dollar mode, total_amount ignored). Falls back to buying
        total_amount into self.ticker if no allocation is configured."""
        allocation = self.allocation or {}
        if not allocation:
            ticker = getattr(self, "ticker", None)
            if ticker is None or total_amount is None:
                return
            df = history.get(ticker)
            if df is None or len(df) == 0:
                return
            portfolio.buy(date, ticker, df["Close"].iloc[-1], dollar_amount=total_amount)
            return

        prices = {}
        for ticker in allocation:
            df = history.get(ticker)
            if df is not None and len(df) > 0:
                prices[ticker] = df["Close"].iloc[-1]

        for ticker, amount in self._resolve_allocation_amounts(prices, total_amount).items():
            if amount > 0:
                portfolio.buy(date, ticker, prices[ticker], dollar_amount=amount)

    def sell_allocation(self, date, portfolio, history: Dict[str, pd.DataFrame], total_amount=None):
        """Sells positions in every ticker named in self.allocation (or just
        self.ticker, if no allocation is configured). With total_amount=None
        (the default), sells the *entire* position in each ticker - useful
        for "move fully to cash" signals. With total_amount set, sells a
        split amount the same way buy_allocation() buys one (percent mode:
        weighted share of total_amount; dollar mode: each ticker's own fixed
        amount) - useful for strategies that trim rather than fully exit."""
        allocation = self.allocation or {}
        tickers = list(allocation.keys()) if allocation else [getattr(self, "ticker", None)]
        tickers = [t for t in tickers if t is not None]

        prices = {}
        for ticker in tickers:
            df = history.get(ticker)
            if df is not None and len(df) > 0:
                prices[ticker] = df["Close"].iloc[-1]

        if total_amount is None:
            for ticker in tickers:
                held = portfolio.positions.get(ticker, 0)
                if held > 0 and ticker in prices:
                    portfolio.sell(date, ticker, prices[ticker], shares=held)
            return

        if allocation:
            amounts = self._resolve_allocation_amounts(prices, total_amount)
        else:
            amounts = {tickers[0]: total_amount} if tickers and tickers[0] in prices else {}

        for ticker, amount in amounts.items():
            if amount > 0:
                portfolio.sell(date, ticker, prices[ticker], dollar_amount=amount)

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
