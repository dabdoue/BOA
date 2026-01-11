"""
BOA Campaign Routes
"""

from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from boa.db.models import Campaign, CampaignStatus
from boa.db.repository import (
    CampaignRepository,
    ProcessRepository,
    NotFoundError,
    InvalidStateTransitionError,
)
from boa.core.engine import CampaignEngine
from boa.core.analyzer import CampaignAnalyzer
from boa.spec.loader import load_process_spec
from boa.cli.export_import import CampaignExporter, CampaignImporter, validate_bundle
from boa.server.deps import get_db, get_config
from boa.server.schemas import (
    CampaignCreate,
    CampaignUpdate,
    CampaignResponse,
    CampaignDetailResponse,
    CampaignMetricsResponse,
)

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.post("", response_model=CampaignDetailResponse, status_code=status.HTTP_201_CREATED)
def create_campaign(
    data: CampaignCreate,
    db: Session = Depends(get_db),
) -> CampaignDetailResponse:
    """Create a new campaign."""
    # Verify process exists
    process_repo = ProcessRepository(db)
    try:
        process_repo.get_or_raise(data.process_id)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Process {data.process_id} not found",
        )
    
    campaign = Campaign(
        process_id=data.process_id,
        name=data.name,
        description=data.description,
        strategy_config=data.strategy_config,
        metadata_=data.metadata,
    )
    
    campaign_repo = CampaignRepository(db)
    campaign = campaign_repo.create(campaign)
    db.commit()
    
    return CampaignDetailResponse(
        id=campaign.id,
        process_id=campaign.process_id,
        name=campaign.name,
        description=campaign.description,
        status=campaign.status.value,
        strategy_config=campaign.strategy_config,
        metadata=campaign.metadata_,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
    )


@router.get("", response_model=List[CampaignResponse])
def list_campaigns(
    process_id: UUID | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> List[CampaignResponse]:
    """List campaigns."""
    campaign_repo = CampaignRepository(db)
    
    status_enum = CampaignStatus(status) if status else None
    campaigns = campaign_repo.list(
        process_id=process_id,
        status=status_enum,
        limit=limit,
        offset=offset,
    )
    
    return [CampaignResponse(
        id=c.id,
        process_id=c.process_id,
        name=c.name,
        description=c.description,
        status=c.status.value,
        created_at=c.created_at,
        updated_at=c.updated_at,
    ) for c in campaigns]


@router.get("/{campaign_id}", response_model=CampaignDetailResponse)
def get_campaign(
    campaign_id: UUID,
    db: Session = Depends(get_db),
) -> CampaignDetailResponse:
    """Get campaign by ID."""
    campaign_repo = CampaignRepository(db)
    
    try:
        campaign = campaign_repo.get_or_raise(campaign_id)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found",
        )
    
    return CampaignDetailResponse(
        id=campaign.id,
        process_id=campaign.process_id,
        name=campaign.name,
        description=campaign.description,
        status=campaign.status.value,
        strategy_config=campaign.strategy_config,
        metadata=campaign.metadata_,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
    )


@router.put("/{campaign_id}", response_model=CampaignDetailResponse)
def update_campaign(
    campaign_id: UUID,
    data: CampaignUpdate,
    db: Session = Depends(get_db),
) -> CampaignDetailResponse:
    """Update a campaign."""
    campaign_repo = CampaignRepository(db)
    
    try:
        campaign = campaign_repo.get_or_raise(campaign_id)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found",
        )
    
    if data.name is not None:
        campaign.name = data.name
    if data.description is not None:
        campaign.description = data.description
    if data.strategy_config is not None:
        campaign.strategy_config = data.strategy_config
    if data.metadata is not None:
        campaign.metadata_ = data.metadata
    if data.status is not None:
        try:
            new_status = CampaignStatus(data.status)
            campaign = campaign_repo.update_status(campaign_id, new_status)
        except (ValueError, InvalidStateTransitionError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status transition: {e}",
            )
    else:
        campaign = campaign_repo.update(campaign)
    
    db.commit()
    
    return CampaignDetailResponse(
        id=campaign.id,
        process_id=campaign.process_id,
        name=campaign.name,
        description=campaign.description,
        status=campaign.status.value,
        strategy_config=campaign.strategy_config,
        metadata=campaign.metadata_,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
    )


@router.post("/{campaign_id}/pause", response_model=CampaignResponse)
def pause_campaign(
    campaign_id: UUID,
    db: Session = Depends(get_db),
) -> CampaignResponse:
    """Pause a campaign."""
    campaign_repo = CampaignRepository(db)
    
    try:
        campaign = campaign_repo.get_or_raise(campaign_id)
        campaign = campaign_repo.update_status(campaign_id, CampaignStatus.PAUSED)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found",
        )
    except InvalidStateTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    db.commit()
    
    return CampaignResponse(
        id=campaign.id,
        process_id=campaign.process_id,
        name=campaign.name,
        description=campaign.description,
        status=campaign.status.value,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
    )


@router.post("/{campaign_id}/resume", response_model=CampaignResponse)
def resume_campaign(
    campaign_id: UUID,
    db: Session = Depends(get_db),
) -> CampaignResponse:
    """Resume a paused campaign."""
    campaign_repo = CampaignRepository(db)
    
    try:
        campaign = campaign_repo.get_or_raise(campaign_id)
        campaign = campaign_repo.update_status(campaign_id, CampaignStatus.ACTIVE)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found",
        )
    except InvalidStateTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    db.commit()
    
    return CampaignResponse(
        id=campaign.id,
        process_id=campaign.process_id,
        name=campaign.name,
        description=campaign.description,
        status=campaign.status.value,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
    )


@router.post("/{campaign_id}/complete", response_model=CampaignResponse)
def complete_campaign(
    campaign_id: UUID,
    db: Session = Depends(get_db),
) -> CampaignResponse:
    """Mark a campaign as completed."""
    campaign_repo = CampaignRepository(db)
    
    try:
        campaign = campaign_repo.get_or_raise(campaign_id)
        campaign = campaign_repo.update_status(campaign_id, CampaignStatus.COMPLETED)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found",
        )
    except InvalidStateTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    db.commit()
    
    return CampaignResponse(
        id=campaign.id,
        process_id=campaign.process_id,
        name=campaign.name,
        description=campaign.description,
        status=campaign.status.value,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
    )


@router.get("/{campaign_id}/metrics", response_model=CampaignMetricsResponse)
def get_campaign_metrics(
    campaign_id: UUID,
    db: Session = Depends(get_db),
) -> CampaignMetricsResponse:
    """Get campaign metrics and analysis."""
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
    metrics = engine.analyze()
    
    return CampaignMetricsResponse(
        n_observations=metrics.n_observations,
        n_iterations=metrics.n_iterations,
        best_values=metrics.best_values,
        best_observation=metrics.best_observation,
        hypervolume=metrics.hypervolume,
        pareto_front_size=metrics.pareto_front_size,
        improvement_history=metrics.improvement_history,
        objective_bounds=metrics.objective_bounds,
    )


@router.get("/{campaign_id}/export")
def export_campaign(
    campaign_id: UUID,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Export a campaign to a bundle format."""
    campaign_repo = CampaignRepository(db)
    
    try:
        campaign_repo.get_or_raise(campaign_id)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found",
        )
    
    exporter = CampaignExporter(db)
    bundle = exporter.export(campaign_id)
    
    return bundle


@router.post("/import")
def import_campaign(
    bundle: Dict[str, Any],
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Import a campaign from a bundle format."""
    try:
        validate_bundle(bundle)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    importer = CampaignImporter(db)
    
    try:
        campaign_id = importer.import_from_dict(bundle)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Import failed: {e}",
        )
    
    return {"campaign_id": str(campaign_id), "message": "Campaign imported successfully"}

