from portfolio_sim.strategies.base import Strategy


class Rebalancing(Strategy):
    """Classic multi-asset allocation (e.g. the famous "60/40" stocks/bonds
    mix): splits starting cash according to target weights, then
    periodically sells whatever has drifted above target and buys whatever
    has drifted below to restore the target mix."""

    name = "Rebalancing"
    display_name = "Two-Asset Rebalancing"
    description = "Hold a target mix of two assets (e.g. 60% stocks / 40% bonds), rebalancing back to target on a schedule."
    param_spec = {
        "ticker_a": {"label": "Asset A ticker", "type": "ticker", "default": "SPY"},
        "ticker_b": {"label": "Asset B ticker", "type": "ticker", "default": "TLT"},
        "weight_a": {"label": "Asset A weight", "type": "percent", "default": 60.0,
                     "min": 0.0, "max": 100.0, "step": 5.0},
        "rebalance_frequency_days": {"label": "Rebalance every N days", "type": "number", "default": 63,
                                      "min": 5, "max": 252, "step": 1,
                                      "help": "~21 = monthly, ~63 = quarterly, ~252 = yearly"},
    }

    def __init__(self, ticker_a="SPY", ticker_b="TLT", weight_a=0.6, rebalance_frequency_days=63):
        super().__init__(ticker_a=ticker_a, ticker_b=ticker_b, weight_a=weight_a,
                          rebalance_frequency_days=rebalance_frequency_days)
        self.ticker_a = ticker_a
        self.ticker_b = ticker_b
        self.weight_a = weight_a
        self.weight_b = 1 - weight_a
        self.rebalance_frequency_days = rebalance_frequency_days
        self._day_count = 0
        self._initialized = False

    def on_data(self, date, history, portfolio):
        df_a = history.get(self.ticker_a)
        df_b = history.get(self.ticker_b)
        if df_a is None or df_b is None or len(df_a) == 0 or len(df_b) == 0:
            return

        price_a = df_a["Close"].iloc[-1]
        price_b = df_b["Close"].iloc[-1]

        if not self._initialized:
            starting_cash = portfolio.cash
            portfolio.buy(date, self.ticker_a, price_a, dollar_amount=starting_cash * self.weight_a)
            portfolio.buy(date, self.ticker_b, price_b, dollar_amount=portfolio.cash)  # rest goes to B
            self._initialized = True
            self._day_count += 1
            return

        if self._day_count % self.rebalance_frequency_days == 0:
            value_a = portfolio.positions.get(self.ticker_a, 0) * price_a
            value_b = portfolio.positions.get(self.ticker_b, 0) * price_b
            total = value_a + value_b + portfolio.cash
            target_a = total * self.weight_a
            target_b = total * self.weight_b

            # Sell overweight side(s) first to free up cash, then buy underweight side(s)
            if value_a > target_a:
                portfolio.sell(date, self.ticker_a, price_a, dollar_amount=value_a - target_a)
            if value_b > target_b:
                portfolio.sell(date, self.ticker_b, price_b, dollar_amount=value_b - target_b)

            value_a = portfolio.positions.get(self.ticker_a, 0) * price_a
            value_b = portfolio.positions.get(self.ticker_b, 0) * price_b
            if value_a < target_a:
                portfolio.buy(date, self.ticker_a, price_a, dollar_amount=target_a - value_a)
            if value_b < target_b:
                portfolio.buy(date, self.ticker_b, price_b, dollar_amount=target_b - value_b)

        self._day_count += 1
