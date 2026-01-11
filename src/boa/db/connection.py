"""
BOA Database Connection Management

Provides engine factory, session management, and connection configuration.
Supports SQLite for development and PostgreSQL for production.
"""

from __future__ import annotations

from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from typing import Generator
import os

from pydantic import BaseModel, Field
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine


class DatabaseSettings(BaseModel):
    """Database configuration settings."""
    
    url: str = Field(
        default="sqlite:///./data/boa.db",
        description="Database URL (SQLite or PostgreSQL)",
    )
    echo: bool = Field(
        default=False,
        description="Echo SQL statements for debugging",
    )
    pool_size: int = Field(
        default=5,
        ge=1,
        description="Connection pool size (ignored for SQLite)",
    )
    max_overflow: int = Field(
        default=10,
        ge=0,
        description="Max connections above pool_size",
    )
    pool_timeout: float = Field(
        default=30.0,
        gt=0,
        description="Seconds to wait for connection from pool",
    )
    connect_args: dict = Field(
        default_factory=dict,
        description="Additional connection arguments",
    )
    
    @classmethod
    def from_env(cls) -> DatabaseSettings:
        """Create settings from environment variables."""
        return cls(
            url=os.getenv("BOA_DATABASE_URL", "sqlite:///./data/boa.db"),
            echo=os.getenv("BOA_DATABASE_ECHO", "false").lower() == "true",
        )
    
    @classmethod
    def in_memory(cls) -> DatabaseSettings:
        """Create settings for in-memory SQLite (testing)."""
        return cls(
            url="sqlite:///:memory:",
            connect_args={"check_same_thread": False},
        )
    
    @classmethod
    def sqlite_file(cls, path: str | Path) -> DatabaseSettings:
        """Create settings for SQLite file database."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        return cls(
            url=f"sqlite:///{path}",
            connect_args={"check_same_thread": False},
        )


def _configure_sqlite_pragmas(dbapi_conn, connection_record) -> None:
    """Configure SQLite for better performance and durability."""
    cursor = dbapi_conn.cursor()
    # Enable foreign key enforcement
    cursor.execute("PRAGMA foreign_keys=ON")
    # Use WAL mode for better concurrency
    cursor.execute("PRAGMA journal_mode=WAL")
    # Synchronous mode for durability/performance balance
    cursor.execute("PRAGMA synchronous=NORMAL")
    # Larger cache for better read performance
    cursor.execute("PRAGMA cache_size=-64000")  # 64MB
    # Busy timeout for lock contention
    cursor.execute("PRAGMA busy_timeout=5000")  # 5 seconds
    cursor.close()


def get_engine(
    url: str = "sqlite:///./data/boa.db",
    echo: bool = False,
    **kwargs,
) -> Engine:
    """
    Get or create the database engine (singleton per URL).
    
    Args:
        url: Database URL
        echo: Echo SQL statements
        **kwargs: Additional engine arguments
        
    Returns:
        SQLAlchemy Engine instance
    """
    # Check cache first
    if url in _engine_cache:
        return _engine_cache[url]
    
    is_sqlite = url.startswith("sqlite")
    
    connect_args = kwargs.pop("connect_args", {})
    if is_sqlite:
        # SQLite needs check_same_thread=False for multi-threaded access
        connect_args.setdefault("check_same_thread", False)
        
        # Ensure parent directory exists for file-based SQLite
        if "memory" not in url:
            db_path = url.replace("sqlite:///", "")
            if db_path.startswith("./"):
                db_path = db_path[2:]
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    engine_kwargs = {
        "echo": echo,
        "connect_args": connect_args,
    }
    
    # Pool settings for non-SQLite databases
    if not is_sqlite:
        engine_kwargs.update({
            "pool_size": kwargs.get("pool_size", 5),
            "max_overflow": kwargs.get("max_overflow", 10),
            "pool_timeout": kwargs.get("pool_timeout", 30.0),
            "pool_pre_ping": True,
        })
    
    engine = create_engine(url, **engine_kwargs)
    
    # Configure SQLite pragmas
    if is_sqlite:
        event.listen(engine, "connect", _configure_sqlite_pragmas)
    
    # Cache the engine
    _engine_cache[url] = engine
    
    return engine


# Engine cache for singleton behavior
_engine_cache: dict[str, Engine] = {}


def create_engine_from_settings(settings: DatabaseSettings) -> Engine:
    """Create engine from DatabaseSettings object."""
    # Clear the cache to allow creating a new engine
    _engine_cache.clear()
    
    return get_engine(
        url=settings.url,
        echo=settings.echo,
        pool_size=settings.pool_size,
        max_overflow=settings.max_overflow,
        pool_timeout=settings.pool_timeout,
        connect_args=settings.connect_args,
    )


def create_db_and_tables(engine: Engine | None = None) -> None:
    """
    Create all database tables.
    
    Args:
        engine: Optional engine, uses default if not provided
    """
    if engine is None:
        engine = get_engine()
    
    SQLModel.metadata.create_all(engine)


def drop_db_and_tables(engine: Engine | None = None) -> None:
    """
    Drop all database tables.
    
    Args:
        engine: Optional engine, uses default if not provided
    """
    if engine is None:
        engine = get_engine()
    
    SQLModel.metadata.drop_all(engine)


@contextmanager
def get_session(engine: Engine | None = None) -> Generator[Session, None, None]:
    """
    Context manager for database sessions.
    
    Args:
        engine: Optional engine, uses default if not provided
        
    Yields:
        SQLModel Session
        
    Example:
        with get_session() as session:
            process = session.get(Process, process_id)
    """
    if engine is None:
        engine = get_engine()
    
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


class SessionManager:
    """
    Session manager for dependency injection.
    
    Useful for FastAPI dependency injection and testing.
    """
    
    def __init__(self, engine: Engine | None = None):
        self._engine = engine
    
    @property
    def engine(self) -> Engine:
        if self._engine is None:
            self._engine = get_engine()
        return self._engine
    
    @engine.setter
    def engine(self, value: Engine) -> None:
        self._engine = value
    
    def get_session(self) -> Generator[Session, None, None]:
        """Get a session as a generator (for FastAPI Depends)."""
        session = Session(self.engine)
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Get a session as a context manager."""
        session = Session(self.engine)
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


# Default session manager instance
session_manager = SessionManager()

