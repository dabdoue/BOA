"""
BOA Proposal Ledger

Manages proposals, decisions, and the experiment lifecycle.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
import logging

from sqlmodel import Session

from boa.db.models import (
    Campaign,
    Iteration,
    Proposal,
    Decision,
    Observation,
    CampaignStatus,
)
from boa.db.repository import (
    IterationRepository,
    ProposalRepository,
    DecisionRepository,
    ObservationRepository,
    CampaignRepository,
)

logger = logging.getLogger(__name__)


@dataclass
class ProposalInfo:
    """Information about a proposal."""
    
    id: UUID
    iteration_id: UUID
    strategy_name: str
    candidates_raw: List[Dict[str, Any]]
    candidates_encoded: Optional[List[List[float]]] = None
    acq_values: Optional[List[float]] = None
    predictions: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class DecisionInfo:
    """Information about a decision."""
    
    id: UUID
    iteration_id: UUID
    accepted: List[Dict[str, Any]]  # [{proposal_id, candidate_indices}]
    notes: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ProposalLedger:
    """
    Manages the proposal/decision lifecycle.
    
    Tracks:
    - Iterations (optimization cycles)
    - Proposals from strategies
    - Decisions on which candidates to run
    - Observations from experiments
    """
    
    def __init__(self, session: Session, campaign: Campaign):
        """
        Initialize ledger.
        
        Args:
            session: Database session
            campaign: Campaign to manage
        """
        self.session = session
        self.campaign = campaign
        
        # Repositories
        self.iteration_repo = IterationRepository(session)
        self.proposal_repo = ProposalRepository(session)
        self.decision_repo = DecisionRepository(session)
        self.observation_repo = ObservationRepository(session)
        self.campaign_repo = CampaignRepository(session)
    
    def get_current_iteration(self) -> Optional[Iteration]:
        """Get the current (most recent) iteration."""
        return self.iteration_repo.get_latest(self.campaign.id)
    
    def get_iteration_count(self) -> int:
        """Get the number of iterations."""
        iterations = self.iteration_repo.list(self.campaign.id)
        return len(iterations)
    
    def start_iteration(
        self,
        dataset_hash: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Iteration:
        """
        Start a new iteration.
        
        Args:
            dataset_hash: Hash of current training data
            metadata: Optional metadata
            
        Returns:
            Created iteration
        """
        current = self.get_current_iteration()
        next_idx = 0 if current is None else current.index + 1
        
        iteration = Iteration(
            campaign_id=self.campaign.id,
            index=next_idx,
            dataset_hash=dataset_hash,
            metadata_=metadata or {},
        )
        
        self.session.add(iteration)
        self.session.commit()
        self.session.refresh(iteration)
        
        logger.info(f"Started iteration {next_idx} for campaign {self.campaign.id}")
        
        # Update campaign status if needed
        if self.campaign.status == CampaignStatus.CREATED:
            self.campaign_repo.update_status(self.campaign.id, CampaignStatus.ACTIVE)
            self.session.refresh(self.campaign)
        
        return iteration
    
    def add_proposal(
        self,
        iteration: Iteration,
        strategy_name: str,
        candidates_raw: List[Dict[str, Any]],
        candidates_encoded: Optional[List[List[float]]] = None,
        acq_values: Optional[List[float]] = None,
        predictions: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Proposal:
        """
        Add a proposal to an iteration.
        
        Args:
            iteration: Iteration to add to
            strategy_name: Name of the strategy
            candidates_raw: Candidate points in raw format
            candidates_encoded: Optional encoded candidates
            acq_values: Optional acquisition values
            predictions: Optional model predictions
            metadata: Optional metadata
            
        Returns:
            Created proposal
        """
        proposal = Proposal(
            iteration_id=iteration.id,
            strategy_name=strategy_name,
            candidates_raw=candidates_raw,
            candidates_encoded=candidates_encoded,
            acq_values=acq_values,
            predictions=predictions,
            metadata_=metadata or {},
        )
        
        self.session.add(proposal)
        self.session.commit()
        self.session.refresh(proposal)
        
        logger.info(
            f"Added proposal from {strategy_name} with {len(candidates_raw)} candidates"
        )
        
        return proposal
    
    def get_proposals(self, iteration: Iteration) -> List[Proposal]:
        """Get all proposals for an iteration."""
        return self.proposal_repo.list(iteration.id)
    
    def record_decision(
        self,
        iteration: Iteration,
        accepted: List[Dict[str, Any]],
        notes: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Decision:
        """
        Record a decision for an iteration.
        
        Args:
            iteration: Iteration to decide on
            accepted: List of accepted candidates [{proposal_id, candidate_indices}]
            notes: Optional human notes
            metadata: Optional metadata
            
        Returns:
            Created decision
        """
        # Check if decision already exists
        existing = self.decision_repo.get_by_iteration(iteration.id)
        if existing:
            raise ValueError(f"Decision already exists for iteration {iteration.index}")
        
        decision = Decision(
            iteration_id=iteration.id,
            accepted=accepted,
            notes=notes,
            metadata_=metadata or {},
        )
        
        self.session.add(decision)
        self.session.commit()
        self.session.refresh(decision)
        
        logger.info(f"Recorded decision for iteration {iteration.index}")
        
        return decision
    
    def add_observation(
        self,
        x_raw: Dict[str, Any],
        y: Dict[str, Any],
        x_encoded: Optional[List[float]] = None,
        source: str = "user",
        observed_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Observation:
        """
        Add an observation to the campaign.
        
        Args:
            x_raw: Input values in raw format
            y: Objective values
            x_encoded: Optional encoded input
            source: Source of observation
            observed_at: When observation was made
            metadata: Optional metadata
            
        Returns:
            Created observation
        """
        observation = Observation(
            campaign_id=self.campaign.id,
            x_raw=x_raw,
            x_encoded=x_encoded,
            y=y,
            source=source,
            observed_at=observed_at or datetime.now(timezone.utc),
            metadata_=metadata or {},
        )
        
        self.session.add(observation)
        self.session.commit()
        self.session.refresh(observation)
        
        logger.debug(f"Added observation: {x_raw} -> {y}")
        
        return observation
    
    def add_observations_batch(
        self,
        observations: List[Dict[str, Any]],
        source: str = "user",
    ) -> List[Observation]:
        """
        Add multiple observations.
        
        Args:
            observations: List of {x_raw, y, ...} dicts
            source: Source of observations
            
        Returns:
            List of created observations
        """
        created = []
        for obs in observations:
            created.append(self.add_observation(
                x_raw=obs["x_raw"],
                y=obs["y"],
                x_encoded=obs.get("x_encoded"),
                source=source,
                observed_at=obs.get("observed_at"),
                metadata=obs.get("metadata"),
            ))
        
        logger.info(f"Added {len(created)} observations")
        
        return created
    
    def get_observations(self) -> List[Observation]:
        """Get all observations for the campaign."""
        return self.observation_repo.list(self.campaign.id)
    
    def get_pending_candidates(self) -> List[Dict[str, Any]]:
        """
        Get candidates that have been accepted but not yet observed.
        
        Returns:
            List of pending candidate dicts
        """
        iterations = self.iteration_repo.list(self.campaign.id)
        observations = self.get_observations()
        
        # Get all observed x values (as JSON strings for comparison)
        observed_x = {str(sorted(o.x_raw.items())) for o in observations}
        
        pending = []
        for iteration in iterations:
            decision = self.decision_repo.get_by_iteration(iteration.id)
            if not decision:
                continue
            
            proposals = self.get_proposals(iteration)
            proposal_map = {str(p.id): p for p in proposals}
            
            for accept in decision.accepted:
                proposal_id = accept.get("proposal_id")
                indices = accept.get("candidate_indices", [])
                
                if str(proposal_id) not in proposal_map:
                    continue
                
                proposal = proposal_map[str(proposal_id)]
                for idx in indices:
                    if idx < len(proposal.candidates_raw):
                        candidate = proposal.candidates_raw[idx]
                        if str(sorted(candidate.items())) not in observed_x:
                            pending.append({
                                "x_raw": candidate,
                                "iteration_idx": iteration.index,
                                "strategy_name": proposal.strategy_name,
                            })
        
        return pending

