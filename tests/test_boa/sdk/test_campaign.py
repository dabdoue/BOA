"""
Tests for BOA SDK Campaign helper.
"""

import tempfile
from pathlib import Path

import pytest
from sqlmodel import SQLModel

from boa.db.connection import get_engine, _engine_cache
from boa.server.app import create_app
from boa.server.config import ServerConfig
from boa.sdk import BOAClient, Campaign
from boa.sdk.campaign import Proposal, Observation


@pytest.fixture
def temp_dir():
    """Create temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_config(temp_dir: Path) -> ServerConfig:
    """Create test configuration."""
    db_path = temp_dir / "test.db"
    return ServerConfig(
        database_url=f"sqlite:///{db_path}",
        artifacts_dir=temp_dir / "artifacts",
        debug=True,
    )


@pytest.fixture
def app(test_config: ServerConfig):
    """Create FastAPI app with test config."""
    _engine_cache.clear()
    return create_app(test_config)


@pytest.fixture
def client(app, test_config: ServerConfig) -> BOAClient:
    """Create BOA SDK client connected to test server."""
    from fastapi.testclient import TestClient
    
    engine = get_engine(test_config.database_url)
    SQLModel.metadata.create_all(engine)
    test_config.artifacts_dir.mkdir(parents=True, exist_ok=True)
    
    test_client = TestClient(app)
    
    boa_client = BOAClient.__new__(BOAClient)
    boa_client.base_url = ""
    boa_client.timeout = 30.0
    boa_client._client = test_client
    
    yield boa_client
    
    _engine_cache.clear()


@pytest.fixture
def sample_spec_yaml() -> str:
    """Sample spec YAML for testing."""
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
def campaign(client: BOAClient, sample_spec_yaml: str) -> Campaign:
    """Create a campaign and return Campaign helper."""
    process = client.create_process("test", sample_spec_yaml)
    campaign_data = client.create_campaign(process["id"], "test_campaign")
    return Campaign(client, campaign_data["id"])


class TestCampaign:
    """Tests for Campaign helper."""
    
    def test_properties(self, campaign: Campaign):
        """Test campaign properties."""
        assert campaign.name == "test_campaign"
        assert campaign.status == "created"
    
    def test_add_observation(self, campaign: Campaign):
        """Test adding an observation."""
        obs = campaign.add_observation(
            x={"x1": 5.0, "x2": 0.0},
            y={"y": 10.0},
        )
        
        assert isinstance(obs, Observation)
        assert obs.x == {"x1": 5.0, "x2": 0.0}
        assert obs.y == {"y": 10.0}
    
    def test_add_observations(self, campaign: Campaign):
        """Test adding multiple observations."""
        obs_data = [
            {"x": {"x1": 1.0, "x2": 0.0}, "y": {"y": 1.0}},
            {"x": {"x1": 2.0, "x2": 1.0}, "y": {"y": 2.5}},
            {"x": {"x1": 3.0, "x2": -1.0}, "y": {"y": 3.0}},
        ]
        
        observations = campaign.add_observations(obs_data)
        
        assert len(observations) == 3
        assert all(isinstance(o, Observation) for o in observations)
    
    def test_get_observations(self, campaign: Campaign):
        """Test getting observations."""
        campaign.add_observation({"x1": 1.0, "x2": 0.0}, {"y": 1.0})
        campaign.add_observation({"x1": 2.0, "x2": 0.0}, {"y": 2.0})
        
        observations = campaign.observations()
        
        assert len(observations) == 2
    
    def test_initial_design(self, campaign: Campaign):
        """Test generating initial design."""
        proposals = campaign.initial_design(n_samples=5)
        
        assert len(proposals) >= 1
        assert isinstance(proposals[0], Proposal)
        assert len(proposals[0]) == 5
    
    def test_propose(self, campaign: Campaign):
        """Test generating proposals."""
        # Add training data
        for i in range(10):
            campaign.add_observation(
                {"x1": float(i), "x2": float(i - 5)},
                {"y": float(i * 2)},
            )
        
        proposals = campaign.propose(n_candidates=2)
        
        assert len(proposals) >= 1
        assert len(proposals[0]) == 2
    
    def test_accept_all(self, campaign: Campaign):
        """Test accepting all proposals."""
        proposals = campaign.initial_design(n_samples=3)
        
        decision = campaign.accept_all(proposals, notes="Test acceptance")
        
        assert decision["notes"] == "Test acceptance"
        assert len(decision["accepted"]) >= 1
    
    def test_lifecycle(self, campaign: Campaign):
        """Test campaign lifecycle methods."""
        # Activate by running initial design
        campaign.initial_design(n_samples=3)
        assert campaign.refresh().status == "active"
        
        # Pause
        campaign.pause()
        assert campaign.status == "paused"
        
        # Resume
        campaign.resume()
        assert campaign.status == "active"
        
        # Complete
        campaign.complete()
        assert campaign.status == "completed"
    
    def test_metrics(self, campaign: Campaign):
        """Test getting metrics."""
        for i in range(5):
            campaign.add_observation(
                {"x1": float(i), "x2": 0.0},
                {"y": float(i * 2)},
            )
        
        metrics = campaign.metrics()
        
        assert metrics["n_observations"] == 5
        assert "best_values" in metrics
    
    def test_best(self, campaign: Campaign):
        """Test getting best observation."""
        campaign.add_observation({"x1": 1.0, "x2": 0.0}, {"y": 1.0})
        campaign.add_observation({"x1": 5.0, "x2": 0.0}, {"y": 10.0})
        campaign.add_observation({"x1": 3.0, "x2": 0.0}, {"y": 5.0})
        
        best = campaign.best()
        
        assert best is not None
        assert best["y"]["y"] == 10.0





