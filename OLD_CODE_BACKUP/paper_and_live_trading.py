"""
Enhanced Strategy Runner - Choose and Run Different Trading Strategies
Supports live trading with real-time data from Zerodha
"""

import os
from dotenv import load_dotenv
from kiteconnect import KiteConnect
from core.data_stream import LiveDataStreamer
from strategies import (
    MovingAverageCrossoverStrategy, 
    RSIMeanReversionStrategy, 
    BollingerBandStrategy,
    MultiIndicatorStrategy
)
from core.trader import TradingEngine
from core.data_manager import DataManager
import pandas as pd
from datetime import datetime, timedelta

load_dotenv()

# Available strategies with their configurations
AVAILABLE_STRATEGIES = {
    '1': {
        'name': 'Moving Average Crossover',
        'class': MovingAverageCrossoverStrategy,
        'description': 'Buy when fast MA crosses above slow MA',
        'default_params': {'fast_period': 10, 'slow_period': 20}
    },
    '2': {
        'name': 'RSI Mean Reversion',
        'class': RSIMeanReversionStrategy,
        'description': 'Buy when oversold, sell when overbought',
        'default_params': {'rsi_period': 14, 'oversold_threshold': 30, 'overbought_threshold': 70}
    },
    '3': {
        'name': 'Bollinger Band Strategy',
        'class': BollingerBandStrategy,
        'description': 'Trade on Bollinger Band signals',
        'default_params': {'bb_period': 15, 'bb_std': 1.5, 'strategy_type': 'reversal'}
    },
    '4': {
        'name': 'Multi-Indicator Strategy',
        'class': MultiIndicatorStrategy,
        'description': 'Combines multiple indicators',
        'default_params': {'ma_fast': 10, 'ma_slow': 20, 'rsi_period': 14, 'bb_period': 20}
    }
}

# Available timeframes for historical data and strategy analysis
AVAILABLE_TIMEFRAMES = {
    '1': {'name': '1 Minute', 'kite_format': 'minute', 'display': '1min', 'description': 'Ultra short-term scalping'},
    '2': {'name': '3 Minute', 'kite_format': '3minute', 'display': '3min', 'description': 'Short-term scalping'},
    '3': {'name': '5 Minute', 'kite_format': '5minute', 'display': '5min', 'description': 'Intraday short-term'},
    '4': {'name': '10 Minute', 'kite_format': '10minute', 'display': '10min', 'description': 'Intraday medium-term'},
    '5': {'name': '15 Minute', 'kite_format': '15minute', 'display': '15min', 'description': 'Intraday standard'},
    '6': {'name': '30 Minute', 'kite_format': '30minute', 'display': '30min', 'description': 'Intraday long-term'},
    '7': {'name': '1 Hour', 'kite_format': 'hour', 'display': '1hr', 'description': 'Hourly analysis'},
    '8': {'name': '1 Day', 'kite_format': 'day', 'display': '1D', 'description': 'Daily/Swing trading'}
}

# Available time periods for historical data (consistent with interactive_backtest.py)
AVAILABLE_PERIODS = {
    '1': {'name': 'Last 7 days', 'days': 7, 'description': 'Good for short-term analysis'},
    '2': {'name': 'Last 2 weeks', 'days': 14, 'description': 'Balanced period for most strategies'},
    '3': {'name': 'Last 1 month', 'days': 30, 'description': 'Standard for intraday strategies'},
    '4': {'name': 'Last 2 months', 'days': 60, 'description': 'More context for analysis'},
    '5': {'name': 'Last 3 months', 'days': 90, 'description': 'Comprehensive historical context'},
    '6': {'name': 'Last 6 months', 'days': 180, 'description': 'Extended analysis period'}
}

# Stock configurations
STOCKS = {
    'RELIANCE': 738561,
    'TCS': 2953217,
    'HDFCBANK': 341249,
    'INFY': 408065,
    'WIPRO': 969473,
    'ITC': 424961
}

class LiveStrategyRunner:
    """
    Main class to run live trading strategies
    """
    
    def __init__(self):
        self.setup_api_connection()
        self.data_manager = DataManager(self.kite)
        self.trading_engine = TradingEngine(self.kite)
        
        # Strategy state
        self.current_strategy = None
        self.selected_stocks = []
        self.selected_timeframe = None
        self.selected_period = None
        self.historical_data = {}
        self.is_paper_trading = True  # Start with paper trading for safety
        
    def setup_api_connection(self):
        """Setup Zerodha API connection"""
        try:
            API_KEY = os.getenv("API_KEY")
            
            # Try to read access token from file
            try:
                with open("access_token.txt") as f:
                    ACCESS_TOKEN = f.read().strip()
            except FileNotFoundError:
                ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
            
            if not API_KEY or not ACCESS_TOKEN:
                raise ValueError("API credentials not found")
            
            self.kite = KiteConnect(api_key=API_KEY)
            self.kite.set_access_token(ACCESS_TOKEN)
            
            # Test connection
            profile = self.kite.profile()
            print(f"✅ Connected to Zerodha - Welcome {profile['user_name']}")
            
        except Exception as e:
            print(f"❌ Failed to connect to Zerodha API: {e}")
            raise
    
    def choose_strategy(self):
        """Interactive strategy selection"""
        print("\n📈 CHOOSE TRADING STRATEGY")
        print("-" * 40)
        
        for key, strategy in AVAILABLE_STRATEGIES.items():
            print(f"{key}. {strategy['name']}")
            print(f"   💡 {strategy['description']}")
        
        while True:
            choice = input(f"\nSelect strategy (1-{len(AVAILABLE_STRATEGIES)}): ").strip()
            if choice in AVAILABLE_STRATEGIES:
                selected = AVAILABLE_STRATEGIES[choice]
                
                # Get custom parameters if needed
                print(f"\n⚙️ Configure {selected['name']} Parameters")
                print("Press Enter to use defaults, or enter custom values:")
                
                params = {}
                for param, default in selected['default_params'].items():
                    user_input = input(f"{param} (default {default}): ").strip()
                    if user_input:
                        try:
                            # Try to convert to number
                            params[param] = float(user_input) if '.' in user_input else int(user_input)
                        except ValueError:
                            params[param] = user_input
                    else:
                        params[param] = default
                
                # Initialize strategy
                strategy_class = selected['class']
                self.current_strategy = strategy_class(kite=self.kite, params=params)
                
                print(f"✅ Strategy initialized: {selected['name']}")
                print(f"📊 Parameters: {params}")
                return
            
            print("❌ Invalid choice. Please try again.")
    
    def choose_timeframe(self):
        """Interactive timeframe selection"""
        print(f"\n⏰ CHOOSE ANALYSIS TIMEFRAME")
        print("-" * 40)
        print("💡 This determines the timeframe for historical data and technical analysis")
        print("📊 Live ticks are real-time, but strategy decisions use this timeframe\n")
        
        for key, timeframe in AVAILABLE_TIMEFRAMES.items():
            print(f"{key}. {timeframe['name']} ({timeframe['display']})")
            print(f"   💡 {timeframe['description']}")
        
        while True:
            choice = input(f"\nSelect timeframe (1-{len(AVAILABLE_TIMEFRAMES)}): ").strip()
            if choice in AVAILABLE_TIMEFRAMES:
                self.selected_timeframe = AVAILABLE_TIMEFRAMES[choice]
                
                print(f"✅ Selected timeframe: {self.selected_timeframe['name']}")
                print(f"📊 Historical data will use: {self.selected_timeframe['kite_format']}")
                
                # Show recommendations based on timeframe
                if choice in ['1', '2', '3']:  # 1-5 minute
                    print("⚡ Scalping mode: Fast execution, small profits, high frequency")
                    print("💡 Recommended for experienced traders with good internet connection")
                elif choice in ['4', '5', '6']:  # 10-30 minute  
                    print("⚖️ Intraday mode: Balanced approach, medium frequency")
                    print("💡 Good for most intraday strategies")
                elif choice in ['7', '8']:  # 1 hour - 1 day
                    print("📈 Swing mode: Longer holds, lower frequency")
                    print("💡 Less stressful, good for part-time trading")
                
                return
            
            print("❌ Invalid choice. Please try again.")
    
    def choose_period(self):
        """Interactive time period selection for historical data"""
        print(f"\n📅 CHOOSE HISTORICAL DATA PERIOD")
        print("-" * 40)
        print("💡 This determines how much historical data to load for strategy context")
        print("📊 More data = better context, but slower loading and higher API usage\n")
        
        for key, period_info in AVAILABLE_PERIODS.items():
            print(f"{key}. {period_info['name']}")
            print(f"   💡 {period_info['description']}")
        
        # Show recommendations based on timeframe
        if self.selected_timeframe:
            timeframe_name = self.selected_timeframe['name']
            if self.selected_timeframe['kite_format'] in ['minute', '3minute', '5minute']:
                print(f"\n💡 For {timeframe_name}: Recommend 7-14 days (options 1-2)")
            elif self.selected_timeframe['kite_format'] in ['10minute', '15minute', '30minute']:
                print(f"\n💡 For {timeframe_name}: Recommend 14-30 days (options 2-3)")
            elif self.selected_timeframe['kite_format'] == 'hour':
                print(f"\n💡 For {timeframe_name}: Recommend 30-90 days (options 3-5)")
            else:  # daily
                print(f"\n💡 For {timeframe_name}: Recommend 90-180 days (options 5-6)")
        
        while True:
            choice = input(f"\nSelect period (1-{len(AVAILABLE_PERIODS)}): ").strip()
            if choice in AVAILABLE_PERIODS:
                self.selected_period = AVAILABLE_PERIODS[choice]
                
                print(f"✅ Selected period: {self.selected_period['name']}")
                print(f"📊 Will load {self.selected_period['days']} days of historical data")
                
                # Warning for very long periods with short timeframes
                if (self.selected_timeframe and 
                    self.selected_timeframe['kite_format'] in ['minute', '3minute', '5minute'] and 
                    self.selected_period['days'] > 14):
                    print(f"⚠️ Warning: {self.selected_period['days']} days of {self.selected_timeframe['name']} data")
                    print(f"   This will be a large dataset and may take time to load!")
                    confirm = input("Continue? (y/n): ").strip().lower()
                    if confirm != 'y':
                        continue
                
                return
            
            print("❌ Invalid choice. Please try again.")
    
    def choose_stocks(self):
        """Select stocks to trade"""
        print(f"\n📊 CHOOSE STOCKS TO TRADE")
        print("-" * 40)
        
        stock_list = list(STOCKS.keys())
        for i, stock in enumerate(stock_list, 1):
            print(f"{i:2d}. {stock}")
        
        print(f"\nEnter stock numbers separated by commas (e.g., 1,3,5)")
        print(f"Or type 'all' to select all stocks")
        
        while True:
            choice = input("Your choice: ").strip().lower()
            
            if choice == 'all':
                self.selected_stocks = [(stock, token) for stock, token in STOCKS.items()]
                break
            
            try:
                indices = [int(x.strip()) - 1 for x in choice.split(',')]
                self.selected_stocks = [(stock_list[i], STOCKS[stock_list[i]]) 
                                      for i in indices if 0 <= i < len(stock_list)]
                if self.selected_stocks:
                    break
            except (ValueError, IndexError):
                pass
            
            print("❌ Invalid choice. Please try again.")
        
        print(f"✅ Selected stocks: {[stock for stock, _ in self.selected_stocks]}")
    
    def choose_trading_mode(self):
        """Choose between paper trading and live trading"""
        print(f"\n💰 CHOOSE TRADING MODE")
        print("-" * 40)
        print("1. Paper Trading (Simulated - RECOMMENDED)")
        print("2. Live Trading (Real money - USE WITH CAUTION)")
        
        while True:
            choice = input("Select mode (1-2): ").strip()
            if choice == '1':
                self.is_paper_trading = True
                self.trading_engine.set_paper_trading(True)
                print("✅ Paper trading mode enabled - Safe for testing!")
                break
            elif choice == '2':
                confirm = input("⚠️ WARNING: This will trade with real money! Type 'CONFIRM' to proceed: ")
                if confirm == 'CONFIRM':
                    self.is_paper_trading = False
                    self.trading_engine.set_paper_trading(False)
                    print("🚨 Live trading mode enabled - Trading with real money!")
                    break
                else:
                    print("❌ Confirmation failed. Staying in paper trading mode.")
                    self.is_paper_trading = True
                    self.trading_engine.set_paper_trading(True)
                    break
            else:
                print("❌ Invalid choice. Please try again.")
    
    def load_historical_data(self):
        """Load recent historical data for strategy initialization"""
        timeframe_name = self.selected_timeframe['name']
        timeframe_format = self.selected_timeframe['kite_format']
        period_name = self.selected_period['name']
        period_days = self.selected_period['days']
        
        print(f"\n📊 Loading historical data for strategy initialization...")
        print(f"⏰ Using timeframe: {timeframe_name} ({timeframe_format})")
        print(f"📅 Using period: {period_name} ({period_days} days)")
        
        # Educational explanation
        print(f"\n💡 WHY HISTORICAL DATA IS NEEDED:")
        print(f"   📈 Technical indicators (MA, RSI, BB) need past data to calculate meaningful values")
        print(f"   🎯 Strategy needs context: Is stock trending up/down? What's the volatility?")
        print(f"   🧠 Without history, first few signals would be unreliable or undefined")
        print(f"   ⚡ Live ticks update this foundation in real-time for informed decisions\n")
        
        # Calculate date range using selected period
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_days)
        
        print(f"📅 Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Estimate data volume
        if timeframe_format in ['minute', '3minute', '5minute']:
            estimated_candles = period_days * 375 // int(timeframe_format.replace('minute', '') or '1')  # Rough market hours
            print(f"� Estimated candles per stock: ~{estimated_candles}")
            if estimated_candles > 5000:
                print(f"⚠️ Large dataset warning: This may take time to load!")
        
        print()  # Empty line for clarity
        
        for stock, token in self.selected_stocks:
            try:
                print(f"📡 Fetching {timeframe_name} data for {stock} (Token: {token})...")
                
                # Format dates properly for Kite API
                start_date_str = start_date.strftime('%Y-%m-%d')
                end_date_str = end_date.strftime('%Y-%m-%d')
                
                print(f"   📅 Date range: {start_date_str} to {end_date_str}")
                print(f"   ⏰ Timeframe: {timeframe_format}")
                
                data = self.data_manager.get_historical_data(
                    instrument_token=token,
                    interval=timeframe_format,
                    from_date=start_date_str,
                    to_date=end_date_str,
                    symbol=stock
                )
                
                if not data.empty:
                    self.historical_data[stock] = data
                    print(f"✅ Loaded {len(data)} {timeframe_name} candles for {stock}")
                    
                    # Show data summary with safer date formatting
                    latest_price = data['close'].iloc[-1]
                    first_date = data.index[0]
                    last_date = data.index[-1]
                    
                    # Handle different date formats safely
                    try:
                        if hasattr(first_date, 'strftime'):
                            date_range = f"{first_date.strftime('%Y-%m-%d %H:%M')} to {last_date.strftime('%Y-%m-%d %H:%M')}"
                        else:
                            date_range = f"{first_date} to {last_date}"
                    except:
                        date_range = f"Index 0 to {len(data)-1}"
                    
                    print(f"   📈 Latest price: ₹{latest_price:.2f}")
                    print(f"   📊 Data range: {date_range}")
                    
                    # Validate data quality
                    null_count = data.isnull().sum().sum()
                    if null_count > 0:
                        print(f"   ⚠️ Warning: {null_count} null values found in data")
                    
                else:
                    print(f"⚠️ No historical data found for {stock}")
                    print(f"   💡 This might be due to:")
                    print(f"      - Market holidays in the selected period")
                    print(f"      - Invalid instrument token") 
                    print(f"      - API rate limits")
                    
            except Exception as e:
                print(f"❌ Error loading data for {stock}: {e}")
                print(f"   🔍 Debug info:")
                print(f"      - Token: {token}")
                print(f"      - Start: {start_date_str}")
                print(f"      - End: {end_date_str}")
                print(f"      - Timeframe: {timeframe_format}")
                
                # Try with a shorter period as fallback
                fallback_days = max(3, self.selected_period['days'] // 3)  # Use 1/3 of selected period, minimum 3 days
                print(f"   💡 Trying with shorter period ({fallback_days} days) as fallback...")
                try:
                    fallback_start = end_date - timedelta(days=fallback_days)
                    fallback_data = self.data_manager.get_historical_data(
                        instrument_token=token,
                        interval=timeframe_format,
                        from_date=fallback_start.strftime('%Y-%m-%d'),
                        to_date=end_date_str,
                        symbol=stock
                    )
                    if not fallback_data.empty:
                        self.historical_data[stock] = fallback_data
                        print(f"   ✅ Fallback successful: {len(fallback_data)} candles")
                    else:
                        print(f"   ❌ Fallback also failed")
                except Exception as fallback_error:
                    print(f"   ❌ Fallback error: {fallback_error}")
        
        # Show summary
        total_data_points = sum(len(data) for data in self.historical_data.values())
        if total_data_points == 0:
            print(f"\n⚠️ WARNING: No historical data loaded!")
            print(f"💡 The strategy will work with live data only, but may be less accurate initially.")
            print(f"   - Technical indicators will need time to build up")
            print(f"   - First few signals may be unreliable")
        else:
            print(f"\n✅ Total historical data loaded: {total_data_points} candles across {len(self.historical_data)} stocks")
    
    def on_tick_callback(self, tick):
        """Process live market ticks"""
        try:
            # Find which stock this tick belongs to
            token = tick['instrument_token']
            stock_name = None
            
            for stock, stock_token in self.selected_stocks:
                if stock_token == token:
                    stock_name = stock
                    break
            
            if not stock_name:
                return
            
            # Update current price data
            current_price = tick['last_price']
            current_time = datetime.now()
            
            # Create a current data point
            current_data = {
                stock_name: pd.DataFrame([{
                    'open': tick.get('ohlc', {}).get('open', current_price),
                    'high': tick.get('ohlc', {}).get('high', current_price),
                    'low': tick.get('ohlc', {}).get('low', current_price),
                    'close': current_price,
                    'volume': tick.get('volume', 0)
                }], index=[current_time])
            }
            
            # Combine with historical data if available
            if stock_name in self.historical_data:
                combined_data = {
                    stock_name: pd.concat([self.historical_data[stock_name], current_data[stock_name]])
                }
            else:
                combined_data = current_data
            
            # Generate signals using the strategy
            signals = self.current_strategy.generate_signals(combined_data, current_time)
            
            # Process signals
            for signal in signals:
                print(f"\n🔔 SIGNAL GENERATED:")
                print(f"   📊 {signal.signal_type.value} {signal.symbol} @ ₹{signal.price:.2f}")
                print(f"   💡 Reason: {signal.reason}")
                print(f"   🎯 Confidence: {signal.confidence:.2%}")
                
                # Execute trade based on signal
                if signal.signal_type.value == 'BUY':
                    # Calculate position size (you can customize this)
                    quantity = 1  # Simple: 1 share for demo
                    
                    result = self.trading_engine.buy(signal.symbol, quantity, signal.price)
                    
                    if self.is_paper_trading:
                        print(f"   📝 Paper Trade: BUY {quantity} {signal.symbol}")
                    else:
                        print(f"   💰 Live Trade: {result}")
                
                elif signal.signal_type.value == 'SELL':
                    quantity = 1  # Simple: 1 share for demo
                    
                    result = self.trading_engine.sell(signal.symbol, quantity, signal.price)
                    
                    if self.is_paper_trading:
                        print(f"   📝 Paper Trade: SELL {quantity} {signal.symbol}")
                    else:
                        print(f"   💰 Live Trade: {result}")
            
            # Print current status with timeframe info
            timeframe_display = self.selected_timeframe['display']
            print(f"📈 {stock_name}: ₹{current_price:.2f} | {current_time.strftime('%H:%M:%S')} | TF: {timeframe_display}")
            
        except Exception as e:
            print(f"❌ Error processing tick: {e}")
    
    def start_live_trading(self):
        """Start live trading with selected strategy and stocks"""
        print(f"\n🚀 STARTING LIVE TRADING")
        print("=" * 50)
        print(f"🎯 Strategy: {type(self.current_strategy).__name__}")
        print(f"⏰ Timeframe: {self.selected_timeframe['name']} ({self.selected_timeframe['display']})")
        print(f"📊 Stocks: {[stock for stock, _ in self.selected_stocks]}")
        print(f"💰 Mode: {'Paper Trading' if self.is_paper_trading else 'Live Trading'}")
        print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 50)
        
        # Get instrument tokens for streaming
        instrument_tokens = [token for _, token in self.selected_stocks]
        
        # Setup live data streamer
        API_KEY = os.getenv("API_KEY")
        try:
            with open("access_token.txt") as f:
                ACCESS_TOKEN = f.read().strip()
        except FileNotFoundError:
            ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
        
        streamer = LiveDataStreamer(API_KEY, ACCESS_TOKEN, instrument_tokens, self.on_tick_callback)
        
        try:
            streamer.start()
            
            print(f"\n✅ Live data streaming started!")
            print(f"📡 Watching {len(instrument_tokens)} instruments")
            print(f"🛑 Press Ctrl+C to stop trading\n")
            
            # Keep the script running
            while True:
                try:
                    # You can add periodic tasks here
                    # Like printing portfolio summary, etc.
                    pass
                except KeyboardInterrupt:
                    print("\n🛑 Stopping live trading...")
                    break
        
        except Exception as e:
            print(f"❌ Error in live trading: {e}")
        
        finally:
            print(f"✅ Live trading stopped at {datetime.now().strftime('%H:%M:%S')}")
    
    def run(self):
        """Main method to run the strategy runner"""
        print("🎯 LIVE STRATEGY TRADING SYSTEM")
        print("=" * 50)
        print("📊 Interactive setup for live trading with real-time data")
        print("⚙️ Configure your strategy, timeframe, and stocks step by step\n")
        
        try:
            # Step 1: Choose strategy
            self.choose_strategy()
            
            # Step 2: Choose timeframe for analysis
            self.choose_timeframe()
            
            # Step 3: Choose time period for historical data
            self.choose_period()
            
            # Step 4: Choose stocks
            self.choose_stocks()
            
            # Step 5: Choose trading mode (paper vs live)
            self.choose_trading_mode()
            
            # Step 6: Load historical data with selected timeframe and period
            self.load_historical_data()
            
            # Step 7: Show configuration summary
            self.show_configuration_summary()
            
            # Step 8: Start live trading
            self.start_live_trading()
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def show_configuration_summary(self):
        """Display the complete trading configuration before starting"""
        print(f"📋 TRADING CONFIGURATION SUMMARY")
        print("=" * 50)
        print(f"🎯 Strategy: {self.current_strategy.__class__.__name__}")
        print(f"⏰ Timeframe: {self.selected_timeframe['name']} ({self.selected_timeframe['kite_format']})")
        print(f"📅 Period: {self.selected_period['name']} ({self.selected_period['days']} days)")
        print(f"📊 Stocks: {', '.join([stock for stock, _ in self.selected_stocks])}")
        print(f"💰 Mode: {'📝 Paper Trading' if self.is_paper_trading else '🚨 LIVE TRADING'}")
        print(f"📈 Data Points: {sum(len(data) for data in self.historical_data.values())} total candles loaded")
        print("=" * 50)
        
        # Ask for final confirmation
        confirm = input("🚀 Ready to start trading? (y/n): ").strip().lower()
        if confirm != 'y':
            print("❌ Trading cancelled.")
            exit(0)

if __name__ == "__main__":
    runner = LiveStrategyRunner()
    runner.run()