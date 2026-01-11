"""
Tests for BOA plugin registry.

Tests plugin registration, discovery, and retrieval.
"""

import pytest

from boa.plugins.registry import PluginRegistry, get_registry, PluginTypeRegistry
from boa.plugins.base import (
    SamplerPlugin,
    ModelPlugin,
    AcquisitionPlugin,
    ConstraintPlugin,
    PluginMeta,
)


class TestPluginTypeRegistry:
    """Tests for PluginTypeRegistry."""
    
    def test_register_plugin(self):
        """Test registering a plugin."""
        registry = PluginTypeRegistry[SamplerPlugin](
            SamplerPlugin, "test.samplers"
        )
        
        # Create a mock plugin
        class MockSampler(SamplerPlugin):
            @classmethod
            def get_meta(cls) -> PluginMeta:
                return PluginMeta(name="mock")
            
            def sample(self, spec, n_samples, params=None):
                return None
            
            def sample_raw(self, spec, n_samples, params=None):
                return []
        
        registry.register("mock", MockSampler)
        
        assert "mock" in registry
        assert registry.get("mock") is MockSampler
    
    def test_get_missing_plugin(self):
        """Test getting a missing plugin raises KeyError."""
        registry = PluginTypeRegistry[SamplerPlugin](
            SamplerPlugin, "test.samplers"
        )
        registry._discovered = True  # Skip discovery
        
        with pytest.raises(KeyError, match="not found"):
            registry.get("nonexistent")
    
    def test_list_plugins(self):
        """Test listing registered plugins."""
        registry = PluginTypeRegistry[SamplerPlugin](
            SamplerPlugin, "test.samplers"
        )
        registry._discovered = True
        
        class MockSampler1(SamplerPlugin):
            @classmethod
            def get_meta(cls):
                return PluginMeta(name="mock1")
            def sample(self, spec, n_samples, params=None):
                return None
            def sample_raw(self, spec, n_samples, params=None):
                return []
        
        class MockSampler2(SamplerPlugin):
            @classmethod
            def get_meta(cls):
                return PluginMeta(name="mock2")
            def sample(self, spec, n_samples, params=None):
                return None
            def sample_raw(self, spec, n_samples, params=None):
                return []
        
        registry.register("mock1", MockSampler1)
        registry.register("mock2", MockSampler2)
        
        plugins = registry.list()
        assert "mock1" in plugins
        assert "mock2" in plugins


class TestPluginRegistry:
    """Tests for the main PluginRegistry."""
    
    @pytest.fixture
    def registry(self) -> PluginRegistry:
        """Create a fresh registry with builtins."""
        reg = PluginRegistry()
        reg.register_builtins()
        return reg
    
    def test_builtin_samplers(self, registry: PluginRegistry):
        """Test built-in samplers are registered."""
        assert "lhs" in registry.samplers
        assert "lhs_optimized" in registry.samplers
        assert "sobol" in registry.samplers
        assert "random" in registry.samplers
    
    def test_builtin_models(self, registry: PluginRegistry):
        """Test built-in models are registered."""
        assert "gp_matern" in registry.models
        assert "gp_rbf" in registry.models
    
    def test_builtin_acquisitions(self, registry: PluginRegistry):
        """Test built-in acquisitions are registered."""
        assert "qlogNEHVI" in registry.acquisitions
        assert "qNEHVI" in registry.acquisitions
        assert "qParEGO" in registry.acquisitions
        assert "random" in registry.acquisitions
    
    def test_builtin_constraints(self, registry: PluginRegistry):
        """Test built-in constraints are registered."""
        assert "clausius_clapeyron" in registry.constraints
    
    def test_get_sampler(self, registry: PluginRegistry):
        """Test getting a sampler."""
        sampler_cls = registry.get_sampler("lhs")
        assert sampler_cls is not None
        
        meta = sampler_cls.get_meta()
        assert meta.name == "lhs"
    
    def test_get_model(self, registry: PluginRegistry):
        """Test getting a model."""
        model_cls = registry.get_model("gp_matern")
        assert model_cls is not None
        
        meta = model_cls.get_meta()
        assert meta.name == "gp_matern"


class TestGlobalRegistry:
    """Tests for global registry singleton."""
    
    def test_get_registry(self):
        """Test getting the global registry."""
        registry = get_registry()
        
        assert registry is not None
        assert "lhs" in registry.samplers
        assert "gp_matern" in registry.models
    
    def test_registry_singleton(self):
        """Test that get_registry returns same instance."""
        reg1 = get_registry()
        reg2 = get_registry()
        
        assert reg1 is reg2





