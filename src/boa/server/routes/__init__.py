"""
BOA API Routes
"""

from boa.server.routes.processes import router as processes_router
from boa.server.routes.campaigns import router as campaigns_router
from boa.server.routes.observations import router as observations_router
from boa.server.routes.proposals import router as proposals_router
from boa.server.routes.jobs import router as jobs_router

__all__ = [
    "processes_router",
    "campaigns_router",
    "observations_router",
    "proposals_router",
    "jobs_router",
]





