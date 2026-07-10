from portfolio_sim.strategies.base import Strategy


class ValueAveraging(Strategy):
    """Value averaging (a lesser-known cousin of DCA, popularized by Michael
    Edleson): instead of investing a fixed amount every period, you target a
    fixed *portfolio value growth path* - buying more when you're behind the
    path (e.g. after a drop) and buying less, or even selling, when you're
    ahead of it. By default all of it lives in `ticker`, but `allocation`
    lets you diversify across multiple tickers while still tracking one
    combined growth path."""

    name = "ValueAveraging"
    display_name = "Value Averaging"
    description = "Target a fixed portfolio value growth path; buy more when below it, sell when above it."
    param_spec = {
        "ticker": {"label": "Ticker", "type": "ticker", "default": "SPY",
                   "help": "Used only as the default allocation target below."},
        "target_growth_per_period": {"label": "Target value growth per period ($)", "type": "number",
                                      "default": 500, "min": 10, "max": 100000, "step": 10},
        "frequency_days": {"label": "Check every N days", "type": "number", "default": 21,
                            "min": 1, "max": 252, "step": 1},
        "allocation": {"label": "Buy allocation", "type": "allocation", "default": {"SPY": 100.0},
                       "help": "Split each purchase (or trim) across tickers. Add rows to diversify."},
        "allocation_mode": {"label": "Allocation mode", "type": "select",
                             "options": ["percent", "dollar"], "default": "percent",
                             "help": "percent = weights of the buy/sell amount. dollar = fixed $ per ticker."},
    }

    def __init__(self, ticker="SPY", target_growth_per_period=500, frequency_days=21,
                 allocation=None, allocation_mode="percent"):
        super().__init__(ticker=ticker, target_growth_per_period=target_growth_per_period,
                          frequency_days=frequency_days, allocation=allocation, allocation_mode=allocation_mode)
        self.ticker = ticker
        self.target_growth_per_period = target_growth_per_period
        self.frequency_days = frequency_days
        self.allocation = allocation or {ticker: 100.0}
        self.allocation_mode = allocation_mode
        self._day_count = 0
        self._period_count = 0

    def on_data(self, date, history, portfolio):
        if self._day_count % self.frequency_days == 0:
            self._period_count += 1
            target_value = self.target_growth_per_period * self._period_count

            current_value = 0.0
            for ticker in self.allocation:
                df = history.get(ticker)
                if df is not None and len(df) > 0:
                    current_value += portfolio.positions.get(ticker, 0) * df["Close"].iloc[-1]

            diff = target_value - current_value
            if diff > 0:
                self.buy_allocation(date, portfolio, history, total_amount=diff)
            elif diff < 0:
                self.sell_allocation(date, portfolio, history, total_amount=-diff)

        self._day_count += 1
