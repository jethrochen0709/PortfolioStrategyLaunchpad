from portfolio_sim.strategies.base import Strategy


class TrendFollowing(Strategy):
    """A well-known "trend filter" approach (popularized for the 200-day
    SMA by researchers like Meb Faber): stay fully invested only while
    `ticker`'s price is above its N-day moving average, and sit in cash
    otherwise. Checked periodically rather than daily to avoid excessive
    whipsaw trading around the line. The signal is always based on
    `ticker`, but `allocation` lets you diversify what actually gets bought
    when the signal goes long."""

    name = "TrendFollowing"
    display_name = "Moving Average Trend"
    description = "Stay invested only while price is above its N-day moving average; sit in cash otherwise."
    param_spec = {
        "ticker": {"label": "Signal ticker", "type": "ticker", "default": "SPY",
                   "help": "The moving-average trend filter is measured on this ticker."},
        "sma_window": {"label": "Moving average window (days)", "type": "number", "default": 200,
                        "min": 20, "max": 400, "step": 1},
        "check_frequency_days": {"label": "Re-check every N days", "type": "number", "default": 21,
                                  "min": 1, "max": 63, "step": 1},
        "allocation": {"label": "Buy allocation", "type": "allocation", "default": {"SPY": 100.0},
                       "help": "What to actually buy while in the market. Add rows to diversify."},
        "allocation_mode": {"label": "Allocation mode", "type": "select",
                             "options": ["percent", "dollar"], "default": "percent",
                             "help": "percent = weights of available cash. dollar = fixed $ per ticker."},
    }

    def __init__(self, ticker="SPY", sma_window=200, check_frequency_days=21,
                 allocation=None, allocation_mode="percent"):
        super().__init__(ticker=ticker, sma_window=sma_window, check_frequency_days=check_frequency_days,
                          allocation=allocation, allocation_mode=allocation_mode)
        self.ticker = ticker
        self.sma_window = sma_window
        self.check_frequency_days = check_frequency_days
        self.allocation = allocation or {ticker: 100.0}
        self.allocation_mode = allocation_mode
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
                self.buy_allocation(date, portfolio, history, total_amount=portfolio.cash)
                self._invested = True
            elif price < sma and self._invested:
                self.sell_allocation(date, portfolio, history)
                self._invested = False

        self._day_count += 1
