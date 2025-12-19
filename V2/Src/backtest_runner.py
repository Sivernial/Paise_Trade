import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime, timedelta
import logging
from Backtesting import BacktestEngine, HistoricalDataFetcher, get_strategy_instance
from Backtesting.config import MarketDataConfig, BacktestConfig, StrategyConfig
from Database import DatabaseConnection, CandleRepository, TradeRepository
from Common import TransactionType
from Common.quant_utils import KalmanFilterReg
from login import get_kite_instance

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_backtest():
    # Determine active symbols first
    strategy_temp = get_strategy_instance()
    active_symbols = MarketDataConfig.SYMBOLS.copy()

    # DYNAMIC PAIR SELECTION
    if isinstance(strategy_temp, get_strategy_instance('PAIR_TRADING').__class__):
        logger.info("⚡️ Running Dynamic Pair Scanner...")
        try:
            from Common.pair_scanner import scan_pairs
            # Scan for pairs (using 60 days to suffice for recent correlation)
            scanned_df = scan_pairs(days=60)
            
            if scanned_df is not None and not scanned_df.empty:
                # Select Top 4 Unique Pairs
                top_pairs = []
                seen_assets = set()
                
                for _, row in scanned_df.iterrows():
                    if len(top_pairs) >= 4: break
                    
                    a, b = row['Asset A'], row['Asset B']
                    # Ensure diversification - avoid reusing same asset if possible?
                    # For now strictly following scan rank
                    top_pairs.append((a, b))
                
                # Update Strategy Params
                strategy_temp.params['pairs'] = top_pairs
                
                # CRITICAL: Re-initialize internal state (pairs list and KF registry)
                strategy_temp.pairs = top_pairs
                from collections import deque
                strategy_temp.kf_registry = {}
                strategy_temp.feature_history = {} # Added
                for pair in top_pairs:
                    strategy_temp.kf_registry[pair] = KalmanFilterReg(delta=1e-4, R=1e-3)
                    strategy_temp.feature_history[pair] = deque(maxlen=30) # Added

                logger.info(f"✅ Selected Top Dynamic Pairs: {top_pairs}")
                
                # Re-build active_symbols
                pair_symbols = set()
                for p in top_pairs:
                    pair_symbols.add(p[0])
                    pair_symbols.add(p[1])
                active_symbols = list(pair_symbols)
                
        except Exception as e:
            logger.error(f"Dynamic Scanning Failed: {e}. Falling back to Config.")
            
        # Fallback to config if scanning failed or empty
        if not 'pairs' in strategy_temp.params or not strategy_temp.params['pairs']:
             if 'pairs' in strategy_temp.params and strategy_temp.params['pairs']:
                pair_symbols = set()
                for p in strategy_temp.params['pairs']:
                    pair_symbols.add(p[0])
                    pair_symbols.add(p[1])
                active_symbols = list(pair_symbols)
    # Add other strategy overrides here if needed
    
    logger.info("\n" + "=" * 80)
    logger.info("BACKTEST CONFIGURATION")
    logger.info("=" * 80)
    logger.info(f"Strategy:           {StrategyConfig.DEFAULT_STRATEGY}")
    logger.info(f"Symbols:            {', '.join(active_symbols)}")
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
    symbols = active_symbols
    
    # ✅ Add market index if strategy requires it
    if hasattr(strategy_temp, 'params'):
        if 'market_index' in strategy_temp.params:
            market_index = strategy_temp.params['market_index']
            if market_index and market_index not in symbols:
                symbols.append(market_index)
                logger.info(f"📊 Adding market index for filter: {market_index}")
    
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
    
    # Initialize strategy (Use the one configured above)
    strategy = strategy_temp
    
    # Initialize DB for logging
    db_conn = DatabaseConnection()
    trade_repo = TradeRepository(db_conn)
    
    # Optional: Clear previous backtest logs for cleaner dashboard
    try:
        with db_conn.get_connection() as conn:
            conn.execute("DELETE FROM strategy_logs") # Clear for replay
            conn.commit()
    except:
        pass
    
    # Get position management settings from strategy params
    enable_pm = True
    time_stop = '15:20'
    partial_exit_pct = 0.5
    trail_atr_mult = 2.0
    
    if hasattr(strategy, 'params'):
        time_stop = strategy.params.get('time_stop', '15:20')
        partial_exit_pct = strategy.params.get('partial_exit_pct', 0.5)
        trail_atr_mult = strategy.params.get('trail_atr_mult', 2.0)
    
    # Initialize backtest engine with position management
    engine = BacktestEngine(
        enable_position_management=enable_pm,
        time_stop=time_stop,
        partial_exit_pct=partial_exit_pct,
        trail_atr_mult=trail_atr_mult
    )
    
    def strategy_callback(data_dict, backtest_engine, current_date):
        # Update strategy with current positions
        if hasattr(strategy, 'update_positions'):
            strategy.update_positions(backtest_engine.positions)
            
        signals = strategy.generate_signals(data_dict, current_date, capital=backtest_engine.get_portfolio_value())
        
        # Log Strategy State for Dashboard
        if hasattr(strategy, 'latest_state'):
            for pair_key, state in strategy.latest_state.items():
                pair_str = f"{pair_key[0]}-{pair_key[1]}"
                # Ensure timestamp is python datetime, not pandas Timestamp
                ts_to_log = current_date
                if hasattr(current_date, 'to_pydatetime'):
                    ts_to_log = current_date.to_pydatetime()

                trade_repo.log_strategy_state(
                    pair_str,
                    state['z_score'],
                    state['beta'],
                    state['spread'],
                    state.get('ai_confidence', 0.0),
                    "SIGNAL" if signals else "NONE",
                    timestamp=ts_to_log
                )
                # We need to manually update the timestamp in the DB log
                # because log_strategy_state uses CURRENT_TIMESTAMP by default.
                # Actually, capturing real-time playback might be better?
                # No, for replay we want the historical date. The Dashboard will sort by ID anyway or TS.
                # Let's override TS in a future iteration if needed, but 'log_strategy_state' 
                # doesn't accept TS. Let's rely on ID order or modify repo. 
                # For now, it will log with NOW time, which is fine for "Watch it run now".
        
        if signals:
            logger.info(f"\n{'='*80}")
            logger.info(f"Date: {current_date} | Signals Generated: {len(signals)}")
        
        for signal in signals:
            # Skip opening new positions if already have one (unless it's a short we need to cover)
            if signal.signal_type.value == "BUY":
                # Check if we have a position
                if signal.symbol in backtest_engine.positions:
                    pos = backtest_engine.positions[signal.symbol]
                    if pos.quantity > 0:
                        logger.debug(f"Already Long {signal.symbol}, skipping BUY")
                        continue
                    # If pos.quantity < 0, we proceed to BUY (Cover Short)
                
                price = signal.price
                # Use configured position size or signal quantity
                quantity = signal.quantity if signal.quantity > 0 else int(BacktestConfig.POSITION_SIZE / price)
                
                # If covering short, we might want to match the short quantity exactly?
                # For now, let's just use standard position size logic or close entire short.
                # The engine handles "Buy to Cover" if we send a BUY order.
                # If we send standard qty, it might flip to long if qty > short_qty.
                # Let's assume we want to flip to Long if signal says BUY.
                
                if quantity > 0:
                    order_id = backtest_engine.place_order(
                        signal.symbol, 
                        TransactionType.BUY, 
                        quantity, 
                        price,
                        signal=signal  # Pass signal for position management
                    )
                    if order_id:
                        logger.info(f"🟢 BUY SIGNAL: {signal.symbol}")
                        logger.info(f"   Price: ₹{price:.2f} | Qty: {quantity} | Value: ₹{price*quantity:,.2f}")
                        if signal.stop_loss:
                            logger.info(f"   Stop Loss: ₹{signal.stop_loss:.2f}")
                        if signal.target:
                            logger.info(f"   Target: ₹{signal.target:.2f}")
                        logger.info(f"   Reason: {signal.reason}")
                        logger.info(f"   Cash: ₹{backtest_engine.cash:,.2f}")
                    else:
                        logger.warning(f"❌ BUY FAILED: {signal.symbol} at ₹{price:.2f} - Insufficient funds")
            
            elif signal.signal_type.value == "SELL":
                # Check if we have a position
                if signal.symbol in backtest_engine.positions:
                    pos = backtest_engine.positions[signal.symbol]
                    
                    if pos.quantity < 0:
                        logger.debug(f"Already Short {signal.symbol}, skipping SELL")
                        continue
                        
                    # Calculate PnL before placing order (position will be modified)
                    entry_price = pos.entry_price
                    quantity = pos.quantity
                    pnl = (signal.price - entry_price) * quantity
                    pnl_pct = (pnl / (entry_price * quantity) * 100) if quantity > 0 else 0.0
                    
                    order_id = backtest_engine.place_order(
                        signal.symbol,
                        TransactionType.SELL,
                        quantity,
                        signal.price,
                        signal=signal
                    )
                    if order_id:
                        logger.info(f"🔴 SELL SIGNAL (Close Long): {signal.symbol}")
                        logger.info(f"   Entry: ₹{entry_price:.2f} → Exit: ₹{signal.price:.2f}")
                        logger.info(f"   Qty: {quantity} | PnL: ₹{pnl:,.2f} ({pnl_pct:.2f}%)")
                        logger.info(f"   Reason: {signal.reason}")
                        logger.info(f"   Cash: ₹{backtest_engine.cash:,.2f}")
                else:
                    # No position, Open Short
                    price = signal.price
                    # Use configured position size or signal quantity
                    quantity = signal.quantity if signal.quantity > 0 else int(BacktestConfig.POSITION_SIZE / price)
                    
                    if quantity > 0:
                        order_id = backtest_engine.place_order(
                            signal.symbol,
                            TransactionType.SELL,
                            quantity,
                            price,
                            signal=signal
                        )
                        if order_id:
                            logger.info(f"🔴 SELL SIGNAL (Open Short): {signal.symbol}")
                            logger.info(f"   Price: ₹{price:.2f} | Qty: {quantity} | Value: ₹{price*quantity:,.2f}")
                            logger.info(f"   Reason: {signal.reason}")
                            logger.info(f"   Cash: ₹{backtest_engine.cash:,.2f}")
                        else:
                            logger.warning(f"❌ SHORT FAILED: {signal.symbol} at ₹{price:.2f} - Insufficient funds")
    
    results = engine.run(data, strategy_callback, start_date, end_date)
    
    logger.info("\n" + "=" * 80)
    logger.info("BACKTEST RESULTS")
    logger.info("=" * 80)
    
    logger.info("OPEN POSITIONS")
    logger.info("-" * 80)
    if engine.positions:
        for symbol, pos in engine.positions.items():
            if pos.quantity != 0:
                current_price = pos.current_price
                pnl = pos.unrealized_pnl
                pnl_pct = (pnl / (pos.entry_price * abs(pos.quantity))) * 100 if pos.entry_price else 0
                logger.info(f"{symbol}: Qty: {pos.quantity} | Entry: {pos.entry_price:.2f} | Current: {current_price:.2f} | PnL: {pnl:,.2f} ({pnl_pct:.2f}%)")
    else:
        logger.info("No open positions.")
    logger.info("-" * 80)

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

