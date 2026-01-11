"""
Tests for BOA built-in samplers.

Tests LHS, Sobol, and Random samplers.
"""

import numpy as np
import pytest

from boa.plugins.builtin.samplers import (
    LHSSampler,
    LHSOptimizedSampler,
    SobolSampler,
    RandomSampler,
)
from boa.spec.models import (
    ProcessSpec,
    ContinuousInput,
    DiscreteInput,
    CategoricalInput,
    ObjectiveSpec,
)


@pytest.fixture
def simple_spec() -> ProcessSpec:
    """Create a simple spec for testing."""
    return ProcessSpec(
        name="test",
        inputs=[
            ContinuousInput(name="x1", bounds=(0, 10)),
            ContinuousInput(name="x2", bounds=(-5, 5)),
        ],
        objectives=[ObjectiveSpec(name="y")],
    )


@pytest.fixture
def mixed_spec() -> ProcessSpec:
    """Create a mixed spec for testing."""
    return ProcessSpec(
        name="mixed",
        inputs=[
            ContinuousInput(name="temp", bounds=(20, 100)),
            DiscreteInput(name="speed", values=[10, 20, 30, 40, 50]),
            CategoricalInput(name="solvent", categories=["A", "B", "C"]),
        ],
        objectives=[ObjectiveSpec(name="y")],
    )


class TestLHSSampler:
    """Tests for LHS sampler."""
    
    def test_sample_shape(self, simple_spec: ProcessSpec):
        """Test that samples have correct shape."""
        sampler = LHSSampler()
        samples = sampler.sample(simple_spec, n_samples=10)
        
        assert samples.shape == (10, 2)
    
    def test_samples_in_bounds(self, simple_spec: ProcessSpec):
        """Test that samples are in [0, 1]."""
        sampler = LHSSampler()
        samples = sampler.sample(simple_spec, n_samples=20)
        
        assert np.all(samples >= 0)
        assert np.all(samples <= 1)
    
    def test_sample_raw(self, simple_spec: ProcessSpec):
        """Test raw sampling."""
        sampler = LHSSampler()
        samples = sampler.sample_raw(simple_spec, n_samples=5)
        
        assert len(samples) == 5
        assert all("x1" in s and "x2" in s for s in samples)
        
        # Check bounds
        for s in samples:
            assert 0 <= s["x1"] <= 10
            assert -5 <= s["x2"] <= 5
    
    def test_reproducibility(self, simple_spec: ProcessSpec):
        """Test that seeded samples are reproducible."""
        sampler = LHSSampler()
        
        s1 = sampler.sample(simple_spec, n_samples=5, params={"seed": 42})
        s2 = sampler.sample(simple_spec, n_samples=5, params={"seed": 42})
        
        np.testing.assert_array_equal(s1, s2)
    
    def test_mixed_space(self, mixed_spec: ProcessSpec):
        """Test sampling mixed space."""
        sampler = LHSSampler()
        samples = sampler.sample(mixed_spec, n_samples=10)
        
        # 1 continuous + 1 discrete + 3 categorical = 5 dims
        assert samples.shape == (10, 5)


class TestLHSOptimizedSampler:
    """Tests for optimized LHS sampler."""
    
    def test_sample_shape(self, simple_spec: ProcessSpec):
        """Test that samples have correct shape."""
        sampler = LHSOptimizedSampler()
        samples = sampler.sample(simple_spec, n_samples=10)
        
        assert samples.shape == (10, 2)
    
    def test_samples_in_bounds(self, simple_spec: ProcessSpec):
        """Test that samples are in [0, 1]."""
        sampler = LHSOptimizedSampler()
        samples = sampler.sample(simple_spec, n_samples=20)
        
        assert np.all(samples >= 0)
        assert np.all(samples <= 1)
    
    def test_meta(self):
        """Test plugin metadata."""
        meta = LHSOptimizedSampler.get_meta()
        
        assert meta.name == "lhs_optimized"
        assert "optimized" in meta.tags


class TestSobolSampler:
    """Tests for Sobol sampler."""
    
    def test_sample_shape(self, simple_spec: ProcessSpec):
        """Test that samples have correct shape."""
        sampler = SobolSampler()
        samples = sampler.sample(simple_spec, n_samples=16)
        
        assert samples.shape == (16, 2)
    
    def test_samples_in_bounds(self, simple_spec: ProcessSpec):
        """Test that samples are in [0, 1]."""
        sampler = SobolSampler()
        samples = sampler.sample(simple_spec, n_samples=16)
        
        assert np.all(samples >= 0)
        assert np.all(samples <= 1)
    
    def test_reproducibility(self, simple_spec: ProcessSpec):
        """Test that seeded samples are reproducible."""
        sampler = SobolSampler()
        
        s1 = sampler.sample(simple_spec, n_samples=8, params={"seed": 42})
        s2 = sampler.sample(simple_spec, n_samples=8, params={"seed": 42})
        
        np.testing.assert_array_equal(s1, s2)


class TestRandomSampler:
    """Tests for random sampler."""
    
    def test_sample_shape(self, simple_spec: ProcessSpec):
        """Test that samples have correct shape."""
        sampler = RandomSampler()
        samples = sampler.sample(simple_spec, n_samples=10)
        
        assert samples.shape == (10, 2)
    
    def test_samples_in_bounds(self, simple_spec: ProcessSpec):
        """Test that samples are in [0, 1]."""
        sampler = RandomSampler()
        samples = sampler.sample(simple_spec, n_samples=50)
        
        assert np.all(samples >= 0)
        assert np.all(samples <= 1)
    
    def test_reproducibility(self, simple_spec: ProcessSpec):
        """Test that seeded samples are reproducible."""
        sampler = RandomSampler()
        
        s1 = sampler.sample(simple_spec, n_samples=10, params={"seed": 123})
        s2 = sampler.sample(simple_spec, n_samples=10, params={"seed": 123})
        
        np.testing.assert_array_equal(s1, s2)
    
    def test_meta(self):
        """Test plugin metadata."""
        meta = RandomSampler.get_meta()
        
        assert meta.name == "random"
        assert "random" in meta.tags





