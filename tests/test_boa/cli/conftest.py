"""
Pytest fixtures for CLI tests.
"""

import pytest
from uuid import uuid4

from sqlmodel import Session

from boa.db.models import Process, Campaign, CampaignStatus
from boa.db.connection import (
    DatabaseSettings,
    create_engine_from_settings,
    create_db_and_tables,
    drop_db_and_tables,
    session_manager,
)


@pytest.fixture
def db_settings():
    """Create test database settings."""
    return DatabaseSettings.in_memory()


@pytest.fixture
def engine(db_settings):
    """Create a test database engine."""
    eng = create_engine_from_settings(db_settings)
    create_db_and_tables(eng)
    yield eng
    drop_db_and_tables(eng)


@pytest.fixture
def session(engine):
    """Create a test database session."""
    with Session(engine) as session:
        yield session


@pytest.fixture
def sample_process():
    """Create a sample process."""
    return Process(
        id=uuid4(),
        name="cli_test_process",
        version=1,
        spec_yaml="""
inputs:
  - name: x
    type: continuous
    bounds: [0, 1]
objectives:
  - name: y
    target: minimize
""",
        is_active=True,
    )


@pytest.fixture
def sample_campaign(sample_process):
    """Create a sample campaign."""
    return Campaign(
        id=uuid4(),
        process_id=sample_process.id,
        name="cli_test_campaign",
        status=CampaignStatus.ACTIVE,
        metadata={"test": True},
    )





