"""
Fixtures for core engine tests.
"""

import tempfile
from pathlib import Path
from uuid import uuid4

import pytest
from sqlmodel import Session, create_engine, SQLModel

from boa.db.models import Process, Campaign, CampaignStatus
from boa.spec.models import (
    ProcessSpec,
    ContinuousInput,
    ObjectiveSpec,
    StrategySpec,
)


@pytest.fixture
def engine():
    """Create in-memory SQLite engine."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    """Create database session."""
    with Session(engine) as session:
        yield session


@pytest.fixture
def simple_spec_yaml() -> str:
    """Simple spec YAML for testing."""
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
  - name: y1
    direction: maximize
    
  - name: y2
    direction: minimize

strategies:
  default:
    sampler: lhs_optimized
    model: gp_matern
    acquisition: qlogNEHVI
"""


@pytest.fixture
def simple_spec() -> ProcessSpec:
    """Simple ProcessSpec for testing."""
    return ProcessSpec(
        name="test",
        inputs=[
            ContinuousInput(name="x1", bounds=(0, 10)),
            ContinuousInput(name="x2", bounds=(-5, 5)),
        ],
        objectives=[
            ObjectiveSpec(name="y1"),
            ObjectiveSpec(name="y2"),
        ],
        strategies={
            "default": StrategySpec(
                name="default",
                sampler="lhs_optimized",
                model="gp_matern",
                acquisition="qlogNEHVI",
            ),
        },
    )


@pytest.fixture
def sample_process(session: Session, simple_spec_yaml: str) -> Process:
    """Create a sample process."""
    import yaml
    parsed = yaml.safe_load(simple_spec_yaml)
    
    process = Process(
        name="test_process",
        description="Test process",
        spec_yaml=simple_spec_yaml,
        spec_parsed=parsed,
    )
    session.add(process)
    session.commit()
    session.refresh(process)
    return process


@pytest.fixture
def sample_campaign(session: Session, sample_process: Process) -> Campaign:
    """Create a sample campaign."""
    campaign = Campaign(
        process_id=sample_process.id,
        name="test_campaign",
        description="Test campaign",
        status=CampaignStatus.CREATED,
    )
    session.add(campaign)
    session.commit()
    session.refresh(campaign)
    return campaign


@pytest.fixture
def temp_checkpoint_dir():
    """Create temporary checkpoint directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)





