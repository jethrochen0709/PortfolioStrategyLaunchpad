from portfolio_sim.strategies.base import Strategy


class DollarCostAveraging(Strategy):
    """Invests a fixed total dollar amount every `frequency_days` trading
    days, regardless of price. By default the full amount goes into
    `ticker`, but `allocation` lets you split each period's purchase across
    multiple tickers (e.g. 70% SPY / 30% VXUS each month). Stops once cash
    runs out."""

    name = "DCA"
    display_name = "Dollar-Cost Averaging"
    description = "Invest a fixed dollar amount on a regular schedule (optionally split across tickers), regardless of price."
    param_spec = {
        "ticker": {"label": "Ticker", "type": "ticker", "default": "SPY",
                   "help": "Used only as the default allocation target below."},
        "amount": {"label": "Amount per buy ($)", "type": "number", "default": 500,
                   "min": 10, "max": 100000, "step": 10,
                   "help": "In percent allocation mode, this is the total split across tickers each period. "
                           "In dollar mode, each ticker's own listed amount is used instead."},
        "frequency_days": {"label": "Buy every N trading days", "type": "number", "default": 21,
                            "min": 1, "max": 252, "step": 1,
                            "help": "~21 = monthly, ~5 = weekly, ~63 = quarterly"},
        "allocation": {"label": "Buy allocation", "type": "allocation", "default": {"SPY": 100.0},
                       "help": "Split each period's purchase across tickers. Add rows to diversify."},
        "allocation_mode": {"label": "Allocation mode", "type": "select",
                             "options": ["percent", "dollar"], "default": "percent",
                             "help": "percent = weights of 'Amount per buy'. dollar = fixed $ per ticker each period."},
    }

    def __init__(self, ticker="SPY", amount=500, frequency_days=21, allocation=None, allocation_mode="percent"):
        super().__init__(ticker=ticker, amount=amount, frequency_days=frequency_days,
                          allocation=allocation, allocation_mode=allocation_mode)
        self.ticker = ticker
        self.amount = amount
        self.frequency_days = frequency_days
        self.allocation = allocation or {ticker: 100.0}
        self.allocation_mode = allocation_mode
        self._day_count = 0

    def on_data(self, date, history, portfolio):
        if self._day_count % self.frequency_days == 0:
            self.buy_allocation(date, portfolio, history, total_amount=self.amount)
        self._day_count += 1
