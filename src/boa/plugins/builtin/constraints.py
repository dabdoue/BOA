"""
BOA Built-in Constraints

Physical and process constraints for optimization.
"""

from typing import Any, Dict, Optional

import numpy as np

from boa.plugins.base import ConstraintPlugin, PluginMeta
from boa.spec.models import ProcessSpec


class ClausiusClapeyronConstraint(ConstraintPlugin):
    """
    Clausius-Clapeyron constraint for humidity and temperature.
    
    Ensures that absolute humidity doesn't exceed the saturation
    humidity at a given temperature.
    """
    
    @classmethod
    def get_meta(cls) -> PluginMeta:
        return PluginMeta(
            name="clausius_clapeyron",
            description="Physical constraint on humidity vs temperature",
            tags=["physical", "humidity", "temperature"],
        )
    
    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        return {
            "absolute_humidity_col": "absolute_humidity",
            "temperature_col": "temperature",
            "safety_factor": 0.95,  # Keep below saturation
        }
    
    def _saturation_humidity(self, temp_c: np.ndarray) -> np.ndarray:
        """
        Calculate saturation absolute humidity (g/m³) at given temperature (°C).
        
        Uses Magnus formula approximation.
        """
        # Saturation vapor pressure (hPa)
        e_s = 6.112 * np.exp(17.67 * temp_c / (temp_c + 243.5))
        
        # Convert to absolute humidity (g/m³)
        # Using ideal gas law approximation
        T_kelvin = temp_c + 273.15
        abs_humidity = 216.7 * e_s / T_kelvin
        
        return abs_humidity
    
    def check(
        self,
        X: np.ndarray,
        spec: ProcessSpec,
        params: Optional[Dict[str, Any]] = None,
    ) -> np.ndarray:
        """Check if points satisfy Clausius-Clapeyron constraint."""
        params = self.validate_params(params or {})
        
        ah_col = params["absolute_humidity_col"]
        temp_col = params["temperature_col"]
        safety_factor = params["safety_factor"]
        
        # Get column indices
        from boa.spec.encoder import MixedSpaceEncoder
        encoder = MixedSpaceEncoder(spec)
        
        # Find indices for the relevant columns
        ah_idx = None
        temp_idx = None
        col_idx = 0
        
        for info in encoder.input_info:
            if info["name"] == ah_col:
                ah_idx = col_idx
            elif info["name"] == temp_col:
                temp_idx = col_idx
            
            if info["type"] == "CategoricalInput":
                col_idx += len(info["categories"])
            else:
                col_idx += 1
            
            if info.get("is_conditional"):
                col_idx += 1
        
        if ah_idx is None or temp_idx is None:
            # Columns not found, constraint doesn't apply
            return np.ones(len(X), dtype=bool)
        
        # Get raw values (denormalize)
        ah_info = next(i for i in encoder.input_info if i["name"] == ah_col)
        temp_info = next(i for i in encoder.input_info if i["name"] == temp_col)
        
        ah_lo, ah_hi = ah_info["bounds"]
        temp_lo, temp_hi = temp_info["bounds"]
        
        ah_values = X[:, ah_idx] * (ah_hi - ah_lo) + ah_lo
        temp_values = X[:, temp_idx] * (temp_hi - temp_lo) + temp_lo
        
        # Calculate saturation humidity
        sat_humidity = self._saturation_humidity(temp_values)
        
        # Check constraint
        return ah_values <= safety_factor * sat_humidity
    
    def apply(
        self,
        X: np.ndarray,
        spec: ProcessSpec,
        params: Optional[Dict[str, Any]] = None,
    ) -> np.ndarray:
        """Project points to feasible region."""
        params = self.validate_params(params or {})
        
        ah_col = params["absolute_humidity_col"]
        temp_col = params["temperature_col"]
        safety_factor = params["safety_factor"]
        
        from boa.spec.encoder import MixedSpaceEncoder
        encoder = MixedSpaceEncoder(spec)
        
        # Find indices
        ah_idx = None
        temp_idx = None
        col_idx = 0
        
        for info in encoder.input_info:
            if info["name"] == ah_col:
                ah_idx = col_idx
            elif info["name"] == temp_col:
                temp_idx = col_idx
            
            if info["type"] == "CategoricalInput":
                col_idx += len(info["categories"])
            else:
                col_idx += 1
            
            if info.get("is_conditional"):
                col_idx += 1
        
        if ah_idx is None or temp_idx is None:
            return X
        
        X = X.copy()
        
        # Get info for denormalization
        ah_info = next(i for i in encoder.input_info if i["name"] == ah_col)
        temp_info = next(i for i in encoder.input_info if i["name"] == temp_col)
        
        ah_lo, ah_hi = ah_info["bounds"]
        temp_lo, temp_hi = temp_info["bounds"]
        
        # Denormalize temperature
        temp_values = X[:, temp_idx] * (temp_hi - temp_lo) + temp_lo
        
        # Calculate max allowed humidity
        sat_humidity = self._saturation_humidity(temp_values)
        max_humidity = safety_factor * sat_humidity
        
        # Denormalize current humidity
        ah_values = X[:, ah_idx] * (ah_hi - ah_lo) + ah_lo
        
        # Clip to max allowed
        ah_values = np.minimum(ah_values, max_humidity)
        
        # Renormalize
        X[:, ah_idx] = (ah_values - ah_lo) / (ah_hi - ah_lo)
        
        return X





