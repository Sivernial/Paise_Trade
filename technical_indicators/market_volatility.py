"""
Market Volatility Analysis Module

Volatility analysis and risk metrics for trading strategies.
Includes historical volatility, VaR, drawdown analysis, and risk-adjusted returns.
"""

import pandas as pd
import numpy as np
from typing import Union, Tuple


class MarketVolatility:
    """
    Volatility analysis and risk metrics
    """
    
    @staticmethod
    def historical_volatility(data: pd.Series, period: int = 20, 
                            annualize: bool = True) -> pd.Series:
        """
        Calculate historical volatility using rolling standard deviation
        
        Args:
            data: Price series
            period: Rolling window period
            annualize: Whether to annualize the volatility
            
        Returns:
            Series of historical volatility values
        """
        returns = data.pct_change()
        volatility = returns.rolling(window=period).std()
        
        if annualize:
            volatility = volatility * np.sqrt(252)  # Assuming 252 trading days
        
        return volatility
    
    @staticmethod
    def realized_volatility(data: pd.Series, period: int = 20) -> pd.Series:
        """
        Calculate realized volatility using high-frequency returns
        
        Args:
            data: Price series
            period: Rolling window period
            
        Returns:
            Series of realized volatility values
        """
        log_returns = np.log(data / data.shift(1))
        squared_returns = log_returns ** 2
        realized_vol = np.sqrt(squared_returns.rolling(window=period).sum())
        
        return realized_vol
    
    @staticmethod
    def volatility_ratio(data: pd.Series, short_period: int = 10, 
                        long_period: int = 30) -> pd.Series:
        """
        Calculate volatility ratio (short-term vol / long-term vol)
        
        Values > 1 indicate increasing volatility
        Values < 1 indicate decreasing volatility
        """
        short_vol = MarketVolatility.historical_volatility(data, short_period, annualize=False)
        long_vol = MarketVolatility.historical_volatility(data, long_period, annualize=False)
        
        # Avoid division by zero
        long_vol = long_vol.replace(0, 0.0001)
        
        return short_vol / long_vol
    
    @staticmethod
    def value_at_risk(returns: pd.Series, confidence_level: float = 0.05, 
                     period: int = 20) -> pd.Series:
        """
        Calculate rolling Value at Risk (VaR)
        
        Args:
            returns: Return series
            confidence_level: Confidence level (0.05 = 95% confidence)
            period: Rolling window period
            
        Returns:
            Series of VaR values
        """
        var_series = returns.rolling(window=period).quantile(confidence_level)
        return var_series
    
    @staticmethod
    def conditional_var(returns: pd.Series, confidence_level: float = 0.05,
                       period: int = 20) -> pd.Series:
        """
        Calculate Conditional Value at Risk (Expected Shortfall)
        
        CVaR is the expected return beyond the VaR threshold
        """
        var_values = MarketVolatility.value_at_risk(returns, confidence_level, period)
        
        cvar_series = pd.Series(index=returns.index, dtype=float)
        
        for i in range(period, len(returns)):
            window_returns = returns.iloc[i-period:i]
            var_threshold = var_values.iloc[i]
            
            # Calculate expected return beyond VaR
            tail_returns = window_returns[window_returns <= var_threshold]
            if len(tail_returns) > 0:
                cvar_series.iloc[i] = tail_returns.mean()
            else:
                cvar_series.iloc[i] = var_threshold
        
        return cvar_series
    
    @staticmethod
    def maximum_drawdown(data: pd.Series) -> float:
        """
        Calculate maximum drawdown from peak to trough
        
        Args:
            data: Price or equity curve series
            
        Returns:
            Maximum drawdown as a decimal (negative value)
        """
        if len(data) == 0:
            return 0.0
        
        # Calculate cumulative returns
        if data.iloc[0] != 0:
            cumulative = data / data.iloc[0]  # Normalize to start at 1
        else:
            cumulative = (1 + data.pct_change()).cumprod()
        
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        
        return drawdown.min()
    
    @staticmethod
    def rolling_drawdown(data: pd.Series, window: int = 252) -> pd.Series:
        """
        Calculate rolling maximum drawdown
        
        Args:
            data: Price series
            window: Rolling window period
            
        Returns:
            Series of rolling maximum drawdown values
        """
        drawdown_series = pd.Series(index=data.index, dtype=float)
        
        for i in range(window, len(data)):
            window_data = data.iloc[i-window:i+1]
            dd = MarketVolatility.maximum_drawdown(window_data)
            drawdown_series.iloc[i] = dd
        
        return drawdown_series
    
    @staticmethod
    def sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.0, 
                    period: int = 252) -> float:
        """
        Calculate Sharpe ratio
        
        Args:
            returns: Return series
            risk_free_rate: Risk-free rate (annual)
            period: Number of periods per year (252 for daily)
            
        Returns:
            Annualized Sharpe ratio
        """
        if len(returns) == 0 or returns.std() == 0:
            return 0.0
        
        excess_returns = returns - risk_free_rate / period
        return excess_returns.mean() / excess_returns.std() * np.sqrt(period)
    
    @staticmethod
    def rolling_sharpe(returns: pd.Series, window: int = 252, 
                      risk_free_rate: float = 0.0) -> pd.Series:
        """
        Calculate rolling Sharpe ratio
        
        Args:
            returns: Return series
            window: Rolling window period
            risk_free_rate: Risk-free rate (annual)
            
        Returns:
            Series of rolling Sharpe ratios
        """
        daily_rf = risk_free_rate / 252
        excess_returns = returns - daily_rf
        
        rolling_mean = excess_returns.rolling(window=window).mean()
        rolling_std = excess_returns.rolling(window=window).std()
        
        # Avoid division by zero
        rolling_std = rolling_std.replace(0, np.nan)
        
        rolling_sharpe = rolling_mean / rolling_std * np.sqrt(252)
        
        return rolling_sharpe
    
    @staticmethod
    def sortino_ratio(returns: pd.Series, risk_free_rate: float = 0.0,
                     period: int = 252) -> float:
        """
        Calculate Sortino ratio (uses downside deviation instead of total volatility)
        
        Args:
            returns: Return series
            risk_free_rate: Risk-free rate (annual)
            period: Number of periods per year
            
        Returns:
            Annualized Sortino ratio
        """
        if len(returns) == 0:
            return 0.0
        
        daily_rf = risk_free_rate / period
        excess_returns = returns - daily_rf
        
        # Calculate downside deviation
        negative_returns = excess_returns[excess_returns < 0]
        if len(negative_returns) == 0:
            return np.inf if excess_returns.mean() > 0 else 0.0
        
        downside_deviation = negative_returns.std()
        
        if downside_deviation == 0:
            return 0.0
        
        return excess_returns.mean() / downside_deviation * np.sqrt(period)
    
    @staticmethod
    def calmar_ratio(returns: pd.Series, period: int = 252) -> float:
        """
        Calculate Calmar ratio (annual return / maximum drawdown)
        
        Args:
            returns: Return series
            period: Number of periods per year
            
        Returns:
            Calmar ratio
        """
        if len(returns) == 0:
            return 0.0
        
        annual_return = returns.mean() * period
        max_dd = abs(MarketVolatility.maximum_drawdown((1 + returns).cumprod()))
        
        if max_dd == 0:
            return np.inf if annual_return > 0 else 0.0
        
        return annual_return / max_dd
    
    @staticmethod
    def volatility_clustering(returns: pd.Series, window: int = 20) -> pd.Series:
        """
        Detect volatility clustering using rolling correlation of absolute returns
        
        Args:
            returns: Return series
            window: Rolling window period
            
        Returns:
            Series indicating volatility clustering strength
        """
        abs_returns = abs(returns)
        
        # Calculate rolling correlation of absolute returns with lagged absolute returns
        lagged_abs_returns = abs_returns.shift(1)
        
        clustering = abs_returns.rolling(window=window).corr(lagged_abs_returns)
        
        return clustering