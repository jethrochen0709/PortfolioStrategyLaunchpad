"""
Portfolio: tracks cash, share positions, and a full trade log.
Strategies interact with this object via .buy() and .sell() - they never
touch cash/positions directly, which keeps accounting consistent.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional
import pandas as pd


@dataclass
class Trade:
    date: pd.Timestamp
    ticker: str
    action: str  # "buy" or "sell"
    shares: float
    price: float
    amount: float  # dollar amount of the trade


class Portfolio:
    def __init__(self, initial_cash: float):
        self.cash: float = initial_cash
        self.initial_cash: float = initial_cash
        self.contributions: float = 0.0
        self.positions: Dict[str, float] = {}   # ticker -> shares held
        self.trade_log: List[Trade] = []
        self.history: List[dict] = []           # daily snapshots, filled by Backtester

    def deposit(self, date, amount: float):
        """Add outside cash to the portfolio, such as recurring income."""
        if amount is None or amount <= 0:
            return
        self.cash += amount
        self.contributions += amount

    def buy(self, date, ticker: str, price: float,
            dollar_amount: Optional[float] = None, shares: Optional[float] = None):
        """Buy either a fixed dollar amount or a fixed number of shares.
        Automatically caps at available cash - never goes negative."""
        if price is None or price <= 0:
            return

        if dollar_amount is not None:
            dollar_amount = max(0.0, min(dollar_amount, self.cash))
            if dollar_amount <= 0:
                return
            shares = dollar_amount / price
        elif shares is not None:
            dollar_amount = shares * price
            if dollar_amount > self.cash:
                shares = self.cash / price
                dollar_amount = self.cash
            if shares <= 0:
                return
        else:
            raise ValueError("buy() requires either dollar_amount or shares")

        self.cash -= dollar_amount
        self.positions[ticker] = self.positions.get(ticker, 0.0) + shares
        self.trade_log.append(Trade(date, ticker, "buy", shares, price, dollar_amount))

    def sell(self, date, ticker: str, price: float,
             dollar_amount: Optional[float] = None, shares: Optional[float] = None):
        """Sell either a fixed dollar amount or a fixed number of shares.
        Automatically caps at what's actually held."""
        held = self.positions.get(ticker, 0.0)
        if held <= 0 or price is None or price <= 0:
            return

        if shares is not None:
            shares = min(shares, held)
        elif dollar_amount is not None:
            shares = min(dollar_amount / price, held)
        else:
            raise ValueError("sell() requires either dollar_amount or shares")

        if shares <= 0:
            return

        proceeds = shares * price
        self.cash += proceeds
        self.positions[ticker] -= shares
        if self.positions[ticker] <= 1e-9:
            self.positions[ticker] = 0.0
        self.trade_log.append(Trade(date, ticker, "sell", shares, price, proceeds))

    def total_value(self, prices: Dict[str, float]) -> float:
        """Cash + value of all held positions, marked at the given prices."""
        value = self.cash
        for ticker, shares in self.positions.items():
            if shares > 0 and ticker in prices and prices[ticker] is not None:
                value += shares * prices[ticker]
        return value

    def record_snapshot(self, date, prices: Dict[str, float]):
        snap = {
            "date": date,
            "cash": self.cash,
            "total_value": self.total_value(prices),
            "contributions": self.contributions,
            "total_contributed": self.initial_cash + self.contributions,
        }
        for ticker, shares in self.positions.items():
            snap[f"{ticker}_shares"] = shares
            if ticker in prices:
                snap[f"{ticker}_price"] = prices[ticker]
        self.history.append(snap)

    def history_df(self) -> pd.DataFrame:
        if not self.history:
            return pd.DataFrame(columns=["cash", "total_value"])
        return pd.DataFrame(self.history).set_index("date")

    def trades_df(self) -> pd.DataFrame:
        if not self.trade_log:
            return pd.DataFrame(columns=["date", "ticker", "action", "shares", "price", "amount"])
        return pd.DataFrame([t.__dict__ for t in self.trade_log])
