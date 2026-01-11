"""
Test fixtures for BOA database layer.

Provides in-memory SQLite databases and session management for tests.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Generator
from uuid import uuid4

import pytest
from sqlalchemy.engine import Engine
from sqlmodel import Session

# Remove unnecessary path manipulation - package should be installed

from boa.db.connection import (
    create_engine_from_settings,
    create_db_and_tables,
    drop_db_and_tables,
    DatabaseSettings,
    _engine_cache,
)
from boa.db.models import Process, Campaign, CampaignStatus


@pytest.fixture(scope="function")
def engine() -> Generator[Engine, None, None]:
    """Create an in-memory SQLite engine for testing."""
    # Clear any cached engine
    _engine_cache.clear()
    
    settings = DatabaseSettings.in_memory()
    eng = create_engine_from_settings(settings)
    create_db_and_tables(eng)
    
    yield eng
    
    drop_db_and_tables(eng)
    eng.dispose()
    _engine_cache.clear()


@pytest.fixture(scope="function")
def session(engine: Engine) -> Generator[Session, None, None]:
    """Create a test session."""
    sess = Session(engine)
    try:
        yield sess
        sess.commit()
    except Exception:
        sess.rollback()
        raise
    finally:
        sess.close()


@pytest.fixture
def sample_process(session: Session) -> Process:
    """Create a sample process for testing."""
    process = Process(
        id=uuid4(),
        name="test_process",
        description="A test process",
        spec_yaml="name: test\ninputs: []\nobjectives: []",
        spec_parsed={"name": "test", "inputs": [], "objectives": []},
        version=1,
        is_active=True,
    )
    session.add(process)
    session.commit()
    session.refresh(process)
    return process


@pytest.fixture
def sample_campaign(session: Session, sample_process: Process) -> Campaign:
    """Create a sample campaign for testing."""
    campaign = Campaign(
        id=uuid4(),
        process_id=sample_process.id,
        name="test_campaign",
        description="A test campaign",
        status=CampaignStatus.CREATED,
        strategy_config={"default": {"sampler": "lhs"}},
    )
    session.add(campaign)
    session.commit()
    session.refresh(campaign)
    return campaign
