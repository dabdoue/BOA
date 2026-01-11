"""
BOA Benchmark Base Classes
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


@dataclass
class BenchmarkResult:
    """Result of a benchmark run."""
    
    benchmark_name: str
    strategy_name: str
    n_iterations: int
    n_observations: int
    best_values: Dict[str, float]
    hypervolume_history: List[float]
    final_hypervolume: Optional[float]
    pareto_front_size: int
    wall_time_seconds: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def summary(self) -> str:
        """Return summary string."""
        return (
            f"{self.benchmark_name} with {self.strategy_name}: "
            f"HV={self.final_hypervolume:.4f}, "
            f"Pareto={self.pareto_front_size}, "
            f"time={self.wall_time_seconds:.1f}s"
        )


class Benchmark(ABC):
    """
    Abstract base class for optimization benchmarks.
    
    Benchmarks define:
    - Input space (bounds)
    - Objective function(s)
    - Reference point for hypervolume
    - True Pareto front (optional)
    """
    
    def __init__(
        self,
        n_var: int,
        n_obj: int,
        bounds: Optional[np.ndarray] = None,
        ref_point: Optional[np.ndarray] = None,
    ):
        """
        Initialize benchmark.
        
        Args:
            n_var: Number of input variables
            n_obj: Number of objectives
            bounds: Variable bounds (n_var, 2)
            ref_point: Reference point for hypervolume
        """
        self.n_var = n_var
        self.n_obj = n_obj
        
        if bounds is None:
            bounds = np.column_stack([
                np.zeros(n_var),
                np.ones(n_var),
            ])
        self.bounds = bounds
        
        if ref_point is None:
            ref_point = np.ones(n_obj) * 2.0
        self.ref_point = ref_point
    
    @property
    def name(self) -> str:
        """Benchmark name."""
        return self.__class__.__name__
    
    @abstractmethod
    def evaluate(self, X: np.ndarray) -> np.ndarray:
        """
        Evaluate objectives.
        
        Args:
            X: Input array of shape (n_points, n_var)
            
        Returns:
            Objectives array of shape (n_points, n_obj)
        """
        pass
    
    def evaluate_single(self, x: np.ndarray) -> np.ndarray:
        """Evaluate single point."""
        X = x.reshape(1, -1)
        return self.evaluate(X)[0]
    
    def to_spec_yaml(self) -> str:
        """Generate YAML spec for this benchmark."""
        inputs = []
        for i in range(self.n_var):
            inputs.append({
                "name": f"x{i+1}",
                "type": "continuous",
                "bounds": [float(self.bounds[i, 0]), float(self.bounds[i, 1])],
            })
        
        objectives = []
        for i in range(self.n_obj):
            objectives.append({
                "name": f"y{i+1}",
                "direction": "minimize",
            })
        
        import yaml
        spec = {
            "name": self.name,
            "version": 1,
            "inputs": inputs,
            "objectives": objectives,
            "strategies": {
                "default": {
                    "sampler": "lhs_optimized",
                    "model": "gp_matern",
                    "acquisition": "qlogNEHVI",
                }
            },
        }
        
        return yaml.dump(spec, default_flow_style=False)
    
    def get_pareto_front(self, n_points: int = 1000) -> Optional[np.ndarray]:
        """
        Get true Pareto front (if known).
        
        Args:
            n_points: Number of points on the front
            
        Returns:
            Pareto front array of shape (n_points, n_obj) or None
        """
        return None
    
    def sample_inputs(self, n_samples: int, seed: Optional[int] = None) -> np.ndarray:
        """Sample inputs uniformly in bounds."""
        if seed is not None:
            np.random.seed(seed)
        
        samples = np.random.uniform(
            self.bounds[:, 0],
            self.bounds[:, 1],
            size=(n_samples, self.n_var),
        )
        return samples





