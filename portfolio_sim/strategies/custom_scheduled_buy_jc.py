from portfolio_sim.strategies.base import Strategy


class CustomScheduledBuyJCCustom(Strategy):
    """Simple personal strategy: buy a chosen dollar amount on a fixed
    trading-day schedule, optionally split across multiple tickers."""

    name = "CustomScheduledBuyJCCustom"
    display_name = "Custom Scheduled Buy"
    is_custom = True
    description = "Choose what to buy (optionally diversified), how many dollars to buy, and how often to buy it."
    param_spec = {
        "ticker": {"label": "What to buy", "type": "ticker", "default": "SPY",
                   "help": "Used only as the default allocation target below."},
        "buy_amount": {"label": "Buy amount ($)", "type": "number", "default": 500,
                       "min": 10, "max": 100000, "step": 50},
        "frequency_days": {"label": "Buy every N trading days", "type": "number", "default": 21,
                           "min": 1, "max": 252, "step": 1,
                           "help": "~5 = weekly, ~21 = monthly, ~63 = quarterly"},
        "allocation": {"label": "Buy allocation", "type": "allocation", "default": {"SPY": 100.0},
                       "help": "Split each purchase across tickers. Add rows to diversify."},
        "allocation_mode": {"label": "Allocation mode", "type": "select",
                             "options": ["percent", "dollar"], "default": "percent",
                             "help": "percent = weights of 'Buy amount'. dollar = fixed $ per ticker."},
    }

    def __init__(self, ticker="SPY", buy_amount=500, frequency_days=21, allocation=None, allocation_mode="percent"):
        super().__init__(ticker=ticker, buy_amount=buy_amount, frequency_days=frequency_days,
                          allocation=allocation, allocation_mode=allocation_mode)
        self.ticker = ticker
        self.buy_amount = buy_amount
        self.frequency_days = frequency_days
        self.allocation = allocation or {ticker: 100.0}
        self.allocation_mode = allocation_mode
        self._day_count = 0

    def on_data(self, date, history, portfolio):
        if self._day_count % self.frequency_days == 0:
            self.buy_allocation(date, portfolio, history, total_amount=self.buy_amount)
        self._day_count += 1
