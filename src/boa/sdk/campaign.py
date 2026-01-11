"""
BOA Campaign Helper

High-level fluent API for campaign management.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID
from dataclasses import dataclass, field

from boa.sdk.client import BOAClient


@dataclass
class Proposal:
    """Represents a proposal from the optimizer."""
    
    id: str
    strategy_name: str
    candidates: List[Dict[str, Any]]
    acq_values: Optional[List[float]] = None
    predictions: Optional[Dict[str, Any]] = None
    
    def __len__(self) -> int:
        return len(self.candidates)
    
    def __getitem__(self, idx: int) -> Dict[str, Any]:
        return self.candidates[idx]


@dataclass
class Observation:
    """Represents an observation."""
    
    id: str
    x: Dict[str, Any]
    y: Dict[str, Any]
    source: str = "user"


class Campaign:
    """
    High-level fluent API for campaign management.
    
    Example:
        with BOAClient("http://localhost:8000") as client:
            campaign = Campaign(client, campaign_id)
            
            # Add observations
            campaign.add_observation({"x1": 5.0, "x2": 2.0}, {"y": 10.0})
            
            # Get proposals
            proposals = campaign.propose(n_candidates=3)
            
            # Accept all candidates
            for proposal in proposals:
                campaign.accept(proposal.id, list(range(len(proposal))))
            
            # Check metrics
            metrics = campaign.metrics()
            print(f"Best value: {metrics['best_values']}")
    """
    
    def __init__(
        self,
        client: BOAClient,
        campaign_id: str | UUID,
    ):
        """
        Initialize campaign helper.
        
        Args:
            client: BOAClient instance
            campaign_id: Campaign ID
        """
        self.client = client
        self.campaign_id = str(campaign_id)
        self._info: Optional[Dict[str, Any]] = None
    
    @property
    def info(self) -> Dict[str, Any]:
        """Get campaign info (cached)."""
        if self._info is None:
            self._info = self.client.get_campaign(self.campaign_id)
        return self._info
    
    @property
    def status(self) -> str:
        """Get campaign status."""
        return self.info["status"]
    
    @property
    def name(self) -> str:
        """Get campaign name."""
        return self.info["name"]
    
    def refresh(self) -> "Campaign":
        """Refresh campaign info."""
        self._info = None
        return self
    
    # =========================================================================
    # Observations
    # =========================================================================
    
    def add_observation(
        self,
        x: Dict[str, Any],
        y: Dict[str, Any],
        source: str = "user",
    ) -> Observation:
        """
        Add an observation.
        
        Args:
            x: Input values
            y: Objective values
            source: Observation source
            
        Returns:
            Created observation
        """
        result = self.client.add_observation(self.campaign_id, x, y, source)
        return Observation(
            id=result["id"],
            x=result["x_raw"],
            y=result["y"],
            source=result["source"],
        )
    
    def add_observations(
        self,
        observations: List[Dict[str, Any]],
    ) -> List[Observation]:
        """
        Add multiple observations.
        
        Args:
            observations: List of {x, y, source?} dicts
            
        Returns:
            List of created observations
        """
        formatted = [
            {"x_raw": o.get("x", o.get("x_raw")), "y": o["y"], "source": o.get("source", "user")}
            for o in observations
        ]
        results = self.client.add_observations_batch(self.campaign_id, formatted)
        return [
            Observation(
                id=r["id"],
                x=r["x_raw"],
                y=r["y"],
                source=r["source"],
            )
            for r in results
        ]
    
    def observations(
        self,
        source: Optional[str] = None,
        limit: int = 1000,
    ) -> List[Observation]:
        """
        Get observations.
        
        Args:
            source: Filter by source
            limit: Maximum to return
            
        Returns:
            List of observations
        """
        results = self.client.list_observations(self.campaign_id, source, limit)
        return [
            Observation(
                id=r["id"],
                x=r["x_raw"],
                y=r["y"],
                source=r["source"],
            )
            for r in results
        ]
    
    # =========================================================================
    # Proposals
    # =========================================================================
    
    def initial_design(
        self,
        n_samples: int,
        strategy_name: Optional[str] = None,
    ) -> List[Proposal]:
        """
        Generate initial design samples.
        
        Args:
            n_samples: Number of samples
            strategy_name: Strategy to use
            
        Returns:
            List of proposals
        """
        results = self.client.initial_design(
            self.campaign_id, n_samples, strategy_name
        )
        self._info = None  # Status may have changed
        return [
            Proposal(
                id=r["id"],
                strategy_name=r["strategy_name"],
                candidates=r["candidates_raw"],
                acq_values=r.get("acq_values"),
                predictions=r.get("predictions"),
            )
            for r in results
        ]
    
    def propose(
        self,
        n_candidates: int = 1,
        strategy_names: Optional[List[str]] = None,
        ref_point: Optional[List[float]] = None,
    ) -> List[Proposal]:
        """
        Generate optimization proposals.
        
        Args:
            n_candidates: Number of candidates per strategy
            strategy_names: Strategies to use
            ref_point: Reference point for hypervolume
            
        Returns:
            List of proposals
        """
        results = self.client.propose(
            self.campaign_id, n_candidates, strategy_names, ref_point
        )
        return [
            Proposal(
                id=r["id"],
                strategy_name=r["strategy_name"],
                candidates=r["candidates_raw"],
                acq_values=r.get("acq_values"),
                predictions=r.get("predictions"),
            )
            for r in results
        ]
    
    def accept(
        self,
        proposal_id: str,
        candidate_indices: List[int],
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Accept candidates from a proposal.
        
        Args:
            proposal_id: Proposal ID
            candidate_indices: Indices of candidates to accept
            notes: Optional notes
            
        Returns:
            Decision record
        """
        iterations = self.client.list_iterations(self.campaign_id)
        latest_index = max(i["index"] for i in iterations)
        
        return self.client.record_decision(
            self.campaign_id,
            latest_index,
            accepted=[{
                "proposal_id": proposal_id,
                "candidate_indices": candidate_indices,
            }],
            notes=notes,
        )
    
    def accept_all(
        self,
        proposals: List[Proposal],
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Accept all candidates from proposals.
        
        Args:
            proposals: Proposals to accept
            notes: Optional notes
            
        Returns:
            Decision record
        """
        iterations = self.client.list_iterations(self.campaign_id)
        latest_index = max(i["index"] for i in iterations)
        
        accepted = [
            {
                "proposal_id": p.id,
                "candidate_indices": list(range(len(p))),
            }
            for p in proposals
        ]
        
        return self.client.record_decision(
            self.campaign_id,
            latest_index,
            accepted=accepted,
            notes=notes,
        )
    
    # =========================================================================
    # Lifecycle
    # =========================================================================
    
    def pause(self) -> "Campaign":
        """Pause the campaign."""
        self.client.pause_campaign(self.campaign_id)
        self._info = None
        return self
    
    def resume(self) -> "Campaign":
        """Resume the campaign."""
        self.client.resume_campaign(self.campaign_id)
        self._info = None
        return self
    
    def complete(self) -> "Campaign":
        """Mark campaign as completed."""
        self.client.complete_campaign(self.campaign_id)
        self._info = None
        return self
    
    # =========================================================================
    # Analysis
    # =========================================================================
    
    def metrics(self) -> Dict[str, Any]:
        """Get campaign metrics."""
        return self.client.get_campaign_metrics(self.campaign_id)
    
    def best(self) -> Optional[Dict[str, Any]]:
        """Get best observation."""
        metrics = self.metrics()
        return metrics.get("best_observation")
    
    def pareto_front(self) -> List[Dict[str, Any]]:
        """Get Pareto front from observations."""
        # The server metrics include Pareto info
        metrics = self.metrics()
        # For now just return best - full Pareto would need separate endpoint
        best = metrics.get("best_observation")
        return [best] if best else []





