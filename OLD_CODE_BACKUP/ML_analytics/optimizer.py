"""
Optimization Algorithms for Strategy Hyperparameter Tuning

Implements various optimization algorithms including Bayesian Optimization,
Genetic Algorithms, and Grid Search for finding optimal strategy parameters.
"""

from typing import Dict, Any, List, Tuple, Optional, Callable
from concurrent.futures import ProcessPoolExecutor, as_completed
import itertools
import random
import json
import pickle
from datetime import datetime
import time

# Numerical computation (optional)
try:
    import numpy as np
    import pandas as pd
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

# Try to import optimization libraries (optional dependencies)
try:
    from skopt import gp_minimize
    from skopt.space import Real, Integer, Categorical
    from skopt.utils import use_named_args
    BAYESIAN_AVAILABLE = True
except ImportError:
    BAYESIAN_AVAILABLE = False

try:
    import deap
    from deap import base, creator, tools, algorithms
    GENETIC_AVAILABLE = True
except ImportError:
    GENETIC_AVAILABLE = False

# Local imports
from .constants import OptimizationConfig, OptimizationResult, ParameterSpec
from .parameter_spaces import ParameterSpace
from .objective_functions import ObjectiveFunction

class BaseOptimizer:
    """Base class for all optimization algorithms"""
    
    def __init__(self, 
                 backtest_function: Callable,
                 strategy_name: str,
                 historical_data: Dict[str, pd.DataFrame],
                 config: OptimizationConfig):
        
        self.backtest_function = backtest_function
        self.strategy_name = strategy_name
        self.historical_data = historical_data
        self.config = config
        
        # Get parameter space and objective function
        self.parameter_space = ParameterSpace.get_strategy_space(strategy_name)
        self.objective_func = ObjectiveFunction.get_objective_function(config.objective_function)
        
        # Results tracking
        self.optimization_history: List[OptimizationResult] = []
        self.best_result: Optional[OptimizationResult] = None
        
    def evaluate_parameters(self, params: Dict[str, Any]) -> float:
        """Evaluate a set of parameters and return objective value"""
        try:
            # Validate parameters
            if not ParameterSpace.validate_parameters(self.strategy_name, params):
                return -999
            
            # Run backtest with these parameters
            backtest_results = self.backtest_function(
                strategy_name=self.strategy_name,
                parameters=params,
                historical_data=self.historical_data
            )
            
            # Calculate objective value
            objective_value = self.objective_func(backtest_results)
            
            # Store result
            result = OptimizationResult(
                parameters=params.copy(),
                objective_value=objective_value,
                metrics=self._extract_metrics(backtest_results),
                backtest_results=backtest_results
            )
            
            self.optimization_history.append(result)
            
            # Update best result
            if self.best_result is None or objective_value > self.best_result.objective_value:
                self.best_result = result
                
            return objective_value
            
        except Exception as e:
            print(f"Error evaluating parameters {params}: {e}")
            return -999
    
    def _extract_metrics(self, backtest_results: Dict[str, Any]) -> Dict[str, float]:
        """Extract key metrics from backtest results"""
        performance = backtest_results.get('performance_metrics')
        if not performance:
            return {}
            
        metrics = {}
        metric_names = [
            'total_return', 'annualized_return', 'volatility', 'sharpe_ratio',
            'max_drawdown', 'win_rate', 'profit_factor', 'total_trades',
            'calmar_ratio', 'sortino_ratio'
        ]
        
        for metric in metric_names:
            value = getattr(performance, metric, None)
            if value is not None and not np.isnan(value):
                metrics[metric] = float(value)
                
        return metrics
    
    def save_results(self, filename: Optional[str] = None):
        """Save optimization results to file"""
        if not self.config.save_results:
            return
            
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.strategy_name}_{self.config.objective_function}_{timestamp}.json"
            
        results_data = {
            'strategy_name': self.strategy_name,
            'objective_function': self.config.objective_function,
            'optimization_config': {
                'max_evaluations': self.config.max_evaluations,
                'random_state': self.config.random_state
            },
            'best_result': {
                'parameters': self.best_result.parameters,
                'objective_value': self.best_result.objective_value,
                'metrics': self.best_result.metrics
            } if self.best_result else None,
            'optimization_history': [
                {
                    'parameters': result.parameters,
                    'objective_value': result.objective_value,
                    'metrics': result.metrics
                }
                for result in self.optimization_history
            ]
        }
        
        with open(filename, 'w') as f:
            json.dump(results_data, f, indent=2, default=str)
            
        print(f"Results saved to {filename}")

class GridSearchOptimizer(BaseOptimizer):
    """Grid search optimization with parallel evaluation"""
    
    def optimize(self, grid_resolution: int = 5) -> OptimizationResult:
        """
        Perform grid search optimization
        
        Args:
            grid_resolution: Number of points per parameter dimension
        """
        print(f"Starting Grid Search optimization for {self.strategy_name}")
        print(f"Objective: {self.config.objective_function}")
        
        # Generate parameter grid
        param_grid = self._generate_grid(grid_resolution)
        total_combinations = len(param_grid)
        
        print(f"Total parameter combinations: {total_combinations}")
        
        # Limit evaluations if specified
        if total_combinations > self.config.max_evaluations:
            print(f"Limiting to {self.config.max_evaluations} random combinations")
            random.seed(self.config.random_state)
            param_grid = random.sample(param_grid, self.config.max_evaluations)
        
        # Evaluate parameter combinations
        start_time = time.time()
        
        if self.config.n_jobs == 1:
            # Sequential evaluation
            for i, params in enumerate(param_grid):
                obj_val = self.evaluate_parameters(params)
                if (i + 1) % 10 == 0:
                    elapsed = time.time() - start_time
                    print(f"Evaluated {i + 1}/{len(param_grid)} combinations. "
                          f"Best: {self.best_result.objective_value:.4f}. "
                          f"Time: {elapsed:.1f}s")
        else:
            # Parallel evaluation
            self._parallel_evaluate(param_grid)
        
        elapsed = time.time() - start_time
        print(f"Grid search completed in {elapsed:.1f}s")
        print(f"Best objective value: {self.best_result.objective_value:.4f}")
        
        self.save_results()
        return self.best_result
    
    def _generate_grid(self, resolution: int) -> List[Dict[str, Any]]:
        """Generate parameter grid for grid search"""
        param_values = {}
        
        for name, spec in self.parameter_space.items():
            if spec.param_type == 'int':
                min_val, max_val = spec.bounds
                param_values[name] = list(range(min_val, max_val + 1, 
                                              max(1, (max_val - min_val) // resolution)))
            elif spec.param_type == 'float':
                min_val, max_val = spec.bounds
                param_values[name] = list(np.linspace(min_val, max_val, resolution))
            elif spec.param_type == 'categorical':
                param_values[name] = spec.bounds
            elif spec.param_type == 'bool':
                param_values[name] = [True, False]
        
        # Generate all combinations
        keys = list(param_values.keys())
        combinations = list(itertools.product(*[param_values[key] for key in keys]))
        
        param_grid = []
        for combination in combinations:
            params = dict(zip(keys, combination))
            param_grid.append(params)
            
        return param_grid
    
    def _parallel_evaluate(self, param_grid: List[Dict[str, Any]]):
        """Evaluate parameter combinations in parallel"""
        print(f"Using {self.config.n_jobs} parallel processes")
        
        with ProcessPoolExecutor(max_workers=self.config.n_jobs) as executor:
            future_to_params = {
                executor.submit(self.evaluate_parameters, params): params 
                for params in param_grid
            }
            
            completed = 0
            for future in as_completed(future_to_params):
                try:
                    objective_value = future.result()
                    completed += 1
                    
                    if completed % 10 == 0:
                        print(f"Completed {completed}/{len(param_grid)} evaluations. "
                              f"Best: {self.best_result.objective_value:.4f}")
                              
                except Exception as e:
                    print(f"Error in parallel evaluation: {e}")

class BayesianOptimizer(BaseOptimizer):
    """Bayesian optimization using Gaussian Process"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if not BAYESIAN_AVAILABLE:
            raise ImportError("scikit-optimize is required for Bayesian optimization. "
                            "Install with: pip install scikit-optimize")
    
    def optimize(self, n_initial_points: int = 10, acq_func: str = 'EI') -> OptimizationResult:
        """
        Perform Bayesian optimization
        
        Args:
            n_initial_points: Number of random initial evaluations
            acq_func: Acquisition function ('EI', 'LCB', 'PI')
        """
        print(f"Starting Bayesian optimization for {self.strategy_name}")
        print(f"Objective: {self.config.objective_function}")
        print(f"Max evaluations: {self.config.max_evaluations}")
        
        # Convert parameter space to skopt format
        dimensions, param_names = self._create_skopt_space()
        
        # Define objective function for skopt
        @use_named_args(dimensions)
        def objective(**params):
            # Convert categorical indices back to values
            processed_params = self._process_skopt_params(params, param_names)
            return -self.evaluate_parameters(processed_params)  # Minimize negative
        
        # Run Bayesian optimization
        start_time = time.time()
        
        result = gp_minimize(
            func=objective,
            dimensions=dimensions,
            n_calls=self.config.max_evaluations,
            n_initial_points=n_initial_points,
            acq_func=acq_func,
            random_state=self.config.random_state,
            verbose=True
        )
        
        elapsed = time.time() - start_time
        print(f"Bayesian optimization completed in {elapsed:.1f}s")
        print(f"Best objective value: {self.best_result.objective_value:.4f}")
        
        self.save_results()
        return self.best_result
    
    def _create_skopt_space(self) -> Tuple[List, List[str]]:
        """Create skopt-compatible parameter space"""
        dimensions = []
        param_names = []
        
        for name, spec in self.parameter_space.items():
            param_names.append(name)
            
            if spec.param_type == 'int':
                min_val, max_val = spec.bounds
                dimensions.append(Integer(min_val, max_val, name=name))
            elif spec.param_type == 'float':
                min_val, max_val = spec.bounds
                dimensions.append(Real(min_val, max_val, name=name))
            elif spec.param_type == 'categorical':
                dimensions.append(Categorical(spec.bounds, name=name))
            elif spec.param_type == 'bool':
                dimensions.append(Categorical([True, False], name=name))
                
        return dimensions, param_names
    
    def _process_skopt_params(self, params: Dict[str, Any], param_names: List[str]) -> Dict[str, Any]:
        """Process parameters from skopt format"""
        processed = {}
        
        for name in param_names:
            value = params[name]
            spec = self.parameter_space[name]
            
            # Ensure correct type
            if spec.param_type == 'int':
                processed[name] = int(value)
            elif spec.param_type == 'float':
                processed[name] = float(value)
            else:
                processed[name] = value
                
        return processed

class GeneticOptimizer(BaseOptimizer):
    """Genetic algorithm optimization"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if not GENETIC_AVAILABLE:
            raise ImportError("DEAP is required for genetic algorithm optimization. "
                            "Install with: pip install deap")
    
    def optimize(self, 
                population_size: int = 50,
                generations: int = 20,
                crossover_prob: float = 0.7,
                mutation_prob: float = 0.2) -> OptimizationResult:
        """
        Perform genetic algorithm optimization
        
        Args:
            population_size: Size of the population
            generations: Number of generations
            crossover_prob: Crossover probability
            mutation_prob: Mutation probability
        """
        print(f"Starting Genetic Algorithm optimization for {self.strategy_name}")
        print(f"Population: {population_size}, Generations: {generations}")
        
        # Setup DEAP
        self._setup_deap()
        
        # Create initial population
        population = [self._create_individual() for _ in range(population_size)]
        
        # Evaluate initial population
        fitnesses = list(map(self._evaluate_individual, population))
        for ind, fit in zip(population, fitnesses):
            ind.fitness.values = (fit,)
        
        # Evolution loop
        for generation in range(generations):
            print(f"Generation {generation + 1}/{generations}")
            
            # Selection
            offspring = deap.tools.selTournament(population, len(population), tournsize=3)
            offspring = list(map(deap.toolbox.clone, offspring))
            
            # Crossover and mutation
            for child1, child2 in zip(offspring[::2], offspring[1::2]):
                if random.random() < crossover_prob:
                    deap.toolbox.mate(child1, child2)
                    del child1.fitness.values
                    del child2.fitness.values
            
            for mutant in offspring:
                if random.random() < mutation_prob:
                    deap.toolbox.mutate(mutant)
                    del mutant.fitness.values
            
            # Evaluate offspring
            invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
            fitnesses = map(self._evaluate_individual, invalid_ind)
            for ind, fit in zip(invalid_ind, fitnesses):
                ind.fitness.values = (fit,)
            
            # Replace population
            population[:] = offspring
            
            # Print best fitness
            best_fit = max(ind.fitness.values[0] for ind in population)
            print(f"Best fitness: {best_fit:.4f}")
        
        print(f"Genetic algorithm completed")
        print(f"Best objective value: {self.best_result.objective_value:.4f}")
        
        self.save_results()
        return self.best_result
    
    def _setup_deap(self):
        """Setup DEAP genetic algorithm components"""
        random.seed(self.config.random_state)
        
        # Create fitness class (maximize objective)
        creator.create("FitnessMax", base.Fitness, weights=(1.0,))
        creator.create("Individual", list, fitness=creator.FitnessMax)
        
        # Register genetic operators
        toolbox = base.Toolbox()
        toolbox.register("individual", self._create_individual)
        toolbox.register("population", tools.initRepeat, list, toolbox.individual)
        toolbox.register("evaluate", self._evaluate_individual)
        toolbox.register("mate", self._crossover)
        toolbox.register("mutate", self._mutate)
        toolbox.register("select", tools.selTournament, tournsize=3)
        
        self.toolbox = toolbox
    
    def _create_individual(self) -> List:
        """Create a random individual (parameter set)"""
        individual = []
        for name, spec in self.parameter_space.items():
            if spec.param_type == 'int':
                min_val, max_val = spec.bounds
                value = random.randint(min_val, max_val)
            elif spec.param_type == 'float':
                min_val, max_val = spec.bounds
                value = random.uniform(min_val, max_val)
            elif spec.param_type == 'categorical':
                value = random.choice(spec.bounds)
            elif spec.param_type == 'bool':
                value = random.choice([True, False])
            
            individual.append(value)
        
        return creator.Individual(individual)
    
    def _evaluate_individual(self, individual: List) -> float:
        """Evaluate an individual (convert to parameters and evaluate)"""
        params = self._individual_to_params(individual)
        return self.evaluate_parameters(params)
    
    def _individual_to_params(self, individual: List) -> Dict[str, Any]:
        """Convert individual list to parameter dictionary"""
        params = {}
        param_names = list(self.parameter_space.keys())
        
        for i, (name, value) in enumerate(zip(param_names, individual)):
            params[name] = value
            
        return params
    
    def _crossover(self, ind1: List, ind2: List):
        """Crossover operation"""
        for i in range(len(ind1)):
            if random.random() < 0.5:
                ind1[i], ind2[i] = ind2[i], ind1[i]
        return ind1, ind2
    
    def _mutate(self, individual: List):
        """Mutation operation"""
        param_names = list(self.parameter_space.keys())
        
        for i, name in enumerate(param_names):
            if random.random() < 0.1:  # 10% mutation rate per gene
                spec = self.parameter_space[name]
                
                if spec.param_type == 'int':
                    min_val, max_val = spec.bounds
                    individual[i] = random.randint(min_val, max_val)
                elif spec.param_type == 'float':
                    min_val, max_val = spec.bounds
                    individual[i] = random.uniform(min_val, max_val)
                elif spec.param_type == 'categorical':
                    individual[i] = random.choice(spec.bounds)
                elif spec.param_type == 'bool':
                    individual[i] = random.choice([True, False])
        
        return (individual,)

class OptimizationRunner:
    """Main class for running optimization experiments"""
    
    def __init__(self, backtest_function: Callable):
        """
        Initialize optimization runner
        
        Args:
            backtest_function: Function that runs backtests
                Should accept (strategy_name, parameters, historical_data)
                Should return backtest results dictionary
        """
        self.backtest_function = backtest_function
        self.optimizers = {
            'grid_search': GridSearchOptimizer,
            'bayesian': BayesianOptimizer,
            'genetic': GeneticOptimizer
        }
    
    def run_optimization(self,
                        strategy_name: str,
                        historical_data: Dict[str, Any],
                        config: OptimizationConfig,
                        optimizer_type: str = 'bayesian',
                        **optimizer_kwargs) -> OptimizationResult:
        """
        Run optimization for a strategy
        
        Args:
            strategy_name: Name of the strategy to optimize
            historical_data: Historical market data
            config: Optimization configuration
            optimizer_type: Type of optimizer ('grid_search', 'bayesian', 'genetic')
            **optimizer_kwargs: Additional arguments for the optimizer
        """
        if optimizer_type not in self.optimizers:
            raise ValueError(f"Unknown optimizer type: {optimizer_type}")
        
        print(f"\n{'='*60}")
        print(f"OPTIMIZATION EXPERIMENT")
        print(f"Strategy: {strategy_name}")
        print(f"Optimizer: {optimizer_type}")
        print(f"Objective: {config.objective_function}")
        print(f"{'='*60}")
        
        # Create optimizer
        optimizer_class = self.optimizers[optimizer_type]
        optimizer = optimizer_class(
            backtest_function=self.backtest_function,
            strategy_name=strategy_name,
            historical_data=historical_data,
            config=config
        )
        
        # Run optimization
        result = optimizer.optimize(**optimizer_kwargs)
        
        print(f"\n{'='*60}")
        print(f"OPTIMIZATION COMPLETED")
        print(f"Best Parameters: {result.parameters}")
        print(f"Best Objective Value: {result.objective_value:.4f}")
        print(f"Best Metrics: {result.metrics}")
        print(f"{'='*60}")
        
        return result