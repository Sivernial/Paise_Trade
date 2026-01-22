import sys
import os
import pandas as pd
from datetime import datetime, timedelta
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Backtesting.data_fetcher import HistoricalDataFetcher
from login import get_kite_instance
from Common import SignalType, Signal

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

SYMBOL = "ITC"

def run_itc_mtfa_test():
    kite = get_kite_instance()
    fetcher = HistoricalDataFetcher(kite)
    
    # Single day backtest: Jan 20, 2026
    test_date = datetime(2026, 1, 20)
    start_date = test_date
    end_date = test_date + timedelta(days=1)
    
    logger.info(f"Fetching MTFA Data for {SYMBOL} on {test_date.strftime('%Y-%m-%d')}...")
    df_10m = fetcher.fetch_historical_data(SYMBOL, start_date, end_date, interval="10minute")
    # Need 30 days of 1H data for warmup
    df_1h = fetcher.fetch_historical_data(SYMBOL, test_date - timedelta(days=30), end_date, interval="60minute")
    
    if df_10m.empty or df_1h.empty:
        logger.error("Failed to fetch data")
        return

    if df_10m.index.tz: df_10m.index = df_10m.index.tz_localize(None)
    if df_1h.index.tz: df_1h.index = df_1h.index.tz_localize(None)
    
    logger.info(f"Fetched {len(df_10m)} 10m bars and {len(df_1h)} 1h bars")
    
    # Simple MTFA Logic Test
    trades = []
    position = None
    
    for i in range(50, len(df_10m)):
        current_time = df_10m.index[i]
        price = df_10m['close'].iloc[i]
        
        # Forest: 1H EMA20
        forest_bias_time = current_time - timedelta(hours=1)
        forest_data = df_1h[df_1h.index <= forest_bias_time]
        
        if len(forest_data) < 20: continue
        
        forest_data['ema'] = forest_data['close'].ewm(span=20, adjust=False).mean()
        forest_price = forest_data['close'].iloc[-1]
        forest_ema = forest_data['ema'].iloc[-1]
        forest_bias = "BULLISH" if forest_price > forest_ema else "BEARISH"
        
        # Trees: 10m EMA9
        trees_data = df_10m.iloc[:i+1]
        trees_data['ema'] = trees_data['close'].ewm(span=9, adjust=False).mean()
        tree_ema = trees_data['ema'].iloc[-1]
        
        # Entry Logic
        if position is None:
            if forest_bias == "BULLISH" and price > tree_ema:
                position = {'entry': price, 'time': current_time, 'side': 'LONG'}
                logger.info(f"[{current_time.strftime('%Y-%m-%d %H:%M')}] BUY {SYMBOL} @ {price:.2f} | Forest: {forest_bias}")
            elif forest_bias == "BEARISH" and price < tree_ema:
                position = {'entry': price, 'time': current_time, 'side': 'SHORT'}
                logger.info(f"[{current_time.strftime('%Y-%m-%d %H:%M')}] SELL {SYMBOL} @ {price:.2f} | Forest: {forest_bias}")
        
        # Exit Logic
        else:
            exit_triggered = False
            if position['side'] == 'LONG':
                if price > position['entry'] * 1.005:
                    exit_triggered = True
                    reason = "Profit 0.5%"
                elif price < position['entry'] * 0.9975:
                    exit_triggered = True
                    reason = "Stop 0.25%"
            else:
                if price < position['entry'] * 0.995:
                    exit_triggered = True
                    reason = "Profit 0.5%"
                elif price > position['entry'] * 1.0025:
                    exit_triggered = True
                    reason = "Stop 0.25%"
            
            if exit_triggered:
                pnl = (price - position['entry']) if position['side'] == 'LONG' else (position['entry'] - price)
                trades.append({'entry': position['entry'], 'exit': price, 'pnl': pnl, 'side': position['side']})
                logger.info(f"[{current_time.strftime('%Y-%m-%d %H:%M')}] EXIT {SYMBOL} @ {price:.2f} | PnL: {pnl:.2f} | {reason}")
                position = None
    
    # Summary
    print("\n" + "="*50)
    print(f"ITC MTFA TEST RESULTS")
    print("="*50)
    print(f"Total Trades: {len(trades)}")
    if trades:
        wins = len([t for t in trades if t['pnl'] > 0])
        print(f"Win Rate:     {wins/len(trades)*100:.1f}%")
        total_pnl = sum([t['pnl'] for t in trades])
        print(f"Total PnL:    ₹{total_pnl:.2f}")
    print("="*50)

if __name__ == "__main__":
    run_itc_mtfa_test()
