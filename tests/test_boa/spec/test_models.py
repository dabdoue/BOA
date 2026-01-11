"""
Tests for BOA specification models.

Tests Pydantic models for inputs, objectives, constraints, and strategies.
"""

import pytest

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
    InputType,
    ObjectiveDirection,
    PreferenceType,
)


class TestContinuousInput:
    """Tests for ContinuousInput model."""
    
    def test_basic_continuous(self):
        """Test basic continuous input."""
        inp = ContinuousInput(
            name="temperature",
            bounds=(20.0, 100.0),
            unit="C",
        )
        
        assert inp.name == "temperature"
        assert inp.type == InputType.CONTINUOUS
        assert inp.bounds == (20.0, 100.0)
        assert inp.unit == "C"
        assert not inp.is_conditional
    
    def test_conditional_continuous(self):
        """Test conditional continuous input."""
        inp = ContinuousInput(
            name="concentration",
            bounds=(0.01, 0.5),
            active_if={"additive": ["MACl", "FAI"]},
        )
        
        assert inp.is_conditional
        assert inp.active_if == {"additive": ["MACl", "FAI"]}
    
    def test_invalid_bounds(self):
        """Test that invalid bounds are rejected."""
        with pytest.raises(ValueError, match="must be less than"):
            ContinuousInput(name="bad", bounds=(100.0, 20.0))


class TestDiscreteInput:
    """Tests for DiscreteInput model."""
    
    def test_basic_discrete(self):
        """Test basic discrete input."""
        inp = DiscreteInput(
            name="speed",
            values=[10, 20, 30, 40, 50],
            unit="mm/s",
        )
        
        assert inp.name == "speed"
        assert inp.type == InputType.DISCRETE
        assert inp.values == [10, 20, 30, 40, 50]
        assert inp.bounds == (10, 50)
    
    def test_discrete_from_range(self):
        """Test discrete input from start/stop/step."""
        inp = DiscreteInput(
            name="temp",
            values=[],  # Will be generated
            start=20.0,
            stop=50.0,
            step=5.0,
        )
        
        assert len(inp.values) == 7
        assert inp.values[0] == 20.0
        assert inp.values[-1] == 50.0


class TestCategoricalInput:
    """Tests for CategoricalInput model."""
    
    def test_basic_categorical(self):
        """Test basic categorical input."""
        inp = CategoricalInput(
            name="solvent",
            categories=["DMF", "DMSO", "GBL", "NMP"],
        )
        
        assert inp.name == "solvent"
        assert inp.type == InputType.CATEGORICAL
        assert len(inp.categories) == 4
        assert "DMF" in inp.categories
    
    def test_categorical_needs_two(self):
        """Test that categorical needs at least 2 categories."""
        with pytest.raises(ValueError, match="at least 2"):
            CategoricalInput(name="bad", categories=["only_one"])
    
    def test_categorical_unique(self):
        """Test that categories must be unique."""
        with pytest.raises(ValueError, match="unique"):
            CategoricalInput(name="bad", categories=["A", "B", "A"])


class TestObjectiveSpec:
    """Tests for ObjectiveSpec model."""
    
    def test_basic_objective(self):
        """Test basic objective."""
        obj = ObjectiveSpec(
            name="efficiency",
            direction=ObjectiveDirection.MAXIMIZE,
        )
        
        assert obj.name == "efficiency"
        assert obj.is_maximization
        assert obj.preference is None
    
    def test_objective_with_preference(self):
        """Test objective with preference."""
        obj = ObjectiveSpec(
            name="cost",
            direction=ObjectiveDirection.MINIMIZE,
            preference=PreferenceSpec(
                type=PreferenceType.WEIGHT,
                value=0.5,
            ),
        )
        
        assert not obj.is_maximization
        assert obj.preference.type == PreferenceType.WEIGHT
        assert obj.preference.value == 0.5
    
    def test_aspiration_preference(self):
        """Test aspiration level preference."""
        obj = ObjectiveSpec(
            name="stability",
            preference=PreferenceSpec(
                type=PreferenceType.ASPIRATION,
                value=1000.0,
            ),
        )
        
        assert obj.preference.type == PreferenceType.ASPIRATION


class TestConstraintSpecs:
    """Tests for constraint specifications."""
    
    def test_input_constraint(self):
        """Test input constraint spec."""
        constraint = InputConstraintSpec(
            type="clausius_clapeyron",
            absolute_humidity_col="humidity",
            temperature_col="temp",
        )
        
        assert constraint.type == "clausius_clapeyron"
        assert constraint.absolute_humidity_col == "humidity"
    
    def test_outcome_constraint(self):
        """Test outcome constraint spec."""
        constraint = OutcomeConstraintSpec(
            objective="efficiency",
            operator=">=",
            value=15.0,
        )
        
        assert constraint.objective == "efficiency"
        assert constraint.operator == ">="
        assert constraint.value == 15.0
    
    def test_invalid_operator(self):
        """Test invalid operator is rejected."""
        with pytest.raises(ValueError, match="operator"):
            OutcomeConstraintSpec(
                objective="eff",
                operator="~=",
                value=10.0,
            )


class TestStrategySpec:
    """Tests for StrategySpec model."""
    
    def test_basic_strategy(self):
        """Test basic strategy."""
        strat = StrategySpec(
            name="default",
            sampler="lhs_optimized",
            model="gp_matern",
            acquisition="qlogNEHVI",
        )
        
        assert strat.name == "default"
        assert strat.sampler == "lhs_optimized"
        assert strat.model == "gp_matern"
        assert strat.acquisition == "qlogNEHVI"
    
    def test_strategy_with_params(self):
        """Test strategy with custom parameters."""
        strat = StrategySpec(
            name="exploration",
            sampler="sobol",
            model="gp_rbf",
            acquisition="qNEHVI",
            acquisition_params={"eta": 0.1},
        )
        
        assert strat.acquisition_params["eta"] == 0.1


class TestProcessSpec:
    """Tests for ProcessSpec model."""
    
    @pytest.fixture
    def simple_spec(self) -> ProcessSpec:
        """Create a simple process spec."""
        return ProcessSpec(
            name="test_process",
            inputs=[
                ContinuousInput(name="temp", bounds=(20, 100)),
                DiscreteInput(name="speed", values=[10, 20, 30]),
            ],
            objectives=[
                ObjectiveSpec(name="efficiency"),
                ObjectiveSpec(name="cost", direction=ObjectiveDirection.MINIMIZE),
            ],
        )
    
    @pytest.fixture
    def mixed_spec(self) -> ProcessSpec:
        """Create a mixed space process spec."""
        return ProcessSpec(
            name="mixed_process",
            inputs=[
                ContinuousInput(name="temp", bounds=(20, 100)),
                CategoricalInput(name="solvent", categories=["DMF", "DMSO", "GBL"]),
                ContinuousInput(
                    name="concentration",
                    bounds=(0.1, 0.5),
                    active_if={"solvent": ["DMF", "DMSO"]},
                ),
            ],
            objectives=[
                ObjectiveSpec(name="efficiency"),
            ],
        )
    
    def test_simple_spec(self, simple_spec: ProcessSpec):
        """Test simple process spec."""
        assert simple_spec.name == "test_process"
        assert simple_spec.n_inputs == 2
        assert simple_spec.n_objectives == 2
        assert simple_spec.input_names == ["temp", "speed"]
        assert simple_spec.objective_names == ["efficiency", "cost"]
    
    def test_mixed_spec(self, mixed_spec: ProcessSpec):
        """Test mixed space process spec."""
        assert mixed_spec.has_categorical
        assert mixed_spec.has_conditional
        assert len(mixed_spec.categorical_inputs) == 1
    
    def test_get_input(self, simple_spec: ProcessSpec):
        """Test getting input by name."""
        temp = simple_spec.get_input("temp")
        assert temp is not None
        assert temp.name == "temp"
        
        none = simple_spec.get_input("nonexistent")
        assert none is None
    
    def test_get_objective(self, simple_spec: ProcessSpec):
        """Test getting objective by name."""
        eff = simple_spec.get_objective("efficiency")
        assert eff is not None
        assert eff.name == "efficiency"
    
    def test_empty_inputs_rejected(self):
        """Test that empty inputs are rejected."""
        with pytest.raises(ValueError, match="At least one input"):
            ProcessSpec(
                name="bad",
                inputs=[],
                objectives=[ObjectiveSpec(name="eff")],
            )
    
    def test_empty_objectives_rejected(self):
        """Test that empty objectives are rejected."""
        with pytest.raises(ValueError, match="At least one objective"):
            ProcessSpec(
                name="bad",
                inputs=[ContinuousInput(name="x", bounds=(0, 1))],
                objectives=[],
            )
    
    def test_duplicate_input_names_rejected(self):
        """Test that duplicate input names are rejected."""
        with pytest.raises(ValueError, match="unique"):
            ProcessSpec(
                name="bad",
                inputs=[
                    ContinuousInput(name="x", bounds=(0, 1)),
                    ContinuousInput(name="x", bounds=(0, 1)),
                ],
                objectives=[ObjectiveSpec(name="y")],
            )
    
    def test_invalid_active_if_reference(self):
        """Test that invalid active_if references are caught."""
        with pytest.raises(ValueError, match="unknown variable"):
            ProcessSpec(
                name="bad",
                inputs=[
                    ContinuousInput(
                        name="x",
                        bounds=(0, 1),
                        active_if={"nonexistent": ["a"]},
                    ),
                ],
                objectives=[ObjectiveSpec(name="y")],
            )
    
    def test_active_if_must_reference_categorical(self):
        """Test that active_if must reference categorical."""
        with pytest.raises(ValueError, match="categorical"):
            ProcessSpec(
                name="bad",
                inputs=[
                    ContinuousInput(name="base", bounds=(0, 1)),
                    ContinuousInput(
                        name="dependent",
                        bounds=(0, 1),
                        active_if={"base": [0.5]},  # base is continuous, not categorical
                    ),
                ],
                objectives=[ObjectiveSpec(name="y")],
            )
    
    def test_invalid_outcome_constraint_reference(self):
        """Test that outcome constraint references are validated."""
        with pytest.raises(ValueError, match="unknown objective"):
            ProcessSpec(
                name="bad",
                inputs=[ContinuousInput(name="x", bounds=(0, 1))],
                objectives=[ObjectiveSpec(name="efficiency")],
                constraints=ConstraintsSpec(
                    outcome=[
                        OutcomeConstraintSpec(
                            objective="nonexistent",
                            operator=">=",
                            value=10,
                        ),
                    ],
                ),
            )





