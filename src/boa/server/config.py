"""
BOA Server Configuration
"""

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class ServerConfig(BaseSettings):
    """Server configuration from environment."""
    
    # Database
    database_url: str = Field(
        default="sqlite:///./boa.db",
        description="Database connection URL",
    )
    
    # Server
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    debug: bool = Field(default=False, description="Debug mode")
    
    # Artifacts
    artifacts_dir: Path = Field(
        default=Path("./artifacts"),
        description="Directory for checkpoints and artifacts",
    )
    
    # CORS
    cors_origins: list[str] = Field(
        default=["*"],
        description="Allowed CORS origins",
    )
    
    # Job Worker
    worker_poll_interval: float = Field(
        default=1.0,
        description="Job worker poll interval in seconds",
    )
    
    model_config = {"env_prefix": "BOA_"}





