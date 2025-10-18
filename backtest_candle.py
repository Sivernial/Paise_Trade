"""
backtest_candle.py

Simple backtester for single-candle patterns + next-bar-open execution.
Input: CSV with columns: Date (ISO), Open, High, Low, Close, Volume (optional)
Usage: python backtest_candle.py data.csv
"""

import sys
import numpy as np
import pandas as pd
from math import isnan
from datetime import timedelta

# ------------- Candle detection -------------
def detect_candle_pattern_row(row, body_thresh_doji = 0.10, spinning_top_thresh = 0.25):
    o, h, l, c = row['Open'], row['High'], row['Low'], row['Close']
    rng = h - l
    if rng == 0:
        return "Flat"
    body = abs(c - o)
    upper = h - max(o, c)
    lower = min(o, c) - l
    body_pct = (body / rng) if rng else 0

    # Doji: tiny body
    if body_pct < body_thresh_doji:
        return "Doji"

    # Hammer/Hanging Man: long lower shadow (lower > 2 * body), small upper
    if lower > 2 * body and upper < body:
        if c > o:
            return "Hammer"        # bullish
        else:
            return "Hanging Man"   # bearish

    # Shooting Star: long upper shadow
    if upper > 2 * body and lower < body:
        return "Shooting Star"

    # Spinning Top: small body but both shadows present
    if body_pct < spinning_top_thresh and upper > body and lower > body:
        return "Spinning Top"

    return "Normal"

# ------------- Signal generator -------------
def pattern_to_signal(pattern):
    if pattern == "Hammer":
        return 1   # BUY
    if pattern in ("Hanging Man", "Shooting Star"):
        return -1  # SELL
    # For Doji/SpinningTop we return 0 (neutral) --- can be changed to a filter
    return 0

# ------------- Backtester -------------
def backtest(df,
             initial_capital = 100000,
             position_size_pct = 0.05,    # fraction of capital per trade
             commission_per_trade = 20.0, # flat
             slippage_pct = 0.0005,       # 0.05% slippage per side
             stop_loss_atr_mult = None    # if None, no SL. else multiplier times ATR
            ):
    """Backtest next-bar-open entries.
    Assumes df has DateTime index sorted ascending and Open/High/Low/Close columns.
    """

    # Add pattern & signal
    df = df.copy()
    df['pattern'] = df.apply(detect_candle_pattern_row, axis=1)
    df['signal'] = df['pattern'].apply(pattern_to_signal)

    # ATR for optional SL
    if stop_loss_atr_mult is not None:
        df['tr'] = np.maximum(df['High'] - df['Low'],
                              np.maximum(abs(df['High'] - df['Close'].shift(1)),
                                         abs(df['Low'] - df['Close'].shift(1))))
        df['ATR'] = df['tr'].rolling(14, min_periods=1).mean()
    else:
        df['ATR'] = np.nan

    # We'll step through bars and execute next-bar-open entries
    capital = initial_capital
    cash = initial_capital
    position = 0         # number of shares (positive = long, negative = short if allowed)
    entry_price = None
    entry_index = None

    trades = []  # list of dicts for each closed trade

    # We'll support only one position at a time (simple model)
    for i in range(len(df)-1):
        row = df.iloc[i]
        next_row = df.iloc[i+1]  # entry/exit at next bar open
        signal = row['signal']

        # If no position and a signal appears -> enter at next open
        if position == 0 and signal != 0:
            # position sizing by % of capital
            notional = capital * position_size_pct
            qty = int(notional // next_row['Open'])
            if qty <= 0:
                continue
            # calculate cost with slippage and commission
            exec_price = next_row['Open'] * (1 + slippage_pct * (1 if signal>0 else -1))
            cost = qty * exec_price + commission_per_trade
            if cost > cash:
                # insufficient cash — skip
                continue
            position = qty if signal > 0 else -qty
            entry_price = exec_price
            entry_index = df.index[i+1]
            cash -= cost
            # compute stop loss if specified
            if not isnan(row['ATR']):
                if signal > 0:
                    stop_loss = exec_price - stop_loss_atr_mult * row['ATR']
                else:
                    stop_loss = exec_price + stop_loss_atr_mult * row['ATR']
            else:
                stop_loss = None

            # record open trade
            open_trade = {
                'entry_index': entry_index,
                'entry_price': entry_price,
                'qty': position,
                'signal': signal,
                'stop_loss': stop_loss,
                'exit_index': None,
                'exit_price': None,
                'pnl': None
            }

        # If position is open, check for stop loss hit intrabar (use High/Low of next row)
        if position != 0:
            # check if stop loss exists and hit on the same next row (conservative)
            hit_sl = False
            if stop_loss is not None:
                if position > 0:
                    # long: stop if next_row.Low <= stop_loss
                    if next_row['Low'] <= stop_loss:
                        # assume exit at stop_loss price (or slight worse due to slippage)
                        exit_price = stop_loss * (1 - slippage_pct)
                        hit_sl = True
                else:
                    if next_row['High'] >= stop_loss:
                        exit_price = stop_loss * (1 + slippage_pct)
                        hit_sl = True
            # Otherwise check for signal in opposite direction to exit (or keep until closed)
            if hit_sl:
                # Close position
                cash += abs(position) * exit_price - commission_per_trade
                pnl = (exit_price - entry_price) * position - commission_per_trade
                open_trade.update({
                    'exit_index': df.index[i+1],
                    'exit_price': exit_price,
                    'pnl': pnl
                })
                trades.append(open_trade)
                position = 0
                entry_price = None
                entry_index = None
                stop_loss = None
            else:
                # Optionally implement signal-based close (e.g., if opposite pattern occurs)
                # We'll check if there's an opposite signal on this row (row, not next_row)
                if row['signal'] * open_trade['signal'] < 0:
                    # close at next open
                    exit_price = next_row['Open'] * (1 - slippage_pct if open_trade['signal']>0 else 1 + slippage_pct)
                    cash += abs(position) * exit_price - commission_per_trade
                    pnl = (exit_price - entry_price) * position - commission_per_trade
                    open_trade.update({
                        'exit_index': df.index[i+1],
                        'exit_price': exit_price,
                        'pnl': pnl
                    })
                    trades.append(open_trade)
                    position = 0
                    entry_price = None
                    entry_index = None
                    stop_loss = None

    # At the end, mark unrealized position
    if position != 0:
        # close at last bar close
        last = df.iloc[-1]
        exit_price = last['Close'] * (1 - slippage_pct if position>0 else 1 + slippage_pct)
        cash += abs(position) * exit_price - commission_per_trade
        pnl = (exit_price - entry_price) * position - commission_per_trade
        open_trade.update({
            'exit_index': df.index[-1],
            'exit_price': exit_price,
            'pnl': pnl
        })
        trades.append(open_trade)
        position = 0

    # Final capital
    final_capital = cash
    returns = final_capital / initial_capital - 1.0

    # Metrics from trades
    trades_df = pd.DataFrame(trades)
    num_trades = len(trades_df)
    wins = trades_df[trades_df['pnl'] > 0]
    win_rate = len(wins) / num_trades if num_trades>0 else np.nan
    avg_pnl = trades_df['pnl'].mean() if num_trades>0 else np.nan

    # Equity curve approximation from trades (simple)
    # We'll reconstruct PnL series by applying trade PnL at exit times (sparse)
    equity = pd.Series(index=df.index, dtype=float)
    equity.iloc[0] = initial_capital
    cum = initial_capital
    trade_idx_map = {t['exit_index']: t['pnl'] for t in trades}
    for idx in df.index[1:]:
        pnl_here = trade_idx_map.get(idx, 0.0)
        cum = cum + pnl_here
        equity.loc[idx] = cum

    # compute drawdown
    equity_ffill = equity.fillna(method='ffill')
    running_max = equity_ffill.cummax()
    drawdown = (equity_ffill - running_max) / running_max
    max_dd = drawdown.min()

    # annualization approximations depending on data freq
    # infer bars per year
    # if data is minute-level, bars_per_day ~ 390 for intraday (NSE)
    inferred_bars_per_day = infer_bars_per_day(df)
    bars_per_year = inferred_bars_per_day * 252
    # compute daily returns from equity series
    daily_equity = equity_ffill.resample('D').last().ffill()
    daily_returns = daily_equity.pct_change().dropna()
    if len(daily_returns)>1:
        avg_daily_ret = daily_returns.mean()
        vol_daily = daily_returns.std()
        annual_return = (1 + daily_returns.mean())**252 - 1
        annual_vol = daily_returns.std() * (252**0.5)
        sharpe = (annual_return) / annual_vol if annual_vol>0 else np.nan
    else:
        annual_return = returns
        annual_vol = np.nan
        sharpe = np.nan

    results = {
        'initial_capital': initial_capital,
        'final_capital': final_capital,
        'total_return_pct': returns*100,
        'num_trades': num_trades,
        'win_rate': win_rate,
        'avg_pnl': avg_pnl,
        'max_drawdown_pct': max_dd*100 if not isnan(max_dd) else np.nan,
        'annual_return_pct': annual_return*100 if not isnan(annual_return) else np.nan,
        'annual_vol_pct': annual_vol*100 if not isnan(annual_vol) else np.nan,
        'sharpe': sharpe,
        'trades_df': trades_df,
        'equity': equity_ffill,
    }

    return results

def infer_bars_per_day(df):
    # crude inference from median delta between consecutive rows
    if len(df.index) < 2:
        return 1
    deltas = df.index.to_series().diff().dropna().map(lambda x: x.total_seconds())
    median_seconds = deltas.median()
    if median_seconds <= 60:
        # minute or sub-minute; assume 390 minutes per trading day
        return 390
    elif median_seconds <= 300:
        return 78  # 5-min bars ~ 78 per day
    elif median_seconds <= 3600:
        return 7  # hourly approximate
    else:
        return 1  # daily

# ------------- Utility to load data -------------
def load_ohlc_csv(path, date_col='Date', parse_dates=True):
    df = pd.read_csv(path)
    if parse_dates:
        df[date_col] = pd.to_datetime(df[date_col])
    df = df.set_index(date_col).sort_index()
    needed = ['Open','High','Low','Close']
    for col in needed:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")
    return df

# ------------- Simple runner CLI -------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python backtest_candle.py path/to/data.csv")
        sys.exit(1)
    path = sys.argv[1]
    df = load_ohlc_csv(path)
    res = backtest(df,
                   initial_capital=100000,
                   position_size_pct=0.05,
                   commission_per_trade=20,
                   slippage_pct=0.0005,
                   stop_loss_atr_mult=1.5)

    print("=== Backtest Summary ===")
    print(f"Initial capital: {res['initial_capital']}")
    print(f"Final capital:   {res['final_capital']:.2f}")
    print(f"Total return:    {res['total_return_pct']:.2f}%")
    print(f"Number trades:   {res['num_trades']}")
    print(f"Win rate:        {res['win_rate']:.2%}" if not isnan(res['win_rate']) else "Win rate: N/A")
    print(f"Avg PnL/trade:   {res['avg_pnl']:.2f}")
    print(f"Max drawdown:    {res['max_drawdown_pct']:.2f}%")
    print(f"Annual return:   {res['annual_return_pct']:.2f}%")
    print(f"Annual vol:      {res['annual_vol_pct']:.2f}%")
    print(f"Sharpe:          {res['sharpe']:.2f}")

    # Save trades to CSV
    if not res['trades_df'].empty:
        res['trades_df'].to_csv("trades_out.csv", index=False)
        print("Saved trades to trades_out.csv")
    # Save equity curve
    res['equity'].to_csv("equity_curve.csv")
    print("Saved equity curve to equity_curve.csv")
