# Paise Trade V2 - Architecture Overview

## Design Principles

1. **Modularity**: Each component is independent and loosely coupled
2. **Simplicity**: Files are under 250 lines, clean and readable
3. **Database-First**: All data stored in SQLite for ML analytics preparation
4. **Type Safety**: Dataclasses and enums for better code quality
5. **Separation of Concerns**: Clear boundaries between modules

## Module Breakdown

### 1. Common (Shared Interfaces)

**Purpose**: Define shared data structures and enums used across the system

**Files**:

- `enums.py` (35 lines): OrderType, OrderStatus, TransactionType, etc.
- `models.py` (51 lines): Order, Position, Signal, Candle dataclasses
- `__init__.py` (13 lines): Module exports

**Key Features**:

- Immutable dataclasses for data integrity
- Enum-based constants for type safety
- No business logic, pure data structures

### 2. Database (Persistence Layer)

**Purpose**: Handle all database operations for historical data and trades

**Files**:

- `connection.py` (80 lines): Database connection and initialization
- `candle_repository.py` (60 lines): OHLCV data storage/retrieval
- `trade_repository.py` (88 lines): Trade history and analytics
- `__init__.py` (3 lines): Module exports

**Key Features**:

- Context manager for safe connections
- Prepared for ML analytics with proper schema
- Efficient indexing on frequently queried columns
- Repository pattern for clean data access

**Schema**:

```sql
historical_candles: symbol, timestamp, OHLCV, interval
trades: entry/exit times, prices, P&L, strategy, mode
orders: all order executions with status tracking
```

### 3. Technical_Indicators (Analysis Tools)

**Purpose**: Calculate technical indicators for strategies

**Files**:

- `static.py` (86 lines): Fixed algorithm indicators
- `dynamic.py` (94 lines): Configurable indicators
- `dynamicConfig.py` (44 lines): Configuration parameters
- `__init__.py` (4 lines): Module exports

**Static Indicators**:

- SMA, EMA, RSI, MACD, Bollinger Bands
- ATR, Stochastic, ADX, VWAP, OBV

**Dynamic Indicators**:

- Volatility (configurable period & annualization)
- Momentum (configurable lookback)
- Trend Strength (configurable periods)
- Volume Profile, Support/Resistance levels

**Design**: Stateless functions for easy testing and caching

### 4. Backtesting (Historical Simulation)

**Purpose**: Test strategies on historical data

**Files**:

- `data_fetcher.py` (71 lines): Fetch data from Zerodha API
- `engine.py` (173 lines): Backtest execution engine
- `__init__.py` (3 lines): Module exports

**Features**:

- Portfolio tracking with P&L calculation
- Commission and slippage modeling
- Comprehensive performance metrics
- Strategy callback architecture

**Metrics Calculated**:

- Total Return, Sharpe Ratio, Max Drawdown
- Win Rate, Profit Factor
- Trade-by-trade analysis

### 5. DataStream_Engine (Live Data & Orders)

**Purpose**: Handle real-time data streaming and order execution

**Files**:

- `stream.py` (53 lines): WebSocket data streaming
- `Actions/base_action.py` (20 lines): Base action class
- `Actions/buyInstant.py` (24 lines): Market buy
- `Actions/sellInstant.py` (24 lines): Market sell
- `Actions/buyLimit.py` (27 lines): Limit buy
- `Actions/sellLimit.py` (27 lines): Limit sell
- `Actions/cancelOrder.py` (21 lines): Cancel orders
- `__init__.py` files: Module exports

**Design Pattern**: Command pattern for order actions
**Threading**: WebSocket runs in separate thread
**Error Handling**: Comprehensive error logging and callback isolation

### 6. Algorithms (Trading Strategies)

**Purpose**: Implement trading strategies using the strategy pattern

**Files**:

- `base_strategy.py` (35 lines): Abstract base class
- `ma_crossover.py` (56 lines): Moving Average Crossover
- `rsi_strategy.py` (57 lines): RSI Mean Reversion
- `bollinger_strategy.py` (62 lines): Bollinger Bands
- `__init__.py` (5 lines): Module exports

**Extension Pattern**:

```python
class MyStrategy(BaseStrategy):
    def __init__(self, params):
        super().__init__(params)

    def generate_signals(self, data, current_date):
        # Use self.static_ind and self.dynamic_ind
        # Return list of Signal objects
        pass
```

**Built-in Utilities**:

- `is_bullish_crossover()`, `is_bearish_crossover()`
- `get_latest_value()` for safe series access

### 7. PaperTrader (Simulated Trading)

**Purpose**: Trade with fake money on live data

**Files**:

- `portfolio.py` (74 lines): Paper portfolio management
- `trader.py` (80 lines): Paper trading logic
- `__init__.py` (3 lines): Module exports

**Features**:

- Real-time data processing
- Simulated order execution
- Portfolio value tracking
- Position management without real money

### 8. LiveTrader (Real Trading)

**Purpose**: Execute real trades with real money

**Files**:

- `portfolio.py` (52 lines): Live portfolio via Kite API
- `trader.py` (77 lines): Live trading logic
- `__init__.py` (3 lines): Module exports

**Safety Features**:

- Requires explicit confirmation
- Position validation before orders
- Real-time margin checking
- Integration with Kite order management

### 9. Src (Entry Points)

**Purpose**: Runnable scripts for different modes

**Files**:

- `login.py` (68 lines): Zerodha authentication
- `backtest_runner.py` (87 lines): Run backtests
- `paperTrading_runner.py` (72 lines): Run paper trading
- `liveTrading_runner.py` (78 lines): Run live trading
- `__init__.py` (1 line): Module marker

**Usage Pattern**:

```bash
cd V2/Src
python login.py              # First time setup
python backtest_runner.py    # Test strategy
python paperTrading_runner.py # Test with live data
python liveTrading_runner.py  # Go live (careful!)
```

## Data Flow

### Backtesting Flow

```
Historical Data → Database → Strategy → Backtest Engine → Results
```

### Paper Trading Flow

```
Live Data Stream → Strategy → Paper Portfolio → Simulated Execution
```

### Live Trading Flow

```
Live Data Stream → Strategy → Live Trader → Kite API → Real Execution
```

## Configuration Management

- Environment variables via `.env` (API keys)
- `config.py` for application settings
- `dynamicConfig.py` for indicator parameters
- Strategy parameters via constructor

## Error Handling Strategy

1. **Logging**: Comprehensive logging at all levels
2. **Graceful Degradation**: Continue on non-critical errors
3. **Validation**: Input validation at boundaries
4. **Exceptions**: Specific exceptions for different error types

## Performance Optimizations

1. **Database Indexing**: Fast queries on common patterns
2. **Indicator Caching**: Avoid redundant calculations
3. **Stateless Design**: Easy to parallelize
4. **Efficient Data Structures**: Pandas for vectorized operations

## Testing Strategy

1. **Unit Tests**: Each module independently
2. **Backtesting**: Historical validation
3. **Paper Trading**: Live data validation
4. **Live Trading**: Small position validation

## Future Extensions

### ML Analytics (Planned)

```
V2/ML_Analytics/
├── feature_engineering.py
├── model_training.py
├── prediction.py
└── optimization.py
```

Database already structured to support:

- Feature extraction from historical data
- Model training on trade history
- Performance prediction
- Parameter optimization

## Code Metrics

- **Total Files**: 43 Python files
- **Max File Size**: 173 lines (engine.py)
- **Average File Size**: ~45 lines
- **Total Lines**: ~1,856 lines
- **Modules**: 9 main modules
- **Strategies**: 3 implemented (easily extensible)

## Dependencies

Minimal and well-maintained:

- `kiteconnect`: Zerodha API
- `pandas`: Data manipulation
- `numpy`: Numerical operations
- `python-dotenv`: Configuration
- `matplotlib`: Visualization (optional)

## Deployment Considerations

1. **Development**: Use paper trading mode
2. **Staging**: Run backtests on recent data
3. **Production**: Start with small positions
4. **Monitoring**: Watch logs and database

## Maintenance

- Modular design makes updates easy
- Each file is small and focused
- Clear separation allows parallel development
- Database migrations can be scripted

---

**Version**: 2.0.0
**Last Updated**: November 2025
**Status**: Production Ready
