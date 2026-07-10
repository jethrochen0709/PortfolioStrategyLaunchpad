from portfolio_sim.strategies.base import Strategy


class GoldenCross(Strategy):
    """Classic trend-following signal: go fully invested when the short
    moving average crosses above the long one (a "golden cross"), move to
    cash when it crosses back below (a "death cross")."""

    name = "GoldenCross"
    display_name = "Golden Cross Trend"
    description = ("Go all-in when the short moving average crosses above the long one; "
                    "move to cash when it crosses back below.")
    param_spec = {
        "ticker": {"label": "Ticker", "type": "ticker", "default": "SPY"},
        "short_window": {"label": "Short MA (days)", "type": "number", "default": 50,
                          "min": 5, "max": 150, "step": 1},
        "long_window": {"label": "Long MA (days)", "type": "number", "default": 200,
                         "min": 50, "max": 400, "step": 1},
    }

    def __init__(self, ticker="SPY", short_window=50, long_window=200):
        super().__init__(ticker=ticker, short_window=short_window, long_window=long_window)
        self.ticker = ticker
        self.short_window = short_window
        self.long_window = long_window
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
        price = closes.iloc[-1]

        golden_cross = prev_short_ma <= prev_long_ma and short_ma > long_ma
        death_cross = prev_short_ma >= prev_long_ma and short_ma < long_ma

        if golden_cross and not self._invested:
            portfolio.buy(date, self.ticker, price, dollar_amount=portfolio.cash)
            self._invested = True
        elif death_cross and self._invested:
            portfolio.sell(date, self.ticker, price, shares=portfolio.positions.get(self.ticker, 0))
            self._invested = False
