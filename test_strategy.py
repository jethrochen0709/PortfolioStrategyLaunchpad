"""
Fast strategy test harness.

Examples:
    python test_strategy.py --list
    python test_strategy.py BuyTheDip
    python test_strategy.py MeanReversion --param window=30 --param entry_z=-1.5
    python test_strategy.py BuyTheDip --real --ticker SPY --start 2015-01-01
"""
import argparse

import numpy as np
import pandas as pd

from portfolio_sim.analysis.metrics import compute_metrics
from portfolio_sim.data.loader import get_price_data
from portfolio_sim.engine.backtest import Backtester
from portfolio_sim.strategies.buy_and_hold import BuyAndHold
from portfolio_sim.strategies.registry import (
    STRATEGY_REGISTRY,
    param_default_kwargs,
    strategy_display_name,
    tickers_from_kwargs,
)


INITIAL_CASH = 10000


def synthetic_price_data(tickers, start="2018-01-02", n_days=252 * 6):
    rng = np.random.default_rng(42)
    dates = pd.bdate_range(start, periods=n_days)
    data = {}

    for i, ticker in enumerate(sorted(tickers)):
        if ticker in {"BOND", "TLT", "IEF", "AGG", "BND"}:
            returns = rng.normal(0.0001, 0.003, n_days)
        else:
            returns = rng.normal(0.0003, 0.01, n_days)
            returns[300:330] = rng.normal(-0.012, 0.01, 30)
            returns[330:360] = rng.normal(0.006, 0.01, 30)
            returns[900:915] = rng.normal(-0.012, 0.008, 15)

        prices = (100 + i * 10) * np.cumprod(1 + returns)
        data[ticker] = pd.DataFrame(
            {
                "Open": prices,
                "High": prices * 1.005,
                "Low": prices * 0.995,
                "Close": prices,
                "Volume": 1_000_000,
            },
            index=dates,
        )

    return data


def coerce_param(raw_value, spec):
    ptype = spec.get("type")
    if ptype == "number":
        default = spec.get("default", 0)
        return int(raw_value) if isinstance(default, int) else float(raw_value)
    if ptype == "percent":
        return float(raw_value) / 100.0
    if ptype == "ticker":
        return raw_value.strip().upper()
    return raw_value


def parse_overrides(raw_params, strategy_cls):
    overrides = {}
    for raw in raw_params:
        if "=" not in raw:
            raise ValueError(f"--param values must look like name=value, got: {raw}")
        name, raw_value = raw.split("=", 1)
        if name not in strategy_cls.param_spec:
            known = ", ".join(strategy_cls.param_spec)
            raise ValueError(f"Unknown param '{name}' for {strategy_cls.name}. Known params: {known}")
        overrides[name] = coerce_param(raw_value, strategy_cls.param_spec[name])
    return overrides


def run_strategy(name, strategy_cls, kwargs, data, initial_cash, income_amount=0, income_frequency="none"):
    strategy = strategy_cls(**kwargs)
    portfolio = Backtester(
        data,
        initial_cash=initial_cash,
        income_amount=income_amount,
        income_frequency=income_frequency,
    ).run(strategy)
    history = portfolio.history_df()
    metrics = compute_metrics(history, initial_cash)
    return portfolio, history, metrics


def format_metrics(name, metrics, trades_count):
    return {
        "Strategy": name,
        "End Value": f"${metrics['end_value']:,.0f}",
        "Total Contributed": f"${metrics['total_contributed']:,.0f}",
        "Net Profit": f"${metrics['net_profit']:,.0f}",
        "Return on Capital": f"{metrics['total_return_pct']:.1f}%",
        "CAGR": f"{metrics['cagr_pct']:.1f}%",
        "Volatility": f"{metrics['volatility_pct']:.1f}%",
        "Sharpe": f"{metrics['sharpe_ratio']:.2f}",
        "Max Drawdown": f"{metrics['max_drawdown_pct']:.1f}%",
        "Trades": trades_count,
    }


def list_strategies():
    for name, cls in STRATEGY_REGISTRY.items():
        print(f"{name} - {strategy_display_name(cls)}: {cls.description}")


def main():
    parser = argparse.ArgumentParser(description="Quickly test one discovered strategy.")
    parser.add_argument("strategy", nargs="?", help="Strategy name, e.g. BuyTheDip")
    parser.add_argument("--list", action="store_true", help="List discovered strategies and exit")
    parser.add_argument("--ticker", default="TEST", help="Primary ticker. Use SPY with --real.")
    parser.add_argument("--secondary-ticker", default="BOND", help="Default for ticker_b-style params")
    parser.add_argument("--start", default="2018-01-02")
    parser.add_argument("--end", default=None)
    parser.add_argument("--cash", type=float, default=INITIAL_CASH)
    parser.add_argument("--income", type=float, default=0, help="Recurring income/contribution amount")
    parser.add_argument(
        "--income-frequency",
        default="none",
        choices=["none", "daily", "weekly", "monthly", "yearly"],
        help="How often recurring income is added",
    )
    parser.add_argument("--real", action="store_true", help="Download real data instead of synthetic data")
    parser.add_argument("--param", action="append", default=[], help="Override constructor param, e.g. --param drop_pct=7")
    parser.add_argument("--no-benchmark", action="store_true", help="Skip automatic Buy & Hold comparison")
    args = parser.parse_args()

    if args.list:
        list_strategies()
        return

    if not args.strategy:
        parser.error("strategy is required unless --list is used")
    if args.strategy not in STRATEGY_REGISTRY:
        known = ", ".join(STRATEGY_REGISTRY)
        parser.error(f"Unknown strategy '{args.strategy}'. Known strategies: {known}")

    strategy_cls = STRATEGY_REGISTRY[args.strategy]
    ticker_map = {"ticker_b": args.secondary_ticker, "secondary_ticker": args.secondary_ticker}
    kwargs = param_default_kwargs(strategy_cls, ticker=args.ticker, ticker_map=ticker_map)
    kwargs.update(parse_overrides(args.param, strategy_cls))

    needed_tickers = tickers_from_kwargs(strategy_cls, kwargs)
    benchmark_ticker = args.ticker.strip().upper()
    if not args.no_benchmark:
        needed_tickers.add(benchmark_ticker)

    if args.real:
        data = {t: get_price_data(t, args.start, args.end) for t in sorted(needed_tickers)}
    else:
        data = synthetic_price_data(needed_tickers, start=args.start)

    rows = []
    portfolio, history, metrics = run_strategy(
        args.strategy,
        strategy_cls,
        kwargs,
        data,
        args.cash,
        income_amount=args.income,
        income_frequency=args.income_frequency,
    )
    rows.append(format_metrics(args.strategy, metrics, len(portfolio.trades_df())))

    if not args.no_benchmark and args.strategy != BuyAndHold.name:
        bh_kwargs = {"ticker": benchmark_ticker}
        bh_portfolio, _, bh_metrics = run_strategy(
            "BuyAndHold",
            BuyAndHold,
            bh_kwargs,
            data,
            args.cash,
            income_amount=args.income,
            income_frequency=args.income_frequency,
        )
        rows.append(format_metrics("BuyAndHold", bh_metrics, len(bh_portfolio.trades_df())))

    print(f"\nData source: {'real' if args.real else 'synthetic'}")
    print(f"Tickers: {', '.join(sorted(needed_tickers))}")
    print(f"Income: ${args.income:,.2f} {args.income_frequency}")
    print(f"Strategy kwargs: {kwargs}\n")
    print(pd.DataFrame(rows).set_index("Strategy").to_string())

    if len(history) == 0:
        raise SystemExit("Strategy produced no history.")
    if history["total_value"].iloc[-1] <= 0:
        raise SystemExit("Strategy ended with a non-positive portfolio value.")
    if portfolio.cash < -1e-6:
        raise SystemExit("Strategy went cash-negative.")


if __name__ == "__main__":
    main()
