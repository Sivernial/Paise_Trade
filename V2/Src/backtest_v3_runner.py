import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime, timedelta
import logging
import json
from Backtesting import BacktestEngine, HistoricalDataFetcher
from Algorithms.multi_factor_strategy import MultiFactorStrategy
from login import get_kite_instance

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Portfolio Configuration
BASKETS = {
    'Banking': ['SBIN', 'PNB', 'BANKBARODA', 'CANBK', 'IDFCFIRSTB'],
    'IT': ['INFY', 'TCS', 'HCLTECH', 'TECHM', 'WIPRO'],
    'Auto': ['MARUTI', 'M&M', 'TMPV', 'BAJAJ-AUTO', 'EICHERMOT'],
    'Pharma': ['SUNPHARMA', 'CIPLA', 'DRREDDY', 'DIVISLAB'],
    'Energy': ['RELIANCE', 'NTPC', 'POWERGRID', 'ONGC', 'COALINDIA']
}

def run_v3_backtest():
    kite = get_kite_instance()
    fetcher = HistoricalDataFetcher(kite)
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    # 1. Fetch Data
    all_symbols = [s for basket in BASKETS.values() for s in basket]
    logger.info(f"Fetching data for {all_symbols}")
    raw_data, data = fetcher.fetch_and_resample(all_symbols, start_date, end_date, "5min", "5min")
    LOOKBACK_WINDOW = 180
    
    # 2. Setup Strategy with Tiered Thresholds
    strategy_params = {
        'baskets': BASKETS,
        'z_threshold': 2.0, 
        'exit_z_threshold': 1.0,
        'lookback': LOOKBACK_WINDOW,
        'tiered_thresholds': {
            'Banking': 2.0,
            'IT': 2.5,
            'Auto': 2.5,
            'Pharma': 2.5,
            'Energy': 2.5
        }
    }
    
    # Try to load optimized thresholds (Phase 34)
    path = "strategy_config.json"
    if os.path.exists(path):
        try:
            with open(path, 'r') as f:
                config = json.load(f)
                strategy_params['symbol_thresholds'] = config.get('symbol_thresholds', {})
                logger.info("Backtest: Loaded AUTOMATED Z-TUNING configuration.")
        except Exception as e:
            logger.error(f"Failed to load strategy_config.json for backtest: {e}")

    strategy = MultiFactorStrategy(params=strategy_params)
    
    # 3. Setup Engine
    engine = BacktestEngine(
        initial_capital=1000000,
        enable_position_management=True,
        time_stop='15:15'
    )
    
    def strategy_callback(data_dict, backtest_engine, current_date):
        # Pass existing positions to avoid duplicates and enable exits
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
                # Close existing position
                if signal.symbol in backtest_engine.positions:
                    pos = backtest_engine.positions[signal.symbol]
                    trans_type = TransactionType.SELL if pos.quantity > 0 else TransactionType.BUY
                    backtest_engine.place_order(signal.symbol, trans_type, abs(pos.quantity), signal.price, signal)
            
            logger.info(f"[{current_date}] {signal.signal_type.value} {signal.symbol} @ {signal.price} | {signal.reason}")

    # 4. Run loop
    results = engine.run(data, strategy_callback, start_date, end_date)
    
    logger.info("\n" + "="*50)
    logger.info("V3 MULTI-FACTOR RESULTS")
    logger.info("="*50)
    logger.info(f"Total Return: {results['total_return']:.2%}")
    logger.info(f"Total Trades: {results['total_trades']}")
    logger.info(f"Win Rate:     {results['win_rate']:.2%}")
    logger.info(f"Sharpe Ratio: {results['sharpe_ratio']:.3f}")
    logger.info("="*50)

if __name__ == "__main__":
    run_v3_backtest()
