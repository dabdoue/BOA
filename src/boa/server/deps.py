"""
BOA Server Dependencies

FastAPI dependency injection utilities.
"""

from typing import Generator

from sqlmodel import Session

from boa.db.connection import get_engine
from boa.server.config import ServerConfig


# Global config (set during app creation)
_config: ServerConfig | None = None


def get_config() -> ServerConfig:
    """Get server configuration."""
    if _config is None:
        raise RuntimeError("Config not initialized")
    return _config


def set_config(config: ServerConfig) -> None:
    """Set server configuration."""
    global _config
    _config = config


def get_db() -> Generator[Session, None, None]:
    """Get database session dependency."""
    config = get_config()
    engine = get_engine(config.database_url)
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

