"""
BOA FastAPI Application
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from boa import __version__
from boa.db.connection import create_db_and_tables, get_engine
from boa.server.config import ServerConfig
from boa.server.deps import set_config, get_config
from boa.server.routes import (
    processes_router,
    campaigns_router,
    observations_router,
    proposals_router,
    jobs_router,
)
from boa.server.schemas import HealthResponse


def create_app(config: ServerConfig | None = None) -> FastAPI:
    """
    Create FastAPI application.
    
    Args:
        config: Server configuration (uses defaults if None)
        
    Returns:
        Configured FastAPI app
    """
    if config is None:
        config = ServerConfig()
    
    set_config(config)
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Application lifespan events."""
        # Startup
        engine = get_engine(config.database_url)
        create_db_and_tables(engine)
        config.artifacts_dir.mkdir(parents=True, exist_ok=True)
        yield
        # Shutdown
        pass
    
    app = FastAPI(
        title="BOA - Bayesian Optimization Assistant",
        description="REST API for Bayesian optimization campaigns",
        version=__version__,
        lifespan=lifespan,
    )
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Routes
    app.include_router(processes_router)
    app.include_router(campaigns_router)
    app.include_router(observations_router)
    app.include_router(proposals_router)
    app.include_router(jobs_router)
    
    @app.get("/health", response_model=HealthResponse, tags=["health"])
    def health_check() -> HealthResponse:
        """Health check endpoint."""
        return HealthResponse(
            status="healthy",
            version=__version__,
            database=config.database_url.split("://")[0],
        )
    
    return app


# Default app for uvicorn
app = create_app()

