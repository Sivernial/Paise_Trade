# V5 Trading System

> Clean, modular architecture for single-stock momentum trading

## Architecture

```
V5/
├── common/              # Shared utilities
│   ├── models.py       # Signal, Position, enums
│   ├── quant_utils.py  # VWAP, RSI, ADX calculations
│   ├── data_stream.py  # WebSocket streaming
│   └── aggregator.py   # Tick aggregation
│
├── core/                # Trading engine
│   ├── portfolio.py    # Position & cash management
│   └── paper_trader.py # Paper trading execution
│
├── strategies/          # Stock-specific strategies
│   └── sbin/           # SBIN Sentinel
│       ├── strategy.py # Entry/exit logic
│       └── runner.py   # Live paper trader
│
└── config/              # Configuration
    └── settings.py     # Trading parameters
```

## Design Principles

1. **Modularity**: Each component has a single responsibility
2. **Stock-Specific**: Each stock gets its own strategy module
3. **Clean Imports**: Explicit paths, no circular dependencies
4. **Type Safety**: Dataclasses and enums for clarity

## Running SBIN Sentinel

```bash
cd V5/strategies/sbin
python runner.py
```

## Adding a New Stock

1. Create folder: `strategies/[SYMBOL]/`
2. Copy SBIN template as starting point
3. Customize entry/exit logic for that stock's behavior
4. Run backtest, then go live

## Key Differences from V2

- ✅ Stock-specific strategies (not generic multi-stock)
- ✅ Cleaner imports (no `sys.path` hacks in core code)
- ✅ Proper data models (Signal, Position classes)
- ✅ Separation of concerns (Portfolio ≠ PaperTrader)

## Next Steps

1. Add database layer for trade logging
2. Create backtesting module per stock
3. Add more stocks (RELIANCE, HDFCBANK)
