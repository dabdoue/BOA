"""
BOA - Bayesian Optimization Assistant

A server-based multi-objective optimization platform with campaign tracking,
multi-strategy proposal generation, async job queue, model checkpointing,
mixed+conditional variable spaces, preference objectives, and benchmarking.
"""

__version__ = "1.0.0"
__author__ = "PV-Lab Team"

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
    CampaignStatus,
    JobStatus,
    JobType,
)

__all__ = [
    "__version__",
    # Database models
    "Process",
    "Campaign",
    "Observation",
    "Iteration",
    "Proposal",
    "Decision",
    "Checkpoint",
    "Artifact",
    "Job",
    "CampaignStatus",
    "JobStatus",
    "JobType",
]






