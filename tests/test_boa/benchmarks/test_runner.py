"""
Tests for BOA benchmark runner.
"""

import pytest

from boa.benchmarks import DTLZ2, ZDT1, BenchmarkRunner, BenchmarkResult
from boa.benchmarks.runner import RunConfig
from boa.spec.models import StrategySpec


class TestBenchmarkRunner:
    """Tests for BenchmarkRunner."""
    
    @pytest.fixture
    def simple_benchmark(self):
        """Create a simple benchmark for fast tests."""
        return DTLZ2(n_var=4, n_obj=2)
    
    @pytest.fixture
    def fast_strategy(self) -> StrategySpec:
        """Create a fast strategy for testing."""
        return StrategySpec(
            name="random",
            sampler="random",
            model="gp_matern",
            acquisition="random",
        )
    
    def test_runner_creation(self, simple_benchmark):
        """Test creating a runner."""
        runner = BenchmarkRunner(simple_benchmark)
        
        assert runner.benchmark is simple_benchmark
        assert runner.spec is not None
        assert runner.spec.name == "DTLZ2"
    
    def test_run_benchmark(self, simple_benchmark, fast_strategy):
        """Test running a benchmark."""
        runner = BenchmarkRunner(simple_benchmark)
        
        result = runner.run(
            strategy=fast_strategy,
            config=RunConfig(
                n_initial=5,
                n_iterations=3,
                n_candidates=1,
                seed=42,
            ),
        )
        
        assert isinstance(result, BenchmarkResult)
        assert result.benchmark_name == "DTLZ2"
        assert result.strategy_name == "random"
        assert result.n_iterations == 3
        assert result.n_observations == 5 + 3  # initial + iterations
    
    def test_hypervolume_history(self, simple_benchmark, fast_strategy):
        """Test hypervolume is tracked."""
        runner = BenchmarkRunner(simple_benchmark)
        
        result = runner.run(
            strategy=fast_strategy,
            config=RunConfig(n_initial=5, n_iterations=3, seed=42),
        )
        
        assert len(result.hypervolume_history) == 4  # iterations + final
        assert result.final_hypervolume is not None
    
    def test_result_summary(self, simple_benchmark, fast_strategy):
        """Test result summary string."""
        runner = BenchmarkRunner(simple_benchmark)
        
        result = runner.run(
            strategy=fast_strategy,
            config=RunConfig(n_initial=5, n_iterations=2, seed=42),
        )
        
        summary = result.summary()
        
        assert "DTLZ2" in summary
        assert "random" in summary
        assert "HV=" in summary


class TestZDTBenchmarkRunner:
    """Tests for running ZDT benchmarks."""
    
    def test_zdt1_run(self):
        """Test running ZDT1 benchmark."""
        benchmark = ZDT1(n_var=5)
        runner = BenchmarkRunner(benchmark)
        
        strategy = StrategySpec(
            name="random",
            sampler="random",
            model="gp_matern",
            acquisition="random",
        )
        
        result = runner.run(
            strategy=strategy,
            config=RunConfig(n_initial=5, n_iterations=2, seed=42),
        )
        
        assert result.benchmark_name == "ZDT1"
        assert result.n_observations == 7





