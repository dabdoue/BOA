"""
BOA Campaign Analyzer

Metrics and analysis for optimization campaigns.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import logging

import numpy as np

from boa.db.models import Campaign, Observation, Iteration
from boa.spec.models import ProcessSpec

logger = logging.getLogger(__name__)


@dataclass
class CampaignMetrics:
    """Aggregated campaign metrics."""
    
    n_observations: int
    n_iterations: int
    best_values: Dict[str, float]  # Objective name -> best value
    best_observation: Optional[Dict[str, Any]]  # Best x_raw, y
    hypervolume: Optional[float] = None
    pareto_front_size: Optional[int] = None
    improvement_history: List[float] = field(default_factory=list)
    objective_bounds: Dict[str, Tuple[float, float]] = field(default_factory=dict)


class CampaignAnalyzer:
    """
    Analyzes campaign progress and computes metrics.
    
    Provides:
    - Best values per objective
    - Pareto front analysis
    - Hypervolume computation
    - Improvement tracking
    """
    
    def __init__(
        self,
        spec: ProcessSpec,
        observations: List[Observation],
        ref_point: Optional[np.ndarray] = None,
    ):
        """
        Initialize analyzer.
        
        Args:
            spec: Process specification
            observations: List of observations
            ref_point: Reference point for hypervolume
        """
        self.spec = spec
        self.observations = observations
        self.ref_point = ref_point
        
        # Build arrays
        self._build_arrays()
    
    def _build_arrays(self) -> None:
        """Build numpy arrays from observations."""
        if not self.observations:
            self.Y = np.array([]).reshape(0, len(self.spec.objectives))
            self.X_raw = []
            return
        
        self.Y = np.array([
            [obs.y.get(obj.name, np.nan) for obj in self.spec.objectives]
            for obs in self.observations
        ])
        
        self.X_raw = [obs.x_raw for obs in self.observations]
    
    def compute_metrics(self) -> CampaignMetrics:
        """
        Compute comprehensive campaign metrics.
        
        Returns:
            CampaignMetrics with all computed values
        """
        if len(self.observations) == 0:
            return CampaignMetrics(
                n_observations=0,
                n_iterations=0,
                best_values={obj.name: float('nan') for obj in self.spec.objectives},
                best_observation=None,
            )
        
        # Best values per objective
        best_values = {}
        for i, obj in enumerate(self.spec.objectives):
            values = self.Y[:, i]
            valid = ~np.isnan(values)
            if not valid.any():
                best_values[obj.name] = float('nan')
            elif obj.is_maximization:
                best_values[obj.name] = float(values[valid].max())
            else:
                best_values[obj.name] = float(values[valid].min())
        
        # Best observation (using first objective as primary)
        best_obs = None
        if len(self.spec.objectives) == 1:
            obj = self.spec.objectives[0]
            valid_mask = ~np.isnan(self.Y[:, 0])
            if valid_mask.any():
                if obj.is_maximization:
                    best_idx = np.argmax(self.Y[valid_mask, 0])
                else:
                    best_idx = np.argmin(self.Y[valid_mask, 0])
                actual_idx = np.where(valid_mask)[0][best_idx]
                best_obs = {
                    "x_raw": self.X_raw[actual_idx],
                    "y": {self.spec.objectives[i].name: float(self.Y[actual_idx, i]) 
                          for i in range(self.Y.shape[1])},
                }
        else:
            # Multi-objective: return a Pareto optimal point
            pareto_mask = self._get_pareto_mask()
            if pareto_mask.any():
                # Pick first Pareto optimal
                pareto_idx = np.where(pareto_mask)[0][0]
                best_obs = {
                    "x_raw": self.X_raw[pareto_idx],
                    "y": {self.spec.objectives[i].name: float(self.Y[pareto_idx, i])
                          for i in range(self.Y.shape[1])},
                }
        
        # Objective bounds
        obj_bounds = {}
        for i, obj in enumerate(self.spec.objectives):
            valid = ~np.isnan(self.Y[:, i])
            if valid.any():
                obj_bounds[obj.name] = (
                    float(self.Y[valid, i].min()),
                    float(self.Y[valid, i].max()),
                )
        
        # Pareto front
        pareto_mask = self._get_pareto_mask()
        pareto_size = int(pareto_mask.sum())
        
        # Hypervolume
        hv = None
        if self.ref_point is not None and len(self.spec.objectives) > 1:
            hv = self._compute_hypervolume()
        
        # Improvement history
        improvement_history = self._compute_improvement_history()
        
        return CampaignMetrics(
            n_observations=len(self.observations),
            n_iterations=0,  # Would need iterations list
            best_values=best_values,
            best_observation=best_obs,
            hypervolume=hv,
            pareto_front_size=pareto_size,
            improvement_history=improvement_history,
            objective_bounds=obj_bounds,
        )
    
    def _get_pareto_mask(self) -> np.ndarray:
        """
        Compute Pareto optimal mask.
        
        Returns:
            Boolean array where True indicates Pareto optimal
        """
        if len(self.Y) == 0:
            return np.array([], dtype=bool)
        
        n = len(self.Y)
        is_pareto = np.ones(n, dtype=bool)
        
        # Transform for maximization (flip minimization objectives)
        Y_max = self.Y.copy()
        for i, obj in enumerate(self.spec.objectives):
            if not obj.is_maximization:
                Y_max[:, i] = -Y_max[:, i]
        
        # Handle NaN values
        Y_max = np.nan_to_num(Y_max, nan=-np.inf)
        
        for i in range(n):
            if not is_pareto[i]:
                continue
            
            for j in range(n):
                if i == j:
                    continue
                
                # Check if j dominates i (j is at least as good in all, strictly better in at least one)
                at_least_as_good = np.all(Y_max[j] >= Y_max[i])
                strictly_better = np.any(Y_max[j] > Y_max[i])
                
                if at_least_as_good and strictly_better:
                    is_pareto[i] = False
                    break
        
        return is_pareto
    
    def _compute_hypervolume(self) -> Optional[float]:
        """
        Compute hypervolume indicator.
        
        Returns:
            Hypervolume value or None if cannot compute
        """
        try:
            from botorch.utils.multi_objective.hypervolume import Hypervolume
            import torch
        except ImportError:
            return None
        
        if self.ref_point is None:
            return None
        
        pareto_mask = self._get_pareto_mask()
        if not pareto_mask.any():
            return 0.0
        
        pareto_Y = self.Y[pareto_mask]
        
        # Transform for maximization
        Y_max = pareto_Y.copy()
        for i, obj in enumerate(self.spec.objectives):
            if not obj.is_maximization:
                Y_max[:, i] = -Y_max[:, i]
        
        ref = self.ref_point.copy()
        for i, obj in enumerate(self.spec.objectives):
            if not obj.is_maximization:
                ref[i] = -ref[i]
        
        hv = Hypervolume(ref_point=torch.tensor(ref))
        return float(hv.compute(torch.tensor(Y_max)))
    
    def _compute_improvement_history(self) -> List[float]:
        """
        Compute improvement over time.
        
        For single objective: best value after each observation.
        For multi-objective: hypervolume after each observation.
        
        Returns:
            List of improvement values
        """
        if len(self.Y) == 0:
            return []
        
        if len(self.spec.objectives) == 1:
            # Single objective: cumulative best
            obj = self.spec.objectives[0]
            history = []
            best = float('-inf') if obj.is_maximization else float('inf')
            
            for val in self.Y[:, 0]:
                if np.isnan(val):
                    history.append(float('nan'))
                elif obj.is_maximization:
                    best = max(best, val)
                    history.append(float(best))
                else:
                    best = min(best, val)
                    history.append(float(best))
            
            return history
        else:
            # Multi-objective: hypervolume at each step
            # This is expensive, so we compute at intervals
            if self.ref_point is None:
                return []
            
            history = []
            for i in range(1, len(self.Y) + 1):
                partial = CampaignAnalyzer(
                    self.spec,
                    self.observations[:i],
                    self.ref_point,
                )
                hv = partial._compute_hypervolume()
                history.append(hv if hv is not None else 0.0)
            
            return history
    
    def get_pareto_front(self) -> List[Dict[str, Any]]:
        """
        Get Pareto optimal observations.
        
        Returns:
            List of {x_raw, y} dicts for Pareto optimal points
        """
        pareto_mask = self._get_pareto_mask()
        
        front = []
        for i, is_optimal in enumerate(pareto_mask):
            if is_optimal:
                front.append({
                    "x_raw": self.X_raw[i],
                    "y": {self.spec.objectives[j].name: float(self.Y[i, j])
                          for j in range(self.Y.shape[1])},
                })
        
        return front

