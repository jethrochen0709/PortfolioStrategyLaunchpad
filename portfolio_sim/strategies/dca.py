from portfolio_sim.strategies.base import Strategy


class DollarCostAveraging(Strategy):
    """Invests a fixed dollar amount every `frequency_days` trading days,
    regardless of price. Stops once cash runs out."""

    name = "DCA"
    display_name = "Dollar-Cost Averaging"
    description = "Invest a fixed dollar amount on a regular schedule, regardless of price."
    param_spec = {
        "ticker": {"label": "Ticker", "type": "ticker", "default": "SPY"},
        "amount": {"label": "Amount per buy ($)", "type": "number", "default": 500,
                   "min": 10, "max": 100000, "step": 10},
        "frequency_days": {"label": "Buy every N trading days", "type": "number", "default": 21,
                            "min": 1, "max": 252, "step": 1,
                            "help": "~21 = monthly, ~5 = weekly, ~63 = quarterly"},
    }

    def __init__(self, ticker="SPY", amount=500, frequency_days=21):
        super().__init__(ticker=ticker, amount=amount, frequency_days=frequency_days)
        self.ticker = ticker
        self.amount = amount
        self.frequency_days = frequency_days
        self._day_count = 0

    def on_data(self, date, history, portfolio):
        df = history.get(self.ticker)
        if df is None or len(df) == 0:
            return

        if self._day_count % self.frequency_days == 0:
            price = df["Close"].iloc[-1]
            portfolio.buy(date, self.ticker, price, dollar_amount=self.amount)

        self._day_count += 1
