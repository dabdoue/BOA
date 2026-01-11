# BOA API Reference

Complete API reference for BOA server endpoints and Python SDK.

## REST API

### Base URL

```
http://localhost:8000
```

### Authentication

Currently, BOA does not require authentication. For production, deploy behind an authentication proxy.

---

## Health

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "connected"
}
```

---

## Processes

### POST /processes

Create a new optimization process.

**Request Body:**
```json
{
  "name": "my_process",
  "spec_yaml": "name: my_process\nversion: 1\n...",
  "description": "Optional description"
}
```

**Response:**
```json
{
  "id": "uuid",
  "name": "my_process",
  "version": 1,
  "description": "Optional description",
  "is_active": true,
  "spec_yaml": "...",
  "spec_parsed": {...},
  "created_at": "2026-01-03T00:00:00Z",
  "updated_at": null
}
```

### GET /processes

List all processes.

**Query Parameters:**
- `name` (optional): Filter by name
- `active_only` (optional, default: true): Only return active processes
- `limit` (optional, default: 100): Maximum results
- `offset` (optional, default: 0): Pagination offset

### GET /processes/{process_id}

Get a specific process by ID.

### PUT /processes/{process_id}

Update a process. If spec_yaml is changed, creates a new version.

**Request Body:**
```json
{
  "description": "Updated description",
  "spec_yaml": "optional new spec"
}
```

### DELETE /processes/{process_id}

Soft delete (deactivate) a process.

---

## Campaigns

### POST /campaigns

Create a new optimization campaign.

**Request Body:**
```json
{
  "process_id": "uuid",
  "name": "my_campaign",
  "description": "Optional description",
  "strategy_config": {},
  "metadata": {}
}
```

**Response:**
```json
{
  "id": "uuid",
  "process_id": "uuid",
  "name": "my_campaign",
  "description": null,
  "status": "created",
  "strategy_config": {},
  "metadata": {},
  "created_at": "2026-01-03T00:00:00Z",
  "updated_at": null
}
```

### GET /campaigns

List campaigns.

**Query Parameters:**
- `process_id` (optional): Filter by process
- `status` (optional): Filter by status (created, active, paused, completed, failed)
- `limit` (optional, default: 100)
- `offset` (optional, default: 0)

### GET /campaigns/{campaign_id}

Get campaign details.

### PUT /campaigns/{campaign_id}

Update campaign.

**Request Body:**
```json
{
  "name": "new_name",
  "description": "new description",
  "strategy_config": {},
  "metadata": {},
  "status": "active"
}
```

### POST /campaigns/{campaign_id}/pause

Pause an active campaign.

### POST /campaigns/{campaign_id}/resume

Resume a paused campaign.

### POST /campaigns/{campaign_id}/complete

Mark campaign as completed.

### GET /campaigns/{campaign_id}/metrics

Get campaign metrics and analysis.

**Response:**
```json
{
  "n_observations": 50,
  "n_iterations": 10,
  "best_values": {"objective1": 0.95, "objective2": 0.12},
  "best_observation": {...},
  "hypervolume": 0.85,
  "pareto_front_size": 8,
  "improvement_history": [0.1, 0.2, 0.4, 0.6, 0.7, 0.8, 0.82, 0.84, 0.85],
  "objective_bounds": {"objective1": [0.1, 0.95], "objective2": [0.05, 0.5]}
}
```

### GET /campaigns/{campaign_id}/export

Export campaign to bundle format.

### POST /campaigns/import

Import campaign from bundle.

**Request Body:** Campaign bundle JSON

---

## Observations

### POST /campaigns/{campaign_id}/observations

Add a single observation.

**Request Body:**
```json
{
  "x_raw": {"input1": 0.5, "input2": "category_a"},
  "y": {"objective1": 0.8, "objective2": 0.15},
  "source": "user",
  "observed_at": "2026-01-03T12:00:00Z",
  "metadata": {}
}
```

### POST /campaigns/{campaign_id}/observations/batch

Add multiple observations.

**Request Body:**
```json
{
  "observations": [
    {"x_raw": {...}, "y": {...}},
    {"x_raw": {...}, "y": {...}}
  ]
}
```

### GET /campaigns/{campaign_id}/observations

List observations.

**Query Parameters:**
- `source` (optional): Filter by source
- `limit` (optional, default: 1000)
- `offset` (optional, default: 0)

### GET /campaigns/{campaign_id}/observations/{observation_id}

Get specific observation.

---

## Proposals

### POST /campaigns/{campaign_id}/initial-design

Generate initial space-filling design.

**Request Body:**
```json
{
  "n_samples": 10,
  "strategy_name": "lhs"
}
```

**Response:**
```json
[
  {
    "id": "uuid",
    "iteration_id": "uuid",
    "strategy_name": "lhs",
    "candidates_raw": [
      {"input1": 0.1, "input2": "a"},
      {"input1": 0.5, "input2": "b"},
      ...
    ],
    "acq_values": null,
    "predictions": null,
    "created_at": "..."
  }
]
```

### POST /campaigns/{campaign_id}/propose

Generate optimization proposals.

**Request Body:**
```json
{
  "n_candidates": 3,
  "strategy_names": ["default"],
  "ref_point": [0.0, 100.0]
}
```

### GET /campaigns/{campaign_id}/iterations

List iterations.

### GET /campaigns/{campaign_id}/iterations/{iteration_index}/proposals

Get proposals for specific iteration.

### POST /campaigns/{campaign_id}/iterations/{iteration_index}/decision

Record decision for iteration.

**Request Body:**
```json
{
  "accepted": [
    {"proposal_id": "uuid", "candidate_indices": [0, 1, 2]}
  ],
  "notes": "Selected all candidates"
}
```

---

## Jobs

### GET /jobs

List jobs.

**Query Parameters:**
- `campaign_id` (optional)
- `status_filter` (optional): pending, running, completed, failed, cancelled
- `limit` (optional, default: 100)
- `offset` (optional, default: 0)

### GET /jobs/{job_id}

Get job details.

### POST /jobs/{job_id}/cancel

Cancel a pending job.

---

## Python SDK

### BOAClient

```python
from boa.sdk import BOAClient

client = BOAClient(
    base_url="http://localhost:8000",
    timeout=30.0,
    headers={"X-Custom-Header": "value"}
)

# Context manager
with BOAClient("http://localhost:8000") as client:
    ...
```

#### Methods

```python
# Health
client.health() -> dict

# Processes
client.create_process(name: str, spec_yaml: str, description: str = None) -> dict
client.list_processes(name: str = None, is_active: bool = True, limit: int = 100, offset: int = 0) -> list
client.get_process(process_id: str | UUID) -> dict
client.update_process(process_id, description: str = None, spec_yaml: str = None) -> dict
client.delete_process(process_id: str | UUID) -> None

# Campaigns
client.create_campaign(process_id, name, description=None, strategy_config=None, metadata=None) -> dict
client.list_campaigns(process_id=None, status=None, limit=100, offset=0) -> list
client.get_campaign(campaign_id) -> dict
client.update_campaign(campaign_id, name=None, description=None, ...) -> dict
client.pause_campaign(campaign_id) -> dict
client.resume_campaign(campaign_id) -> dict
client.complete_campaign(campaign_id) -> dict
client.get_campaign_metrics(campaign_id) -> dict

# Observations
client.add_observation(campaign_id, x_raw: dict, y: dict, source="user") -> dict
client.add_observations_batch(campaign_id, observations: list) -> list
client.list_observations(campaign_id, source=None, limit=1000, offset=0) -> list
client.get_observation(campaign_id, observation_id) -> dict

# Proposals
client.initial_design(campaign_id, n_samples: int, strategy_name=None) -> list
client.propose(campaign_id, n_candidates=1, strategy_names=None, ref_point=None) -> list
client.list_iterations(campaign_id, limit=100, offset=0) -> list
client.get_iteration_proposals(campaign_id, iteration_index: int) -> list
client.record_decision(campaign_id, iteration_index, accepted: list, notes=None) -> dict

# Jobs
client.list_jobs(campaign_id=None, status=None, limit=100, offset=0) -> list
client.get_job(job_id) -> dict
client.cancel_job(job_id) -> dict

# Export/Import
client.export_campaign(campaign_id) -> dict
client.import_campaign(bundle: dict) -> dict
```

### Campaign Helper

```python
from boa.sdk import Campaign

# Create new campaign
campaign = Campaign.create(client, process_id, name, metadata={})

# Load existing campaign
campaign = Campaign.from_id(client, campaign_id)

# Properties
campaign.id -> UUID
campaign.name -> str
campaign.status -> str
campaign.process_id -> UUID

# Operations
campaign.initial_design(n_samples: int, strategy_name=None) -> list[Proposal]
campaign.propose(n_candidates: int, strategy_names=None, ref_point=None) -> list[Proposal]
campaign.accept_all(proposals: list[Proposal]) -> None
campaign.add_observation(x: dict, y: dict) -> Observation
campaign.add_observations(data: list[tuple]) -> list[Observation]
campaign.get_observations() -> list[Observation]
campaign.metrics() -> CampaignMetrics
campaign.best() -> dict
campaign.pareto_front() -> list[dict]
campaign.pause() -> None
campaign.resume() -> None
campaign.complete() -> None
```

### Exceptions

```python
from boa.sdk.exceptions import (
    BOAError,          # Base exception
    BOAConnectionError,  # Connection failed
    BOANotFoundError,   # Resource not found (404)
    BOAValidationError,  # Validation error (400)
    BOAServerError,     # Server error (5xx)
)
```





