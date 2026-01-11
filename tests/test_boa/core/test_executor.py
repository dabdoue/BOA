"""
Tests for BOA strategy executor.
"""

import numpy as np
import pytest

from boa.core.executor import StrategyExecutor, ExecutionResult
from boa.spec.models import (
    ProcessSpec,
    ContinuousInput,
    ObjectiveSpec,
    StrategySpec,
)


@pytest.fixture
def simple_spec() -> ProcessSpec:
    """Simple ProcessSpec for testing."""
    return ProcessSpec(
        name="test",
        inputs=[
            ContinuousInput(name="x1", bounds=(0, 10)),
            ContinuousInput(name="x2", bounds=(-5, 5)),
        ],
        objectives=[
            ObjectiveSpec(name="y"),
        ],
        strategies={
            "default": StrategySpec(
                name="default",
                sampler="lhs_optimized",
                model="gp_matern",
                acquisition="random",  # Use random for faster tests
            ),
        },
    )


@pytest.fixture
def strategy() -> StrategySpec:
    """Default strategy for testing."""
    return StrategySpec(
        name="default",
        sampler="lhs_optimized",
        model="gp_matern",
        acquisition="random",
    )


class TestStrategyExecutor:
    """Tests for StrategyExecutor."""
    
    def test_initial_design(self, simple_spec: ProcessSpec, strategy: StrategySpec):
        """Test generating initial design."""
        executor = StrategyExecutor(simple_spec, strategy)
        
        result = executor.execute_initial_design(n_samples=10)
        
        assert isinstance(result, ExecutionResult)
        assert result.strategy_name == "default"
        assert result.candidates_encoded.shape == (10, 2)
        assert len(result.candidates_raw) == 10
        assert result.metadata["phase"] == "initial_design"
    
    def test_initial_design_values_in_bounds(
        self, simple_spec: ProcessSpec, strategy: StrategySpec
    ):
        """Test that initial design values are within bounds."""
        executor = StrategyExecutor(simple_spec, strategy)
        
        result = executor.execute_initial_design(n_samples=20)
        
        # Encoded should be in [0, 1]
        assert np.all(result.candidates_encoded >= 0)
        assert np.all(result.candidates_encoded <= 1)
        
        # Raw should be in original bounds
        for candidate in result.candidates_raw:
            assert 0 <= candidate["x1"] <= 10
            assert -5 <= candidate["x2"] <= 5
    
    def test_optimization_iteration(
        self, simple_spec: ProcessSpec, strategy: StrategySpec
    ):
        """Test running optimization iteration."""
        executor = StrategyExecutor(simple_spec, strategy)
        
        # Create synthetic training data
        np.random.seed(42)
        X = np.random.rand(15, 2)
        Y = np.sin(X[:, 0:1] * 3) + X[:, 1:2] * 0.5
        
        result = executor.execute_optimization(X, Y, n_candidates=3)
        
        assert isinstance(result, ExecutionResult)
        assert result.candidates_encoded.shape == (3, 2)
        assert len(result.candidates_raw) == 3
        assert result.metadata["phase"] == "optimization"
    
    def test_optimization_with_ref_point(
        self, simple_spec: ProcessSpec, strategy: StrategySpec
    ):
        """Test optimization with explicit reference point."""
        executor = StrategyExecutor(simple_spec, strategy)
        
        X = np.random.rand(10, 2)
        Y = np.random.rand(10, 1)
        
        ref_point = np.array([-1.0])
        result = executor.execute_optimization(X, Y, n_candidates=2, ref_point=ref_point)
        
        assert result.candidates_encoded.shape == (2, 2)


class TestMultiObjectiveExecutor:
    """Tests for multi-objective optimization."""
    
    @pytest.fixture
    def multi_obj_spec(self) -> ProcessSpec:
        """Multi-objective spec."""
        return ProcessSpec(
            name="multi_obj",
            inputs=[
                ContinuousInput(name="x", bounds=(0, 1)),
            ],
            objectives=[
                ObjectiveSpec(name="y1"),
                ObjectiveSpec(name="y2"),
            ],
        )
    
    @pytest.fixture
    def multi_strategy(self) -> StrategySpec:
        """Strategy for multi-objective."""
        return StrategySpec(
            name="multi",
            sampler="random",
            model="gp_matern",
            acquisition="random",
        )
    
    def test_multi_objective_optimization(
        self, multi_obj_spec: ProcessSpec, multi_strategy: StrategySpec
    ):
        """Test multi-objective optimization."""
        executor = StrategyExecutor(multi_obj_spec, multi_strategy)
        
        X = np.random.rand(20, 1)
        Y = np.column_stack([
            np.sin(X[:, 0] * 3),
            np.cos(X[:, 0] * 2),
        ])
        
        result = executor.execute_optimization(X, Y, n_candidates=2)
        
        assert result.candidates_encoded.shape == (2, 1)
        assert len(result.candidates_raw) == 2





