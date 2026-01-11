"""
Tests for BOA proposal ledger.
"""

import pytest
from sqlmodel import Session, create_engine, SQLModel
from uuid import uuid4

from boa.db.models import Process, Campaign, CampaignStatus, Observation
from boa.core.ledger import ProposalLedger


@pytest.fixture
def engine():
    """Create in-memory SQLite engine."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    """Create database session."""
    with Session(engine) as sess:
        yield sess


@pytest.fixture
def sample_campaign(session: Session) -> Campaign:
    """Create a sample campaign with process."""
    process = Process(
        name="test",
        spec_yaml="name: test",
        spec_parsed={"name": "test"},
    )
    session.add(process)
    session.commit()
    
    campaign = Campaign(
        process_id=process.id,
        name="test_campaign",
        status=CampaignStatus.CREATED,
    )
    session.add(campaign)
    session.commit()
    session.refresh(campaign)
    return campaign


class TestProposalLedger:
    """Tests for ProposalLedger."""
    
    def test_start_iteration(self, session: Session, sample_campaign: Campaign):
        """Test starting a new iteration."""
        ledger = ProposalLedger(session, sample_campaign)
        
        iteration = ledger.start_iteration()
        
        assert iteration.index == 0
        assert iteration.campaign_id == sample_campaign.id
    
    def test_iteration_incrementing(self, session: Session, sample_campaign: Campaign):
        """Test that iteration indices increment."""
        ledger = ProposalLedger(session, sample_campaign)
        
        iter0 = ledger.start_iteration()
        iter1 = ledger.start_iteration()
        iter2 = ledger.start_iteration()
        
        assert iter0.index == 0
        assert iter1.index == 1
        assert iter2.index == 2
    
    def test_add_proposal(self, session: Session, sample_campaign: Campaign):
        """Test adding a proposal."""
        ledger = ProposalLedger(session, sample_campaign)
        iteration = ledger.start_iteration()
        
        candidates = [
            {"x1": 0.5, "x2": 0.3},
            {"x1": 0.7, "x2": 0.1},
        ]
        
        proposal = ledger.add_proposal(
            iteration=iteration,
            strategy_name="default",
            candidates_raw=candidates,
        )
        
        assert proposal.strategy_name == "default"
        assert len(proposal.candidates_raw) == 2
    
    def test_get_proposals(self, session: Session, sample_campaign: Campaign):
        """Test getting proposals for an iteration."""
        ledger = ProposalLedger(session, sample_campaign)
        iteration = ledger.start_iteration()
        
        ledger.add_proposal(iteration, "strategy1", [{"x": 0.1}])
        ledger.add_proposal(iteration, "strategy2", [{"x": 0.2}])
        
        proposals = ledger.get_proposals(iteration)
        
        assert len(proposals) == 2
        strategy_names = {p.strategy_name for p in proposals}
        assert strategy_names == {"strategy1", "strategy2"}
    
    def test_record_decision(self, session: Session, sample_campaign: Campaign):
        """Test recording a decision."""
        ledger = ProposalLedger(session, sample_campaign)
        iteration = ledger.start_iteration()
        
        proposal = ledger.add_proposal(iteration, "default", [{"x": 0.5}])
        
        decision = ledger.record_decision(
            iteration=iteration,
            accepted=[{"proposal_id": str(proposal.id), "candidate_indices": [0]}],
            notes="Looks good",
        )
        
        assert decision.notes == "Looks good"
        assert len(decision.accepted) == 1
    
    def test_decision_one_per_iteration(self, session: Session, sample_campaign: Campaign):
        """Test that only one decision allowed per iteration."""
        ledger = ProposalLedger(session, sample_campaign)
        iteration = ledger.start_iteration()
        
        ledger.add_proposal(iteration, "default", [{"x": 0.5}])
        ledger.record_decision(iteration, [])
        
        with pytest.raises(ValueError, match="already exists"):
            ledger.record_decision(iteration, [])
    
    def test_add_observation(self, session: Session, sample_campaign: Campaign):
        """Test adding an observation."""
        ledger = ProposalLedger(session, sample_campaign)
        
        obs = ledger.add_observation(
            x_raw={"x1": 0.5, "x2": 0.3},
            y={"y1": 1.5, "y2": 0.8},
            source="user",
        )
        
        assert obs.x_raw == {"x1": 0.5, "x2": 0.3}
        assert obs.y == {"y1": 1.5, "y2": 0.8}
        assert obs.source == "user"
    
    def test_get_observations(self, session: Session, sample_campaign: Campaign):
        """Test getting all observations."""
        ledger = ProposalLedger(session, sample_campaign)
        
        ledger.add_observation({"x": 0.1}, {"y": 1.0})
        ledger.add_observation({"x": 0.2}, {"y": 2.0})
        ledger.add_observation({"x": 0.3}, {"y": 3.0})
        
        observations = ledger.get_observations()
        
        assert len(observations) == 3
    
    def test_add_observations_batch(self, session: Session, sample_campaign: Campaign):
        """Test batch adding observations."""
        ledger = ProposalLedger(session, sample_campaign)
        
        obs_data = [
            {"x_raw": {"x": 0.1}, "y": {"y": 1.0}},
            {"x_raw": {"x": 0.2}, "y": {"y": 2.0}},
            {"x_raw": {"x": 0.3}, "y": {"y": 3.0}},
        ]
        
        created = ledger.add_observations_batch(obs_data)
        
        assert len(created) == 3
    
    def test_campaign_status_update(self, session: Session, sample_campaign: Campaign):
        """Test that starting iteration updates campaign status."""
        ledger = ProposalLedger(session, sample_campaign)
        
        assert sample_campaign.status == CampaignStatus.CREATED
        
        ledger.start_iteration()
        session.refresh(sample_campaign)
        
        assert sample_campaign.status == CampaignStatus.ACTIVE





