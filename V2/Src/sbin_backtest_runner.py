import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime, timedelta
import logging
from Backtesting import BacktestEngine, HistoricalDataFetcher
from Algorithms.sbin_sentinel_strategy import SbinSentinelStrategy
from login import get_kite_instance

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_sbin_backtest():
    kite = get_kite_instance()
    fetcher = HistoricalDataFetcher(kite)
    
    # Analyze the last 30 days (Jan 2026)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    symbol = "SBIN"
    logger.info(f"Fetching data for {symbol} from {start_date.date()} to {end_date.date()}")
    
    raw_data, data = fetcher.fetch_and_resample([symbol], start_date, end_date, "5min", "5min")
    
    if symbol not in data or data[symbol].empty:
        logger.error(f"No data for {symbol}")
        return
    
    # Setup Strategy
    strategy = SbinSentinelStrategy()
    
    # Engine
    engine = BacktestEngine(initial_capital=100000)
    
    def strategy_callback(data_dict, backtest_engine, current_date):
        existing_pos = list(backtest_engine.positions.keys())
        
        signals = strategy.generate_signals(
            data_dict, 
            current_date, 
            capital=backtest_engine.get_portfolio_value(),
            existing_positions=existing_pos
        )
        
        from Common import TransactionType, SignalType
        for signal in signals:
            if signal.signal_type == SignalType.BUY:
                backtest_engine.place_order(signal.symbol, TransactionType.BUY, signal.quantity, signal.price, signal)
            elif signal.signal_type == SignalType.SELL:
                backtest_engine.place_order(signal.symbol, TransactionType.SELL, signal.quantity, signal.price, signal)
            elif signal.signal_type == SignalType.EXIT:
                if signal.symbol in backtest_engine.positions:
                    pos = backtest_engine.positions[signal.symbol]
                    trans_type = TransactionType.SELL if pos.quantity > 0 else TransactionType.BUY
                    backtest_engine.place_order(signal.symbol, trans_type, abs(pos.quantity), signal.price, signal)
            
            logger.info(f"[{current_date}] {signal.signal_type.value} {signal.symbol} @ {signal.price} | {signal.reason}")

    logger.info("Starting SBIN Sentinel Backtest...")
    results = engine.run(data, strategy_callback, start_date, end_date)
    
    # Print Summary
    print("\n" + "="*50)
    print("SBIN SENTINEL (PHASE 40) RESULTS")
    print("="*50)
    print(f"Total Return: {results['total_return']:.4%}")
    print(f"Total Trades: {results['total_trades']}")
    print(f"Win Rate:     {results['win_rate']:.2f}%")
    print(f"Sharpe Ratio: {results['sharpe_ratio']:.3f}")
    print("="*50)
    
    # Print last 10 trades
    trades = engine.trades
    if trades:
        print("\nLast 10 Trades:")
        for t in trades[-10:]:
            pnl = t.get('pnl', 0)
            print(f"{t['entry_date']} | Entry: {t['entry_price']:.2f} | Exit: {t['exit_price']:.2f} | PnL: {pnl:.2f} | Reason: {t.get('exit_reason', 'N/A')}")

if __name__ == "__main__":
    run_sbin_backtest()
