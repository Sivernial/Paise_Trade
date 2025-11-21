# Intraday Trading Strategies Implementation

## Overview

Two professional intraday strategies implemented for Indian equities trading via Zerodha.

---

## Strategy A: Opening Range Breakout + VWAP Momentum

**File:** `Algorithms/orb_vwap_strategy.py`  
**Config Key:** `ORB_VWAP`

### Core Logic

Trades breakouts from the opening range (first 15 minutes) when aligned with VWAP and high relative volume.

### Entry Conditions (LONG)

- Time > 9:30 AM (after opening range)
- Price breaks above Opening Range High (ORH)
- Price > VWAP
- Relative Volume (RVOL) > 1.5x average
- Distance from VWAP < 1.5 × ATR (avoids chasing)

### Entry Conditions (SHORT)

- Same as above but inverted
- Price breaks below Opening Range Low (ORL)
- Price < VWAP

### Parameters

```python
ORB_VWAP = {
    'orb_minutes': 15,           # Opening range duration
    'rvol_threshold': 1.5,       # Min relative volume
    'vwap_distance_atr': 1.5,    # Max distance from VWAP
    'stop_atr_mult': 0.6,        # Stop loss multiplier
    'trail_atr_mult': 2.0,       # Trailing stop multiplier
    'gap_min': 0.5,              # Min gap % (future use)
    'gap_max': 3.0,              # Max gap % (future use)
    'atr_period': 14,            # ATR calculation period
    'min_confidence': 0.7
}
```

### When to Use

- Trending market days
- High volume days
- Clear directional bias in indices (NIFTY/BANKNIFTY)

---

## Strategy B: VWAP Mean Reversion After Exhaustion

**File:** `Algorithms/vwap_reversion_strategy.py`  
**Config Key:** `VWAP_REVERSION`

### Core Logic

Fades extreme moves away from VWAP when price shows exhaustion and starts reverting.

### Entry Conditions (LONG - Buying Dip)

- Time > 10:00 AM (after initial volatility)
- RVOL > 2.0 (high volume)
- Price extended > 2.0 × ATR below VWAP
- Failed second push down (lower low rejection)
- Price reclaims VWAP - 0.5 SD band

### Entry Conditions (SHORT - Fading Rally)

- Same but inverted
- Price extended > 2.0 × ATR above VWAP
- Failed second push up (higher high rejection)
- Price drops below VWAP + 0.5 SD band

### Parameters

```python
VWAP_REVERSION = {
    'min_time': '10:00',         # Avoid early volatility
    'rvol_threshold': 2.0,       # Min relative volume
    'extension_atr_mult': 2.0,   # Required extension from VWAP
    'vwap_reclaim_sd': 0.5,      # Standard deviation for bands
    'atr_period': 14,            # ATR calculation period
    'lookback_bars': 3,          # Bars to detect failed push
    'min_confidence': 0.7
}
```

### When to Use

- Choppy, range-bound days
- High intraday volatility
- No clear trend in indices
- Post news/event volatility

---

## Usage

### 1. Switch Strategy in Config

```python
# config.py
class StrategyConfig:
    DEFAULT_STRATEGY = "ORB_VWAP"  # or "VWAP_REVERSION"
```

### 2. Adjust Parameters

Edit the strategy config block in `config.py`:

```python
ORB_VWAP = {
    'orb_minutes': 20,        # Change to 20-min opening range
    'rvol_threshold': 2.0,    # Stricter volume filter
    # ... etc
}
```

### 3. Run Backtest

```bash
cd V2
source venv/bin/activate
python3 Src/backtest_runner.py
```

---

## Key Features Implemented

### VWAP Calculation

- Cumulative (Price × Volume) / Cumulative Volume
- Resets daily at market open
- Used as dynamic support/resistance

### Relative Volume (RVOL)

- Current bar volume / Average volume at same time over past 20 days
- Identifies unusual activity
- Confirms breakout/breakdown strength

### Opening Range Breakout (ORB)

- High/Low of first N minutes (default 15)
- ORH = Opening Range High
- ORL = Opening Range Low
- Clear support/resistance zones

### ATR (Average True Range)

- 14-period default
- Volatility-adjusted stops and targets
- Prevents tight stops in volatile stocks

### Failed Push Detection

- Checks last 3 bars for lower high (uptrend failure)
- Checks last 3 bars for higher low (downtrend failure)
- Signals exhaustion and potential reversal

---

## Best Practices

### Stock Selection (Already in Config)

Current universe includes liquid F&O stocks:

- RELIANCE, HDFCBANK, ICICIBANK, SBIN
- INFY, TCS, WIPRO
- ITC, TATASTEEL, etc.

### Time Settings

- **ORB Strategy**: Active 9:30 AM - 3:25 PM
- **Reversion Strategy**: Active 10:00 AM - 3:25 PM
- Flat by 3:25 PM (avoid closing volatility)

### Risk Management (in BacktestConfig)

```python
INITIAL_CAPITAL = 1000000.0   # 10 lakhs
POSITION_SIZE = 1000.0         # ₹1000 per trade
COMMISSION_RATE = 0.003        # 0.3% all-in costs
```

### Data Requirements

```python
INTERVAL = "5minute"           # 5-min bars for signals
LOOKBACK_DAYS = 30            # 1 month of data
```

---

## Combining Strategies

### Portfolio Approach

Run both strategies simultaneously:

1. ORB_VWAP catches trending moves
2. VWAP_REVERSION catches reversals
3. Diversified across market regimes

### Implementation

Modify `backtest_runner.py` to instantiate both:

```python
strategy_a = get_strategy_instance('ORB_VWAP')
strategy_b = get_strategy_instance('VWAP_REVERSION')

signals_a = strategy_a.generate_signals(data_dict, current_date)
signals_b = strategy_b.generate_signals(data_dict, current_date)
all_signals = signals_a + signals_b
```

---

## Future Enhancements (Not Yet Implemented)

### 1. Gap Filter

- Only trade ORB if gap is between 0.5% - 3.0%
- Requires overnight data

### 2. Market Regime Filter

- Check NIFTY above 20-EMA before longs
- Check sector index alignment
- Requires index data

### 3. Time-Based Exits

- Scale out at specific times
- Tighten stops near 3:15 PM

### 4. Chandelier Trailing Stop

- Dynamic trailing based on ATR
- Requires position tracking in engine

### 5. Scale-Out Logic

- Exit 50% at +1R
- Move stop to breakeven
- Requires engine modifications

---

## Validation Checklist

Before live trading:

- [ ] Backtest on 3+ months of data
- [ ] Win rate > 40% minimum
- [ ] Profit factor > 1.3
- [ ] Max drawdown acceptable
- [ ] Slippage and fees realistic
- [ ] No look-ahead bias
- [ ] Walk-forward validation
- [ ] Paper trade 2+ weeks

---

## Notes

### Limitations

- No ML/AI (pure rule-based)
- No dynamic position sizing yet
- No correlation filters
- No index alignment check
- No gap trading filters
- Static time windows (doesn't adapt to holidays)

### Strengths

- Clear, logical rules
- Volatility-adjusted (ATR)
- Volume-confirmed moves
- Multiple time frame awareness
- Production-ready code structure

---

## Support

For strategy tuning or issues:

1. Check parameters in `config.py`
2. Review signals in backtest logs
3. Adjust thresholds based on backtest results
4. Test one strategy at a time initially
