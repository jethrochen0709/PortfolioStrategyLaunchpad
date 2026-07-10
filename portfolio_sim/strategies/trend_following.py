from portfolio_sim.strategies.base import Strategy


class TrendFollowing(Strategy):
    """A well-known "trend filter" approach (popularized for the 200-day
    SMA by researchers like Meb Faber): stay fully invested only while
    price is above its N-day moving average, and sit in cash otherwise.
    Checked periodically rather than daily to avoid excessive whipsaw
    trading around the line."""

    name = "TrendFollowing"
    display_name = "Moving Average Trend"
    description = "Stay invested only while price is above its N-day moving average; sit in cash otherwise."
    param_spec = {
        "ticker": {"label": "Ticker", "type": "ticker", "default": "SPY"},
        "sma_window": {"label": "Moving average window (days)", "type": "number", "default": 200,
                        "min": 20, "max": 400, "step": 1},
        "check_frequency_days": {"label": "Re-check every N days", "type": "number", "default": 21,
                                  "min": 1, "max": 63, "step": 1},
    }

    def __init__(self, ticker="SPY", sma_window=200, check_frequency_days=21):
        super().__init__(ticker=ticker, sma_window=sma_window, check_frequency_days=check_frequency_days)
        self.ticker = ticker
        self.sma_window = sma_window
        self.check_frequency_days = check_frequency_days
        self._day_count = 0
        self._invested = False

    def on_data(self, date, history, portfolio):
        df = history.get(self.ticker)
        if df is None or len(df) < self.sma_window + 1:
            return

        if self._day_count % self.check_frequency_days == 0:
            price = df["Close"].iloc[-1]
            sma = df["Close"].tail(self.sma_window).mean()

            if price > sma and not self._invested:
                portfolio.buy(date, self.ticker, price, dollar_amount=portfolio.cash)
                self._invested = True
            elif price < sma and self._invested:
                portfolio.sell(date, self.ticker, price, shares=portfolio.positions.get(self.ticker, 0))
                self._invested = False

        self._day_count += 1
