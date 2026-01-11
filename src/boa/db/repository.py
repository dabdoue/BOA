"""
BOA Repository Pattern

Provides repository classes for CRUD operations on all entities.
Includes write locking for campaign modifications.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Generic, TypeVar, Any
from uuid import UUID

from sqlmodel import Session, select, col

from boa.db.models import (
    Process,
    Campaign,
    Observation,
    Iteration,
    Proposal,
    Decision,
    Checkpoint,
    Artifact,
    CampaignLock,
    CampaignStatus,
)


# =============================================================================
# Exceptions
# =============================================================================


class RepositoryError(Exception):
    """Base exception for repository errors."""
    pass


class NotFoundError(RepositoryError):
    """Entity not found."""
    pass


class CampaignLockedError(RepositoryError):
    """Campaign is locked by another writer."""
    
    def __init__(self, campaign_id: UUID, locked_by: str, expires_at: datetime):
        self.campaign_id = campaign_id
        self.locked_by = locked_by
        self.expires_at = expires_at
        super().__init__(
            f"Campaign {campaign_id} is locked by {locked_by} until {expires_at}"
        )


class InvalidStateTransitionError(RepositoryError):
    """Invalid campaign state transition."""
    pass


# =============================================================================
# Generic Base Repository
# =============================================================================

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Base repository with common CRUD operations."""
    
    model: type[T]
    
    def __init__(self, session: Session):
        self.session = session
    
    def get(self, id: UUID) -> T | None:
        """Get entity by ID."""
        return self.session.get(self.model, id)
    
    def get_or_raise(self, id: UUID) -> T:
        """Get entity by ID or raise NotFoundError."""
        entity = self.get(id)
        if entity is None:
            raise NotFoundError(f"{self.model.__name__} with id {id} not found")
        return entity
    
    def create(self, entity: T) -> T:
        """Create a new entity."""
        self.session.add(entity)
        self.session.flush()
        self.session.refresh(entity)
        return entity
    
    def update(self, entity: T) -> T:
        """Update an existing entity."""
        entity.updated_at = datetime.utcnow()  # type: ignore
        self.session.add(entity)
        self.session.flush()
        self.session.refresh(entity)
        return entity
    
    def delete(self, entity: T) -> None:
        """Delete an entity."""
        self.session.delete(entity)
        self.session.flush()
    
    def delete_by_id(self, id: UUID) -> bool:
        """Delete entity by ID. Returns True if deleted."""
        entity = self.get(id)
        if entity:
            self.delete(entity)
            return True
        return False


# =============================================================================
# Process Repository
# =============================================================================


class ProcessRepository(BaseRepository[Process]):
    """Repository for Process entities."""
    
    model = Process
    
    def list(
        self,
        name: str | None = None,
        is_active: bool | None = None,
        active_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Process]:
        """List processes with optional filters."""
        stmt = select(Process)
        
        if name is not None:
            stmt = stmt.where(Process.name == name)
        if is_active is not None:
            stmt = stmt.where(Process.is_active == is_active)
        elif active_only:
            stmt = stmt.where(Process.is_active == True)
        
        stmt = stmt.order_by(col(Process.created_at).desc())
        stmt = stmt.offset(offset).limit(limit)
        
        return list(self.session.exec(stmt).all())
    
    def list_versions(
        self,
        name: str,
        active_only: bool = True,
    ) -> list[Process]:
        """List all versions of a process by name."""
        stmt = select(Process).where(Process.name == name)
        if active_only:
            stmt = stmt.where(Process.is_active == True)
        stmt = stmt.order_by(col(Process.version).desc())
        return list(self.session.exec(stmt).all())
    
    def create_from_spec(
        self,
        spec_yaml: str,
        spec_parsed: dict,
        name: str | None = None,
        description: str | None = None,
    ) -> Process:
        """Create a new process from spec."""
        # Use name from spec_parsed if not provided
        process_name = name or spec_parsed.get("name", "Unnamed Process")
        
        process = Process(
            name=process_name,
            spec_yaml=spec_yaml,
            spec_parsed=spec_parsed,
            description=description,
            version=1,
            is_active=True,
        )
        return self.create(process)
    
    def get_by_name(self, name: str, version: int | None = None) -> Process | None:
        """Get process by name and optional version."""
        stmt = select(Process).where(Process.name == name)
        
        if version is not None:
            stmt = stmt.where(Process.version == version)
        else:
            # Get latest version
            stmt = stmt.where(Process.is_active == True)
        
        return self.session.exec(stmt).first()
    
    def create_version(self, process: Process) -> Process:
        """Create a new version of an existing process."""
        # Deactivate all previous versions
        stmt = select(Process).where(
            Process.name == process.name,
            Process.is_active == True,
        )
        for old in self.session.exec(stmt):
            old.is_active = False
            old.updated_at = datetime.utcnow()
            self.session.add(old)
        
        # Create new version
        new_version = max(p.version for p in self.list(name=process.name)) + 1
        process.version = new_version
        process.is_active = True
        
        return self.create(process)


# =============================================================================
# Campaign Repository with Locking
# =============================================================================


class CampaignRepository(BaseRepository[Campaign]):
    """Repository for Campaign entities with write locking."""
    
    model = Campaign
    
    # Valid state transitions
    VALID_TRANSITIONS: dict[CampaignStatus, set[CampaignStatus]] = {
        CampaignStatus.CREATED: {CampaignStatus.ACTIVE},
        CampaignStatus.ACTIVE: {
            CampaignStatus.PAUSED,
            CampaignStatus.COMPLETED,
        },
        CampaignStatus.PAUSED: {
            CampaignStatus.ACTIVE,
            CampaignStatus.ARCHIVED,
        },
        CampaignStatus.COMPLETED: {CampaignStatus.ARCHIVED},
        CampaignStatus.ARCHIVED: set(),
    }
    
    def list(
        self,
        process_id: UUID | None = None,
        status: CampaignStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Campaign]:
        """List campaigns with optional filters."""
        stmt = select(Campaign)
        
        if process_id is not None:
            stmt = stmt.where(Campaign.process_id == process_id)
        if status is not None:
            stmt = stmt.where(Campaign.status == status)
        
        stmt = stmt.order_by(col(Campaign.created_at).desc())
        stmt = stmt.offset(offset).limit(limit)
        
        return list(self.session.exec(stmt).all())
    
    def update_status(
        self,
        campaign_id: UUID,
        new_status: CampaignStatus,
    ) -> Campaign:
        """Update campaign status with validation."""
        campaign = self.get_or_raise(campaign_id)
        
        valid_next = self.VALID_TRANSITIONS.get(campaign.status, set())
        if new_status not in valid_next:
            raise InvalidStateTransitionError(
                f"Cannot transition from {campaign.status.value} to {new_status.value}. "
                f"Valid transitions: {[s.value for s in valid_next]}"
            )
        
        campaign.status = new_status
        return self.update(campaign)
    
    def acquire_write_lock(
        self,
        campaign_id: UUID,
        locked_by: str,
        timeout_seconds: float = 30.0,
    ) -> bool:
        """
        Acquire write lock for a campaign.
        
        Args:
            campaign_id: Campaign to lock
            locked_by: Identifier of lock holder
            timeout_seconds: Lock expiration time
            
        Returns:
            True if lock acquired, False if already locked
            
        Raises:
            CampaignLockedError: If locked by another holder
        """
        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=timeout_seconds)
        
        # Check existing lock
        existing = self.session.get(CampaignLock, campaign_id)
        
        if existing:
            if existing.expires_at > now and existing.locked_by != locked_by:
                # Lock held by someone else
                raise CampaignLockedError(
                    campaign_id, existing.locked_by, existing.expires_at
                )
            # Lock expired or same holder - update it
            existing.locked_by = locked_by
            existing.locked_at = now
            existing.expires_at = expires_at
            self.session.add(existing)
        else:
            # Create new lock
            lock = CampaignLock(
                campaign_id=campaign_id,
                locked_by=locked_by,
                locked_at=now,
                expires_at=expires_at,
            )
            self.session.add(lock)
        
        self.session.flush()
        return True
    
    def release_write_lock(self, campaign_id: UUID, locked_by: str | None = None) -> bool:
        """
        Release write lock for a campaign.
        
        Args:
            campaign_id: Campaign to unlock
            locked_by: Optional - only release if held by this holder
            
        Returns:
            True if released, False if not locked or wrong holder
        """
        existing = self.session.get(CampaignLock, campaign_id)
        
        if not existing:
            return False
        
        if locked_by and existing.locked_by != locked_by:
            return False
        
        self.session.delete(existing)
        self.session.flush()
        return True
    
    def is_locked(self, campaign_id: UUID) -> tuple[bool, CampaignLock | None]:
        """Check if campaign is locked."""
        lock = self.session.get(CampaignLock, campaign_id)
        
        if lock and lock.expires_at > datetime.utcnow():
            return True, lock
        
        return False, None
    
    def cleanup_expired_locks(self) -> int:
        """Remove expired locks. Returns count removed."""
        now = datetime.utcnow()
        stmt = select(CampaignLock).where(CampaignLock.expires_at <= now)
        expired = list(self.session.exec(stmt).all())
        
        for lock in expired:
            self.session.delete(lock)
        
        self.session.flush()
        return len(expired)


# =============================================================================
# Observation Repository
# =============================================================================


class ObservationRepository(BaseRepository[Observation]):
    """Repository for Observation entities."""
    
    model = Observation
    
    def list(
        self,
        campaign_id: UUID,
        source: str | None = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[Observation]:
        """List observations for a campaign."""
        stmt = select(Observation).where(Observation.campaign_id == campaign_id)
        
        if source is not None:
            stmt = stmt.where(Observation.source == source)
        
        stmt = stmt.order_by(col(Observation.observed_at).asc())
        stmt = stmt.offset(offset).limit(limit)
        
        return list(self.session.exec(stmt).all())
    
    def count(self, campaign_id: UUID) -> int:
        """Count observations for a campaign."""
        from sqlalchemy import func
        stmt = select(func.count()).select_from(Observation).where(
            Observation.campaign_id == campaign_id
        )
        return self.session.exec(stmt).one()
    
    def bulk_create(self, observations: list[Observation]) -> list[Observation]:
        """Bulk insert observations."""
        for obs in observations:
            self.session.add(obs)
        self.session.flush()
        for obs in observations:
            self.session.refresh(obs)
        return observations


# =============================================================================
# Iteration Repository
# =============================================================================


class IterationRepository(BaseRepository[Iteration]):
    """Repository for Iteration entities."""
    
    model = Iteration
    
    def list(
        self,
        campaign_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Iteration]:
        """List iterations for a campaign."""
        stmt = select(Iteration).where(Iteration.campaign_id == campaign_id)
        stmt = stmt.order_by(col(Iteration.index).asc())
        stmt = stmt.offset(offset).limit(limit)
        
        return list(self.session.exec(stmt).all())
    
    def get_by_index(self, campaign_id: UUID, index: int) -> Iteration | None:
        """Get iteration by campaign and index."""
        stmt = select(Iteration).where(
            Iteration.campaign_id == campaign_id,
            Iteration.index == index,
        )
        return self.session.exec(stmt).first()
    
    def get_latest(self, campaign_id: UUID) -> Iteration | None:
        """Get the latest iteration for a campaign."""
        stmt = select(Iteration).where(Iteration.campaign_id == campaign_id)
        stmt = stmt.order_by(col(Iteration.index).desc()).limit(1)
        return self.session.exec(stmt).first()
    
    def next_index(self, campaign_id: UUID) -> int:
        """Get the next iteration index for a campaign."""
        latest = self.get_latest(campaign_id)
        return (latest.index + 1) if latest else 0


# =============================================================================
# Proposal Repository
# =============================================================================


class ProposalRepository(BaseRepository[Proposal]):
    """Repository for Proposal entities."""
    
    model = Proposal
    
    def list(
        self,
        iteration_id: UUID,
        strategy_name: str | None = None,
    ) -> list[Proposal]:
        """List proposals for an iteration."""
        stmt = select(Proposal).where(Proposal.iteration_id == iteration_id)
        
        if strategy_name is not None:
            stmt = stmt.where(Proposal.strategy_name == strategy_name)
        
        stmt = stmt.order_by(col(Proposal.created_at).asc())
        
        return list(self.session.exec(stmt).all())
    
    def get_by_strategy(
        self,
        iteration_id: UUID,
        strategy_name: str,
    ) -> Proposal | None:
        """Get proposal by iteration and strategy."""
        stmt = select(Proposal).where(
            Proposal.iteration_id == iteration_id,
            Proposal.strategy_name == strategy_name,
        )
        return self.session.exec(stmt).first()


# =============================================================================
# Decision Repository
# =============================================================================


class DecisionRepository(BaseRepository[Decision]):
    """Repository for Decision entities."""
    
    model = Decision
    
    def get_by_iteration(self, iteration_id: UUID) -> Decision | None:
        """Get decision for an iteration."""
        stmt = select(Decision).where(Decision.iteration_id == iteration_id)
        return self.session.exec(stmt).first()
    
    def has_decision(self, iteration_id: UUID) -> bool:
        """Check if iteration has a decision."""
        return self.get_by_iteration(iteration_id) is not None


# =============================================================================
# Checkpoint Repository
# =============================================================================


class CheckpointRepository(BaseRepository[Checkpoint]):
    """Repository for Checkpoint entities."""
    
    model = Checkpoint
    
    def list(
        self,
        campaign_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Checkpoint]:
        """List checkpoints for a campaign."""
        stmt = select(Checkpoint).where(Checkpoint.campaign_id == campaign_id)
        stmt = stmt.order_by(col(Checkpoint.created_at).desc())
        stmt = stmt.offset(offset).limit(limit)
        
        return list(self.session.exec(stmt).all())
    
    def get_latest(self, campaign_id: UUID) -> Checkpoint | None:
        """Get the latest checkpoint for a campaign."""
        stmt = select(Checkpoint).where(Checkpoint.campaign_id == campaign_id)
        stmt = stmt.order_by(col(Checkpoint.created_at).desc()).limit(1)
        return self.session.exec(stmt).first()
    
    def get_by_iteration(
        self,
        campaign_id: UUID,
        iteration_id: UUID,
    ) -> Checkpoint | None:
        """Get checkpoint for a specific iteration."""
        stmt = select(Checkpoint).where(
            Checkpoint.campaign_id == campaign_id,
            Checkpoint.iteration_id == iteration_id,
        )
        return self.session.exec(stmt).first()
    
    def cleanup_old(self, campaign_id: UUID, keep_last: int = 5) -> list[Checkpoint]:
        """
        Remove old checkpoints, keeping the latest N.
        
        Returns list of removed checkpoints (caller should delete files).
        """
        all_checkpoints = self.list(campaign_id, limit=1000)
        
        if len(all_checkpoints) <= keep_last:
            return []
        
        to_remove = all_checkpoints[keep_last:]
        for cp in to_remove:
            self.session.delete(cp)
        
        self.session.flush()
        return to_remove


# =============================================================================
# Artifact Repository
# =============================================================================


class ArtifactRepository(BaseRepository[Artifact]):
    """Repository for Artifact entities."""
    
    model = Artifact
    
    def list(
        self,
        campaign_id: UUID,
        artifact_type: str | None = None,
        iteration_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Artifact]:
        """List artifacts with optional filters."""
        stmt = select(Artifact).where(Artifact.campaign_id == campaign_id)
        
        if artifact_type is not None:
            stmt = stmt.where(Artifact.artifact_type == artifact_type)
        if iteration_id is not None:
            stmt = stmt.where(Artifact.iteration_id == iteration_id)
        
        stmt = stmt.order_by(col(Artifact.created_at).desc())
        stmt = stmt.offset(offset).limit(limit)
        
        return list(self.session.exec(stmt).all())
    
    def get_by_path(self, campaign_id: UUID, path: str) -> Artifact | None:
        """Get artifact by path."""
        stmt = select(Artifact).where(
            Artifact.campaign_id == campaign_id,
            Artifact.path == path,
        )
        return self.session.exec(stmt).first()


