# BOA - Bayesian Optimization Assistant

<p align="center">
  <img src="docs/assets/boa-logo.svg" alt="BOA Logo" width="200"/>
</p>

<p align="center">
  <strong>A production-ready, server-based multi-objective Bayesian optimization platform</strong>
</p>

<p align="center">
  <a href="#installation">Installation</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#features">Features</a> •
  <a href="#documentation">Documentation</a> •
  <a href="#examples">Examples</a>
</p>

---

## Overview

BOA (Bayesian Optimization Assistant) is a comprehensive platform for multi-objective Bayesian optimization. It provides:

- **Server-based architecture** with REST API for distributed experiments
- **Multi-objective optimization** using state-of-the-art acquisition functions
- **Mixed variable spaces** supporting continuous, discrete, and categorical inputs
- **Conditional variables** for complex experiment design
- **Campaign management** with persistent storage and model checkpointing
- **Python SDK** for seamless integration
- **CLI** for command-line workflows
- **Docker support** for easy deployment

## Installation

### From PyPI

```bash
pip install boa
```

### From Source

```bash
git clone https://github.com/PV-Lab/BOA.git
cd BOA
pip install -e ".[dev]"
```

### Docker

```bash
docker pull pvlab/boa:latest
docker run -p 8000:8000 pvlab/boa:latest
```

## Quick Start

### 1. Define Your Optimization Problem

Create a YAML specification file (`process.yaml`):

```yaml
name: materials_optimization
version: 1

inputs:
  - name: temperature
    type: continuous
    bounds: [300, 800]  # Kelvin
    
  - name: pressure
    type: continuous
    bounds: [1, 100]    # bar
    
  - name: catalyst
    type: categorical
    levels: [Pt, Pd, Au, Ag]

objectives:
  - name: yield
    direction: maximize
    
  - name: cost
    direction: minimize

constraints:
  - expr: "temperature + pressure <= 850"

strategies:
  default:
    sampler: lhs
    model: gp_matern
    acquisition: qnehvi
```

### 2. Start the Server

```bash
# Using CLI
boa serve --port 8000

# Or using Docker
docker-compose up
```

### 3. Run Optimization

Using the Python SDK:

```python
from boa.sdk import BOAClient, Campaign

# Connect to server
client = BOAClient("http://localhost:8000")

# Create process and campaign
process = client.create_process("materials_opt", open("process.yaml").read())
campaign = Campaign.create(client, process["id"], "experiment_run_1")

# Generate initial design
proposals = campaign.initial_design(n_samples=10)
campaign.accept_all(proposals)

# Run initial experiments
for candidate in proposals[0].candidates:
    result = run_experiment(candidate)  # Your experiment function
    campaign.add_observation(candidate, result)

# Optimization loop
for iteration in range(20):
    # Get next suggestions
    proposals = campaign.propose(n_candidates=3)
    campaign.accept_all(proposals)
    
    # Run experiments
    for candidate in proposals[0].candidates:
        result = run_experiment(candidate)
        campaign.add_observation(candidate, result)
    
    # Check progress
    metrics = campaign.metrics()
    print(f"Iteration {iteration}: Hypervolume = {metrics.hypervolume:.4f}")

# Get best results
best = campaign.best()
pareto_front = campaign.pareto_front()

# Complete campaign
campaign.complete()
```

Or using the CLI:

```bash
# Create process
boa process create process.yaml

# Create campaign
boa campaign create <process_id> --name "experiment_run_1"

# Generate initial design
boa design <campaign_id> --samples 10

# Add observations (from your experiments)
boa observe <campaign_id> '{"temperature": 450, "pressure": 50, "catalyst": "Pt"}' '{"yield": 0.85, "cost": 12.5}'

# Get next suggestions
boa propose <campaign_id> --candidates 3

# Export results
boa export <campaign_id> --output results.json
```

## Features

### Multi-Objective Optimization

- **Pareto front tracking** with hypervolume computation
- **Multiple acquisition functions**: qNEHVI, qNParEGO, EHVI
- **Reference point specification** for hypervolume calculations
- **Weighted sum objectives** for scalarization

### Mixed Variable Spaces

```yaml
inputs:
  # Continuous variables
  - name: temperature
    type: continuous
    bounds: [200, 500]
    
  # Discrete variables
  - name: n_layers
    type: discrete
    bounds: [1, 10]
    
  # Categorical variables
  - name: material
    type: categorical
    levels: [silicon, germanium, gallium_arsenide]
```

### Conditional Variables

```yaml
inputs:
  - name: use_dopant
    type: categorical
    levels: [yes, no]
    
  - name: dopant_concentration
    type: continuous
    bounds: [0.001, 0.1]
    condition:
      use_dopant: yes
```

### Constraint Handling

```yaml
constraints:
  # Linear constraints
  - expr: "x1 + x2 <= 100"
  
  # Nonlinear constraints  
  - expr: "x1 * x2 >= 10"
  
  # Custom functions
  - function: my_constraint_function
```

### Model Checkpointing

BOA automatically saves and restores model states:

```python
# Models are automatically checkpointed after each iteration
campaign.propose(n_candidates=3)

# Resume from checkpoint after server restart
campaign = Campaign.from_id(client, campaign_id)
proposals = campaign.propose(n_candidates=3)  # Uses restored model
```

### Campaign Export/Import

```bash
# Export campaign with all data
boa export <campaign_id> --output campaign_backup.json

# Import on another server
boa import campaign_backup.json
```

## API Reference

### REST API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/processes` | POST | Create process |
| `/processes` | GET | List processes |
| `/processes/{id}` | GET | Get process |
| `/campaigns` | POST | Create campaign |
| `/campaigns` | GET | List campaigns |
| `/campaigns/{id}` | GET | Get campaign |
| `/campaigns/{id}/initial-design` | POST | Generate initial design |
| `/campaigns/{id}/propose` | POST | Get optimization proposals |
| `/campaigns/{id}/observations` | POST | Add observation |
| `/campaigns/{id}/metrics` | GET | Get campaign metrics |
| `/campaigns/{id}/export` | GET | Export campaign |
| `/campaigns/import` | POST | Import campaign |

### Python SDK

```python
from boa.sdk import BOAClient, Campaign

# Client operations
client = BOAClient("http://localhost:8000")
client.create_process(name, spec_yaml)
client.create_campaign(process_id, name)
client.add_observation(campaign_id, x_raw, y)
client.initial_design(campaign_id, n_samples)
client.propose(campaign_id, n_candidates)

# Campaign helper
campaign = Campaign.create(client, process_id, name)
campaign.initial_design(n_samples=10)
campaign.propose(n_candidates=3)
campaign.add_observation(inputs, outputs)
campaign.metrics()
campaign.best()
campaign.pareto_front()
```

## Configuration

### Server Configuration

Environment variables:

```bash
BOA_DATABASE_URL=sqlite:///boa.db  # or postgresql://...
BOA_ARTIFACTS_DIR=/path/to/artifacts
BOA_HOST=0.0.0.0
BOA_PORT=8000
BOA_DEBUG=false
```

### Docker Compose

```yaml
# SQLite (default)
docker-compose up boa

# PostgreSQL
docker-compose --profile postgres up
```

## Benchmarks

BOA includes standard multi-objective benchmark suites:

```python
from boa.benchmarks import DTLZ2, ZDT1, BenchmarkRunner

# Run benchmark
runner = BenchmarkRunner(
    benchmark=DTLZ2(n_dim=6, n_objectives=2),
    n_initial=10,
    n_iterations=50,
)
results = runner.run()
print(f"Final hypervolume: {results.final_hypervolume:.4f}")
```

## Development

### Running Tests

```bash
# All tests
pytest tests/test_boa/ -v

# Specific module
pytest tests/test_boa/server/ -v

# With coverage
pytest tests/test_boa/ --cov=src/boa --cov-report=html
```

### Code Quality

```bash
# Formatting
black src/boa tests

# Linting
ruff check src/boa tests

# Type checking
mypy src/boa
```

## Citation

If you use BOA in your research, please cite:

```bibtex
@software{boa2026,
  title = {BOA: Bayesian Optimization Assistant},
  author = {Schwartz, Ethan and Abdoue, Daniel and Evans, Nicky and Buonassisi, Tonio},
  year = {2026},
  url = {https://github.com/PV-Lab/BOA}
}
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Acknowledgments

BOA builds on these excellent libraries:
- [BoTorch](https://botorch.org/) - Bayesian optimization in PyTorch
- [GPyTorch](https://gpytorch.ai/) - Gaussian processes in PyTorch
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [SQLModel](https://sqlmodel.tiangolo.com/) - Database ORM
