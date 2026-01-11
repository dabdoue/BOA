# BOA Documentation

Welcome to the BOA (Bayesian Optimization Assistant) documentation.

## What is BOA?

BOA is a production-ready, server-based platform for multi-objective Bayesian optimization. It provides a comprehensive solution for running optimization campaigns with:

- **Persistent storage** of experiments and model states
- **REST API** for distributed and remote optimization
- **Python SDK** for seamless integration
- **CLI** for command-line workflows
- **Docker support** for easy deployment

## Key Features

### Multi-Objective Optimization
Optimize multiple objectives simultaneously using state-of-the-art acquisition functions like qNEHVI and qNParEGO. Track Pareto fronts and hypervolume automatically.

### Mixed Variable Spaces
Handle continuous, discrete, and categorical variables in the same optimization problem. Support for conditional variables that depend on other variable values.

### Campaign Management
Organize your experiments into campaigns with persistent storage, model checkpointing, and comprehensive metrics tracking.

### Extensible Plugin System
Easily add custom samplers, models, acquisition functions, and constraints through the plugin registry.

## Getting Started

1. **[Installation](guides/getting-started.md#installation)** - Install BOA via pip or Docker
2. **[Quick Start](guides/getting-started.md#your-first-optimization)** - Run your first optimization
3. **[API Reference](guides/api-reference.md)** - Complete API documentation

## Guides

- [Getting Started](guides/getting-started.md) - First steps with BOA
- [Multi-Objective Optimization](guides/multi-objective.md) - Optimizing multiple objectives
- [API Reference](guides/api-reference.md) - REST API and SDK documentation

## Examples

- [Simple Optimization](../examples/simple_optimization.py) - Single-objective optimization
- [Multi-Objective Optimization](../examples/multi_objective_optimization.py) - Pareto optimization
- [Mixed Space Optimization](../examples/mixed_space_optimization.py) - Mixed variable types

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Clients                              │
│  ┌─────────┐  ┌─────────────┐  ┌─────────┐                  │
│  │   CLI   │  │ Python SDK  │  │  HTTP   │                  │
│  └────┬────┘  └──────┬──────┘  └────┬────┘                  │
│       │              │              │                        │
│       └──────────────┼──────────────┘                        │
│                      │                                       │
├──────────────────────┼───────────────────────────────────────┤
│                      ▼                                       │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                   FastAPI Server                     │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │    │
│  │  │  Routes  │  │ Schemas  │  │ Background Jobs  │   │    │
│  │  └────┬─────┘  └──────────┘  └──────────────────┘   │    │
│  │       │                                              │    │
│  └───────┼──────────────────────────────────────────────┘    │
│          │                                                   │
├──────────┼───────────────────────────────────────────────────┤
│          ▼                                                   │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                    Core Engine                       │    │
│  │  ┌────────────────┐  ┌─────────────────┐            │    │
│  │  │ CampaignEngine │  │ StrategyExecutor│            │    │
│  │  └────────┬───────┘  └───────┬─────────┘            │    │
│  │           │                  │                       │    │
│  │  ┌────────▼───────┐  ┌───────▼─────────┐            │    │
│  │  │ ProposalLedger │  │ModelCheckpointer│            │    │
│  │  └────────────────┘  └─────────────────┘            │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌────────────────────────────────┐    │
│  │  Plugin System  │  │        Database Layer          │    │
│  │  ┌───────────┐  │  │  ┌──────────┐  ┌───────────┐  │    │
│  │  │ Samplers  │  │  │  │ SQLModel │  │Repository │  │    │
│  │  │  Models   │  │  │  │  ORM     │  │  Pattern  │  │    │
│  │  │ Acquis.   │  │  │  └──────────┘  └───────────┘  │    │
│  │  └───────────┘  │  │                               │    │
│  └─────────────────┘  └────────────────────────────────┘    │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

## Quick Links

- [GitHub Repository](https://github.com/PV-Lab/BOA)
- [Issue Tracker](https://github.com/PV-Lab/BOA/issues)
- [Contributing Guide](../CONTRIBUTING.md)

## Citation

```bibtex
@software{boa2026,
  title = {BOA: Bayesian Optimization Assistant},
  author = {Schwartz, Ethan and Abdoue, Daniel and Evans, Nicky and Buonassisi, Tonio},
  year = {2026},
  url = {https://github.com/PV-Lab/BOA}
}
```





