import sys
import os
import argparse
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from Backtesting.data_fetcher import HistoricalDataFetcher
from Src.login import get_kite_instance
from Algorithms.generic_3tf_strategy import Generic3TFStrategy
from Common import Signal, SignalType
from config_3tf import CONFIG

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Generic_3TF_Backtest")

class MTFAPortfolio:
    def __init__(self, initial_capital: float = 100000, leverage: float = 4.0):
        self.capital = initial_capital
        self.leverage = leverage
        self.positions = {} # {symbol: {'qty': int, 'entry_price': float, 'side': str}}
        self.trades = []
        self.current_cash = initial_capital

    def execute_signal(self, signal: Signal, current_price: float):
        symbol = signal.symbol
        if signal.signal_type == SignalType.BUY:
            if symbol not in self.positions:
                qty = signal.quantity
                if qty > 0:
                    self.positions[symbol] = {
                        'qty': qty, 
                        'entry_price': current_price, 
                        'side': 'LONG',
                        'entry_time': signal.timestamp,
                        'sl': signal.stop_loss,
                        'tp': signal.target
                    }
                    logger.info(f"[OPEN LONG] {qty} {symbol} @ {current_price:.2f} | Reason: {signal.reason}")
            else:
                pos = self.positions[symbol]
                if pos['side'] == 'SHORT':
                    pnl = (pos['entry_price'] - current_price) * pos['qty']
                    self.current_cash += pnl
                    self.trades.append({
                        'symbol': symbol, 'side': 'SHORT', 'entry_price': pos['entry_price'],
                        'exit_price': current_price, 'qty': pos['qty'], 'pnl': pnl,
                        'entry_time': pos['entry_time'], 'exit_time': signal.timestamp, 'reason': signal.reason
                    })
                    logger.info(f"[CLOSE SHORT] {pos['qty']} {symbol} @ {current_price:.2f} | PnL: {pnl:.2f} | Reason: {signal.reason}")
                    del self.positions[symbol]

        elif signal.signal_type == SignalType.SELL:
            if symbol not in self.positions:
                qty = signal.quantity
                if qty > 0:
                    self.positions[symbol] = {
                        'qty': qty, 
                        'entry_price': current_price, 
                        'side': 'SHORT',
                        'entry_time': signal.timestamp,
                        'sl': signal.stop_loss,
                        'tp': signal.target
                    }
                    logger.info(f"[OPEN SHORT] {qty} {symbol} @ {current_price:.2f} | Reason: {signal.reason}")
            else:
                pos = self.positions[symbol]
                if pos['side'] == 'LONG':
                    pnl = (current_price - pos['entry_price']) * pos['qty']
                    self.current_cash += pnl
                    self.trades.append({
                        'symbol': symbol, 'side': 'LONG', 'entry_price': pos['entry_price'],
                        'exit_price': current_price, 'qty': pos['qty'], 'pnl': pnl,
                        'entry_time': pos['entry_time'], 'exit_time': signal.timestamp, 'reason': signal.reason
                    })
                    logger.info(f"[CLOSE LONG] {pos['qty']} {symbol} @ {current_price:.2f} | PnL: {pnl:.2f} | Reason: {signal.reason}")
                    del self.positions[symbol]

        elif signal.signal_type == SignalType.EXIT:
            if symbol in self.positions:
                pos = self.positions[symbol]
                if pos['side'] == 'LONG':
                    pnl = (current_price - pos['entry_price']) * pos['qty']
                    side = 'LONG'
                else:
                    pnl = (pos['entry_price'] - current_price) * pos['qty']
                    side = 'SHORT'
                
                self.current_cash += pnl
                self.trades.append({
                    'symbol': symbol, 'side': side, 'entry_price': pos['entry_price'],
                    'exit_price': current_price, 'qty': pos['qty'], 'pnl': pnl,
                    'entry_time': pos['entry_time'], 'exit_time': signal.timestamp, 'reason': signal.reason
                })
                logger.info(f"[CLOSE {side}] {pos['qty']} {symbol} @ {current_price:.2f} | PnL: {pnl:.2f} | Reason: {signal.reason}")
                del self.positions[symbol]

    def check_intra_bar_exits(self, symbol: str, bar: pd.Series):
        """Simulates broker-side SL/TP hits using the bar's High and Low."""
        if symbol not in self.positions: return
        
        pos = self.positions[symbol]
        high = bar['high']
        low = bar['low']
        timestamp = bar.name
        
        hit_sl = False
        hit_tp = False
        exit_price = 0
        
        if pos['side'] == 'LONG':
            # Check SL First (worst case)
            if pos['sl'] and low <= pos['sl']:
                hit_sl = True
                exit_price = pos['sl']
            elif pos['tp'] and high >= pos['tp']:
                hit_tp = True
                exit_price = pos['tp']
        else: # SHORT
            if pos['sl'] and high >= pos['sl']:
                hit_sl = True
                exit_price = pos['sl']
            elif pos['tp'] and low <= pos['tp']:
                hit_tp = True
                exit_price = pos['tp']
        
        if hit_sl or hit_tp:
            reason = "INTRA-BAR STOP LOSS" if hit_sl else "INTRA-BAR PROFIT TARGET"
            # Calculate PnL
            if pos['side'] == 'LONG':
                pnl = (exit_price - pos['entry_price']) * pos['qty']
            else:
                pnl = (pos['entry_price'] - exit_price) * pos['qty']
            
            self.current_cash += pnl
            self.trades.append({
                'symbol': symbol, 'side': pos['side'], 'entry_price': pos['entry_price'],
                'exit_price': exit_price, 'qty': pos['qty'], 'pnl': pnl,
                'entry_time': pos['entry_time'], 'exit_time': timestamp, 'reason': reason
            })
            logger.info(f"[{reason}] {pos['qty']} {symbol} @ {exit_price:.2f} | PnL: {pnl:.2f}")
            del self.positions[symbol]

    def get_summary(self):
        total_pnl = sum([t['pnl'] for t in self.trades])
        win_rate = (len([t for t in self.trades if t['pnl'] > 0]) / len(self.trades) * 100) if self.trades else 0
        return {
            'initial_capital': self.capital,
            'final_cash': self.current_cash,
            'total_pnl': total_pnl,
            'total_trades': len(self.trades),
            'win_rate': win_rate,
            'roi_percent': (total_pnl / self.capital) * 100
        }

def run_backtest(symbol: str, target_date: datetime, days: int = 1, capital: float = None):
    # Use symbol from config if it exists, otherwise use fallback logic or DEFAULT if available
    symbol_key = symbol
    if symbol not in CONFIG:
        if "DEFAULT" in CONFIG:
            logger.warning(f"Symbol {symbol} not found in config. Using DEFAULT settings.")
            symbol_key = "DEFAULT"
        else:
            raise ValueError(f"Symbol {symbol} not found in config_3tf.py and no DEFAULT set.")
        
    config = CONFIG[symbol_key]
    kite = get_kite_instance()
    fetcher = HistoricalDataFetcher(kite)
    
    strategy_params = config['strategy_params'].copy()
    strategy_params['symbol'] = symbol
    strategy = Generic3TFStrategy(params=strategy_params)
    
    # V7.1: Pull initial capital and leverage from config
    initial_cap = capital if capital else strategy_params.get('max_capital', 100000)
    lev = strategy_params.get('leverage', 4.0)
    
    portfolio = MTFAPortfolio(initial_capital=initial_cap, leverage=lev)
    
    test_start_date = target_date
    test_end_date = target_date + timedelta(days=days-1)
    
    logger.info(f"Fetching data for {symbol} from {test_start_date.strftime('%Y-%m-%d')} to {test_end_date.strftime('%Y-%m-%d')}...")
    
    # Use configured lookback or default lookback if using DEFAULT
    lookbacks = config.get('lookbacks', {"10m": 110, "30m": 60, "1h": 50})
    tree_interval = strategy_params.get('tree_interval', 10)
    tree_interval_str = f"{tree_interval}minute"
    
    df_tree_full = fetcher.fetch_historical_data(symbol, test_start_date - timedelta(days=10), test_end_date + timedelta(days=1), interval=tree_interval_str)
    df_30m_full = fetcher.fetch_historical_data(symbol, test_start_date - timedelta(days=20), test_end_date + timedelta(days=1), interval="30minute")
    df_1h_full = fetcher.fetch_historical_data(symbol, test_start_date - timedelta(days=40), test_end_date + timedelta(days=1), interval="60minute")
    
    if df_tree_full.empty or df_30m_full.empty or df_1h_full.empty:
        logger.error("Missing data for one or more timeframes.")
        return

    # V8.1: Fetch Index Data for Filtering
    logger.info("Fetching Index data for filtering...")
    df_nifty_full = fetcher.fetch_historical_data("NIFTY 50", test_start_date - timedelta(days=10), test_end_date + timedelta(days=1), interval="10minute")
    df_banknifty_full = fetcher.fetch_historical_data("NIFTY BANK", test_start_date - timedelta(days=10), test_end_date + timedelta(days=1), interval="10minute")
    
    for df in [df_tree_full, df_30m_full, df_1h_full, df_nifty_full, df_banknifty_full]:
        if df is not None and not df.empty and df.index.tz: 
            df.index = df.index.tz_localize(None)
    
    df_exec = df_tree_full[(df_tree_full.index >= test_start_date) & (df_tree_full.index < test_end_date + timedelta(days=1))]
    logger.info(f"Slicing complete. {len(df_exec)} execution bars found.")

    def get_index_bias(df_idx, current_time):
        if df_idx is None or df_idx.empty: return "NEUTRAL"
        idx_slice = df_idx[df_idx.index <= current_time]
        if len(idx_slice) < 20: return "NEUTRAL"
        ema = idx_slice['close'].ewm(span=20, adjust=False).mean()
        last_price = idx_slice['close'].iloc[-1]
        last_ema = ema.iloc[-1]
        return "BULLISH" if last_price > last_ema else "BEARISH"

    for i in range(len(df_exec)):
        current_time = df_exec.index[i]
        current_price = df_exec['close'].iloc[i]
        
        full_df_30m = df_30m_full[df_30m_full.index <= current_time]
        full_df_1h = df_1h_full[df_1h_full.index < current_time]
        full_df_tree = df_tree_full[df_tree_full.index <= current_time]
        
        # Calculate Index Bias
        indices_bias = {
            'NIFTY': get_index_bias(df_nifty_full, current_time),
            'BANKNIFTY': get_index_bias(df_banknifty_full, current_time)
        }
        
        strategy_data = {
            symbol: {
                "tree": full_df_tree,
                "30minute": full_df_30m,
                "1hour": full_df_1h
            }
        }
        
        # 0. Check Intra-bar SL/TP hits (V6 Broker Logic)
        portfolio.check_intra_bar_exits(symbol, df_exec.iloc[i])
        
        existing = [s for s in portfolio.positions.keys()]
        signals = strategy.generate_signals(
            strategy_data, 
            current_time, 
            capital=portfolio.current_cash, 
            existing_positions=existing,
            indices_bias=indices_bias
        )
        
        if signals:
            portfolio.execute_signal(signals[0], current_price)
            
    # Final: Close any open positions at the end of the day (V6.2 Backtest Fix)
    final_bar = df_exec.iloc[-1]
    last_time = df_exec.index[-1]
    for sym in list(portfolio.positions.keys()):
        logger.info(f"EOD FORCE CLOSE: {sym} @ {final_bar['close']:.2f}")
        portfolio.execute_signal(Signal(sym, SignalType.EXIT, final_bar['close'], last_time, 0, "EOD FORCE CLOSE"), final_bar['close']) # Pass final_bar['close'] as current_price

    summary = portfolio.get_summary()
    print("\n" + "="*50)
    print(f"GENERIC 3TF BACKTEST: {symbol}")
    print(f"Period: {test_start_date.strftime('%Y-%m-%d')} to {test_end_date.strftime('%Y-%m-%d')}")
    print("="*50)
    print(f"Initial Capital: ₹{summary['initial_capital']:.2f}")
    print(f"Final Cash:      ₹{summary['final_cash']:.2f}")
    print(f"Total PnL:       ₹{summary['total_pnl']:.2f}")
    print(f"ROI:             {summary['roi_percent']:.2f}%")
    print(f"Total Trades:    {summary['total_trades']}")
    print(f"Win Rate:        {summary['win_rate']:.1f}%")
    print("="*50)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generic 3TF MTFA Backtest')
    parser.add_argument('--symbol', type=str, required=True, help='Symbol to backtest')
    parser.add_argument('--date', type=str, default='2026-01-20', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--days', type=int, default=1, help='Number of days')
    parser.add_argument('--capital', type=float, help='Override initial capital')
    args = parser.parse_args()
    
    try:
        target_dt = datetime.strptime(args.date.strip(), '%Y-%m-%d')
        run_backtest(args.symbol, target_dt, args.days, args.capital)
    except Exception as e:
        logger.error(f"Error: {e}")
