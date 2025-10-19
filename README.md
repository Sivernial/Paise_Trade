# 🚀 Paise Trade - Advanced Algorithmic Trading System

A comprehensive, production-ready algorithmic trading platform for the Indian stock market using Zerodha Kite Connect API.

## 🌟 Features

### 📊 **Complete Trading Infrastructure**

- **Data Management**: Historical data fetching, real-time feeds, local caching
- **Backtesting Engine**: Historical simulation with performance metrics
- **Paper Trading**: Risk-free strategy testing with realistic simulation
- **Live Trading**: Real trading execution via Zerodha Kite API
- **Portfolio Management**: Position tracking, P&L calculation, risk management

### 📈 **Technical Analysis**

- **50+ Technical Indicators**: SMA, EMA, RSI, MACD, Bollinger Bands, ATR, ADX, etc.
- **Pattern Recognition**: Candlestick patterns, chart patterns
- **Trend Analysis**: Trend detection, support/resistance levels
- **Volatility Analysis**: Historical volatility, VaR, maximum drawdown

### 🤖 **Strategy Framework**

- **Pre-built Strategies**: Moving average crossover, RSI mean reversion, multi-indicator
- **Custom Strategy Support**: Easy-to-extend base classes
- **Signal Generation**: Confidence-based signal system
- **Strategy Comparison**: Backtest multiple strategies simultaneously

### 🛡️ **Risk Management**

- **Position Sizing**: Risk-based position calculation
- **Stop Loss/Take Profit**: Automated risk controls
- **Drawdown Protection**: Daily loss limits
- **Correlation Analysis**: Portfolio diversification checks

### ⚙️ **Configuration Management**

- **Multiple Profiles**: Conservative, aggressive, custom configurations
- **Environment Integration**: Load settings from .env files
- **Dynamic Updates**: Runtime configuration changes
- **Validation**: Automatic configuration validation

## 🏗️ Architecture

```
Paise_Trade/
├── core/
│   ├── data_manager.py      # Data fetching and management
│   ├── technical_analysis.py # Technical indicators library
│   ├── strategy.py          # Strategy framework and implementations
│   ├── backtesting.py       # Backtesting engine
│   ├── portfolio_manager.py # Portfolio and position management
│   ├── trader.py            # Order execution and trading engine
│   └── config_manager.py    # Configuration management
├── config/                  # Configuration files
├── login.py                 # Zerodha authentication
├── demo_trading_system.py   # Comprehensive demo
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## 🚀 Quick Start

### 1. **Setup Environment**

```bash
# Clone the repository
git clone <repository_url>
cd Paise_Trade

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. **Configure API Credentials**

Create a `.env` file in the project root:

```env
API_KEY=your_zerodha_api_key
API_SECRET=your_zerodha_api_secret
REDIRECT_URL=http://127.0.0.1:8000
INITIAL_CAPITAL=100000
PAPER_TRADING=true
LOG_LEVEL=INFO
```

### 3. **Authenticate with Zerodha**

```bash
# Get access token
python login.py
```

### 4. **Run Demo**

```bash
# Run comprehensive demo
python demo_trading_system.py
```

## 📖 Usage Examples

### **Simple Backtesting**

```python
from core.backtesting import BacktestEngine
from core.data_manager import DataManager
from core.strategy import MovingAverageCrossoverStrategy

# Initialize components
data_manager = DataManager(kite)
strategy = MovingAverageCrossoverStrategy()
backtest = BacktestEngine(initial_capital=1000000)

# Get historical data
data = data_manager.get_multiple_symbols_data(
    symbols=['RELIANCE', 'INFY'],
    days_back=365
)

# Run backtest
results = backtest.run_backtest(data)

# Print results
backtest.print_performance_summary(results['performance_metrics'])
```

### **Paper Trading**

```python
from core.trader import TradingEngine
from core.strategy import RSIMeanReversionStrategy

# Initialize paper trading
trader = TradingEngine(paper_trading=True, initial_capital=500000)
strategy = RSIMeanReversionStrategy()

# Update market prices
trader.update_market_prices({'RELIANCE': 2450.75, 'INFY': 1520.30})

# Place orders
order_id = trader.buy('RELIANCE', 100, 2450.75)
print(f"Order placed: {order_id}")

# Check positions
positions = trader.get_positions()
print(positions)
```

### **Portfolio Management**

```python
from core.portfolio_manager import PortfolioManager, PositionType

# Initialize portfolio
portfolio = PortfolioManager(initial_capital=1000000)

# Add positions
portfolio.add_position(
    symbol='RELIANCE',
    quantity=100,
    entry_price=2450.0,
    position_type=PositionType.LONG,
    stop_loss=2327.5,  # 5% stop loss
    take_profit=2817.5  # 15% take profit
)

# Update prices
portfolio.update_prices({'RELIANCE': 2478.25})

# Check performance
portfolio.print_portfolio_summary()
```

### **Technical Analysis**

```python
from core.technical_analysis import TechnicalIndicators
import pandas as pd

# Initialize technical analysis
ta = TechnicalIndicators()

# Calculate indicators
rsi = ta.rsi(data['close'], period=14)
sma_20 = ta.sma(data['close'], period=20)
bb_upper, bb_middle, bb_lower = ta.bollinger_bands(data['close'])

# MACD
macd, signal, histogram = ta.macd(data['close'])

print(f"Current RSI: {rsi.iloc[-1]:.2f}")
print(f"Current SMA(20): {sma_20.iloc[-1]:.2f}")
```

### **Custom Strategy**

```python
from core.strategy import BaseStrategy, Signal, SignalType

class MyCustomStrategy(BaseStrategy):
    def generate_signals(self, data, current_date):
        signals = []

        for symbol, df in data.items():
            if len(df) < 20:
                continue

            # Calculate your indicators
            rsi = self.ta.rsi(df['close'], 14)
            sma = self.ta.sma(df['close'], 20)

            current_price = df['close'].iloc[-1]
            current_rsi = rsi.iloc[-1]

            # Your trading logic
            if current_rsi < 30 and current_price > sma.iloc[-1]:
                signal = Signal(
                    symbol=symbol,
                    signal_type=SignalType.BUY,
                    confidence=0.8,
                    price=current_price,
                    timestamp=current_date,
                    reason="RSI oversold with price above SMA"
                )
                signals.append(signal)

        return signals

# Use your strategy
strategy = MyCustomStrategy()
```

## 📊 Strategy Library

### **Built-in Strategies**

1. **Moving Average Crossover**

   - Buy when fast MA crosses above slow MA
   - Sell when fast MA crosses below slow MA
   - Configurable periods (default: 10/20)

2. **RSI Mean Reversion**

   - Buy when RSI < 30 (oversold)
   - Sell when RSI > 70 (overbought)
   - Configurable thresholds

3. **Bollinger Band Strategy**

   - Reversal: Buy at lower band, sell at upper band
   - Breakout: Buy above upper band, sell below lower band
   - Configurable periods and standard deviations

4. **Multi-Indicator Strategy**
   - Combines multiple indicators
   - Weighted signal confidence
   - Reduces false signals

### **Performance Metrics**

- **Returns**: Total return, annualized return
- **Risk Metrics**: Sharpe ratio, Sortino ratio, Calmar ratio
- **Drawdown**: Maximum drawdown, current drawdown
- **Trade Analysis**: Win rate, profit factor, average trade
- **Volatility**: Historical volatility, VaR

## 🛡️ Risk Management

### **Position Sizing**

- Risk-based position calculation
- Maximum position size limits
- Portfolio diversification checks

### **Stop Loss & Take Profit**

- Automatic stop loss execution
- Trailing stop loss support
- Configurable profit targets

### **Daily Limits**

- Maximum daily loss protection
- Order count limitations
- Exposure limits

## ⚙️ Configuration

### **Trading Configuration**

```python
from core.config_manager import get_config

config = get_config()

# Update settings
config.trading.max_position_size_pct = 0.1  # 10% max per position
config.trading.stop_loss_pct = 0.05         # 5% stop loss
config.save_configurations()
```

### **Strategy Parameters**

```python
# RSI strategy configuration
config.strategy.rsi_period = 14
config.strategy.rsi_oversold = 25
config.strategy.rsi_overbought = 75

# Moving average configuration
config.strategy.ma_fast_period = 8
config.strategy.ma_slow_period = 21
```

### **Configuration Profiles**

```python
# Create profiles for different risk levels
config.create_profile('conservative')
config.create_profile('aggressive')

# Load a profile
config.load_profile('conservative')
```

## 📈 Backtesting

### **Historical Data**

- Automatic data fetching from Zerodha API
- Local caching for performance
- Multiple timeframes support
- Data cleaning and validation

### **Simulation Engine**

- Realistic order execution
- Commission and slippage modeling
- Position tracking
- Performance calculation

### **Results Analysis**

- Comprehensive performance metrics
- Trade-by-trade analysis
- Equity curve generation
- Drawdown analysis

## 🔴 Live Trading

### **Paper Trading**

- Risk-free strategy testing
- Realistic market simulation
- Portfolio tracking
- Performance monitoring

### **Live Trading**

- Real order execution via Zerodha
- Order management and tracking
- Risk controls and limits
- Real-time monitoring

## 🔧 Installation & Dependencies

### **System Requirements**

- Python 3.8+
- Internet connection for API access
- Minimum 4GB RAM
- 1GB free disk space

### **Python Packages**

```bash
pip install pandas numpy scipy matplotlib seaborn
pip install kiteconnect python-dotenv flask
pip install scikit-learn ta-lib finta
```

### **Optional Packages**

```bash
pip install plotly jupyter notebook  # For advanced analysis
pip install streamlit dash           # For web interface
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Implement your changes
4. Add tests
5. Submit a pull request

## ⚠️ Disclaimer

**This software is for educational and research purposes only. Trading in financial markets involves substantial risk of loss. Past performance does not guarantee future results. Always do your own research and consider consulting with a financial advisor before making investment decisions.**

## 📞 Support

- **Documentation**: Check the code comments and docstrings
- **Issues**: Open an issue on GitHub
- **Discussions**: Use GitHub discussions for questions

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Happy Trading! 🚀📈**
