"""
BOA Built-in Models

Gaussian Process surrogate models.
"""

from typing import Any, Dict, Optional

import torch
from botorch.fit import fit_gpytorch_mll
from botorch.models import SingleTaskGP
from botorch.models.model import Model as BoTorchModel
from botorch.models.transforms.outcome import Standardize
from gpytorch.kernels import MaternKernel, RBFKernel, ScaleKernel
from gpytorch.mlls import ExactMarginalLogLikelihood

from boa.plugins.base import ModelPlugin, PluginMeta


class GPMaternModel(ModelPlugin):
    """Gaussian Process with Matern 5/2 kernel."""
    
    @classmethod
    def get_meta(cls) -> PluginMeta:
        return PluginMeta(
            name="gp_matern",
            description="GP with Matern 5/2 kernel",
            tags=["surrogate", "gp", "matern"],
        )
    
    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        return {
            "nu": 2.5,
            "outcome_transform": True,
        }
    
    def fit(
        self,
        X: torch.Tensor,
        Y: torch.Tensor,
        params: Optional[Dict[str, Any]] = None,
    ) -> BoTorchModel:
        """Fit GP with Matern kernel."""
        params = self.validate_params(params or {})
        
        # Build model
        outcome_transform = Standardize(m=Y.shape[-1]) if params.get("outcome_transform") else None
        
        model = SingleTaskGP(
            train_X=X,
            train_Y=Y,
            outcome_transform=outcome_transform,
            covar_module=ScaleKernel(
                MaternKernel(nu=params.get("nu", 2.5), ard_num_dims=X.shape[-1])
            ),
        )
        
        # Fit
        mll = ExactMarginalLogLikelihood(model.likelihood, model)
        fit_gpytorch_mll(mll)
        
        return model
    
    def load(
        self,
        state_dict: Dict[str, Any],
        X: torch.Tensor,
        Y: torch.Tensor,
    ) -> BoTorchModel:
        """Load GP from state dict."""
        model = SingleTaskGP(
            train_X=X,
            train_Y=Y,
            outcome_transform=Standardize(m=Y.shape[-1]),
            covar_module=ScaleKernel(MaternKernel(nu=2.5, ard_num_dims=X.shape[-1])),
        )
        model.load_state_dict(state_dict)
        return model


class GPRBFModel(ModelPlugin):
    """Gaussian Process with RBF (Squared Exponential) kernel."""
    
    @classmethod
    def get_meta(cls) -> PluginMeta:
        return PluginMeta(
            name="gp_rbf",
            description="GP with RBF kernel",
            tags=["surrogate", "gp", "rbf"],
        )
    
    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        return {
            "outcome_transform": True,
        }
    
    def fit(
        self,
        X: torch.Tensor,
        Y: torch.Tensor,
        params: Optional[Dict[str, Any]] = None,
    ) -> BoTorchModel:
        """Fit GP with RBF kernel."""
        params = self.validate_params(params or {})
        
        outcome_transform = Standardize(m=Y.shape[-1]) if params.get("outcome_transform") else None
        
        model = SingleTaskGP(
            train_X=X,
            train_Y=Y,
            outcome_transform=outcome_transform,
            covar_module=ScaleKernel(RBFKernel(ard_num_dims=X.shape[-1])),
        )
        
        mll = ExactMarginalLogLikelihood(model.likelihood, model)
        fit_gpytorch_mll(mll)
        
        return model
    
    def load(
        self,
        state_dict: Dict[str, Any],
        X: torch.Tensor,
        Y: torch.Tensor,
    ) -> BoTorchModel:
        """Load GP from state dict."""
        model = SingleTaskGP(
            train_X=X,
            train_Y=Y,
            outcome_transform=Standardize(m=Y.shape[-1]),
            covar_module=ScaleKernel(RBFKernel(ard_num_dims=X.shape[-1])),
        )
        model.load_state_dict(state_dict)
        return model





