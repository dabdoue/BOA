"""
BOA Specification Models

Pydantic models for defining optimization problems including:
- Process specifications (inputs, objectives, constraints, strategies)
- Mixed + conditional variable spaces
- Preference objectives
- YAML loading and validation
"""

from boa.spec.models import (
    ProcessSpec,
    InputSpec,
    ContinuousInput,
    DiscreteInput,
    CategoricalInput,
    ObjectiveSpec,
    PreferenceSpec,
    InputConstraintSpec,
    OutcomeConstraintSpec,
    StrategySpec,
    InputType,
    ObjectiveDirection,
    PreferenceType,
)
from boa.spec.encoder import MixedSpaceEncoder
from boa.spec.loader import load_process_spec, load_process_spec_from_file
from boa.spec.validators import validate_process_spec

__all__ = [
    # Models
    "ProcessSpec",
    "InputSpec",
    "ContinuousInput",
    "DiscreteInput",
    "CategoricalInput",
    "ObjectiveSpec",
    "PreferenceSpec",
    "InputConstraintSpec",
    "OutcomeConstraintSpec",
    "StrategySpec",
    # Enums
    "InputType",
    "ObjectiveDirection",
    "PreferenceType",
    # Encoder
    "MixedSpaceEncoder",
    # Loader
    "load_process_spec",
    "load_process_spec_from_file",
    # Validators
    "validate_process_spec",
]





