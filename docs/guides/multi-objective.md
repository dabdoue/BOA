# Multi-Objective Optimization with BOA

This guide covers multi-objective optimization using BOA's powerful acquisition functions.

## Overview

In multi-objective optimization, we aim to optimize multiple competing objectives simultaneously. BOA supports:

- **Pareto optimization**: Finding the set of non-dominated solutions
- **Hypervolume maximization**: Maximizing the dominated hypervolume
- **Weighted scalarization**: Converting to single-objective via weights

## Defining Multi-Objective Problems

```yaml
# multi_objective.yaml
name: material_design
version: 1

inputs:
  - name: thickness
    type: continuous
    bounds: [10, 500]  # nm
    
  - name: temperature
    type: continuous
    bounds: [300, 700]  # K
    
  - name: dopant_level
    type: continuous
    bounds: [0.001, 0.1]  # fraction

objectives:
  - name: efficiency
    direction: maximize
    
  - name: cost
    direction: minimize
    
  - name: stability
    direction: maximize

strategies:
  default:
    sampler: lhs
    model: gp_matern
    acquisition: qnehvi
    ref_point: [0.0, 100.0, 0.0]  # Reference point for hypervolume
```

## Available Acquisition Functions

### qNEHVI (Noisy Expected Hypervolume Improvement)

Best for:
- Noisy objective functions
- Batch acquisition
- General multi-objective problems

```yaml
strategies:
  default:
    acquisition: qnehvi
    ref_point: [0.0, 100.0]  # Must specify reference point
```

### qNParEGO (Noisy Parallel Efficient Global Optimization)

Best for:
- Many-objective problems (>3 objectives)
- When you want diversity in suggestions
- Faster than qNEHVI for high-dimensional objective spaces

```yaml
strategies:
  default:
    acquisition: qnparego
```

### EHVI (Expected Hypervolume Improvement)

Best for:
- Noise-free objective functions
- Single acquisition (batch_size=1)

```yaml
strategies:
  default:
    acquisition: ehvi
    ref_point: [0.0, 100.0]
```

## Setting Reference Points

The reference point defines the "worst acceptable" values for each objective:

```python
from boa.sdk import BOAClient

client = BOAClient("http://localhost:8000")

# Get proposals with specific reference point
proposals = client.propose(
    campaign_id=campaign_id,
    n_candidates=3,
    ref_point=[0.0, 100.0, 0.0]  # [min_efficiency, max_cost, min_stability]
)
```

Guidelines for reference points:
- For maximization objectives: use a value below the worst observed
- For minimization objectives: use a value above the worst observed
- Reference points affect the shape of the Pareto front exploration

## Working with the Pareto Front

```python
from boa.sdk import Campaign

campaign = Campaign.from_id(client, campaign_id)

# Get Pareto optimal solutions
pareto_front = campaign.pareto_front()

for solution in pareto_front:
    print(f"Inputs: {solution['x_raw']}")
    print(f"Objectives: {solution['y']}")
    print("---")
```

## Hypervolume Tracking

```python
metrics = campaign.metrics()

print(f"Current hypervolume: {metrics.hypervolume:.4f}")
print(f"Pareto front size: {metrics.pareto_front_size}")
print(f"Hypervolume history: {metrics.improvement_history}")
```

## Visualization

```python
import matplotlib.pyplot as plt
import numpy as np

# Get observations
observations = campaign.get_observations()

# Extract objective values
efficiency = [obs.y["efficiency"] for obs in observations]
cost = [obs.y["cost"] for obs in observations]
stability = [obs.y["stability"] for obs in observations]

# 2D Pareto front plot
fig, axes = plt.subplots(1, 3, figsize=(15, 5))

axes[0].scatter(efficiency, cost, c=stability, cmap='viridis')
axes[0].set_xlabel('Efficiency')
axes[0].set_ylabel('Cost')
axes[0].set_title('Efficiency vs Cost')

axes[1].scatter(efficiency, stability, c=cost, cmap='viridis')
axes[1].set_xlabel('Efficiency')
axes[1].set_ylabel('Stability')
axes[1].set_title('Efficiency vs Stability')

axes[2].scatter(cost, stability, c=efficiency, cmap='viridis')
axes[2].set_xlabel('Cost')
axes[2].set_ylabel('Stability')
axes[2].set_title('Cost vs Stability')

plt.tight_layout()
plt.savefig('pareto_front.png')
```

## Example: Complete Multi-Objective Workflow

```python
from boa.sdk import BOAClient, Campaign

# Connect
client = BOAClient("http://localhost:8000")

# Create process
spec = """
name: battery_optimization
version: 1

inputs:
  - name: cathode_ratio
    type: continuous
    bounds: [0.3, 0.9]
    
  - name: electrolyte_conc
    type: continuous
    bounds: [0.5, 2.0]
    
  - name: temperature
    type: continuous
    bounds: [20, 60]

objectives:
  - name: capacity
    direction: maximize
    
  - name: cycle_life
    direction: maximize
    
  - name: cost
    direction: minimize

strategies:
  default:
    sampler: lhs_optimized
    model: gp_matern
    acquisition: qnehvi
    ref_point: [0.0, 0.0, 100.0]
"""

process = client.create_process("battery_opt", spec)
campaign = Campaign.create(client, process["id"], "experiment_1")

# Initial design
proposals = campaign.initial_design(n_samples=15)
campaign.accept_all(proposals)

# Simulate experiments
for candidate in proposals[0].candidates:
    result = simulate_battery(**candidate)
    campaign.add_observation(candidate, result)

# Optimization loop
for iteration in range(30):
    proposals = campaign.propose(n_candidates=4)
    campaign.accept_all(proposals)
    
    for candidate in proposals[0].candidates:
        result = simulate_battery(**candidate)
        campaign.add_observation(candidate, result)
    
    metrics = campaign.metrics()
    print(f"Iteration {iteration}: HV={metrics.hypervolume:.4f}, Pareto size={metrics.pareto_front_size}")

# Final analysis
print("\n=== Pareto Front ===")
for solution in campaign.pareto_front():
    print(f"{solution['x_raw']} -> {solution['y']}")

campaign.complete()
```

## Tips for Multi-Objective Optimization

1. **Reference point selection**: Start with a reference point well outside your expected Pareto front, then refine based on observed values.

2. **Batch size**: Use larger batch sizes (3-10) to explore diverse regions of the Pareto front.

3. **Balance exploration**: If the front seems clustered, try qNParEGO for more diversity.

4. **Objective scaling**: If objectives are on very different scales, consider normalizing them in your objective function.

5. **Many objectives**: For >3 objectives, consider using preference weights or reducing to key objectives.





