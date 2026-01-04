import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime, timedelta
import logging
from Backtesting import BacktestEngine, HistoricalDataFetcher
from Backtesting.config import MarketDataConfig, BacktestConfig, StrategyConfig
from Algorithms import PairTradingStrategy
from Database import DatabaseConnection, CandleRepository, TradeRepository
from Common import TransactionType
from Common.quant_utils import KalmanFilterReg
from login import get_kite_instance

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- INTRADAY CONFIGURATION ---
INTRA_CONFIG = StrategyConfig.INTRADAY_PAIR_TRADING
INTERVAL_ALIAS = "5min"     # Fetch 5min data
SIGNAL_INTERVAL = "5min"    # Signal 5min data (No resampling needed)
LOOKBACK = INTRA_CONFIG['lookback_window']
PAIRS = INTRA_CONFIG['pairs']

def run_backtest():
    logger.info("\n" + "=" * 80)
    logger.info("INTRADAY BACKTEST CONFIGURATION")
    logger.info("=" * 80)
    logger.info(f"Strategy:           INTRADAY_PAIR_TRADING")
    logger.info(f"Pairs:              {PAIRS}")
    logger.info(f"Fetch Interval:     {INTERVAL_ALIAS}")
    logger.info(f"Time Stop:          {INTRA_CONFIG['time_stop']}")
    logger.info("=" * 80 + "\n")
    
    kite = get_kite_instance()
    if not kite:
        logger.error("Failed to initialize Kite")
        return
    
    # 1. Prepare Symbols
    active_symbols = set()
    for p in PAIRS:
        active_symbols.add(p[0])
        active_symbols.add(p[1])
    symbols = list(active_symbols)
    
    # 2. Fetch Data (5-min candles for 5-10 days to cover intraday sessions)
    # 60 * 7 = 420 candles per day approx.
    # Let's fetch 30 days of 5min data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30) 
    
    fetcher = HistoricalDataFetcher(kite)
    
    logger.info(f"Fetching {INTERVAL_ALIAS} data from {start_date.date()} to {end_date.date()}")
    
    # Use fetch_and_resample (even if no resample, good wrapper) 
    # Or fetch directly
    raw_data, data = fetcher.fetch_and_resample(
        symbols, 
        start_date, 
        end_date,
        INTERVAL_ALIAS,
        SIGNAL_INTERVAL
    )
    
    if not data:
        logger.error("No data fetched")
        return

    # Save to candles DB (optional but good for debugging)
    db_conn = DatabaseConnection()
    candle_repo = CandleRepository(db_conn)
    # Clear old candles? Maybe not.
    
    # 3. Setup Strategy
    strategy = PairTradingStrategy(params=INTRA_CONFIG)
    strategy.kf_registry = {}
    for pair in PAIRS:
        strategy.kf_registry[pair] = KalmanFilterReg(delta=1e-4, R=1e-3)

    # 4. Setup Engine
    trade_repo = TradeRepository(db_conn)
    
    # Intraday Engine Settings
    enable_pm = True
    time_stop = INTRA_CONFIG.get('time_stop', '15:15') 
    
    engine = BacktestEngine(
        enable_position_management=enable_pm,
        time_stop=time_stop,
        partial_exit_pct=0.0, # Simple exit at Close or Time Stop
        trail_atr_mult=0.0 # Intraday simple
    )
    
    def strategy_callback(data_dict, backtest_engine, current_date):
        # Time logging
        if current_date.hour == 9 and current_date.minute == 15:
            logger.info(f"--- Market Open: {current_date.date()} ---")
            
        # Strategy Logic
        if hasattr(strategy, 'update_positions'):
            strategy.update_positions(backtest_engine.positions)
            
        signals = strategy.generate_signals(data_dict, current_date, capital=backtest_engine.get_portfolio_value())
        
        # Log State
        if hasattr(strategy, 'latest_state'):
            for pair_key, state in strategy.latest_state.items():
                pair_str = f"{pair_key[0]}-{pair_key[1]}"
                ts_to_log = current_date
                if hasattr(current_date, 'to_pydatetime'):
                    ts_to_log = current_date.to_pydatetime()

                trade_repo.log_strategy_state(
                    pair_str,
                    state['z_score'],
                    state['beta'],
                    state['spread'],
                    0.0,
                    "SIGNAL" if signals else "NONE",
                    timestamp=ts_to_log
                )
        
        # Execute Signals
        for signal in signals:
            if signal.signal_type.value == "BUY":
                if signal.symbol in backtest_engine.positions and backtest_engine.positions[signal.symbol].quantity > 0:
                     continue # Already Long
                
                # Close Short if exists
                if signal.symbol in backtest_engine.positions and backtest_engine.positions[signal.symbol].quantity < 0:
                     # Covered by engine or simply place buy
                     pass

                quantity = signal.quantity if signal.quantity > 0 else 100 # Default size
                
                engine.place_order(signal.symbol, TransactionType.BUY, quantity, signal.price, signal)
                logger.info(f"{current_date.time()} 🟢 BUY {signal.symbol} @ {signal.price:.2f} | {signal.reason}")

            elif signal.signal_type.value == "SELL":
                 if signal.symbol in backtest_engine.positions and backtest_engine.positions[signal.symbol].quantity < 0:
                     continue # Already Short
                 
                 quantity = signal.quantity if signal.quantity > 0 else 100
                 
                 engine.place_order(signal.symbol, TransactionType.SELL, quantity, signal.price, signal)
                 logger.info(f"{current_date.time()} 🔴 SELL {signal.symbol} @ {signal.price:.2f} | {signal.reason}")

    # Run
    # Override market hours? Engine usually assumes 9:15-3:30 for IN data
    results = engine.run(data, strategy_callback, start_date, end_date)
    
    # Results
    logger.info("\n" + "=" * 80)
    logger.info("INTRADAY RESULTS")
    logger.info("=" * 80)
    logger.info(f"Total Return:       {results['total_return']:.2%}")
    logger.info(f"Total Trades:       {results['total_trades']}")
    logger.info(f"Win Rate:           {results['win_rate']:.2%}")
    logger.info(f"Sharpe Ratio:       {results['sharpe_ratio']:.3f}")
    logger.info(f"Max Drawdown:       {results['max_drawdown']:.2%}")
    logger.info("=" * 80)

if __name__ == "__main__":
    run_backtest()
