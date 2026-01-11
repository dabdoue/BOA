"""
BOA Built-in Acquisition Functions

Multi-objective acquisition functions for Bayesian optimization.
"""

from typing import Any, Dict, Optional

import torch
from botorch.acquisition import AcquisitionFunction
from botorch.acquisition.multi_objective.logei import (
    qLogNoisyExpectedHypervolumeImprovement,
)
from botorch.acquisition.multi_objective.monte_carlo import (
    qNoisyExpectedHypervolumeImprovement,
)
from botorch.acquisition.multi_objective.parego import qLogNParEGO
from botorch.models.model import Model as BoTorchModel
from botorch.optim import optimize_acqf
from botorch.sampling.normal import SobolQMCNormalSampler
from botorch.utils.sampling import sample_simplex

from boa.plugins.base import AcquisitionPlugin, PluginMeta


class QLogNEHVIAcquisition(AcquisitionPlugin):
    """Log-transformed Noisy Expected Hypervolume Improvement."""
    
    @classmethod
    def get_meta(cls) -> PluginMeta:
        return PluginMeta(
            name="qlogNEHVI",
            description="Log-transformed qNEHVI for numerical stability",
            tags=["multi_objective", "hypervolume", "log_transform"],
        )
    
    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        return {
            "num_samples": 128,
            "prune_baseline": True,
            "cache_root": True,
        }
    
    def build(
        self,
        model: BoTorchModel,
        best_f: Optional[torch.Tensor] = None,
        ref_point: Optional[torch.Tensor] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> AcquisitionFunction:
        """Build qLogNEHVI acquisition function."""
        params = self.validate_params(params or {})
        
        if ref_point is None:
            raise ValueError("ref_point is required for qLogNEHVI")
        
        sampler = SobolQMCNormalSampler(
            sample_shape=torch.Size([params["num_samples"]])
        )
        
        return qLogNoisyExpectedHypervolumeImprovement(
            model=model,
            ref_point=ref_point,
            X_baseline=model.train_inputs[0],
            sampler=sampler,
            prune_baseline=params["prune_baseline"],
            cache_root=params["cache_root"],
        )
    
    def optimize(
        self,
        acq_function: AcquisitionFunction,
        bounds: torch.Tensor,
        q: int = 1,
        params: Optional[Dict[str, Any]] = None,
    ) -> torch.Tensor:
        """Optimize qLogNEHVI."""
        params = params or {}
        
        candidates, _ = optimize_acqf(
            acq_function=acq_function,
            bounds=bounds,
            q=q,
            num_restarts=params.get("num_restarts", 20),
            raw_samples=params.get("raw_samples", 512),
        )
        
        return candidates


class QNEHVIAcquisition(AcquisitionPlugin):
    """Noisy Expected Hypervolume Improvement."""
    
    @classmethod
    def get_meta(cls) -> PluginMeta:
        return PluginMeta(
            name="qNEHVI",
            description="Noisy Expected Hypervolume Improvement",
            tags=["multi_objective", "hypervolume"],
        )
    
    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        return {
            "num_samples": 128,
            "prune_baseline": True,
            "cache_root": True,
        }
    
    def build(
        self,
        model: BoTorchModel,
        best_f: Optional[torch.Tensor] = None,
        ref_point: Optional[torch.Tensor] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> AcquisitionFunction:
        """Build qNEHVI acquisition function."""
        params = self.validate_params(params or {})
        
        if ref_point is None:
            raise ValueError("ref_point is required for qNEHVI")
        
        sampler = SobolQMCNormalSampler(
            sample_shape=torch.Size([params["num_samples"]])
        )
        
        return qNoisyExpectedHypervolumeImprovement(
            model=model,
            ref_point=ref_point,
            X_baseline=model.train_inputs[0],
            sampler=sampler,
            prune_baseline=params["prune_baseline"],
            cache_root=params["cache_root"],
        )
    
    def optimize(
        self,
        acq_function: AcquisitionFunction,
        bounds: torch.Tensor,
        q: int = 1,
        params: Optional[Dict[str, Any]] = None,
    ) -> torch.Tensor:
        """Optimize qNEHVI."""
        params = params or {}
        
        candidates, _ = optimize_acqf(
            acq_function=acq_function,
            bounds=bounds,
            q=q,
            num_restarts=params.get("num_restarts", 20),
            raw_samples=params.get("raw_samples", 512),
        )
        
        return candidates


class QParEGOAcquisition(AcquisitionPlugin):
    """ParEGO: Scalarized multi-objective with random weights."""
    
    @classmethod
    def get_meta(cls) -> PluginMeta:
        return PluginMeta(
            name="qParEGO",
            description="ParEGO with Chebyshev scalarization (qLogNParEGO)",
            tags=["multi_objective", "scalarization"],
        )
    
    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        return {
            "num_samples": 128,
        }
    
    def build(
        self,
        model: BoTorchModel,
        best_f: Optional[torch.Tensor] = None,
        ref_point: Optional[torch.Tensor] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> AcquisitionFunction:
        """Build qLogNParEGO acquisition function."""
        params = self.validate_params(params or {})
        
        sampler = SobolQMCNormalSampler(
            sample_shape=torch.Size([params["num_samples"]])
        )
        
        # Use the modern qLogNParEGO
        return qLogNParEGO(
            model=model,
            X_baseline=model.train_inputs[0],
            sampler=sampler,
        )
    
    def optimize(
        self,
        acq_function: AcquisitionFunction,
        bounds: torch.Tensor,
        q: int = 1,
        params: Optional[Dict[str, Any]] = None,
    ) -> torch.Tensor:
        """Optimize qParEGO."""
        params = params or {}
        
        candidates, _ = optimize_acqf(
            acq_function=acq_function,
            bounds=bounds,
            q=q,
            num_restarts=params.get("num_restarts", 10),
            raw_samples=params.get("raw_samples", 256),
        )
        
        return candidates


class RandomAcquisition(AcquisitionPlugin):
    """Random acquisition (baseline)."""
    
    @classmethod
    def get_meta(cls) -> PluginMeta:
        return PluginMeta(
            name="random",
            description="Random sampling (no optimization)",
            tags=["baseline", "random"],
        )
    
    def build(
        self,
        model: BoTorchModel,
        best_f: Optional[torch.Tensor] = None,
        ref_point: Optional[torch.Tensor] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Random doesn't need an acquisition function."""
        return None
    
    def optimize(
        self,
        acq_function: AcquisitionFunction,
        bounds: torch.Tensor,
        q: int = 1,
        params: Optional[Dict[str, Any]] = None,
    ) -> torch.Tensor:
        """Generate random candidates."""
        params = params or {}
        seed = params.get("seed")
        
        if seed is not None:
            torch.manual_seed(seed)
        
        d = bounds.shape[1]
        candidates = torch.rand(q, d)
        
        # Scale to bounds
        candidates = bounds[0] + (bounds[1] - bounds[0]) * candidates
        
        return candidates

