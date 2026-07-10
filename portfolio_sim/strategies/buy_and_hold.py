from portfolio_sim.strategies.base import Strategy


class BuyAndHold(Strategy):
    """Invests available cash and holds. By default it all goes into
    `ticker`, but you can diversify the purchase itself across multiple
    tickers via `allocation` (percent-of-cash weights, or fixed dollar
    amounts) - the ticker/moving-average-style signal isn't relevant here
    since this strategy just buys once, but allocation still lets you split
    that one purchase. If recurring income is enabled, new cash is invested
    the same way the next time data is available."""

    name = "BuyAndHold"
    display_name = "Buy & Hold"
    description = "Invest available cash (optionally split across multiple tickers) and hold."
    param_spec = {
        "ticker": {"label": "Ticker", "type": "ticker", "default": "SPY",
                   "help": "Used only as the default allocation target below."},
        "allocation": {"label": "Buy allocation", "type": "allocation", "default": {"SPY": 100.0},
                       "help": "Split each purchase across tickers. Add rows to diversify."},
        "allocation_mode": {"label": "Allocation mode", "type": "select",
                             "options": ["percent", "dollar"], "default": "percent",
                             "help": "percent = weights of available cash. dollar = fixed $ per ticker."},
    }

    def __init__(self, ticker="SPY", allocation=None, allocation_mode="percent"):
        super().__init__(ticker=ticker, allocation=allocation, allocation_mode=allocation_mode)
        self.ticker = ticker
        self.allocation = allocation or {ticker: 100.0}
        self.allocation_mode = allocation_mode

    def on_data(self, date, history, portfolio):
        if portfolio.cash <= 0:
            return
        self.buy_allocation(date, portfolio, history, total_amount=portfolio.cash)
