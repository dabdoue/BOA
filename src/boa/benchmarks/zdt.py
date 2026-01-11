"""
ZDT Benchmark Suite

Two-objective test problems from:
Zitzler, E., Deb, K., & Thiele, L. (2000).
Comparison of multiobjective evolutionary algorithms.
"""

from typing import Optional

import numpy as np

from boa.benchmarks.base import Benchmark


class ZDT1(Benchmark):
    """
    ZDT1 benchmark.
    
    Convex Pareto front.
    """
    
    def __init__(self, n_var: int = 30):
        super().__init__(n_var, n_obj=2)
    
    def evaluate(self, X: np.ndarray) -> np.ndarray:
        n = X.shape[0]
        Y = np.zeros((n, 2))
        
        f1 = X[:, 0]
        g = 1 + 9 * np.sum(X[:, 1:], axis=1) / (self.n_var - 1)
        h = 1 - np.sqrt(f1 / g)
        
        Y[:, 0] = f1
        Y[:, 1] = g * h
        
        return Y
    
    def get_pareto_front(self, n_points: int = 1000) -> np.ndarray:
        """Pareto front: f2 = 1 - sqrt(f1)."""
        f1 = np.linspace(0, 1, n_points)
        f2 = 1 - np.sqrt(f1)
        return np.column_stack([f1, f2])


class ZDT2(Benchmark):
    """
    ZDT2 benchmark.
    
    Concave Pareto front.
    """
    
    def __init__(self, n_var: int = 30):
        super().__init__(n_var, n_obj=2)
    
    def evaluate(self, X: np.ndarray) -> np.ndarray:
        n = X.shape[0]
        Y = np.zeros((n, 2))
        
        f1 = X[:, 0]
        g = 1 + 9 * np.sum(X[:, 1:], axis=1) / (self.n_var - 1)
        h = 1 - (f1 / g) ** 2
        
        Y[:, 0] = f1
        Y[:, 1] = g * h
        
        return Y
    
    def get_pareto_front(self, n_points: int = 1000) -> np.ndarray:
        """Pareto front: f2 = 1 - f1^2."""
        f1 = np.linspace(0, 1, n_points)
        f2 = 1 - f1 ** 2
        return np.column_stack([f1, f2])


class ZDT3(Benchmark):
    """
    ZDT3 benchmark.
    
    Disconnected Pareto front.
    """
    
    def __init__(self, n_var: int = 30):
        super().__init__(n_var, n_obj=2)
    
    def evaluate(self, X: np.ndarray) -> np.ndarray:
        n = X.shape[0]
        Y = np.zeros((n, 2))
        
        f1 = X[:, 0]
        g = 1 + 9 * np.sum(X[:, 1:], axis=1) / (self.n_var - 1)
        h = 1 - np.sqrt(f1 / g) - (f1 / g) * np.sin(10 * np.pi * f1)
        
        Y[:, 0] = f1
        Y[:, 1] = g * h
        
        return Y
    
    def get_pareto_front(self, n_points: int = 1000) -> np.ndarray:
        """Disconnected Pareto front."""
        f1 = np.linspace(0, 1, n_points)
        f2 = 1 - np.sqrt(f1) - f1 * np.sin(10 * np.pi * f1)
        
        # Filter to actual Pareto front
        pf = np.column_stack([f1, f2])
        
        # Remove dominated points
        is_pareto = np.ones(n_points, dtype=bool)
        for i in range(n_points):
            for j in range(n_points):
                if i != j:
                    if np.all(pf[j] <= pf[i]) and np.any(pf[j] < pf[i]):
                        is_pareto[i] = False
                        break
        
        return pf[is_pareto]





