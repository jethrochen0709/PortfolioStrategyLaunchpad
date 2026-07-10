# Strategy Launchpad

Create custom investing strategies, backtest them over a chosen date range,
and compare them against popular pre-existing strategies side by side.

## Setup

```bash
pip install -r requirements.txt
```

## Quick start - interactive app (recommended)

```bash
streamlit run app.py
```

Opens a dashboard in your browser where you can:
- Pick your `JCCustom` strategy ideas from the sidebar
- Compare them against popular built-in baselines (add `BuyAndHold` to the
  comparison set if you want a benchmark line - there's no separate
  benchmark-ticker control anymore, it's just another strategy)
- Tune every strategy's parameters with sliders/inputs, auto-generated from
  its `param_spec` (amount, frequency, thresholds, tickers, etc.)
- Give each strategy **starting holdings** - a ticker + % of its portfolio it
  already owns on day one (e.g. "already 30% VTI"); whatever isn't allocated
  starts as cash
- Set the date range and a single shared **initial cash** amount - every
  selected strategy is backtested from that same starting capital, so
  comparisons stay apples-to-apples no matter how each strategy chooses to
  deploy it
- Click **Run Backtest** to see a performance summary table (including each
  strategy's end-of-period **uninvested cash**, in dollars and as a % of its
  value), an interactive value + drawdown chart shaded with historical events
  (2008 GFC, COVID crash, dot-com bust, etc.) with an optional overlay of
  each strategy's uninvested cash over time, and per-strategy trade logs

## Quick start - plain script

```bash
python run_backtest.py
```

This downloads SPY data since 2000 (cached locally after the first run),
runs two strategies (Buy & Hold, Dollar-Cost Averaging) against it, prints
performance metrics for each, and saves a comparison chart to
`backtest_comparison.png`.

Edit the `CONFIG` section at the top of `run_backtest.py` to change the
ticker, date range, starting cash, or which strategies run.

## Sanity-check without internet

```bash
python test_synthetic.py
```

Runs the same engine against a generated (fake) price series with two
engineered crashes, so you can confirm the mechanics work even without
network access. Don't use its numbers as real backtest results.

## Fast strategy test loop

```bash
python test_strategy.py --list
python test_strategy.py DCA
python test_strategy.py DCA --param amount=750 --param frequency_days=10
python test_strategy.py GoldenCross --real --ticker SPY --start 2015-01-01
```

`test_strategy.py` runs one strategy from the auto-discovered registry,
defaults to synthetic data for instant feedback, and compares it against
Buy & Hold unless you pass `--no-benchmark`. For `"percent"` params, pass
human percentages on the command line (`drop_pct=7` means 7%, passed to the
strategy as `0.07`).

## Strategy launchpad workflow

Use this when you brainstorm a new strategy and want to get it into the app
quickly:

```bash
python create_strategy.py my_idea
python create_strategy.py dip_idea --template buy_the_dip
python create_strategy.py trend_idea --template moving_average
python test_strategy.py MyIdeaJCCustom
```

`create_strategy.py` writes a new file into `portfolio_sim/strategies/`, marks
the class as `JCCustom`, and prints the exact smoke-test command to run next.
After the smoke test passes, refresh Streamlit and the strategy appears in the
picker next to the built-ins.

Available generator templates:

| Template | Good for |
|---|---|
| `scheduled_buy` | Buy a chosen ticker with a chosen dollar amount every N trading days |
| `buy_the_dip` | Buy a chosen ticker after it falls X% from a trailing high |
| `moving_average` | Stay invested above a moving average and move to cash below it |

## How it's structured

```
portfolio_sim/
  data/loader.py           - yfinance downloader + local CSV cache
  engine/portfolio.py      - Portfolio: cash, positions, trade log
  engine/backtest.py       - Backtester: steps through history day-by-day
  strategies/base.py       - Strategy base class (subclass this)
  strategies/registry.py   - auto-discovers strategy classes + shared helpers
  strategies/_strategy_template.py - copy-paste scaffold for new strategies
  strategies/*.py          - the 7 strategies themselves (see below)
  analysis/metrics.py      - CAGR, drawdown, Sharpe, etc.
  analysis/plotting.py     - matplotlib charts (used by run_backtest.py)
  analysis/events.py       - historical market events for chart shading
app.py                     - interactive Streamlit dashboard
run_backtest.py            - plain-script example, no UI
test_strategy.py           - fast one-strategy harness with benchmark compare
create_strategy.py         - generates a new JCCustom strategy file
```

## Included strategies

| Strategy | What it does |
|---|---|
| `BuyAndHold` | Invest everything on day one, never trade again |
| `DCA` | Dollar-cost averaging - fixed amount on a fixed schedule |
| `GoldenCross` | Go all-in on a golden cross (50/200-day MA), to cash on a death cross |
| `TrendFollowing` | Stay invested only while price is above its N-day moving average |
| `Rebalancing` | Hold a target mix of two assets (e.g. 60/40 stocks/bonds), periodically rebalanced |
| `ValueAveraging` | Target a fixed portfolio value growth path; buy more when behind, less when ahead |
| `MeanReversion` | Buy when price is statistically far below its average (z-score), sell on reversion |

Every strategy declares a `param_spec` dict describing its own tunable
parameters - the Streamlit app reads this to auto-generate the right widget
(slider, number input, ticker box, etc.) for each one. **Add a new strategy
with a `param_spec` and it automatically appears in the app** - no UI code
to write.

## Writing your own strategy

Subclass `Strategy` and implement `on_data()`. It's called once per trading
day with all data available up to (and including) that day - never anything
from the future - plus the live `Portfolio` to trade through.

```python
from portfolio_sim.strategies.base import Strategy

class MyStrategy(Strategy):
    name = "MyStrategy"
    description = "Sells strength above the 200-day average, buys weakness below it."
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
            portfolio.sell(date, self.ticker, price, dollar_amount=1000)  # take profit
        elif price < ma200 * (1 - self.threshold):
            portfolio.buy(date, self.ticker, price, dollar_amount=1000)   # buy weakness
```

Save it as a new `.py` file in `portfolio_sim/strategies/`. The registry
auto-discovers concrete `Strategy` subclasses, so it will show up in the
Streamlit app and in `python test_strategy.py --list` with no manual wiring.
You can also copy `portfolio_sim/strategies/_strategy_template.py` as a
starting point.

`param_spec` types: `"ticker"` (text box, uppercased), `"text"` (plain text),
`"number"` (numeric input with min/max/step), `"percent"` (0-100 slider,
passed to your constructor as a 0-1 fraction), `"select"` (dropdown, needs
an `"options"` list).

### Ideas to try next
- **Momentum**: buy when price crosses above its 50/200-day moving average
- **Rebalancing**: hold a 60/40 stocks/bonds mix, rebalance back to target monthly
- **Multi-asset rotation**: hold whichever of several ETFs has the best trailing return
- **Volatility-scaled sizing**: buy more on dips when volatility is low, less when it's high
- **Stop-loss / trailing stop** overlays on top of another strategy

## Multiple tickers / assets

`Backtester` and `Strategy.on_data()` already work with any number of
tickers - `history` is a dict keyed by ticker. Just pass more tickers into
the `data` dict:

```python
data = {
    "SPY": get_price_data("SPY", "2010-01-01"),
    "TLT": get_price_data("TLT", "2010-01-01"),
}
```

and have your strategy read/trade whichever of `history["SPY"]` /
`history["TLT"]` it needs - useful for rotation or rebalancing strategies.

## Notes & caveats

- Prices are `auto_adjust=True` from yfinance (split/dividend adjusted), so
  returns include reinvested dividends for most ETFs.
- No transaction costs, slippage, taxes, or bid/ask spread are modeled - real
  results would be somewhat worse, especially for high-frequency strategies.
- `Portfolio.buy()` / `.sell()` automatically cap trades at available
  cash/shares, so a strategy can never go negative or oversell.
- Data is cached in `portfolio_sim/data/cache/*.csv` - delete a file (or pass
  `force_refresh=True`) to re-download fresh data for that ticker.
- `Backtester.run(strategy, starting_holdings={"VTI": 0.3})` seeds a strategy
  with existing positions (as a fraction of `initial_cash`) before its own
  logic runs on day one; whatever fraction isn't allocated starts as cash.
  The Streamlit app exposes this per-strategy as a "Starting holdings" table.
  Every strategy in a comparison still shares the same `initial_cash`, so
  total investable capital stays uniform - only the starting allocation
  differs.
