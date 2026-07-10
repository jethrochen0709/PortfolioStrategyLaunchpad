"""Standard backtest performance metrics."""
import numpy as np
import pandas as pd


def compute_metrics(history_df: pd.DataFrame, initial_cash: float, risk_free_rate: float = 0.0) -> dict:
    """
    history_df: the DataFrame from Portfolio.history_df() (must have a
                "total_value" column indexed by date)
    """
    values = history_df["total_value"]
    start_val = initial_cash
    end_val = values.iloc[-1]
    total_contributed = (
        history_df["total_contributed"].iloc[-1]
        if "total_contributed" in history_df.columns
        else initial_cash
    )
    contributions = max(0.0, total_contributed - initial_cash)
    net_profit = end_val - total_contributed

    total_return = (end_val / total_contributed) - 1 if total_contributed > 0 else float("nan")

    days = (values.index[-1] - values.index[0]).days
    years = max(days, 1) / 365.25
    cagr = (end_val / total_contributed) ** (1 / years) - 1 if end_val > 0 and total_contributed > 0 else float("nan")

    daily_returns = values.pct_change().dropna()
    volatility = daily_returns.std() * np.sqrt(252) if len(daily_returns) > 1 else float("nan")

    if volatility and volatility > 0:
        sharpe = ((daily_returns.mean() * 252) - risk_free_rate) / volatility
    else:
        sharpe = float("nan")

    running_max = values.cummax()
    drawdown = (values - running_max) / running_max
    max_drawdown = drawdown.min()

    return {
        "start_value": start_val,
        "end_value": end_val,
        "contributions": contributions,
        "total_contributed": total_contributed,
        "net_profit": net_profit,
        "total_return_pct": total_return * 100,
        "cagr_pct": cagr * 100,
        "volatility_pct": volatility * 100 if volatility == volatility else float("nan"),
        "sharpe_ratio": sharpe,
        "max_drawdown_pct": max_drawdown * 100,
    }


def print_metrics(name: str, metrics: dict):
    print(f"\n=== {name} ===")
    print(f"  Start value:     ${metrics['start_value']:,.2f}")
    print(f"  Contributions:   ${metrics['contributions']:,.2f}")
    print(f"  Total invested:  ${metrics['total_contributed']:,.2f}")
    print(f"  End value:        ${metrics['end_value']:,.2f}")
    print(f"  Net profit:       ${metrics['net_profit']:,.2f}")
    print(f"  Return on capital:{metrics['total_return_pct']:.2f}%")
    print(f"  CAGR:             {metrics['cagr_pct']:.2f}%")
    print(f"  Volatility (ann): {metrics['volatility_pct']:.2f}%")
    print(f"  Sharpe ratio:     {metrics['sharpe_ratio']:.2f}")
    print(f"  Max drawdown:     {metrics['max_drawdown_pct']:.2f}%")
