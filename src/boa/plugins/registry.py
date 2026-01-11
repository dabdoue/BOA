"""
BOA Plugin Registry

Type-safe registry for discovering and managing plugins.
"""

from typing import Dict, List, Optional, Type, TypeVar, Generic
import importlib.metadata
import logging

from boa.plugins.base import (
    Plugin,
    PluginMeta,
    SamplerPlugin,
    ModelPlugin,
    AcquisitionPlugin,
    ConstraintPlugin,
    ObjectiveTransformPlugin,
)


logger = logging.getLogger(__name__)

T = TypeVar("T", bound=Plugin)


class PluginTypeRegistry(Generic[T]):
    """Registry for a specific plugin type."""
    
    def __init__(self, plugin_type: Type[T], entry_point_group: str):
        """
        Initialize registry.
        
        Args:
            plugin_type: Base class for this plugin type
            entry_point_group: Entry point group name for discovery
        """
        self.plugin_type = plugin_type
        self.entry_point_group = entry_point_group
        self._plugins: Dict[str, Type[T]] = {}
        self._discovered = False
    
    def register(self, name: str, plugin_class: Type[T]) -> None:
        """
        Register a plugin.
        
        Args:
            name: Plugin name
            plugin_class: Plugin class
        """
        if not issubclass(plugin_class, self.plugin_type):
            raise TypeError(
                f"Plugin {plugin_class} must be a subclass of {self.plugin_type}"
            )
        self._plugins[name] = plugin_class
        logger.debug(f"Registered {self.plugin_type.__name__}: {name}")
    
    def get(self, name: str) -> Type[T]:
        """
        Get plugin by name.
        
        Args:
            name: Plugin name
            
        Returns:
            Plugin class
            
        Raises:
            KeyError: If plugin not found
        """
        if not self._discovered:
            self.discover()
        
        if name not in self._plugins:
            available = list(self._plugins.keys())
            raise KeyError(
                f"Plugin '{name}' not found. Available: {available}"
            )
        
        return self._plugins[name]
    
    def list(self) -> List[str]:
        """List all registered plugins."""
        if not self._discovered:
            self.discover()
        return list(self._plugins.keys())
    
    def all(self) -> Dict[str, Type[T]]:
        """Get all registered plugins."""
        if not self._discovered:
            self.discover()
        return dict(self._plugins)
    
    def discover(self) -> None:
        """Discover plugins from entry points."""
        if self._discovered:
            return
        
        try:
            eps = importlib.metadata.entry_points(group=self.entry_point_group)
            for ep in eps:
                try:
                    plugin_class = ep.load()
                    self.register(ep.name, plugin_class)
                except Exception as e:
                    logger.warning(
                        f"Failed to load plugin {ep.name} from {ep.value}: {e}"
                    )
        except Exception as e:
            logger.debug(f"No entry points found for {self.entry_point_group}: {e}")
        
        self._discovered = True
    
    def __contains__(self, name: str) -> bool:
        """Check if plugin is registered."""
        if not self._discovered:
            self.discover()
        return name in self._plugins


class PluginRegistry:
    """
    Central registry for all plugin types.
    
    Manages samplers, models, acquisition functions, constraints,
    and objective transforms.
    """
    
    def __init__(self):
        """Initialize registry with all plugin types."""
        self.samplers = PluginTypeRegistry[SamplerPlugin](
            SamplerPlugin, "boa.samplers"
        )
        self.models = PluginTypeRegistry[ModelPlugin](
            ModelPlugin, "boa.models"
        )
        self.acquisitions = PluginTypeRegistry[AcquisitionPlugin](
            AcquisitionPlugin, "boa.acquisitions"
        )
        self.constraints = PluginTypeRegistry[ConstraintPlugin](
            ConstraintPlugin, "boa.constraints"
        )
        self.transforms = PluginTypeRegistry[ObjectiveTransformPlugin](
            ObjectiveTransformPlugin, "boa.transforms"
        )
    
    def register_sampler(self, name: str, plugin: Type[SamplerPlugin]) -> None:
        """Register a sampler plugin."""
        self.samplers.register(name, plugin)
    
    def register_model(self, name: str, plugin: Type[ModelPlugin]) -> None:
        """Register a model plugin."""
        self.models.register(name, plugin)
    
    def register_acquisition(self, name: str, plugin: Type[AcquisitionPlugin]) -> None:
        """Register an acquisition plugin."""
        self.acquisitions.register(name, plugin)
    
    def register_constraint(self, name: str, plugin: Type[ConstraintPlugin]) -> None:
        """Register a constraint plugin."""
        self.constraints.register(name, plugin)
    
    def register_transform(self, name: str, plugin: Type[ObjectiveTransformPlugin]) -> None:
        """Register an objective transform plugin."""
        self.transforms.register(name, plugin)
    
    def get_sampler(self, name: str) -> Type[SamplerPlugin]:
        """Get sampler by name."""
        return self.samplers.get(name)
    
    def get_model(self, name: str) -> Type[ModelPlugin]:
        """Get model by name."""
        return self.models.get(name)
    
    def get_acquisition(self, name: str) -> Type[AcquisitionPlugin]:
        """Get acquisition by name."""
        return self.acquisitions.get(name)
    
    def get_constraint(self, name: str) -> Type[ConstraintPlugin]:
        """Get constraint by name."""
        return self.constraints.get(name)
    
    def get_transform(self, name: str) -> Type[ObjectiveTransformPlugin]:
        """Get transform by name."""
        return self.transforms.get(name)
    
    def discover_all(self) -> None:
        """Discover all plugins from entry points."""
        self.samplers.discover()
        self.models.discover()
        self.acquisitions.discover()
        self.constraints.discover()
        self.transforms.discover()
    
    def register_builtins(self) -> None:
        """Register built-in plugins."""
        # Import here to avoid circular imports
        from boa.plugins.builtin.samplers import (
            LHSSampler,
            LHSOptimizedSampler,
            SobolSampler,
            RandomSampler,
        )
        from boa.plugins.builtin.models import (
            GPMaternModel,
            GPRBFModel,
        )
        from boa.plugins.builtin.acquisitions import (
            QLogNEHVIAcquisition,
            QNEHVIAcquisition,
            QParEGOAcquisition,
            RandomAcquisition,
        )
        from boa.plugins.builtin.constraints import (
            ClausiusClapeyronConstraint,
        )
        
        # Samplers
        self.register_sampler("lhs", LHSSampler)
        self.register_sampler("lhs_optimized", LHSOptimizedSampler)
        self.register_sampler("sobol", SobolSampler)
        self.register_sampler("random", RandomSampler)
        
        # Models
        self.register_model("gp_matern", GPMaternModel)
        self.register_model("gp_rbf", GPRBFModel)
        
        # Acquisitions
        self.register_acquisition("qlogNEHVI", QLogNEHVIAcquisition)
        self.register_acquisition("qNEHVI", QNEHVIAcquisition)
        self.register_acquisition("qParEGO", QParEGOAcquisition)
        self.register_acquisition("random", RandomAcquisition)
        
        # Constraints
        self.register_constraint("clausius_clapeyron", ClausiusClapeyronConstraint)


# Global registry singleton
_registry: Optional[PluginRegistry] = None


def get_registry() -> PluginRegistry:
    """
    Get the global plugin registry.
    
    Initializes with built-in plugins on first call.
    """
    global _registry
    
    if _registry is None:
        _registry = PluginRegistry()
        _registry.register_builtins()
        _registry.discover_all()
    
    return _registry





