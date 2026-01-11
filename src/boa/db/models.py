"""
BOA Database Models

SQLModel ORM models for all BOA entities with proper relationships,
JSON columns for flexible schema, and enum types for status fields.
"""

import enum
from datetime import datetime
from typing import Any, Optional, List, TYPE_CHECKING
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel, Column, JSON

if TYPE_CHECKING:
    from typing import List as ListType


# =============================================================================
# Enums
# =============================================================================


class CampaignStatus(str, enum.Enum):
    """Campaign lifecycle states."""
    
    CREATED = "created"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class JobStatus(str, enum.Enum):
    """Job queue states."""
    
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, enum.Enum):
    """Types of background jobs."""
    
    PROPOSE = "propose"
    BENCHMARK = "benchmark"
    EXPORT = "export"
    IMPORT = "import"


# =============================================================================
# Base Model
# =============================================================================


class TimestampMixin(SQLModel):
    """Mixin for created_at/updated_at timestamps."""
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)


# =============================================================================
# Process
# =============================================================================


class Process(TimestampMixin, table=True):
    """
    A Process defines the optimization problem specification.
    
    Contains the YAML spec defining inputs, objectives, constraints, and strategies.
    Processes are versioned - updates create new versions.
    """
    
    __tablename__ = "processes"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = Field(default=None)
    spec_yaml: str = Field(description="Full YAML specification as string")
    spec_parsed: dict = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Parsed spec as JSON for querying",
    )
    version: int = Field(default=1, ge=1)
    is_active: bool = Field(default=True, description="Latest version flag")
    
    # Relationships
    campaigns: List["Campaign"] = Relationship(back_populates="process")
    
    def __repr__(self) -> str:
        return f"Process(id={self.id}, name={self.name!r}, version={self.version})"


# =============================================================================
# Campaign
# =============================================================================


class Campaign(TimestampMixin, table=True):
    """
    A Campaign is an optimization run using a Process specification.
    
    Tracks all observations, iterations, proposals, and decisions.
    Supports multi-strategy configuration and state transitions.
    """
    
    __tablename__ = "campaigns"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    process_id: UUID = Field(foreign_key="processes.id", index=True)
    name: str = Field(index=True)
    description: Optional[str] = Field(default=None)
    status: CampaignStatus = Field(default=CampaignStatus.CREATED, index=True)
    strategy_config: dict = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Strategy configuration overrides",
    )
    metadata_: dict = Field(
        default_factory=dict,
        sa_column=Column("metadata", JSON),
        description="Additional campaign metadata",
    )
    
    # Relationships
    process: Optional["Process"] = Relationship(back_populates="campaigns")
    observations: List["Observation"] = Relationship(back_populates="campaign")
    iterations: List["Iteration"] = Relationship(back_populates="campaign")
    checkpoints: List["Checkpoint"] = Relationship(back_populates="campaign")
    artifacts: List["Artifact"] = Relationship(back_populates="campaign")
    jobs: List["Job"] = Relationship(back_populates="campaign")
    
    def __repr__(self) -> str:
        return f"Campaign(id={self.id}, name={self.name!r}, status={self.status.value})"


# =============================================================================
# Observation
# =============================================================================


class Observation(TimestampMixin, table=True):
    """
    An Observation records experimental data (inputs and outputs).
    
    Stores both raw values (as entered) and encoded values (for model training).
    """
    
    __tablename__ = "observations"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    campaign_id: UUID = Field(foreign_key="campaigns.id", index=True)
    x_raw: dict = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Raw input values as entered",
    )
    x_encoded: Optional[list] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Encoded input values for model",
    )
    y: dict = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Objective values",
    )
    source: str = Field(
        default="user",
        description="Source of observation (user, benchmark, import)",
    )
    observed_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the experiment was performed",
    )
    metadata_: dict = Field(
        default_factory=dict,
        sa_column=Column("metadata", JSON),
    )
    
    # Relationships
    campaign: Optional["Campaign"] = Relationship(back_populates="observations")
    
    def __repr__(self) -> str:
        return f"Observation(id={self.id}, source={self.source!r})"


# =============================================================================
# Iteration
# =============================================================================


class Iteration(TimestampMixin, table=True):
    """
    An Iteration represents one optimization cycle.
    
    Contains proposals from multiple strategies and a decision selecting
    which candidates to run next.
    """
    
    __tablename__ = "iterations"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    campaign_id: UUID = Field(foreign_key="campaigns.id", index=True)
    index: int = Field(ge=0, description="0-based iteration index")
    dataset_hash: Optional[str] = Field(
        default=None,
        description="Hash of training data for reproducibility",
    )
    metadata_: dict = Field(
        default_factory=dict,
        sa_column=Column("metadata", JSON),
    )
    
    # Relationships
    campaign: Optional["Campaign"] = Relationship(back_populates="iterations")
    proposals: List["Proposal"] = Relationship(back_populates="iteration")
    decision: Optional["Decision"] = Relationship(
        back_populates="iteration",
        sa_relationship_kwargs={"uselist": False},
    )
    checkpoints: List["Checkpoint"] = Relationship(back_populates="iteration")
    artifacts: List["Artifact"] = Relationship(back_populates="iteration")
    
    def __repr__(self) -> str:
        return f"Iteration(id={self.id}, index={self.index})"


# =============================================================================
# Proposal
# =============================================================================


class Proposal(TimestampMixin, table=True):
    """
    A Proposal contains candidate points from one strategy.
    
    Each iteration may have proposals from multiple strategies for comparison.
    """
    
    __tablename__ = "proposals"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    iteration_id: UUID = Field(foreign_key="iterations.id", index=True)
    strategy_name: str = Field(index=True, description="Name of strategy that generated this")
    candidates_raw: list = Field(
        default_factory=list,
        sa_column=Column(JSON),
        description="Candidate points in raw format",
    )
    candidates_encoded: Optional[list] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Candidate points encoded for model",
    )
    acq_values: Optional[list] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Acquisition function values",
    )
    predictions: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Model predictions (mean, std) for candidates",
    )
    metadata_: dict = Field(
        default_factory=dict,
        sa_column=Column("metadata", JSON),
    )
    
    # Relationships
    iteration: Optional["Iteration"] = Relationship(back_populates="proposals")
    
    def __repr__(self) -> str:
        n = len(self.candidates_raw) if self.candidates_raw else 0
        return f"Proposal(id={self.id}, strategy={self.strategy_name!r}, n_candidates={n})"


# =============================================================================
# Decision
# =============================================================================


class Decision(TimestampMixin, table=True):
    """
    A Decision records which proposals were accepted for an iteration.
    
    Supports selecting candidates from multiple strategies.
    """
    
    __tablename__ = "decisions"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    iteration_id: UUID = Field(foreign_key="iterations.id", unique=True, index=True)
    accepted: list = Field(
        default_factory=list,
        sa_column=Column(JSON),
        description="List of {proposal_id, candidate_indices}",
    )
    notes: Optional[str] = Field(default=None, description="Human notes on decision")
    metadata_: dict = Field(
        default_factory=dict,
        sa_column=Column("metadata", JSON),
    )
    
    # Relationships
    iteration: Optional["Iteration"] = Relationship(back_populates="decision")
    
    def __repr__(self) -> str:
        n = len(self.accepted) if self.accepted else 0
        return f"Decision(id={self.id}, n_accepted={n})"


# =============================================================================
# Checkpoint
# =============================================================================


class Checkpoint(TimestampMixin, table=True):
    """
    A Checkpoint stores a saved model state for recovery.
    
    Enables resuming campaigns after crashes or restarts.
    """
    
    __tablename__ = "checkpoints"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    campaign_id: UUID = Field(foreign_key="campaigns.id", index=True)
    iteration_id: Optional[UUID] = Field(
        default=None,
        foreign_key="iterations.id",
        index=True,
    )
    path: str = Field(description="Path to checkpoint file relative to artifacts dir")
    file_size_bytes: Optional[int] = Field(default=None)
    metadata_: dict = Field(
        default_factory=dict,
        sa_column=Column("metadata", JSON),
        description="Checkpoint metadata (hyperparams, etc.)",
    )
    
    # Relationships
    campaign: Optional["Campaign"] = Relationship(back_populates="checkpoints")
    iteration: Optional["Iteration"] = Relationship(back_populates="checkpoints")
    
    def __repr__(self) -> str:
        return f"Checkpoint(id={self.id}, path={self.path!r})"


# =============================================================================
# Artifact
# =============================================================================


class Artifact(TimestampMixin, table=True):
    """
    An Artifact is any generated file (plots, reports, exports).
    
    Tracks artifact type and location for organization and cleanup.
    """
    
    __tablename__ = "artifacts"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    campaign_id: UUID = Field(foreign_key="campaigns.id", index=True)
    iteration_id: Optional[UUID] = Field(
        default=None,
        foreign_key="iterations.id",
        index=True,
    )
    artifact_type: str = Field(index=True, description="Type: plot, report, export, etc.")
    name: str = Field(description="Human-readable name")
    path: str = Field(description="Path relative to artifacts dir")
    file_size_bytes: Optional[int] = Field(default=None)
    content_type: Optional[str] = Field(default=None, description="MIME type")
    metadata_: dict = Field(
        default_factory=dict,
        sa_column=Column("metadata", JSON),
    )
    
    # Relationships
    campaign: Optional["Campaign"] = Relationship(back_populates="artifacts")
    iteration: Optional["Iteration"] = Relationship(back_populates="artifacts")
    
    def __repr__(self) -> str:
        return f"Artifact(id={self.id}, type={self.artifact_type!r}, name={self.name!r})"


# =============================================================================
# Job
# =============================================================================


class Job(TimestampMixin, table=True):
    """
    A Job represents an async background task.
    
    Used for long-running operations like proposal generation.
    """
    
    __tablename__ = "jobs"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    campaign_id: Optional[UUID] = Field(
        default=None,
        foreign_key="campaigns.id",
        index=True,
    )
    job_type: JobType = Field(index=True)
    status: JobStatus = Field(default=JobStatus.PENDING, index=True)
    params: dict = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Job parameters",
    )
    result: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Job result on completion",
    )
    error: Optional[str] = Field(default=None, description="Error message on failure")
    progress: Optional[float] = Field(default=None, ge=0, le=1, description="Progress 0-1")
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    
    # Relationships
    campaign: Optional["Campaign"] = Relationship(back_populates="jobs")
    
    def __repr__(self) -> str:
        return f"Job(id={self.id}, type={self.job_type.value}, status={self.status.value})"


# =============================================================================
# Campaign Lock
# =============================================================================


class CampaignLock(SQLModel, table=True):
    """
    Campaign write lock for single-writer concurrency control.
    
    Prevents race conditions when multiple clients try to modify a campaign.
    Uses timestamp-based expiration for automatic cleanup.
    """
    
    __tablename__ = "campaign_locks"
    
    campaign_id: UUID = Field(primary_key=True)
    locked_by: str = Field(description="Lock holder identifier")
    locked_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(description="Auto-expire time")
    
    def __repr__(self) -> str:
        return f"CampaignLock(campaign_id={self.campaign_id}, locked_by={self.locked_by!r})"
