# BOA Examples

This directory contains working examples demonstrating BOA's capabilities.

## Prerequisites

1. Install BOA:
   ```bash
   pip install boa
   ```

2. Start the BOA server:
   ```bash
   boa serve --port 8000
   ```

## Examples

### 1. Simple Optimization (`simple_optimization.py`)

Single-objective optimization of the Rosenbrock function.

**Key concepts:**
- Process creation from YAML spec
- Campaign management
- Initial design generation
- Optimization loop
- Retrieving best results

```bash
python simple_optimization.py
```

### 2. Multi-Objective Optimization (`multi_objective_optimization.py`)

Multi-objective optimization of the Binh-Korn benchmark function with constraints.

**Key concepts:**
- Multiple objectives with different directions
- Constraint handling
- Pareto front tracking
- Hypervolume computation
- Visualization

```bash
python multi_objective_optimization.py
```

### 3. Mixed Space Optimization (`mixed_space_optimization.py`)

Optimization with mixed variable types: continuous, discrete, and categorical.

**Key concepts:**
- Continuous variables (temperature, pressure)
- Discrete variables (number of layers)
- Categorical variables (material type, method)
- Batch proposals
- Analysis by category

```bash
python mixed_space_optimization.py
```

## Creating Your Own Optimization

1. **Define your problem** in a YAML specification:

```yaml
name: my_problem
version: 1

inputs:
  - name: x1
    type: continuous
    bounds: [0, 10]
    
  - name: x2
    type: categorical
    levels: [a, b, c]

objectives:
  - name: y
    direction: maximize

strategies:
  default:
    sampler: lhs
    model: gp_matern
    acquisition: expected_improvement
```

2. **Connect to BOA** and create a campaign:

```python
from boa.sdk import BOAClient, Campaign

client = BOAClient("http://localhost:8000")
process = client.create_process("my_problem", open("spec.yaml").read())
campaign = Campaign.create(client, process["id"], "run_1")
```

3. **Run optimization**:

```python
# Initial design
proposals = campaign.initial_design(n_samples=10)
campaign.accept_all(proposals)

for candidate in proposals[0].candidates:
    result = your_experiment(**candidate)
    campaign.add_observation(candidate, result)

# Optimization loop
for _ in range(20):
    proposals = campaign.propose(n_candidates=3)
    campaign.accept_all(proposals)
    
    for candidate in proposals[0].candidates:
        result = your_experiment(**candidate)
        campaign.add_observation(candidate, result)

# Results
print(campaign.best())
campaign.complete()
```

## Tips

1. **Initial design size**: Use at least 5-10× the number of input dimensions
2. **Batch size**: For multi-objective, larger batches (3-10) explore the Pareto front better
3. **Reference point**: For hypervolume-based acquisition, choose a point dominated by all Pareto-optimal solutions
4. **Checkpointing**: BOA automatically saves model states; campaigns can be resumed after server restarts





