#!/usr/bin/env python3
"""
How to Run ML Hyperparameter Optimization - Quick Start Guide

This script demonstrates how to use the ML Analytics module for strategy optimization.
Run this file to see the ML optimization in action with your trading strategies.
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def quick_start_ml_optimization():
    """
    Quick start guide for running ML optimization
    
    This function shows step-by-step how to:
    1. Set up the ML optimization interface
    2. Run single strategy optimization  
    3. Compare multiple strategies
    4. Interpret the results
    """
    
    print("="*80)
    print("ML HYPERPARAMETER OPTIMIZATION - QUICK START GUIDE")
    print("="*80)
    
    # Step 1: Import the ML optimization interface
    print("\n1. Importing ML Optimization Interface...")
    try:
        from ML_analytics.optimization_runner import MLOptimizationInterface
        from ML_analytics.constants import OptimizationConfig
        print("✓ Successfully imported ML optimization modules")
    except ImportError as e:
        print(f"✗ Import error: {e}")
        print("Make sure you're running from the project root directory")
        return
    
    # Step 2: Initialize the interface
    print("\n2. Initializing ML Optimization Interface...")
    try:
        ml_optimizer = MLOptimizationInterface()
        print("✓ ML Optimization Interface initialized successfully")
        print(f"Available strategies: {ml_optimizer.available_strategies}")
        print(f"Available optimizers: {ml_optimizer.available_optimizers}")
        print(f"Available objectives: {ml_optimizer.available_objectives}")
    except Exception as e:
        print(f"✗ Initialization error: {e}")
        return
    
    # Step 3: Run a simple optimization example
    print("\n3. Running Simple Strategy Optimization...")
    print("Starting with Moving Average Crossover strategy optimization...")
    
    try:
        # Configure optimization
        result = ml_optimizer.optimize_strategy(
            strategy_name='moving_average_crossover',
            symbols=['NIFTY'],  # You can add more symbols: ['NIFTY', 'BANKNIFTY']
            start_date='2023-01-01',  # 2 years of data
            end_date='2024-12-31',
            optimizer_type='grid_search',  # Start with grid search (most reliable)
            objective_function='sharpe_ratio',  # Optimize for risk-adjusted returns
            max_evaluations=20,  # Small number for quick testing
            n_jobs=1,  # Single process for simplicity
            save_results=True
        )
        
        print("✓ Optimization completed successfully!")
        print(f"Best Sharpe Ratio: {result['best_objective_value']:.4f}")
        print(f"Best Parameters: {result['best_parameters']}")
        
    except Exception as e:
        print(f"✗ Optimization error: {e}")
        print("This might happen if historical data is not available")
        print("Try running the data collection first or check your data sources")
    
    # Step 4: Show how to compare strategies
    print("\n4. Strategy Comparison Example...")
    print("Comparing multiple strategies (if the first optimization worked)...")
    
    try:
        comparison_results = ml_optimizer.compare_strategies(
            strategies=['moving_average_crossover', 'rsi_mean_reversion'],
            symbols=['NIFTY'],
            optimizer_type='grid_search',
            objective_function='sharpe_ratio',
            max_evaluations_per_strategy=15
        )
        
        print("✓ Strategy comparison completed!")
        print("Rankings:")
        for i, (strategy, result) in enumerate(comparison_results.items(), 1):
            print(f"{i}. {strategy}: {result['best_objective_value']:.4f}")
            
    except Exception as e:
        print(f"Strategy comparison failed: {e}")
    
    # Step 5: Usage recommendations
    print("\n" + "="*80)
    print("NEXT STEPS & RECOMMENDATIONS")
    print("="*80)
    
    print("\n🎯 For Better Results:")
    print("1. Install optional dependencies for advanced optimization:")
    print("   pip install scikit-optimize  # For Bayesian optimization")
    print("   pip install deap            # For genetic algorithms")
    
    print("\n📊 Optimization Strategy:")
    print("1. Start with 'grid_search' (reliable, no extra dependencies)")
    print("2. Use 'bayesian' for better efficiency (needs scikit-optimize)")
    print("3. Try 'genetic' for complex parameter spaces (needs deap)")
    
    print("\n⚙️ Parameter Tuning:")
    print("1. Use max_evaluations=50-200 for thorough optimization")
    print("2. Increase n_jobs for parallel processing (grid search only)")
    print("3. Try different objective functions (sharpe_ratio, calmar_ratio)")
    
    print("\n📈 Data Requirements:")
    print("1. Ensure you have historical data for your symbols")
    print("2. Use at least 1-2 years of data for reliable optimization")
    print("3. Consider walk-forward optimization for robustness testing")

def advanced_optimization_example():
    """
    Advanced example showing more sophisticated optimization features
    """
    print("\n" + "="*80)
    print("ADVANCED OPTIMIZATION EXAMPLE")
    print("="*80)
    
    try:
        from ML_analytics.optimization_runner import MLOptimizationInterface
        
        ml_optimizer = MLOptimizationInterface()
        
        # Advanced configuration
        print("\n🔬 Advanced Configuration Example:")
        print("This shows how to use custom configuration...")
        
        # Custom optimization with Bayesian optimization (if available)
        print("\nTrying Bayesian Optimization (requires scikit-optimize)...")
        
        try:
            result = ml_optimizer.optimize_strategy(
                strategy_name='bollinger_band',
                symbols=['NIFTY'],
                optimizer_type='bayesian',  # More sophisticated
                objective_function='calmar_ratio',  # Different objective
                max_evaluations=50,  # More evaluations
                n_jobs=1,
                save_results=True
            )
            print("✓ Bayesian optimization successful!")
            print(f"Best Calmar Ratio: {result['best_objective_value']:.4f}")
            
        except Exception as e:
            print(f"Bayesian optimization failed: {e}")
            print("Try: pip install scikit-optimize")
        
        # Walk-forward optimization example
        print("\n📊 Walk-Forward Optimization Example:")
        print("Testing parameter stability over time...")
        
        try:
            walk_forward_result = ml_optimizer.run_walk_forward_optimization(
                strategy_name='moving_average_crossover',
                symbols=['NIFTY'],
                training_window_months=6,  # 6 months training
                reoptimization_frequency_months=2,  # Reoptimize every 2 months
                max_evaluations=30
            )
            
            print("✓ Walk-forward optimization completed!")
            summary = walk_forward_result['summary_statistics']
            print(f"Average parameter stability: {summary.get('avg_parameter_stability', 'N/A')}")
            print(f"Successful periods: {summary.get('successful_periods', 'N/A')}")
            
        except Exception as e:
            print(f"Walk-forward optimization failed: {e}")
    
    except ImportError:
        print("Could not import ML optimization modules")

def check_dependencies():
    """
    Check which optimization algorithms are available
    """
    print("\n" + "="*80)
    print("DEPENDENCY CHECK")
    print("="*80)
    
    # Check core dependencies
    print("\n📦 Core Dependencies:")
    
    try:
        import numpy
        print("✓ numpy available")
    except ImportError:
        print("✗ numpy not available (recommended: pip install numpy)")
    
    try:
        import pandas
        print("✓ pandas available")
    except ImportError:
        print("✗ pandas not available (recommended: pip install pandas)")
    
    # Check optimization libraries
    print("\n🤖 Optimization Libraries:")
    
    try:
        import skopt
        print("✓ scikit-optimize available (Bayesian optimization enabled)")
    except ImportError:
        print("✗ scikit-optimize not available")
        print("  Install with: pip install scikit-optimize")
        print("  Enables: Bayesian optimization (most efficient)")
    
    try:
        import deap
        print("✓ DEAP available (Genetic algorithms enabled)")
    except ImportError:
        print("✗ DEAP not available")
        print("  Install with: pip install deap")
        print("  Enables: Genetic algorithm optimization")
    
    # Check project structure
    print("\n📁 Project Structure:")
    
    project_files = [
        'core/backtesting.py',
        'core/data_manager.py', 
        'strategies/moving_average_crossover.py',
        'ML_analytics/optimizer.py',
        'ML_analytics/optimization_runner.py'
    ]
    
    for file_path in project_files:
        full_path = Path(__file__).parent.parent / file_path
        if full_path.exists():
            print(f"✓ {file_path}")
        else:
            print(f"✗ {file_path} (missing)")

def main():
    """
    Main function to run all examples
    """
    
    print("ML HYPERPARAMETER OPTIMIZATION GUIDE")
    print("This guide will show you how to use the ML optimization system\n")
    
    # Check dependencies first
    check_dependencies()
    
    # Run basic example
    quick_start_ml_optimization()
    
    # Run advanced example
    advanced_optimization_example()
    
    print("\n" + "="*80)
    print("OPTIMIZATION COMPLETE!")
    print("="*80)
    print("\n💡 Tips for Success:")
    print("1. Start with small max_evaluations (20-50) for testing")
    print("2. Use grid_search first, then try bayesian for better results")
    print("3. Check the saved JSON results in the optimization_results folder")
    print("4. Monitor the console output to understand what's happening")
    print("5. Experiment with different objective functions")
    
    print("\n📚 For More Information:")
    print("- Check ML_analytics/README.md for detailed documentation")
    print("- Look at the parameter_spaces.py to understand parameter ranges")
    print("- Examine objective_functions.py for different optimization targets")
    
    print("\n🚀 Ready to optimize your trading strategies!")

if __name__ == "__main__":
    main()