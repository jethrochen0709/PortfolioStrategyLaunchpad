from portfolio_sim.strategies.base import Strategy


class CustomScheduledBuyJCCustom(Strategy):
    """Simple personal strategy: buy a chosen ticker with a chosen dollar
    amount on a fixed trading-day schedule."""

    name = "CustomScheduledBuyJCCustom"
    display_name = "Custom Scheduled Buy"
    is_custom = True
    description = "Choose what ticker to buy, how many dollars to buy, and how often to buy it."
    param_spec = {
        "ticker": {"label": "What to buy", "type": "ticker", "default": "SPY"},
        "buy_amount": {"label": "Buy amount ($)", "type": "number", "default": 500,
                       "min": 10, "max": 100000, "step": 50},
        "frequency_days": {"label": "Buy every N trading days", "type": "number", "default": 21,
                           "min": 1, "max": 252, "step": 1,
                           "help": "~5 = weekly, ~21 = monthly, ~63 = quarterly"},
    }

    def __init__(self, ticker="SPY", buy_amount=500, frequency_days=21):
        super().__init__(ticker=ticker, buy_amount=buy_amount, frequency_days=frequency_days)
        self.ticker = ticker
        self.buy_amount = buy_amount
        self.frequency_days = frequency_days
        self._day_count = 0

    def on_data(self, date, history, portfolio):
        df = history.get(self.ticker)
        if df is None or len(df) == 0:
            return

        if self._day_count % self.frequency_days == 0:
            price = df["Close"].iloc[-1]
            portfolio.buy(date, self.ticker, price, dollar_amount=self.buy_amount)

        self._day_count += 1
