"""
Alembic Environment Configuration

Configures Alembic to use SQLModel metadata and BOA database settings.
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Import SQLModel and all models to register them
from sqlmodel import SQLModel

# Import all models so they're registered with SQLModel.metadata
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
)

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use SQLModel's metadata for autogenerate
target_metadata = SQLModel.metadata


def get_url() -> str:
    """Get database URL from environment or config."""
    import os
    return os.getenv("BOA_DATABASE_URL", "sqlite:///./data/boa.db")


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine,
    though an Engine is acceptable here as well. By skipping the Engine
    creation we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # Required for SQLite ALTER TABLE
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    In this scenario we need to create an Engine and associate a
    connection with the context.
    """
    from boa.db.connection import get_engine

    connectable = get_engine(url=get_url())

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # Required for SQLite ALTER TABLE
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()






