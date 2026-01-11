"""
BOA Specification Loader

YAML loading and parsing for ProcessSpec.
"""

from pathlib import Path
from typing import Any, Dict, List, Union

import yaml

from boa.spec.models import (
    ProcessSpec,
    ContinuousInput,
    DiscreteInput,
    CategoricalInput,
    ObjectiveSpec,
    PreferenceSpec,
    InputConstraintSpec,
    OutcomeConstraintSpec,
    ConstraintsSpec,
    StrategySpec,
    ObjectiveDirection,
    PreferenceType,
)
from boa.spec.validators import validate_process_spec, SpecValidationError


class SpecLoadError(Exception):
    """Error loading specification."""
    pass


def load_process_spec(yaml_content: str, validate: bool = True) -> ProcessSpec:
    """
    Load ProcessSpec from YAML string.
    
    Args:
        yaml_content: YAML content as string
        validate: Run validation after loading
        
    Returns:
        Parsed ProcessSpec
        
    Raises:
        SpecLoadError: If parsing fails
        SpecValidationError: If validation fails
    """
    try:
        data = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        raise SpecLoadError(f"Invalid YAML: {e}") from e
    
    return _parse_spec(data, validate)


def load_process_spec_from_file(
    path: Union[str, Path],
    validate: bool = True,
) -> ProcessSpec:
    """
    Load ProcessSpec from YAML file.
    
    Args:
        path: Path to YAML file
        validate: Run validation after loading
        
    Returns:
        Parsed ProcessSpec
        
    Raises:
        SpecLoadError: If parsing fails
        SpecValidationError: If validation fails
    """
    path = Path(path)
    
    if not path.exists():
        raise SpecLoadError(f"File not found: {path}")
    
    try:
        with open(path, "r") as f:
            yaml_content = f.read()
    except IOError as e:
        raise SpecLoadError(f"Cannot read file: {e}") from e
    
    return load_process_spec(yaml_content, validate)


def _parse_spec(data: Dict[str, Any], validate: bool) -> ProcessSpec:
    """Parse raw dict into ProcessSpec."""
    if not isinstance(data, dict):
        raise SpecLoadError("Specification must be a YAML mapping")
    
    # Parse inputs
    inputs = _parse_inputs(data.get("inputs", []))
    
    # Parse objectives
    objectives = _parse_objectives(data.get("objectives", []))
    
    # Parse constraints
    constraints = _parse_constraints(data.get("constraints", {}))
    
    # Parse strategies
    strategies = _parse_strategies(data.get("strategies", {}))
    
    # Build spec
    spec = ProcessSpec(
        name=data.get("name", "unnamed"),
        version=data.get("version", 1),
        description=data.get("description"),
        inputs=inputs,
        objectives=objectives,
        constraints=constraints,
        strategies=strategies,
        metadata=data.get("metadata", {}),
    )
    
    # Validate if requested
    if validate:
        errors = validate_process_spec(spec)
        if errors:
            raise SpecValidationError(errors)
    
    return spec


def _parse_inputs(inputs_data: List[Dict[str, Any]]) -> List[Union[ContinuousInput, DiscreteInput, CategoricalInput]]:
    """Parse input specifications."""
    inputs = []
    
    for inp_data in inputs_data:
        inp_type = inp_data.get("type", "continuous").lower()
        
        # Handle active_if
        active_if = inp_data.get("active_if")
        
        if inp_type == "continuous":
            # Parse bounds from various formats
            bounds = inp_data.get("bounds")
            if bounds is None:
                start = inp_data.get("start")
                stop = inp_data.get("stop")
                if start is not None and stop is not None:
                    bounds = (float(start), float(stop))
                else:
                    raise SpecLoadError(
                        f"Continuous input '{inp_data.get('name')}' requires bounds or start/stop"
                    )
            
            inputs.append(ContinuousInput(
                name=inp_data["name"],
                bounds=tuple(bounds),
                unit=inp_data.get("unit"),
                description=inp_data.get("description"),
                active_if=active_if,
            ))
            
        elif inp_type == "discrete":
            # Parse values or generate from range
            values = inp_data.get("values")
            
            inputs.append(DiscreteInput(
                name=inp_data["name"],
                values=values if values else [],
                start=inp_data.get("start"),
                stop=inp_data.get("stop"),
                step=inp_data.get("step"),
                unit=inp_data.get("unit"),
                description=inp_data.get("description"),
                active_if=active_if,
            ))
            
        elif inp_type == "categorical":
            # Categories can be in "values" or "categories"
            categories = inp_data.get("categories") or inp_data.get("values")
            if not categories:
                raise SpecLoadError(
                    f"Categorical input '{inp_data.get('name')}' requires categories or values"
                )
            
            inputs.append(CategoricalInput(
                name=inp_data["name"],
                categories=[str(c) for c in categories],
                description=inp_data.get("description"),
                active_if=active_if,
            ))
            
        else:
            raise SpecLoadError(f"Unknown input type: {inp_type}")
    
    return inputs


def _parse_objectives(objectives_data: Any) -> List[ObjectiveSpec]:
    """Parse objective specifications."""
    objectives = []
    
    # Handle simple list of names format
    if isinstance(objectives_data, dict) and "names" in objectives_data:
        for name in objectives_data["names"]:
            objectives.append(ObjectiveSpec(name=name))
        return objectives
    
    # Handle full specification format
    if not isinstance(objectives_data, list):
        objectives_data = [objectives_data]
    
    for obj_data in objectives_data:
        if isinstance(obj_data, str):
            objectives.append(ObjectiveSpec(name=obj_data))
        else:
            # Parse preference if present
            preference = None
            pref_data = obj_data.get("preference")
            if pref_data:
                preference = PreferenceSpec(
                    type=PreferenceType(pref_data.get("type", "weight")),
                    value=float(pref_data.get("value", pref_data.get("target", 1.0))),
                )
            
            # Parse direction
            direction_str = obj_data.get("direction", "maximize").lower()
            direction = ObjectiveDirection.MAXIMIZE if direction_str == "maximize" else ObjectiveDirection.MINIMIZE
            
            objectives.append(ObjectiveSpec(
                name=obj_data["name"],
                direction=direction,
                preference=preference,
                description=obj_data.get("description"),
            ))
    
    return objectives


def _parse_constraints(constraints_data: Any) -> ConstraintsSpec:
    """Parse constraint specifications."""
    if not constraints_data:
        return ConstraintsSpec()
    
    input_constraints = []
    outcome_constraints = []
    
    # Handle list format (legacy)
    if isinstance(constraints_data, list):
        for c in constraints_data:
            if isinstance(c, dict):
                # Check for clausius_clapeyron
                if c.get("clausius_clapeyron"):
                    input_constraints.append(InputConstraintSpec(
                        type="clausius_clapeyron",
                        absolute_humidity_col=c.get("ah_col") or c.get("absolute_humidity_col"),
                        temperature_col=c.get("temp_c_col") or c.get("temperature_col"),
                    ))
    
    # Handle dict format (new)
    elif isinstance(constraints_data, dict):
        # Input constraints
        for c in constraints_data.get("input", []):
            input_constraints.append(InputConstraintSpec(
                type=c.get("type", "custom"),
                params=c.get("params", {}),
                absolute_humidity_col=c.get("absolute_humidity_col"),
                temperature_col=c.get("temperature_col"),
            ))
        
        # Outcome constraints
        for c in constraints_data.get("outcome", []):
            outcome_constraints.append(OutcomeConstraintSpec(
                type=c.get("type", "threshold"),
                objective=c["objective"],
                operator=c["operator"],
                value=float(c["value"]),
            ))
    
    return ConstraintsSpec(
        input=input_constraints,
        outcome=outcome_constraints,
    )


def _parse_strategies(strategies_data: Dict[str, Any]) -> Dict[str, StrategySpec]:
    """Parse strategy specifications."""
    strategies = {}
    
    for name, strat_data in strategies_data.items():
        if isinstance(strat_data, dict):
            strategies[name] = StrategySpec(
                name=name,
                sampler=strat_data.get("sampler", "lhs_optimized"),
                model=strat_data.get("model", "gp_matern"),
                acquisition=strat_data.get("acquisition", "qlogNEHVI"),
                sampler_params=strat_data.get("sampler_params", {}),
                model_params=strat_data.get("model_params", {}),
                acquisition_params=strat_data.get("acquisition_params", {}),
                description=strat_data.get("description"),
            )
    
    return strategies





