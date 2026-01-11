"""
Tests for BOA SDK client.
"""

import tempfile
from pathlib import Path

import pytest
from sqlmodel import SQLModel

from boa.db.connection import get_engine, _engine_cache
from boa.server.app import create_app
from boa.server.config import ServerConfig
from boa.sdk import BOAClient
from boa.sdk.exceptions import BOANotFoundError, BOAValidationError


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
    
    # Create tables
    engine = get_engine(test_config.database_url)
    SQLModel.metadata.create_all(engine)
    test_config.artifacts_dir.mkdir(parents=True, exist_ok=True)
    
    # Use TestClient as transport
    test_client = TestClient(app)
    
    # Create BOA client using the test client's transport
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


class TestBOAClient:
    """Tests for BOAClient."""
    
    def test_health(self, client: BOAClient):
        """Test health check."""
        result = client.health()
        
        assert result["status"] == "healthy"
        assert "version" in result
    
    def test_create_process(self, client: BOAClient, sample_spec_yaml: str):
        """Test creating a process."""
        result = client.create_process(
            "test_process",
            sample_spec_yaml,
            description="A test process",
        )
        
        assert result["name"] == "test_process"
        assert result["version"] == 1
        assert "id" in result
    
    def test_create_campaign(self, client: BOAClient, sample_spec_yaml: str):
        """Test creating a campaign."""
        # Create process first
        process = client.create_process("test", sample_spec_yaml)
        
        # Create campaign
        campaign = client.create_campaign(
            process_id=process["id"],
            name="test_campaign",
        )
        
        assert campaign["name"] == "test_campaign"
        assert campaign["status"] == "created"
    
    def test_add_observation(self, client: BOAClient, sample_spec_yaml: str):
        """Test adding an observation."""
        process = client.create_process("test", sample_spec_yaml)
        campaign = client.create_campaign(process["id"], "test")
        
        obs = client.add_observation(
            campaign["id"],
            x_raw={"x1": 5.0, "x2": 0.0},
            y={"y": 10.0},
        )
        
        assert obs["x_raw"] == {"x1": 5.0, "x2": 0.0}
        assert obs["y"] == {"y": 10.0}
    
    def test_initial_design(self, client: BOAClient, sample_spec_yaml: str):
        """Test generating initial design."""
        process = client.create_process("test", sample_spec_yaml)
        campaign = client.create_campaign(process["id"], "test")
        
        proposals = client.initial_design(campaign["id"], n_samples=5)
        
        assert len(proposals) >= 1
        assert len(proposals[0]["candidates_raw"]) == 5
    
    def test_propose_with_data(self, client: BOAClient, sample_spec_yaml: str):
        """Test generating proposals with training data."""
        process = client.create_process("test", sample_spec_yaml)
        campaign = client.create_campaign(process["id"], "test")
        
        # Add observations
        for i in range(10):
            client.add_observation(
                campaign["id"],
                x_raw={"x1": float(i), "x2": float(i - 5)},
                y={"y": float(i * 2)},
            )
        
        # Propose
        proposals = client.propose(campaign["id"], n_candidates=2)
        
        assert len(proposals) >= 1
        assert len(proposals[0]["candidates_raw"]) == 2
    
    def test_campaign_lifecycle(self, client: BOAClient, sample_spec_yaml: str):
        """Test campaign status transitions."""
        process = client.create_process("test", sample_spec_yaml)
        campaign = client.create_campaign(process["id"], "test")
        
        # Initial design activates campaign
        client.initial_design(campaign["id"], n_samples=3)
        
        campaign = client.get_campaign(campaign["id"])
        assert campaign["status"] == "active"
        
        # Pause
        client.pause_campaign(campaign["id"])
        campaign = client.get_campaign(campaign["id"])
        assert campaign["status"] == "paused"
        
        # Resume
        client.resume_campaign(campaign["id"])
        campaign = client.get_campaign(campaign["id"])
        assert campaign["status"] == "active"
        
        # Complete
        client.complete_campaign(campaign["id"])
        campaign = client.get_campaign(campaign["id"])
        assert campaign["status"] == "completed"
    
    def test_get_metrics(self, client: BOAClient, sample_spec_yaml: str):
        """Test getting campaign metrics."""
        process = client.create_process("test", sample_spec_yaml)
        campaign = client.create_campaign(process["id"], "test")
        
        # Add some observations
        for i in range(5):
            client.add_observation(
                campaign["id"],
                x_raw={"x1": float(i), "x2": 0.0},
                y={"y": float(i * 2)},
            )
        
        metrics = client.get_campaign_metrics(campaign["id"])
        
        assert metrics["n_observations"] == 5
        assert "best_values" in metrics
    
    def test_not_found_error(self, client: BOAClient):
        """Test not found error handling."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        
        with pytest.raises(BOANotFoundError):
            client.get_process(fake_id)
    
    def test_validation_error(self, client: BOAClient):
        """Test validation error handling."""
        with pytest.raises(BOAValidationError):
            client.create_process(
                "bad",
                "invalid: yaml: content",
            )

