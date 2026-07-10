from portfolio_sim.strategies.base import Strategy


class GoldenCross(Strategy):
    """Classic trend-following signal: go fully invested when the short
    moving average of `ticker` crosses above the long one (a "golden
    cross"), move to cash when it crosses back below (a "death cross").
    The signal is always based on `ticker`, but you can diversify what
    actually gets bought when it fires via `allocation`."""

    name = "GoldenCross"
    display_name = "Golden Cross Trend"
    description = ("Go all-in when the short moving average crosses above the long one; "
                    "move to cash when it crosses back below.")
    param_spec = {
        "ticker": {"label": "Signal ticker", "type": "ticker", "default": "SPY",
                   "help": "The moving-average crossover is measured on this ticker."},
        "short_window": {"label": "Short MA (days)", "type": "number", "default": 50,
                          "min": 5, "max": 150, "step": 1},
        "long_window": {"label": "Long MA (days)", "type": "number", "default": 200,
                         "min": 50, "max": 400, "step": 1},
        "allocation": {"label": "Buy allocation", "type": "allocation", "default": {"SPY": 100.0},
                       "help": "What to actually buy when the signal goes long. Add rows to diversify."},
        "allocation_mode": {"label": "Allocation mode", "type": "select",
                             "options": ["percent", "dollar"], "default": "percent",
                             "help": "percent = weights of available cash. dollar = fixed $ per ticker."},
    }

    def __init__(self, ticker="SPY", short_window=50, long_window=200, allocation=None, allocation_mode="percent"):
        super().__init__(ticker=ticker, short_window=short_window, long_window=long_window,
                          allocation=allocation, allocation_mode=allocation_mode)
        self.ticker = ticker
        self.short_window = short_window
        self.long_window = long_window
        self.allocation = allocation or {ticker: 100.0}
        self.allocation_mode = allocation_mode
        self._invested = False

    def on_data(self, date, history, portfolio):
        df = history.get(self.ticker)
        if df is None or len(df) < self.long_window + 1:
            return

        closes = df["Close"]
        short_ma = closes.tail(self.short_window).mean()
        long_ma = closes.tail(self.long_window).mean()
        # Previous day's averages, to detect the actual crossing (not just the state)
        prev_closes = closes.iloc[:-1]
        prev_short_ma = prev_closes.tail(self.short_window).mean()
        prev_long_ma = prev_closes.tail(self.long_window).mean()

        golden_cross = prev_short_ma <= prev_long_ma and short_ma > long_ma
        death_cross = prev_short_ma >= prev_long_ma and short_ma < long_ma

        if golden_cross and not self._invested:
            self.buy_allocation(date, portfolio, history, total_amount=portfolio.cash)
            self._invested = True
        elif death_cross and self._invested:
            self.sell_allocation(date, portfolio, history)
            self._invested = False
