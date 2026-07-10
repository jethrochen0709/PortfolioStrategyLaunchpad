"""
Auto-discovered registry of available strategies.

Drop a new strategy module into this package, subclass Strategy, give it a
unique `name`, and it will appear in the Streamlit app and CLI harness without
manual registration.
"""
from importlib import import_module
from inspect import isclass
from pathlib import Path

from portfolio_sim.strategies.base import Strategy


_SKIP_MODULES = {"base", "registry", "__init__"}


def _iter_strategy_modules():
    package_dir = Path(__file__).parent
    for path in sorted(package_dir.glob("*.py")):
        module_name = path.stem
        if module_name in _SKIP_MODULES or module_name.startswith("_"):
            continue
        yield import_module(f"{__package__}.{module_name}")


def discover_strategies():
    """Return concrete Strategy subclasses found in portfolio_sim.strategies."""
    strategies = []
    for module in _iter_strategy_modules():
        for obj in vars(module).values():
            if not isclass(obj):
                continue
            if obj is Strategy or not issubclass(obj, Strategy):
                continue
            if obj.__module__ != module.__name__:
                continue
            strategies.append(obj)

    by_name = {}
    for cls in strategies:
        if cls.name in by_name:
            raise ValueError(f"Duplicate strategy name found: {cls.name}")
        by_name[cls.name] = cls

    return [by_name[name] for name in sorted(by_name)]


def param_default_kwargs(strategy_cls, ticker="SPY", ticker_map=None):
    """
    Build constructor kwargs from a strategy's param_spec.

    Percent params are stored in param_spec as display percentages (5.0 means
    5%) and converted to constructor fractions (0.05), matching the Streamlit
    widget behavior.
    """
    ticker_map = ticker_map or {}
    kwargs = {}
    for pname, spec in strategy_cls.param_spec.items():
        ptype = spec.get("type")
        value = spec.get("default")
        if ptype == "ticker":
            value = ticker_map.get(pname, ticker)
        elif ptype == "percent":
            value = value / 100.0
        kwargs[pname] = value
    return kwargs


def tickers_from_kwargs(strategy_cls, kwargs):
    """Extract ticker values from constructor kwargs using param_spec metadata."""
    tickers = set()
    for pname, spec in strategy_cls.param_spec.items():
        if spec.get("type") == "ticker":
            value = kwargs.get(pname, spec.get("default"))
            if value:
                tickers.add(str(value).strip().upper())
    return tickers


def is_custom_strategy(strategy_cls):
    """Return True for personal strategy classes."""
    return bool(getattr(strategy_cls, "is_custom", False) or strategy_cls.name.endswith("JCCustom"))


def strategy_display_name(strategy_cls):
    """Friendlier name for UI lists and headings."""
    base = getattr(strategy_cls, "display_name", "") or strategy_cls.name
    suffix = "JCCustom" if is_custom_strategy(strategy_cls) else "Built-in"
    return f"{base} ({suffix})"


ALL_STRATEGIES = discover_strategies()
STRATEGY_REGISTRY = {cls.name: cls for cls in ALL_STRATEGIES}
CUSTOM_STRATEGY_NAMES = [cls.name for cls in ALL_STRATEGIES if is_custom_strategy(cls)]
BUILT_IN_STRATEGY_NAMES = [cls.name for cls in ALL_STRATEGIES if not is_custom_strategy(cls)]
