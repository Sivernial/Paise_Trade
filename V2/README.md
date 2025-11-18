# Paise Trade V2 - Algorithmic Trading System

A modular, clean, and efficient algorithmic trading system for Indian markets using Zerodha Kite API.

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
