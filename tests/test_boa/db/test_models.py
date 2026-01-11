"""
Tests for BOA database models.

Tests ORM model creation, relationships, JSON columns, and enums.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

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
    Job,
    CampaignLock,
    CampaignStatus,
    JobStatus,
    JobType,
)


class TestProcessModel:
    """Tests for Process model."""
    
    def test_create_process(self, session: Session) -> None:
        """Test creating a process."""
        process = Process(
            name="perovskite_opt",
            description="Perovskite optimization",
            spec_yaml="name: perovskite\nversion: 1",
            spec_parsed={"name": "perovskite", "version": 1},
            version=1,
            is_active=True,
        )
        session.add(process)
        session.commit()
        session.refresh(process)
        
        assert process.id is not None
        assert process.name == "perovskite_opt"
        assert process.version == 1
        assert process.is_active is True
        assert process.created_at is not None
        assert process.updated_at is None
    
    def test_process_json_column(self, session: Session) -> None:
        """Test JSON column storage and retrieval."""
        spec = {
            "inputs": [
                {"name": "temp", "type": "continuous", "bounds": [20, 100]},
                {"name": "speed", "type": "discrete", "values": [10, 20, 30]},
            ],
            "objectives": [
                {"name": "efficiency", "direction": "maximize"},
            ],
        }
        
        process = Process(
            name="test_json",
            spec_yaml="...",
            spec_parsed=spec,
        )
        session.add(process)
        session.commit()
        
        # Reload from database
        loaded = session.get(Process, process.id)
        assert loaded is not None
        assert loaded.spec_parsed == spec
        assert loaded.spec_parsed["inputs"][0]["name"] == "temp"
    
    def test_process_repr(self, session: Session) -> None:
        """Test process string representation."""
        process = Process(name="test", spec_yaml="...", spec_parsed={})
        session.add(process)
        session.commit()
        
        repr_str = repr(process)
        assert "Process" in repr_str
        assert "test" in repr_str


class TestCampaignModel:
    """Tests for Campaign model."""
    
    def test_create_campaign(self, session: Session, sample_process: Process) -> None:
        """Test creating a campaign."""
        campaign = Campaign(
            process_id=sample_process.id,
            name="run_001",
            description="First optimization run",
            status=CampaignStatus.CREATED,
            strategy_config={"default": {"sampler": "lhs"}},
        )
        session.add(campaign)
        session.commit()
        session.refresh(campaign)
        
        assert campaign.id is not None
        assert campaign.process_id == sample_process.id
        assert campaign.status == CampaignStatus.CREATED
        assert campaign.strategy_config["default"]["sampler"] == "lhs"
    
    def test_campaign_process_relationship(
        self, session: Session, sample_process: Process
    ) -> None:
        """Test campaign-process relationship."""
        campaign = Campaign(
            process_id=sample_process.id,
            name="run_002",
            status=CampaignStatus.CREATED,
        )
        session.add(campaign)
        session.commit()
        session.refresh(campaign)
        session.refresh(sample_process)
        
        # Relationship access
        assert campaign.process.id == sample_process.id
        assert campaign.process.name == sample_process.name
        
        # Reverse relationship
        assert len(sample_process.campaigns) >= 1
        assert any(c.id == campaign.id for c in sample_process.campaigns)
    
    def test_campaign_status_enum(self, session: Session, sample_process: Process) -> None:
        """Test campaign status enum values."""
        campaign = Campaign(
            process_id=sample_process.id,
            name="status_test",
            status=CampaignStatus.ACTIVE,
        )
        session.add(campaign)
        session.commit()
        
        loaded = session.get(Campaign, campaign.id)
        assert loaded is not None
        assert loaded.status == CampaignStatus.ACTIVE
        assert loaded.status.value == "active"
        
        # Update status
        loaded.status = CampaignStatus.PAUSED
        session.commit()
        
        reloaded = session.get(Campaign, campaign.id)
        assert reloaded is not None
        assert reloaded.status == CampaignStatus.PAUSED


class TestObservationModel:
    """Tests for Observation model."""
    
    def test_create_observation(self, session: Session, sample_campaign: Campaign) -> None:
        """Test creating an observation."""
        obs = Observation(
            campaign_id=sample_campaign.id,
            x_raw={"temp": 50.0, "speed": 20},
            x_encoded=[0.5, 0.5],
            y={"efficiency": 18.5, "stability": 95.0},
            source="user",
        )
        session.add(obs)
        session.commit()
        session.refresh(obs)
        
        assert obs.id is not None
        assert obs.x_raw["temp"] == 50.0
        assert obs.y["efficiency"] == 18.5
        assert obs.source == "user"
        assert obs.observed_at is not None
    
    def test_observation_json_columns(
        self, session: Session, sample_campaign: Campaign
    ) -> None:
        """Test observation JSON column round-trip."""
        x_raw = {"temp": 75.0, "speed": 30, "solvent": "DMF"}
        y = {"efficiency": 20.0}
        
        obs = Observation(
            campaign_id=sample_campaign.id,
            x_raw=x_raw,
            y=y,
        )
        session.add(obs)
        session.commit()
        
        loaded = session.get(Observation, obs.id)
        assert loaded is not None
        assert loaded.x_raw == x_raw
        assert loaded.y == y


class TestIterationModel:
    """Tests for Iteration model."""
    
    def test_create_iteration(self, session: Session, sample_campaign: Campaign) -> None:
        """Test creating an iteration."""
        iteration = Iteration(
            campaign_id=sample_campaign.id,
            index=0,
            dataset_hash="abc123def",
        )
        session.add(iteration)
        session.commit()
        session.refresh(iteration)
        
        assert iteration.id is not None
        assert iteration.index == 0
        assert iteration.dataset_hash == "abc123def"
    
    def test_iteration_proposals_relationship(
        self, session: Session, sample_campaign: Campaign
    ) -> None:
        """Test iteration-proposals relationship."""
        iteration = Iteration(
            campaign_id=sample_campaign.id,
            index=0,
        )
        session.add(iteration)
        session.commit()
        
        proposal = Proposal(
            iteration_id=iteration.id,
            strategy_name="default",
            candidates_raw=[{"temp": 50.0}, {"temp": 60.0}],
        )
        session.add(proposal)
        session.commit()
        session.refresh(iteration)
        
        assert len(iteration.proposals) == 1
        assert iteration.proposals[0].strategy_name == "default"


class TestProposalModel:
    """Tests for Proposal model."""
    
    def test_create_proposal(self, session: Session, sample_campaign: Campaign) -> None:
        """Test creating a proposal."""
        iteration = Iteration(campaign_id=sample_campaign.id, index=0)
        session.add(iteration)
        session.commit()
        
        proposal = Proposal(
            iteration_id=iteration.id,
            strategy_name="qnehvi",
            candidates_raw=[
                {"temp": 50.0, "speed": 20},
                {"temp": 60.0, "speed": 30},
            ],
            candidates_encoded=[[0.5, 0.5], [0.6, 0.7]],
            acq_values=[0.85, 0.72],
            predictions={
                "mean": [[18.0], [19.5]],
                "std": [[1.2], [0.8]],
            },
        )
        session.add(proposal)
        session.commit()
        session.refresh(proposal)
        
        assert proposal.id is not None
        assert proposal.strategy_name == "qnehvi"
        assert len(proposal.candidates_raw) == 2
        assert proposal.acq_values[0] == 0.85


class TestDecisionModel:
    """Tests for Decision model."""
    
    def test_create_decision(self, session: Session, sample_campaign: Campaign) -> None:
        """Test creating a decision."""
        iteration = Iteration(campaign_id=sample_campaign.id, index=0)
        session.add(iteration)
        session.commit()
        
        proposal = Proposal(
            iteration_id=iteration.id,
            strategy_name="default",
            candidates_raw=[{"temp": 50.0}, {"temp": 60.0}],
        )
        session.add(proposal)
        session.commit()
        
        decision = Decision(
            iteration_id=iteration.id,
            accepted=[
                {"proposal_id": str(proposal.id), "candidate_indices": [0, 1]},
            ],
            notes="Both candidates look promising",
        )
        session.add(decision)
        session.commit()
        session.refresh(decision)
        
        assert decision.id is not None
        assert len(decision.accepted) == 1
        assert decision.notes == "Both candidates look promising"
    
    def test_decision_one_per_iteration(
        self, session: Session, sample_campaign: Campaign
    ) -> None:
        """Test that only one decision per iteration is allowed."""
        from sqlalchemy.exc import IntegrityError
        
        iteration = Iteration(campaign_id=sample_campaign.id, index=0)
        session.add(iteration)
        session.commit()
        
        decision1 = Decision(iteration_id=iteration.id, accepted=[])
        session.add(decision1)
        session.commit()
        
        # Try to add second decision
        decision2 = Decision(iteration_id=iteration.id, accepted=[])
        session.add(decision2)
        
        with pytest.raises(IntegrityError):
            session.flush()
        
        # Rollback to clean up the failed transaction
        session.rollback()


class TestCheckpointModel:
    """Tests for Checkpoint model."""
    
    def test_create_checkpoint(self, session: Session, sample_campaign: Campaign) -> None:
        """Test creating a checkpoint."""
        iteration = Iteration(campaign_id=sample_campaign.id, index=0)
        session.add(iteration)
        session.commit()
        
        checkpoint = Checkpoint(
            campaign_id=sample_campaign.id,
            iteration_id=iteration.id,
            path="checkpoints/model_iter_0.pt",
            file_size_bytes=1024 * 1024,
            metadata_={"hyperparams": {"lr": 0.01}},
        )
        session.add(checkpoint)
        session.commit()
        session.refresh(checkpoint)
        
        assert checkpoint.id is not None
        assert checkpoint.path == "checkpoints/model_iter_0.pt"
        assert checkpoint.file_size_bytes == 1024 * 1024


class TestArtifactModel:
    """Tests for Artifact model."""
    
    def test_create_artifact(self, session: Session, sample_campaign: Campaign) -> None:
        """Test creating an artifact."""
        artifact = Artifact(
            campaign_id=sample_campaign.id,
            artifact_type="plot",
            name="parity_plot",
            path="plots/parity.png",
            content_type="image/png",
            file_size_bytes=50000,
        )
        session.add(artifact)
        session.commit()
        session.refresh(artifact)
        
        assert artifact.id is not None
        assert artifact.artifact_type == "plot"
        assert artifact.content_type == "image/png"


class TestJobModel:
    """Tests for Job model."""
    
    def test_create_job(self, session: Session, sample_campaign: Campaign) -> None:
        """Test creating a job."""
        job = Job(
            campaign_id=sample_campaign.id,
            job_type=JobType.PROPOSE,
            status=JobStatus.PENDING,
            params={"batch_size": 5, "strategies": ["default"]},
        )
        session.add(job)
        session.commit()
        session.refresh(job)
        
        assert job.id is not None
        assert job.job_type == JobType.PROPOSE
        assert job.status == JobStatus.PENDING
        assert job.params["batch_size"] == 5
    
    def test_job_lifecycle(self, session: Session, sample_campaign: Campaign) -> None:
        """Test job status transitions."""
        job = Job(
            campaign_id=sample_campaign.id,
            job_type=JobType.PROPOSE,
            params={},
        )
        session.add(job)
        session.commit()
        
        # Start job
        job.status = JobStatus.RUNNING
        job.started_at = datetime.utcnow()
        session.commit()
        
        assert job.status == JobStatus.RUNNING
        assert job.started_at is not None
        
        # Complete job
        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.utcnow()
        job.result = {"iteration_id": str(uuid4())}
        session.commit()
        
        assert job.status == JobStatus.COMPLETED
        assert job.result is not None


class TestCampaignLockModel:
    """Tests for CampaignLock model."""
    
    def test_create_lock(self, session: Session, sample_campaign: Campaign) -> None:
        """Test creating a campaign lock."""
        from datetime import timedelta
        
        now = datetime.utcnow()
        lock = CampaignLock(
            campaign_id=sample_campaign.id,
            locked_by="worker_1",
            locked_at=now,
            expires_at=now + timedelta(seconds=30),
        )
        session.add(lock)
        session.commit()
        
        loaded = session.get(CampaignLock, sample_campaign.id)
        assert loaded is not None
        assert loaded.locked_by == "worker_1"
        assert loaded.expires_at > now

