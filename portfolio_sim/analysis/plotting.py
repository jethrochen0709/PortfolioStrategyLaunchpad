"""Charts for comparing strategies against each other."""
import matplotlib.pyplot as plt


def plot_comparison(results: dict, save_path: str = None, log_scale: bool = False):
    """
    results: dict of strategy_name -> history_df (from Portfolio.history_df())
    save_path: if given, saves the figure to this path instead of only displaying it
    log_scale: use a log y-axis on the value chart (useful for multi-decade backtests)
    """
    fig, axes = plt.subplots(2, 1, figsize=(11, 8), sharex=True,
                              gridspec_kw={"height_ratios": [3, 1]})

    for name, df in results.items():
        axes[0].plot(df.index, df["total_value"], label=name, linewidth=1.5)

    axes[0].set_title("Portfolio Value Over Time")
    axes[0].set_ylabel("Value ($)")
    if log_scale:
        axes[0].set_yscale("log")
    axes[0].legend()
    axes[0].grid(alpha=0.3)

    for name, df in results.items():
        values = df["total_value"]
        running_max = values.cummax()
        drawdown = (values - running_max) / running_max * 100
        axes[1].plot(df.index, drawdown, label=name, linewidth=1.2)

    axes[1].set_title("Drawdown")
    axes[1].set_ylabel("Drawdown (%)")
    axes[1].set_xlabel("Date")
    axes[1].grid(alpha=0.3)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150)
        print(f"Saved chart to {save_path}")
    else:
        plt.show()

    return fig
