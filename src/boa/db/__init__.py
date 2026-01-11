"""
BOA Database Layer

Provides SQLModel ORM models, repository pattern, job queue, and connection management.
"""

from boa.db.models import (
    Process,
    Campaign,
    Observation,
    Iteration,
    Proposal,
    Decision,
    Checkpoint,
    Artifact,
    Job,
    CampaignLock,
    CampaignStatus,
    JobStatus,
    JobType,
)
from boa.db.connection import (
    get_engine,
    get_session,
    create_db_and_tables,
    DatabaseSettings,
)
from boa.db.repository import (
    ProcessRepository,
    CampaignRepository,
    ObservationRepository,
    IterationRepository,
    ProposalRepository,
    DecisionRepository,
    CheckpointRepository,
    ArtifactRepository,
)
from boa.db.job_queue import JobQueue

__all__ = [
    # Models
    "Process",
    "Campaign",
    "Observation",
    "Iteration",
    "Proposal",
    "Decision",
    "Checkpoint",
    "Artifact",
    "Job",
    "CampaignLock",
    "CampaignStatus",
    "JobStatus",
    "JobType",
    # Connection
    "get_engine",
    "get_session",
    "create_db_and_tables",
    "DatabaseSettings",
    # Repositories
    "ProcessRepository",
    "CampaignRepository",
    "ObservationRepository",
    "IterationRepository",
    "ProposalRepository",
    "DecisionRepository",
    "CheckpointRepository",
    "ArtifactRepository",
    # Job Queue
    "JobQueue",
]






