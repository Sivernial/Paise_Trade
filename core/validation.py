"""
Input Validation Utilities for Trading System
Provides comprehensive validation for trading operations
"""

import pandas as pd
import numpy as np
from datetime import datetime, date
from typing import Union, Optional, List, Dict, Any

class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass

class TradingValidator:
    """
    Comprehensive validation utilities for trading system
    
    Provides validation for:
    - Financial data
    - Order parameters
    - Date ranges
    - Numeric values
    - DataFrames
    """
    
    @staticmethod
    def validate_positive_number(value: Union[int, float], name: str, allow_zero: bool = False) -> None:
        """Validate that a number is positive"""
        if not isinstance(value, (int, float)):
            raise ValidationError(f"{name} must be a number, got {type(value)}")
        
        if np.isnan(value) or np.isinf(value):
            raise ValidationError(f"{name} cannot be NaN or infinite")
        
        if allow_zero and value < 0:
            raise ValidationError(f"{name} must be non-negative, got {value}")
        elif not allow_zero and value <= 0:
            raise ValidationError(f"{name} must be positive, got {value}")
    
    @staticmethod
    def validate_percentage(value: float, name: str) -> None:
        """Validate percentage value (0-100)"""
        TradingValidator.validate_positive_number(value, name, allow_zero=True)
        if value > 100:
            raise ValidationError(f"{name} cannot exceed 100%, got {value}")
    
    @staticmethod
    def validate_ratio(value: float, name: str) -> None:
        """Validate ratio value (0-1)"""
        TradingValidator.validate_positive_number(value, name, allow_zero=True)
        if value > 1:
            raise ValidationError(f"{name} cannot exceed 1.0, got {value}")
    
    @staticmethod
    def validate_quantity(quantity: int) -> None:
        """Validate trading quantity"""
        if not isinstance(quantity, int):
            raise ValidationError(f"Quantity must be an integer, got {type(quantity)}")
        
        if quantity <= 0:
            raise ValidationError(f"Quantity must be positive, got {quantity}")
        
        if quantity > 1000000:  # Reasonable upper limit
            raise ValidationError(f"Quantity {quantity} seems unreasonably large")
    
    @staticmethod
    def validate_price(price: float) -> None:
        """Validate trading price"""
        TradingValidator.validate_positive_number(price, "Price")
        
        if price > 1000000:  # Reasonable upper limit
            raise ValidationError(f"Price {price} seems unreasonably high")
    
    @staticmethod
    def validate_symbol(symbol: str) -> None:
        """Validate trading symbol"""
        if not isinstance(symbol, str):
            raise ValidationError(f"Symbol must be a string, got {type(symbol)}")
        
        if not symbol or symbol.isspace():
            raise ValidationError("Symbol cannot be empty")
        
        if len(symbol) > 20:
            raise ValidationError(f"Symbol too long: {symbol}")
        
        # Basic format validation
        if not symbol.replace('-', '').replace('_', '').isalnum():
            raise ValidationError(f"Symbol contains invalid characters: {symbol}")
    
    @staticmethod
    def validate_date_range(start_date: Union[datetime, date, str], 
                          end_date: Union[datetime, date, str]) -> None:
        """Validate date range"""
        
        # Convert strings to dates if needed
        if isinstance(start_date, str):
            try:
                start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            except ValueError:
                raise ValidationError(f"Invalid start_date format: {start_date}. Use YYYY-MM-DD")
        
        if isinstance(end_date, str):
            try:
                end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            except ValueError:
                raise ValidationError(f"Invalid end_date format: {end_date}. Use YYYY-MM-DD")
        
        # Convert datetime to date if needed
        if isinstance(start_date, datetime):
            start_date = start_date.date()
        if isinstance(end_date, datetime):
            end_date = end_date.date()
        
        if start_date >= end_date:
            raise ValidationError(f"Start date {start_date} must be before end date {end_date}")
        
        # Check for reasonable bounds
        min_date = date(2000, 1, 1)
        max_date = date(2030, 12, 31)
        
        if start_date < min_date:
            raise ValidationError(f"Start date {start_date} is too early (minimum: {min_date})")
        
        if end_date > max_date:
            raise ValidationError(f"End date {end_date} is too far in future (maximum: {max_date})")
    
    @staticmethod
    def validate_dataframe(df: pd.DataFrame, required_columns: List[str] = None) -> None:
        """Validate DataFrame structure"""
        if not isinstance(df, pd.DataFrame):
            raise ValidationError(f"Expected DataFrame, got {type(df)}")
        
        if df.empty:
            raise ValidationError("DataFrame cannot be empty")
        
        if required_columns:
            missing_cols = set(required_columns) - set(df.columns)
            if missing_cols:
                raise ValidationError(f"Missing required columns: {missing_cols}")
        
        # Check for common OHLCV columns if present
        price_columns = ['open', 'high', 'low', 'close']
        present_price_cols = [col for col in price_columns if col in df.columns]
        
        for col in present_price_cols:
            if df[col].isna().any():
                raise ValidationError(f"Column '{col}' contains NaN values")
            
            if (df[col] <= 0).any():
                raise ValidationError(f"Column '{col}' contains non-positive values")
        
        # Validate OHLC relationships if all present
        if all(col in df.columns for col in price_columns):
            invalid_ohlc = (
                (df['high'] < df['low']) |
                (df['high'] < df['open']) |
                (df['high'] < df['close']) |
                (df['low'] > df['open']) |
                (df['low'] > df['close'])
            )
            
            if invalid_ohlc.any():
                raise ValidationError("Invalid OHLC relationships found in data")
    
    @staticmethod
    def validate_capital(capital: float) -> None:
        """Validate trading capital"""
        TradingValidator.validate_positive_number(capital, "Capital")
        
        if capital < 1000:  # Minimum reasonable capital
            raise ValidationError(f"Capital {capital} is too low (minimum: 1000)")
        
        if capital > 100000000:  # Maximum reasonable capital (10 crores)
            raise ValidationError(f"Capital {capital} seems unreasonably high")
    
    @staticmethod
    def validate_commission_rate(rate: float) -> None:
        """Validate commission rate"""
        TradingValidator.validate_ratio(rate, "Commission rate")
        
        if rate > 0.05:  # 5% commission seems excessive
            raise ValidationError(f"Commission rate {rate} seems too high")
    
    @staticmethod
    def validate_order_params(symbol: str, quantity: int, price: float = None) -> None:
        """Validate complete order parameters"""
        TradingValidator.validate_symbol(symbol)
        TradingValidator.validate_quantity(quantity)
        
        if price is not None and price > 0:
            TradingValidator.validate_price(price)
    
    @staticmethod
    def sanitize_symbol(symbol: str) -> str:
        """Sanitize and standardize symbol"""
        if not symbol:
            raise ValidationError("Symbol cannot be empty")
        
        # Remove whitespace and convert to uppercase
        clean_symbol = symbol.strip().upper()
        
        # Validate cleaned symbol
        TradingValidator.validate_symbol(clean_symbol)
        
        return clean_symbol