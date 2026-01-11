"""
BOA Built-in Samplers

Initial design samplers for exploration.
"""

from typing import Any, Dict, List, Optional

import numpy as np
from scipy.stats import qmc

from boa.plugins.base import SamplerPlugin, PluginMeta
from boa.spec.models import ProcessSpec
from boa.spec.encoder import MixedSpaceEncoder


class LHSSampler(SamplerPlugin):
    """Latin Hypercube Sampler."""
    
    @classmethod
    def get_meta(cls) -> PluginMeta:
        return PluginMeta(
            name="lhs",
            description="Latin Hypercube Sampling",
            tags=["initial_design", "space_filling"],
        )
    
    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        return {
            "seed": None,
        }
    
    def sample(
        self,
        spec: ProcessSpec,
        n_samples: int,
        params: Optional[Dict[str, Any]] = None,
    ) -> np.ndarray:
        """Generate LHS samples in [0, 1]^d."""
        params = self.validate_params(params or {})
        encoder = MixedSpaceEncoder(spec)
        d = encoder.n_encoded
        
        sampler = qmc.LatinHypercube(d=d, seed=params.get("seed"))
        samples = sampler.random(n=n_samples)
        
        return encoder.snap_to_grid(samples)
    
    def sample_raw(
        self,
        spec: ProcessSpec,
        n_samples: int,
        params: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Generate LHS samples in raw format."""
        encoded = self.sample(spec, n_samples, params)
        encoder = MixedSpaceEncoder(spec)
        return encoder.decode(encoded, return_dataframe=False)


class LHSOptimizedSampler(SamplerPlugin):
    """Optimized Latin Hypercube Sampler with maximin criterion."""
    
    @classmethod
    def get_meta(cls) -> PluginMeta:
        return PluginMeta(
            name="lhs_optimized",
            description="Optimized Latin Hypercube Sampling (maximin)",
            tags=["initial_design", "space_filling", "optimized"],
        )
    
    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        return {
            "seed": None,
            "strength": 1,
            "optimization": "random-cd",
        }
    
    def sample(
        self,
        spec: ProcessSpec,
        n_samples: int,
        params: Optional[Dict[str, Any]] = None,
    ) -> np.ndarray:
        """Generate optimized LHS samples."""
        params = self.validate_params(params or {})
        encoder = MixedSpaceEncoder(spec)
        d = encoder.n_encoded
        
        sampler = qmc.LatinHypercube(
            d=d,
            seed=params.get("seed"),
            strength=params.get("strength", 1),
            optimization=params.get("optimization", "random-cd"),
        )
        samples = sampler.random(n=n_samples)
        
        return encoder.snap_to_grid(samples)
    
    def sample_raw(
        self,
        spec: ProcessSpec,
        n_samples: int,
        params: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Generate optimized LHS samples in raw format."""
        encoded = self.sample(spec, n_samples, params)
        encoder = MixedSpaceEncoder(spec)
        return encoder.decode(encoded, return_dataframe=False)


class SobolSampler(SamplerPlugin):
    """Sobol sequence sampler."""
    
    @classmethod
    def get_meta(cls) -> PluginMeta:
        return PluginMeta(
            name="sobol",
            description="Sobol quasi-random sequence",
            tags=["initial_design", "quasi_random"],
        )
    
    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        return {
            "seed": None,
            "scramble": True,
        }
    
    def sample(
        self,
        spec: ProcessSpec,
        n_samples: int,
        params: Optional[Dict[str, Any]] = None,
    ) -> np.ndarray:
        """Generate Sobol sequence samples."""
        params = self.validate_params(params or {})
        encoder = MixedSpaceEncoder(spec)
        d = encoder.n_encoded
        
        sampler = qmc.Sobol(
            d=d,
            scramble=params.get("scramble", True),
            seed=params.get("seed"),
        )
        samples = sampler.random(n=n_samples)
        
        return encoder.snap_to_grid(samples)
    
    def sample_raw(
        self,
        spec: ProcessSpec,
        n_samples: int,
        params: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Generate Sobol samples in raw format."""
        encoded = self.sample(spec, n_samples, params)
        encoder = MixedSpaceEncoder(spec)
        return encoder.decode(encoded, return_dataframe=False)


class RandomSampler(SamplerPlugin):
    """Uniform random sampler."""
    
    @classmethod
    def get_meta(cls) -> PluginMeta:
        return PluginMeta(
            name="random",
            description="Uniform random sampling",
            tags=["initial_design", "random"],
        )
    
    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        return {
            "seed": None,
        }
    
    def sample(
        self,
        spec: ProcessSpec,
        n_samples: int,
        params: Optional[Dict[str, Any]] = None,
    ) -> np.ndarray:
        """Generate uniform random samples."""
        params = self.validate_params(params or {})
        encoder = MixedSpaceEncoder(spec)
        d = encoder.n_encoded
        
        rng = np.random.default_rng(params.get("seed"))
        samples = rng.uniform(0, 1, size=(n_samples, d))
        
        return encoder.snap_to_grid(samples)
    
    def sample_raw(
        self,
        spec: ProcessSpec,
        n_samples: int,
        params: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Generate random samples in raw format."""
        encoded = self.sample(spec, n_samples, params)
        encoder = MixedSpaceEncoder(spec)
        return encoder.decode(encoded, return_dataframe=False)





