"""
Ornstein-Uhlenbeck Process utilities for mean-reverting spread modeling.
Used for dynamic threshold calculation in pair trading.
"""
import numpy as np
from scipy.optimize import minimize
import logging

logger = logging.getLogger(__name__)

class OUProcess:
    """
    Ornstein-Uhlenbeck process parameter estimator and threshold calculator.
    
    The OU process is defined as:
    dX_t = θ(μ - X_t)dt + σdW_t
    
    Where:
    - θ (theta): Mean reversion speed
    - μ (mu): Long-term mean
    - σ (sigma): Volatility
    """
    
    def __init__(self):
        self.theta = None  # Mean reversion speed
        self.mu = None     # Long-term mean
        self.sigma = None  # Volatility
        self.half_life = None  # Half-life of mean reversion
        
    def fit(self, spread_series: np.ndarray, dt: float = 1.0):
        """
        Estimate OU parameters using Maximum Likelihood Estimation.
        
        Args:
            spread_series: Array of spread values
            dt: Time delta between observations (default 1.0 for daily/bar-based)
        
        Returns:
            dict with estimated parameters
        """
        # Remove NaN values
        spread = spread_series[~np.isnan(spread_series)]
        
        if len(spread) < 10:
            logger.warning("Insufficient data for OU fitting")
            return None
            
        # Calculate first differences
        dx = np.diff(spread)
        x = spread[:-1]
        
        # Initial parameter guesses
        mu_init = np.mean(spread)
        theta_init = 0.1
        sigma_init = np.std(dx)
        
        # MLE optimization
        def negative_log_likelihood(params):
            theta, mu, sigma = params
            
            if theta <= 0 or sigma <= 0:
                return 1e10
                
            # Expected change under OU
            expected_dx = theta * (mu - x) * dt
            
            # Variance of change
            variance = sigma**2 * dt
            
            # Log-likelihood (Gaussian)
            ll = -0.5 * np.sum(np.log(2 * np.pi * variance) + (dx - expected_dx)**2 / variance)
            
            return -ll
        
        # Optimize
        try:
            result = minimize(
                negative_log_likelihood,
                x0=[theta_init, mu_init, sigma_init],
                method='L-BFGS-B',
                bounds=[(0.001, 10), (None, None), (0.001, None)]
            )
            
            if result.success:
                self.theta, self.mu, self.sigma = result.x
                self.half_life = np.log(2) / self.theta if self.theta > 0 else np.inf
                self.hurst_exponent = self.calculate_hurst_exponent(spread)
                
                # Check for mean-reverting regime (H < 0.5)
                # But we'll be lenient to allow signals if theta is strong
                is_mr_regime = self.hurst_exponent < 0.5 or (self.theta > 0.05 and self.hurst_exponent < 0.55)
                
                logger.debug(f"OU Fit: θ={self.theta:.4f}, μ={self.mu:.4f}, H={self.hurst_exponent:.2f}")
                
                return {
                    'theta': self.theta,
                    'mu': self.mu,
                    'sigma': self.sigma,
                    'half_life': self.half_life,
                    'is_valid': True,
                    'hurst': self.hurst_exponent,
                    'is_mr_regime': is_mr_regime
                }
            else:
                return None
                
        except Exception as e:
            logger.error(f"OU fitting error: {e}")
            return None
    
    def get_optimal_thresholds(self, confidence_level: float = 0.90, sentiment_bias: float = 0.0):
        """
        Calculate absolute entry/exit levels with news-driven bias.
        
        Args:
            confidence_level: Probabilistic confidence (usually 0.85-0.95)
            sentiment_bias: -1.0 to 1.0 (Asset A vs B news)
        """
        if self.theta is None or self.sigma is None:
            return None
            
        eq_variance = self.sigma**2 / (2 * self.theta)
        eq_std = np.sqrt(eq_variance)
        
        # 1. News-Driven Mean Drift (Dynamic Target)
        # Shift the equilibrium mean by up to 0.75 * eq_std based on news
        mu_adj = self.mu + (sentiment_bias * 0.75 * eq_std)
        
        # 2. Probability-based Entry Width
        from scipy.stats import norm
        alpha = (1 - confidence_level) / 2
        z_entry = norm.ppf(1 - alpha)
        
        # 3. Dynamic Width based on volatility
        # We use the OU standard deviation (eq_std) for absolute levels
        width = z_entry * eq_std
        
        # Tight Exit Width
        exit_width = 0.2 * eq_std # Exit when 80% reverted
        
        return {
            'mu': self.mu,
            'mu_adj': mu_adj,
            'entry_upper': mu_adj + width,
            'entry_lower': mu_adj - width,
            'exit_upper': mu_adj + exit_width,
            'exit_lower': mu_adj - exit_width,
            'eq_std': eq_std,
            'z_entry': z_entry
        }
    
    def calculate_hurst_exponent(self, time_series: np.ndarray):
        """
        Calculate Hurst Exponent using Rescaled Range (R/S) analysis.
        H < 0.5: Mean Reverting
        H = 0.5: Random Walk
        H > 0.5: Trending
        """
        try:
            lags = range(2, 20)
            tau = [np.sqrt(np.std(np.subtract(time_series[lag:], time_series[:-lag]))) for lag in lags]
            poly = np.polyfit(np.log(lags), np.log(tau), 1)
            return poly[0] * 2.0
        except Exception as e:
            logger.error(f"Error calculating Hurst: {e}")
            return 0.5

    def calculate_z_score(self, current_spread: float, sentiment_bias: float = 0.0):
        """
        Calculate OU-based z-score with sentiment adjustment.
        """
        if self.theta is None or self.sigma is None:
            return 0.0
            
        eq_variance = self.sigma**2 / (2 * self.theta)
        eq_std = np.sqrt(eq_variance)
        
        # Adjusted mean
        mu_adj = self.mu + (sentiment_bias * 0.5 * eq_std)
        
        return (current_spread - mu_adj) / eq_std if eq_std > 0 else 0.0
