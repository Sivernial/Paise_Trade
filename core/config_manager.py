"""
Configuration Management System for Algorithmic Trading Platform
Handles settings, parameters, and configuration for all trading components
"""

import json
import os
import configparser
from typing import Dict, Any, Optional, Union
from datetime import datetime
import logging
from dataclasses import asdict

# Import dataclasses from data_structures
from data_structures.config_dataclass import (
    TradingConfig, StrategyConfig, APIConfig, BacktestConfig
)

class ConfigManager:
    """
    Centralized configuration management system
    
    Features:
    - Load/save configurations from files
    - Environment variable integration
    - Configuration validation
    - Runtime configuration updates
    - Multiple configuration profiles
    """
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = config_dir
        self.config_file = os.path.join(config_dir, "trading_config.json")
        self.env_file = ".env"
        
        # Configuration instances
        self.trading = TradingConfig()
        self.strategy = StrategyConfig()
        self.api = APIConfig()
        self.backtest = BacktestConfig()
        
        # Create config directory if it doesn't exist
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
        
        # Setup logging
        self.logger = logging.getLogger('ConfigManager')
        
        # Load configurations
        self.load_configurations()
    
    def load_configurations(self):
        """Load all configurations from files and environment"""
        
        # Load from JSON file if exists
        if os.path.exists(self.config_file):
            self.load_from_json()
        
        # Load environment variables
        self.load_from_env()
        
        # Load from .env file if exists
        if os.path.exists(self.env_file):
            self.load_from_env_file()
        
        # Validate configurations
        self.validate_configurations()
    
    def load_from_json(self):
        """Load configuration from JSON file"""
        try:
            with open(self.config_file, 'r') as f:
                config_data = json.load(f)
            
            # Update configurations
            if 'trading' in config_data:
                self._update_dataclass(self.trading, config_data['trading'])
            
            if 'strategy' in config_data:
                self._update_dataclass(self.strategy, config_data['strategy'])
            
            if 'api' in config_data:
                self._update_dataclass(self.api, config_data['api'])
            
            if 'backtest' in config_data:
                self._update_dataclass(self.backtest, config_data['backtest'])
            
            self.logger.info(f"Configuration loaded from {self.config_file}")
            
        except Exception as e:
            self.logger.warning(f"Error loading JSON config: {e}")
    
    def load_from_env(self):
        """Load configuration from environment variables"""
        
        # API credentials
        self.api.api_key = os.getenv('API_KEY', self.api.api_key)
        self.api.api_secret = os.getenv('API_SECRET', self.api.api_secret)
        self.api.access_token = os.getenv('ACCESS_TOKEN', self.api.access_token)
        
        # Trading settings
        if os.getenv('INITIAL_CAPITAL'):
            self.trading.initial_capital = float(os.getenv('INITIAL_CAPITAL'))
        
        if os.getenv('PAPER_TRADING'):
            self.trading.paper_trading = os.getenv('PAPER_TRADING').lower() == 'true'
        
        # Logging
        self.api.log_level = os.getenv('LOG_LEVEL', self.api.log_level)
    
    def load_from_env_file(self):
        """Load configuration from .env file"""
        try:
            from dotenv import load_dotenv
            load_dotenv(self.env_file)
            self.load_from_env()  # Reload after loading .env
            
        except ImportError:
            self.logger.warning("python-dotenv not installed, skipping .env file")
        except Exception as e:
            self.logger.warning(f"Error loading .env file: {e}")
    
    def _update_dataclass(self, instance, data: Dict[str, Any]):
        """Update dataclass instance with dictionary data"""
        for key, value in data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
    
    def save_configurations(self):
        """Save all configurations to JSON file"""
        try:
            config_data = {
                'trading': asdict(self.trading),
                'strategy': asdict(self.strategy),
                'api': asdict(self.api),
                'backtest': asdict(self.backtest),
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            self.logger.info(f"Configuration saved to {self.config_file}")
            
        except Exception as e:
            self.logger.error(f"Error saving configuration: {e}")
    
    def validate_configurations(self):
        """Validate configuration values"""
        
        # Trading config validation
        if self.trading.initial_capital <= 0:
            raise ValueError("Initial capital must be positive")
        
        if not 0 < self.trading.max_position_size_pct <= 1:
            raise ValueError("Max position size percentage must be between 0 and 1")
        
        if not 0 < self.trading.max_daily_loss_pct <= 1:
            raise ValueError("Max daily loss percentage must be between 0 and 1")
        
        # Strategy config validation
        if self.strategy.min_signal_confidence < 0 or self.strategy.min_signal_confidence > 1:
            raise ValueError("Min signal confidence must be between 0 and 1")
        
        if self.strategy.rsi_period <= 0:
            raise ValueError("RSI period must be positive")
        
        # API config validation
        if not self.trading.paper_trading:
            if not self.api.api_key or not self.api.api_secret:
                self.logger.warning("Live trading requires API key and secret")
        
        self.logger.info("Configuration validation passed")
    
    def get_strategy_config(self, strategy_name: str) -> Dict[str, Any]:
        """Get configuration for a specific strategy"""
        
        base_config = {
            'min_confidence': self.strategy.min_signal_confidence,
            'lookback_period': self.trading.default_lookback_days
        }
        
        strategy_configs = {
            'ma_crossover': {
                'fast_period': self.strategy.ma_fast_period,
                'slow_period': self.strategy.ma_slow_period
            },
            'rsi_mean_reversion': {
                'rsi_period': self.strategy.rsi_period,
                'oversold_threshold': self.strategy.rsi_oversold,
                'overbought_threshold': self.strategy.rsi_overbought
            },
            'bollinger_bands': {
                'bb_period': self.strategy.bb_period,
                'bb_std': self.strategy.bb_std_dev
            },
            'multi_indicator': {
                'use_ma_filter': True,
                'use_rsi_filter': True,
                'use_macd_filter': True
            }
        }
        
        config = base_config.copy()
        if strategy_name in strategy_configs:
            config.update(strategy_configs[strategy_name])
        
        return config
    
    def update_strategy_config(self, strategy_name: str, updates: Dict[str, Any]):
        """Update configuration for a specific strategy"""
        
        if strategy_name == 'ma_crossover':
            if 'fast_period' in updates:
                self.strategy.ma_fast_period = updates['fast_period']
            if 'slow_period' in updates:
                self.strategy.ma_slow_period = updates['slow_period']
        
        elif strategy_name == 'rsi_mean_reversion':
            if 'rsi_period' in updates:
                self.strategy.rsi_period = updates['rsi_period']
            if 'oversold_threshold' in updates:
                self.strategy.rsi_oversold = updates['oversold_threshold']
            if 'overbought_threshold' in updates:
                self.strategy.rsi_overbought = updates['overbought_threshold']
        
        # Update general strategy settings
        if 'min_confidence' in updates:
            self.strategy.min_signal_confidence = updates['min_confidence']
        
        self.save_configurations()
    
    def create_profile(self, profile_name: str, base_profile: str = None):
        """Create a new configuration profile"""
        
        profile_file = os.path.join(self.config_dir, f"{profile_name}_config.json")
        
        if base_profile and base_profile != 'default':
            # Copy from existing profile
            base_file = os.path.join(self.config_dir, f"{base_profile}_config.json")
            if os.path.exists(base_file):
                with open(base_file, 'r') as f:
                    profile_data = json.load(f)
            else:
                profile_data = self._get_current_config_dict()
        else:
            # Use current configuration
            profile_data = self._get_current_config_dict()
        
        with open(profile_file, 'w') as f:
            json.dump(profile_data, f, indent=2)
        
        self.logger.info(f"Created profile: {profile_name}")
    
    def load_profile(self, profile_name: str):
        """Load a configuration profile"""
        
        profile_file = os.path.join(self.config_dir, f"{profile_name}_config.json")
        
        if not os.path.exists(profile_file):
            raise FileNotFoundError(f"Profile {profile_name} not found")
        
        # Save current config as backup
        self.save_configurations()
        
        # Load profile
        with open(profile_file, 'r') as f:
            config_data = json.load(f)
        
        # Update configurations
        if 'trading' in config_data:
            self._update_dataclass(self.trading, config_data['trading'])
        
        if 'strategy' in config_data:
            self._update_dataclass(self.strategy, config_data['strategy'])
        
        if 'api' in config_data:
            self._update_dataclass(self.api, config_data['api'])
        
        if 'backtest' in config_data:
            self._update_dataclass(self.backtest, config_data['backtest'])
        
        self.validate_configurations()
        self.logger.info(f"Loaded profile: {profile_name}")
    
    def list_profiles(self) -> list:
        """List all available configuration profiles"""
        
        profiles = []
        for file in os.listdir(self.config_dir):
            if file.endswith('_config.json'):
                profile_name = file.replace('_config.json', '')
                profiles.append(profile_name)
        
        return profiles
    
    def _get_current_config_dict(self) -> Dict[str, Any]:
        """Get current configuration as dictionary"""
        return {
            'trading': asdict(self.trading),
            'strategy': asdict(self.strategy),
            'api': asdict(self.api),
            'backtest': asdict(self.backtest),
            'created': datetime.now().isoformat()
        }
    
    def export_config(self, filename: str):
        """Export current configuration to a file"""
        
        config_data = self._get_current_config_dict()
        
        with open(filename, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        self.logger.info(f"Configuration exported to {filename}")
    
    def import_config(self, filename: str):
        """Import configuration from a file"""
        
        if not os.path.exists(filename):
            raise FileNotFoundError(f"Config file {filename} not found")
        
        with open(filename, 'r') as f:
            config_data = json.load(f)
        
        # Update configurations
        if 'trading' in config_data:
            self._update_dataclass(self.trading, config_data['trading'])
        
        if 'strategy' in config_data:
            self._update_dataclass(self.strategy, config_data['strategy'])
        
        if 'api' in config_data:
            self._update_dataclass(self.api, config_data['api'])
        
        if 'backtest' in config_data:
            self._update_dataclass(self.backtest, config_data['backtest'])
        
        self.validate_configurations()
        self.save_configurations()
        self.logger.info(f"Configuration imported from {filename}")
    
    def print_config_summary(self):
        """Print a summary of current configuration"""
        
        print("\n" + "="*60)
        print("⚙️ TRADING SYSTEM CONFIGURATION")
        print("="*60)
        
        print(f"💰 ACCOUNT SETTINGS")
        print(f"   Initial Capital: ₹{self.trading.initial_capital:,.2f}")
        print(f"   Paper Trading: {self.trading.paper_trading}")
        print(f"   Max Positions: {self.trading.max_positions}")
        print(f"   Max Position Size: {self.trading.max_position_size_pct:.1%}")
        
        print(f"\n🛡️ RISK MANAGEMENT")
        print(f"   Max Daily Loss: {self.trading.max_daily_loss_pct:.1%}")
        print(f"   Stop Loss: {self.trading.stop_loss_pct:.1%}")
        print(f"   Take Profit: {self.trading.take_profit_pct:.1%}")
        print(f"   Commission Rate: {self.trading.commission_rate:.3%}")
        
        print(f"\n📊 STRATEGY SETTINGS")
        print(f"   Active Strategies: {', '.join(self.strategy.active_strategies)}")
        print(f"   Min Signal Confidence: {self.strategy.min_signal_confidence:.1%}")
        print(f"   RSI Period: {self.strategy.rsi_period}")
        print(f"   MA Fast/Slow: {self.strategy.ma_fast_period}/{self.strategy.ma_slow_period}")
        
        print(f"\n🔌 API SETTINGS")
        print(f"   API Key: {'✅ Set' if self.api.api_key else '❌ Not Set'}")
        print(f"   API Secret: {'✅ Set' if self.api.api_secret else '❌ Not Set'}")
        print(f"   Access Token: {'✅ Set' if self.api.access_token else '❌ Not Set'}")
        print(f"   Log Level: {self.api.log_level}")
        
        print("="*60)

# Global configuration instance
config = ConfigManager()

def get_config() -> ConfigManager:
    """Get the global configuration instance"""
    return config

def create_default_configs():
    """Create default configuration files"""
    
    # Conservative profile
    config.create_profile('conservative')
    config.trading.max_position_size_pct = 0.05  # 5% per position
    config.trading.stop_loss_pct = 0.03          # 3% stop loss
    config.strategy.min_signal_confidence = 0.8  # High confidence required
    config.save_configurations()
    
    # Aggressive profile
    config.create_profile('aggressive')
    config.trading.max_position_size_pct = 0.2   # 20% per position
    config.trading.stop_loss_pct = 0.08          # 8% stop loss
    config.strategy.min_signal_confidence = 0.5  # Lower confidence threshold
    config.save_configurations()
    
    # Reset to default
    config.load_configurations()

if __name__ == "__main__":
    # Demo configuration management
    
    print("⚙️ Configuration Management Demo")
    
    # Print current config
    config.print_config_summary()
    
    # Create profiles
    create_default_configs()
    
    # List profiles
    profiles = config.list_profiles()
    print(f"\n📁 Available Profiles: {profiles}")
    
    # Load aggressive profile
    if 'aggressive' in profiles:
        print(f"\n🔄 Loading 'aggressive' profile...")
        config.load_profile('aggressive')
        config.print_config_summary()