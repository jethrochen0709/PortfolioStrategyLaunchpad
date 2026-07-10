from portfolio_sim.strategies.base import Strategy


class BuyTheDip(Strategy):
    """
    Tracks the trailing high over the last `lookback` trading days. Every
    time the close is down `drop_pct` or more from that high, invests
    `buy_amount` dollars.

    To avoid buying every single day while price sits in a deep drawdown,
    the strategy "re-arms" only once price recovers back above the trigger
    level - so a 20%-long crash triggers one buy at -5%, not 300 of them.
    """

    name = "BuyTheDip"
    display_name = "Buy the Dip"
    description = "Buy a fixed amount every time price falls by your chosen percentage from its trailing high."
    param_spec = {
        "ticker": {"label": "Ticker", "type": "ticker", "default": "SPY"},
        "drop_pct": {"label": "Buy after drop (%)", "type": "percent", "default": 5.0,
                     "min": 0.5, "max": 80.0, "step": 0.25,
                     "help": "Example: 5 means buy after a 5% drop from the trailing high."},
        "buy_amount": {"label": "Buy amount ($)", "type": "number", "default": 1000,
                       "min": 10, "max": 100000, "step": 50},
        "lookback": {"label": "Trailing high lookback (days)", "type": "number", "default": 252,
                     "min": 10, "max": 1000, "step": 1},
    }

    def __init__(self, ticker="SPY", drop_pct=0.05, buy_amount=1000, lookback=252):
        super().__init__(ticker=ticker, drop_pct=drop_pct, buy_amount=buy_amount, lookback=lookback)
        self.ticker = ticker
        self.drop_pct = drop_pct
        self.buy_amount = buy_amount
        self.lookback = lookback
        self._armed = True  # True = eligible to buy on the next qualifying dip

    def on_data(self, date, history, portfolio):
        df = history.get(self.ticker)
        if df is None or len(df) < 2:
            return

        window = df["Close"].tail(self.lookback)
        rolling_high = window.max()
        price = df["Close"].iloc[-1]

        if rolling_high <= 0:
            return

        drop = (rolling_high - price) / rolling_high

        if drop >= self.drop_pct:
            if self._armed:
                portfolio.buy(date, self.ticker, price, dollar_amount=self.buy_amount)
                self._armed = False
        else:
            # Price has recovered back above the trigger level - re-arm
            self._armed = True
