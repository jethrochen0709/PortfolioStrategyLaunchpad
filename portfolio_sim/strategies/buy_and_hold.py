from portfolio_sim.strategies.base import Strategy


class BuyAndHold(Strategy):
    """Invests available cash in `ticker` and holds. If recurring income is
    enabled, new cash is invested the next time data is available."""

    name = "BuyAndHold"
    display_name = "Buy & Hold"
    description = "Invest available cash into one ticker and hold. Recurring income is invested as it arrives."
    param_spec = {
        "ticker": {"label": "Ticker", "type": "ticker", "default": "SPY"},
    }

    def __init__(self, ticker="SPY"):
        super().__init__(ticker=ticker)
        self.ticker = ticker

    def on_data(self, date, history, portfolio):
        df = history.get(self.ticker)
        if df is None or len(df) == 0 or portfolio.cash <= 0:
            return
        price = df["Close"].iloc[-1]
        portfolio.buy(date, self.ticker, price, dollar_amount=portfolio.cash)
