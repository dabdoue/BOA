"""
BOA Campaign Engine

Main orchestration engine for running optimization campaigns.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID
import hashlib
import json
import logging

import numpy as np
from sqlmodel import Session

from boa.db.models import Campaign, Process, CampaignStatus
from boa.db.repository import CampaignRepository, ProcessRepository
from boa.spec.models import ProcessSpec, StrategySpec
from boa.spec.loader import load_process_spec
from boa.spec.encoder import MixedSpaceEncoder
from boa.core.executor import StrategyExecutor, ExecutionResult
from boa.core.checkpointer import ModelCheckpointer
from boa.core.ledger import ProposalLedger
from boa.core.analyzer import CampaignAnalyzer, CampaignMetrics

logger = logging.getLogger(__name__)


class CampaignEngine:
    """
    Main engine for orchestrating optimization campaigns.
    
    Coordinates:
    - Strategy execution
    - Proposal management
    - Model checkpointing
    - Campaign analysis
    """
    
    def __init__(
        self,
        session: Session,
        campaign: Campaign,
        checkpoint_dir: Optional[Path | str] = None,
    ):
        """
        Initialize engine.
        
        Args:
            session: Database session
            campaign: Campaign to run
            checkpoint_dir: Directory for model checkpoints
        """
        self.session = session
        self.campaign = campaign
        
        # Load process spec
        process_repo = ProcessRepository(session)
        self.process = process_repo.get(campaign.process_id)
        if not self.process:
            raise ValueError(f"Process {campaign.process_id} not found")
        
        self.spec = load_process_spec(self.process.spec_yaml, validate=False)
        self.encoder = MixedSpaceEncoder(self.spec)
        
        # Setup components
        self.ledger = ProposalLedger(session, campaign)
        
        if checkpoint_dir:
            self.checkpointer = ModelCheckpointer(checkpoint_dir, campaign.id)
        else:
            self.checkpointer = None
        
        # Strategy executors
        self._executors: Dict[str, StrategyExecutor] = {}
        for name, strategy in self.spec.strategies.items():
            self._executors[name] = StrategyExecutor(self.spec, strategy)
        
        # Default strategy if none defined
        if not self._executors:
            default_strategy = StrategySpec(
                name="default",
                sampler="lhs_optimized",
                model="gp_matern",
                acquisition="qlogNEHVI",
            )
            self._executors["default"] = StrategyExecutor(self.spec, default_strategy)
    
    def get_training_data(self) -> tuple[np.ndarray, np.ndarray]:
        """
        Get current training data.
        
        Returns:
            Tuple of (X, Y) arrays
        """
        observations = self.ledger.get_observations()
        
        if not observations:
            n_obj = len(self.spec.objectives)
            return (
                np.array([]).reshape(0, self.encoder.n_encoded),
                np.array([]).reshape(0, n_obj),
            )
        
        X = np.array([
            self.encoder.encode_single(obs.x_raw) for obs in observations
        ])
        
        Y = np.array([
            [obs.y.get(obj.name, np.nan) for obj in self.spec.objectives]
            for obs in observations
        ])
        
        return X, Y
    
    def compute_dataset_hash(self) -> str:
        """Compute hash of current dataset for reproducibility."""
        X, Y = self.get_training_data()
        data_str = json.dumps({
            "X": X.tolist(),
            "Y": Y.tolist(),
        }, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()[:16]
    
    def run_initial_design(
        self,
        n_samples: int,
        strategy_name: Optional[str] = None,
    ) -> ExecutionResult:
        """
        Run initial design phase.
        
        Args:
            n_samples: Number of initial samples
            strategy_name: Strategy to use (default: first available)
            
        Returns:
            ExecutionResult with initial candidates
        """
        strategy_name = strategy_name or list(self._executors.keys())[0]
        executor = self._executors[strategy_name]
        
        result = executor.execute_initial_design(n_samples)
        
        # Record in ledger
        iteration = self.ledger.start_iteration()
        self.ledger.add_proposal(
            iteration=iteration,
            strategy_name=result.strategy_name,
            candidates_raw=result.candidates_raw,
            candidates_encoded=result.candidates_encoded.tolist(),
            metadata=result.metadata,
        )
        
        logger.info(f"Generated {n_samples} initial design samples")
        
        return result
    
    def run_optimization_iteration(
        self,
        n_candidates: int = 1,
        strategy_names: Optional[List[str]] = None,
        ref_point: Optional[np.ndarray] = None,
    ) -> Dict[str, ExecutionResult]:
        """
        Run one optimization iteration.
        
        Args:
            n_candidates: Number of candidates per strategy
            strategy_names: Strategies to run (default: all)
            ref_point: Reference point for hypervolume
            
        Returns:
            Dict of strategy_name -> ExecutionResult
        """
        X, Y = self.get_training_data()
        
        if len(X) == 0:
            raise ValueError("No training data. Run initial design first.")
        
        strategy_names = strategy_names or list(self._executors.keys())
        
        # Start iteration
        iteration = self.ledger.start_iteration(
            dataset_hash=self.compute_dataset_hash()
        )
        
        results = {}
        for strategy_name in strategy_names:
            if strategy_name not in self._executors:
                logger.warning(f"Unknown strategy: {strategy_name}")
                continue
            
            executor = self._executors[strategy_name]
            
            try:
                result = executor.execute_optimization(
                    X, Y,
                    n_candidates=n_candidates,
                    ref_point=ref_point,
                )
                
                # Record proposal - convert numpy arrays to lists for JSON
                predictions_json = None
                if result.predictions:
                    predictions_json = {
                        k: v.tolist() if hasattr(v, 'tolist') else v
                        for k, v in result.predictions.items()
                    }
                
                self.ledger.add_proposal(
                    iteration=iteration,
                    strategy_name=result.strategy_name,
                    candidates_raw=result.candidates_raw,
                    candidates_encoded=result.candidates_encoded.tolist(),
                    acq_values=result.acq_values.tolist() if result.acq_values is not None else None,
                    predictions=predictions_json,
                    metadata=result.metadata,
                )
                
                # Checkpoint model
                if self.checkpointer and result.model_state:
                    path = self.checkpointer.save(
                        result.model_state,
                        iteration.index,
                        strategy_name,
                    )
                    logger.debug(f"Saved checkpoint: {path}")
                
                results[strategy_name] = result
                
            except Exception as e:
                logger.error(f"Strategy {strategy_name} failed: {e}")
                raise
        
        logger.info(
            f"Iteration {iteration.index}: generated {n_candidates} candidates "
            f"from {len(results)} strategies"
        )
        
        return results
    
    def accept_candidates(
        self,
        accepted: List[Dict[str, Any]],
        notes: Optional[str] = None,
    ) -> None:
        """
        Accept candidates from proposals.
        
        Args:
            accepted: List of {proposal_id, candidate_indices}
            notes: Optional notes
        """
        iteration = self.ledger.get_current_iteration()
        if not iteration:
            raise ValueError("No current iteration")
        
        self.ledger.record_decision(iteration, accepted, notes)
        
        logger.info(f"Accepted candidates for iteration {iteration.index}")
    
    def add_observation(
        self,
        x_raw: Dict[str, Any],
        y: Dict[str, Any],
        source: str = "user",
    ) -> None:
        """
        Add an observation.
        
        Args:
            x_raw: Input values
            y: Objective values
            source: Observation source
        """
        x_encoded = self.encoder.encode_single(x_raw).tolist()
        self.ledger.add_observation(x_raw, y, x_encoded, source)
    
    def add_observations_batch(
        self,
        observations: List[Dict[str, Any]],
        source: str = "user",
    ) -> None:
        """
        Add multiple observations.
        
        Args:
            observations: List of {x_raw, y} dicts
            source: Observation source
        """
        for obs in observations:
            self.add_observation(obs["x_raw"], obs["y"], source)
    
    def analyze(
        self,
        ref_point: Optional[np.ndarray] = None,
    ) -> CampaignMetrics:
        """
        Analyze campaign progress.
        
        Args:
            ref_point: Reference point for hypervolume
            
        Returns:
            CampaignMetrics
        """
        observations = self.ledger.get_observations()
        analyzer = CampaignAnalyzer(self.spec, observations, ref_point)
        return analyzer.compute_metrics()
    
    def get_pareto_front(self) -> List[Dict[str, Any]]:
        """Get Pareto optimal observations."""
        observations = self.ledger.get_observations()
        analyzer = CampaignAnalyzer(self.spec, observations)
        return analyzer.get_pareto_front()
    
    def complete(self) -> None:
        """Mark campaign as completed."""
        campaign_repo = CampaignRepository(self.session)
        campaign_repo.update_status(self.campaign.id, CampaignStatus.COMPLETED)
        self.session.refresh(self.campaign)
        
        logger.info(f"Campaign {self.campaign.id} completed")
    
    def pause(self) -> None:
        """Pause the campaign."""
        campaign_repo = CampaignRepository(self.session)
        campaign_repo.update_status(self.campaign.id, CampaignStatus.PAUSED)
        self.session.refresh(self.campaign)
        
        logger.info(f"Campaign {self.campaign.id} paused")
    
    def resume(self) -> None:
        """Resume a paused campaign."""
        if self.campaign.status != CampaignStatus.PAUSED:
            raise ValueError("Campaign is not paused")
        
        campaign_repo = CampaignRepository(self.session)
        campaign_repo.update_status(self.campaign.id, CampaignStatus.ACTIVE)
        self.session.refresh(self.campaign)
        
        logger.info(f"Campaign {self.campaign.id} resumed")

