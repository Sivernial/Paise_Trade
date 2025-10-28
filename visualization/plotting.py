"""Visualization utilities for backtest results.

Generates static matplotlib/Seaborn plots for:
 - Equity curve
 - Drawdown curve
 - Portfolio value components (cash vs invested)
 - Distribution of trade P&L and returns
 - Per-symbol price series annotated with trade executions

All functions are defensive: they won't raise if data is missing; instead they
log a warning and skip that plot.

Headless-safe: forces the Agg backend when running in environments without a display.
"""

from __future__ import annotations

import os
import math
import warnings
from typing import Dict, List, Any, Sequence

import matplotlib

# Force non-interactive backend (safe for CI / headless execution)
matplotlib.use("Agg")

import matplotlib.pyplot as plt
try:
    import seaborn as sns  # type: ignore
    sns.set_style("darkgrid")
    _SEABORN = True
except Exception:
    _SEABORN = False
import pandas as pd


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _safe_dates(portfolio_values: List[Dict[str, Any]]) -> List[pd.Timestamp]:
    return [pv["date"] for pv in portfolio_values if pv.get("date") is not None]


def plot_equity_curve(equity_curve: Sequence[float], portfolio_values: List[Dict[str, Any]], output_dir: str) -> str:
    """Plot equity curve over time.

    Returns path to the saved figure.
    """
    if not equity_curve or len(portfolio_values) == 0:
        warnings.warn("Equity curve data missing; skipping equity plot")
        return ""

    # equity_curve has initial capital at index 0 before first date; align by trimming if lengths mismatch
    dates = _safe_dates(portfolio_values)
    curve = equity_curve
    if len(curve) == len(dates) + 1:
        curve = curve[1:]
    elif len(curve) != len(dates):
        # Fallback: create a range index
        dates = list(range(len(curve)))

    _ensure_dir(output_dir)
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(dates, curve, label="Equity", color="#1f77b4")
    ax.set_title("Equity Curve")
    ax.set_ylabel("Portfolio Value")
    ax.set_xlabel("Date")
    ax.legend()
    fig.autofmt_xdate()
    path = os.path.join(output_dir, "equity_curve.png")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_drawdown(drawdown_curve: Sequence[float], portfolio_values: List[Dict[str, Any]], output_dir: str) -> str:
    if not drawdown_curve or len(portfolio_values) == 0:
        warnings.warn("Drawdown data missing; skipping drawdown plot")
        return ""

    dates = _safe_dates(portfolio_values)
    curve = drawdown_curve
    if len(curve) == len(dates) + 1:
        curve = curve[1:]
    elif len(curve) != len(dates):
        dates = list(range(len(curve)))

    _ensure_dir(output_dir)
    fig, ax = plt.subplots(figsize=(12, 3))
    ax.fill_between(dates, curve, 0, color="red", alpha=0.3)
    ax.set_title("Drawdown Curve")
    ax.set_ylabel("Drawdown")
    ax.set_xlabel("Date")
    fig.autofmt_xdate()
    path = os.path.join(output_dir, "drawdown_curve.png")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_portfolio_components(portfolio_values: List[Dict[str, Any]], output_dir: str) -> str:
    if not portfolio_values:
        warnings.warn("Portfolio values missing; skipping component plot")
        return ""

    df = pd.DataFrame(portfolio_values)
    if "date" in df.columns:
        df = df.sort_values("date")

    _ensure_dir(output_dir)
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(df["date"], df["portfolio_value"], label="Total", color="#1f77b4")
    ax.plot(df["date"], df["cash"], label="Cash", color="#ff7f0e")
    ax.plot(df["date"], df["positions_value"], label="Invested", color="#2ca02c")
    ax.set_title("Portfolio Components")
    ax.set_ylabel("Value")
    ax.legend()
    fig.autofmt_xdate()
    path = os.path.join(output_dir, "portfolio_components.png")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_trade_distribution(trades: List[Dict[str, Any]], completed_trades: List[Dict[str, Any]], output_dir: str) -> List[str]:
    if not trades and not completed_trades:
        warnings.warn("No trades to visualize; skipping trade distribution plots")
        return []

    paths: List[str] = []
    _ensure_dir(output_dir)

    # Completed trade P&L distribution
    if completed_trades:
        df_ct = pd.DataFrame(completed_trades)
        if not df_ct.empty and "pnl" in df_ct.columns:
            fig, ax = plt.subplots(figsize=(8, 4))
            if _SEABORN:
                sns.histplot(df_ct["pnl"], bins=min(50, math.ceil(len(df_ct) / 2)), kde=True, ax=ax, color="#1f77b4")
            else:
                ax.hist(df_ct["pnl"], bins=min(50, math.ceil(len(df_ct) / 2)), color="#1f77b4", alpha=0.7)
            ax.set_title("Completed Trade P&L Distribution")
            ax.set_xlabel("P&L")
            path = os.path.join(output_dir, "trade_pnl_distribution.png")
            fig.savefig(path, bbox_inches="tight")
            plt.close(fig)
            paths.append(path)

        if "return" in df_ct.columns:
            fig, ax = plt.subplots(figsize=(8, 4))
            if _SEABORN:
                sns.histplot(df_ct["return"], bins=min(50, math.ceil(len(df_ct) / 2)), kde=True, ax=ax, color="#2ca02c")
            else:
                ax.hist(df_ct["return"], bins=min(50, math.ceil(len(df_ct) / 2)), color="#2ca02c", alpha=0.7)
            ax.set_title("Completed Trade Return Distribution")
            ax.set_xlabel("Return")
            path = os.path.join(output_dir, "trade_return_distribution.png")
            fig.savefig(path, bbox_inches="tight")
            plt.close(fig)
            paths.append(path)

    return paths


def plot_price_with_trades(symbol: str, price_df: pd.DataFrame, trades: List[Dict[str, Any]], output_dir: str) -> str:
    """Plot price series with buy/sell markers for a single symbol."""
    if price_df is None or price_df.empty:
        warnings.warn(f"Price data for {symbol} missing; skipping price plot")
        return ""

    sym_trades = [t for t in trades if t.get("symbol") == symbol]
    if not sym_trades:
        warnings.warn(f"No trades for {symbol}; plot will show price only")

    _ensure_dir(output_dir)
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(price_df.index, price_df["close"], label="Close", color="#1f77b4")

    # Annotate trades
    for trade in sym_trades:
        ts = trade.get("timestamp")
        price = trade.get("price")
        ttype = trade.get("type")
        color = "green" if ttype == "BUY" else "red"
        ax.scatter(ts, price, color=color, marker="^" if ttype == "BUY" else "v", s=60, zorder=3)
        ax.text(ts, price, ttype, fontsize=8, color=color, ha="center", va="bottom")

    ax.set_title(f"Price & Trades - {symbol}")
    ax.set_ylabel("Price")
    ax.legend()
    fig.autofmt_xdate()
    path = os.path.join(output_dir, f"{symbol}_price_trades.png")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def generate_backtest_plots(
    results: Dict[str, Any],
    price_data: Dict[str, pd.DataFrame],
    output_dir: str = "plots",
    max_symbols: int = 5,
) -> List[str]:
    """Generate all standard backtest plots and return list of file paths."""
    _ensure_dir(output_dir)
    created: List[str] = []

    equity_curve = results.get("equity_curve", [])
    drawdown_curve = results.get("drawdown_curve", [])
    portfolio_values = results.get("portfolio_values", [])
    trades = results.get("trades", [])
    completed_trades = results.get("completed_trades", results.get("completed_trades_summary", []))

    # Core performance plots
    eq_path = plot_equity_curve(equity_curve, portfolio_values, output_dir)
    if eq_path:
        created.append(eq_path)

    dd_path = plot_drawdown(drawdown_curve, portfolio_values, output_dir)
    if dd_path:
        created.append(dd_path)

    comp_path = plot_portfolio_components(portfolio_values, output_dir)
    if comp_path:
        created.append(comp_path)

    trade_dist_paths = plot_trade_distribution(trades, completed_trades, output_dir)
    created.extend(trade_dist_paths)

    # Per-symbol price with trades (limit to avoid excessive plots)
    symbols_plotted = 0
    for symbol, df in price_data.items():
        if symbols_plotted >= max_symbols:
            break
        path = plot_price_with_trades(symbol, df, trades, output_dir)
        if path:
            created.append(path)
            symbols_plotted += 1

    return created


__all__ = [
    "plot_equity_curve",
    "plot_drawdown",
    "plot_portfolio_components",
    "plot_trade_distribution",
    "plot_price_with_trades",
    "generate_backtest_plots",
]
