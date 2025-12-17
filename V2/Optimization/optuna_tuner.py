
import sys
import os
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add parent directory (V2)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# Add Src directory (V2/Src)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Src')))

try:
    import optuna
except ImportError:
    print("❌ Optuna not found. Please install it using: pip install optuna")
    sys.exit(1)

from Backtesting import BacktestEngine
from Backtesting.config import BacktestConfig, StrategyConfig, MarketDataConfig
from Backtesting.data_fetcher import HistoricalDataFetcher
from Algorithms import PairTradingStrategy
from Common.quant_utils import KalmanFilterReg
from login import get_kite_instance

# Configure Logging (Suppress INFO for speed)
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("OptunaTuner")

class OptunaTuner:
    def __init__(self, pairs=None):
        self.kite = get_kite_instance()
        
        # Use Dynamic Scanner if pairs not provided
        if not pairs:
            logger.warning("Running Scanner for Tuning...")
            try:
                from Common.pair_scanner import scan_pairs
                scanned_df = scan_pairs(days=60)
                self.pairs = []
                if scanned_df is not None and not scanned_df.empty:
                    count = 0
                    for _, row in scanned_df.iterrows():
                        if count >= 4: break
                        self.pairs.append((row['Asset A'], row['Asset B']))
                        count += 1
            except Exception as e:
                logger.error(f"Scan failed: {e}")
                self.pairs = StrategyConfig.PAIR_TRADING['pairs']
        else:
            self.pairs = pairs

        print(f"🎯 Tuning for Pairs: {self.pairs}")
        self.data_dict = self.fetch_data()

    def fetch_data(self):
        """Fetch data ONCE to avoid API calls during training"""
        symbols = set()
        for p in self.pairs:
            symbols.add(p[0])
            symbols.add(p[1])
        
        fetcher = HistoricalDataFetcher(self.kite)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=MarketDataConfig.LOOKBACK_DAYS)
        
        print(f"Fetching data for {len(symbols)} symbols from {start_date.date()} to {end_date.date()}...")
        
        # Using resample logic from runner if needed, simplifying here to direct fetch if interval matches
        # Assuming we want to tune on the actual trading interval (15min)
        # Fetcher assumes 'interval' argument.
        
        # Use fetch_and_resample which handles pagination/limits correctly
        try:
            logger.info("Using fetch_and_resample...")
            print(f"Fetching data for symbols: {list(symbols)} | Start: {start_date} | End: {end_date}")
            raw_data, data_map = fetcher.fetch_and_resample(
                list(symbols), 
                start_date, 
                end_date,
                MarketDataConfig.FETCH_INTERVAL,
                MarketDataConfig.SIGNAL_INTERVAL
            )
            print(f"Fetch completed. Loaded {len(data_map)} symbols.")
        except Exception as e:
            print(f"Fetch Error: {e}")
            import traceback
            traceback.print_exc()
            return {}
        
        print(f"Fetch completed. Loaded {len(data_map)} symbols.")
        if not data_map:
            print("❌ No data fetched! Check symbol names or connectivity.")
            # Print symbols tried
            print(f"Tried symbols: {symbols}")
        
        return data_map

    def objective(self, trial):
        # 1. Suggest Parameters
        z_score_threshold = trial.suggest_float("z_score_threshold", 1.5, 3.5, step=0.1)
        lookback_window = trial.suggest_int("lookback_window", 15, 60, step=5)
        stop_loss_z = trial.suggest_float("stop_loss_z", 3.0, 6.0, step=0.5)
        take_profit_z = trial.suggest_float("take_profit_z", 0.0, 1.0, step=0.1)
        
        # 2. Setup Strategy
        params = {
            'pairs': self.pairs,
            'z_score_threshold': z_score_threshold,
            'lookback_window': lookback_window,
            'stop_loss_z': stop_loss_z,
            'take_profit_z': take_profit_z,
            'min_confidence': 0.7 # Keep AI strict
        }
        
        strategy = PairTradingStrategy(params)
        # Re-init KF
        strategy.kf_registry = {}
        for p in self.pairs:
            strategy.kf_registry[p] = KalmanFilterReg(delta=1e-4, R=1e-3)
            
        # 3. Run Backtest
        # We need a lightweight runner. We can use BacktestEngine but bypass logging callback overhead?
        # Ideally using the real engine ensures accuracy.
        
        engine = BacktestEngine(
            enable_position_management=True,
            time_stop='15:20',
            partial_exit_pct=0.5,
            trail_atr_mult=2.0
        )
        
        # Define simple callback
        def strategy_callback(data_dict, backtest_engine, current_date):
            if hasattr(strategy, 'update_positions'):
                strategy.update_positions(backtest_engine.positions)
            if hasattr(strategy, 'update_positions'):
                strategy.update_positions(backtest_engine.positions)
            signals = strategy.generate_signals(data_dict, current_date, capital=backtest_engine.get_portfolio_value())
            
            for signal in signals:
                 # Simplified Execution Logic for Speed
                 if signal.signal_type.value == "BUY":
                     if signal.symbol not in backtest_engine.positions or backtest_engine.positions[signal.symbol].quantity <= 0:
                         engine.place_order(signal.symbol, signal.signal_type, 
                                          signal.quantity if signal.quantity>0 else 1, 
                                          signal.price, signal)
                 elif signal.signal_type.value == "SELL":
                      if signal.symbol not in backtest_engine.positions or backtest_engine.positions[signal.symbol].quantity >= 0:
                         engine.place_order(signal.symbol, signal.signal_type, 
                                          signal.quantity if signal.quantity>0 else 1, 
                                          signal.price, signal)

        # Run
        # Determine start/end from data
        if not self.data_dict: return -9999
        
        # Run
        try:
            # Let engine determine range from data to avoid TZ mismatch
            results = engine.run(self.data_dict, strategy_callback)
            sharpe = results['sharpe_ratio']
            
            # Penalize low trades to avoid "Lucky 1 trade"
            if results['total_trades'] < 10:
                sharpe -= 5.0
                
            return sharpe
        except Exception as e:
            logger.error(f"Trial failed: {e}")
            import traceback
            traceback.print_exc()
            return -9999

    def run_study(self, n_trials=20):
        print(f"🚀 Starting Optuna Study with {n_trials} trials...")
        study = optuna.create_study(direction="maximize")
        study.optimize(self.objective, n_trials=n_trials)
        
        print("\n" + "="*50)
        print("🏆 BEST PARAMETERS FOUND")
        print("="*50)
        print(f"Best Sharpe Ratio: {study.best_value:.3f}")
        print("Params:")
        for k, v in study.best_params.items():
            print(f"  {k}: {v}")
        print("="*50)
        
        # Save to file
        with open("best_params.txt", "w") as f:
            f.write(str(study.best_params))

if __name__ == "__main__":
    tuner = OptunaTuner()
    tuner.run_study(n_trials=20)
