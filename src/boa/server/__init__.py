"""
BOA FastAPI Server

REST API for Bayesian Optimization Assistant.
"""

from boa.server.app import create_app
from boa.server.config import ServerConfig

__all__ = [
    "create_app",
    "ServerConfig",
]





