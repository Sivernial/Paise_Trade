"""
Data Loading Utilities

Contains functions for loading and preprocessing historical data
for optimization experiments.
"""

from typing import Dict, Any, List


def load_historical_data_for_optimization(symbols: List[str], 
                                        data_manager) -> Dict[str, Any]:
    """
    Load historical data for optimization
    
    Args:
        symbols: List of symbols to load
        data_manager: DataManager instance
        
    Returns:
        Dictionary of historical data
    """
    historical_data = {}
    
    for symbol in symbols:
        try:
            # Load historical data using data manager
            data = data_manager.get_historical_data(symbol)
            
            if data is not None and not data.empty:
                historical_data[symbol] = data
                print(f"✅ Loaded {len(data)} rows for {symbol}")
            else:
                print(f"⚠️  Warning: No data available for {symbol}")
                
        except Exception as e:
            print(f"❌ Error loading data for {symbol}: {e}")
            continue
    
    return historical_data


def validate_historical_data(historical_data: Dict[str, Any]) -> bool:
    """
    Validate that historical data is suitable for backtesting
    
    Args:
        historical_data: Dictionary of symbol -> DataFrame
        
    Returns:
        True if data is valid, False otherwise
    """
    if not historical_data:
        print("❌ No historical data provided")
        return False
    
    for symbol, data in historical_data.items():
        if data is None or data.empty:
            print(f"❌ Empty data for {symbol}")
            return False
        
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in data.columns]
        
        if missing_columns:
            print(f"❌ Missing columns for {symbol}: {missing_columns}")
            return False
        
        if len(data) < 50:  # Need sufficient data for indicators
            print(f"❌ Insufficient data for {symbol}: {len(data)} rows (need at least 50)")
            return False
    
    print("✅ Historical data validation passed")
    return True