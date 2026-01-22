import sys
import os
import pandas as pd
from datetime import datetime, timedelta
import logging

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Algorithms.silver_sentinel_strategy import SilverSentinelStrategy
from Backtesting.data_fetcher import HistoricalDataFetcher
from login import get_kite_instance
from Common import SignalType, Signal

logging.basicConfig(level=logging.DEBUG, format='%(message)s')
logger = logging.getLogger(__name__)

SYMBOL = "SILVERBEES"

class MTFAPortfolio:
    """Simple portfolio for MTFA backtesting."""
    def __init__(self, initial_capital=100000):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.position = 0 # quantity
        self.entry_price = 0
        self.entry_date = None
        self.side = None
        self.trades = []

    def execute(self, signal, price, timestamp):
        if signal == SignalType.BUY and self.position == 0:
            self.side = 'LONG'
            self.position = signal.quantity
            self.entry_price = price
            self.entry_date = timestamp
            self.cash -= (self.position * price)
            logger.info(f"[{timestamp}] BUY {SYMBOL} @ {price:.2f} | {signal.reason}")
            
        elif signal == SignalType.SELL and self.position == 0:
            self.side = 'SHORT'
            self.position = -signal.quantity
            self.entry_price = price
            self.entry_date = timestamp
            self.cash += (abs(self.position) * price)
            logger.info(f"[{timestamp}] SELL {SYMBOL} @ {price:.2f} | {signal.reason}")
            
        elif signal == SignalType.EXIT and self.position != 0:
            pnl = 0
            if self.side == 'LONG':
                pnl = (price - self.entry_price) * self.position
                self.cash += (self.position * price)
            else:
                pnl = (self.entry_price - price) * abs(self.position)
                self.cash -= (abs(self.position) * price)
            
            self.trades.append({
                'entry_date': self.entry_date,
                'exit_date': timestamp,
                'entry_price': self.entry_price,
                'exit_price': price,
                'pnl': pnl,
                'side': self.side
            })
            logger.info(f"[{timestamp}] EXIT {SYMBOL} @ {price:.2f} | PnL: {pnl:.2f} | {signal.reason}")
            self.position = 0
            self.side = None

    def get_total_value(self, current_price):
        if self.position == 0:
            return self.cash
        if self.side == 'LONG':
            return self.cash + (self.position * current_price)
        else:
            return self.cash - (abs(self.position) * current_price)

def run_backtest():
    kite = get_kite_instance()
    fetcher = HistoricalDataFetcher(kite)
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    logger.info(f"Fetching Backtest Data for {SYMBOL}...")
    df_10m = fetcher.fetch_historical_data(SYMBOL, start_date, end_date, interval="10minute")
    df_1h = fetcher.fetch_historical_data(SYMBOL, start_date - timedelta(days=40), end_date, interval="60minute")
    
    if df_10m.empty or df_1h.empty:
        logger.error("Failed to fetch data")
        return

    df_10m.to_csv("silver_10m_debug.csv")
    df_1h.to_csv("silver_1h_debug.csv")

    # TZ Clean
    if df_10m.index.tz: df_10m.index = df_10m.index.tz_localize(None)
    if df_1h.index.tz: df_1h.index = df_1h.index.tz_localize(None)
    
    strategy = SilverSentinelStrategy()
    portfolio = MTFAPortfolio(initial_capital=100000)
    
    logger.info(f"\nStarting Backtest: {df_10m.index[0]} to {df_10m.index[-1]}")
    logger.info("="*50)
    
    for i in range(50, len(df_10m)):
        if i == 50: print(f"LOOP STARTED: len(df_10m)={len(df_10m)}, len(df_1h)={len(df_1h)}")
        current_time = df_10m.index[i]
        price = df_10m['close'].iloc[i]
        
        # 1. Trees: 10m data up to now
        trees_data = df_10m.iloc[:i+1]
        
        # 2. Forest: Only use 1H bars completed BEFORE current candle.
        # Kite 60min bars at '09:15' cover until '10:15'.
        # We subtract 1 hour to find the last fully closed Hourly bar.
        forest_bias_time = current_time - timedelta(hours=1)
        forest_data = df_1h[df_1h.index <= forest_bias_time]
        
        if len(forest_data) < 10: continue
        
        data_map = {
            SYMBOL: {
                '10m': trees_data,
                '1h': forest_data
            }
        }
        
        existing = [SYMBOL] if portfolio.position != 0 else []
        equity = portfolio.get_total_value(price)
        
        signals = strategy.generate_signals(data_map, current_time, capital=equity, existing_positions=existing)
        
        for sig in signals:
            portfolio.execute(sig, price, current_time)

    # Summary
    final_val = portfolio.get_total_value(df_10m['close'].iloc[-1])
    pnl = final_val - 100000
    pnl_pct = (pnl / 100000) * 100
    
    print("\n" + "="*50)
    print(f"SILVER SENTINEL MTFA BACKTEST RESULTS (V2)")
    print("="*50)
    print(f"Total Return: {pnl_pct:.2f}%")
    print(f"Total Trades: {len(portfolio.trades)}")
    win_rate = len([t for t in portfolio.trades if t['pnl'] > 0]) / len(portfolio.trades) if portfolio.trades else 0
    print(f"Win Rate:     {win_rate*100:.1f}%")
    print(f"End Value:    ₹{final_val:.2f}")
    print("="*50)

if __name__ == "__main__":
    run_backtest()
