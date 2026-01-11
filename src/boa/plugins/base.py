"""
BOA Plugin Base Classes

Abstract base classes for all plugin types with consistent interface patterns.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type, TypeVar

import numpy as np
import torch
from botorch.acquisition import AcquisitionFunction
from botorch.models.model import Model as BoTorchModel

from boa.spec.models import ProcessSpec


@dataclass
class PluginMeta:
    """Plugin metadata."""
    
    name: str
    description: str = ""
    version: str = "1.0.0"
    author: str = ""
    tags: List[str] = field(default_factory=list)


class Plugin(ABC):
    """Base class for all plugins."""
    
    meta: PluginMeta
    
    @classmethod
    @abstractmethod
    def get_meta(cls) -> PluginMeta:
        """Return plugin metadata."""
        ...
    
    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        """Return default parameters."""
        return {}
    
    @classmethod
    def validate_params(cls, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize parameters."""
        defaults = cls.get_default_params()
        return {**defaults, **params}


# =============================================================================
# Sampler Plugin
# =============================================================================


class SamplerPlugin(Plugin):
    """
    Base class for initial design samplers.
    
    Generates initial points for exploration before model training.
    """
    
    @abstractmethod
    def sample(
        self,
        spec: ProcessSpec,
        n_samples: int,
        params: Optional[Dict[str, Any]] = None,
    ) -> np.ndarray:
        """
        Generate sample points.
        
        Args:
            spec: Process specification
            n_samples: Number of samples to generate
            params: Optional sampler parameters
            
        Returns:
            Array of shape (n_samples, n_dims) with normalized values in [0, 1]
        """
        ...
    
    @abstractmethod
    def sample_raw(
        self,
        spec: ProcessSpec,
        n_samples: int,
        params: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generate sample points in raw (unencoded) format.
        
        Args:
            spec: Process specification
            n_samples: Number of samples to generate
            params: Optional sampler parameters
            
        Returns:
            List of dicts with variable names as keys
        """
        ...


# =============================================================================
# Model Plugin
# =============================================================================


class ModelPlugin(Plugin):
    """
    Base class for surrogate models.
    
    Wraps GP or other surrogate models for optimization.
    """
    
    @abstractmethod
    def fit(
        self,
        X: torch.Tensor,
        Y: torch.Tensor,
        params: Optional[Dict[str, Any]] = None,
    ) -> BoTorchModel:
        """
        Fit surrogate model.
        
        Args:
            X: Training inputs of shape (n, d)
            Y: Training outputs of shape (n, m)
            params: Optional model parameters
            
        Returns:
            Fitted BoTorch model
        """
        ...
    
    @abstractmethod
    def load(
        self,
        state_dict: Dict[str, Any],
        X: torch.Tensor,
        Y: torch.Tensor,
    ) -> BoTorchModel:
        """
        Load model from state dict.
        
        Args:
            state_dict: Saved model state
            X: Training inputs
            Y: Training outputs
            
        Returns:
            Restored BoTorch model
        """
        ...
    
    def save(self, model: BoTorchModel) -> Dict[str, Any]:
        """
        Save model state.
        
        Args:
            model: Trained model
            
        Returns:
            State dict for serialization
        """
        return model.state_dict()


# =============================================================================
# Acquisition Plugin
# =============================================================================


class AcquisitionPlugin(Plugin):
    """
    Base class for acquisition functions.
    
    Defines how to select next candidate points.
    """
    
    @abstractmethod
    def build(
        self,
        model: BoTorchModel,
        best_f: Optional[torch.Tensor] = None,
        ref_point: Optional[torch.Tensor] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> AcquisitionFunction:
        """
        Build acquisition function.
        
        Args:
            model: Fitted surrogate model
            best_f: Best observed value (for improvement-based acq)
            ref_point: Reference point for hypervolume-based acq
            params: Optional acquisition parameters
            
        Returns:
            BoTorch acquisition function
        """
        ...
    
    @abstractmethod
    def optimize(
        self,
        acq_function: AcquisitionFunction,
        bounds: torch.Tensor,
        q: int = 1,
        params: Optional[Dict[str, Any]] = None,
    ) -> torch.Tensor:
        """
        Optimize acquisition function.
        
        Args:
            acq_function: Built acquisition function
            bounds: Variable bounds of shape (2, d)
            q: Batch size (number of candidates)
            params: Optional optimization parameters
            
        Returns:
            Candidate points of shape (q, d)
        """
        ...


# =============================================================================
# Constraint Plugin
# =============================================================================


class ConstraintPlugin(Plugin):
    """
    Base class for constraints.
    
    Implements constraint checking and enforcement.
    """
    
    @abstractmethod
    def check(
        self,
        X: np.ndarray,
        spec: ProcessSpec,
        params: Optional[Dict[str, Any]] = None,
    ) -> np.ndarray:
        """
        Check if points satisfy constraint.
        
        Args:
            X: Points to check of shape (n, d)
            spec: Process specification
            params: Optional constraint parameters
            
        Returns:
            Boolean mask of shape (n,) - True if constraint satisfied
        """
        ...
    
    @abstractmethod
    def apply(
        self,
        X: np.ndarray,
        spec: ProcessSpec,
        params: Optional[Dict[str, Any]] = None,
    ) -> np.ndarray:
        """
        Apply constraint to points (project to feasible region).
        
        Args:
            X: Points to constrain of shape (n, d)
            spec: Process specification
            params: Optional constraint parameters
            
        Returns:
            Constrained points of shape (n, d)
        """
        ...


# =============================================================================
# Objective Transform Plugin
# =============================================================================


class ObjectiveTransformPlugin(Plugin):
    """
    Base class for objective transforms.
    
    Transforms objective values for scalarization or normalization.
    """
    
    @abstractmethod
    def transform(
        self,
        Y: torch.Tensor,
        spec: ProcessSpec,
        params: Optional[Dict[str, Any]] = None,
    ) -> torch.Tensor:
        """
        Transform objective values.
        
        Args:
            Y: Objective values of shape (n, m)
            spec: Process specification
            params: Optional transform parameters
            
        Returns:
            Transformed values of shape (n, m') where m' may differ from m
        """
        ...
    
    @abstractmethod
    def inverse_transform(
        self,
        Y_transformed: torch.Tensor,
        spec: ProcessSpec,
        params: Optional[Dict[str, Any]] = None,
    ) -> torch.Tensor:
        """
        Inverse transform objective values.
        
        Args:
            Y_transformed: Transformed values
            spec: Process specification
            params: Optional transform parameters
            
        Returns:
            Original-scale values
        """
        ...





