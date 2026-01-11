"""
BOA Specification Models

Pydantic v2 models for defining optimization problems with:
- Continuous, discrete, and categorical inputs
- Conditional variable dependencies (active_if)
- Objective preferences (weights, aspirations, reference points)
- Input and outcome constraints
- Strategy configurations
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator


# =============================================================================
# Enums
# =============================================================================


class InputType(str, Enum):
    """Variable input types."""
    CONTINUOUS = "continuous"
    DISCRETE = "discrete"
    CATEGORICAL = "categorical"


class ObjectiveDirection(str, Enum):
    """Optimization direction."""
    MAXIMIZE = "maximize"
    MINIMIZE = "minimize"


class PreferenceType(str, Enum):
    """Preference specification types."""
    WEIGHT = "weight"
    ASPIRATION = "aspiration"
    REFERENCE_POINT = "reference_point"


# =============================================================================
# Input Specifications
# =============================================================================


class ActiveIfCondition(BaseModel):
    """Condition for conditional variable activation."""
    
    variable: str = Field(description="Name of the variable to check")
    values: List[Any] = Field(description="Values that activate this variable")


class ContinuousInput(BaseModel):
    """Continuous input variable specification."""
    
    name: str = Field(description="Variable name")
    type: InputType = Field(default=InputType.CONTINUOUS)
    bounds: tuple[float, float] = Field(description="(min, max) bounds")
    unit: Optional[str] = Field(default=None, description="Physical unit")
    description: Optional[str] = Field(default=None)
    active_if: Optional[Dict[str, List[Any]]] = Field(
        default=None,
        description="Conditional activation: {variable: [values]}",
    )
    
    @field_validator("bounds")
    @classmethod
    def validate_bounds(cls, v: tuple[float, float]) -> tuple[float, float]:
        if len(v) != 2:
            raise ValueError("bounds must be a tuple of (min, max)")
        if v[0] >= v[1]:
            raise ValueError(f"bounds min ({v[0]}) must be less than max ({v[1]})")
        return v
    
    @property
    def is_conditional(self) -> bool:
        return self.active_if is not None


class DiscreteInput(BaseModel):
    """Discrete input variable specification (grid values)."""
    
    name: str = Field(description="Variable name")
    type: InputType = Field(default=InputType.DISCRETE)
    values: List[float] = Field(description="Allowed discrete values")
    unit: Optional[str] = Field(default=None, description="Physical unit")
    description: Optional[str] = Field(default=None)
    active_if: Optional[Dict[str, List[Any]]] = Field(default=None)
    
    # Alternative specification: start, stop, step
    start: Optional[float] = Field(default=None)
    stop: Optional[float] = Field(default=None)
    step: Optional[float] = Field(default=None)
    
    @model_validator(mode="after")
    def validate_values_or_range(self) -> "DiscreteInput":
        # If start/stop/step provided, generate values
        if self.start is not None and self.stop is not None:
            step = self.step or 1.0
            import numpy as np
            self.values = list(np.arange(self.start, self.stop + step/2, step))
        
        if not self.values:
            raise ValueError("DiscreteInput must have values or start/stop/step")
        
        return self
    
    @property
    def bounds(self) -> tuple[float, float]:
        return (min(self.values), max(self.values))
    
    @property
    def is_conditional(self) -> bool:
        return self.active_if is not None


class CategoricalInput(BaseModel):
    """Categorical input variable specification."""
    
    name: str = Field(description="Variable name")
    type: InputType = Field(default=InputType.CATEGORICAL)
    categories: List[str] = Field(description="Category names")
    description: Optional[str] = Field(default=None)
    active_if: Optional[Dict[str, List[Any]]] = Field(default=None)
    
    @field_validator("categories")
    @classmethod
    def validate_categories(cls, v: List[str]) -> List[str]:
        if len(v) < 2:
            raise ValueError("CategoricalInput must have at least 2 categories")
        if len(v) != len(set(v)):
            raise ValueError("Category names must be unique")
        return v
    
    @property
    def is_conditional(self) -> bool:
        return self.active_if is not None


# Union type for all input types
InputSpec = Union[ContinuousInput, DiscreteInput, CategoricalInput]


# =============================================================================
# Objective Specifications
# =============================================================================


class PreferenceSpec(BaseModel):
    """Preference specification for an objective."""
    
    type: PreferenceType = Field(description="Type of preference")
    value: float = Field(description="Preference value (weight, target, reference)")
    
    @field_validator("value")
    @classmethod
    def validate_value(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Preference value must be positive")
        return v


class ObjectiveSpec(BaseModel):
    """Objective specification with optional preferences."""
    
    name: str = Field(description="Objective name")
    direction: ObjectiveDirection = Field(
        default=ObjectiveDirection.MAXIMIZE,
        description="Optimization direction",
    )
    preference: Optional[PreferenceSpec] = Field(
        default=None,
        description="Optional preference specification",
    )
    description: Optional[str] = Field(default=None)
    
    @property
    def is_maximization(self) -> bool:
        return self.direction == ObjectiveDirection.MAXIMIZE


# =============================================================================
# Constraint Specifications
# =============================================================================


class InputConstraintSpec(BaseModel):
    """Input space constraint specification."""
    
    type: str = Field(description="Constraint type (e.g., clausius_clapeyron)")
    params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Constraint-specific parameters",
    )
    
    # Common constraint parameters
    absolute_humidity_col: Optional[str] = Field(default=None)
    temperature_col: Optional[str] = Field(default=None)


class OutcomeConstraintSpec(BaseModel):
    """Outcome/objective constraint specification."""
    
    type: str = Field(default="threshold", description="Constraint type")
    objective: str = Field(description="Objective name to constrain")
    operator: str = Field(description="Comparison operator (>=, <=, >, <)")
    value: float = Field(description="Threshold value")
    
    @field_validator("operator")
    @classmethod
    def validate_operator(cls, v: str) -> str:
        valid = {">=", "<=", ">", "<", "==", "!="}
        if v not in valid:
            raise ValueError(f"operator must be one of {valid}")
        return v


class ConstraintsSpec(BaseModel):
    """Combined constraints specification."""
    
    input: List[InputConstraintSpec] = Field(default_factory=list)
    outcome: List[OutcomeConstraintSpec] = Field(default_factory=list)


# =============================================================================
# Strategy Specifications
# =============================================================================


class StrategySpec(BaseModel):
    """Optimization strategy configuration."""
    
    name: str = Field(description="Strategy name")
    sampler: str = Field(default="lhs_optimized", description="Initial sampler")
    model: str = Field(default="gp_matern", description="Surrogate model")
    acquisition: str = Field(default="qlogNEHVI", description="Acquisition function")
    sampler_params: Dict[str, Any] = Field(default_factory=dict)
    model_params: Dict[str, Any] = Field(default_factory=dict)
    acquisition_params: Dict[str, Any] = Field(default_factory=dict)
    description: Optional[str] = Field(default=None)


# =============================================================================
# Process Specification
# =============================================================================


class ProcessSpec(BaseModel):
    """
    Complete process specification for optimization.
    
    Defines the full optimization problem including:
    - Input variables (continuous, discrete, categorical)
    - Conditional dependencies
    - Objectives with preferences
    - Constraints (input and outcome)
    - Strategy configurations
    """
    
    name: str = Field(description="Process name")
    version: int = Field(default=1, ge=1, description="Spec version")
    description: Optional[str] = Field(default=None)
    
    inputs: List[InputSpec] = Field(
        description="Input variable specifications",
    )
    objectives: List[ObjectiveSpec] = Field(
        description="Objective specifications",
    )
    constraints: ConstraintsSpec = Field(
        default_factory=ConstraintsSpec,
        description="Constraint specifications",
    )
    strategies: Dict[str, StrategySpec] = Field(
        default_factory=dict,
        description="Strategy configurations by name",
    )
    
    # Metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )
    
    @field_validator("inputs")
    @classmethod
    def validate_inputs(cls, v: List[InputSpec]) -> List[InputSpec]:
        if not v:
            raise ValueError("At least one input is required")
        names = [inp.name for inp in v]
        if len(names) != len(set(names)):
            raise ValueError("Input names must be unique")
        return v
    
    @field_validator("objectives")
    @classmethod
    def validate_objectives(cls, v: List[ObjectiveSpec]) -> List[ObjectiveSpec]:
        if not v:
            raise ValueError("At least one objective is required")
        names = [obj.name for obj in v]
        if len(names) != len(set(names)):
            raise ValueError("Objective names must be unique")
        return v
    
    @model_validator(mode="after")
    def validate_conditional_references(self) -> "ProcessSpec":
        """Validate that active_if references exist."""
        input_names = {inp.name for inp in self.inputs}
        
        for inp in self.inputs:
            if inp.active_if:
                for ref_var in inp.active_if.keys():
                    if ref_var not in input_names:
                        raise ValueError(
                            f"Input '{inp.name}' has active_if reference to "
                            f"unknown variable '{ref_var}'"
                        )
                    # Check that reference is to a categorical variable
                    ref_input = next(i for i in self.inputs if i.name == ref_var)
                    if not isinstance(ref_input, CategoricalInput):
                        raise ValueError(
                            f"active_if can only reference categorical variables, "
                            f"but '{ref_var}' is {type(ref_input).__name__}"
                        )
        
        return self
    
    @model_validator(mode="after")
    def validate_outcome_constraint_references(self) -> "ProcessSpec":
        """Validate that outcome constraints reference existing objectives."""
        objective_names = {obj.name for obj in self.objectives}
        
        for constraint in self.constraints.outcome:
            if constraint.objective not in objective_names:
                raise ValueError(
                    f"Outcome constraint references unknown objective "
                    f"'{constraint.objective}'"
                )
        
        return self
    
    def get_input(self, name: str) -> Optional[InputSpec]:
        """Get input by name."""
        for inp in self.inputs:
            if inp.name == name:
                return inp
        return None
    
    def get_objective(self, name: str) -> Optional[ObjectiveSpec]:
        """Get objective by name."""
        for obj in self.objectives:
            if obj.name == name:
                return obj
        return None
    
    @property
    def input_names(self) -> List[str]:
        """Get list of input variable names."""
        return [inp.name for inp in self.inputs]
    
    @property
    def objective_names(self) -> List[str]:
        """Get list of objective names."""
        return [obj.name for obj in self.objectives]
    
    @property
    def n_inputs(self) -> int:
        """Number of input variables."""
        return len(self.inputs)
    
    @property
    def n_objectives(self) -> int:
        """Number of objectives."""
        return len(self.objectives)
    
    @property
    def has_categorical(self) -> bool:
        """Check if any inputs are categorical."""
        return any(isinstance(inp, CategoricalInput) for inp in self.inputs)
    
    @property
    def has_conditional(self) -> bool:
        """Check if any inputs are conditional."""
        return any(inp.is_conditional for inp in self.inputs)
    
    @property
    def continuous_inputs(self) -> List[ContinuousInput]:
        """Get continuous inputs only."""
        return [inp for inp in self.inputs if isinstance(inp, ContinuousInput)]
    
    @property
    def discrete_inputs(self) -> List[DiscreteInput]:
        """Get discrete inputs only."""
        return [inp for inp in self.inputs if isinstance(inp, DiscreteInput)]
    
    @property
    def categorical_inputs(self) -> List[CategoricalInput]:
        """Get categorical inputs only."""
        return [inp for inp in self.inputs if isinstance(inp, CategoricalInput)]





