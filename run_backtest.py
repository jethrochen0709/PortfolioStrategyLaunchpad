"""
Example entry point.

Run with:
    python run_backtest.py

Edit the CONFIG section below to change the ticker, date range, starting
cash, and which strategies to compare. Add new strategies by subclassing
Strategy in portfolio_sim/strategies/ - see base.py for the template.
"""
from portfolio_sim.data.loader import get_price_data
from portfolio_sim.engine.backtest import Backtester
from portfolio_sim.analysis.metrics import compute_metrics, print_metrics
from portfolio_sim.analysis.plotting import plot_comparison

from portfolio_sim.strategies.buy_and_hold import BuyAndHold
from portfolio_sim.strategies.dca import DollarCostAveraging

# ---------------------------- CONFIG ----------------------------
TICKER = "SPY"
START = "2000-01-01"
END = None            # None = through the most recent trading day
INITIAL_CASH = 10000

STRATEGIES = [
    BuyAndHold(ticker=TICKER),
    DollarCostAveraging(ticker=TICKER, amount=500, frequency_days=21),  # ~monthly
]
# ------------------------------------------------------------------


def main():
    print(f"Downloading/loading {TICKER} data from {START}...")
    prices = get_price_data(TICKER, START, END)
    data = {TICKER: prices}

    results = {}
    for strategy in STRATEGIES:
        bt = Backtester(data, initial_cash=INITIAL_CASH)
        portfolio = bt.run(strategy)
        history = portfolio.history_df()
        results[strategy.name] = history

        metrics = compute_metrics(history, INITIAL_CASH)
        print_metrics(strategy.name, metrics)

    plot_comparison(results, save_path="backtest_comparison.png")


if __name__ == "__main__":
    main()
