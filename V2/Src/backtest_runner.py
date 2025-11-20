import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime, timedelta
import logging
from Backtesting import BacktestEngine, HistoricalDataFetcher, get_strategy_instance
from Backtesting.config import MarketDataConfig, BacktestConfig
from Database import DatabaseConnection, CandleRepository
from Common import TransactionType
from login import get_kite_instance

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_backtest():
    logger.info("Starting backtest...")
    
    kite = get_kite_instance()
    if not kite:
        logger.error("Failed to initialize Kite")
        return
    
    # Load configuration
    symbols = MarketDataConfig.SYMBOLS
    end_date = datetime.now()
    start_date = end_date - timedelta(days=MarketDataConfig.LOOKBACK_DAYS)
    
    fetcher = HistoricalDataFetcher(kite)
    data = fetcher.fetch_multiple_symbols(symbols, start_date, end_date)
    
    if not data:
        logger.error("No data fetched")
        return
    
    db = DatabaseConnection()
    candle_repo = CandleRepository(db)
    
    for symbol, df in data.items():
        candles = df.reset_index().to_dict('records')
        for candle in candles:
            candle['symbol'] = symbol
            if 'timestamp' not in candle and 'date' in candle:
                candle['timestamp'] = candle['date']
        candle_repo.save_candles(candles)
    
    # Initialize strategy from config
    strategy = get_strategy_instance()
    
    # Initialize backtest engine with config parameters
    engine = BacktestEngine()
    
    def strategy_callback(data_dict, backtest_engine, current_date):
        signals = strategy.generate_signals(data_dict, current_date)
        
        for signal in signals:
            if signal.signal_type.value == "BUY":
                price = signal.price
                # Use configured position size
                quantity = int(BacktestConfig.POSITION_SIZE / price)
                if quantity > 0:
                    backtest_engine.place_order(
                        signal.symbol, 
                        TransactionType.BUY, 
                        quantity, 
                        price
                    )
            elif signal.signal_type.value == "SELL":
                if signal.symbol in backtest_engine.positions:
                    pos = backtest_engine.positions[signal.symbol]
                    backtest_engine.place_order(
                        signal.symbol,
                        TransactionType.SELL,
                        pos.quantity,
                        signal.price
                    )
    
    results = engine.run(data, strategy_callback, start_date, end_date)
    
    logger.info("=" * 60)
    logger.info("BACKTEST RESULTS")
    logger.info("=" * 60)
    logger.info(f"Total Return: {results['total_return']:.2%}")
    logger.info(f"Sharpe Ratio: {results['sharpe_ratio']:.3f}")
    logger.info(f"Max Drawdown: {results['max_drawdown']:.2%}")
    logger.info(f"Total Trades: {results['total_trades']}")
    logger.info(f"Win Rate: {results['win_rate']:.2%}")
    logger.info(f"Final Value: ${results['final_value']:,.2f}")
    logger.info("=" * 60)

if __name__ == "__main__":
    run_backtest()

