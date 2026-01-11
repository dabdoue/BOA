"""
Tests for BOA campaign engine.
"""

import tempfile
from pathlib import Path

import numpy as np
import pytest
from sqlmodel import Session, create_engine, SQLModel

from boa.db.models import Process, Campaign, CampaignStatus
from boa.core.engine import CampaignEngine


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
def spec_yaml() -> str:
    """Simple spec YAML."""
    return """
name: test_process
version: 1

inputs:
  - name: x1
    type: continuous
    bounds: [0, 10]
    
  - name: x2
    type: continuous
    bounds: [-5, 5]

objectives:
  - name: y
    direction: maximize

strategies:
  default:
    sampler: random
    model: gp_matern
    acquisition: random
"""


@pytest.fixture
def sample_campaign(session: Session, spec_yaml: str) -> Campaign:
    """Create a sample campaign with process."""
    import yaml
    
    process = Process(
        name="test",
        spec_yaml=spec_yaml,
        spec_parsed=yaml.safe_load(spec_yaml),
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


class TestCampaignEngine:
    """Tests for CampaignEngine."""
    
    def test_initialization(self, session: Session, sample_campaign: Campaign):
        """Test engine initialization."""
        engine = CampaignEngine(session, sample_campaign)
        
        assert engine.spec.name == "test_process"
        assert engine.campaign == sample_campaign
        assert "default" in engine._executors
    
    def test_initial_design(self, session: Session, sample_campaign: Campaign):
        """Test running initial design."""
        engine = CampaignEngine(session, sample_campaign)
        
        result = engine.run_initial_design(n_samples=5)
        
        assert len(result.candidates_raw) == 5
        assert result.candidates_encoded.shape == (5, 2)
    
    def test_add_observation(self, session: Session, sample_campaign: Campaign):
        """Test adding an observation."""
        engine = CampaignEngine(session, sample_campaign)
        
        engine.add_observation(
            x_raw={"x1": 5.0, "x2": 0.0},
            y={"y": 10.0},
        )
        
        X, Y = engine.get_training_data()
        
        assert X.shape == (1, 2)
        assert Y.shape == (1, 1)
    
    def test_optimization_iteration(self, session: Session, sample_campaign: Campaign):
        """Test running optimization iteration."""
        engine = CampaignEngine(session, sample_campaign)
        
        # Add some initial observations
        for _ in range(10):
            x1 = np.random.uniform(0, 10)
            x2 = np.random.uniform(-5, 5)
            y = np.sin(x1 / 3) + x2 / 10
            engine.add_observation({"x1": x1, "x2": x2}, {"y": y})
        
        results = engine.run_optimization_iteration(n_candidates=2)
        
        assert "default" in results
        assert len(results["default"].candidates_raw) == 2
    
    def test_analyze(self, session: Session, sample_campaign: Campaign):
        """Test campaign analysis."""
        engine = CampaignEngine(session, sample_campaign)
        
        # Add observations
        for i in range(5):
            engine.add_observation(
                {"x1": float(i), "x2": 0.0},
                {"y": float(i * 2)},
            )
        
        metrics = engine.analyze()
        
        assert metrics.n_observations == 5
        assert metrics.best_values["y"] == 8.0  # 4 * 2
    
    def test_campaign_lifecycle(self, session: Session, sample_campaign: Campaign):
        """Test campaign status transitions."""
        engine = CampaignEngine(session, sample_campaign)
        
        assert sample_campaign.status == CampaignStatus.CREATED
        
        # Running initial design should activate
        engine.run_initial_design(3)
        session.refresh(sample_campaign)
        assert sample_campaign.status == CampaignStatus.ACTIVE
        
        # Pause
        engine.pause()
        session.refresh(sample_campaign)
        assert sample_campaign.status == CampaignStatus.PAUSED
        
        # Resume
        engine.resume()
        session.refresh(sample_campaign)
        assert sample_campaign.status == CampaignStatus.ACTIVE
        
        # Complete
        engine.complete()
        session.refresh(sample_campaign)
        assert sample_campaign.status == CampaignStatus.COMPLETED
    
    def test_with_checkpointing(self, session: Session, sample_campaign: Campaign):
        """Test engine with checkpointing enabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = CampaignEngine(
                session,
                sample_campaign,
                checkpoint_dir=Path(tmpdir),
            )
            
            # Add observations - use random x values to ensure diversity
            np.random.seed(42)
            for i in range(15):
                x1 = np.random.uniform(0, 10)
                x2 = np.random.uniform(-5, 5)
                y = np.sin(x1 / 3) + x2 / 10
                engine.add_observation({"x1": x1, "x2": x2}, {"y": y})
            
            # Run iteration
            results = engine.run_optimization_iteration(n_candidates=1)
            
            # Check checkpoint was saved
            checkpoints = engine.checkpointer.list_checkpoints()
            assert len(checkpoints) >= 1
    
    def test_dataset_hash(self, session: Session, sample_campaign: Campaign):
        """Test dataset hash computation."""
        engine = CampaignEngine(session, sample_campaign)
        
        # Empty dataset
        hash1 = engine.compute_dataset_hash()
        
        # Add observation
        engine.add_observation({"x1": 1.0, "x2": 2.0}, {"y": 3.0})
        hash2 = engine.compute_dataset_hash()
        
        # Add another
        engine.add_observation({"x1": 4.0, "x2": 5.0}, {"y": 6.0})
        hash3 = engine.compute_dataset_hash()
        
        # All should be different
        assert hash1 != hash2
        assert hash2 != hash3
        assert hash1 != hash3

