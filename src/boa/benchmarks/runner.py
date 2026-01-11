"""
BOA Benchmark Runner

Runs benchmarks and collects results.
"""

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Type

import numpy as np

from boa.benchmarks.base import Benchmark, BenchmarkResult
from boa.spec.models import ProcessSpec, StrategySpec
from boa.spec.loader import load_process_spec
from boa.spec.encoder import MixedSpaceEncoder
from boa.core.executor import StrategyExecutor
from boa.core.analyzer import CampaignAnalyzer


@dataclass
class RunConfig:
    """Configuration for benchmark run."""
    
    n_initial: int = 10
    n_iterations: int = 20
    n_candidates: int = 1
    seed: Optional[int] = None


class BenchmarkRunner:
    """
    Runs optimization benchmarks.
    
    Example:
        benchmark = DTLZ2(n_var=6, n_obj=2)
        runner = BenchmarkRunner(benchmark)
        
        result = runner.run(
            strategy=StrategySpec(
                name="qlogNEHVI",
                sampler="lhs_optimized",
                model="gp_matern",
                acquisition="qlogNEHVI",
            ),
            config=RunConfig(n_initial=10, n_iterations=30),
        )
        
        print(result.summary())
    """
    
    def __init__(self, benchmark: Benchmark):
        """
        Initialize runner.
        
        Args:
            benchmark: Benchmark to run
        """
        self.benchmark = benchmark
        self._spec: Optional[ProcessSpec] = None
    
    @property
    def spec(self) -> ProcessSpec:
        """Get ProcessSpec for benchmark."""
        if self._spec is None:
            self._spec = load_process_spec(
                self.benchmark.to_spec_yaml(),
                validate=False,
            )
        return self._spec
    
    def run(
        self,
        strategy: Optional[StrategySpec] = None,
        config: Optional[RunConfig] = None,
    ) -> BenchmarkResult:
        """
        Run benchmark with strategy.
        
        Args:
            strategy: Strategy to use (default: qlogNEHVI)
            config: Run configuration
            
        Returns:
            BenchmarkResult
        """
        if strategy is None:
            strategy = StrategySpec(
                name="qlogNEHVI",
                sampler="lhs_optimized",
                model="gp_matern",
                acquisition="qlogNEHVI",
            )
        
        if config is None:
            config = RunConfig()
        
        if config.seed is not None:
            np.random.seed(config.seed)
        
        start_time = time.time()
        
        # Create executor
        executor = StrategyExecutor(self.spec, strategy)
        encoder = MixedSpaceEncoder(self.spec)
        
        # Collect observations
        X_encoded: List[np.ndarray] = []
        Y: List[np.ndarray] = []
        
        # Initial design
        initial_result = executor.execute_initial_design(config.n_initial)
        
        for candidate in initial_result.candidates_raw:
            x_array = np.array([candidate[f"x{i+1}"] for i in range(self.benchmark.n_var)])
            y_array = self.benchmark.evaluate_single(x_array)
            
            X_encoded.append(encoder.encode_single(candidate))
            Y.append(y_array)
        
        # Optimization loop
        hypervolume_history = []
        
        for iteration in range(config.n_iterations):
            X_train = np.array(X_encoded)
            Y_train = np.array(Y)
            
            # Track hypervolume
            hv = self._compute_hypervolume(Y_train)
            hypervolume_history.append(hv)
            
            # Generate candidates
            result = executor.execute_optimization(
                X_train,
                Y_train,
                n_candidates=config.n_candidates,
                ref_point=self.benchmark.ref_point,
            )
            
            # Evaluate candidates
            for candidate in result.candidates_raw:
                x_array = np.array([candidate[f"x{i+1}"] for i in range(self.benchmark.n_var)])
                y_array = self.benchmark.evaluate_single(x_array)
                
                X_encoded.append(encoder.encode_single(candidate))
                Y.append(y_array)
        
        # Final metrics
        Y_final = np.array(Y)
        final_hv = self._compute_hypervolume(Y_final)
        hypervolume_history.append(final_hv)
        
        # Best values
        best_values = {}
        for i in range(self.benchmark.n_obj):
            best_values[f"y{i+1}"] = float(Y_final[:, i].min())
        
        # Pareto front size
        pareto_mask = self._get_pareto_mask(Y_final)
        pareto_size = int(pareto_mask.sum())
        
        elapsed = time.time() - start_time
        
        return BenchmarkResult(
            benchmark_name=self.benchmark.name,
            strategy_name=strategy.name,
            n_iterations=config.n_iterations,
            n_observations=len(Y),
            best_values=best_values,
            hypervolume_history=hypervolume_history,
            final_hypervolume=final_hv,
            pareto_front_size=pareto_size,
            wall_time_seconds=elapsed,
            metadata={
                "n_initial": config.n_initial,
                "n_candidates": config.n_candidates,
                "seed": config.seed,
            },
        )
    
    def _compute_hypervolume(self, Y: np.ndarray) -> float:
        """Compute hypervolume indicator."""
        try:
            from botorch.utils.multi_objective.hypervolume import Hypervolume
            import torch
        except ImportError:
            return 0.0
        
        # Get Pareto front
        pareto_mask = self._get_pareto_mask(Y)
        if not pareto_mask.any():
            return 0.0
        
        pareto_Y = Y[pareto_mask]
        
        # Negate for maximization (all minimization)
        hv = Hypervolume(ref_point=torch.tensor(self.benchmark.ref_point))
        return float(hv.compute(torch.tensor(-pareto_Y)))
    
    def _get_pareto_mask(self, Y: np.ndarray) -> np.ndarray:
        """Compute Pareto optimal mask."""
        n = len(Y)
        is_pareto = np.ones(n, dtype=bool)
        
        for i in range(n):
            if not is_pareto[i]:
                continue
            
            for j in range(n):
                if i == j:
                    continue
                
                # Check if j dominates i (all minimization)
                if np.all(Y[j] <= Y[i]) and np.any(Y[j] < Y[i]):
                    is_pareto[i] = False
                    break
        
        return is_pareto
    
    def compare_strategies(
        self,
        strategies: List[StrategySpec],
        config: Optional[RunConfig] = None,
        n_runs: int = 1,
    ) -> List[BenchmarkResult]:
        """
        Compare multiple strategies.
        
        Args:
            strategies: List of strategies to compare
            config: Run configuration
            n_runs: Number of runs per strategy
            
        Returns:
            List of results
        """
        results = []
        
        for strategy in strategies:
            for run_idx in range(n_runs):
                run_config = config or RunConfig()
                if run_config.seed is not None:
                    run_config.seed = run_config.seed + run_idx
                
                result = self.run(strategy, run_config)
                results.append(result)
        
        return results





