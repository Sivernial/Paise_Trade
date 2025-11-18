"""
Dataclasses for Configuration Management
Contains all data structures used in the configuration management module
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

@dataclass
class TradingConfig:
    """Main trading configuration"""
    # Account Settings
    initial_capital: float = 100000
    paper_trading: bool = True
    max_positions: int = 10
    max_position_size_pct: float = 0.1  # 10% of portfolio per position
    
    # Risk Management
    max_daily_loss_pct: float = 0.05  # 5% max daily loss
    stop_loss_pct: float = 0.05       # 5% stop loss
    take_profit_pct: float = 0.15     # 15% take profit
    trailing_stop_pct: float = 0.03   # 3% trailing stop
    
    # Order Management
    commission_rate: float = 0.001    # 0.1% commission
    slippage_rate: float = 0.0005     # 0.05% slippage
    max_orders_per_day: int = 100
    
    # Data Settings
    default_lookback_days: int = 252  # 1 year of data
    data_cache_enabled: bool = True
    real_time_data: bool = True

@dataclass
class StrategyConfig:
    """Strategy-specific configuration"""
    # Strategy Selection
    active_strategies: Optional[List[str]] = None
    strategy_weights: Optional[Dict[str, float]] = None
    
    # Technical Indicators
    rsi_period: int = 14
    rsi_oversold: float = 30
    rsi_overbought: float = 70
    
    ma_fast_period: int = 10
    ma_slow_period: int = 20
    
    bb_period: int = 20
    bb_std_dev: float = 2.0
    
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    
    # Signal Generation
    min_signal_confidence: float = 0.6
    signal_cooldown_minutes: int = 30
    
    def __post_init__(self):
        if self.active_strategies is None:
            self.active_strategies = ['ma_crossover', 'rsi_mean_reversion']
        if self.strategy_weights is None:
            self.strategy_weights = {'ma_crossover': 0.5, 'rsi_mean_reversion': 0.5}

@dataclass
class APIConfig:
    """API and connection configuration"""
    # Zerodha API
    api_key: str = ""
    api_secret: str = ""
    access_token: str = ""
    redirect_url: str = "http://127.0.0.1:8000"
    
    # Connection Settings
    timeout_seconds: int = 30
    retry_attempts: int = 3
    rate_limit_delay: float = 0.1
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "trading.log"
    log_max_size_mb: int = 10

@dataclass
class BacktestConfig:
    """Backtesting configuration"""
    start_date: str = "2023-01-01"
    end_date: str = "2023-12-31"
    benchmark_symbol: str = "NIFTY50"
    
    # Performance metrics
    risk_free_rate: float = 0.06  # 6% risk-free rate
    calculate_sharpe: bool = True
    calculate_sortino: bool = True
    calculate_calmar: bool = True
    
    # Output settings
    save_results: bool = True
    results_directory: str = "backtest_results"
    generate_plots: bool = True