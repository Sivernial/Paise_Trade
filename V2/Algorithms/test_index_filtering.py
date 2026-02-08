import pandas as pd
import numpy as np
from datetime import datetime
from Algorithms.generic_3tf_strategy import Generic3TFStrategy
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_mock_data(price_trend="UP"):
    """Creates mock 3TF data with a crossover at the end"""
    dates = pd.date_range(end=datetime.now(), periods=100, freq='10min')
    if price_trend == "UP":
        close = np.linspace(90, 110, 100)
        # Force a crossover at the end: prev price below EMA, curr price above
        # EMA(20) of 90..110 will be around 105
        close[-2] = 100 # Below EMA
        close[-1] = 115 # Above EMA
    else:
        close = np.linspace(110, 90, 100)
        close[-2] = 115
        close[-1] = 100
    
    df = pd.DataFrame({
        'open': close * 0.99,
        'high': close * 1.01,
        'low': close * 0.98,
        'close': close,
        'volume': 1000
    }, index=dates)
    return df

def test_index_correlation_filter():
    # 1. Setup SBIN (Correlated to BANKNIFTY) at 9:25 AM
    test_time = datetime.now().replace(hour=9, minute=25)
    params = {
        'symbol': 'SBIN',
        'sky_ema_period': 20, 'forest_ema_period': 9, 'tree_ema_period': 9,
        'correlated_index': 'BANKNIFTY',
        'use_atr_target': True, 'atr_multiplier': 2.0,
        'use_atr_sl': True, 'atr_sl_multiplier': 1.5,
        'max_ema_dist_atr': 3.0, 'adx_min': 20, 'max_atr_allowed': 0.1
    }
    strategy = Generic3TFStrategy(params)
    
    # Create BULLISH setup for SBIN
    mock_df = create_mock_data("UP")
    data = {'SBIN': {'tree': mock_df, '30m': mock_df, '1h': mock_df}}
    
    # CASE A: Index is BULLISH -> Signal should be generated
    indices_bias = {'BANKNIFTY': 'BULLISH', 'NIFTY': 'BULLISH'}
    signals = strategy.generate_signals(data, test_time, indices_bias=indices_bias)
    print(f"Index BULLISH -> Signals Count: {len(signals)}")
    assert len(signals) > 0, "Should generate signal when index is Bullish"

    # CASE B: Index is BEARISH -> Signal should be REJECTED
    indices_bias = {'BANKNIFTY': 'BEARISH', 'NIFTY': 'BULLISH'}
    signals = strategy.generate_signals(data, test_time, indices_bias=indices_bias)
    print(f"Index BEARISH -> Signals Count: {len(signals)}")
    assert len(signals) == 0, "Should REJECT signal when correlate index is Bearish"

def test_independence_filter():
    # 1. Setup GOLDBEES (Correlated to NONE)
    test_time = datetime.now().replace(hour=9, minute=25)
    params = {
        'symbol': 'GOLDBEES',
        'sky_ema_period': 20, 'forest_ema_period': 9, 'tree_ema_period': 9,
        'correlated_index': 'NONE',
        'use_atr_target': True, 'atr_multiplier': 2.0,
        'use_atr_sl': True, 'atr_sl_multiplier': 1.5,
        'max_ema_dist_atr': 3.0, 'adx_min': 20, 'max_atr_allowed': 0.1
    }
    strategy = Generic3TFStrategy(params)
    
    # Create BULLISH setup for GOLDBEES
    mock_df = create_mock_data("UP")
    data = {'GOLDBEES': {'tree': mock_df, '30m': mock_df, '1h': mock_df}}
    
    # CASE: Index is BEARISH -> Signal should still be generated (GOLDBEES is independent)
    indices_bias = {'BANKNIFTY': 'BEARISH', 'NIFTY': 'BEARISH'}
    signals = strategy.generate_signals(data, test_time, indices_bias=indices_bias)
    print(f"Index BEARISH | Symbol GOLDBEES -> Signals Count: {len(signals)}")
    assert len(signals) > 0, "Gold should be independent of Nifty Bearishness"

if __name__ == "__main__":
    import traceback
    try:
        test_index_correlation_filter()
        print("✅ Index Correlation Filter Test Passed")
        test_independence_filter()
        print("✅ Independence Filter Test Passed")
    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()
