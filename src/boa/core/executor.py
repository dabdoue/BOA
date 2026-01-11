"""
BOA Strategy Executor

Executes optimization strategies: fitting models and generating proposals.
"""

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import logging

import numpy as np
import torch

from boa.spec.models import ProcessSpec, StrategySpec
from boa.spec.encoder import MixedSpaceEncoder
from boa.plugins.registry import get_registry

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of strategy execution."""
    
    strategy_name: str
    candidates_encoded: np.ndarray  # Shape (q, d)
    candidates_raw: List[Dict[str, Any]]
    acq_values: Optional[np.ndarray] = None
    predictions: Optional[Dict[str, np.ndarray]] = None
    model_state: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class StrategyExecutor:
    """
    Executes optimization strategies.
    
    Handles:
    - Initial sampling when no data
    - Model fitting with data
    - Acquisition function optimization
    - Candidate generation
    """
    
    def __init__(
        self,
        spec: ProcessSpec,
        strategy: StrategySpec,
        device: Optional[str] = None,
        dtype: torch.dtype = torch.float64,
    ):
        """
        Initialize executor.
        
        Args:
            spec: Process specification
            strategy: Strategy configuration
            device: Torch device (auto-detect if None)
            dtype: Torch dtype for numerical precision
        """
        self.spec = spec
        self.strategy = strategy
        self.encoder = MixedSpaceEncoder(spec)
        self.dtype = dtype
        
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)
        
        # Get plugins
        registry = get_registry()
        self.sampler_cls = registry.get_sampler(strategy.sampler)
        self.model_cls = registry.get_model(strategy.model)
        self.acquisition_cls = registry.get_acquisition(strategy.acquisition)
        
        self._fitted_model = None
    
    def execute_initial_design(
        self,
        n_samples: int,
    ) -> ExecutionResult:
        """
        Generate initial design samples.
        
        Args:
            n_samples: Number of samples to generate
            
        Returns:
            ExecutionResult with initial candidates
        """
        sampler = self.sampler_cls()
        
        samples_encoded = sampler.sample(
            self.spec,
            n_samples,
            self.strategy.sampler_params,
        )
        samples_raw = sampler.sample_raw(
            self.spec,
            n_samples,
            self.strategy.sampler_params,
        )
        
        return ExecutionResult(
            strategy_name=self.strategy.name,
            candidates_encoded=samples_encoded,
            candidates_raw=samples_raw,
            metadata={"phase": "initial_design", "sampler": self.strategy.sampler},
        )
    
    def execute_optimization(
        self,
        X: np.ndarray,
        Y: np.ndarray,
        n_candidates: int = 1,
        ref_point: Optional[np.ndarray] = None,
    ) -> ExecutionResult:
        """
        Execute optimization iteration.
        
        Args:
            X: Training inputs, shape (n, d)
            Y: Training outputs, shape (n, m)
            n_candidates: Number of candidates to propose
            ref_point: Reference point for hypervolume (auto-compute if None)
            
        Returns:
            ExecutionResult with optimized candidates
        """
        # Convert to torch tensors
        X_torch = torch.tensor(X, dtype=self.dtype, device=self.device)
        Y_torch = torch.tensor(Y, dtype=self.dtype, device=self.device)
        
        # Flip signs for minimization objectives
        Y_transformed = Y_torch.clone()
        for i, obj in enumerate(self.spec.objectives):
            if not obj.is_maximization:
                Y_transformed[:, i] = -Y_transformed[:, i]
        
        # Fit model
        model_plugin = self.model_cls()
        model = model_plugin.fit(
            X_torch,
            Y_transformed,
            self.strategy.model_params,
        )
        self._fitted_model = model
        
        # Compute reference point if not provided
        if ref_point is None:
            # Use min observed - buffer for each objective
            ref_point = Y_transformed.min(dim=0).values - 0.1 * Y_transformed.std(dim=0)
        else:
            ref_point = torch.tensor(ref_point, dtype=self.dtype, device=self.device)
        
        # Build acquisition function
        acq_plugin = self.acquisition_cls()
        acq_func = acq_plugin.build(
            model=model,
            best_f=Y_transformed.max(dim=0).values if Y_transformed.shape[1] == 1 else None,
            ref_point=ref_point,
            params=self.strategy.acquisition_params,
        )
        
        # Get bounds
        bounds = torch.tensor(
            [[0.0] * self.encoder.n_encoded, [1.0] * self.encoder.n_encoded],
            dtype=self.dtype,
            device=self.device,
        )
        
        # Optimize acquisition
        if acq_func is not None:
            candidates = acq_plugin.optimize(
                acq_func,
                bounds,
                q=n_candidates,
                params=self.strategy.acquisition_params,
            )
            
            # Get acquisition values at candidates
            with torch.no_grad():
                acq_values = acq_func(candidates.unsqueeze(0) if candidates.dim() == 2 else candidates)
        else:
            # Random acquisition
            candidates = acq_plugin.optimize(
                None,
                bounds,
                q=n_candidates,
                params=self.strategy.acquisition_params,
            )
            acq_values = None
        
        # Convert back to numpy
        candidates_np = candidates.cpu().numpy()
        
        # Ensure 2D shape
        if candidates_np.ndim == 1:
            candidates_np = candidates_np.reshape(1, -1)
        
        # Snap to grid for discrete/categorical
        candidates_np = self.encoder.snap_to_grid(candidates_np)
        
        # Ensure 2D shape after snap
        if candidates_np.ndim == 1:
            candidates_np = candidates_np.reshape(1, -1)
        
        # Decode to raw format
        candidates_raw = self.encoder.decode(candidates_np, return_dataframe=False)
        
        # Get predictions for candidates
        predictions = None
        if model is not None:
            with torch.no_grad():
                candidates_torch = torch.tensor(
                    candidates_np, dtype=self.dtype, device=self.device
                )
                posterior = model.posterior(candidates_torch)
                predictions = {
                    "mean": posterior.mean.cpu().numpy(),
                    "std": posterior.variance.sqrt().cpu().numpy(),
                }
        
        return ExecutionResult(
            strategy_name=self.strategy.name,
            candidates_encoded=candidates_np,
            candidates_raw=candidates_raw,
            acq_values=acq_values.cpu().numpy() if acq_values is not None else None,
            predictions=predictions,
            model_state=model_plugin.save(model) if model is not None else None,
            metadata={
                "phase": "optimization",
                "model": self.strategy.model,
                "acquisition": self.strategy.acquisition,
            },
        )
    
    def get_model(self):
        """Get the last fitted model."""
        return self._fitted_model

