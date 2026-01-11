"""
Tests for BOA mixed space encoder.

Tests encoding/decoding of continuous, discrete, categorical, and conditional variables.
"""

import numpy as np
import pandas as pd
import pytest

from boa.spec.models import (
    ProcessSpec,
    ContinuousInput,
    DiscreteInput,
    CategoricalInput,
    ObjectiveSpec,
)
from boa.spec.encoder import MixedSpaceEncoder


class TestContinuousEncoding:
    """Tests for continuous variable encoding."""
    
    @pytest.fixture
    def continuous_spec(self) -> ProcessSpec:
        """Create spec with continuous variables only."""
        return ProcessSpec(
            name="continuous_test",
            inputs=[
                ContinuousInput(name="x1", bounds=(0, 10)),
                ContinuousInput(name="x2", bounds=(-5, 5)),
            ],
            objectives=[ObjectiveSpec(name="y")],
        )
    
    def test_encode_continuous(self, continuous_spec: ProcessSpec):
        """Test encoding continuous variables."""
        encoder = MixedSpaceEncoder(continuous_spec)
        
        data = pd.DataFrame([
            {"x1": 0.0, "x2": -5.0},
            {"x1": 5.0, "x2": 0.0},
            {"x1": 10.0, "x2": 5.0},
        ])
        
        encoded = encoder.encode(data)
        
        assert encoded.shape == (3, 2)
        # Check normalization to [0, 1]
        np.testing.assert_array_almost_equal(encoded[0], [0.0, 0.0])
        np.testing.assert_array_almost_equal(encoded[1], [0.5, 0.5])
        np.testing.assert_array_almost_equal(encoded[2], [1.0, 1.0])
    
    def test_decode_continuous(self, continuous_spec: ProcessSpec):
        """Test decoding continuous variables."""
        encoder = MixedSpaceEncoder(continuous_spec)
        
        encoded = np.array([
            [0.0, 0.0],
            [0.5, 0.5],
            [1.0, 1.0],
        ])
        
        decoded = encoder.decode(encoded)
        
        assert len(decoded) == 3
        assert decoded["x1"].iloc[0] == pytest.approx(0.0)
        assert decoded["x2"].iloc[0] == pytest.approx(-5.0)
        assert decoded["x1"].iloc[2] == pytest.approx(10.0)
        assert decoded["x2"].iloc[2] == pytest.approx(5.0)
    
    def test_round_trip(self, continuous_spec: ProcessSpec):
        """Test encode/decode round trip."""
        encoder = MixedSpaceEncoder(continuous_spec)
        
        original = pd.DataFrame([
            {"x1": 3.5, "x2": 2.0},
            {"x1": 7.0, "x2": -1.0},
        ])
        
        encoded = encoder.encode(original)
        decoded = encoder.decode(encoded)
        
        pd.testing.assert_frame_equal(
            original.reset_index(drop=True),
            decoded.reset_index(drop=True),
            check_exact=False,
            atol=1e-10,
        )


class TestDiscreteEncoding:
    """Tests for discrete variable encoding."""
    
    @pytest.fixture
    def discrete_spec(self) -> ProcessSpec:
        """Create spec with discrete variables."""
        return ProcessSpec(
            name="discrete_test",
            inputs=[
                DiscreteInput(name="speed", values=[10, 20, 30, 40, 50]),
            ],
            objectives=[ObjectiveSpec(name="y")],
        )
    
    def test_encode_discrete(self, discrete_spec: ProcessSpec):
        """Test encoding discrete variables."""
        encoder = MixedSpaceEncoder(discrete_spec)
        
        data = pd.DataFrame([
            {"speed": 10},
            {"speed": 30},
            {"speed": 50},
        ])
        
        encoded = encoder.encode(data)
        
        assert encoded.shape == (3, 1)
        assert encoded[0, 0] == pytest.approx(0.0)
        assert encoded[1, 0] == pytest.approx(0.5)
        assert encoded[2, 0] == pytest.approx(1.0)
    
    def test_decode_snaps_to_grid(self, discrete_spec: ProcessSpec):
        """Test that decoding snaps to grid values."""
        encoder = MixedSpaceEncoder(discrete_spec)
        
        # Value between grid points
        encoded = np.array([[0.35]])  # Between 0.25 (20) and 0.5 (30)
        decoded = encoder.decode(encoded)
        
        # Should snap to nearest grid value
        assert decoded["speed"].iloc[0] in [20, 30]


class TestCategoricalEncoding:
    """Tests for categorical variable encoding."""
    
    @pytest.fixture
    def categorical_spec(self) -> ProcessSpec:
        """Create spec with categorical variables."""
        return ProcessSpec(
            name="categorical_test",
            inputs=[
                CategoricalInput(name="solvent", categories=["DMF", "DMSO", "GBL"]),
            ],
            objectives=[ObjectiveSpec(name="y")],
        )
    
    def test_encode_categorical(self, categorical_spec: ProcessSpec):
        """Test one-hot encoding of categorical variables."""
        encoder = MixedSpaceEncoder(categorical_spec)
        
        data = pd.DataFrame([
            {"solvent": "DMF"},
            {"solvent": "DMSO"},
            {"solvent": "GBL"},
        ])
        
        encoded = encoder.encode(data)
        
        assert encoded.shape == (3, 3)  # 3 categories
        # Check one-hot encoding
        np.testing.assert_array_equal(encoded[0], [1, 0, 0])
        np.testing.assert_array_equal(encoded[1], [0, 1, 0])
        np.testing.assert_array_equal(encoded[2], [0, 0, 1])
    
    def test_decode_categorical(self, categorical_spec: ProcessSpec):
        """Test decoding one-hot to category."""
        encoder = MixedSpaceEncoder(categorical_spec)
        
        encoded = np.array([
            [1, 0, 0],
            [0, 1, 0],
            [0, 0, 1],
        ])
        
        decoded = encoder.decode(encoded)
        
        assert decoded["solvent"].iloc[0] == "DMF"
        assert decoded["solvent"].iloc[1] == "DMSO"
        assert decoded["solvent"].iloc[2] == "GBL"
    
    def test_snap_categorical(self, categorical_spec: ProcessSpec):
        """Test snapping softmax-like values to one-hot."""
        encoder = MixedSpaceEncoder(categorical_spec)
        
        # Soft values (e.g., from optimizer)
        encoded = np.array([[0.6, 0.3, 0.1]])
        snapped = encoder.snap_to_grid(encoded)
        
        # Should snap to argmax
        np.testing.assert_array_equal(snapped.flatten(), [1, 0, 0])


class TestMixedSpaceEncoding:
    """Tests for mixed variable space encoding."""
    
    @pytest.fixture
    def mixed_spec(self) -> ProcessSpec:
        """Create spec with mixed variable types."""
        return ProcessSpec(
            name="mixed_test",
            inputs=[
                ContinuousInput(name="temp", bounds=(20, 100)),
                DiscreteInput(name="speed", values=[10, 20, 30]),
                CategoricalInput(name="solvent", categories=["A", "B"]),
            ],
            objectives=[ObjectiveSpec(name="y")],
        )
    
    def test_encode_mixed(self, mixed_spec: ProcessSpec):
        """Test encoding mixed variable space."""
        encoder = MixedSpaceEncoder(mixed_spec)
        
        data = pd.DataFrame([
            {"temp": 60, "speed": 20, "solvent": "A"},
        ])
        
        encoded = encoder.encode(data)
        
        # 1 continuous + 1 discrete + 2 categorical = 4 columns
        assert encoded.shape == (1, 4)
        
        # Check values
        assert encoded[0, 0] == pytest.approx(0.5)  # temp normalized
        assert encoded[0, 1] == pytest.approx(0.5)  # speed normalized
        assert encoded[0, 2] == 1.0  # solvent A
        assert encoded[0, 3] == 0.0  # solvent B
    
    def test_decode_mixed(self, mixed_spec: ProcessSpec):
        """Test decoding mixed variable space."""
        encoder = MixedSpaceEncoder(mixed_spec)
        
        encoded = np.array([[0.5, 0.5, 0, 1]])  # temp=60, speed=20, solvent=B
        decoded = encoder.decode(encoded)
        
        assert decoded["temp"].iloc[0] == pytest.approx(60.0)
        assert decoded["speed"].iloc[0] in [20]
        assert decoded["solvent"].iloc[0] == "B"
    
    def test_get_bounds(self, mixed_spec: ProcessSpec):
        """Test getting encoded space bounds."""
        encoder = MixedSpaceEncoder(mixed_spec)
        
        lower, upper = encoder.get_bounds()
        
        assert len(lower) == 4
        assert len(upper) == 4
        np.testing.assert_array_equal(lower, [0, 0, 0, 0])
        np.testing.assert_array_equal(upper, [1, 1, 1, 1])
    
    def test_get_column_names(self, mixed_spec: ProcessSpec):
        """Test getting encoded column names."""
        encoder = MixedSpaceEncoder(mixed_spec)
        
        cols = encoder.get_encoded_column_names()
        
        assert "temp" in cols
        assert "speed" in cols
        assert "solvent__A" in cols
        assert "solvent__B" in cols


class TestConditionalEncoding:
    """Tests for conditional variable encoding."""
    
    @pytest.fixture
    def conditional_spec(self) -> ProcessSpec:
        """Create spec with conditional variables."""
        return ProcessSpec(
            name="conditional_test",
            inputs=[
                CategoricalInput(
                    name="additive",
                    categories=["none", "MACl", "FAI"],
                ),
                ContinuousInput(
                    name="concentration",
                    bounds=(0.01, 0.5),
                    active_if={"additive": ["MACl", "FAI"]},
                ),
            ],
            objectives=[ObjectiveSpec(name="y")],
        )
    
    def test_encode_conditional_active(self, conditional_spec: ProcessSpec):
        """Test encoding when conditional is active."""
        encoder = MixedSpaceEncoder(conditional_spec)
        
        data = pd.DataFrame([
            {"additive": "MACl", "concentration": 0.25},
        ])
        
        encoded = encoder.encode(data)
        
        # 3 categorical + 1 continuous + 1 activity = 5 columns
        assert encoded.shape == (1, 5)
        
        # Check activity indicator
        assert encoded[0, -1] == 1.0  # concentration is active
        
        # Check concentration is encoded (not default)
        assert encoded[0, 3] == pytest.approx((0.25 - 0.01) / (0.5 - 0.01))
    
    def test_encode_conditional_inactive(self, conditional_spec: ProcessSpec):
        """Test encoding when conditional is inactive."""
        encoder = MixedSpaceEncoder(conditional_spec)
        
        data = pd.DataFrame([
            {"additive": "none", "concentration": 0.25},  # concentration ignored
        ])
        
        encoded = encoder.encode(data)
        
        # Check activity indicator
        assert encoded[0, -1] == 0.0  # concentration is inactive
        
        # Concentration should be set to midpoint (0.5)
        assert encoded[0, 3] == pytest.approx(0.5)
    
    def test_activity_column_names(self, conditional_spec: ProcessSpec):
        """Test that activity columns are named correctly."""
        encoder = MixedSpaceEncoder(conditional_spec)
        
        cols = encoder.get_encoded_column_names()
        
        assert "concentration__active" in cols


class TestEncoderEdgeCases:
    """Tests for encoder edge cases."""
    
    def test_encode_single_dict(self):
        """Test encoding a single dictionary."""
        spec = ProcessSpec(
            name="test",
            inputs=[ContinuousInput(name="x", bounds=(0, 1))],
            objectives=[ObjectiveSpec(name="y")],
        )
        encoder = MixedSpaceEncoder(spec)
        
        encoded = encoder.encode_single({"x": 0.5})
        
        assert encoded.shape == (1,)
        assert encoded[0] == pytest.approx(0.5)
    
    def test_decode_single(self):
        """Test decoding a single point."""
        spec = ProcessSpec(
            name="test",
            inputs=[ContinuousInput(name="x", bounds=(0, 1))],
            objectives=[ObjectiveSpec(name="y")],
        )
        encoder = MixedSpaceEncoder(spec)
        
        decoded = encoder.decode_single(np.array([0.75]))
        
        assert decoded["x"] == pytest.approx(0.75)
    
    def test_encode_clips_out_of_bounds(self):
        """Test that encoding clips out-of-bounds values."""
        spec = ProcessSpec(
            name="test",
            inputs=[ContinuousInput(name="x", bounds=(0, 10))],
            objectives=[ObjectiveSpec(name="y")],
        )
        encoder = MixedSpaceEncoder(spec)
        
        data = pd.DataFrame([
            {"x": -5},   # Below bounds
            {"x": 15},   # Above bounds
        ])
        
        encoded = encoder.encode(data)
        
        assert encoded[0, 0] == 0.0  # Clipped to min
        assert encoded[1, 0] == 1.0  # Clipped to max





