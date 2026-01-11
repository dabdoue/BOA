"""
BOA Mixed Space Encoder

Handles encoding and decoding of mixed variable spaces:
- Continuous: normalize to [0, 1]
- Discrete: normalize to [0, 1] based on grid position
- Categorical: one-hot encoding
- Conditional: activity indicators for inactive variables
"""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from boa.spec.models import (
    ProcessSpec,
    InputSpec,
    ContinuousInput,
    DiscreteInput,
    CategoricalInput,
)


class MixedSpaceEncoder:
    """
    Encoder for mixed variable spaces.
    
    Handles:
    - Continuous variables: min-max normalization to [0, 1]
    - Discrete variables: grid index normalization to [0, 1]
    - Categorical variables: one-hot encoding
    - Conditional variables: activity indicator columns
    
    The encoded space is always numeric and suitable for GP modeling.
    """
    
    def __init__(self, spec: ProcessSpec):
        """
        Initialize encoder from ProcessSpec.
        
        Args:
            spec: Process specification with input definitions
        """
        self.spec = spec
        self._build_encoding_info()
    
    def _build_encoding_info(self) -> None:
        """Build encoding metadata."""
        self.input_info: List[Dict[str, Any]] = []
        self.encoded_columns: List[str] = []
        self.activity_columns: List[str] = []
        
        for inp in self.spec.inputs:
            info: Dict[str, Any] = {
                "name": inp.name,
                "type": type(inp).__name__,
                "is_conditional": inp.is_conditional,
                "active_if": inp.active_if,
            }
            
            if isinstance(inp, ContinuousInput):
                info["bounds"] = inp.bounds
                info["encoded_cols"] = [inp.name]
                self.encoded_columns.append(inp.name)
                
            elif isinstance(inp, DiscreteInput):
                info["values"] = inp.values
                info["bounds"] = inp.bounds
                info["encoded_cols"] = [inp.name]
                self.encoded_columns.append(inp.name)
                
            elif isinstance(inp, CategoricalInput):
                # One-hot columns for categories
                cat_cols = [f"{inp.name}__{cat}" for cat in inp.categories]
                info["categories"] = inp.categories
                info["encoded_cols"] = cat_cols
                self.encoded_columns.extend(cat_cols)
            
            # Add activity indicator for conditional variables
            if inp.is_conditional:
                act_col = f"{inp.name}__active"
                info["activity_col"] = act_col
                self.activity_columns.append(act_col)
            
            self.input_info.append(info)
        
        # Total encoded dimension
        self.n_encoded = len(self.encoded_columns) + len(self.activity_columns)
    
    def encode(
        self,
        data: pd.DataFrame | Dict[str, Any] | List[Dict[str, Any]],
    ) -> np.ndarray:
        """
        Encode raw input data to numeric array.
        
        Args:
            data: DataFrame, single dict, or list of dicts with raw values
            
        Returns:
            Encoded array of shape (n_samples, n_encoded)
        """
        # Convert to DataFrame if needed
        if isinstance(data, dict):
            df = pd.DataFrame([data])
        elif isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = data.copy()
        
        n_samples = len(df)
        encoded = np.zeros((n_samples, self.n_encoded))
        
        col_idx = 0
        for info in self.input_info:
            name = info["name"]
            
            # Check if variable is active for each sample
            if info["is_conditional"]:
                is_active = self._check_activity(df, info["active_if"])
            else:
                is_active = np.ones(n_samples, dtype=bool)
            
            if info["type"] == "ContinuousInput":
                # Normalize to [0, 1]
                lo, hi = info["bounds"]
                values = df[name].values.astype(float)
                normalized = (values - lo) / (hi - lo)
                normalized = np.clip(normalized, 0, 1)
                # Set inactive to 0.5 (midpoint)
                normalized[~is_active] = 0.5
                encoded[:, col_idx] = normalized
                col_idx += 1
                
            elif info["type"] == "DiscreteInput":
                # Normalize based on grid position
                grid = np.array(info["values"])
                lo, hi = info["bounds"]
                values = df[name].values.astype(float)
                normalized = (values - lo) / (hi - lo)
                normalized = np.clip(normalized, 0, 1)
                normalized[~is_active] = 0.5
                encoded[:, col_idx] = normalized
                col_idx += 1
                
            elif info["type"] == "CategoricalInput":
                # One-hot encoding
                categories = info["categories"]
                for cat in categories:
                    is_cat = (df[name] == cat).values.astype(float)
                    is_cat[~is_active] = 0.0
                    encoded[:, col_idx] = is_cat
                    col_idx += 1
            
            # Activity indicator
            if info["is_conditional"]:
                encoded[:, col_idx] = is_active.astype(float)
                col_idx += 1
        
        return encoded
    
    def decode(
        self,
        encoded: np.ndarray,
        return_dataframe: bool = True,
    ) -> pd.DataFrame | List[Dict[str, Any]]:
        """
        Decode numeric array back to raw values.
        
        Args:
            encoded: Encoded array of shape (n_samples, n_encoded)
            return_dataframe: Return DataFrame (True) or list of dicts (False)
            
        Returns:
            Decoded data in raw format
        """
        if encoded.ndim == 1:
            encoded = encoded.reshape(1, -1)
        
        n_samples = encoded.shape[0]
        decoded: List[Dict[str, Any]] = [{} for _ in range(n_samples)]
        
        col_idx = 0
        for info in self.input_info:
            name = info["name"]
            
            if info["type"] == "ContinuousInput":
                lo, hi = info["bounds"]
                normalized = encoded[:, col_idx]
                values = normalized * (hi - lo) + lo
                for i, v in enumerate(values):
                    decoded[i][name] = float(v)
                col_idx += 1
                
            elif info["type"] == "DiscreteInput":
                lo, hi = info["bounds"]
                grid = np.array(info["values"])
                normalized = encoded[:, col_idx]
                values = normalized * (hi - lo) + lo
                # Snap to nearest grid value
                for i, v in enumerate(values):
                    idx = np.argmin(np.abs(grid - v))
                    decoded[i][name] = float(grid[idx])
                col_idx += 1
                
            elif info["type"] == "CategoricalInput":
                categories = info["categories"]
                n_cats = len(categories)
                one_hot = encoded[:, col_idx:col_idx + n_cats]
                cat_indices = np.argmax(one_hot, axis=1)
                for i, idx in enumerate(cat_indices):
                    decoded[i][name] = categories[idx]
                col_idx += n_cats
            
            # Skip activity indicator
            if info["is_conditional"]:
                col_idx += 1
        
        if return_dataframe:
            return pd.DataFrame(decoded)
        return decoded
    
    def _check_activity(
        self,
        df: pd.DataFrame,
        active_if: Dict[str, List[Any]],
    ) -> np.ndarray:
        """Check if variable is active based on conditions."""
        n_samples = len(df)
        is_active = np.ones(n_samples, dtype=bool)
        
        for ref_var, values in active_if.items():
            matches = df[ref_var].isin(values).values
            is_active &= matches
        
        return is_active
    
    def get_bounds(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get bounds for encoded space.
        
        Returns:
            Tuple of (lower_bounds, upper_bounds) arrays
        """
        lower = np.zeros(self.n_encoded)
        upper = np.ones(self.n_encoded)
        return lower, upper
    
    def get_encoded_column_names(self) -> List[str]:
        """Get ordered list of encoded column names."""
        return self.encoded_columns + self.activity_columns
    
    def encode_single(self, x: Dict[str, Any]) -> np.ndarray:
        """Encode a single point."""
        return self.encode(x).flatten()
    
    def decode_single(self, encoded: np.ndarray) -> Dict[str, Any]:
        """Decode a single point."""
        return self.decode(encoded, return_dataframe=False)[0]
    
    def snap_to_grid(self, encoded: np.ndarray) -> np.ndarray:
        """
        Snap encoded values to valid grid points for discrete variables.
        
        Args:
            encoded: Encoded array
            
        Returns:
            Snapped encoded array
        """
        if encoded.ndim == 1:
            encoded = encoded.reshape(1, -1)
        
        result = encoded.copy()
        col_idx = 0
        
        for info in self.input_info:
            if info["type"] == "DiscreteInput":
                # Snap to grid
                grid = np.array(info["values"])
                lo, hi = info["bounds"]
                
                # Denormalize
                values = result[:, col_idx] * (hi - lo) + lo
                
                # Snap
                for i, v in enumerate(values):
                    idx = np.argmin(np.abs(grid - v))
                    values[i] = grid[idx]
                
                # Renormalize
                result[:, col_idx] = (values - lo) / (hi - lo)
                col_idx += 1
                
            elif info["type"] == "ContinuousInput":
                col_idx += 1
                
            elif info["type"] == "CategoricalInput":
                # Snap one-hot to argmax
                n_cats = len(info["categories"])
                one_hot = result[:, col_idx:col_idx + n_cats]
                max_idx = np.argmax(one_hot, axis=1)
                one_hot[:] = 0.0
                for i, idx in enumerate(max_idx):
                    one_hot[i, idx] = 1.0
                col_idx += n_cats
            
            if info["is_conditional"]:
                col_idx += 1
        
        return result.squeeze() if result.shape[0] == 1 else result





