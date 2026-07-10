# Portfolio Strategy Launchpad

A Python backtesting lab for comparing investment strategies side by side. Design custom rules, tune parameters in a browser dashboard, and measure performance against built-in baselines over any historical period.

## What it does

- **Backtest** one or many strategies on real market data (Yahoo Finance via `yfinance`)
- **Compare** strategies apples-to-apples with shared starting capital and optional recurring contributions
- **Visualize** portfolio value, drawdowns, uninvested cash, and major market events (GFC, COVID, dot-com, etc.)
- **Extend** by dropping a new strategy file into `portfolio_sim/strategies/` — the app discovers it automatically

## Quick start

**Requirements:** Python 3.9+

```bash
pip install -r requirements.txt
streamlit run app.py
```

The dashboard opens in your browser. Pick strategies in the sidebar, adjust parameters, set a date range and initial cash, then click **Run Backtest**.

### Other entry points

| Command | Purpose |
|---|---|
| `python run_backtest.py` | Script-based comparison (saves `backtest_comparison.png`) |
| `python test_strategy.py --list` | List all registered strategies |
| `python test_strategy.py DCA` | Fast single-strategy test on synthetic data |
| `python test_synthetic.py` | Sanity check without internet |
| `python create_strategy.py my_idea` | Scaffold a new custom strategy |

## Dashboard features

- **Strategy picker** — built-in baselines plus your custom `JCCustom` strategies
- **Auto-generated controls** — sliders, inputs, and dropdowns built from each strategy's `param_spec`
- **Starting holdings** — seed a strategy with existing positions (ticker + % of portfolio) on day one
- **Recurring income** — simulate periodic contributions (weekly, monthly, etc.) added equally to every strategy
- **Metrics table** — CAGR, max drawdown, Sharpe ratio, and end-of-period uninvested cash
- **Interactive charts** — Plotly value/drawdown chart with optional cash overlay and log scale
- **Trade logs** — per-strategy buy/sell history

Every strategy in a comparison run shares the same **initial cash** and **recurring income**, so differences in results come from how each strategy deploys capital — not from unequal funding.

## Project structure

```
PortfolioStrategyLaunchpad/
├── app.py                          # Streamlit dashboard (main UI)
├── run_backtest.py                 # Script-based backtest example
├── test_strategy.py                # Fast CLI harness for one strategy
├── test_synthetic.py               # Offline engine sanity check
├── create_strategy.py              # Strategy file generator
├── requirements.txt
└── portfolio_sim/
    ├── data/
    │   ├── loader.py               # yfinance downloader + local CSV cache
    │   ├── ticker_guide.py         # Ticker reference for the UI
    │   └── cache/                  # Cached price data (gitignored)
    ├── engine/
    │   ├── portfolio.py            # Cash, positions, trade log
    │   └── backtest.py             # Day-by-day simulation loop
    ├── strategies/
    │   ├── base.py                 # Strategy base class
    │   ├── registry.py             # Auto-discovery + shared helpers
    │   ├── _strategy_template.py   # Copy-paste scaffold
    │   └── *.py                    # Individual strategy implementations
    └── analysis/
        ├── metrics.py              # CAGR, drawdown, Sharpe, etc.
        ├── plotting.py             # Matplotlib charts (used by run_backtest.py)
        └── events.py               # Historical market events for chart shading
```

## Built-in strategies

| Name | Description |
|---|---|
| `BuyAndHold` | Invest everything on day one, hold |
| `DCA` | Fixed dollar amount on a regular schedule (optionally split across tickers) |
| `GoldenCross` | All-in on 50/200-day golden cross, to cash on death cross |
| `TrendFollowing` | Stay invested while price is above its N-day moving average |
| `Rebalancing` | Maintain a target mix (e.g. 60/40 stocks/bonds), rebalance periodically |
| `ValueAveraging` | Target a growth path — buy more when behind, less when ahead |
| `MeanReversion` | Buy on statistical dips (z-score), sell on reversion |

Custom strategies (files ending in `JCCustom` or marked `is_custom = True`) appear in a separate section of the picker.

## Create a custom strategy

### Option 1 — generator (fastest)

```bash
python create_strategy.py my_idea
python create_strategy.py dip_idea --template buy_the_dip
python create_strategy.py trend_idea --template moving_average
python test_strategy.py MyIdeaJCCustom
```

| Template | Best for |
|---|---|
| `scheduled_buy` | Buy a ticker for a fixed dollar amount every N trading days |
| `buy_the_dip` | Buy after a drop of X% from a trailing high |
| `moving_average` | Stay invested above a moving average, move to cash below |

After the smoke test passes, refresh Streamlit — the strategy appears in the picker.

### Option 2 — subclass `Strategy`

Implement `on_data(date, history, portfolio)`. It runs once per trading day with all data up to and including that day (no lookahead) and a live `Portfolio` to trade through.

```python
from portfolio_sim.strategies.base import Strategy

class MyStrategyJCCustom(Strategy):
    name = "MyStrategyJCCustom"
    display_name = "My Strategy"
    is_custom = True
    description = "Brief description shown in the UI."
    param_spec = {
        "ticker": {"label": "Ticker", "type": "ticker", "default": "SPY"},
        "threshold": {"label": "Distance from MA", "type": "percent", "default": 10.0,
                      "min": 1.0, "max": 50.0, "step": 1.0},
    }

    def __init__(self, ticker="SPY", threshold=0.10):
        super().__init__(ticker=ticker, threshold=threshold)
        self.ticker = ticker
        self.threshold = threshold

    def on_data(self, date, history, portfolio):
        df = history.get(self.ticker)
        if df is None or len(df) < 200:
            return

        price = df["Close"].iloc[-1]
        ma200 = df["Close"].rolling(200).mean().iloc[-1]

        if price > ma200 * (1 + self.threshold):
            portfolio.sell(date, self.ticker, price, dollar_amount=1000)
        elif price < ma200 * (1 - self.threshold):
            portfolio.buy(date, self.ticker, price, dollar_amount=1000)
```

Save as a new `.py` file in `portfolio_sim/strategies/`. No manual registration needed.

### `param_spec` types

| Type | Widget | Notes |
|---|---|---|
| `ticker` | Text input | Uppercased automatically |
| `text` | Text input | Plain string |
| `number` | Number input | Supports `min`, `max`, `step` |
| `percent` | Slider (0–100) | Passed to constructor as 0–1 fraction |
| `select` | Dropdown | Requires `"options"` list |
| `allocation` | Multi-ticker table | Split purchases across tickers |

## CLI testing

```bash
# List strategies
python test_strategy.py --list

# Quick test on synthetic data (instant, no network)
python test_strategy.py DCA
python test_strategy.py DCA --param amount=750 --param frequency_days=10

# Real market data
python test_strategy.py GoldenCross --real --ticker SPY --start 2015-01-01

# With recurring income
python test_strategy.py DCA --real --income 500 --income-frequency monthly
```

For `"percent"` params, pass human-readable values on the CLI (`drop_pct=7` means 7%, stored as `0.07`).

## Multi-ticker strategies

`history` in `on_data()` is a dict keyed by ticker. Pass multiple series to the backtester:

```python
data = {
    "SPY": get_price_data("SPY", "2010-01-01"),
    "TLT": get_price_data("TLT", "2010-01-01"),
}
```

Useful for rotation, rebalancing, and diversified DCA strategies.

## Limitations

- Prices use `auto_adjust=True` from yfinance (split/dividend adjusted)
- No transaction costs, slippage, taxes, or bid/ask spread
- `Portfolio.buy()` / `.sell()` cap trades at available cash/shares
- Price data caches locally in `portfolio_sim/data/cache/` — delete a CSV or pass `force_refresh=True` to re-download

## License

Personal project — use and modify freely.
