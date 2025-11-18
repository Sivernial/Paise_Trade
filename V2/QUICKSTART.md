# Quick Start Guide

## Installation

1. **Setup Environment**
```bash
cd V2
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure Credentials**
```bash
cp .env.example .env
# Edit .env with your Zerodha API Key and Secret
```

3. **Login to Zerodha**
```bash
cd Src
python login.py
```
Follow the URL, login, copy the request token, and paste it back.

## Running Your First Backtest

```bash
cd Src
python backtest_runner.py
```

This will:
- Fetch 1 year of historical data for RELIANCE, TCS, INFY, HDFCBANK
- Store data in the database
- Run a Moving Average Crossover strategy
- Display performance metrics

## Testing with Paper Trading

```bash
cd Src
python paperTrading_runner.py
```

This will:
- Start live data streaming
- Execute trades with fake money
- Show portfolio value updates every minute

## Customizing Strategies

Edit `Algorithms/ma_crossover.py` or create a new strategy:

```python
# Algorithms/my_strategy.py
from .base_strategy import BaseStrategy
from Common import Signal, SignalType

class MyStrategy(BaseStrategy):
    def generate_signals(self, data, current_date):
        signals = []
        
        for symbol, df in data.items():
            # Calculate indicators
            rsi = self.static_ind.rsi(df['close'], 14)
            sma = self.static_ind.sma(df['close'], 20)
            
            # Generate signals
            if rsi.iloc[-1] < 30:
                signals.append(Signal(
                    symbol=symbol,
                    signal_type=SignalType.BUY,
                    price=df['close'].iloc[-1],
                    timestamp=current_date,
                    confidence=0.8,
                    reason=f"RSI oversold: {rsi.iloc[-1]:.2f}"
                ))
        
        return signals
```

## File Size Check

All files are under 250 lines as requested:
```bash
find . -name "*.py" -exec wc -l {} + | sort -n
```

## Database Location

All data is stored in `trading_data_v2.db` for ML analytics preparation.

## Tips

1. **Always test in backtest mode first**
2. **Then test in paper trading mode**
3. **Only go live after thorough testing**
4. **Monitor logs carefully**
5. **Set appropriate position sizes**

## Troubleshooting

**Issue**: ImportError
**Solution**: Make sure you're in the V2 directory and Python path is set correctly

**Issue**: No data fetched
**Solution**: Check your internet connection and Kite API limits

**Issue**: Access token expired
**Solution**: Run `python login.py` again

## Next Steps

1. Explore different strategies in `Algorithms/`
2. Customize indicator parameters in `Technical_Indicators/dynamicConfig.py`
3. Review trade history in the database
4. Prepare for ML analytics integration

