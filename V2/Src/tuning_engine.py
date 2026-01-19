import sqlite3
import pandas as pd
import json
import os
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TuningEngine:
    def __init__(self, db_path="trading_data_v2.db", config_path="strategy_config.json"):
        self.db_path = db_path
        self.config_path = config_path

    def optimize_thresholds(self, lookback_days=3):
        """
        Analyze performance data and find optimal Z-thresholds per symbol.
        Logic: Find the Z-score that maximizes (Reversion Profit - Trending Losses).
        """
        logger.info(f"Optimizing thresholds based on last {lookback_days} days...")
        
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Fetch metrics for analysis
            since_date = (datetime.now() - timedelta(days=lookback_days)).strftime('%Y-%m-%d')
            query = f"SELECT symbol, z_score, regime FROM strategy_metrics WHERE timestamp > '{since_date}'"
            df = pd.read_sql_query(query, conn)
            
            if df.empty:
                logger.warning("No data found for optimization. Using defaults.")
                return {}

            optimized_config = {}
            for symbol in df['symbol'].unique():
                s_data = df[df['symbol'] == symbol]
                
                # Simple optimization logic: 
                # We want a threshold that is high enough to be 'extreme'
                # but low enough to catch moves.
                
                # We filter for 'CALM' regimes (where our strategy trades)
                # We want the threshold to be at the edge of the noise, i.e., 
                # the 95th percentile of the Z-score distribution in this regime.
                revert_moves = s_data[s_data['regime'] == 'CALM']['z_score'].abs()
                
                if not revert_moves.empty:
                    # 95th percentile represents the 'rare' event in the Calm regime
                    suggested_z = round(revert_moves.quantile(0.95), 2)
                    # Stay within sane bounds [1.8, 3.5] to prevent over-tightening or loosening
                    suggested_z = max(1.8, min(3.5, suggested_z))
                    optimized_config[symbol] = suggested_z
                else:
                    optimized_config[symbol] = 2.5 # Default fallback
            
            # Group by Sector/Basket if needed, or just return per-symbol
            # For simplicity, we create a flat map
            self._save_config(optimized_config)
            return optimized_config

        except Exception as e:
            logger.error(f"Tuning failed: {e}")
            return {}
        finally:
            conn.close()

    def _save_config(self, config):
        """Save the optimized thresholds to a JSON file."""
        # We store them in a structure that the Strategy can easily ingest
        final_output = {
            "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "symbol_thresholds": config
        }
        
        with open(self.config_path, "w") as f:
            json.dump(final_output, f, indent=4)
        logger.info(f"Optimized configuration saved to {self.config_path}")

if __name__ == "__main__":
    tuner = TuningEngine()
    tuner.optimize_thresholds()
