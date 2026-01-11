"""
BOA Specification Validators

Custom validation functions for ProcessSpec and related models.
"""

from typing import Any, Dict, List, Set

from boa.spec.models import (
    ProcessSpec,
    InputSpec,
    ContinuousInput,
    DiscreteInput,
    CategoricalInput,
    ObjectiveSpec,
    StrategySpec,
)


class SpecValidationError(Exception):
    """Specification validation error."""
    
    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__(f"Specification validation failed: {errors}")


def validate_process_spec(spec: ProcessSpec) -> List[str]:
    """
    Validate a ProcessSpec for consistency and correctness.
    
    Args:
        spec: ProcessSpec to validate
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors: List[str] = []
    
    # Validate inputs
    errors.extend(_validate_inputs(spec))
    
    # Validate objectives
    errors.extend(_validate_objectives(spec))
    
    # Validate constraints
    errors.extend(_validate_constraints(spec))
    
    # Validate strategies
    errors.extend(_validate_strategies(spec))
    
    # Validate conditional dependencies
    errors.extend(_validate_conditional_dependencies(spec))
    
    return errors


def _validate_inputs(spec: ProcessSpec) -> List[str]:
    """Validate input specifications."""
    errors: List[str] = []
    
    if not spec.inputs:
        errors.append("At least one input is required")
        return errors
    
    # Check for duplicate names
    names = [inp.name for inp in spec.inputs]
    duplicates = [n for n in names if names.count(n) > 1]
    if duplicates:
        errors.append(f"Duplicate input names: {set(duplicates)}")
    
    # Validate each input
    for inp in spec.inputs:
        if isinstance(inp, ContinuousInput):
            lo, hi = inp.bounds
            if lo >= hi:
                errors.append(f"Input '{inp.name}': lower bound must be less than upper")
            if not isinstance(lo, (int, float)) or not isinstance(hi, (int, float)):
                errors.append(f"Input '{inp.name}': bounds must be numeric")
                
        elif isinstance(inp, DiscreteInput):
            if not inp.values:
                errors.append(f"Input '{inp.name}': discrete input must have values")
            if len(inp.values) != len(set(inp.values)):
                errors.append(f"Input '{inp.name}': discrete values must be unique")
                
        elif isinstance(inp, CategoricalInput):
            if len(inp.categories) < 2:
                errors.append(f"Input '{inp.name}': categorical input needs at least 2 categories")
    
    return errors


def _validate_objectives(spec: ProcessSpec) -> List[str]:
    """Validate objective specifications."""
    errors: List[str] = []
    
    if not spec.objectives:
        errors.append("At least one objective is required")
        return errors
    
    # Check for duplicate names
    names = [obj.name for obj in spec.objectives]
    duplicates = [n for n in names if names.count(n) > 1]
    if duplicates:
        errors.append(f"Duplicate objective names: {set(duplicates)}")
    
    # Validate preferences
    total_weight = 0.0
    for obj in spec.objectives:
        if obj.preference:
            if obj.preference.value <= 0:
                errors.append(
                    f"Objective '{obj.name}': preference value must be positive"
                )
            if obj.preference.type.value == "weight":
                total_weight += obj.preference.value
    
    # Check weight normalization (if using weights)
    if total_weight > 0:
        # Weights don't need to sum to 1, but warn if they're very different
        pass
    
    return errors


def _validate_constraints(spec: ProcessSpec) -> List[str]:
    """Validate constraint specifications."""
    errors: List[str] = []
    
    input_names = {inp.name for inp in spec.inputs}
    objective_names = {obj.name for obj in spec.objectives}
    
    # Validate input constraints
    for constraint in spec.constraints.input:
        if constraint.type == "clausius_clapeyron":
            if constraint.absolute_humidity_col:
                if constraint.absolute_humidity_col not in input_names:
                    errors.append(
                        f"Input constraint references unknown variable: "
                        f"'{constraint.absolute_humidity_col}'"
                    )
            if constraint.temperature_col:
                if constraint.temperature_col not in input_names:
                    errors.append(
                        f"Input constraint references unknown variable: "
                        f"'{constraint.temperature_col}'"
                    )
    
    # Validate outcome constraints
    for constraint in spec.constraints.outcome:
        if constraint.objective not in objective_names:
            errors.append(
                f"Outcome constraint references unknown objective: "
                f"'{constraint.objective}'"
            )
    
    return errors


def _validate_strategies(spec: ProcessSpec) -> List[str]:
    """Validate strategy specifications."""
    errors: List[str] = []
    
    # Known samplers, models, and acquisition functions
    known_samplers = {"lhs", "lhs_optimized", "sobol", "random", "grid"}
    known_models = {"gp_matern", "gp_rbf", "gp_matern25", "gp_loocv"}
    known_acquisitions = {
        "qlogNEHVI", "qNEHVI", "qEHVI", "qParEGO", 
        "qKG", "qEI", "random", "pool_based"
    }
    
    for name, strategy in spec.strategies.items():
        # Validate sampler
        if strategy.sampler not in known_samplers:
            errors.append(
                f"Strategy '{name}': unknown sampler '{strategy.sampler}'"
            )
        
        # Validate model
        if strategy.model not in known_models:
            errors.append(
                f"Strategy '{name}': unknown model '{strategy.model}'"
            )
        
        # Validate acquisition
        if strategy.acquisition not in known_acquisitions:
            errors.append(
                f"Strategy '{name}': unknown acquisition '{strategy.acquisition}'"
            )
    
    return errors


def _validate_conditional_dependencies(spec: ProcessSpec) -> List[str]:
    """Validate conditional variable dependencies."""
    errors: List[str] = []
    
    input_map = {inp.name: inp for inp in spec.inputs}
    categorical_names = {
        inp.name for inp in spec.inputs 
        if isinstance(inp, CategoricalInput)
    }
    
    # Build dependency graph
    dependencies: Dict[str, Set[str]] = {}
    for inp in spec.inputs:
        if inp.active_if:
            dependencies[inp.name] = set(inp.active_if.keys())
    
    # Check that all references are to categorical variables
    for var_name, deps in dependencies.items():
        for dep in deps:
            if dep not in input_map:
                errors.append(
                    f"Input '{var_name}' has active_if reference to "
                    f"unknown variable '{dep}'"
                )
            elif dep not in categorical_names:
                errors.append(
                    f"Input '{var_name}' has active_if reference to "
                    f"non-categorical variable '{dep}'"
                )
    
    # Check for circular dependencies
    def has_cycle(var: str, visited: Set[str], path: Set[str]) -> bool:
        if var in path:
            return True
        if var in visited:
            return False
        
        visited.add(var)
        path.add(var)
        
        for dep in dependencies.get(var, set()):
            if has_cycle(dep, visited, path):
                return True
        
        path.remove(var)
        return False
    
    visited: Set[str] = set()
    for var in dependencies:
        if has_cycle(var, visited, set()):
            errors.append(f"Circular dependency detected involving '{var}'")
    
    # Validate that active_if values exist in category
    for inp in spec.inputs:
        if inp.active_if:
            for ref_var, values in inp.active_if.items():
                ref_input = input_map.get(ref_var)
                if ref_input and isinstance(ref_input, CategoricalInput):
                    for val in values:
                        if val not in ref_input.categories:
                            errors.append(
                                f"Input '{inp.name}' active_if references "
                                f"unknown category '{val}' in '{ref_var}'"
                            )
    
    return errors





