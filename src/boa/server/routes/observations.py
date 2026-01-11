"""
BOA Observation Routes
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from boa.db.repository import CampaignRepository, ObservationRepository, NotFoundError
from boa.core.engine import CampaignEngine
from boa.server.deps import get_db, get_config
from boa.server.schemas import (
    ObservationCreate,
    ObservationBatchCreate,
    ObservationResponse,
)

router = APIRouter(prefix="/campaigns/{campaign_id}/observations", tags=["observations"])


@router.post("", response_model=ObservationResponse, status_code=status.HTTP_201_CREATED)
def create_observation(
    campaign_id: UUID,
    data: ObservationCreate,
    db: Session = Depends(get_db),
) -> ObservationResponse:
    """Add an observation to a campaign."""
    config = get_config()
    campaign_repo = CampaignRepository(db)
    
    try:
        campaign = campaign_repo.get_or_raise(campaign_id)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found",
        )
    
    engine = CampaignEngine(db, campaign, config.artifacts_dir)
    engine.add_observation(
        x_raw=data.x_raw,
        y=data.y,
        source=data.source,
    )
    
    db.commit()
    
    # Get the created observation
    observations = engine.ledger.get_observations()
    obs = observations[-1]
    
    return ObservationResponse.model_validate(obs)


@router.post("/batch", response_model=List[ObservationResponse], status_code=status.HTTP_201_CREATED)
def create_observations_batch(
    campaign_id: UUID,
    data: ObservationBatchCreate,
    db: Session = Depends(get_db),
) -> List[ObservationResponse]:
    """Add multiple observations to a campaign."""
    config = get_config()
    campaign_repo = CampaignRepository(db)
    
    try:
        campaign = campaign_repo.get_or_raise(campaign_id)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found",
        )
    
    engine = CampaignEngine(db, campaign, config.artifacts_dir)
    
    for obs_data in data.observations:
        engine.add_observation(
            x_raw=obs_data.x_raw,
            y=obs_data.y,
            source=obs_data.source,
        )
    
    db.commit()
    
    # Get all observations
    observations = engine.ledger.get_observations()
    
    return [ObservationResponse.model_validate(o) for o in observations[-len(data.observations):]]


@router.get("", response_model=List[ObservationResponse])
def list_observations(
    campaign_id: UUID,
    source: str | None = None,
    limit: int = 1000,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> List[ObservationResponse]:
    """List observations for a campaign."""
    campaign_repo = CampaignRepository(db)
    obs_repo = ObservationRepository(db)
    
    try:
        campaign_repo.get_or_raise(campaign_id)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found",
        )
    
    observations = obs_repo.list(
        campaign_id=campaign_id,
        source=source,
        limit=limit,
        offset=offset,
    )
    
    return [ObservationResponse.model_validate(o) for o in observations]


@router.get("/{observation_id}", response_model=ObservationResponse)
def get_observation(
    campaign_id: UUID,
    observation_id: UUID,
    db: Session = Depends(get_db),
) -> ObservationResponse:
    """Get a specific observation."""
    obs_repo = ObservationRepository(db)
    
    try:
        obs = obs_repo.get_or_raise(observation_id)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Observation {observation_id} not found",
        )
    
    if obs.campaign_id != campaign_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Observation {observation_id} not found in campaign {campaign_id}",
        )
    
    return ObservationResponse.model_validate(obs)





