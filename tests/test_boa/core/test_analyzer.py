"""
Tests for BOA campaign analyzer.
"""

import numpy as np
import pytest

from boa.db.models import Observation
from boa.spec.models import (
    ProcessSpec,
    ContinuousInput,
    ObjectiveSpec,
    ObjectiveDirection,
)
from boa.core.analyzer import CampaignAnalyzer, CampaignMetrics


def make_observation(x_raw: dict, y: dict) -> Observation:
    """Helper to create observation objects."""
    obs = Observation(
        campaign_id=None,
        x_raw=x_raw,
        y=y,
    )
    return obs


class TestCampaignAnalyzer:
    """Tests for CampaignAnalyzer."""
    
    @pytest.fixture
    def single_obj_spec(self) -> ProcessSpec:
        """Single objective spec."""
        return ProcessSpec(
            name="single",
            inputs=[ContinuousInput(name="x", bounds=(0, 1))],
            objectives=[ObjectiveSpec(name="y", direction=ObjectiveDirection.MAXIMIZE)],
        )
    
    @pytest.fixture
    def multi_obj_spec(self) -> ProcessSpec:
        """Multi-objective spec."""
        return ProcessSpec(
            name="multi",
            inputs=[ContinuousInput(name="x", bounds=(0, 1))],
            objectives=[
                ObjectiveSpec(name="y1", direction=ObjectiveDirection.MAXIMIZE),
                ObjectiveSpec(name="y2", direction=ObjectiveDirection.MINIMIZE),
            ],
        )
    
    def test_empty_observations(self, single_obj_spec: ProcessSpec):
        """Test analyzer with no observations."""
        analyzer = CampaignAnalyzer(single_obj_spec, [])
        
        metrics = analyzer.compute_metrics()
        
        assert metrics.n_observations == 0
        assert np.isnan(metrics.best_values["y"])
        assert metrics.best_observation is None
    
    def test_single_objective_best(self, single_obj_spec: ProcessSpec):
        """Test finding best value for single objective."""
        observations = [
            make_observation({"x": 0.1}, {"y": 1.0}),
            make_observation({"x": 0.5}, {"y": 3.0}),  # Best
            make_observation({"x": 0.9}, {"y": 2.0}),
        ]
        
        analyzer = CampaignAnalyzer(single_obj_spec, observations)
        metrics = analyzer.compute_metrics()
        
        assert metrics.n_observations == 3
        assert metrics.best_values["y"] == 3.0
        assert metrics.best_observation["y"]["y"] == 3.0
    
    def test_minimization_objective(self):
        """Test finding best for minimization objective."""
        spec = ProcessSpec(
            name="min",
            inputs=[ContinuousInput(name="x", bounds=(0, 1))],
            objectives=[ObjectiveSpec(name="y", direction=ObjectiveDirection.MINIMIZE)],
        )
        
        observations = [
            make_observation({"x": 0.1}, {"y": 5.0}),
            make_observation({"x": 0.5}, {"y": 1.0}),  # Best (min)
            make_observation({"x": 0.9}, {"y": 3.0}),
        ]
        
        analyzer = CampaignAnalyzer(spec, observations)
        metrics = analyzer.compute_metrics()
        
        assert metrics.best_values["y"] == 1.0
    
    def test_pareto_front(self, multi_obj_spec: ProcessSpec):
        """Test Pareto front computation."""
        # For y1 maximize, y2 minimize:
        # Create trade-offs where no point dominates another
        observations = [
            make_observation({"x": 0.1}, {"y1": 1.0, "y2": 1.0}),  # low y1, low y2 - Pareto
            make_observation({"x": 0.3}, {"y1": 2.0, "y2": 3.0}),  # Dominated by (3, 2)
            make_observation({"x": 0.5}, {"y1": 3.0, "y2": 2.0}),  # Pareto (trade-off)
            make_observation({"x": 0.9}, {"y1": 4.0, "y2": 4.0}),  # Pareto (highest y1, but high y2)
        ]
        
        analyzer = CampaignAnalyzer(multi_obj_spec, observations)
        pareto_front = analyzer.get_pareto_front()
        
        # Should have 3 Pareto optimal points: (1,1), (3,2), (4,4)
        # (2,3) is dominated by (3,2) because 3>2 and 2<3
        assert len(pareto_front) == 3
        
        # Check they're the right ones
        y1_values = {p["y"]["y1"] for p in pareto_front}
        assert y1_values == {1.0, 3.0, 4.0}
    
    def test_pareto_front_size_in_metrics(self, multi_obj_spec: ProcessSpec):
        """Test Pareto front size is in metrics."""
        # For y1 maximize, y2 minimize:
        # (1, 3): low y1, high y2
        # (2, 2): medium both - Pareto
        # (3, 1): high y1, low y2 - dominates all (best in both)
        # Actually (3,1) dominates both others, so only 1 Pareto point
        # Let's create actual trade-offs:
        observations = [
            make_observation({"x": 0.1}, {"y1": 1.0, "y2": 1.0}),  # Pareto: low y1, but best y2
            make_observation({"x": 0.5}, {"y1": 2.0, "y2": 2.0}),  # Pareto: middle trade-off
            make_observation({"x": 0.9}, {"y1": 3.0, "y2": 3.0}),  # Pareto: best y1, but worst y2
        ]
        
        analyzer = CampaignAnalyzer(multi_obj_spec, observations)
        metrics = analyzer.compute_metrics()
        
        # All three form Pareto front (each is best in one objective)
        assert metrics.pareto_front_size == 3
    
    def test_improvement_history_single(self, single_obj_spec: ProcessSpec):
        """Test improvement history for single objective."""
        observations = [
            make_observation({"x": 0.1}, {"y": 1.0}),
            make_observation({"x": 0.2}, {"y": 0.5}),  # Worse
            make_observation({"x": 0.3}, {"y": 2.0}),  # New best
            make_observation({"x": 0.4}, {"y": 1.5}),  # Still 2.0 is best
        ]
        
        analyzer = CampaignAnalyzer(single_obj_spec, observations)
        metrics = analyzer.compute_metrics()
        
        history = metrics.improvement_history
        
        assert len(history) == 4
        assert history[0] == 1.0
        assert history[1] == 1.0  # Still 1.0
        assert history[2] == 2.0  # New best
        assert history[3] == 2.0  # Still 2.0
    
    def test_objective_bounds(self, single_obj_spec: ProcessSpec):
        """Test objective bounds computation."""
        observations = [
            make_observation({"x": 0.1}, {"y": 1.0}),
            make_observation({"x": 0.5}, {"y": 5.0}),
            make_observation({"x": 0.9}, {"y": 3.0}),
        ]
        
        analyzer = CampaignAnalyzer(single_obj_spec, observations)
        metrics = analyzer.compute_metrics()
        
        assert metrics.objective_bounds["y"] == (1.0, 5.0)
    
    def test_hypervolume_computation(self, multi_obj_spec: ProcessSpec):
        """Test hypervolume computation."""
        observations = [
            make_observation({"x": 0.1}, {"y1": 1.0, "y2": 3.0}),
            make_observation({"x": 0.5}, {"y1": 2.0, "y2": 2.0}),
            make_observation({"x": 0.9}, {"y1": 3.0, "y2": 1.0}),
        ]
        
        ref_point = np.array([0.0, 4.0])  # y1: below all, y2: above all (to be minimized)
        
        analyzer = CampaignAnalyzer(multi_obj_spec, observations, ref_point)
        metrics = analyzer.compute_metrics()
        
        # Should have non-zero hypervolume
        assert metrics.hypervolume is not None
        assert metrics.hypervolume > 0

