"""
BOA Plugin System

Extensible plugin architecture for samplers, models, acquisition functions,
constraints, and objective transforms.
"""

from boa.plugins.base import (
    Plugin,
    PluginMeta,
    SamplerPlugin,
    ModelPlugin,
    AcquisitionPlugin,
    ConstraintPlugin,
    ObjectiveTransformPlugin,
)
from boa.plugins.registry import (
    PluginRegistry,
    get_registry,
)

__all__ = [
    # Base classes
    "Plugin",
    "PluginMeta",
    "SamplerPlugin",
    "ModelPlugin",
    "AcquisitionPlugin",
    "ConstraintPlugin",
    "ObjectiveTransformPlugin",
    # Registry
    "PluginRegistry",
    "get_registry",
]





