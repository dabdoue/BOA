"""
BOA API Schemas

Pydantic models for API request/response.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# =============================================================================
# Process Schemas
# =============================================================================


class ProcessCreate(BaseModel):
    """Create a new process."""
    
    name: Optional[str] = Field(default=None, description="Process name (optional, can come from spec)")
    description: Optional[str] = Field(default=None)
    spec_yaml: str = Field(description="YAML specification")


class ProcessUpdate(BaseModel):
    """Update a process (creates new version)."""
    
    description: Optional[str] = None
    spec_yaml: Optional[str] = None


class ProcessResponse(BaseModel):
    """Process response."""
    
    id: UUID
    name: str
    description: Optional[str]
    version: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    
    model_config = {"from_attributes": True}


class ProcessDetailResponse(ProcessResponse):
    """Detailed process response with spec."""
    
    spec_yaml: str
    spec_parsed: Dict[str, Any]


# =============================================================================
# Campaign Schemas
# =============================================================================


class CampaignCreate(BaseModel):
    """Create a new campaign."""
    
    process_id: UUID = Field(description="Process ID")
    name: str = Field(description="Campaign name")
    description: Optional[str] = None
    strategy_config: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CampaignUpdate(BaseModel):
    """Update a campaign."""
    
    name: Optional[str] = None
    description: Optional[str] = None
    strategy_config: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    status: Optional[str] = None


class CampaignResponse(BaseModel):
    """Campaign response."""
    
    id: UUID
    process_id: UUID
    name: str
    description: Optional[str]
    status: str
    created_at: datetime
    updated_at: Optional[datetime]
    
    model_config = {"from_attributes": True}


class CampaignDetailResponse(CampaignResponse):
    """Detailed campaign response."""
    
    strategy_config: Dict[str, Any]
    metadata: Dict[str, Any]


# =============================================================================
# Observation Schemas
# =============================================================================


class ObservationCreate(BaseModel):
    """Create a new observation."""
    
    x_raw: Dict[str, Any] = Field(description="Input values")
    y: Dict[str, Any] = Field(description="Objective values")
    source: str = Field(default="user")
    observed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ObservationBatchCreate(BaseModel):
    """Create multiple observations."""
    
    observations: List[ObservationCreate]


class ObservationResponse(BaseModel):
    """Observation response."""
    
    id: UUID
    campaign_id: UUID
    x_raw: Dict[str, Any]
    y: Dict[str, Any]
    source: str
    observed_at: datetime
    created_at: datetime
    
    model_config = {"from_attributes": True}


# =============================================================================
# Iteration Schemas
# =============================================================================


class IterationResponse(BaseModel):
    """Iteration response."""
    
    id: UUID
    campaign_id: UUID
    index: int
    dataset_hash: Optional[str]
    created_at: datetime
    
    model_config = {"from_attributes": True}


# =============================================================================
# Proposal Schemas
# =============================================================================


class ProposalResponse(BaseModel):
    """Proposal response."""
    
    id: UUID
    iteration_id: UUID
    strategy_name: str
    candidates_raw: List[Dict[str, Any]]
    acq_values: Optional[List[float]]
    predictions: Optional[Dict[str, Any]]
    created_at: datetime
    
    model_config = {"from_attributes": True}


class ProposeRequest(BaseModel):
    """Request to generate proposals."""
    
    n_candidates: int = Field(default=1, ge=1, le=100)
    strategy_names: Optional[List[str]] = None
    ref_point: Optional[List[float]] = None


class InitialDesignRequest(BaseModel):
    """Request for initial design."""
    
    n_samples: int = Field(ge=1, le=1000)
    strategy_name: Optional[str] = None


# =============================================================================
# Decision Schemas
# =============================================================================


class AcceptedCandidate(BaseModel):
    """Accepted candidate specification."""
    
    proposal_id: UUID
    candidate_indices: List[int]


class DecisionCreate(BaseModel):
    """Create a decision."""
    
    accepted: List[AcceptedCandidate]
    notes: Optional[str] = None


class DecisionResponse(BaseModel):
    """Decision response."""
    
    id: UUID
    iteration_id: UUID
    accepted: List[Dict[str, Any]]
    notes: Optional[str]
    created_at: datetime
    
    model_config = {"from_attributes": True}


# =============================================================================
# Job Schemas
# =============================================================================


class JobResponse(BaseModel):
    """Job response."""
    
    id: UUID
    campaign_id: Optional[UUID]
    job_type: str
    status: str
    params: Dict[str, Any]
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    progress: Optional[float]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    
    model_config = {"from_attributes": True}


# =============================================================================
# Metrics Schemas
# =============================================================================


class CampaignMetricsResponse(BaseModel):
    """Campaign metrics response."""
    
    n_observations: int
    n_iterations: int
    best_values: Dict[str, float]
    best_observation: Optional[Dict[str, Any]]
    hypervolume: Optional[float]
    pareto_front_size: Optional[int]
    improvement_history: List[float]
    objective_bounds: Dict[str, tuple]


# =============================================================================
# Health Schemas
# =============================================================================


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str
    version: str
    database: str

