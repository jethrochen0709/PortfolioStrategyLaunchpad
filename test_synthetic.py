"""
Sanity-checks the engine using a synthetic price series (a random walk with
a couple of engineered crashes), since this environment has no internet
access to actually hit Yahoo Finance. Run this to confirm the logic is
correct before you run the real thing with yfinance on your own machine.
"""
import numpy as np
import pandas as pd

from portfolio_sim.engine.backtest import Backtester
from portfolio_sim.analysis.metrics import compute_metrics, print_metrics
from portfolio_sim.analysis.events import events_in_range
from portfolio_sim.strategies.registry import STRATEGY_REGISTRY, param_default_kwargs

np.random.seed(42)

# Build ~6 years of fake daily data with a slow uptrend, noise, and two
# engineered crashes (~-25% and ~-15%) so we can confirm BuyTheDip actually
# fires and doesn't machine-gun buys during a single drawdown.
n_days = 252 * 6
dates = pd.bdate_range("2018-01-02", periods=n_days)

daily_returns = np.random.normal(0.0003, 0.01, n_days)

# Crash 1: days 300-330, total ~-25%
daily_returns[300:330] = np.random.normal(-0.012, 0.01, 30)
# Recovery bump
daily_returns[330:360] = np.random.normal(0.006, 0.01, 30)

# Crash 2: days 900-915, total ~-15%
daily_returns[900:915] = np.random.normal(-0.012, 0.008, 15)

prices = 100 * np.cumprod(1 + daily_returns)
df = pd.DataFrame({
    "Open": prices, "High": prices * 1.005, "Low": prices * 0.995,
    "Close": prices, "Volume": 1_000_000
}, index=dates)

# Second synthetic series, lower vol, to act as a "bond" for the Rebalancing strategy
bond_returns = np.random.normal(0.0001, 0.003, n_days)
bond_prices = 100 * np.cumprod(1 + bond_returns)
bond_df = pd.DataFrame({
    "Open": bond_prices, "High": bond_prices * 1.001, "Low": bond_prices * 0.999,
    "Close": bond_prices, "Volume": 500_000
}, index=dates)

data = {"TEST": df, "BOND": bond_df}
INITIAL_CASH = 10000

print(f"Synthetic price series: {len(df)} trading days, "
      f"start=${prices[0]:.2f}, end=${prices[-1]:.2f}, "
      f"min=${prices.min():.2f} (day {int(prices.argmin())})")

for name, strategy_cls in STRATEGY_REGISTRY.items():
    kwargs = param_default_kwargs(
        strategy_cls,
        ticker="TEST",
        ticker_map={"ticker_b": "BOND", "secondary_ticker": "BOND"},
    )
    strat = strategy_cls(**kwargs)
    bt = Backtester(data, initial_cash=INITIAL_CASH)
    portfolio = bt.run(strat)
    history = portfolio.history_df()
    metrics = compute_metrics(history, INITIAL_CASH)
    print_metrics(name, metrics)

    trades = portfolio.trades_df()
    total_value = history["total_value"].iloc[-1]
    print(f"  # of trades: {len(trades)}, cash remaining: ${portfolio.cash:,.2f}, "
          f"final value: ${total_value:,.2f}")
    assert total_value > 0, f"{name} ended with non-positive value - bug!"
    assert portfolio.cash >= -1e-6, f"{name} went cash-negative - bug!"

print("\nEvents overlapping this date range:")
for e in events_in_range(dates[0], dates[-1]):
    print(f"  {e['name']}: {e['start']} to {e['end']}")

print("\nAll sanity checks ran without errors.")
