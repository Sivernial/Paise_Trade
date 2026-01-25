import sys
import os
import argparse
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

try:
    from Backtesting.data_fetcher import HistoricalDataFetcher
    from Src.login import get_kite_instance
    from Algorithms.indigo_refined_strategy import IndigoRefinedStrategy
    from Common import Signal, SignalType
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("indigo_backtest.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("INDIGO_MTFA_Backtest")

class MTFAPortfolio:
    def __init__(self, initial_capital: float = 50000, leverage: float = 4.0):
        self.capital = initial_capital
        self.leverage = leverage
        self.positions = {}
        self.trades = []
        self.current_cash = initial_capital

    def execute_signal(self, signal: Signal, current_price: float):
        symbol = signal.symbol
        if signal.signal_type == SignalType.BUY:
            if symbol not in self.positions:
                qty = signal.quantity
                if qty > 0:
                    self.positions[symbol] = {'qty': qty, 'entry_price': current_price, 'side': 'LONG', 'entry_time': signal.timestamp}
                    logger.info(f"[OPEN LONG] {qty} {symbol} @ {current_price:.2f} | Reason: {signal.reason}")
            else:
                pos = self.positions[symbol]
                if pos['side'] == 'SHORT':
                    pnl = (pos['entry_price'] - current_price) * pos['qty']
                    self.current_cash += pnl
                    self.trades.append({'symbol': symbol, 'side': 'SHORT', 'entry_price': pos['entry_price'], 'exit_price': current_price, 'qty': pos['qty'], 'pnl': pnl, 'entry_time': pos['entry_time'], 'exit_time': signal.timestamp, 'reason': signal.reason})
                    logger.info(f"[CLOSE SHORT] {pos['qty']} {symbol} @ {current_price:.2f} | PnL: {pnl:.2f} | Reason: {signal.reason}")
                    del self.positions[symbol]
        elif signal.signal_type == SignalType.SELL:
            if symbol not in self.positions:
                # Open Short Position (Sell first)
                qty = signal.quantity
                if qty > 0:
                    self.positions[symbol] = {'qty': qty, 'entry_price': current_price, 'side': 'SHORT', 'entry_time': signal.timestamp}
                    logger.info(f"[OPEN SHORT] {qty} {symbol} @ {current_price:.2f} | Reason: {signal.reason}")
            else:
                pos = self.positions[symbol]
                if pos['side'] == 'LONG':
                    pnl = (current_price - pos['entry_price']) * pos['qty']
                    self.current_cash += pnl
                    self.trades.append({'symbol': symbol, 'side': 'LONG', 'entry_price': pos['entry_price'], 'exit_price': current_price, 'qty': pos['qty'], 'pnl': pnl, 'entry_time': pos['entry_time'], 'exit_time': signal.timestamp, 'reason': signal.reason})
                    logger.info(f"[CLOSE LONG] {pos['qty']} {symbol} @ {current_price:.2f} | PnL: {pnl:.2f} | Reason: {signal.reason}")
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

def run_backtest(target_date: datetime, days: int = 1):
    kite = get_kite_instance()
    fetcher = HistoricalDataFetcher(kite)
    
    strategy_params = {
        'symbol': 'INDIGO', 
        'forest_ema_period': 20, 
        'tree_ema_period': 9, 
        'leverage': 4.0,
        'stop_loss': 0.01,
        'profit_target': 0.025,
        'opening_noise_mins': 10
    }
    strategy = IndigoRefinedStrategy(params=strategy_params)
    portfolio = MTFAPortfolio(initial_capital=50000, leverage=4.0)
    
    test_start_date = target_date
    test_end_date = target_date + timedelta(days=days-1)
    
    logger.info(f"Fetching data for INDIGO from {test_start_date.strftime('%Y-%m-%d')} to {test_end_date.strftime('%Y-%m-%d')}...")
    df_10m_full = fetcher.fetch_historical_data("INDIGO", test_start_date - timedelta(days=10), test_end_date + timedelta(days=1), interval="10minute")
    df_1h_full = fetcher.fetch_historical_data("INDIGO", test_start_date - timedelta(days=40), test_end_date + timedelta(days=1), interval="60minute")
    
    if df_10m_full.empty or df_1h_full.empty:
        logger.error("No data fetched.")
        return

    if df_10m_full.index.tz: df_10m_full.index = df_10m_full.index.tz_localize(None)
    if df_1h_full.index.tz: df_1h_full.index = df_1h_full.index.tz_localize(None)
    
    df_exec = df_10m_full[(df_10m_full.index >= test_start_date) & (df_10m_full.index < test_end_date + timedelta(days=1))]
    logger.info(f"Slicing complete. {len(df_exec)} execution bars found.")

    for i in range(len(df_exec)):
        current_time = df_exec.index[i]
        current_price = df_exec['close'].iloc[i]
        full_df_1h = df_1h_full[df_1h_full.index < current_time]
        full_df_10m = df_10m_full[df_10m_full.index <= current_time]
        strategy_data = {"INDIGO": {"10minute": full_df_10m, "1hour": full_df_1h}}
        existing = list(portfolio.positions.keys())
        signals = strategy.generate_signals(strategy_data, current_time, capital=portfolio.current_cash, existing_positions=existing)
        for sig in signals:
            portfolio.execute_signal(sig, current_price)

    if portfolio.positions:
        end_time = df_exec.index[-1]
        end_price = df_exec['close'].iloc[-1]
        for symbol in list(portfolio.positions.keys()):
            sig = Signal(symbol=symbol, signal_type=SignalType.SELL if portfolio.positions[symbol]['side'] == 'LONG' else SignalType.BUY, price=end_price, timestamp=end_time, quantity=0, reason="End of Backtest Forced Exit")
            portfolio.execute_signal(sig, end_price)

    summary = portfolio.get_summary()
    print("\n" + "="*50)
    print(f"MTFA BACKTEST: INDIGO")
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
    parser = argparse.ArgumentParser(description='INDIGO MTFA Backtest')
    parser.add_argument('--date', type=str, default='2026-01-20', help='Target date (YYYY-MM-DD)')
    parser.add_argument('--days', type=int, default=1, help='Number of days to run')
    args = parser.parse_args()
    try:
        target_dt = datetime.strptime(args.date.strip(), '%Y-%m-%d')
        run_backtest(target_dt, args.days)
    except Exception as e:
        print(f"Error occurred: {e}")
        import traceback
        traceback.print_exc()
