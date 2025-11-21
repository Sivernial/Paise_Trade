import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime, timedelta
import logging
from Backtesting import BacktestEngine, HistoricalDataFetcher, get_strategy_instance
from Backtesting.config import MarketDataConfig, BacktestConfig, StrategyConfig
from Database import DatabaseConnection, CandleRepository
from Common import TransactionType
from login import get_kite_instance

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_backtest():
    logger.info("\n" + "=" * 80)
    logger.info("BACKTEST CONFIGURATION")
    logger.info("=" * 80)
    logger.info(f"Strategy:           {StrategyConfig.DEFAULT_STRATEGY}")
    logger.info(f"Symbols:            {', '.join(MarketDataConfig.SYMBOLS)}")
    logger.info(f"Lookback Days:      {MarketDataConfig.LOOKBACK_DAYS}")
    logger.info(f"Fetch Interval:     {MarketDataConfig.FETCH_INTERVAL}")
    logger.info(f"Signal Interval:    {MarketDataConfig.SIGNAL_INTERVAL}")
    logger.info(f"Initial Capital:    ₹{BacktestConfig.INITIAL_CAPITAL:,.2f}")
    logger.info(f"Position Size:      ₹{BacktestConfig.POSITION_SIZE:,.2f}")
    logger.info(f"Commission Rate:    {BacktestConfig.COMMISSION_RATE:.2%}")
    logger.info("=" * 80 + "\n")
    
    kite = get_kite_instance()
    if not kite:
        logger.error("Failed to initialize Kite")
        return
    
    # Load configuration
    symbols = MarketDataConfig.SYMBOLS
    end_date = datetime.now()
    start_date = end_date - timedelta(days=MarketDataConfig.LOOKBACK_DAYS)
    
    fetcher = HistoricalDataFetcher(kite)
    
    # Check if resampling is enabled
    if hasattr(MarketDataConfig, 'USE_RESAMPLING') and MarketDataConfig.USE_RESAMPLING:
        logger.info(f"Fetching {MarketDataConfig.FETCH_INTERVAL} data and resampling to {MarketDataConfig.SIGNAL_INTERVAL}")
        raw_data, data = fetcher.fetch_and_resample(
            symbols, 
            start_date, 
            end_date,
            MarketDataConfig.FETCH_INTERVAL,
            MarketDataConfig.SIGNAL_INTERVAL
        )
        
        # Store raw 1-min data in database (more granular)
        db = DatabaseConnection()
        candle_repo = CandleRepository(db)
        
        for symbol, df in raw_data.items():
            candles = df.reset_index().to_dict('records')
            for candle in candles:
                candle['symbol'] = symbol
                if 'timestamp' not in candle and 'date' in candle:
                    candle['timestamp'] = candle['date']
            candle_repo.save_candles(candles)
        
        logger.info(f"Using resampled {MarketDataConfig.SIGNAL_INTERVAL} data for signals")
    else:
        # Traditional approach - fetch at signal interval directly
        data = fetcher.fetch_multiple_symbols(symbols, start_date, end_date)
        
        db = DatabaseConnection()
        candle_repo = CandleRepository(db)
        
        for symbol, df in data.items():
            candles = df.reset_index().to_dict('records')
            for candle in candles:
                candle['symbol'] = symbol
                if 'timestamp' not in candle and 'date' in candle:
                    candle['timestamp'] = candle['date']
            candle_repo.save_candles(candles)
    
    if not data:
        logger.error("No data fetched")
        return
    
    # Initialize strategy from config
    strategy = get_strategy_instance()
    
    # Initialize backtest engine with config parameters
    engine = BacktestEngine()
    
    def strategy_callback(data_dict, backtest_engine, current_date):
        signals = strategy.generate_signals(data_dict, current_date)
        
        if signals:
            logger.info(f"\n{'='*80}")
            logger.info(f"Date: {current_date} | Signals Generated: {len(signals)}")
        
        for signal in signals:
            if signal.signal_type.value == "BUY":
                price = signal.price
                # Use configured position size
                quantity = int(BacktestConfig.POSITION_SIZE / price)
                if quantity > 0:
                    order_id = backtest_engine.place_order(
                        signal.symbol, 
                        TransactionType.BUY, 
                        quantity, 
                        price
                    )
                    if order_id:
                        logger.info(f"🟢 BUY SIGNAL: {signal.symbol}")
                        logger.info(f"   Price: ₹{price:.2f} | Qty: {quantity} | Value: ₹{price*quantity:,.2f}")
                        logger.info(f"   Reason: {signal.reason}")
                        logger.info(f"   Cash: ₹{backtest_engine.cash:,.2f}")
                    else:
                        logger.warning(f"❌ BUY FAILED: {signal.symbol} at ₹{price:.2f} - Insufficient funds")
            elif signal.signal_type.value == "SELL":
                if signal.symbol in backtest_engine.positions:
                    pos = backtest_engine.positions[signal.symbol]
                    # Calculate PnL before placing order (position will be modified)
                    entry_price = pos.entry_price
                    quantity = pos.quantity
                    pnl = (signal.price - entry_price) * quantity
                    pnl_pct = (pnl / (entry_price * quantity) * 100) if quantity > 0 else 0.0
                    
                    order_id = backtest_engine.place_order(
                        signal.symbol,
                        TransactionType.SELL,
                        quantity,
                        signal.price
                    )
                    if order_id:
                        logger.info(f"🔴 SELL SIGNAL: {signal.symbol}")
                        logger.info(f"   Entry: ₹{entry_price:.2f} → Exit: ₹{signal.price:.2f}")
                        logger.info(f"   Qty: {quantity} | PnL: ₹{pnl:,.2f} ({pnl_pct:.2f}%)")
                        logger.info(f"   Reason: {signal.reason}")
                        logger.info(f"   Cash: ₹{backtest_engine.cash:,.2f}")
                else:
                    logger.warning(f"⚠️  SELL SIGNAL IGNORED: {signal.symbol} - No position held")
    
    results = engine.run(data, strategy_callback, start_date, end_date)
    
    logger.info("\n" + "=" * 80)
    logger.info("BACKTEST RESULTS")
    logger.info("=" * 80)
    logger.info(f"Initial Capital:    ₹{BacktestConfig.INITIAL_CAPITAL:,.2f}")
    logger.info(f"Final Value:        ₹{results['final_value']:,.2f}")
    logger.info(f"Total Return:       {results['total_return']:.2%}")
    logger.info(f"Total Trades:       {results['total_trades']}")
    logger.info(f"Win Rate:           {results['win_rate']:.2%}")
    logger.info(f"Sharpe Ratio:       {results['sharpe_ratio']:.3f}")
    logger.info(f"Max Drawdown:       {results['max_drawdown']:.2%}")
    logger.info("=" * 80)

if __name__ == "__main__":
    run_backtest()

