"""
Comprehensive Example: Complete Algorithmic Trading System Demo
Shows how to use all components together for backtesting and live trading
"""

import sys
import os
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Add the core directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'core'))

# Import our trading system components
from core.data_manager import DataManager
from core.technical_analysis import TechnicalIndicators
from core.strategy import MovingAverageCrossoverStrategy, RSIMeanReversionStrategy, MultiIndicatorStrategy
from core.backtesting import BacktestEngine, OrderType
from core.portfolio_manager import PortfolioManager, PositionType
from core.trader import TradingEngine, TransactionType, OrderType as TraderOrderType

def demo_strategy_function(data, backtest_engine, current_date):
    """
    Example strategy function for backtesting
    This is where you implement your trading logic
    """
    
    # Example: Simple moving average crossover strategy
    for symbol, df in data.items():
        if len(df) < 30:  # Need enough data
            continue
        
        # Calculate indicators
        ta = TechnicalIndicators()
        sma_short = ta.sma(df['close'], 10)
        sma_long = ta.sma(df['close'], 20)
        rsi = ta.rsi(df['close'], 14)
        
        if len(sma_short) < 2 or len(sma_long) < 2:
            continue
        
        current_price = df['close'].iloc[-1]
        current_rsi = rsi.iloc[-1] if len(rsi) > 0 else 50
        
        # Check for bullish crossover with RSI confirmation
        if (sma_short.iloc[-1] > sma_long.iloc[-1] and 
            sma_short.iloc[-2] <= sma_long.iloc[-2] and 
            current_rsi < 60):  # Not overbought
            
            # Place buy order
            backtest_engine.place_order(
                symbol=symbol,
                order_type=OrderType.BUY,
                quantity=100,
                price=current_price
            )
        
        # Check for bearish crossover or RSI overbought
        elif (sma_short.iloc[-1] < sma_long.iloc[-1] and 
              sma_short.iloc[-2] >= sma_long.iloc[-2]) or current_rsi > 75:
            
            # Place sell order
            backtest_engine.place_order(
                symbol=symbol,
                order_type=OrderType.SELL,
                quantity=100,
                price=current_price
            )

def run_backtest_demo():
    """Run a comprehensive backtest demo"""
    
    print("🚀 Starting Backtesting Demo...")
    print("This demo shows how to use the backtesting engine with historical data from Zerodha API")
    
    # Note: For this demo to work with real data, you need:
    # 1. Valid Zerodha API credentials in .env file
    # 2. A valid access token
    # 3. The required Python packages installed
    
    # For now, we'll create some synthetic data for demonstration
    import pandas as pd
    import numpy as np
    
    # Create synthetic historical data for demo
    dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='D')
    
    # Simulate RELIANCE stock data
    np.random.seed(42)
    price = 2400  # Starting price
    
    reliance_data = []
    for date in dates:
        # Random walk with slight upward bias
        change = np.random.normal(0.001, 0.02)  # 0.1% daily return, 2% volatility
        price = price * (1 + change)
        
        # Generate OHLCV data
        high = price * (1 + abs(np.random.normal(0, 0.01)))
        low = price * (1 - abs(np.random.normal(0, 0.01)))
        open_price = price * (1 + np.random.normal(0, 0.005))
        volume = int(np.random.normal(1000000, 200000))
        
        reliance_data.append({
            'date': date,
            'open': open_price,
            'high': high,
            'low': low,
            'close': price,
            'volume': max(volume, 100000)  # Ensure positive volume
        })
    
    reliance_df = pd.DataFrame(reliance_data)
    reliance_df.set_index('date', inplace=True)
    
    # Create similar data for INFY
    np.random.seed(43)
    price = 1500
    
    infy_data = []
    for date in dates:
        change = np.random.normal(0.0005, 0.025)
        price = price * (1 + change)
        
        high = price * (1 + abs(np.random.normal(0, 0.012)))
        low = price * (1 - abs(np.random.normal(0, 0.012)))
        open_price = price * (1 + np.random.normal(0, 0.007))
        volume = int(np.random.normal(800000, 150000))
        
        infy_data.append({
            'date': date,
            'open': open_price,
            'high': high,
            'low': low,
            'close': price,
            'volume': max(volume, 50000)
        })
    
    infy_df = pd.DataFrame(infy_data)
    infy_df.set_index('date', inplace=True)
    
    # Prepare data for backtesting
    historical_data = {
        'RELIANCE': reliance_df,
        'INFY': infy_df
    }
    
    print(f"📊 Generated synthetic data for {len(historical_data)} symbols")
    print(f"📅 Date range: {dates[0].date()} to {dates[-1].date()}")
    
    # Initialize backtest engine
    backtest = BacktestEngine(
        initial_capital=1000000,  # 10 lakh
        commission_rate=0.001,    # 0.1% commission
        slippage_rate=0.0005     # 0.05% slippage
    )
    
    # Set strategy
    backtest.set_strategy(demo_strategy_function)
    
    # Run backtest
    start_date = datetime(2023, 3, 1)  # Start after some warmup period
    end_date = datetime(2023, 11, 30)
    
    results = backtest.run_backtest(
        data=historical_data,
        start_date=start_date,
        end_date=end_date
    )
    
    # Print results
    print("\n" + "="*60)
    print("📈 BACKTEST RESULTS")
    print("="*60)
    
    backtest.print_performance_summary(results['performance_metrics'])
    
    # Show some trades
    if results['trades']:
        trades_df = pd.DataFrame(results['trades'][-10:])  # Last 10 trades
        print(f"\n📋 RECENT TRADES (Last 10)")
        print(trades_df.to_string(index=False))
    
    return results

def demo_paper_trading():
    """Demo paper trading functionality"""
    
    print("\n🧪 Starting Paper Trading Demo...")
    
    # Initialize paper trading engine
    trader = TradingEngine(
        paper_trading=True,
        initial_capital=500000  # 5 lakh for paper trading
    )
    
    # Simulate some market prices
    current_prices = {
        'RELIANCE': 2450.75,
        'INFY': 1520.30,
        'TCS': 3890.50,
        'WIPRO': 450.25
    }
    
    trader.update_market_prices(current_prices)
    
    print(f"💰 Initial Capital: ₹{trader.current_capital:,.2f}")
    print(f"📊 Current Market Prices:")
    for symbol, price in current_prices.items():
        print(f"   {symbol}: ₹{price:.2f}")
    
    # Place some demo orders
    print(f"\n📋 Placing Demo Orders...")
    
    # Buy some stocks
    order1 = trader.buy('RELIANCE', 100, current_prices['RELIANCE'])
    order2 = trader.buy('INFY', 200, current_prices['INFY'])
    order3 = trader.buy('TCS', 50, current_prices['TCS'])
    
    print(f"✅ Placed buy orders: {order1}, {order2}, {order3}")
    
    # Simulate price changes
    new_prices = {
        'RELIANCE': 2465.80,  # +0.6%
        'INFY': 1508.75,      # -0.8%
        'TCS': 3920.25,       # +0.8%
        'WIPRO': 448.50       # -0.4%
    }
    
    trader.update_market_prices(new_prices)
    
    print(f"\n📈 Updated Market Prices:")
    for symbol, price in new_prices.items():
        old_price = current_prices[symbol]
        change_pct = ((price - old_price) / old_price) * 100
        print(f"   {symbol}: ₹{price:.2f} ({change_pct:+.2f}%)")
    
    # Sell some positions
    order4 = trader.sell('INFY', 100, new_prices['INFY'])  # Partial sell
    print(f"✅ Placed sell order: {order4}")
    
    # Show current positions
    positions_df = trader.get_positions()
    if not positions_df.empty:
        print(f"\n📊 Current Positions:")
        print(positions_df.to_string(index=False, float_format='%.2f'))
    
    # Show trading summary
    trader.print_trading_summary()
    
    return trader

def demo_strategy_comparison():
    """Demo comparing different strategies"""
    
    print("\n🔬 Strategy Comparison Demo...")
    
    # Create synthetic data for strategy testing
    import pandas as pd
    import numpy as np
    
    np.random.seed(100)
    dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='D')
    
    # Generate trending stock data
    price = 1000
    stock_data = []
    
    for i, date in enumerate(dates):
        # Create trending pattern with some noise
        trend = 0.0003 * (1 + 0.5 * np.sin(i / 50))  # Cyclical trend
        noise = np.random.normal(0, 0.02)
        change = trend + noise
        
        price = price * (1 + change)
        
        high = price * (1 + abs(np.random.normal(0, 0.01)))
        low = price * (1 - abs(np.random.normal(0, 0.01)))
        open_price = price * (1 + np.random.normal(0, 0.005))
        volume = int(np.random.normal(500000, 100000))
        
        stock_data.append({
            'date': date,
            'open': open_price,
            'high': high,
            'low': low,
            'close': price,
            'volume': max(volume, 10000)
        })
    
    df = pd.DataFrame(stock_data)
    df.set_index('date', inplace=True)
    
    test_data = {'TESTSTOCK': df}
    
    # Test different strategies
    strategies = {
        'MA Crossover': MovingAverageCrossoverStrategy(params={'fast_period': 10, 'slow_period': 20}),
        'RSI Mean Reversion': RSIMeanReversionStrategy(params={'rsi_period': 14}),
        'Multi-Indicator': MultiIndicatorStrategy(params={'min_confidence': 0.7})
    }
    
    print(f"📊 Testing {len(strategies)} strategies on synthetic data...")
    
    strategy_results = {}
    
    for name, strategy in strategies.items():
        print(f"\n🔄 Testing {name} Strategy...")
        
        # Generate signals for the last 50 days
        recent_data = df.tail(50)
        test_data_recent = {'TESTSTOCK': recent_data}
        
        signals = strategy.generate_signals(test_data_recent, datetime(2023, 12, 31))
        
        print(f"   📈 Generated {len(signals)} signals")
        
        if signals:
            for signal in signals[-3:]:  # Show last 3 signals
                print(f"   🔔 {signal.signal_type.value} at ₹{signal.price:.2f} "
                      f"(confidence: {signal.confidence:.1%})")
                print(f"      Reason: {signal.reason}")
        
        strategy_results[name] = {
            'signals': len(signals),
            'avg_confidence': np.mean([s.confidence for s in signals]) if signals else 0,
            'strategy': strategy
        }
    
    # Summary comparison
    print(f"\n📊 STRATEGY COMPARISON SUMMARY")
    print("="*50)
    
    for name, results in strategy_results.items():
        print(f"{name}:")
        print(f"  📈 Total Signals: {results['signals']}")
        print(f"  🎯 Avg Confidence: {results['avg_confidence']:.1%}")
    
    return strategy_results

def demo_portfolio_management():
    """Demo portfolio management features"""
    
    print("\n💼 Portfolio Management Demo...")
    
    # Initialize portfolio manager
    portfolio = PortfolioManager(
        initial_capital=1000000,
        commission_rate=0.001
    )
    
    print(f"💰 Initial Capital: ₹{portfolio.initial_capital:,.2f}")
    
    # Add some positions
    positions_to_add = [
        ('RELIANCE', 100, 2450.0, PositionType.LONG),
        ('INFY', 200, 1520.0, PositionType.LONG),
        ('TCS', 50, 3890.0, PositionType.LONG),
        ('HDFC', 75, 1680.0, PositionType.LONG)
    ]
    
    print(f"\n📈 Adding positions to portfolio...")
    
    for symbol, qty, price, pos_type in positions_to_add:
        success = portfolio.add_position(
            symbol=symbol,
            quantity=qty,
            entry_price=price,
            position_type=pos_type,
            stop_loss=price * 0.95,  # 5% stop loss
            take_profit=price * 1.15  # 15% take profit
        )
        
        if success:
            print(f"✅ Added {symbol}: {qty} shares @ ₹{price:.2f}")
        else:
            print(f"❌ Failed to add {symbol}")
    
    # Simulate price updates
    new_prices = {
        'RELIANCE': 2478.25,  # +1.15%
        'INFY': 1495.60,      # -1.60%
        'TCS': 3945.75,       # +1.43%
        'HDFC': 1705.20       # +1.50%
    }
    
    print(f"\n📊 Updating prices...")
    portfolio.update_prices(new_prices)
    
    # Show portfolio summary
    portfolio.print_portfolio_summary()
    
    # Show positions detail
    positions_df = portfolio.get_positions_summary()
    if not positions_df.empty:
        print(f"\n📋 DETAILED POSITIONS")
        print(positions_df.to_string(index=False, float_format='%.2f'))
    
    # Check for stop loss triggers
    stop_loss_triggers = portfolio.check_stop_losses(new_prices)
    if stop_loss_triggers:
        print(f"\n⚠️ Stop Loss Triggers: {stop_loss_triggers}")
    
    return portfolio

def main():
    """Main demo function showcasing the complete trading system"""
    
    print("🎯 COMPLETE ALGORITHMIC TRADING SYSTEM DEMO")
    print("="*60)
    print("This demo showcases all components of the trading system:")
    print("1. Backtesting Engine")
    print("2. Paper Trading")
    print("3. Strategy Comparison") 
    print("4. Portfolio Management")
    print("="*60)
    
    try:
        # Run all demos
        backtest_results = run_backtest_demo()
        
        paper_trader = demo_paper_trading()
        
        strategy_results = demo_strategy_comparison()
        
        portfolio = demo_portfolio_management()
        
        print("\n✅ ALL DEMOS COMPLETED SUCCESSFULLY!")
        print("\n📚 NEXT STEPS:")
        print("1. Install required packages: pip install -r requirements.txt")
        print("2. Set up Zerodha API credentials in .env file")
        print("3. Run login.py to get access token")
        print("4. Modify strategies to implement your trading logic")
        print("5. Test with paper trading before going live")
        print("6. Use backtesting to validate strategies")
        
        return {
            'backtest': backtest_results,
            'paper_trader': paper_trader,
            'strategies': strategy_results,
            'portfolio': portfolio
        }
        
    except Exception as e:
        print(f"❌ Error in demo: {e}")
        print("\n🔧 TROUBLESHOOTING:")
        print("1. Make sure you're in a virtual environment")
        print("2. Install dependencies: pip install pandas numpy")
        print("3. Check that all core modules are in the correct directory")
        return None

if __name__ == "__main__":
    results = main()