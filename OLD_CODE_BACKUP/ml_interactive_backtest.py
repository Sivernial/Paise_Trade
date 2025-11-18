#!/usr/bin/env python3
"""
ML Optimization Integration with Interactive Backtest

This script shows how to integrate ML hyperparameter optimization 
into your existing interactive backtesting workflow.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

def run_ml_enhanced_backtest():
    """
    Enhanced interactive backtest with ML optimization option
    """
    
    print("="*60)
    print("INTERACTIVE BACKTEST WITH ML OPTIMIZATION")
    print("="*60)
    
    # Import required modules
    try:
        from core.backtesting import BacktestEngine
        from core.data_manager import DataManager
        from ML_analytics.optimization_runner import MLOptimizationInterface
        print("✓ All modules imported successfully")
    except ImportError as e:
        print(f"✗ Import error: {e}")
        print("Make sure you're in the project root directory")
        return
    
    # Available strategies
    strategies = [
        'moving_average_crossover',
        'rsi_mean_reversion', 
        'bollinger_band',
        'multi_indicator',
        'adaptive_momentum_breakout'
    ]
    
    print(f"\nAvailable strategies:")
    for i, strategy in enumerate(strategies, 1):
        print(f"{i}. {strategy}")
    
    # Strategy selection
    try:
        strategy_choice = input(f"\nSelect strategy (1-{len(strategies)}): ").strip()
        strategy_idx = int(strategy_choice) - 1
        
        if strategy_idx < 0 or strategy_idx >= len(strategies):
            print("Invalid selection")
            return
            
        selected_strategy = strategies[strategy_idx]
        print(f"Selected: {selected_strategy}")
        
    except (ValueError, KeyboardInterrupt):
        print("Invalid input or cancelled")
        return
    
    # Symbol selection
    symbol = input("\nEnter symbol (default: NIFTY): ").strip() or 'NIFTY'
    
    # Ask if user wants ML optimization
    print("\nBacktest Options:")
    print("1. Manual parameter entry (traditional)")
    print("2. ML hyperparameter optimization (recommended)")
    
    try:
        mode_choice = input("Select mode (1-2): ").strip()
        
        if mode_choice == "2":
            # ML Optimization Mode
            print(f"\n🤖 Running ML optimization for {selected_strategy}...")
            
            # Initialize ML optimizer
            ml_optimizer = MLOptimizationInterface()
            
            # Optimization settings
            print("\nOptimization Settings:")
            print("1. Quick test (20 evaluations)")
            print("2. Thorough optimization (100 evaluations)")
            print("3. Custom settings")
            
            eval_choice = input("Select (1-3): ").strip()
            
            if eval_choice == "1":
                max_evals = 20
            elif eval_choice == "2":
                max_evals = 100
            elif eval_choice == "3":
                try:
                    max_evals = int(input("Enter max evaluations: "))
                except ValueError:
                    max_evals = 50
            else:
                max_evals = 50
            
            # Select optimizer
            print("\nOptimization Algorithm:")
            print("1. Grid Search (reliable, no extra dependencies)")
            print("2. Bayesian Optimization (efficient, needs scikit-optimize)")
            print("3. Genetic Algorithm (flexible, needs deap)")
            
            opt_choice = input("Select (1-3): ").strip()
            
            if opt_choice == "2":
                optimizer_type = 'bayesian'
            elif opt_choice == "3":
                optimizer_type = 'genetic'
            else:
                optimizer_type = 'grid_search'
            
            print(f"\n🚀 Starting optimization...")
            print(f"Strategy: {selected_strategy}")
            print(f"Symbol: {symbol}")
            print(f"Algorithm: {optimizer_type}")
            print(f"Max Evaluations: {max_evals}")
            print("-" * 40)
            
            try:
                # Run optimization
                result = ml_optimizer.optimize_strategy(
                    strategy_name=selected_strategy,
                    symbols=[symbol],
                    optimizer_type=optimizer_type,
                    objective_function='sharpe_ratio',
                    max_evaluations=max_evals,
                    save_results=True
                )
                
                print("\n✅ OPTIMIZATION COMPLETED!")
                print(f"Best Sharpe Ratio: {result['best_objective_value']:.4f}")
                print(f"Optimal Parameters: {result['best_parameters']}")
                
                # Ask if user wants to run backtest with optimal parameters
                run_backtest = input("\nRun backtest with optimal parameters? (y/n): ").strip().lower()
                
                if run_backtest == 'y':
                    print("\n📊 Running backtest with optimal parameters...")
                    
                    # Initialize backtest engine
                    backtest_engine = BacktestEngine()
                    data_manager = DataManager()
                    
                    # Load data
                    data = data_manager.get_historical_data(symbol)
                    if data is None or data.empty:
                        print(f"❌ No data available for {symbol}")
                        return
                    
                    # Run backtest with optimal parameters
                    backtest_results = backtest_engine.run_backtest(
                        strategy_name=selected_strategy,
                        symbol=symbol,
                        data=data,
                        strategy_params=result['best_parameters'],
                        generate_plots=True  # Generate visualization
                    )
                    
                    print("✅ Backtest completed with optimal parameters!")
                    
                    # Display results
                    if backtest_results and 'performance_metrics' in backtest_results:
                        perf = backtest_results['performance_metrics']
                        print(f"\n📈 Performance Summary:")
                        print(f"Total Return: {perf.total_return:.2%}")
                        print(f"Sharpe Ratio: {perf.sharpe_ratio:.4f}")
                        print(f"Max Drawdown: {perf.max_drawdown:.2%}")
                        print(f"Win Rate: {perf.win_rate:.2%}")
                        print(f"Total Trades: {perf.total_trades}")
                
            except Exception as e:
                print(f"❌ Optimization failed: {e}")
                print("This might be due to:")
                print("- Missing historical data")
                print("- Missing optional dependencies")
                print("- Configuration issues")
                
        elif mode_choice == "1":
            # Manual Mode
            print(f"\n📝 Manual parameter entry for {selected_strategy}")
            print("You can still use the traditional interactive_backtest.py")
            print("or implement manual parameter input here")
            
            # For now, refer to existing script
            print(f"Run: python interactive_backtest.py")
            
        else:
            print("Invalid selection")
            
    except (ValueError, KeyboardInterrupt):
        print("\nOperation cancelled")

def show_optimization_results():
    """
    Show saved optimization results
    """
    print("\n" + "="*60)
    print("SAVED OPTIMIZATION RESULTS")
    print("="*60)
    
    import os
    import json
    from datetime import datetime
    
    results_dir = "ML_analytics/results"
    
    if not os.path.exists(results_dir):
        print("No optimization results found")
        print(f"Results will be saved to: {results_dir}")
        return
    
    # Find JSON result files
    result_files = []
    for root, dirs, files in os.walk(results_dir):
        for file in files:
            if file.endswith('.json'):
                result_files.append(os.path.join(root, file))
    
    if not result_files:
        print("No optimization result files found")
        return
    
    print(f"Found {len(result_files)} optimization results:")
    
    for i, file_path in enumerate(result_files, 1):
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            strategy = data.get('strategy_name', 'Unknown')
            objective = data.get('objective_function', 'Unknown')
            best_result = data.get('best_result', {})
            best_value = best_result.get('objective_value', 'N/A')
            
            file_name = os.path.basename(file_path)
            print(f"{i}. {file_name}")
            print(f"   Strategy: {strategy}")
            print(f"   Objective: {objective}")
            print(f"   Best Value: {best_value}")
            print()
            
        except Exception as e:
            print(f"{i}. {os.path.basename(file_path)} (error reading: {e})")

def main():
    """
    Main menu for ML-enhanced backtesting
    """
    
    while True:
        print("\n" + "="*60)
        print("ML-ENHANCED BACKTESTING SYSTEM")
        print("="*60)
        print("1. Run ML-optimized backtest")
        print("2. View saved optimization results")
        print("3. Quick dependency check")
        print("4. Exit")
        
        try:
            choice = input("\nSelect option (1-4): ").strip()
            
            if choice == "1":
                run_ml_enhanced_backtest()
            elif choice == "2":
                show_optimization_results()
            elif choice == "3":
                # Quick dependency check
                print("\n🔍 Checking dependencies...")
                try:
                    import numpy
                    print("✓ numpy")
                except ImportError:
                    print("✗ numpy (pip install numpy)")
                
                try:
                    import pandas
                    print("✓ pandas") 
                except ImportError:
                    print("✗ pandas (pip install pandas)")
                
                try:
                    import skopt
                    print("✓ scikit-optimize (Bayesian optimization)")
                except ImportError:
                    print("✗ scikit-optimize (pip install scikit-optimize)")
                
                try:
                    import deap
                    print("✓ deap (Genetic algorithms)")
                except ImportError:
                    print("✗ deap (pip install deap)")
                    
            elif choice == "4":
                print("Goodbye!")
                break
            else:
                print("Invalid selection")
                
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()