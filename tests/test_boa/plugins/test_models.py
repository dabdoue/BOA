"""
Tests for BOA built-in models.

Tests GP models with different kernels.
"""

import pytest
import torch

from boa.plugins.builtin.models import GPMaternModel, GPRBFModel


class TestGPMaternModel:
    """Tests for GP Matern model."""
    
    @pytest.fixture
    def training_data(self):
        """Create synthetic training data."""
        torch.manual_seed(42)
        X = torch.rand(20, 2)
        Y = torch.sin(X[:, 0:1] * 3) + torch.cos(X[:, 1:2] * 2) + 0.1 * torch.randn(20, 1)
        return X, Y
    
    def test_fit(self, training_data):
        """Test fitting GP model."""
        X, Y = training_data
        
        model_plugin = GPMaternModel()
        model = model_plugin.fit(X, Y)
        
        assert model is not None
        # Model should have been fitted
        assert hasattr(model, "posterior")
    
    def test_predict(self, training_data):
        """Test prediction with GP model."""
        X, Y = training_data
        
        model_plugin = GPMaternModel()
        model = model_plugin.fit(X, Y)
        
        # Predict at new points
        X_test = torch.rand(5, 2)
        posterior = model.posterior(X_test)
        
        mean = posterior.mean
        var = posterior.variance
        
        assert mean.shape == (5, 1)
        assert var.shape == (5, 1)
        assert torch.all(var >= 0)
    
    def test_save_load(self, training_data):
        """Test saving and loading model."""
        X, Y = training_data
        
        model_plugin = GPMaternModel()
        model = model_plugin.fit(X, Y)
        
        # Save
        state_dict = model_plugin.save(model)
        
        # Load
        loaded_model = model_plugin.load(state_dict, X, Y)
        
        # Predictions should match
        X_test = torch.rand(3, 2)
        orig_pred = model.posterior(X_test).mean
        loaded_pred = loaded_model.posterior(X_test).mean
        
        torch.testing.assert_close(orig_pred, loaded_pred, rtol=1e-4, atol=1e-4)
    
    def test_meta(self):
        """Test plugin metadata."""
        meta = GPMaternModel.get_meta()
        
        assert meta.name == "gp_matern"
        assert "gp" in meta.tags
        assert "matern" in meta.tags


class TestGPRBFModel:
    """Tests for GP RBF model."""
    
    @pytest.fixture
    def training_data(self):
        """Create synthetic training data."""
        torch.manual_seed(42)
        X = torch.rand(20, 2)
        Y = torch.sin(X[:, 0:1] * 3) + torch.cos(X[:, 1:2] * 2) + 0.1 * torch.randn(20, 1)
        return X, Y
    
    def test_fit(self, training_data):
        """Test fitting GP RBF model."""
        X, Y = training_data
        
        model_plugin = GPRBFModel()
        model = model_plugin.fit(X, Y)
        
        assert model is not None
        assert hasattr(model, "posterior")
    
    def test_predict(self, training_data):
        """Test prediction with GP RBF model."""
        X, Y = training_data
        
        model_plugin = GPRBFModel()
        model = model_plugin.fit(X, Y)
        
        X_test = torch.rand(5, 2)
        posterior = model.posterior(X_test)
        
        mean = posterior.mean
        var = posterior.variance
        
        assert mean.shape == (5, 1)
        assert var.shape == (5, 1)
    
    def test_meta(self):
        """Test plugin metadata."""
        meta = GPRBFModel.get_meta()
        
        assert meta.name == "gp_rbf"
        assert "rbf" in meta.tags


class TestMultiOutputModels:
    """Tests for multi-output GP models."""
    
    @pytest.fixture
    def multi_output_data(self):
        """Create multi-output training data."""
        torch.manual_seed(42)
        X = torch.rand(25, 3)
        Y = torch.stack([
            torch.sin(X[:, 0] * 3) + 0.1 * torch.randn(25),
            torch.cos(X[:, 1] * 2) + 0.1 * torch.randn(25),
        ], dim=-1)
        return X, Y
    
    def test_matern_multi_output(self, multi_output_data):
        """Test Matern GP with multiple outputs."""
        X, Y = multi_output_data
        
        model_plugin = GPMaternModel()
        model = model_plugin.fit(X, Y)
        
        X_test = torch.rand(5, 3)
        posterior = model.posterior(X_test)
        
        mean = posterior.mean
        assert mean.shape == (5, 2)
    
    def test_rbf_multi_output(self, multi_output_data):
        """Test RBF GP with multiple outputs."""
        X, Y = multi_output_data
        
        model_plugin = GPRBFModel()
        model = model_plugin.fit(X, Y)
        
        X_test = torch.rand(5, 3)
        posterior = model.posterior(X_test)
        
        mean = posterior.mean
        assert mean.shape == (5, 2)





