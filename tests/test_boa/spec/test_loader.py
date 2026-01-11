"""
Tests for BOA specification loader.

Tests YAML loading, parsing, and validation.
"""

import tempfile
from pathlib import Path

import pytest

from boa.spec.loader import (
    load_process_spec,
    load_process_spec_from_file,
    SpecLoadError,
)
from boa.spec.validators import SpecValidationError
from boa.spec.models import (
    InputType,
    ObjectiveDirection,
    PreferenceType,
)


class TestYAMLLoading:
    """Tests for YAML loading."""
    
    def test_load_simple_spec(self):
        """Test loading a simple spec."""
        yaml_content = """
name: simple_test
version: 1

inputs:
  - name: temperature
    type: continuous
    bounds: [20, 100]
    unit: C
    
objectives:
  - name: efficiency
    direction: maximize
"""
        spec = load_process_spec(yaml_content)
        
        assert spec.name == "simple_test"
        assert spec.version == 1
        assert spec.n_inputs == 1
        assert spec.n_objectives == 1
        assert spec.inputs[0].name == "temperature"
        assert spec.objectives[0].name == "efficiency"
    
    def test_load_mixed_space_spec(self):
        """Test loading a mixed space spec."""
        yaml_content = """
name: mixed_test

inputs:
  - name: temp
    type: continuous
    bounds: [20, 100]
    
  - name: speed
    type: discrete
    values: [10, 20, 30, 40, 50]
    
  - name: solvent
    type: categorical
    categories: [DMF, DMSO, GBL]
    
objectives:
  - name: efficiency
  - name: stability
"""
        spec = load_process_spec(yaml_content)
        
        assert spec.n_inputs == 3
        assert spec.has_categorical
        assert len(spec.categorical_inputs) == 1
    
    def test_load_conditional_spec(self):
        """Test loading spec with conditional variables."""
        yaml_content = """
name: conditional_test

inputs:
  - name: additive
    type: categorical
    categories: [none, MACl, FAI, CsI]
    
  - name: concentration
    type: continuous
    bounds: [0.01, 0.5]
    active_if:
      additive: [MACl, FAI, CsI]
    
objectives:
  - name: efficiency
"""
        spec = load_process_spec(yaml_content)
        
        assert spec.has_conditional
        conc = spec.get_input("concentration")
        assert conc.is_conditional
        assert conc.active_if == {"additive": ["MACl", "FAI", "CsI"]}
    
    def test_load_with_constraints(self):
        """Test loading spec with constraints."""
        yaml_content = """
name: constrained_test

inputs:
  - name: temp
    type: continuous
    bounds: [20, 100]
    
  - name: humidity
    type: continuous
    bounds: [0, 100]
    
objectives:
  - name: efficiency

constraints:
  input:
    - type: clausius_clapeyron
      absolute_humidity_col: humidity
      temperature_col: temp
      
  outcome:
    - objective: efficiency
      operator: ">="
      value: 15.0
"""
        spec = load_process_spec(yaml_content)
        
        assert len(spec.constraints.input) == 1
        assert len(spec.constraints.outcome) == 1
        assert spec.constraints.outcome[0].value == 15.0
    
    def test_load_with_strategies(self):
        """Test loading spec with strategies."""
        yaml_content = """
name: strategy_test

inputs:
  - name: x
    type: continuous
    bounds: [0, 1]
    
objectives:
  - name: y

strategies:
  default:
    sampler: lhs_optimized
    model: gp_matern
    acquisition: qlogNEHVI
    
  exploration:
    sampler: sobol
    model: gp_rbf
    acquisition: qNEHVI
    acquisition_params:
      eta: 0.1
"""
        spec = load_process_spec(yaml_content)
        
        assert len(spec.strategies) == 2
        assert "default" in spec.strategies
        assert "exploration" in spec.strategies
        assert spec.strategies["exploration"].acquisition_params["eta"] == 0.1
    
    def test_load_with_preferences(self):
        """Test loading spec with objective preferences."""
        yaml_content = """
name: preference_test

inputs:
  - name: x
    type: continuous
    bounds: [0, 1]
    
objectives:
  - name: efficiency
    direction: maximize
    
  - name: stability
    direction: maximize
    preference:
      type: aspiration
      value: 1000
      
  - name: cost
    direction: minimize
    preference:
      type: weight
      value: 0.5
"""
        spec = load_process_spec(yaml_content)
        
        assert spec.objectives[0].preference is None
        assert spec.objectives[1].preference.type == PreferenceType.ASPIRATION
        assert spec.objectives[1].preference.value == 1000
        assert spec.objectives[2].preference.type == PreferenceType.WEIGHT


class TestLegacyFormats:
    """Tests for legacy YAML formats."""
    
    def test_load_legacy_objectives_format(self):
        """Test loading legacy objectives format with names list."""
        yaml_content = """
name: legacy_test

inputs:
  - name: x
    type: continuous
    bounds: [0, 1]
    
objectives:
  names:
    - PCE
    - Stability
    - Repeatability
"""
        spec = load_process_spec(yaml_content)
        
        assert spec.n_objectives == 3
        assert spec.objective_names == ["PCE", "Stability", "Repeatability"]
    
    def test_load_legacy_constraints_format(self):
        """Test loading legacy constraints format."""
        yaml_content = """
name: legacy_constraints

inputs:
  - name: temp
    type: continuous
    bounds: [20, 50]
    
  - name: humidity
    type: continuous
    bounds: [2, 37]
    
objectives:
  - name: y

constraints:
  - clausius_clapeyron: true
    ah_col: humidity
    temp_c_col: temp
"""
        spec = load_process_spec(yaml_content)
        
        assert len(spec.constraints.input) == 1
        assert spec.constraints.input[0].type == "clausius_clapeyron"
    
    def test_load_discrete_from_range(self):
        """Test loading discrete input from start/stop/step."""
        yaml_content = """
name: range_test

inputs:
  - name: speed
    type: discrete
    start: 0.25
    stop: 1.0
    step: 0.25
    unit: m/min
    
objectives:
  - name: y
"""
        spec = load_process_spec(yaml_content)
        
        speed = spec.get_input("speed")
        assert len(speed.values) == 4
        assert speed.values[0] == pytest.approx(0.25)
        assert speed.values[-1] == pytest.approx(1.0)


class TestFileLoading:
    """Tests for file-based loading."""
    
    def test_load_from_file(self):
        """Test loading spec from file."""
        yaml_content = """
name: file_test
inputs:
  - name: x
    type: continuous
    bounds: [0, 1]
objectives:
  - name: y
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            f.flush()
            
            spec = load_process_spec_from_file(f.name)
            
        assert spec.name == "file_test"
    
    def test_load_missing_file(self):
        """Test loading from missing file."""
        with pytest.raises(SpecLoadError, match="not found"):
            load_process_spec_from_file("/nonexistent/path.yaml")


class TestValidation:
    """Tests for validation during loading."""
    
    def test_invalid_yaml(self):
        """Test that invalid YAML raises error."""
        yaml_content = """
name: bad
inputs: [
  - this is invalid yaml
"""
        with pytest.raises(SpecLoadError, match="Invalid YAML"):
            load_process_spec(yaml_content)
    
    def test_validation_errors(self):
        """Test that validation errors are caught."""
        yaml_content = """
name: invalid_test

inputs:
  - name: additive
    type: categorical
    categories: [A, B]
    
  - name: conc
    type: continuous
    bounds: [0, 1]
    active_if:
      nonexistent: [X]  # Invalid reference
    
objectives:
  - name: y
"""
        # Pydantic validates first (during ProcessSpec construction), so we get ValidationError
        # rather than SpecValidationError
        from pydantic import ValidationError
        with pytest.raises((SpecValidationError, ValidationError)):
            load_process_spec(yaml_content)
    
    def test_skip_validation(self):
        """Test that validation can be skipped."""
        # This spec has an invalid active_if but we skip validation
        yaml_content = """
name: skip_validation

inputs:
  - name: x
    type: continuous
    bounds: [0, 1]
    
objectives:
  - name: y
"""
        # Should not raise
        spec = load_process_spec(yaml_content, validate=False)
        assert spec.name == "skip_validation"


class TestCompleteSpec:
    """Test loading complete real-world-like spec."""
    
    def test_perovskite_spec(self):
        """Test loading a realistic perovskite optimization spec."""
        yaml_content = """
name: perovskite_optimization
version: 1
description: Multi-objective optimization for perovskite solar cell fabrication

inputs:
  - name: temperature
    type: continuous
    bounds: [25, 150]
    unit: C
    description: Substrate temperature
    
  - name: coating_speed
    type: discrete
    values: [10, 20, 30, 40, 50]
    unit: mm/s
    
  - name: solvent
    type: categorical
    categories: [DMF, DMSO, GBL, NMP]
    
  - name: additive
    type: categorical
    categories: [none, MACl, FAI, CsI]
    
  - name: additive_concentration
    type: continuous
    bounds: [0.01, 0.5]
    active_if:
      additive: [MACl, FAI, CsI]

objectives:
  - name: efficiency
    direction: maximize
    
  - name: stability
    direction: maximize
    preference:
      type: aspiration
      value: 1000
      
  - name: cost
    direction: minimize
    preference:
      type: weight
      value: 0.5

constraints:
  outcome:
    - objective: efficiency
      operator: ">="
      value: 15.0

strategies:
  default:
    sampler: lhs_optimized
    model: gp_matern
    acquisition: qlogNEHVI
    
  exploration:
    sampler: lhs_optimized
    model: gp_rbf
    acquisition: qNEHVI
    acquisition_params:
      eta: 0.1
"""
        spec = load_process_spec(yaml_content)
        
        # Validate structure
        assert spec.name == "perovskite_optimization"
        assert spec.n_inputs == 5
        assert spec.n_objectives == 3
        assert spec.has_categorical
        assert spec.has_conditional
        
        # Check inputs
        assert len(spec.continuous_inputs) == 2
        assert len(spec.discrete_inputs) == 1
        assert len(spec.categorical_inputs) == 2
        
        # Check conditional
        conc = spec.get_input("additive_concentration")
        assert conc.is_conditional
        
        # Check objectives
        assert spec.objectives[0].is_maximization
        assert not spec.objectives[2].is_maximization
        
        # Check constraints
        assert len(spec.constraints.outcome) == 1
        
        # Check strategies
        assert len(spec.strategies) == 2

