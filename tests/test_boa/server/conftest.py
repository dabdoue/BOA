"""
Fixtures for server tests.
"""

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel

from boa.db.connection import get_engine, _engine_cache, create_db_and_tables
from boa.server.app import create_app
from boa.server.config import ServerConfig


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
    # Clear engine cache to ensure fresh database
    _engine_cache.clear()
    return create_app(test_config)


@pytest.fixture
def client(app, test_config: ServerConfig) -> TestClient:
    """Create test client with database tables created."""
    # Manually create tables since TestClient may not trigger lifespan properly
    engine = get_engine(test_config.database_url)
    SQLModel.metadata.create_all(engine)
    test_config.artifacts_dir.mkdir(parents=True, exist_ok=True)
    
    with TestClient(app) as client:
        yield client
    
    # Clean up
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

