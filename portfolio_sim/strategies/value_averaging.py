from portfolio_sim.strategies.base import Strategy


class ValueAveraging(Strategy):
    """Value averaging (a lesser-known cousin of DCA, popularized by Michael
    Edleson): instead of investing a fixed amount every period, you target a
    fixed *portfolio value growth path* - buying more when you're behind the
    path (e.g. after a drop) and buying less, or even selling, when you're
    ahead of it."""

    name = "ValueAveraging"
    display_name = "Value Averaging"
    description = "Target a fixed portfolio value growth path; buy more when below it, sell when above it."
    param_spec = {
        "ticker": {"label": "Ticker", "type": "ticker", "default": "SPY"},
        "target_growth_per_period": {"label": "Target value growth per period ($)", "type": "number",
                                      "default": 500, "min": 10, "max": 100000, "step": 10},
        "frequency_days": {"label": "Check every N days", "type": "number", "default": 21,
                            "min": 1, "max": 252, "step": 1},
    }

    def __init__(self, ticker="SPY", target_growth_per_period=500, frequency_days=21):
        super().__init__(ticker=ticker, target_growth_per_period=target_growth_per_period,
                          frequency_days=frequency_days)
        self.ticker = ticker
        self.target_growth_per_period = target_growth_per_period
        self.frequency_days = frequency_days
        self._day_count = 0
        self._period_count = 0

    def on_data(self, date, history, portfolio):
        df = history.get(self.ticker)
        if df is None or len(df) == 0:
            return

        if self._day_count % self.frequency_days == 0:
            price = df["Close"].iloc[-1]
            self._period_count += 1
            target_value = self.target_growth_per_period * self._period_count
            current_value = portfolio.positions.get(self.ticker, 0) * price

            diff = target_value - current_value
            if diff > 0:
                portfolio.buy(date, self.ticker, price, dollar_amount=diff)
            elif diff < 0:
                portfolio.sell(date, self.ticker, price, dollar_amount=-diff)

        self._day_count += 1
