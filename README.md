# 🚀 Paise Trade - Algorithmic Trading System

A comprehensive algorithmic trading platform for Indian stock markets using Zerodha Kite API.

## 📁 Project Structure

```
Paise_Trade/
├── 📊 Core Trading System
│   ├── core/
│   │   ├── backtesting.py          # Backtesting engine with proper trade matching
│   │   ├── strategy.py             # Trading strategies (MA, RSI, Bollinger, Multi-indicator)
│   │   ├── trader.py               # Order execution (paper & live trading)
│   │   ├── data_manager.py         # Historical data fetching & caching
│   │   ├── technical_analysis.py   # 50+ technical indicators
│   │   ├── portfolio_manager.py    # Position tracking & risk management
│   │   ├── data_stream.py          # Live market data streaming
│   │   └── config_manager.py       # Configuration management
│   │
│   ├── data_structures/
│   │   ├── backtesting_dataclass.py    # Backtest data classes
│   │   ├── trading_dataclass.py        # Trading data classes
│   │   ├── strategy_dataclass.py       # Strategy data classes
│   │   ├── portfolio_dataclass.py      # Portfolio data classes
│   │   └── config_dataclass.py         # Configuration data classes
│   │
├── 🎯 Main Applications
│   ├── interactive_backtest.py     # Interactive backtesting tool
│   ├── paper_and_live_trading.py   # Paper & live trading interface
│   ├── quick_start.py              # Getting started guide
│   └── login.py                    # Zerodha authentication helper
│   │
├── 📋 Configuration
│   ├── .env                        # API credentials (not in git)
│   ├── access_token.txt            # Zerodha access token (not in git)
│   ├── requirements.txt            # Python dependencies
│   └── .gitignore                  # Git ignore patterns
│   │
└── 📚 Documentation
    └── README.md                   # This file
```

## 🚀 Quick Start

### 1. Installation
```bash
# Clone the repository
git clone <your-repo-url>
cd Paise_Trade

# Install dependencies
pip install -r requirements.txt
```

### 2. Setup Zerodha API Credentials
Create a `.env` file with your Zerodha credentials:
```env
API_KEY=your_zerodha_api_key
ACCESS_TOKEN=your_access_token
```

### 3. Choose Your Tool

#### 📊 **Interactive Backtesting**
Test strategies on historical data:
```bash
python interactive_backtest.py
```
- Choose from 15+ Indian stocks
- 4 built-in strategies (MA Crossover, RSI, Bollinger Bands, Multi-indicator)
- Multiple timeframes (1min to daily)
- Customizable parameters
- Comprehensive performance analysis

#### 📈 **Paper & Live Trading**
Run strategies with real-time data:
```bash
python paper_and_live_trading.py
```
- **Paper Trading**: Risk-free testing with simulated trades
- **Live Trading**: Real money trading (use with caution!)
- Real-time signal generation
- Multiple stock monitoring
- Interactive strategy selection

#### 🎯 **Quick Start Guide**
New to the system? Start here:
```bash
python quick_start.py
```

## 🛠️ Available Trading Strategies

### 1. **Moving Average Crossover**
- **Signal**: Buy when fast MA crosses above slow MA
- **Parameters**: Fast period (default: 10), Slow period (default: 20)
- **Best for**: Trend following

### 2. **RSI Mean Reversion**
- **Signal**: Buy when RSI < 30 (oversold), Sell when RSI > 70 (overbought)
- **Parameters**: RSI period (default: 14), thresholds
- **Best for**: Range-bound markets

### 3. **Bollinger Band Strategy**
- **Signal**: Buy at lower band, sell at upper band (reversal) or breakouts
- **Parameters**: Period (default: 20), Standard deviations (default: 2)
- **Best for**: Volatility-based trading

### 4. **Multi-Indicator Strategy**
- **Signal**: Combines MA, RSI, and BB for robust signals
- **Parameters**: Customizable for all indicators
- **Best for**: Comprehensive analysis

## 📊 Features

### ✅ **Backtesting Engine**
- **Accurate Trade Matching**: Proper buy/sell pair tracking
- **Realistic Costs**: Commission and slippage modeling
- **Performance Metrics**: Sharpe ratio, win rate, drawdown, profit factor
- **Trade Analysis**: Individual trade P&L, hold times, best/worst trades

### ✅ **Live Trading System**
- **Paper Trading**: Safe testing environment
- **Live Trading**: Real order execution via Zerodha
- **Risk Management**: Position sizing, daily limits
- **Real-time Monitoring**: Live price updates and signal generation

### ✅ **Data Management**
- **Historical Data**: Fetch from Zerodha API with intelligent caching
- **Multiple Timeframes**: 1min to daily data
- **Data Quality**: Automatic cleaning and validation
- **Offline Support**: SQLite database for cached data

### ✅ **Technical Analysis**
- **50+ Indicators**: SMA, EMA, RSI, MACD, Bollinger Bands, ATR, ADX, etc.
- **Pattern Recognition**: Support/resistance, trend analysis
- **Custom Indicators**: Easy to add new technical indicators

## 📈 Example Usage

### Backtesting Example
```python
# Run interactive backtesting
python interactive_backtest.py

# Choose:
# 1. Stock: RELIANCE
# 2. Strategy: Moving Average Crossover (10/20)
# 3. Timeframe: 15 minute
# 4. Period: Last 2 months
# 5. Capital: ₹1,00,000

# Results:
# Total Return: 8.45%
# Win Rate: 62.5%
# Sharpe Ratio: 0.676
# Max Drawdown: -5.67%
```

### Live Trading Example
```python
# Run paper trading
python paper_and_live_trading.py

# Choose:
# 1. Strategy: RSI Mean Reversion
# 2. Stocks: RELIANCE, TCS
# 3. Mode: Paper Trading (safe)

# Output:
# 🔔 SIGNAL: BUY RELIANCE @ ₹2,545.30
# 💡 Reason: RSI oversold (28.5)
# 📝 Paper Trade: BUY 39 RELIANCE
```

## ⚠️ Important Notes

### **Safety First**
- **Always start with paper trading** to test strategies
- **Use small position sizes** when going live
- **Set proper risk limits** before live trading
- **Monitor trades closely** during market hours

### **API Limitations**
- Zerodha access tokens expire daily
- Rate limits apply to API calls
- Market data is available only during trading hours

### **Risk Disclaimer**
- **Past performance doesn't guarantee future results**
- **Trading involves significant risk of loss**
- **Only trade with money you can afford to lose**
- **This is for educational purposes**

## 🔧 Development

### Adding New Strategies
1. Create strategy class inheriting from `BaseStrategy`
2. Implement `generate_signals()` method
3. Add to available strategies in applications

### Custom Indicators
1. Add indicator function to `TechnicalAnalysis` class
2. Use in strategy signal generation logic

### Database Schema
The system uses SQLite for caching:
- `historical_data`: OHLCV data with timestamps
- `trades`: Executed trade records
- `performance`: Strategy performance metrics

## 📞 Support

For issues and questions:
1. Check the code comments for detailed explanations
2. Review the example outputs in each module
3. Start with paper trading to understand the system

## 🎯 Roadmap

- [ ] Web dashboard for monitoring
- [ ] More advanced strategies
- [ ] Options trading support
- [ ] Multi-asset portfolio optimization
- [ ] Machine learning integration

---

**Happy Trading! 📈**