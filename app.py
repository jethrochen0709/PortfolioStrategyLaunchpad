"""
Interactive dashboard for the portfolio backtest simulator.

Run with:
    streamlit run app.py

Pick any number of strategies in the sidebar, tune each one's parameters
(amount, frequency, thresholds, etc.), optionally give each strategy a
starting allocation (e.g. "already 30% in VTI"), then click Run Backtest
to compare them - metrics table (including uninvested cash), an interactive
value/drawdown chart with historical event shading (2008 GFC, COVID crash,
etc.), and per-strategy trade logs.

Every strategy in a comparison run always starts from the same Initial cash
and receives the same recurring income, so the total investable capital is
identical across strategies - the only thing that can differ is how much of
it each strategy chooses to keep in cash vs. deploy at any given time.
"""
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from portfolio_sim.data.loader import get_price_data
from portfolio_sim.data.ticker_guide import TICKER_GUIDE
from portfolio_sim.engine.backtest import Backtester
from portfolio_sim.analysis.metrics import compute_metrics
from portfolio_sim.analysis.events import events_in_range
from portfolio_sim.strategies.registry import (
    BUILT_IN_STRATEGY_NAMES,
    CUSTOM_STRATEGY_NAMES,
    STRATEGY_REGISTRY,
    strategy_display_name,
    tickers_from_kwargs,
)

st.set_page_config(page_title="Strategy Launchpad", layout="wide")
st.title("Strategy Launchpad")
st.caption("Create custom strategies, then compare them against popular baselines over any historical period.")


@st.cache_data(show_spinner=False)
def load_prices(ticker: str, start: str, end: str):
    return get_price_data(ticker, start, end)


def build_widget(param_name, spec, key_prefix, context_kwargs=None):
    """Renders the right Streamlit widget for a given param_spec entry and
    returns the value ready to pass into the strategy's constructor.
    context_kwargs: kwargs already resolved earlier in this same strategy's
    loop (e.g. its "ticker" value), so later params like "allocation" can
    default off the *current* ticker instead of the literal param_spec
    default."""
    context_kwargs = context_kwargs or {}
    key = f"{key_prefix}_{param_name}"
    label = spec.get("label", param_name)
    help_text = spec.get("help")
    ptype = spec["type"]

    if ptype == "ticker":
        return st.text_input(label, value=spec["default"], key=key, help=help_text).strip().upper()
    elif ptype == "text":
        return st.text_input(label, value=spec["default"], key=key, help=help_text)
    elif ptype == "number":
        return st.number_input(label, min_value=spec.get("min"), max_value=spec.get("max"),
                                value=spec["default"], step=spec.get("step", 1), key=key, help=help_text)
    elif ptype == "percent":
        pct = st.slider(label, min_value=spec.get("min", 0.0), max_value=spec.get("max", 100.0),
                         value=spec["default"], step=spec.get("step", 1.0), key=key, help=help_text)
        return pct / 100.0
    elif ptype == "select":
        options = spec["options"]
        return st.selectbox(label, options=options, index=options.index(spec["default"]),
                             key=key, help=help_text)
    elif ptype == "allocation":
        default = spec.get("default") or {}
        ticker_value = context_kwargs.get("ticker")
        if ticker_value and len(default) == 1:
            # Reseed the single-ticker literal default (e.g. {"SPY": 100.0})
            # to match whichever ticker this strategy is currently set to,
            # so changing the Ticker box above updates the default
            # allocation target too, instead of silently staying on SPY.
            default = {ticker_value: next(iter(default.values()))}
        return build_allocation_widget(label, default, help_text, key)
    else:
        return spec["default"]


def build_allocation_widget(label, default: dict, help_text, key):
    """Editable ticker/value table for an 'allocation' param_spec entry.
    Returns a dict of {ticker: value} (weights in percent mode, dollars in
    dollar mode - the strategy itself knows which, via its allocation_mode
    param). Add rows to diversify a single purchase across several tickers."""
    st.caption(label + (f" - {help_text}" if help_text else ""))
    rows_df = pd.DataFrame({"Ticker": list(default.keys()), "Value": list(default.values())})
    edited = st.data_editor(
        rows_df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key=key,
        column_config={
            "Ticker": st.column_config.TextColumn("Ticker", help="e.g. SPY"),
            "Value": st.column_config.NumberColumn("Value", min_value=0.0, step=1.0,
                                                     help="Percent weight or dollar amount, depending on Allocation mode below."),
        },
    )
    result = {}
    total = 0.0
    for _, row in edited.iterrows():
        ticker = str(row.get("Ticker") or "").strip().upper()
        value = row.get("Value")
        if not ticker or value is None or pd.isna(value) or value <= 0:
            continue
        result[ticker] = result.get(ticker, 0.0) + float(value)
        total += float(value)
    if len(result) > 1:
        st.caption(f"{len(result)} tickers, {total:,.1f} total weight/dollars.")
    return result


def build_holdings_editor(key_prefix, initial_cash):
    """Lets the user add starting holdings for a single strategy - a ticker
    plus either a % of its portfolio or a fixed dollar amount already owned
    on day one. Returns (holdings dict of ticker -> fraction of initial_cash,
    error_str)."""
    st.caption("Starting holdings (optional) - what this strategy already owns on day one. "
               "Anything left over starts as cash.")
    mode = st.radio("Specify as", options=["Percent of portfolio", "Dollar amount"],
                     key=f"{key_prefix}_holdings_mode", horizontal=True)

    if mode == "Percent of portfolio":
        value_col = "Percent of portfolio"
        empty_df = pd.DataFrame({"Ticker": pd.Series(dtype="str"), value_col: pd.Series(dtype="float")})
        value_col_config = st.column_config.NumberColumn(
            value_col, min_value=0.0, max_value=100.0, step=1.0, format="%.1f%%"
        )
    else:
        value_col = "Dollar amount ($)"
        empty_df = pd.DataFrame({"Ticker": pd.Series(dtype="str"), value_col: pd.Series(dtype="float")})
        value_col_config = st.column_config.NumberColumn(
            value_col, min_value=0.0, step=100.0, format="$%.0f"
        )

    edited = st.data_editor(
        empty_df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key=f"{key_prefix}_holdings_{mode}",
        column_config={
            "Ticker": st.column_config.TextColumn("Ticker", help="e.g. VTI"),
            value_col: value_col_config,
        },
    )

    raw = {}
    total = 0.0
    for _, row in edited.iterrows():
        ticker = str(row.get("Ticker") or "").strip().upper()
        value = row.get(value_col)
        if not ticker or value is None or pd.isna(value) or value <= 0:
            continue
        raw[ticker] = raw.get(ticker, 0.0) + float(value)
        total += float(value)

    error = None
    if mode == "Percent of portfolio":
        if total > 100.0001:
            error = f"Starting holdings add up to {total:.1f}% of portfolio - reduce to 100% or less."
        fractions = {t: v / 100.0 for t, v in raw.items()}
    else:
        if total > initial_cash + 0.01:
            error = (f"Starting holdings add up to ${total:,.0f}, more than the "
                     f"${initial_cash:,.0f} initial cash - reduce the amounts.")
        fractions = {t: (v / initial_cash if initial_cash else 0.0) for t, v in raw.items()}

    return fractions, error


# ==================== Sidebar ====================
st.sidebar.header("Backtest Settings")

col1, col2 = st.sidebar.columns(2)
start_date = col1.date_input("Start date", value=pd.Timestamp("2000-01-01"))
end_date = col2.date_input("End date", value=pd.Timestamp.today())

initial_cash = st.sidebar.number_input("Initial cash ($)", min_value=100, max_value=100_000_000,
                                        value=10000, step=500,
                                        help="The same starting capital pool every selected strategy is backtested with, "
                                             "so comparisons stay apples-to-apples.")
income_amount = st.sidebar.number_input("Income to invest ($)", min_value=0, max_value=10_000_000,
                                        value=0, step=100,
                                        help="Extra cash added to the portfolio at the selected frequency.")
income_frequency_label = st.sidebar.selectbox(
    "Income frequency",
    options=["None", "Daily", "Weekly", "Monthly", "Yearly"],
    index=0,
    disabled=income_amount <= 0,
)
income_frequency = income_frequency_label.lower() if income_amount > 0 else "none"

log_scale = st.sidebar.checkbox("Log scale for value chart", value=False)
show_cash_on_chart = st.sidebar.checkbox("Show uninvested cash on chart", value=False,
                                          help="Adds a dotted line per strategy showing how much of its value is sitting in cash.")

st.sidebar.markdown("---")
st.sidebar.header("Strategy Comparison")

with st.sidebar.expander("Launchpad workflow", expanded=False):
    st.markdown(
        """
        1. Create or drop a strategy file in `portfolio_sim/strategies/`.
        2. Use a class name ending in `JCCustom`.
        3. Run `python test_strategy.py YourStrategyJCCustom`.
        4. Refresh this app and compare it with the built-ins.

        Starter command:
        `python create_strategy.py my_idea --template scheduled_buy`
        """
    )

with st.sidebar.expander("Ticker guide", expanded=False):
    st.caption("A quick reference for tickers you can type into any Ticker box, Starting holdings, "
               "or Buy allocation table below. Not exhaustive - just popular examples by category.")
    for category, rows in TICKER_GUIDE.items():
        st.markdown(f"**{category}**")
        st.dataframe(
            pd.DataFrame(rows, columns=["Ticker", "Name"]),
            use_container_width=True,
            hide_index=True,
        )

custom_default = CUSTOM_STRATEGY_NAMES[:1]
selected_custom_names = st.sidebar.multiselect(
    "Your strategies",
    options=CUSTOM_STRATEGY_NAMES,
    default=custom_default,
    format_func=lambda name: strategy_display_name(STRATEGY_REGISTRY[name]),
    help="Strategies marked JCCustom. Drop or generate new files in portfolio_sim/strategies/.",
)

comparison_default = [name for name in ["BuyAndHold", "DCA"] if name in BUILT_IN_STRATEGY_NAMES]
comparison_mode = st.sidebar.radio(
    "Comparison set",
    options=["Popular defaults", "Choose manually", "All built-ins"],
    horizontal=False,
)
if comparison_mode == "All built-ins":
    selected_comparison_names = BUILT_IN_STRATEGY_NAMES
elif comparison_mode == "Choose manually":
    selected_comparison_names = st.sidebar.multiselect(
        "Popular / pre-existing strategies",
        options=BUILT_IN_STRATEGY_NAMES,
        default=comparison_default,
        format_func=lambda name: strategy_display_name(STRATEGY_REGISTRY[name]),
    )
else:
    selected_comparison_names = comparison_default
    st.sidebar.caption(", ".join(strategy_display_name(STRATEGY_REGISTRY[name]) for name in selected_comparison_names))

selected_names = list(dict.fromkeys(selected_custom_names + selected_comparison_names))

with st.sidebar.expander("Strategy guide", expanded=False):
    st.markdown("**Your strategies**")
    for name in CUSTOM_STRATEGY_NAMES:
        cls = STRATEGY_REGISTRY[name]
        st.markdown(f"**{strategy_display_name(cls)}** - {cls.description}")

    st.markdown("**Popular / pre-existing strategies**")
    for name in BUILT_IN_STRATEGY_NAMES:
        cls = STRATEGY_REGISTRY[name]
        st.markdown(f"**{strategy_display_name(cls)}** - {cls.description}")

strategy_instances = []
holdings_errors = []
for name in selected_names:
    cls = STRATEGY_REGISTRY[name]
    display_name = strategy_display_name(cls)
    with st.sidebar.expander(display_name, expanded=False):
        st.caption(cls.description)
        kwargs = {}
        for pname, spec in cls.param_spec.items():
            kwargs[pname] = build_widget(pname, spec, key_prefix=name, context_kwargs=kwargs)
        st.markdown("---")
        starting_holdings, holdings_error = build_holdings_editor(key_prefix=name, initial_cash=initial_cash)
        if holdings_error:
            st.error(holdings_error)
            holdings_errors.append(f"**{display_name}**: {holdings_error}")
    strategy_instances.append((display_name, cls, kwargs, starting_holdings))

run_clicked = st.sidebar.button("Run Backtest", type="primary", use_container_width=True,
                                 disabled=bool(holdings_errors))

# ==================== Run backtests ====================
if not selected_names:
    st.info("Pick one of your JCCustom strategies or at least one comparison strategy from the sidebar.")
    st.stop()

if run_clicked:
    # Collect every ticker needed across all selected strategies (handles
    # multi-asset strategies like Rebalancing which need two tickers, plus
    # whatever tickers show up in each strategy's starting holdings)
    tickers_needed = set()
    for name, cls, kwargs, starting_holdings in strategy_instances:
        tickers_needed.update(tickers_from_kwargs(cls, kwargs))
        tickers_needed.update(starting_holdings.keys())

    with st.spinner(f"Downloading price data for {', '.join(sorted(tickers_needed))}..."):
        try:
            price_data = {t: load_prices(t, str(start_date), str(end_date)) for t in tickers_needed}
        except Exception as e:
            st.error(f"Failed to load price data: {e}")
            st.stop()

    results = {}
    portfolios = {}
    errors = []
    for name, cls, kwargs, starting_holdings in strategy_instances:
        try:
            strategy = cls(**kwargs)
            bt = Backtester(
                price_data,
                initial_cash=initial_cash,
                income_amount=income_amount,
                income_frequency=income_frequency,
            )
            portfolio = bt.run(strategy, starting_holdings=starting_holdings)
            results[name] = portfolio.history_df()
            portfolios[name] = portfolio
        except Exception as e:
            errors.append(f"**{name}**: {e}")

    st.session_state["results"] = results
    st.session_state["portfolios"] = portfolios
    st.session_state["initial_cash"] = initial_cash
    st.session_state["income_amount"] = income_amount
    st.session_state["income_frequency"] = income_frequency
    for err in errors:
        st.error(err)

results = st.session_state.get("results", {})
portfolios = st.session_state.get("portfolios", {})

if not results:
    st.info("Choose the strategies and time period to compare, then click **Run Backtest**.")
    st.stop()

# ==================== Metrics table ====================
st.subheader("Performance Summary")
rows = []
for name, history in results.items():
    if len(history) == 0:
        continue
    m = compute_metrics(history, st.session_state["initial_cash"])
    end_cash = history["cash"].iloc[-1]
    end_value = m["end_value"]
    cash_pct = (end_cash / end_value * 100) if end_value > 0 else float("nan")
    rows.append({
        "Strategy": name,
        "End Value": f"${m['end_value']:,.0f}",
        "Uninvested Cash": f"${end_cash:,.0f}",
        "Cash %": f"{cash_pct:.1f}%",
        "Total Contributed": f"${m['total_contributed']:,.0f}",
        "Net Profit": f"${m['net_profit']:,.0f}",
        "Return on Capital": f"{m['total_return_pct']:.1f}%",
        "CAGR": f"{m['cagr_pct']:.1f}%",
        "Volatility": f"{m['volatility_pct']:.1f}%",
        "Sharpe": f"{m['sharpe_ratio']:.2f}",
        "Max Drawdown": f"{m['max_drawdown_pct']:.1f}%",
    })
st.dataframe(pd.DataFrame(rows).set_index("Strategy"), use_container_width=True)
st.caption("Every strategy above started from the same Initial cash (and the same recurring income, if any), "
           "so \"Uninvested Cash\" shows how much of that shared capital each strategy chose to leave on the "
           "sidelines rather than deploy.")

# ==================== Chart ====================
st.subheader("Portfolio Value & Drawdown")
show_events = st.toggle("Show historical events overlay", value=True)

fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08,
                     row_heights=[0.7, 0.3])

palette = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f"]

for i, (name, history) in enumerate(results.items()):
    if len(history) == 0:
        continue
    color = palette[i % len(palette)]
    fig.add_trace(go.Scatter(x=history.index, y=history["total_value"], name=name,
                              line=dict(color=color, width=2)),
                  row=1, col=1)

    if show_cash_on_chart and "cash" in history.columns:
        fig.add_trace(go.Scatter(x=history.index, y=history["cash"], name=f"{name} (uninvested cash)",
                                  showlegend=True, line=dict(color=color, width=1, dash="dot")),
                      row=1, col=1)

    values = history["total_value"]
    running_max = values.cummax()
    drawdown = (values - running_max) / running_max * 100
    fig.add_trace(go.Scatter(x=history.index, y=drawdown, name=f"{name} (drawdown)", showlegend=False,
                              line=dict(color=color, width=1.2)),
                  row=2, col=1)

if show_events:
    non_empty = [h for h in results.values() if len(h) > 0]
    if non_empty:
        range_start = min(h.index.min() for h in non_empty)
        range_end = max(h.index.max() for h in non_empty)
        for event in events_in_range(range_start, range_end):
            for row in (1, 2):
                fig.add_vrect(x0=event["start"], x1=event["end"], fillcolor="gray", opacity=0.15,
                              line_width=0, row=row, col=1)
            fig.add_annotation(x=event["start"], y=1, yref="y domain", yanchor="bottom",
                                text=event["name"], showarrow=False, textangle=-90,
                                font=dict(size=9, color="gray"), row=1, col=1)

fig.update_yaxes(title_text="Value ($)", type="log" if log_scale else "linear", row=1, col=1)
fig.update_yaxes(title_text="Drawdown (%)", row=2, col=1)
fig.update_layout(height=700, hovermode="x unified",
                   legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
                   margin=dict(t=40))

st.plotly_chart(fig, use_container_width=True)

# ==================== Trade logs ====================
with st.expander("View trade logs"):
    tabs = st.tabs(list(portfolios.keys()))
    for tab, (name, portfolio) in zip(tabs, portfolios.items()):
        with tab:
            trades = portfolio.trades_df()
            if len(trades) == 0:
                st.write("No trades were made.")
            else:
                st.dataframe(trades, use_container_width=True)
