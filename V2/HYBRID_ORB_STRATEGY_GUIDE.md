# Hybrid ORB/VWAP Strategy Guide

## Overview

The **HybridORBStrategy** is a comprehensive intraday trading strategy that combines Opening Range Breakout (ORB) and VWAP momentum principles with sophisticated position management.

### Strategy Modes

1. **PRIMARY**: ORB/VWAP Momentum (Longs Only) ✅ **IMPLEMENTED**
2. **BACKUP**: VWAP Mean Reversion (Future Addition) ⏳ **PLANNED**

---

## Primary Mode: ORB/VWAP Momentum

### Entry Logic

A **LONG** signal is generated when ALL of the following conditions are met:

1. ✅ **Time**: After 9:30 AM (post-ORB period) and before 3:20 PM
2. ✅ **Price Action**: 5-min close breaks above Opening Range High (ORH)
3. ✅ **VWAP**: Stock price is above VWAP
4. ✅ **Volume**: Relative Volume (RVOL) > 1.5
5. ✅ **Distance Check**: Price not more than 1.5x ATR above VWAP (avoid chasing)
6. ✅ **Market Filter**: NIFTY above its 20-EMA OR above its VWAP

### Stop Loss Calculation

```
Stop Loss = max(ORH - 0.6 × ATR, VWAP - 1.0 × ATR)
```

The stop is set to the **higher** of the two values to provide optimal protection.

**Example:**
- Current Price: ₹1000
- ORH: ₹995
- VWAP: ₹990
- ATR: ₹10

Stop Options:
- Option 1: ORH - 0.6×ATR = 995 - 6 = ₹989
- Option 2: VWAP - 1.0×ATR = 990 - 10 = ₹980
- **Final Stop**: max(989, 980) = **₹989**

### Position Management

#### Initial Entry
- Risk per trade: Defined by entry price minus stop loss (1R)
- Position sizing: Based on your portfolio allocation rules

#### Partial Profit Taking (At +1R)
- **When**: Price reaches Entry + 1R
- **Action**: Exit 50% of position
- **Stop**: Move remaining position's stop to breakeven (entry price)

#### Trailing Stop (For Remaining 50%)
Choose one method (configured via `use_chandelier_trail`):

**Option A: Chandelier Stop** (Default)
```
Trailing Stop = Current High - 2 × ATR
```

**Option B: VWAP Standard Deviation**
```
Trailing Stop = VWAP - 1 SD
```

#### Time-Based Exit
- **ALL positions** are closed at **3:20 PM** regardless of profit/loss

---

## Configuration Parameters

### ORB Parameters
```python
'orb_minutes': 15           # Opening Range: 9:15 - 9:30 (15 mins)
'orb_start_time': '09:15'   # Market open
'entry_start_time': '09:30' # Can start trading after ORB
'time_stop': '15:20'        # Force exit by 3:20 PM
```

### Entry Filters
```python
'rvol_threshold': 1.5        # Min relative volume
'vwap_distance_atr': 1.5     # Max distance from VWAP (ATR multiples)
```

### Risk Management
```python
'atr_period': 5              # ATR calculation period (for 5-min bars)
'stop_orb_atr_mult': 0.6     # ORH - 0.6×ATR component
'stop_vwap_atr_mult': 1.0    # VWAP - 1.0×ATR component
'trail_atr_mult': 2.0        # Chandelier trailing stop multiplier
```

### Position Management
```python
'partial_exit_r': 1.0        # Take profit trigger (+1R)
'partial_exit_pct': 0.5      # Exit 50% at target
'use_chandelier_trail': True # Chandelier (True) vs VWAP-SD (False)
```

### Market Filter
```python
'use_market_filter': True    # Enable NIFTY filter
'market_index': 'NIFTY'      # Market benchmark
'ema_period': 20             # EMA period for filter
```

### Mode Control
```python
'enable_longs': True         # Enable long trades
'enable_shorts': False       # Disable shorts (start with longs only)
'enable_reversion': False    # Mean reversion backup (future)
```

---

## Signal Model Enhancement

The `Signal` dataclass now includes comprehensive exit management:

```python
@dataclass
class Signal:
    symbol: str
    signal_type: SignalType
    price: float
    timestamp: datetime
    confidence: float = 0.0
    reason: str = ""
    quantity: int = 0
    
    # NEW FIELDS for position management
    stop_loss: Optional[float] = None              # Initial stop loss
    target: Optional[float] = None                 # First target (+1R)
    trailing_stop: Optional[float] = None          # Trailing stop value
    breakeven_trigger: Optional[float] = None      # Move stop to BE at this price
    partial_exit_trigger: Optional[float] = None   # Take partial profit at this price
```

---

## Trade Flow Example

### Entry Setup
```
Time: 9:45 AM
Symbol: RELIANCE
Current Price: ₹2500
ORH: ₹2490
VWAP: ₹2480
ATR: ₹15
RVOL: 2.1
NIFTY: Above 20-EMA ✓

✓ Price > ORH (2500 > 2490)
✓ Price > VWAP (2500 > 2480)
✓ RVOL > 1.5 (2.1 > 1.5)
✓ Distance OK (20 < 1.5×15 = 22.5)
✓ Market filter passes

→ ENTRY LONG @ ₹2500
```

### Stop Loss Calculation
```
Option 1: ORH - 0.6×ATR = 2490 - 9 = ₹2481
Option 2: VWAP - 1.0×ATR = 2480 - 15 = ₹2465
Stop Loss = max(2481, 2465) = ₹2481
```

### Risk & Target
```
Risk (1R) = 2500 - 2481 = ₹19
Target (+1R) = 2500 + 19 = ₹2519
```

### Position Management

**Scenario 1: Target Hit**
```
Price reaches ₹2519
→ Exit 50% of position
→ Move stop to breakeven (₹2500) for remaining 50%
→ Trail with Chandelier: HighestHigh - 2×ATR
```

**Scenario 2: Stop Hit**
```
Price drops to ₹2481
→ Exit 100% at stop loss
→ Loss = -₹19 per share (-1R)
```

**Scenario 3: Time Stop**
```
Time reaches 3:20 PM
→ Exit 100% at market price
→ Close all positions regardless of P&L
```

---

## Data Requirements

### Required Data
1. **Stock Data** (5-minute bars):
   - Open, High, Low, Close, Volume
   - Historical data for RVOL calculation (20+ days)

2. **Market Index Data** (5-minute bars):
   - NIFTY 50: Open, High, Low, Close, Volume
   - Used for market filter

### Recommended Data Sources
- NSE official data
- Your existing database with 5-minute candles
- Ensure data includes:
  - Pre-market session data if using 9:15-9:30 ORB
  - Full trading day (9:15 AM - 3:30 PM)

---

## Backtest Integration

### Basic Setup
```python
from Algorithms import HybridORBStrategy

# Initialize strategy
strategy = HybridORBStrategy(params={
    'enable_longs': True,
    'enable_shorts': False,
    'atr_period': 5,
    'rvol_threshold': 1.5,
    # ... other params
})

# Run backtest
results = run_backtest(
    strategy=strategy,
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 12, 31),
    symbols=['RELIANCE', 'TCS', 'INFY'],
    timeframe='5minute'
)
```

### Position Management Implementation

Your trader/portfolio manager needs to handle:

1. **Partial Exits**: 
   - Monitor `signal.partial_exit_trigger`
   - Exit `partial_exit_pct` (50%) when price reaches trigger

2. **Breakeven Stops**:
   - Monitor `signal.breakeven_trigger`
   - Move stop to entry price when triggered

3. **Trailing Stops**:
   - Update trailing stop on each bar
   - Use `signal.trailing_stop` as initial value
   - Chandelier: `HighestHigh - trail_atr_mult × ATR`

4. **Time Stops**:
   - Exit all positions at 3:20 PM
   - Use market orders for guaranteed exit

---

## Performance Metrics to Track

### Win Rate & Risk/Reward
- Win rate (% profitable trades)
- Average R-multiple per trade
- Profit factor (gross profit / gross loss)

### Drawdown
- Maximum drawdown
- Average drawdown per trade
- Recovery time

### Time-based Analysis
- Best performing hours
- Time in market per day
- Overnight vs intraday returns

### Filter Effectiveness
- Win rate WITH market filter ON vs OFF
- RVOL threshold optimization
- VWAP distance impact

---

## Optimization Suggestions

### Phase 1: Validate Core Strategy
1. Run backtest with default parameters
2. Analyze win rate and R-multiples
3. Verify stop loss placement is effective
4. Confirm partial profit taking improves results

### Phase 2: Optimize Parameters
- **ORB Period**: Test 15, 30, 45 minutes
- **RVOL Threshold**: Test 1.0, 1.5, 2.0
- **ATR Multiples**: Optimize stop and trail multiples
- **Entry Window**: Test different entry start times

### Phase 3: Add Filters
- **Sector Filter**: Add sector index requirement
- **Gap Filter**: Consider overnight gap size
- **Trend Filter**: Add longer-term trend confirmation

### Phase 4: Enable Shorts (Optional)
```python
'enable_shorts': True
```
Test short side performance separately before combining.

### Phase 5: Add Mean Reversion Backup
```python
'enable_reversion': True
```
Enable VWAP reversion after validating momentum strategy.

---

## Risk Management Guidelines

### Position Sizing
```
Position Size = (Account Risk × Account Value) / (Entry Price - Stop Loss)

Example:
- Account: ₹1,00,000
- Risk per trade: 2%
- Entry: ₹2500
- Stop: ₹2481
- Risk per share: ₹19

Position Size = (0.02 × 100,000) / 19 = 105 shares
```

### Daily/Weekly Limits
- Max 5-7 trades per day
- Stop trading after 3 consecutive losses
- Max daily loss: 6% of account (3 trades × 2% risk)
- Weekly max loss: 10% of account

### Correlation Management
- Limit trades in same sector (max 2-3 at once)
- Diversify across sectors
- Monitor correlation with NIFTY

---

## Troubleshooting

### No Signals Generated
- ✓ Check if data includes NIFTY for market filter
- ✓ Verify RVOL threshold isn't too high
- ✓ Ensure timeframe is 5-minute bars
- ✓ Check if entry_start_time and time_stop are correct

### Too Many Signals
- Increase RVOL threshold (1.5 → 2.0)
- Tighten VWAP distance filter (1.5 → 1.0)
- Enable stricter market filter

### Stops Too Tight
- Increase ATR period (5 → 7)
- Adjust stop multipliers (0.6 → 0.8)
- Check if ATR calculation is correct

### Stops Too Wide
- Decrease ATR multipliers
- Use only one stop method (ORH or VWAP, not max)
- Consider using shorter ATR period

---

## Next Steps

1. ✅ **COMPLETED**: Extend Signal model with position management fields
2. ✅ **COMPLETED**: Implement HybridORBStrategy with full entry logic
3. ✅ **COMPLETED**: Add stop loss, target, and trailing stop calculations
4. ✅ **COMPLETED**: Implement market filter (NIFTY)
5. ✅ **COMPLETED**: Add time-based exit logic

### TODO (Future Enhancements):
6. ⏳ Update Portfolio/Trader classes to handle new Signal fields
7. ⏳ Implement partial exit logic in position management
8. ⏳ Add trailing stop updates on each bar
9. ⏳ Implement VWAP mean reversion backup mode
10. ⏳ Add sector filter (optional)
11. ⏳ Create position management visualization tools

---

## Support & Questions

For issues or questions:
1. Check your data has all required fields (OHLCV + timestamps)
2. Verify 5-minute timeframe is used
3. Ensure NIFTY data is included if market filter is enabled
4. Review logs for detailed error messages
5. Test with single symbol first before multiple symbols

---

**Strategy Status**: ✅ **READY FOR BACKTESTING**

The core strategy is fully implemented. Test with historical data, validate performance, and optimize parameters before live/paper trading.

