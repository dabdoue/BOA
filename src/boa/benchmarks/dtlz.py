"""
DTLZ Benchmark Suite

Multi-objective test problems from:
Deb, K., Thiele, L., Laumanns, M., & Zitzler, E. (2005).
Scalable test problems for evolutionary multiobjective optimization.
"""

from typing import Optional

import numpy as np

from boa.benchmarks.base import Benchmark


class DTLZ1(Benchmark):
    """
    DTLZ1 benchmark.
    
    Linear Pareto front with many local fronts.
    """
    
    def __init__(self, n_var: int = 7, n_obj: int = 3):
        super().__init__(n_var, n_obj)
        self.k = n_var - n_obj + 1
    
    def evaluate(self, X: np.ndarray) -> np.ndarray:
        n = X.shape[0]
        Y = np.zeros((n, self.n_obj))
        
        # g function
        xm = X[:, self.n_obj - 1:]
        g = 100 * (
            self.k + 
            np.sum((xm - 0.5) ** 2 - np.cos(20 * np.pi * (xm - 0.5)), axis=1)
        )
        
        for i in range(self.n_obj):
            f = 0.5 * (1 + g)
            for j in range(self.n_obj - 1 - i):
                f = f * X[:, j]
            if i > 0:
                f = f * (1 - X[:, self.n_obj - 1 - i])
            Y[:, i] = f
        
        return Y
    
    def get_pareto_front(self, n_points: int = 1000) -> np.ndarray:
        """Linear Pareto front: sum(f) = 0.5."""
        from scipy.stats import dirichlet
        
        # Sample from unit simplex
        pf = dirichlet.rvs([1] * self.n_obj, size=n_points)
        return pf * 0.5


class DTLZ2(Benchmark):
    """
    DTLZ2 benchmark.
    
    Spherical Pareto front.
    """
    
    def __init__(self, n_var: int = 12, n_obj: int = 3):
        super().__init__(n_var, n_obj)
        self.k = n_var - n_obj + 1
    
    def evaluate(self, X: np.ndarray) -> np.ndarray:
        n = X.shape[0]
        Y = np.zeros((n, self.n_obj))
        
        # g function
        xm = X[:, self.n_obj - 1:]
        g = np.sum((xm - 0.5) ** 2, axis=1)
        
        for i in range(self.n_obj):
            f = (1 + g)
            for j in range(self.n_obj - 1 - i):
                f = f * np.cos(X[:, j] * np.pi / 2)
            if i > 0:
                f = f * np.sin(X[:, self.n_obj - 1 - i] * np.pi / 2)
            Y[:, i] = f
        
        return Y
    
    def get_pareto_front(self, n_points: int = 1000) -> np.ndarray:
        """Spherical Pareto front: sum(f^2) = 1."""
        # Sample angles
        angles = np.random.uniform(0, np.pi / 2, (n_points, self.n_obj - 1))
        
        pf = np.ones((n_points, self.n_obj))
        for i in range(self.n_obj):
            for j in range(self.n_obj - 1 - i):
                pf[:, i] *= np.cos(angles[:, j])
            if i > 0:
                pf[:, i] *= np.sin(angles[:, self.n_obj - 1 - i])
        
        return pf


class DTLZ3(Benchmark):
    """
    DTLZ3 benchmark.
    
    Like DTLZ2 but with many local Pareto fronts.
    """
    
    def __init__(self, n_var: int = 12, n_obj: int = 3):
        super().__init__(n_var, n_obj)
        self.k = n_var - n_obj + 1
    
    def evaluate(self, X: np.ndarray) -> np.ndarray:
        n = X.shape[0]
        Y = np.zeros((n, self.n_obj))
        
        # g function (like DTLZ1)
        xm = X[:, self.n_obj - 1:]
        g = 100 * (
            self.k + 
            np.sum((xm - 0.5) ** 2 - np.cos(20 * np.pi * (xm - 0.5)), axis=1)
        )
        
        for i in range(self.n_obj):
            f = (1 + g)
            for j in range(self.n_obj - 1 - i):
                f = f * np.cos(X[:, j] * np.pi / 2)
            if i > 0:
                f = f * np.sin(X[:, self.n_obj - 1 - i] * np.pi / 2)
            Y[:, i] = f
        
        return Y
    
    def get_pareto_front(self, n_points: int = 1000) -> np.ndarray:
        """Same as DTLZ2."""
        return DTLZ2(self.n_var, self.n_obj).get_pareto_front(n_points)


class DTLZ4(Benchmark):
    """
    DTLZ4 benchmark.
    
    Like DTLZ2 but with biased distribution.
    """
    
    def __init__(self, n_var: int = 12, n_obj: int = 3, alpha: float = 100.0):
        super().__init__(n_var, n_obj)
        self.k = n_var - n_obj + 1
        self.alpha = alpha
    
    def evaluate(self, X: np.ndarray) -> np.ndarray:
        n = X.shape[0]
        Y = np.zeros((n, self.n_obj))
        
        # Apply alpha transformation
        X_alpha = X.copy()
        X_alpha[:, :self.n_obj - 1] = X[:, :self.n_obj - 1] ** self.alpha
        
        # g function
        xm = X_alpha[:, self.n_obj - 1:]
        g = np.sum((xm - 0.5) ** 2, axis=1)
        
        for i in range(self.n_obj):
            f = (1 + g)
            for j in range(self.n_obj - 1 - i):
                f = f * np.cos(X_alpha[:, j] * np.pi / 2)
            if i > 0:
                f = f * np.sin(X_alpha[:, self.n_obj - 1 - i] * np.pi / 2)
            Y[:, i] = f
        
        return Y
    
    def get_pareto_front(self, n_points: int = 1000) -> np.ndarray:
        """Same as DTLZ2."""
        return DTLZ2(self.n_var, self.n_obj).get_pareto_front(n_points)





