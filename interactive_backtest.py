"""
🎯 Interactive Strategy Backtesting Tool with Zerodha Historical Data
Choose strategies, stocks, timeframes, and parameters interactively
"""

import pandas as pd
from datetime import datetime, timedelta
import sys
import os

from kiteconnect import KiteConnect
from core.backtesting import BacktestEngine
from strategies import (
    MovingAverageCrossoverStrategy, 
    RSIMeanReversionStrategy, 
    BollingerBandStrategy,
    MultiIndicatorStrategy
)
from strategies.adaptive_momentum_breakout import AdaptiveMomentumBreakoutStrategy
from data_structures.backtesting_dataclass import OrderType

# Common Indian stock instrument tokens (you can add more)
STOCK_TOKENS = {
    'RELIANCE': 738561,
    'TCS': 2953217,
    'HDFCBANK': 341249,
    'INFY': 408065,
    'HINDUNILVR': 356865,
    'ICICIBANK': 1270529,
    'SBIN': 779521,
    'BHARTIARTL': 2714625,
    'ITC': 424961,
    'WIPRO': 969473,
    'LT': 2939649,
    'HCLTECH': 1850625,
    'AXISBANK': 1510401,
    'MARUTI': 2815745,
    'ASIANPAINT': 60417
}

AVAILABLE_STRATEGIES = {
    '1': {
        'name': 'Moving Average Crossover',
        'class': MovingAverageCrossoverStrategy,
        'description': 'Buy when fast MA crosses above slow MA, sell when below',
        'params': ['fast_period', 'slow_period']
    },
    '2': {
        'name': 'RSI Mean Reversion',
        'class': RSIMeanReversionStrategy,
        'description': 'Buy when RSI oversold, sell when overbought',
        'params': ['rsi_period', 'oversold_threshold', 'overbought_threshold']
    },
    '3': {
        'name': 'Bollinger Band Strategy',
        'class': BollingerBandStrategy,
        'description': 'Buy at lower band, sell at upper band',
        'params': ['bb_period', 'bb_std', 'strategy_type']
    },
    '4': {
        'name': 'Multi-Indicator Strategy',
        'class': MultiIndicatorStrategy,
        'description': 'Combines multiple indicators for signals',
        'params': ['ma_fast', 'ma_slow', 'rsi_period', 'bb_period']
    },
    '5': {
        'name': 'Adaptive Momentum Breakout',
        'class': AdaptiveMomentumBreakoutStrategy,
        'description': '🚀 Advanced intraday strategy with VWAP, SuperTrend, Volume Profile',
        'params': ['min_confidence', 'vwap_deviation_threshold', 'supertrend_multiplier', 'rsi_oversold', 'rsi_overbought']
    }
}

TIMEFRAMES = {
    '1': 'minute',
    '2': '3minute',
    '3': '5minute',
    '4': '10minute',
    '5': '15minute',
    '6': '30minute',
    '7': 'hour',
    '8': 'day'
}

def get_user_inputs():
    """
    Interactive function to get user preferences for backtesting
    """
    print("🎯 INTERACTIVE STRATEGY BACKTESTING TOOL")
    print("=" * 60)
    
    # Step 1: Choose Stock
    print("\n📈 STEP 1: Choose Stock to Backtest")
    print("-" * 40)
    
    stocks_list = list(STOCK_TOKENS.keys())
    for i, stock in enumerate(stocks_list, 1):
        print(f"{i:2d}. {stock}")
    
    while True:
        try:
            stock_choice = input(f"\nEnter stock number (1-{len(stocks_list)}) or custom symbol: ").strip()
            
            if stock_choice.isdigit():
                stock_idx = int(stock_choice) - 1
                if 0 <= stock_idx < len(stocks_list):
                    selected_stock = stocks_list[stock_idx]
                    instrument_token = STOCK_TOKENS[selected_stock]
                    break
            elif stock_choice.upper() in STOCK_TOKENS:
                selected_stock = stock_choice.upper()
                instrument_token = STOCK_TOKENS[selected_stock]
                break
            else:
                # Custom stock - ask for instrument token
                selected_stock = stock_choice.upper()
                token_input = input(f"Enter instrument token for {selected_stock}: ").strip()
                if token_input.isdigit():
                    instrument_token = int(token_input)
                    break
            
            print("❌ Invalid choice. Please try again.")
        except (ValueError, KeyError):
            print("❌ Invalid input. Please try again.")
    
    # Step 2: Choose Strategy
    print(f"\n📊 STEP 2: Choose Trading Strategy")
    print("-" * 40)
    
    for key, strategy in AVAILABLE_STRATEGIES.items():
        print(f"{key}. {strategy['name']}")
        print(f"   💡 {strategy['description']}")
    
    while True:
        strategy_choice = input(f"\nEnter strategy number (1-{len(AVAILABLE_STRATEGIES)}): ").strip()
        if strategy_choice in AVAILABLE_STRATEGIES:
            selected_strategy = AVAILABLE_STRATEGIES[strategy_choice]
            break
        print("❌ Invalid choice. Please try again.")
    
    # Step 3: Choose Timeframe
    print(f"\n⏰ STEP 3: Choose Timeframe")
    print("-" * 40)
    
    for key, timeframe in TIMEFRAMES.items():
        print(f"{key}. {timeframe}")
    
    while True:
        timeframe_choice = input(f"\nEnter timeframe number (1-{len(TIMEFRAMES)}): ").strip()
        if timeframe_choice in TIMEFRAMES:
            selected_timeframe = TIMEFRAMES[timeframe_choice]
            break
        print("❌ Invalid choice. Please try again.")
    
    # Step 4: Choose Time Period
    print(f"\n📅 STEP 4: Choose Time Period")
    print("-" * 40)
    
    period_options = {
        '1': ('Last 7 days', 7),
        '2': ('Last 2 weeks', 14),
        '3': ('Last 1 month', 30),
        '4': ('Last 2 months', 60),
        '5': ('Last 3 months', 90),
        '6': ('Last 6 months', 180),
        '7': ('Custom period', 0)
    }
    
    for key, (desc, days) in period_options.items():
        print(f"{key}. {desc}")
    
    while True:
        period_choice = input(f"\nEnter period number (1-7): ").strip()
        if period_choice in period_options:
            if period_choice == '7':
                # Custom period
                try:
                    days_back = int(input("Enter number of days back: "))
                    if days_back > 0:
                        break
                except ValueError:
                    print("❌ Please enter a valid number.")
                    continue
            else:
                days_back = period_options[period_choice][1]
                break
        print("❌ Invalid choice. Please try again.")
    
    # Step 5: Strategy Parameters
    print(f"\n⚙️ STEP 5: Strategy Parameters")
    print("-" * 40)
    
    strategy_params = {}
    param_names = selected_strategy['params']
    
    if selected_strategy['name'] == 'Moving Average Crossover':
        print("Configure Moving Average periods:")
        strategy_params['fast_period'] = get_int_input("Fast MA period (default 10): ", 10)
        strategy_params['slow_period'] = get_int_input("Slow MA period (default 20): ", 20)
        
    elif selected_strategy['name'] == 'RSI Mean Reversion':
        print("Configure RSI parameters:")
        strategy_params['rsi_period'] = get_int_input("RSI period (default 14): ", 14)
        strategy_params['oversold_threshold'] = get_float_input("Oversold threshold (default 30): ", 30)
        strategy_params['overbought_threshold'] = get_float_input("Overbought threshold (default 70): ", 70)
        
    elif selected_strategy['name'] == 'Bollinger Band Strategy':
        print("Configure Bollinger Band parameters:")
        strategy_params['bb_period'] = get_int_input("BB period (default 15): ", 15)
        strategy_params['bb_std'] = get_float_input("BB standard deviations (default 1.5): ", 1.5)
        strategy_params['strategy_type'] = get_choice_input(
            "Strategy type (1=Reversal, 2=Breakout): ", 
            {'1': 'reversal', '2': 'breakout'}, 
            'reversal'
        )
        
    elif selected_strategy['name'] == 'Multi-Indicator Strategy':
        print("Configure Multi-Indicator parameters:")
        strategy_params['ma_fast'] = get_int_input("Fast MA period (default 10): ", 10)
        strategy_params['ma_slow'] = get_int_input("Slow MA period (default 20): ", 20)
        strategy_params['rsi_period'] = get_int_input("RSI period (default 14): ", 14)
        strategy_params['bb_period'] = get_int_input("BB period (default 20): ", 20)
    
    elif selected_strategy['name'] == 'Adaptive Momentum Breakout':
        print("🚀 Configure Adaptive Momentum Breakout parameters:")
        print("   (Advanced intraday strategy with multiple indicators)")
        strategy_params['min_confidence'] = get_float_input("Minimum confidence threshold (default 0.65): ", 0.65)
        strategy_params['vwap_deviation_threshold'] = get_float_input("VWAP deviation threshold (default 0.008): ", 0.008)
        strategy_params['supertrend_multiplier'] = get_float_input("SuperTrend multiplier (default 2.5): ", 2.5)
        strategy_params['rsi_oversold'] = get_float_input("RSI oversold level (default 35): ", 35)
        strategy_params['rsi_overbought'] = get_float_input("RSI overbought level (default 65): ", 65)
        strategy_params['atr_multiplier'] = get_float_input("ATR risk multiplier (default 2.0): ", 2.0)
        strategy_params['volume_spike_threshold'] = get_float_input("Volume spike threshold (default 1.3): ", 1.3)
    
    # Step 6: Backtesting Parameters
    print(f"\n💰 STEP 6: Backtesting Parameters")
    print("-" * 40)
    
    initial_capital = get_float_input("Initial capital (default 100000): ", 100000)
    commission_rate = get_float_input("Commission rate % (default 0.2): ", 0.2) / 100
    slippage_rate = get_float_input("Slippage rate % (default 0.05): ", 0.05) / 100
    position_size_pct = get_float_input("Position size % of portfolio (default 50): ", 50) / 100
    
    return {
        'stock': selected_stock,
        'instrument_token': instrument_token,
        'strategy': selected_strategy,
        'strategy_params': strategy_params,
        'timeframe': selected_timeframe,
        'days_back': days_back,
        'initial_capital': initial_capital,
        'commission_rate': commission_rate,
        'slippage_rate': slippage_rate,
        'position_size_pct': position_size_pct
    }

def get_int_input(prompt, default):
    """Helper function to get integer input with default"""
    user_input = input(prompt).strip()
    if not user_input:
        return default
    try:
        return int(user_input)
    except ValueError:
        print(f"❌ Invalid input. Using default: {default}")
        return default

def get_float_input(prompt, default):
    """Helper function to get float input with default"""
    user_input = input(prompt).strip()
    if not user_input:
        return default
    try:
        return float(user_input)
    except ValueError:
        print(f"❌ Invalid input. Using default: {default}")
        return default

def get_choice_input(prompt, choices, default):
    """Helper function to get choice input with default"""
    user_input = input(prompt).strip()
    if not user_input:
        return default
    return choices.get(user_input, default)

def setup_kite_connection():
    """
    Setup Zerodha Kite connection using API credentials
    Make sure you have your API key and access token ready
    """
    
    # Read API credentials (make sure these are in your .env file or set them directly)
    try:
        with open('.env', 'r') as f:
            env_vars = {}
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    env_vars[key] = value.strip('"').strip("'")
        
        api_key = env_vars.get('API_KEY')
        access_token = env_vars.get('ACCESS_TOKEN')
        
    except FileNotFoundError:
        print("⚠️ .env file not found. Please set API credentials manually:")
        api_key = input("Enter your Zerodha API Key: ")
        access_token = input("Enter your Access Token: ")
    
    if not api_key or not access_token:
        print("❌ API credentials not found!")
        print("💡 Please set API_KEY and ACCESS_TOKEN in .env file")
        return None
    
    # Initialize Kite Connect
    kite = KiteConnect(api_key=api_key)
    kite.set_access_token(access_token)
    
    print(f"✅ Kite connection established")
    return kite
    

def fetch_historical_data(kite, symbol, instrument_token, days_back=60, interval="15minute"):
    """
    Fetch historical data from Zerodha in chunks to respect API interval limits.
    Intraday (minute/hour) is capped at ~60 days per call.
    """
    print(f"📊 Fetching {symbol} historical data...")
    print(f"📅 Period: Last {days_back} days")
    print(f"⏰ Timeframe: {interval}")

    # Per-interval max window (days). Adjust if your API plan differs.
    intraday_intervals = {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour'}
    max_window_days = 60 if interval in intraday_intervals else 3650  # ~10 years for 'day'

    to_date = datetime.now()
    from_date = to_date - timedelta(days=days_back)

    all_frames = []
    cur_to = to_date

    while cur_to > from_date:
        window_from = max(from_date, cur_to - timedelta(days=max_window_days - 1))

        try:
            historical_data = kite.historical_data(
                instrument_token=instrument_token,
                from_date=window_from,
                to_date=cur_to,
                interval=interval
            )
        except Exception as e:
            print(f"❌ Error fetching chunk {window_from.date()} -> {cur_to.date()}: {e}")
            break

        df_chunk = pd.DataFrame(historical_data)
        if df_chunk.empty:
            # No more data returned—stop
            break

        # Normalize
        df_chunk['date'] = pd.to_datetime(df_chunk['date'])
        all_frames.append(df_chunk)

        # Move to previous window (leave a 1-day gap to avoid overlap)
        cur_to = window_from - timedelta(days=1)

    if not all_frames:
        print(f"❌ No data received for {symbol}")
        return None

    # Concatenate and clean
    df = pd.concat(all_frames, ignore_index=True)
    df.drop_duplicates(subset=['date'], inplace=True)
    df.sort_values('date', inplace=True)
    df.set_index('date', inplace=True)

    # Standardize column names to match the rest of the code
    df.columns = ['open', 'high', 'low', 'close', 'volume']

    print(f"✅ Data fetched successfully!")
    print(f"📈 Records: {len(df)}")
    print(f"📅 Date range: {df.index[0]} to {df.index[-1]}")
    print(f"💰 Price range: ₹{df['close'].min():.2f} - ₹{df['close'].max():.2f}")
    print(f"\n📋 Sample data (last 5 records):")
    print(df.tail().round(2))

    return df

def create_strategy_function(strategy_config, position_size_pct=0.5):
    """
    Create strategy function for backtesting based on user selection
    
    Args:
        strategy_config: Dictionary with strategy class and parameters
        position_size_pct: Position size as percentage of portfolio
    
    Returns:
        Strategy function compatible with BacktestEngine
    """
    
    # Initialize the strategy
    strategy_class = strategy_config['class']
    strategy_params = strategy_config.get('params', {})
    strategy = strategy_class(params=strategy_params)
    
    def generic_backtest_function(data_dict, backtest_engine, current_date):
        """
        Generic strategy function for backtesting any strategy
        """
        
        # Generate signals using the strategy
        signals = strategy.generate_signals(data_dict, current_date)
        
        for signal in signals:
            symbol = signal.symbol
            current_price = signal.price
            portfolio_value = backtest_engine.get_portfolio_value()
            
            # Check current position
            has_position = symbol in backtest_engine.positions
            
            if signal.signal_type.value == 'BUY' and not has_position:
                # BUY Signal
                position_value = portfolio_value * position_size_pct
                shares_to_buy = int(position_value / current_price)
                
                if shares_to_buy > 0:
                    order_id = backtest_engine.place_order(symbol, OrderType.BUY, shares_to_buy)
                    print(f"🟢 {current_date.strftime('%Y-%m-%d %H:%M')} | BUY {shares_to_buy} {symbol} @ ₹{current_price:.2f}")
                    print(f"   💡 Reason: {signal.reason}")
            
            elif signal.signal_type.value == 'SELL' and has_position:
                # SELL Signal - Close entire position
                position = backtest_engine.positions[symbol]
                order_id = backtest_engine.place_order(symbol, OrderType.SELL, position.quantity)
                print(f"🔴 {current_date.strftime('%Y-%m-%d %H:%M')} | SELL {position.quantity} {symbol} @ ₹{current_price:.2f}")
                print(f"   💡 Reason: {signal.reason}")
    
    return generic_backtest_function

def run_strategy_backtest(df, symbol, config):
    """
    Run strategy backtest on historical data
    
    Args:
        df: Historical data DataFrame
        symbol: Stock symbol
        config: Configuration dictionary from user inputs
    
    Returns:
        Backtest results
    """
    
    print(f"\n🚀 RUNNING {config['strategy']['name'].upper()} BACKTEST")
    print(f"=" * 60)
    
    # Initialize BacktestEngine
    backtest = BacktestEngine(
        initial_capital=config['initial_capital'],
        commission_rate=config['commission_rate'],
        slippage_rate=config['slippage_rate'],
        max_positions=1  # Single stock backtest
    )
    
    print(f"💰 Initial Capital: ₹{backtest.initial_capital:,}")
    print(f"📊 Commission: {backtest.commission_rate:.2%}")
    print(f"⚡ Slippage: {backtest.slippage_rate:.3%}")
    
    # Create strategy function
    strategy_config = {
        'class': config['strategy']['class'],
        'params': config['strategy_params']
    }
    strategy_function = create_strategy_function(strategy_config, config['position_size_pct'])
    backtest.set_strategy(strategy_function)
    
    print(f"\n📈 Strategy: {config['strategy']['name']}")
    print(f"   Parameters: {config['strategy_params']}")
    print(f"   Position Size: {config['position_size_pct']:.1%} of portfolio")
    
    # Prepare data for backtesting
    historical_data = {symbol: df}
    
    # Set backtest period
    # For short timeframes, we need to ensure we have enough data for indicators
    min_periods = max(config['strategy_params'].get('slow_period', 20), 
                     config['strategy_params'].get('bb_period', 20),
                     config['strategy_params'].get('rsi_period', 14))
    
    start_date = df.index[max(min_periods + 5, 0)]
    end_date = df.index[-1]
    
    print(f"\n📅 Backtest Period:")
    print(f"   From: {start_date}")
    print(f"   To: {end_date}")
    print(f"   Duration: {(end_date - start_date).days} days")
    print(f"   Timeframe: {config['timeframe']}")
    
    print(f"\n⏳ Running backtest...")
    
    # Run the backtest
    # Determine plotting preference (optional key injected later)
    generate_plots = config.get('generate_plots', False)
    plot_dir = config.get('plot_output_dir', f"plots_{symbol}")

    results = backtest.run_backtest(
        data=historical_data,
        start_date=start_date,
        end_date=end_date,
        generate_plots=generate_plots,
        plot_output_dir=plot_dir,
        max_plot_symbols=1
    )
    
    return backtest, results

def analyze_results(backtest_engine, results):
    """
    Analyze and display backtest results
    """
    
    print(f"\n🎉 BACKTEST COMPLETED!")
    print(f"=" * 60)
    
    # Performance Summary
    performance = results['performance_metrics']
    backtest_engine.print_performance_summary(performance)
    
    # Completed Trades Analysis
    completed_trades = backtest_engine.get_completed_trades_summary()
    
    if not completed_trades.empty:
        print(f"\n📋 TRADE ANALYSIS:")
        print(f"   Total Completed Trades: {len(completed_trades)}")
        
        # Show all trades
        print(f"\n💼 ALL COMPLETED TRADES:")
        for idx, trade in completed_trades.iterrows():
            profit_emoji = "✅" if trade['is_profitable'] else "❌"
            print(f"{profit_emoji} Trade #{idx+1}: {trade['entry_date'].strftime('%m/%d %H:%M')} → {trade['exit_date'].strftime('%m/%d %H:%M')}")
            print(f"   💰 ₹{trade['entry_price']:.2f} → ₹{trade['exit_price']:.2f} | Qty: {trade['quantity']}")
            print(f"   📊 P&L: ₹{trade['pnl']:.2f} ({trade['return']:.2%}) | Hold: {trade['hold_days']:.1f} days")
        
        # Best and worst trades
        if len(completed_trades) > 0:
            best_trade = completed_trades.loc[completed_trades['pnl'].idxmax()]
            worst_trade = completed_trades.loc[completed_trades['pnl'].idxmin()]
            
            print(f"\n🏆 BEST TRADE: ₹{best_trade['pnl']:.2f} ({best_trade['return']:.2%})")
            print(f"💔 WORST TRADE: ₹{worst_trade['pnl']:.2f} ({worst_trade['return']:.2%})")
        
    else:
        print(f"\n❌ No completed trades found")
        print(f"💡 Possible reasons:")
        print(f"   - No MA crossover signals in the period")
        print(f"   - All positions still open")
        print(f"   - MA periods too long for the data range")
    
    # Current Positions
    current_positions = backtest_engine.get_positions_summary()
    if not current_positions.empty:
        print(f"\n💼 FINAL OPEN POSITIONS:")
        print(current_positions.to_string(index=False))
    
    # Final Summary
    print(f"\n" + "=" * 60)
    print(f"📈 FINAL SUMMARY")
    print(f"=" * 60)
    print(f"💰 Starting Capital: ₹{backtest_engine.initial_capital:,}")
    print(f"💵 Final Portfolio Value: ₹{results['final_value']:,.2f}")
    print(f"📊 Total Return: {results['total_return']:.2%}")
    
    if performance.total_trades > 0:
        print(f"🎯 Win Rate: {performance.win_rate:.1%}")
        print(f"⚡ Sharpe Ratio: {performance.sharpe_ratio:.3f}")
        print(f"📉 Max Drawdown: {performance.max_drawdown:.2%}")

def main():
    """
    Main function to run interactive strategy backtesting
    """
    print(f"🎯 INTERACTIVE STRATEGY BACKTESTING TOOL")
    print(f"Choose your stock, strategy, and parameters interactively!")
    print(f"=" * 60)

    # Step 1: Get user inputs
    config = get_user_inputs()
    # Ask user about plot generation
    try:
        plot_choice = input("\n📊 Generate visualization plots? (y/N): ").strip().lower()
        if plot_choice == 'y':
            config['generate_plots'] = True
            custom_dir = input("Enter plot output directory (default 'plots'): ").strip()
            if custom_dir:
                config['plot_output_dir'] = custom_dir
            else:
                config['plot_output_dir'] = 'plots'
        else:
            config['generate_plots'] = False
    except Exception:
        config['generate_plots'] = False

    # Step 2: Setup Zerodha connection
    print(f"\n📡 CONNECTING TO ZERODHA API")
    print("-" * 40)
    kite = setup_kite_connection()
    if not kite:
        print(f"❌ Failed to connect to Zerodha. Exiting...")
        return (None, None)

    # Step 3: Fetch historical data
    print(f"\n📊 FETCHING HISTORICAL DATA")
    print("-" * 40)
    historical_data = fetch_historical_data(
        kite,
        config['stock'],
        config['instrument_token'],
        config['days_back'],
        config['timeframe']
    )
    if historical_data is None or historical_data.empty:
        print(f"❌ Failed to fetch data. Exiting...")
        return (None, None)

    # Step 4: Run backtest
    backtest, results = run_strategy_backtest(historical_data, config['stock'], config)
    return (backtest, results)

if __name__ == "__main__":
    try:
        engine, results = main()
        if engine is None:
            # Already printed a reason above; just stop gracefully
            pass
        else:
            # If plots were generated, present summary
            if isinstance(results, dict) and results.get('plot_files'):
                print("\n🖼 GENERATED PLOTS:")
                for fp in results['plot_files']:
                    print(f"   • {fp}")
                print("\n💡 You can open these image files to inspect performance and trades.")
    except KeyboardInterrupt:
        print(f"\n\n⏹️ Backtesting interrupted by user. Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"\n🔧 Troubleshooting:")
        print(f"1. Check your API credentials in .env file")
        print(f"2. Ensure you have active Zerodha account and API access")
        print(f"3. Verify internet connection")
        print(f"4. Check if instrument token is correct")
        print(f"5. Make sure all required packages are installed: pip install kiteconnect pandas numpy")