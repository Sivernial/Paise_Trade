"""
Enhanced Strategy Runner - Choose and Run Different Trading Strategies
Supports live trading with real-time data from Zerodha
"""

import os
from dotenv import load_dotenv
from kiteconnect import KiteConnect
from core.data_stream import LiveDataStreamer
from core.strategy import (
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
        'default_params': {'bb_period': 20, 'bb_std': 2, 'strategy_type': 'reversal'}
    },
    '4': {
        'name': 'Multi-Indicator Strategy',
        'class': MultiIndicatorStrategy,
        'description': 'Combines multiple indicators',
        'default_params': {'ma_fast': 10, 'ma_slow': 20, 'rsi_period': 14, 'bb_period': 20}
    }
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
        print(f"\n📊 Loading historical data for strategy initialization...")
        
        for stock, token in self.selected_stocks:
            try:
                # Get last 100 days of daily data for context
                end_date = datetime.now()
                start_date = end_date - timedelta(days=100)
                
                data = self.data_manager.get_historical_data(
                    token, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'), 'day'
                )
                
                if not data.empty:
                    self.historical_data[stock] = data
                    print(f"✅ Loaded {len(data)} days of data for {stock}")
                else:
                    print(f"⚠️ No historical data found for {stock}")
            
            except Exception as e:
                print(f"❌ Error loading data for {stock}: {e}")
    
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
            
            # Print current status
            print(f"📈 {stock_name}: ₹{current_price:.2f} | {current_time.strftime('%H:%M:%S')}")
            
        except Exception as e:
            print(f"❌ Error processing tick: {e}")
    
    def start_live_trading(self):
        """Start live trading with selected strategy and stocks"""
        print(f"\n🚀 STARTING LIVE TRADING")
        print("=" * 50)
        print(f"🎯 Strategy: {type(self.current_strategy).__name__}")
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
        
        try:
            # Step 1: Choose strategy
            self.choose_strategy()
            
            # Step 2: Choose stocks
            self.choose_stocks()
            
            # Step 3: Choose trading mode
            self.choose_trading_mode()
            
            # Step 4: Load historical data
            self.load_historical_data()
            
            # Step 5: Start live trading
            self.start_live_trading()
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    runner = LiveStrategyRunner()
    runner.run()