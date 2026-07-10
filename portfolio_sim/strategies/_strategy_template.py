"""
Copy this file to `portfolio_sim/strategies/my_strategy.py`, rename the class,
and set a unique `name` ending in JCCustom. The strategy registry will discover
it automatically.

Want to diversify your buys across multiple tickers instead of just one? Add
an "allocation" + "allocation_mode" param_spec entry (see base.py's docstring
for the exact shape) and call `self.buy_allocation(...)` /
`self.sell_allocation(...)` instead of `portfolio.buy()` / `portfolio.sell()`
directly - see dca.py or golden_cross.py for worked examples.
"""
from portfolio_sim.strategies.base import Strategy


class MyStrategyJCCustom(Strategy):
    name = "MyStrategyJCCustom"
    display_name = "My Strategy"
    is_custom = True
    description = "Describe the market behavior this strategy is trying to capture."
    param_spec = {
        "ticker": {"label": "Ticker", "type": "ticker", "default": "SPY"},
        "buy_amount": {
            "label": "Buy amount ($)",
            "type": "number",
            "default": 1000,
            "min": 10,
            "max": 100000,
            "step": 50,
        },
        "drop_pct": {
            "label": "Drop trigger",
            "type": "percent",
            "default": 5.0,
            "min": 1.0,
            "max": 50.0,
            "step": 0.5,
            "help": "Displayed as 5%, passed into __init__ as 0.05.",
        },
    }

    def __init__(self, ticker="SPY", buy_amount=1000, drop_pct=0.05):
        super().__init__(ticker=ticker, buy_amount=buy_amount, drop_pct=drop_pct)
        self.ticker = ticker
        self.buy_amount = buy_amount
        self.drop_pct = drop_pct

    def on_data(self, date, history, portfolio):
        df = history.get(self.ticker)
        if df is None or len(df) < 2:
            return

        price = df["Close"].iloc[-1]
        previous_price = df["Close"].iloc[-2]
        one_day_return = (price - previous_price) / previous_price

        if one_day_return <= -self.drop_pct:
            portfolio.buy(date, self.ticker, price, dollar_amount=self.buy_amount)
