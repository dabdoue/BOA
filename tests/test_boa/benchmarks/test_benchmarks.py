"""
Tests for BOA benchmarks.
"""

import numpy as np
import pytest

from boa.benchmarks import (
    Benchmark,
    BenchmarkResult,
    DTLZ1,
    DTLZ2,
    DTLZ3,
    DTLZ4,
    ZDT1,
    ZDT2,
    ZDT3,
)


class TestDTLZBenchmarks:
    """Tests for DTLZ benchmarks."""
    
    def test_dtlz1_properties(self):
        """Test DTLZ1 properties."""
        benchmark = DTLZ1(n_var=7, n_obj=3)
        
        assert benchmark.n_var == 7
        assert benchmark.n_obj == 3
        assert benchmark.bounds.shape == (7, 2)
        assert benchmark.ref_point.shape == (3,)
    
    def test_dtlz1_evaluate(self):
        """Test DTLZ1 evaluation."""
        benchmark = DTLZ1(n_var=7, n_obj=3)
        
        X = np.random.rand(10, 7)
        Y = benchmark.evaluate(X)
        
        assert Y.shape == (10, 3)
        assert np.all(Y >= 0)
    
    def test_dtlz1_pareto_front(self):
        """Test DTLZ1 Pareto front."""
        benchmark = DTLZ1(n_var=7, n_obj=3)
        
        pf = benchmark.get_pareto_front(n_points=100)
        
        assert pf.shape == (100, 3)
        # Points should sum to ~0.5
        np.testing.assert_allclose(pf.sum(axis=1), 0.5, rtol=0.01)
    
    def test_dtlz2_evaluate(self):
        """Test DTLZ2 evaluation."""
        benchmark = DTLZ2(n_var=12, n_obj=3)
        
        X = np.random.rand(10, 12)
        Y = benchmark.evaluate(X)
        
        assert Y.shape == (10, 3)
        assert np.all(Y >= 0)
    
    def test_dtlz2_pareto_front(self):
        """Test DTLZ2 Pareto front."""
        benchmark = DTLZ2(n_var=12, n_obj=3)
        
        pf = benchmark.get_pareto_front(n_points=100)
        
        assert pf.shape == (100, 3)
        # Points should have norm ~1
        norms = np.linalg.norm(pf, axis=1)
        np.testing.assert_allclose(norms, 1.0, rtol=0.1)
    
    def test_dtlz3_evaluate(self):
        """Test DTLZ3 evaluation."""
        benchmark = DTLZ3(n_var=12, n_obj=3)
        
        X = np.random.rand(10, 12)
        Y = benchmark.evaluate(X)
        
        assert Y.shape == (10, 3)
    
    def test_dtlz4_evaluate(self):
        """Test DTLZ4 evaluation."""
        benchmark = DTLZ4(n_var=12, n_obj=3)
        
        X = np.random.rand(10, 12)
        Y = benchmark.evaluate(X)
        
        assert Y.shape == (10, 3)


class TestZDTBenchmarks:
    """Tests for ZDT benchmarks."""
    
    def test_zdt1_properties(self):
        """Test ZDT1 properties."""
        benchmark = ZDT1(n_var=30)
        
        assert benchmark.n_var == 30
        assert benchmark.n_obj == 2
    
    def test_zdt1_evaluate(self):
        """Test ZDT1 evaluation."""
        benchmark = ZDT1(n_var=30)
        
        X = np.random.rand(10, 30)
        Y = benchmark.evaluate(X)
        
        assert Y.shape == (10, 2)
        assert np.all(Y >= 0)
    
    def test_zdt1_pareto_front(self):
        """Test ZDT1 Pareto front."""
        benchmark = ZDT1(n_var=30)
        
        pf = benchmark.get_pareto_front(n_points=100)
        
        assert pf.shape == (100, 2)
        # f2 = 1 - sqrt(f1)
        expected_f2 = 1 - np.sqrt(pf[:, 0])
        np.testing.assert_allclose(pf[:, 1], expected_f2, rtol=0.01)
    
    def test_zdt2_evaluate(self):
        """Test ZDT2 evaluation."""
        benchmark = ZDT2(n_var=30)
        
        X = np.random.rand(10, 30)
        Y = benchmark.evaluate(X)
        
        assert Y.shape == (10, 2)
    
    def test_zdt2_pareto_front(self):
        """Test ZDT2 Pareto front."""
        benchmark = ZDT2(n_var=30)
        
        pf = benchmark.get_pareto_front(n_points=100)
        
        assert pf.shape == (100, 2)
        # f2 = 1 - f1^2
        expected_f2 = 1 - pf[:, 0] ** 2
        np.testing.assert_allclose(pf[:, 1], expected_f2, rtol=0.01)
    
    def test_zdt3_evaluate(self):
        """Test ZDT3 evaluation."""
        benchmark = ZDT3(n_var=30)
        
        X = np.random.rand(10, 30)
        Y = benchmark.evaluate(X)
        
        assert Y.shape == (10, 2)
    
    def test_zdt3_pareto_front(self):
        """Test ZDT3 Pareto front (disconnected)."""
        benchmark = ZDT3(n_var=30)
        
        pf = benchmark.get_pareto_front(n_points=1000)
        
        assert pf.shape[1] == 2
        # Should have multiple disconnected segments
        assert len(pf) > 100


class TestBenchmarkBase:
    """Tests for Benchmark base class."""
    
    def test_to_spec_yaml(self):
        """Test generating YAML spec."""
        benchmark = DTLZ2(n_var=6, n_obj=2)
        
        yaml_str = benchmark.to_spec_yaml()
        
        assert "name: DTLZ2" in yaml_str
        assert "x1" in yaml_str
        assert "y1" in yaml_str
    
    def test_sample_inputs(self):
        """Test sampling inputs."""
        benchmark = DTLZ2(n_var=6, n_obj=2)
        
        samples = benchmark.sample_inputs(10, seed=42)
        
        assert samples.shape == (10, 6)
        assert np.all(samples >= 0)
        assert np.all(samples <= 1)
    
    def test_evaluate_single(self):
        """Test evaluating single point."""
        benchmark = ZDT1(n_var=5)
        
        x = np.random.rand(5)
        y = benchmark.evaluate_single(x)
        
        assert y.shape == (2,)





