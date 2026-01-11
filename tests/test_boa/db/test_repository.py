"""
Tests for BOA repository pattern.

Tests CRUD operations, write locking, and state transitions.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4
import time

import pytest
from sqlmodel import Session

from boa.db.models import (
    Process,
    Campaign,
    Observation,
    Iteration,
    Proposal,
    Decision,
    Checkpoint,
    Artifact,
    CampaignStatus,
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
    NotFoundError,
    CampaignLockedError,
    InvalidStateTransitionError,
)


class TestProcessRepository:
    """Tests for ProcessRepository."""
    
    def test_create_and_get(self, session: Session) -> None:
        """Test creating and retrieving a process."""
        repo = ProcessRepository(session)
        
        process = Process(
            name="test_process",
            spec_yaml="name: test",
            spec_parsed={"name": "test"},
        )
        created = repo.create(process)
        
        assert created.id is not None
        assert created.name == "test_process"
        
        retrieved = repo.get(created.id)
        assert retrieved is not None
        assert retrieved.id == created.id
    
    def test_get_not_found(self, session: Session) -> None:
        """Test getting non-existent process."""
        repo = ProcessRepository(session)
        
        result = repo.get(uuid4())
        assert result is None
    
    def test_get_or_raise(self, session: Session) -> None:
        """Test get_or_raise with missing entity."""
        repo = ProcessRepository(session)
        
        with pytest.raises(NotFoundError):
            repo.get_or_raise(uuid4())
    
    def test_list_processes(self, session: Session) -> None:
        """Test listing processes with filters."""
        repo = ProcessRepository(session)
        
        # Create multiple processes
        for i in range(5):
            process = Process(
                name=f"process_{i}",
                spec_yaml="...",
                spec_parsed={},
                is_active=(i % 2 == 0),
            )
            repo.create(process)
        
        # List all
        all_procs = repo.list()
        assert len(all_procs) == 5
        
        # List active only
        active = repo.list(is_active=True)
        assert len(active) == 3
        
        # List by name
        by_name = repo.list(name="process_2")
        assert len(by_name) == 1
        
        # Pagination
        page1 = repo.list(limit=2, offset=0)
        page2 = repo.list(limit=2, offset=2)
        assert len(page1) == 2
        assert len(page2) == 2
    
    def test_get_by_name(self, session: Session) -> None:
        """Test getting process by name."""
        repo = ProcessRepository(session)
        
        process = Process(
            name="unique_name",
            spec_yaml="...",
            spec_parsed={},
            is_active=True,
        )
        repo.create(process)
        
        found = repo.get_by_name("unique_name")
        assert found is not None
        assert found.id == process.id
        
        not_found = repo.get_by_name("nonexistent")
        assert not_found is None
    
    def test_create_version(self, session: Session) -> None:
        """Test creating a new version of a process."""
        repo = ProcessRepository(session)
        
        # Create initial version
        v1 = Process(
            name="versioned_process",
            spec_yaml="version: 1",
            spec_parsed={"version": 1},
            version=1,
            is_active=True,
        )
        repo.create(v1)
        
        # Create new version
        v2 = Process(
            name="versioned_process",
            spec_yaml="version: 2",
            spec_parsed={"version": 2},
        )
        created_v2 = repo.create_version(v2)
        
        assert created_v2.version == 2
        assert created_v2.is_active is True
        
        # Original should be inactive
        session.refresh(v1)
        assert v1.is_active is False
    
    def test_update_process(self, session: Session) -> None:
        """Test updating a process."""
        repo = ProcessRepository(session)
        
        process = Process(
            name="to_update",
            spec_yaml="...",
            spec_parsed={},
        )
        repo.create(process)
        
        process.description = "Updated description"
        updated = repo.update(process)
        
        assert updated.description == "Updated description"
        assert updated.updated_at is not None
    
    def test_delete_process(self, session: Session) -> None:
        """Test deleting a process."""
        repo = ProcessRepository(session)
        
        process = Process(name="to_delete", spec_yaml="...", spec_parsed={})
        repo.create(process)
        process_id = process.id
        
        repo.delete(process)
        session.commit()
        
        assert repo.get(process_id) is None
    
    def test_delete_by_id(self, session: Session) -> None:
        """Test delete_by_id."""
        repo = ProcessRepository(session)
        
        process = Process(name="to_delete", spec_yaml="...", spec_parsed={})
        repo.create(process)
        process_id = process.id
        
        result = repo.delete_by_id(process_id)
        assert result is True
        
        result = repo.delete_by_id(uuid4())
        assert result is False


class TestCampaignRepository:
    """Tests for CampaignRepository with locking."""
    
    def test_create_and_list(
        self, session: Session, sample_process: Process
    ) -> None:
        """Test creating and listing campaigns."""
        repo = CampaignRepository(session)
        
        campaign = Campaign(
            process_id=sample_process.id,
            name="test_campaign",
            status=CampaignStatus.CREATED,
        )
        created = repo.create(campaign)
        
        campaigns = repo.list(process_id=sample_process.id)
        assert len(campaigns) >= 1
        assert any(c.id == created.id for c in campaigns)
    
    def test_list_by_status(
        self, session: Session, sample_process: Process
    ) -> None:
        """Test listing campaigns by status."""
        repo = CampaignRepository(session)
        
        for status in [CampaignStatus.CREATED, CampaignStatus.ACTIVE, CampaignStatus.COMPLETED]:
            campaign = Campaign(
                process_id=sample_process.id,
                name=f"campaign_{status.value}",
                status=status,
            )
            repo.create(campaign)
        
        active = repo.list(status=CampaignStatus.ACTIVE)
        assert len(active) == 1
        assert active[0].status == CampaignStatus.ACTIVE
    
    def test_update_status_valid_transition(
        self, session: Session, sample_process: Process
    ) -> None:
        """Test valid status transitions."""
        repo = CampaignRepository(session)
        
        campaign = Campaign(
            process_id=sample_process.id,
            name="status_test",
            status=CampaignStatus.CREATED,
        )
        repo.create(campaign)
        
        # CREATED -> ACTIVE
        updated = repo.update_status(campaign.id, CampaignStatus.ACTIVE)
        assert updated.status == CampaignStatus.ACTIVE
        
        # ACTIVE -> PAUSED
        updated = repo.update_status(campaign.id, CampaignStatus.PAUSED)
        assert updated.status == CampaignStatus.PAUSED
        
        # PAUSED -> ACTIVE
        updated = repo.update_status(campaign.id, CampaignStatus.ACTIVE)
        assert updated.status == CampaignStatus.ACTIVE
        
        # ACTIVE -> COMPLETED
        updated = repo.update_status(campaign.id, CampaignStatus.COMPLETED)
        assert updated.status == CampaignStatus.COMPLETED
        
        # COMPLETED -> ARCHIVED
        updated = repo.update_status(campaign.id, CampaignStatus.ARCHIVED)
        assert updated.status == CampaignStatus.ARCHIVED
    
    def test_update_status_invalid_transition(
        self, session: Session, sample_process: Process
    ) -> None:
        """Test invalid status transitions."""
        repo = CampaignRepository(session)
        
        campaign = Campaign(
            process_id=sample_process.id,
            name="invalid_transition",
            status=CampaignStatus.CREATED,
        )
        repo.create(campaign)
        
        # Cannot go directly from CREATED to COMPLETED
        with pytest.raises(InvalidStateTransitionError):
            repo.update_status(campaign.id, CampaignStatus.COMPLETED)
    
    def test_acquire_write_lock(
        self, session: Session, sample_campaign: Campaign
    ) -> None:
        """Test acquiring a write lock."""
        repo = CampaignRepository(session)
        
        result = repo.acquire_write_lock(
            sample_campaign.id,
            locked_by="worker_1",
            timeout_seconds=30.0,
        )
        assert result is True
        
        is_locked, lock = repo.is_locked(sample_campaign.id)
        assert is_locked is True
        assert lock is not None
        assert lock.locked_by == "worker_1"
    
    def test_lock_conflict(
        self, session: Session, sample_campaign: Campaign
    ) -> None:
        """Test lock conflict between different holders."""
        repo = CampaignRepository(session)
        
        # First worker acquires lock
        repo.acquire_write_lock(sample_campaign.id, "worker_1", 30.0)
        
        # Second worker should fail
        with pytest.raises(CampaignLockedError) as exc_info:
            repo.acquire_write_lock(sample_campaign.id, "worker_2", 30.0)
        
        assert exc_info.value.campaign_id == sample_campaign.id
        assert exc_info.value.locked_by == "worker_1"
    
    def test_same_holder_can_reacquire(
        self, session: Session, sample_campaign: Campaign
    ) -> None:
        """Test that same holder can reacquire lock."""
        repo = CampaignRepository(session)
        
        repo.acquire_write_lock(sample_campaign.id, "worker_1", 30.0)
        
        # Same worker can reacquire
        result = repo.acquire_write_lock(sample_campaign.id, "worker_1", 60.0)
        assert result is True
    
    def test_release_write_lock(
        self, session: Session, sample_campaign: Campaign
    ) -> None:
        """Test releasing a write lock."""
        repo = CampaignRepository(session)
        
        repo.acquire_write_lock(sample_campaign.id, "worker_1", 30.0)
        
        result = repo.release_write_lock(sample_campaign.id, "worker_1")
        assert result is True
        
        is_locked, _ = repo.is_locked(sample_campaign.id)
        assert is_locked is False
    
    def test_release_lock_wrong_holder(
        self, session: Session, sample_campaign: Campaign
    ) -> None:
        """Test that wrong holder cannot release lock."""
        repo = CampaignRepository(session)
        
        repo.acquire_write_lock(sample_campaign.id, "worker_1", 30.0)
        
        result = repo.release_write_lock(sample_campaign.id, "worker_2")
        assert result is False
        
        # Lock still held
        is_locked, lock = repo.is_locked(sample_campaign.id)
        assert is_locked is True
        assert lock.locked_by == "worker_1"
    
    def test_expired_lock_can_be_acquired(
        self, session: Session, sample_campaign: Campaign
    ) -> None:
        """Test that expired locks can be acquired by others."""
        repo = CampaignRepository(session)
        
        # Acquire lock with very short timeout
        repo.acquire_write_lock(sample_campaign.id, "worker_1", 0.1)
        
        # Wait for expiration
        time.sleep(0.2)
        
        # Check lock is expired
        is_locked, lock = repo.is_locked(sample_campaign.id)
        assert is_locked is False
        
        # Another worker can now acquire
        result = repo.acquire_write_lock(sample_campaign.id, "worker_2", 30.0)
        assert result is True
    
    def test_cleanup_expired_locks(
        self, session: Session, sample_campaign: Campaign
    ) -> None:
        """Test cleaning up expired locks."""
        repo = CampaignRepository(session)
        
        # Create expired lock
        repo.acquire_write_lock(sample_campaign.id, "worker_1", 0.1)
        time.sleep(0.2)
        
        # Cleanup
        count = repo.cleanup_expired_locks()
        assert count == 1


class TestObservationRepository:
    """Tests for ObservationRepository."""
    
    def test_create_and_list(
        self, session: Session, sample_campaign: Campaign
    ) -> None:
        """Test creating and listing observations."""
        repo = ObservationRepository(session)
        
        for i in range(5):
            obs = Observation(
                campaign_id=sample_campaign.id,
                x_raw={"temp": 50 + i},
                y={"efficiency": 15 + i * 0.5},
                source="user" if i % 2 == 0 else "import",
            )
            repo.create(obs)
        
        all_obs = repo.list(sample_campaign.id)
        assert len(all_obs) == 5
        
        user_obs = repo.list(sample_campaign.id, source="user")
        assert len(user_obs) == 3
    
    def test_count(
        self, session: Session, sample_campaign: Campaign
    ) -> None:
        """Test counting observations."""
        repo = ObservationRepository(session)
        
        for i in range(10):
            obs = Observation(
                campaign_id=sample_campaign.id,
                x_raw={"temp": 50 + i},
                y={"efficiency": 15 + i},
            )
            repo.create(obs)
        
        count = repo.count(sample_campaign.id)
        assert count == 10
    
    def test_bulk_create(
        self, session: Session, sample_campaign: Campaign
    ) -> None:
        """Test bulk creating observations."""
        repo = ObservationRepository(session)
        
        observations = [
            Observation(
                campaign_id=sample_campaign.id,
                x_raw={"temp": 50 + i},
                y={"efficiency": 15 + i},
            )
            for i in range(100)
        ]
        
        created = repo.bulk_create(observations)
        assert len(created) == 100
        assert all(obs.id is not None for obs in created)


class TestIterationRepository:
    """Tests for IterationRepository."""
    
    def test_create_and_get_by_index(
        self, session: Session, sample_campaign: Campaign
    ) -> None:
        """Test creating iterations and getting by index."""
        repo = IterationRepository(session)
        
        for i in range(3):
            iteration = Iteration(
                campaign_id=sample_campaign.id,
                index=i,
            )
            repo.create(iteration)
        
        iter_1 = repo.get_by_index(sample_campaign.id, 1)
        assert iter_1 is not None
        assert iter_1.index == 1
    
    def test_get_latest(
        self, session: Session, sample_campaign: Campaign
    ) -> None:
        """Test getting latest iteration."""
        repo = IterationRepository(session)
        
        for i in range(5):
            iteration = Iteration(
                campaign_id=sample_campaign.id,
                index=i,
            )
            repo.create(iteration)
        
        latest = repo.get_latest(sample_campaign.id)
        assert latest is not None
        assert latest.index == 4
    
    def test_next_index(
        self, session: Session, sample_campaign: Campaign
    ) -> None:
        """Test getting next iteration index."""
        repo = IterationRepository(session)
        
        # No iterations yet
        assert repo.next_index(sample_campaign.id) == 0
        
        # Add some iterations
        for i in range(3):
            repo.create(Iteration(campaign_id=sample_campaign.id, index=i))
        
        assert repo.next_index(sample_campaign.id) == 3


class TestProposalRepository:
    """Tests for ProposalRepository."""
    
    def test_list_proposals(
        self, session: Session, sample_campaign: Campaign
    ) -> None:
        """Test listing proposals for an iteration."""
        iter_repo = IterationRepository(session)
        prop_repo = ProposalRepository(session)
        
        iteration = Iteration(campaign_id=sample_campaign.id, index=0)
        iter_repo.create(iteration)
        
        # Create proposals from multiple strategies
        for strategy in ["default", "exploration", "exploitation"]:
            proposal = Proposal(
                iteration_id=iteration.id,
                strategy_name=strategy,
                candidates_raw=[{"temp": 50}],
            )
            prop_repo.create(proposal)
        
        all_props = prop_repo.list(iteration.id)
        assert len(all_props) == 3
        
        default_prop = prop_repo.list(iteration.id, strategy_name="default")
        assert len(default_prop) == 1
    
    def test_get_by_strategy(
        self, session: Session, sample_campaign: Campaign
    ) -> None:
        """Test getting proposal by strategy name."""
        iter_repo = IterationRepository(session)
        prop_repo = ProposalRepository(session)
        
        iteration = Iteration(campaign_id=sample_campaign.id, index=0)
        iter_repo.create(iteration)
        
        proposal = Proposal(
            iteration_id=iteration.id,
            strategy_name="qnehvi",
            candidates_raw=[{"temp": 50}],
        )
        prop_repo.create(proposal)
        
        found = prop_repo.get_by_strategy(iteration.id, "qnehvi")
        assert found is not None
        assert found.strategy_name == "qnehvi"
        
        not_found = prop_repo.get_by_strategy(iteration.id, "nonexistent")
        assert not_found is None


class TestDecisionRepository:
    """Tests for DecisionRepository."""
    
    def test_get_by_iteration(
        self, session: Session, sample_campaign: Campaign
    ) -> None:
        """Test getting decision by iteration."""
        iter_repo = IterationRepository(session)
        dec_repo = DecisionRepository(session)
        
        iteration = Iteration(campaign_id=sample_campaign.id, index=0)
        iter_repo.create(iteration)
        
        decision = Decision(
            iteration_id=iteration.id,
            accepted=[{"proposal_id": str(uuid4()), "indices": [0]}],
        )
        dec_repo.create(decision)
        
        found = dec_repo.get_by_iteration(iteration.id)
        assert found is not None
        assert found.id == decision.id
    
    def test_has_decision(
        self, session: Session, sample_campaign: Campaign
    ) -> None:
        """Test checking if iteration has decision."""
        iter_repo = IterationRepository(session)
        dec_repo = DecisionRepository(session)
        
        iteration = Iteration(campaign_id=sample_campaign.id, index=0)
        iter_repo.create(iteration)
        
        assert dec_repo.has_decision(iteration.id) is False
        
        decision = Decision(iteration_id=iteration.id, accepted=[])
        dec_repo.create(decision)
        
        assert dec_repo.has_decision(iteration.id) is True


class TestCheckpointRepository:
    """Tests for CheckpointRepository."""
    
    def test_list_and_get_latest(
        self, session: Session, sample_campaign: Campaign
    ) -> None:
        """Test listing checkpoints and getting latest."""
        repo = CheckpointRepository(session)
        iter_repo = IterationRepository(session)
        
        for i in range(5):
            iteration = Iteration(campaign_id=sample_campaign.id, index=i)
            iter_repo.create(iteration)
            
            checkpoint = Checkpoint(
                campaign_id=sample_campaign.id,
                iteration_id=iteration.id,
                path=f"checkpoints/iter_{i}.pt",
            )
            repo.create(checkpoint)
        
        all_cp = repo.list(sample_campaign.id)
        assert len(all_cp) == 5
        
        latest = repo.get_latest(sample_campaign.id)
        assert latest is not None
        assert "iter_4" in latest.path
    
    def test_cleanup_old(
        self, session: Session, sample_campaign: Campaign
    ) -> None:
        """Test cleaning up old checkpoints."""
        repo = CheckpointRepository(session)
        
        for i in range(10):
            checkpoint = Checkpoint(
                campaign_id=sample_campaign.id,
                path=f"checkpoints/iter_{i}.pt",
            )
            repo.create(checkpoint)
        
        removed = repo.cleanup_old(sample_campaign.id, keep_last=3)
        assert len(removed) == 7
        
        remaining = repo.list(sample_campaign.id)
        assert len(remaining) == 3


class TestArtifactRepository:
    """Tests for ArtifactRepository."""
    
    def test_list_with_filters(
        self, session: Session, sample_campaign: Campaign
    ) -> None:
        """Test listing artifacts with filters."""
        repo = ArtifactRepository(session)
        
        for artifact_type in ["plot", "report", "export"]:
            for i in range(3):
                artifact = Artifact(
                    campaign_id=sample_campaign.id,
                    artifact_type=artifact_type,
                    name=f"{artifact_type}_{i}",
                    path=f"artifacts/{artifact_type}_{i}.png",
                )
                repo.create(artifact)
        
        all_artifacts = repo.list(sample_campaign.id)
        assert len(all_artifacts) == 9
        
        plots = repo.list(sample_campaign.id, artifact_type="plot")
        assert len(plots) == 3
    
    def test_get_by_path(
        self, session: Session, sample_campaign: Campaign
    ) -> None:
        """Test getting artifact by path."""
        repo = ArtifactRepository(session)
        
        artifact = Artifact(
            campaign_id=sample_campaign.id,
            artifact_type="plot",
            name="parity",
            path="plots/parity.png",
        )
        repo.create(artifact)
        
        found = repo.get_by_path(sample_campaign.id, "plots/parity.png")
        assert found is not None
        assert found.name == "parity"
        
        not_found = repo.get_by_path(sample_campaign.id, "nonexistent.png")
        assert not_found is None

