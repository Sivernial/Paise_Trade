# Paise Trade V2: AI-Powered Pair Trading System 🚀

V2 is a sophisticated **Quant-AI Hybrid Trading System** designed for the Indian Markets (NSE).
It leverages Cointegration, Kalman Filters, and Machine Learning (Gradient Boosting) to identify and trade statistical arbitrage opportunities.

## 🌟 Key Features

### 🧠 AI Neural Engine

- **Dynamic Pair Scanner**: Automatically scans 500+ NSE pairs daily to find the most cointegrated assets (ADF Test < -3.5).
- **Machine Learning Filter**: Uses XGBoost/GradientBoosting to validate signals, reducing false positives.
- **Smart Features**: Hurst Exponent, Bollinger Width, Relative Volume (RVOL), and Z-Score Velocity.
- **Confidence Scoring**: Trades are only taken if AI Probability > 70%.

### ⚡️ Execution & Optimization

- **Kalman Filters**: Adaptive hedge ratios that adjust to market volatility in real-time.
- **Optuna Tuning**: Automated hyperparameter optimization to find the "Sweet Spot" (Lookback, Stop Loss) for each market regime.
- **Multi-Mode**: Backtesting, Paper Trading, and Live Trading (Zerodha Kite).
- **Live Dashboard**: Streamlit-based UI to monitor P&L, Signals, and Strategy State in real-time.

---

## 📂 Project Structure

```
V2/
├── AI/                 # ML Models, Feature Engineering, Training Scripts
├── Algorithms/         # Pair Trading Strategy, Kalman Filters
├── Backtesting/        # Engine, Data Fetcher, Config
├── Common/             # Shared Utilities (Scanner, Quant Utils)
├── Dashboard/          # Streamlit Real-time Monitor `app.py`
├── Database/           # SQLite Storage for Trades & Analytics
├── Optimization/       # Optuna Hyperparameter Tuner
├── Src/                # RUNNERS (Entry Points)
│   ├── backtest_runner.py    # Run Simulation
│   ├── paperTrading_runner.py# Run Paper Trading
│   └── liveTrading_runner.py # Run Live Trading
└── requirements.txt    # Dependencies
```

---

## 🚀 Quick Start

### 1. Installation

```bash
pip install -r V2/requirements.txt
```

### 2. Login (Zerodha)

```bash
cd V2/Src
python login.py
```

_(Follow the Selenium interaction or enter credentials if prompted)_

### 3. Run Optimization (Optional but Recommended)

Finds the best parameters (Lookback, Z-Score) for today's market.

### 6. Portfolio Optimization (New)

- **Markowitz Model**: Allocates capital to Maximize Sharpe Ratio.
- **Constraints**: define Min/Max weight per asset.
- **Dashboard UI**: One-click optimization of tracked assets.

```bash
cd V2
python Optimization/optuna_tuner.py
```

### 4. Start Trading

**Mode A: Backtest (Simulation)**
Simulate strategy over past 30 days.

```bash
cd V2/Src
python backtest_runner.py
```

**Mode B: Paper Trading (Real-Time Mock)**
Trade with fake money on live signals.

```bash
cd V2/Src
python paperTrading_runner.py
```

**Mode C: Live Trading (Real Money)**
Real execution via Kite API.

```bash
cd V2/Src
python liveTrading_runner.py
# Type 'YES' to confirm
```

### 5. Launch Dashboard

Monitor your trading in real-time.

```bash
cd V2
streamlit run Dashboard/app.py
```

---

## 📊 Strategy Logic

1.  **Scan**: System Identifies Pairs (e.g., `ACC` vs `AMBUJACEM`) with high cointegration.
2.  **Monitor**: Tracks the Spread (Price A - Hedge Ratio \* Price B).
3.  **Signal**:
    - If Spread Z-Score > 2.0 (Deviation).
    - AND AI Model Confidence > 0.7 (Validation).
    - AND Beta is stable.
4.  **Execute**: Buy Long Asset / Sell Short Asset (Market Neutral).
5.  **Exit**: When Spread returns to Mean (Z-Score = 0) OR Stop Loss is hit.

---

## 🔮 Future Roadmap (Profitability)

1.  **Risk Parity**: Volatility-weighted position sizing.
2.  **VWAP Execution**: Minimize slippage on large orders.
3.  **Sentiment Analysis**: Filter trades based on News API.
4.  **Portfolio Optimizer**: Rebalance capital between multiple pairs.

---

_Disclaimer: Algorithmic trading involves significant risk. Use this software at your own risk._

## Architecture

The system is organized into modular components:

```
V2/
├── Common/              # Shared interfaces, enums, and models
├── Database/            # Database connections and repositories
├── Technical_Indicators/# Static and dynamic technical indicators
├── Backtesting/        # Historical data fetching and backtest engine
├── DataStream_Engine/  # Live data streaming and order actions
│   └── Actions/        # Buy/Sell/Cancel order implementations
├── Algorithms/         # Trading strategies
├── PaperTrader/        # Paper trading implementation
├── LiveTrader/         # Live trading implementation
└── Src/                # Entry point runners
```

## Features

- **Clean Modular Architecture**: Each component is independent and under 250 lines
- **Database Storage**: All historical data and trades stored in SQLite for ML analytics
- **Multiple Trading Modes**: Backtesting, Paper Trading, and Live Trading
- **Technical Indicators**: Comprehensive static and configurable dynamic indicators
- **Strategy Framework**: Easy-to-extend base strategy class
- **Risk Management**: Built-in position sizing and risk controls

## Setup

1. **Install Dependencies**

```bash
pip install -r requirements.txt
```

2. **Configure Environment**

```bash
cp .env.example .env
# Edit .env and add your Zerodha API credentials
```

3. **Login to Zerodha**

```bash
cd Src
python login.py
```

## Usage

### Backtesting

```bash
cd Src
python backtest_runner.py
```

### Paper Trading

```bash
cd Src
python paperTrading_runner.py
```

### Live Trading

```bash
cd Src
python liveTrading_runner.py
```

## Components

### 1. Common

Shared data models and enums used across all modules.

- `enums.py`: OrderType, OrderStatus, TransactionType, SignalType, etc.
- `models.py`: Order, Position, Signal, Candle dataclasses

### 2. Database

SQLite-based storage for scalability and ML analytics preparation.

- `connection.py`: Database connection management
- `candle_repository.py`: Historical candle data storage/retrieval
- `trade_repository.py`: Trade history and analytics

### 3. Technical_Indicators

- `static.py`: Fixed algorithm indicators (SMA, EMA, RSI, MACD, Bollinger, etc.)
- `dynamic.py`: Configurable indicators (Volatility, Momentum, Support/Resistance)
- `dynamicConfig.py`: Configuration parameters for dynamic indicators

### 4. Backtesting

- `data_fetcher.py`: Fetch historical data from Zerodha API
- `engine.py`: Backtest execution engine with performance metrics

### 5. DataStream_Engine

Live data streaming and order execution.

- `stream.py`: WebSocket connection to Zerodha for live data
- `Actions/`: Order execution modules
  - `buyInstant.py`: Market buy orders
  - `sellInstant.py`: Market sell orders
  - `buyLimit.py`: Limit buy orders
  - `sellLimit.py`: Limit sell orders
  - `cancelOrder.py`: Cancel pending orders

### 6. Algorithms

Trading strategy implementations.

- `base_strategy.py`: Abstract base class for all strategies
- `ma_crossover.py`: Moving Average Crossover strategy
- `rsi_strategy.py`: RSI Overbought/Oversold strategy
- `bollinger_strategy.py`: Bollinger Bands mean reversion

### 7. PaperTrader

Simulated trading with fake money on live data.

- `portfolio.py`: Paper portfolio management
- `trader.py`: Paper trading execution logic

### 8. LiveTrader

Real money trading (use with caution!).

- `portfolio.py`: Live portfolio management via Kite API
- `trader.py`: Live trading execution logic

### 9. Src

Entry point runners for different modes.

- `login.py`: Zerodha authentication
- `backtest_runner.py`: Run backtests
- `paperTrading_runner.py`: Run paper trading
- `liveTrading_runner.py`: Run live trading (requires confirmation)

## Creating Custom Strategies

Extend the `BaseStrategy` class in `Algorithms/`:

```python
from Algorithms.base_strategy import BaseStrategy
from Common import Signal, SignalType

class MyStrategy(BaseStrategy):
    def __init__(self, params: dict = None):
        super().__init__(params)

    def generate_signals(self, data, current_date):
        signals = []

        for symbol, df in data.items():
            # Your logic here
            # Use self.static_ind.sma(), self.dynamic_ind.momentum(), etc.

            if buy_condition:
                signals.append(Signal(
                    symbol=symbol,
                    signal_type=SignalType.BUY,
                    price=current_price,
                    timestamp=current_date,
                    confidence=0.8,
                    reason="Your reason"
                ))

        return signals
```

## Database Schema

### historical_candles

- Stores OHLCV data for all symbols
- Indexed by symbol and timestamp
- Supports multiple intervals (1min, 5min, 1day, etc.)

### trades

- Complete trade records (entry and exit)
- Tracks P&L, strategy used, and mode (backtest/paper/live)
- Ready for ML analytics

### orders

- All order executions
- Status tracking and filled quantities

## Performance Metrics

Backtesting provides comprehensive metrics:

- Total Return
- Sharpe Ratio
- Maximum Drawdown
- Win Rate
- Profit Factor
- Total Trades

## Safety Features

- Paper trading mode for risk-free testing
- Position size limits
- Maximum daily loss limits
- Confirmation required for live trading
- Comprehensive logging

## Future Enhancements

- ML Analytics module (already prepared with database structure)
- More advanced strategies (Multi-timeframe, ML-based)
- Portfolio optimization
- Real-time alerts and notifications
- Web dashboard for monitoring

## License

Private Project

## Disclaimer

This software is for educational purposes. Trading involves risk. Always test strategies thoroughly in paper trading before going live.
