
import sys
import os
import pandas as pd
import numpy as np

# Add parent to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Common.portfolio_optimizer import PortfolioOptimizer

def test_optimization():
    print("Testing Portfolio Optimizer...")
    
    # Create Dummy Data
    dates = pd.date_range(start='2024-01-01', periods=100)
    data = {
        'AssetA': np.cumprod(1 + np.random.normal(0.001, 0.02, 100)), # High Return, High Vol
        'AssetB': np.cumprod(1 + np.random.normal(0.0005, 0.01, 100)), # Med Return, Med Vol
        'AssetC': np.cumprod(1 + np.random.normal(0.0002, 0.005, 100)) # Low Return, Low Vol
    }
    df = pd.DataFrame(data, index=dates)
    
    optimizer = PortfolioOptimizer(risk_free_rate=0.05)
    result = optimizer.optimize(df)
    
    if result:
        print("✅ Optimization Successful")
        print("Weights:", result['weights'])
        print("Metrics:", result['metrics'])
        
        # Verify Sum = 1
        total_weight = sum(result['weights'].values())
        if abs(total_weight - 1.0) < 0.01:
            print("✅ Weights sum to 1.0")
        else:
            print(f"❌ Weights sum to {total_weight}")
    else:
        print("❌ Optimization Failed")

if __name__ == "__main__":
    test_optimization()
