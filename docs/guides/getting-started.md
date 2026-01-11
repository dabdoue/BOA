# Getting Started with BOA

This guide will walk you through setting up BOA and running your first optimization campaign.

## Prerequisites

- Python 3.10 or higher
- pip package manager

## Installation

### Option 1: pip install

```bash
pip install boa
```

### Option 2: From source

```bash
git clone https://github.com/PV-Lab/BOA.git
cd BOA
pip install -e ".[dev]"
```

### Option 3: Docker

```bash
docker pull pvlab/boa:latest
```

## Starting the Server

BOA runs as a server that manages optimization campaigns. Start it with:

```bash
# Using CLI
boa serve --port 8000

# Or with Docker
docker run -p 8000:8000 pvlab/boa:latest
```

By default, BOA uses SQLite for storage. For production, consider PostgreSQL:

```bash
BOA_DATABASE_URL=postgresql://user:pass@localhost/boa boa serve
```

## Your First Optimization

### Step 1: Define Your Problem

Create a YAML specification file describing your optimization problem:

```yaml
# my_problem.yaml
name: simple_optimization
version: 1

inputs:
  - name: x1
    type: continuous
    bounds: [0, 10]
    
  - name: x2
    type: continuous
    bounds: [-5, 5]

objectives:
  - name: output
    direction: maximize

strategies:
  default:
    sampler: lhs
    model: gp_matern
    acquisition: expected_improvement
```

### Step 2: Create a Process

```python
from boa.sdk import BOAClient

client = BOAClient("http://localhost:8000")

# Load specification
with open("my_problem.yaml") as f:
    spec_yaml = f.read()

# Create process
process = client.create_process("my_problem", spec_yaml)
print(f"Process ID: {process['id']}")
```

### Step 3: Create a Campaign

```python
campaign_data = client.create_campaign(
    process_id=process["id"],
    name="run_001",
    metadata={"experiment_date": "2026-01-03"}
)
campaign_id = campaign_data["id"]
```

### Step 4: Generate Initial Design

```python
# Generate space-filling initial samples
proposals = client.initial_design(campaign_id, n_samples=10)

# Get the sample points
initial_samples = proposals[0]["candidates_raw"]
print(f"Initial samples: {initial_samples}")
```

### Step 5: Run Experiments and Add Observations

```python
def my_objective_function(x1, x2):
    """Your actual experiment or simulation."""
    return x1 * x2 - (x1 - 2)**2 - (x2 + 1)**2

# Run experiments and record results
for sample in initial_samples:
    result = my_objective_function(sample["x1"], sample["x2"])
    
    client.add_observation(
        campaign_id=campaign_id,
        x_raw=sample,
        y={"output": result}
    )
```

### Step 6: Optimization Loop

```python
for iteration in range(20):
    # Get next suggestions from the optimizer
    proposals = client.propose(campaign_id, n_candidates=1)
    candidate = proposals[0]["candidates_raw"][0]
    
    # Run experiment
    result = my_objective_function(candidate["x1"], candidate["x2"])
    
    # Record observation
    client.add_observation(
        campaign_id=campaign_id,
        x_raw=candidate,
        y={"output": result}
    )
    
    print(f"Iteration {iteration}: x1={candidate['x1']:.2f}, x2={candidate['x2']:.2f}, output={result:.2f}")
```

### Step 7: Analyze Results

```python
# Get campaign metrics
metrics = client.get_campaign_metrics(campaign_id)

print(f"Total observations: {metrics['n_observations']}")
print(f"Best value: {metrics['best_values']}")
print(f"Best inputs: {metrics['best_observation']['x_raw']}")

# Complete the campaign
client.complete_campaign(campaign_id)
```

## Using the Campaign Helper

For a more convenient API, use the `Campaign` helper class:

```python
from boa.sdk import BOAClient, Campaign

client = BOAClient("http://localhost:8000")

# Create campaign with helper
campaign = Campaign.create(client, process["id"], "run_002")

# Initial design
proposals = campaign.initial_design(n_samples=10)
campaign.accept_all(proposals)

# Add observations
for candidate in proposals[0].candidates:
    result = my_objective_function(**candidate)
    campaign.add_observation(candidate, {"output": result})

# Optimization loop
for _ in range(20):
    proposals = campaign.propose(n_candidates=1)
    campaign.accept_all(proposals)
    
    for candidate in proposals[0].candidates:
        result = my_objective_function(**candidate)
        campaign.add_observation(candidate, {"output": result})

# Get best
best = campaign.best()
print(f"Best: {best}")

# Complete
campaign.complete()
```

## Next Steps

- [Multi-Objective Optimization](multi-objective.md)
- [Mixed Variable Spaces](mixed-spaces.md)
- [Constraint Handling](constraints.md)
- [Custom Plugins](custom-plugins.md)





