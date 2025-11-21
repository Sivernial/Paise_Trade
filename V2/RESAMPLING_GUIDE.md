# Data Resampling Guide

## Overview

The system now supports fetching high-frequency data (e.g., 1-minute) and resampling it to lower frequencies (e.g., 5-minute) for signal generation. This provides:

- **Better VWAP calculations** (more granular volume data)
- **Accurate intraday indicators** (precise ATR, RVOL)
- **Cleaner signals** (less noise on higher timeframes)
- **Realistic backtesting** (1-min execution data, 5-min signals)

---

## Configuration

### Enable/Disable Resampling

In `Backtesting/config.py`:

```python
class MarketDataConfig:
    # Traditional approach (fetch at signal interval)
    USE_RESAMPLING = False
    INTERVAL = "5minute"

    # OR

    # Resampling approach (fetch 1-min, use 5-min for signals)
    USE_RESAMPLING = True
    FETCH_INTERVAL = "1min"      # Fetch from API
    SIGNAL_INTERVAL = "5min"     # Resample to this for signals
```

---

## How It Works

### Data Flow

```
Zerodha API (1-min bars)
    ↓
Raw 1-min Data (stored in database)
    ↓
Resampling Engine
    ↓
5-min OHLCV Data (for strategy signals)
    ↓
Backtest Engine
```

### Resampling Logic

The `resample_ohlcv()` function:

- **Open**: First price in the period
- **High**: Maximum price in the period
- **Low**: Minimum price in the period
- **Close**: Last price in the period
- **Volume**: Sum of all volumes in the period

Example:

```
1-min bars (9:15, 9:16, 9:17, 9:18, 9:19)
    ↓
1 x 5-min bar (9:20)
```

---

## Usage Examples

### Basic Usage (Already Configured)

The `backtest_runner.py` automatically uses resampling if enabled:

```python
# It checks the config and handles everything
if MarketDataConfig.USE_RESAMPLING:
    raw_data, data = fetcher.fetch_and_resample(...)
else:
    data = fetcher.fetch_multiple_symbols(...)
```

### Manual Resampling

```python
from Backtesting import HistoricalDataFetcher
from Backtesting.config import MarketDataConfig

# Fetch and resample
raw_data, signal_data = fetcher.fetch_and_resample(
    symbols=['RELIANCE', 'HDFCBANK'],
    start_date=start_date,
    end_date=end_date,
    fetch_interval='1min',
    signal_interval='5min'
)

# raw_data['RELIANCE'] = 1-min bars
# signal_data['RELIANCE'] = 5-min bars
```

### Custom Resampling

```python
from Backtesting.data_fetcher import HistoricalDataFetcher

# Resample existing dataframe
df_1min = ...  # Your 1-min data
df_15min = HistoricalDataFetcher.resample_ohlcv(df_1min, '15min')
```

---

## Supported Intervals

### Fetch Intervals (from Zerodha)

- `1min` - 1-minute bars (recommended for intraday)
- `5min` - 5-minute bars
- `15min` - 15-minute bars
- `1hour` - Hourly bars
- `1day` - Daily bars

### Signal Intervals (for strategies)

- `1min` - Very noisy, use with caution
- `5min` - **Recommended for intraday strategies**
- `15min` - Good for swing intraday
- `1hour` - Position trading
- `1day` - Swing trading

---

## Best Practices

### For Intraday Strategies (ORB, VWAP Reversion)

```python
USE_RESAMPLING = True
FETCH_INTERVAL = "1min"
SIGNAL_INTERVAL = "5min"
LOOKBACK_DAYS = 30  # 1 month of 1-min data
```

**Why?**

- VWAP needs precise volume data (1-min)
- RVOL calculations are more accurate (1-min)
- 5-min signals reduce false breakouts
- ATR is smoother on 5-min

### For Swing Strategies (MA Crossover, RSI, Bollinger)

```python
USE_RESAMPLING = False
INTERVAL = "1day"
LOOKBACK_DAYS = 365  # 1 year of daily data
```

**Why?**

- Daily strategies don't need intraday precision
- Direct daily data fetch is faster
- Less data storage required

### For Multi-Timeframe Analysis

```python
# Fetch 1-min data
raw_data, data_5min = fetcher.fetch_and_resample(
    symbols, start, end, '1min', '5min'
)

# Manually resample to multiple timeframes
data_15min = {
    symbol: HistoricalDataFetcher.resample_ohlcv(df, '15min')
    for symbol, df in raw_data.items()
}

data_1hour = {
    symbol: HistoricalDataFetcher.resample_ohlcv(df, '1hour')
    for symbol, df in raw_data.items()
}

# Now you have 5-min, 15-min, and 1-hour data from same source
```

---

## Performance Considerations

### Data Volume

**1-min data for 30 days:**

- Trading session: 375 minutes/day (9:15 AM - 3:30 PM)
- 30 days ≈ 11,250 bars per symbol
- 10 symbols ≈ 112,500 bars total

**5-min data for 30 days:**

- ≈ 2,250 bars per symbol
- 10 symbols ≈ 22,500 bars total

**Recommendation:**

- For intraday: Fetch 1-min, store it, resample as needed
- For daily: Fetch daily directly
- Limit `LOOKBACK_DAYS` to 30-60 for 1-min data

### API Rate Limits

Zerodha historical data API:

- 3 requests/second
- 5000 ticks per request

**Tip:** The fetcher adds natural delays between symbols, so you're safe with reasonable symbol counts (<50).

---

## Verification

### Check Resampling Output

```python
# Run backtest with logging
python3 Src/backtest_runner.py

# Look for:
# INFO:__main__:Fetching 1min data and resampling to 5min
# INFO:Backtesting.data_fetcher:Fetched 11250 1min bars for RELIANCE, resampled to 2250 5min bars
```

### Validate OHLCV Integrity

```python
# Quick check script
df_1min = raw_data['RELIANCE']
df_5min = signal_data['RELIANCE']

# Volume should sum correctly
print(df_1min['volume'].sum())  # Should equal
print(df_5min['volume'].sum())  # Should equal

# Bar counts should match ratio
print(len(df_1min) / 5)  # Approx equals
print(len(df_5min))       # Should be close
```

---

## Common Issues

### Issue: "Fetched 0 records"

**Cause:** Zerodha API limits historical data by days

- 1-min: 60 days max
- 5-min: 100 days max
- Daily: No limit

**Fix:**

```python
FETCH_INTERVAL = "1min"
LOOKBACK_DAYS = 30  # Keep under 60
```

### Issue: "Missing bars in resampled data"

**Cause:** Market holidays, no trading data

**Expected behavior:** Resampling drops NaN bars. This is correct.

### Issue: "VWAP values different from 1-min vs 5-min"

**Cause:** VWAP should be calculated on the finest granularity available

**Fix:** Always compute VWAP from 1-min data, then use resampled bars for signals:

```python
# In strategy
vwap = self.compute_vwap(df_1min)  # Use raw data
signals = self.generate_signals(df_5min)  # Use resampled
```

---

## Advanced: Custom Resampling Rules

### Weekend Aggregation

```python
# Resample to weekly bars
df_weekly = HistoricalDataFetcher.resample_ohlcv(df_daily, '1W')
```

### Session-Based Resampling

```python
# Only resample during trading hours
df_session = df_1min.between_time('09:15', '15:30')
df_5min = HistoricalDataFetcher.resample_ohlcv(df_session, '5min')
```

---

## Current Settings

Your current config (`Backtesting/config.py`):

```python
USE_RESAMPLING = True
FETCH_INTERVAL = "1min"
SIGNAL_INTERVAL = "5min"
LOOKBACK_DAYS = 30
```

✅ **Optimal for intraday strategies (ORB_VWAP, VWAP_REVERSION)**

To test the new resampling feature:

```bash
cd V2
source venv/bin/activate
python3 Src/backtest_runner.py
```

You should see logs indicating 1-min data fetches and 5-min resampling!
