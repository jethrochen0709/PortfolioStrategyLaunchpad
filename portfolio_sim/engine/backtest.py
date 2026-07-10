"""
Backtester: walks through historical data one trading day at a time, calling
your strategy's on_data() with only the data available up to (and including)
that day - no lookahead bias - and a live Portfolio it can trade through.
"""
from typing import Dict, Optional
import pandas as pd

from portfolio_sim.engine.portfolio import Portfolio


class Backtester:
    def __init__(
        self,
        data: Dict[str, pd.DataFrame],
        initial_cash: float = 10000,
        income_amount: float = 0,
        income_frequency: str = "none",
    ):
        """
        data: dict of ticker -> DataFrame (indexed by date, must include a
              "Close" column). Supports any number of tickers - strategies
              decide what to do with each one.
        """
        if not data:
            raise ValueError("data must contain at least one ticker's DataFrame")

        self.data = data
        self.initial_cash = initial_cash
        self.income_amount = income_amount
        self.income_frequency = income_frequency
        self.tickers = list(data.keys())

        all_dates = sorted(set().union(*[df.index for df in data.values()]))
        self.dates = all_dates

    def _should_deposit_income(self, date, previous_date) -> bool:
        if self.income_amount <= 0 or self.income_frequency == "none":
            return False
        if previous_date is None:
            return True
        if self.income_frequency == "daily":
            return True
        if self.income_frequency == "weekly":
            return date.isocalendar()[:2] != previous_date.isocalendar()[:2]
        if self.income_frequency == "monthly":
            return (date.year, date.month) != (previous_date.year, previous_date.month)
        if self.income_frequency == "yearly":
            return date.year != previous_date.year
        raise ValueError("income_frequency must be one of: none, daily, weekly, monthly, yearly")

    def run(self, strategy, starting_holdings: Optional[Dict[str, float]] = None) -> Portfolio:
        """
        starting_holdings: optional dict of ticker -> fraction of initial_cash
            (0-1) to buy on day one, before the strategy's own logic runs.
            Lets a strategy start already partly invested (e.g. "I already
            hold 30% VTI") instead of starting 100% in cash. Every strategy
            in a comparison still draws from the same initial_cash, so the
            total investable capital stays uniform across strategies - only
            the starting allocation of that capital differs.
        """
        portfolio = Portfolio(self.initial_cash)
        strategy.setup(self.tickers, portfolio)

        if starting_holdings:
            first_date = self.dates[0]
            for ticker, fraction in starting_holdings.items():
                if not fraction or fraction <= 0:
                    continue
                df = self.data.get(ticker)
                if df is None:
                    continue
                sub = df.loc[:first_date]
                if len(sub) == 0:
                    continue
                price = sub["Close"].iloc[-1]
                dollar_amount = fraction * self.initial_cash
                portfolio.buy(first_date, ticker, price, dollar_amount=dollar_amount)

        previous_date = None
        for date in self.dates:
            if self._should_deposit_income(date, previous_date):
                portfolio.deposit(date, self.income_amount)

            # Data "as of" this date only - prevents any lookahead bias
            history_slice = {}
            prices = {}
            for ticker, df in self.data.items():
                sub = df.loc[:date]
                if len(sub) > 0:
                    history_slice[ticker] = sub
                    prices[ticker] = sub["Close"].iloc[-1]

            strategy.on_data(date, history_slice, portfolio)
            portfolio.record_snapshot(date, prices)
            previous_date = date

        return portfolio
