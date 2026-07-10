from portfolio_sim.strategies.base import Strategy


class MeanReversion(Strategy):
    """Buys when price is unusually far *below* its recent average
    (measured in standard deviations - a "z-score"), and takes profit
    once price reverts back toward the average. A popular short-to-medium
    term counter-trend approach."""

    name = "MeanReversion"
    display_name = "Mean Reversion"
    description = "Buy when price is statistically far below its recent average (z-score); sell once it reverts back."
    param_spec = {
        "ticker": {"label": "Ticker", "type": "ticker", "default": "SPY"},
        "window": {"label": "Lookback window (days)", "type": "number", "default": 20,
                   "min": 5, "max": 120, "step": 1},
        "entry_z": {"label": "Entry z-score (buy when below)", "type": "number", "default": -2.0,
                    "min": -4.0, "max": -0.5, "step": 0.1},
        "exit_z": {"label": "Exit z-score (sell when above)", "type": "number", "default": 0.0,
                   "min": -1.0, "max": 2.0, "step": 0.1},
        "trade_amount": {"label": "Trade size ($)", "type": "number", "default": 1000,
                          "min": 10, "max": 100000, "step": 50},
    }

    def __init__(self, ticker="SPY", window=20, entry_z=-2.0, exit_z=0.0, trade_amount=1000):
        super().__init__(ticker=ticker, window=window, entry_z=entry_z, exit_z=exit_z,
                          trade_amount=trade_amount)
        self.ticker = ticker
        self.window = window
        self.entry_z = entry_z
        self.exit_z = exit_z
        self.trade_amount = trade_amount
        self._in_position = False

    def on_data(self, date, history, portfolio):
        df = history.get(self.ticker)
        if df is None or len(df) < self.window + 1:
            return

        closes = df["Close"].tail(self.window)
        mean = closes.mean()
        std = closes.std()
        if not std or std != std:  # zero or NaN
            return

        price = df["Close"].iloc[-1]
        z = (price - mean) / std

        if z <= self.entry_z and not self._in_position:
            portfolio.buy(date, self.ticker, price, dollar_amount=self.trade_amount)
            self._in_position = True
        elif z >= self.exit_z and self._in_position:
            portfolio.sell(date, self.ticker, price, shares=portfolio.positions.get(self.ticker, 0))
            self._in_position = False
