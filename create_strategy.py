"""
Create a new personal strategy file from a launchpad template.

Examples:
    python create_strategy.py my_monthly_qqq
    python create_strategy.py dip_buyer --template buy_the_dip
    python create_strategy.py trend_filter --template moving_average
"""
import argparse
import re
from pathlib import Path


STRATEGY_DIR = Path(__file__).parent / "portfolio_sim" / "strategies"


TEMPLATES = {
    "scheduled_buy": {
        "description": "Buy a chosen ticker with a chosen dollar amount every N trading days.",
        "body": '''
from portfolio_sim.strategies.base import Strategy


class {class_name}(Strategy):
    name = "{class_name}"
    display_name = "{display_name}"
    is_custom = True
    description = "JCCustom: buy a chosen ticker with a chosen dollar amount on a fixed schedule."
    param_spec = {{
        "ticker": {{"label": "What to buy", "type": "ticker", "default": "SPY"}},
        "buy_amount": {{"label": "Buy amount ($)", "type": "number", "default": 500,
                       "min": 10, "max": 100000, "step": 50}},
        "frequency_days": {{"label": "Buy every N trading days", "type": "number", "default": 21,
                           "min": 1, "max": 252, "step": 1,
                           "help": "~5 = weekly, ~21 = monthly, ~63 = quarterly"}},
    }}

    def __init__(self, ticker="SPY", buy_amount=500, frequency_days=21):
        super().__init__(ticker=ticker, buy_amount=buy_amount, frequency_days=frequency_days)
        self.ticker = ticker
        self.buy_amount = buy_amount
        self.frequency_days = frequency_days
        self._day_count = 0

    def on_data(self, date, history, portfolio):
        df = history.get(self.ticker)
        if df is None or len(df) == 0:
            return

        if self._day_count % self.frequency_days == 0:
            price = df["Close"].iloc[-1]
            portfolio.buy(date, self.ticker, price, dollar_amount=self.buy_amount)

        self._day_count += 1
''',
    },
    "buy_the_dip": {
        "description": "Buy a chosen ticker when it falls X% from a trailing high.",
        "body": '''
from portfolio_sim.strategies.base import Strategy


class {class_name}(Strategy):
    name = "{class_name}"
    display_name = "{display_name}"
    is_custom = True
    description = "JCCustom: buy after a configurable drop from the recent high."
    param_spec = {{
        "ticker": {{"label": "What to buy", "type": "ticker", "default": "SPY"}},
        "drop_pct": {{"label": "Buy after drop (%)", "type": "percent", "default": 5.0,
                     "min": 0.5, "max": 80.0, "step": 0.25}},
        "buy_amount": {{"label": "Buy amount ($)", "type": "number", "default": 1000,
                       "min": 10, "max": 100000, "step": 50}},
        "lookback": {{"label": "Trailing high lookback (days)", "type": "number", "default": 252,
                     "min": 10, "max": 1000, "step": 1}},
    }}

    def __init__(self, ticker="SPY", drop_pct=0.05, buy_amount=1000, lookback=252):
        super().__init__(ticker=ticker, drop_pct=drop_pct, buy_amount=buy_amount, lookback=lookback)
        self.ticker = ticker
        self.drop_pct = drop_pct
        self.buy_amount = buy_amount
        self.lookback = lookback
        self._armed = True

    def on_data(self, date, history, portfolio):
        df = history.get(self.ticker)
        if df is None or len(df) < 2:
            return

        price = df["Close"].iloc[-1]
        trailing_high = df["Close"].tail(self.lookback).max()
        if trailing_high <= 0:
            return

        drop = (trailing_high - price) / trailing_high
        if drop >= self.drop_pct and self._armed:
            portfolio.buy(date, self.ticker, price, dollar_amount=self.buy_amount)
            self._armed = False
        elif drop < self.drop_pct:
            self._armed = True
''',
    },
    "moving_average": {
        "description": "Go invested above a moving average and move to cash below it.",
        "body": '''
from portfolio_sim.strategies.base import Strategy


class {class_name}(Strategy):
    name = "{class_name}"
    display_name = "{display_name}"
    is_custom = True
    description = "JCCustom: stay invested only while price is above a moving average."
    param_spec = {{
        "ticker": {{"label": "What to buy", "type": "ticker", "default": "SPY"}},
        "sma_window": {{"label": "Moving average window (days)", "type": "number", "default": 200,
                       "min": 20, "max": 400, "step": 1}},
        "check_frequency_days": {{"label": "Re-check every N days", "type": "number", "default": 21,
                                 "min": 1, "max": 63, "step": 1}},
    }}

    def __init__(self, ticker="SPY", sma_window=200, check_frequency_days=21):
        super().__init__(ticker=ticker, sma_window=sma_window, check_frequency_days=check_frequency_days)
        self.ticker = ticker
        self.sma_window = sma_window
        self.check_frequency_days = check_frequency_days
        self._day_count = 0
        self._invested = False

    def on_data(self, date, history, portfolio):
        df = history.get(self.ticker)
        if df is None or len(df) < self.sma_window:
            return

        if self._day_count % self.check_frequency_days == 0:
            price = df["Close"].iloc[-1]
            sma = df["Close"].tail(self.sma_window).mean()
            shares = portfolio.positions.get(self.ticker, 0)

            if price > sma and not self._invested:
                portfolio.buy(date, self.ticker, price, dollar_amount=portfolio.cash)
                self._invested = True
            elif price < sma and self._invested:
                portfolio.sell(date, self.ticker, price, shares=shares)
                self._invested = False

        self._day_count += 1
''',
    },
}


def snake_name(raw_name):
    name = re.sub(r"[^a-zA-Z0-9]+", "_", raw_name).strip("_").lower()
    if not name:
        raise ValueError("Strategy name must contain at least one letter or number.")
    return name


def class_name_from_snake(name):
    return "".join(part.capitalize() for part in name.split("_")) + "JCCustom"


def display_name_from_snake(name):
    return " ".join(part.capitalize() for part in name.split("_"))


def list_templates():
    for name, template in TEMPLATES.items():
        print(f"{name}: {template['description']}")


def main():
    parser = argparse.ArgumentParser(description="Create a new JCCustom strategy file.")
    parser.add_argument("name", nargs="?", help="New strategy name, e.g. my_monthly_qqq")
    parser.add_argument("--template", default="scheduled_buy", choices=sorted(TEMPLATES))
    parser.add_argument("--list-templates", action="store_true")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing strategy file")
    args = parser.parse_args()

    if args.list_templates:
        list_templates()
        return

    if not args.name:
        parser.error("name is required unless --list-templates is used")

    file_stem = snake_name(args.name)
    file_path = STRATEGY_DIR / f"{file_stem}.py"
    if file_path.exists() and not args.force:
        raise SystemExit(f"{file_path} already exists. Pick a new name or pass --force.")

    class_name = class_name_from_snake(file_stem)
    display_name = display_name_from_snake(file_stem)
    source = TEMPLATES[args.template]["body"].strip().format(
        class_name=class_name,
        display_name=display_name,
    )
    file_path.write_text(source + "\n")

    print(f"Created {file_path}")
    print(f"Strategy key: {class_name}")
    print(f"Smoke test: python test_strategy.py {class_name}")


if __name__ == "__main__":
    main()
