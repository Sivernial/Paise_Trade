"""
Technical Indicators Module

Comprehensive collection of technical analysis tools organized by category:

1. Technical Analysis (technical_analysis.py):
   - SMA, EMA (Moving Averages)
   - RSI (Relative Strength Index)
   - MACD (Moving Average Convergence Divergence)
   - Bollinger Bands and related indicators
   - Stochastic Oscillator
   - ATR (Average True Range)
   - ADX (Average Directional Index)
   - VWAP (Volume Weighted Average Price)
   - Momentum indicators

2. Pattern Recognition (pattern_recognition.py):
   - Doji candlestick pattern
   - Hammer and Hanging Man
   - Shooting Star
   - Bullish/Bearish Engulfing patterns
   - Morning Star and Evening Star
   - Additional reversal patterns

3. Trend Analysis (trend_analysis.py):
   - Trend direction identification
   - Trend strength measurement
   - Support and resistance levels
   - Dynamic support/resistance
   - Breakout detection
   - Trend lines calculation
   - ZigZag indicator

4. Market Volatility (market_volatility.py):
   - Historical volatility
   - Realized volatility
   - Value at Risk (VaR)
   - Conditional VaR
   - Maximum drawdown analysis
   - Sharpe ratio calculations
   - Sortino ratio
   - Calmar ratio
   - Volatility clustering detection

Usage:
    from technical_indicators import TechnicalIndicators, PatternRecognition
    
    ta = TechnicalIndicators()
    rsi = ta.rsi(close_prices, period=14)
    
    patterns = PatternRecognition()
    doji = patterns.doji(open_prices, high, low, close)
"""

from .technical_analysis import TechnicalIndicators
from .pattern_recognition import PatternRecognition
from .trend_analysis import TrendAnalysis
from .market_volatility import MarketVolatility

__all__ = [
    'TechnicalIndicators',
    'PatternRecognition', 
    'TrendAnalysis',
    'MarketVolatility'
]

# Indicator categories for easy reference
INDICATOR_CATEGORIES = {
    'moving_averages': ['sma', 'ema'],
    'momentum': ['rsi', 'momentum', 'stochastic'],
    'trend': ['macd', 'adx', 'trend_direction'],
    'volatility': ['bollinger_bands', 'atr', 'historical_volatility'],
    'volume': ['vwap'],
    'patterns': ['doji', 'hammer', 'engulfing_bullish', 'engulfing_bearish'],
    'support_resistance': ['support_resistance', 'breakout_detection'],
    'risk_metrics': ['sharpe_ratio', 'maximum_drawdown', 'value_at_risk']
}

def get_indicator_list(category: str = None):
    """
    Get list of available indicators
    
    Args:
        category: Optional category filter
        
    Returns:
        List of indicator names
    """
    if category and category in INDICATOR_CATEGORIES:
        return INDICATOR_CATEGORIES[category]
    elif category is None:
        # Return all indicators
        all_indicators = []
        for indicators in INDICATOR_CATEGORIES.values():
            all_indicators.extend(indicators)
        return all_indicators
    else:
        raise ValueError(f"Unknown category: {category}. Available: {list(INDICATOR_CATEGORIES.keys())}")

def get_categories():
    """Get list of available indicator categories"""
    return list(INDICATOR_CATEGORIES.keys())