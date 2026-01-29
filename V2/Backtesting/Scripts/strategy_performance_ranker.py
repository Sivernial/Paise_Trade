import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import argparse
from typing import List, Dict

from Src.login import get_kite_instance
from Backtesting.data_fetcher import HistoricalDataFetcher
from Algorithms.generic_3tf_strategy import Generic3TFStrategy
from Backtesting.Scripts.generic_3tf_backtest import MTFAPortfolio
from Common import SignalType
from config_3tf import CONFIG

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger("StrategyRanker")

def rank_stocks(symbols: List[str], scan_days: int = 5):
    kite = get_kite_instance()
    fetcher = HistoricalDataFetcher(kite)
    
    results = []
    
    # Use today's date vs the scan period
    end_date = datetime.now()
    start_date = end_date - timedelta(days=scan_days + 10) # Buffer for lookbacks
    
    print(f"\n🚀 Scanning {len(symbols)} stocks for Strategy-Fit (Last {scan_days} days)...\n")
    
    for symbol in symbols:
        try:
            # 1. Setup Config
            symbol_key = symbol if symbol in CONFIG else "DEFAULT"
            config = CONFIG[symbol_key]
            params = config['strategy_params'].copy()
            params['symbol'] = symbol
            
            strategy = Generic3TFStrategy(params=params)
            
            # 2. Fetch Data
            # Note: Using larger range to ensure we have enough data for EMAs
            df_10m = fetcher.fetch_historical_data(symbol, start_date, end_date, interval="10minute")
            df_30m = fetcher.fetch_historical_data(symbol, start_date, end_date, interval="30minute")
            df_1h = fetcher.fetch_historical_data(symbol, start_date, end_date, interval="60minute")
            
            if df_10m.empty or df_30m.empty or df_1h.empty:
                continue

            # Timezone strip
            for df in [df_10m, df_30m, df_1h]:
                if df.index.tz:
                    df.index = df.index.tz_localize(None)

            # 3. Quick Backtest (Last X days)
            portfolio = MTFAPortfolio(initial_capital=100000)
            
            # Find the actual start time for the last X days of testing
            test_start_boundary = datetime.now() - timedelta(days=scan_days)
            df_exec = df_10m[df_10m.index >= test_start_boundary]
            
            for i in range(len(df_exec)):
                current_time = df_exec.index[i]
                current_price = df_exec['close'].iloc[i]
                
                # Slicing data for strategy
                strategy_data = {
                    symbol: {
                        "10minute": df_10m[df_10m.index <= current_time],
                        "30minute": df_30m[df_30m.index <= current_time],
                        "1hour": df_1h[df_1h.index < current_time]
                    }
                }
                
                portfolio.check_intra_bar_exits(symbol, df_exec.iloc[i])
                existing = [s for s in portfolio.positions.keys()]
                signals = strategy.generate_signals(strategy_data, current_time, capital=portfolio.current_cash, existing_positions=existing)
                
                if signals:
                    portfolio.execute_signal(signals[0], current_price)
            
            # 4. Current Setup Check (Live State)
            latest_time = df_10m.index[-1]
            latest_price = df_10m['close'].iloc[-1]
            live_data = {
                symbol: {
                    "10minute": df_10m,
                    "30minute": df_30m,
                    "1hour": df_1h
                }
            }
            # We check if a signal *would* be generated right now or ifindicators are aligned
            # We can't easily check for a "new" signal vs "existing" alignment without modifying strategy
            # But we can look at the inner state
            
            # Simple check: Is Price > EMA10 AND Sky/Forest BULL?
            # We'll just run generate_signals one last time
            live_signals = strategy.generate_signals(live_data, latest_time, capital=100000, existing_positions=[])
            setup_status = "PULLBACK/WAIT"
            if live_signals:
                setup_status = "🔥 ACTIVE SIGNAL"
            
            summary = portfolio.get_summary()
            
            # Risk/Reward Factor
            avg_pnl = summary['total_pnl'] / summary['total_trades'] if summary['total_trades'] > 0 else 0
            
            results.append({
                "Symbol": symbol,
                "Win Rate%": f"{summary['win_rate']:.1f}%",
                "Total PnL": round(summary['total_pnl'], 2),
                "Trades": summary['total_trades'],
                "Avg PnL": round(avg_pnl, 2),
                "Status": setup_status,
                "Score": round((summary['win_rate'] * 0.6) + (min(summary['total_trades'], 5) * 8), 2) # Weighted score
            })
            
        except Exception as e:
            logger.error(f"Error scanning {symbol}: {e}")
            continue

    # Sort by Score high to low
    results.sort(key=lambda x: x['Score'], reverse=True)
    
    # Custom simple table print
    header = ["Symbol", "Win Rate%", "Total PnL", "Trades", "Avg PnL", "Status", "Score"]
    print(f"{header[0]:<12} {header[1]:<10} {header[2]:<12} {header[3]:<8} {header[4]:<10} {header[5]:<16} {header[6]:<6}")
    print("-" * 80)
    for r in results:
        print(f"{r['Symbol']:<12} {r['Win Rate%']:<10} {r['Total PnL']:<12} {r['Trades']:<8} {r['Avg PnL']:<10} {r['Status']:<16} {r['Score']:<6}")
    
    print("\n💡 Recommendation: Trade symbols with Score > 70 and 'LIVE SIGNAL' setup.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Strategy-Fit Stock Ranker')
    parser.add_argument('--symbols', type=str, help='Comma separated symbols (e.g. SILVERBEES,IRFC,KAYNES)')
    parser.add_argument('--days', type=int, default=5, help='Number of days to look back for scoring')
    args = parser.parse_args()
    
    if args.symbols:
        symbol_list = [s.strip() for s in args.symbols.split(',')]
    else:
        # Default to all symbols in config plus some high liquidity ones
        symbol_list = list(CONFIG.keys())
        if "DEFAULT" in symbol_list: symbol_list.remove("DEFAULT")
        # Add a few manual ones if config is small
        additional = ["ADANIGREEN", "KAYNES", "SILVERBEES", "IRFC", "VEDL", "HDFCBANK", "SBIN", "RELIANCE"]
        symbol_list = list(set(symbol_list + additional))

    rank_stocks(symbol_list, scan_days=args.days)
