"""
BOA Proposal Routes
"""

from typing import List
from uuid import UUID

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from boa.db.repository import (
    CampaignRepository,
    IterationRepository,
    ProposalRepository,
    NotFoundError,
)
from boa.core.engine import CampaignEngine
from boa.server.deps import get_db, get_config
from boa.server.schemas import (
    ProposeRequest,
    InitialDesignRequest,
    ProposalResponse,
    IterationResponse,
    DecisionCreate,
    DecisionResponse,
)

router = APIRouter(prefix="/campaigns/{campaign_id}", tags=["proposals"])


@router.post("/initial-design", response_model=List[ProposalResponse], status_code=status.HTTP_201_CREATED)
def run_initial_design(
    campaign_id: UUID,
    data: InitialDesignRequest,
    db: Session = Depends(get_db),
) -> List[ProposalResponse]:
    """Generate initial design samples."""
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
    
    try:
        result = engine.run_initial_design(
            n_samples=data.n_samples,
            strategy_name=data.strategy_name,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Initial design failed: {e}",
        )
    
    db.commit()
    
    # Get created proposals
    iteration = engine.ledger.get_current_iteration()
    proposals = engine.ledger.get_proposals(iteration)
    
    return [ProposalResponse.model_validate(p) for p in proposals]


@router.post("/propose", response_model=List[ProposalResponse], status_code=status.HTTP_201_CREATED)
def generate_proposals(
    campaign_id: UUID,
    data: ProposeRequest,
    db: Session = Depends(get_db),
) -> List[ProposalResponse]:
    """Generate optimization proposals."""
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
    
    ref_point = np.array(data.ref_point) if data.ref_point else None
    
    try:
        results = engine.run_optimization_iteration(
            n_candidates=data.n_candidates,
            strategy_names=data.strategy_names,
            ref_point=ref_point,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Proposal generation failed: {e}",
        )
    
    db.commit()
    
    # Get created proposals
    iteration = engine.ledger.get_current_iteration()
    proposals = engine.ledger.get_proposals(iteration)
    
    return [ProposalResponse.model_validate(p) for p in proposals]


@router.get("/iterations", response_model=List[IterationResponse])
def list_iterations(
    campaign_id: UUID,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> List[IterationResponse]:
    """List iterations for a campaign."""
    campaign_repo = CampaignRepository(db)
    iter_repo = IterationRepository(db)
    
    try:
        campaign_repo.get_or_raise(campaign_id)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found",
        )
    
    iterations = iter_repo.list(campaign_id, limit=limit, offset=offset)
    
    return [IterationResponse.model_validate(i) for i in iterations]


@router.get("/iterations/{iteration_index}/proposals", response_model=List[ProposalResponse])
def get_iteration_proposals(
    campaign_id: UUID,
    iteration_index: int,
    db: Session = Depends(get_db),
) -> List[ProposalResponse]:
    """Get proposals for a specific iteration."""
    campaign_repo = CampaignRepository(db)
    iter_repo = IterationRepository(db)
    proposal_repo = ProposalRepository(db)
    
    try:
        campaign_repo.get_or_raise(campaign_id)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found",
        )
    
    iteration = iter_repo.get_by_index(campaign_id, iteration_index)
    if not iteration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Iteration {iteration_index} not found",
        )
    
    proposals = proposal_repo.list(iteration.id)
    
    return [ProposalResponse.model_validate(p) for p in proposals]


@router.post("/iterations/{iteration_index}/decision", response_model=DecisionResponse, status_code=status.HTTP_201_CREATED)
def create_decision(
    campaign_id: UUID,
    iteration_index: int,
    data: DecisionCreate,
    db: Session = Depends(get_db),
) -> DecisionResponse:
    """Record a decision for an iteration."""
    config = get_config()
    campaign_repo = CampaignRepository(db)
    iter_repo = IterationRepository(db)
    
    try:
        campaign = campaign_repo.get_or_raise(campaign_id)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found",
        )
    
    iteration = iter_repo.get_by_index(campaign_id, iteration_index)
    if not iteration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Iteration {iteration_index} not found",
        )
    
    engine = CampaignEngine(db, campaign, config.artifacts_dir)
    
    # Convert to format expected by ledger
    accepted = [
        {"proposal_id": str(a.proposal_id), "candidate_indices": a.candidate_indices}
        for a in data.accepted
    ]
    
    try:
        decision = engine.ledger.record_decision(
            iteration=iteration,
            accepted=accepted,
            notes=data.notes,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    db.commit()
    
    return DecisionResponse.model_validate(decision)





