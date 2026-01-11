"""
BOA Export/Import functionality for campaign bundles.
"""

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
import json

from sqlmodel import Session

from boa.db.models import (
    Process,
    Campaign,
    Observation,
    Iteration,
    Proposal,
    Decision,
    Checkpoint,
    CampaignStatus,
)
from boa.db.repository import (
    ProcessRepository,
    CampaignRepository,
    ObservationRepository,
    IterationRepository,
    ProposalRepository,
    DecisionRepository,
    CheckpointRepository,
)


@dataclass
class ExportBundle:
    """Represents an exported campaign bundle."""
    
    version: str
    process: Dict[str, Any]
    campaign: Dict[str, Any]
    observations: List[Dict[str, Any]] = field(default_factory=list)
    iterations: List[Dict[str, Any]] = field(default_factory=list)
    proposals: List[Dict[str, Any]] = field(default_factory=list)
    decisions: List[Dict[str, Any]] = field(default_factory=list)
    checkpoints: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert bundle to dictionary."""
        return asdict(self)
    
    def to_json(self, indent: int = 2) -> str:
        """Convert bundle to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExportBundle":
        """Create bundle from dictionary."""
        return cls(
            version=data.get("version", "1.0"),
            process=data.get("process", {}),
            campaign=data.get("campaign", {}),
            observations=data.get("observations", []),
            iterations=data.get("iterations", []),
            proposals=data.get("proposals", []),
            decisions=data.get("decisions", []),
            checkpoints=data.get("checkpoints", []),
            metadata=data.get("metadata", {}),
        )


def validate_bundle(data: Dict[str, Any]) -> ExportBundle:
    """
    Validate an import bundle.
    
    Args:
        data: Bundle data dictionary
        
    Returns:
        Validated ExportBundle
        
    Raises:
        ValueError: If bundle is invalid
    """
    required_fields = ["version", "process", "campaign"]
    
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")
    
    # Validate version
    if data["version"] not in ["1.0"]:
        raise ValueError(f"Unsupported bundle version: {data['version']}")
    
    # Validate process
    process = data["process"]
    if "name" not in process:
        raise ValueError("Process must have a name")
    
    # Validate campaign
    campaign = data["campaign"]
    if "name" not in campaign:
        raise ValueError("Campaign must have a name")
    
    return ExportBundle.from_dict(data)


class CampaignExporter:
    """Exports campaigns to bundle format."""
    
    def __init__(self, session: Session):
        """
        Initialize exporter.
        
        Args:
            session: Database session
        """
        self.session = session
        self.process_repo = ProcessRepository(session)
        self.campaign_repo = CampaignRepository(session)
        self.obs_repo = ObservationRepository(session)
        self.iter_repo = IterationRepository(session)
        self.proposal_repo = ProposalRepository(session)
        self.decision_repo = DecisionRepository(session)
        self.checkpoint_repo = CheckpointRepository(session)
    
    def export(self, campaign_id: UUID) -> Dict[str, Any]:
        """
        Export a campaign to a bundle dictionary.
        
        Args:
            campaign_id: Campaign ID to export
            
        Returns:
            Bundle dictionary
            
        Raises:
            ValueError: If campaign not found
        """
        # Get campaign
        campaign = self.campaign_repo.get(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign not found: {campaign_id}")
        
        # Get process
        process = self.process_repo.get(campaign.process_id)
        if not process:
            raise ValueError(f"Process not found: {campaign.process_id}")
        
        # Get related data
        observations = self.obs_repo.list(campaign_id)
        iterations = self.iter_repo.list(campaign_id)
        
        proposals = []
        decisions = []
        for iteration in iterations:
            iter_proposals = self.proposal_repo.list(iteration_id=iteration.id)
            proposals.extend(iter_proposals)
            
            decision = self.decision_repo.get_by_iteration(iteration.id)
            if decision:
                decisions.append(decision)
        
        checkpoints = self.checkpoint_repo.list(campaign_id)
        
        # Build bundle
        bundle = ExportBundle(
            version="1.0",
            process={
                "name": process.name,
                "version": process.version,
                "spec_yaml": process.spec_yaml,
                "metadata": process.metadata or {},
            },
            campaign={
                "name": campaign.name,
                "status": campaign.status.value if hasattr(campaign.status, 'value') else campaign.status,
                "metadata": campaign.metadata or {},
            },
            observations=[
                {
                    "inputs": obs.x_raw,
                    "outputs": obs.y,
                    "metadata": obs.metadata_ or {},
                }
                for obs in observations
            ],
            iterations=[
                {
                    "index": iter.index,
                    "acquisition_config": iter.acquisition_config or {},
                }
                for iter in iterations
            ],
            proposals=[
                {
                    "iteration_index": self._get_iteration_index(prop.iteration_id),
                    "candidate_index": prop.candidate_index,
                    "inputs": prop.inputs,
                    "acquisition_value": prop.acquisition_value,
                }
                for prop in proposals
            ],
            decisions=[
                {
                    "iteration_index": self._get_iteration_index(dec.iteration_id),
                    "selected_indices": dec.selected_indices,
                    "reason": dec.reason,
                }
                for dec in decisions
            ],
            checkpoints=[
                {
                    "iteration_index": cp.iteration_index,
                    "model_type": cp.model_type,
                    # Note: model_state is binary and not exported
                }
                for cp in checkpoints
            ],
        )
        
        return bundle.to_dict()
    
    def _get_iteration_index(self, iteration_id: UUID) -> int:
        """Get iteration index by ID."""
        iteration = self.iter_repo.get(iteration_id)
        return iteration.index if iteration else -1
    
    def export_to_file(self, campaign_id: UUID, output_path: Path) -> None:
        """
        Export campaign to a file.
        
        Args:
            campaign_id: Campaign ID to export
            output_path: Output file path
        """
        bundle = self.export(campaign_id)
        
        with open(output_path, "w") as f:
            json.dump(bundle, f, indent=2, default=str)


class CampaignImporter:
    """Imports campaigns from bundle format."""
    
    def __init__(self, session: Session):
        """
        Initialize importer.
        
        Args:
            session: Database session
        """
        self.session = session
        self.process_repo = ProcessRepository(session)
        self.campaign_repo = CampaignRepository(session)
        self.obs_repo = ObservationRepository(session)
        self.iter_repo = IterationRepository(session)
        self.proposal_repo = ProposalRepository(session)
        self.decision_repo = DecisionRepository(session)
    
    def import_from_dict(self, data: Dict[str, Any]) -> UUID:
        """
        Import a campaign from a bundle dictionary.
        
        Args:
            data: Bundle data dictionary
            
        Returns:
            Created campaign ID
            
        Raises:
            ValueError: If bundle is invalid
        """
        bundle = validate_bundle(data)
        
        # Create or get process
        process = self._create_or_get_process(bundle.process)
        
        # Create campaign
        campaign = Campaign(
            id=uuid4(),
            process_id=process.id,
            name=bundle.campaign.get("name", "Imported Campaign"),
            status=CampaignStatus.ACTIVE,
            metadata=bundle.campaign.get("metadata", {}),
        )
        self.campaign_repo.create(campaign)
        
        # Import observations
        for obs_data in bundle.observations:
            obs = Observation(
                id=uuid4(),
                campaign_id=campaign.id,
                x_raw=obs_data.get("inputs", {}),
                y=obs_data.get("outputs", {}),
                metadata_=obs_data.get("metadata", {}),
            )
            self.obs_repo.create(obs)
        
        # Import iterations, proposals, and decisions
        iteration_map: Dict[int, UUID] = {}
        
        for iter_data in bundle.iterations:
            iteration = Iteration(
                id=uuid4(),
                campaign_id=campaign.id,
                index=iter_data.get("index", 0),
                acquisition_config=iter_data.get("acquisition_config", {}),
            )
            self.iter_repo.create(iteration)
            iteration_map[iteration.index] = iteration.id
        
        for prop_data in bundle.proposals:
            iter_index = prop_data.get("iteration_index", 0)
            if iter_index in iteration_map:
                proposal = Proposal(
                    id=uuid4(),
                    iteration_id=iteration_map[iter_index],
                    candidate_index=prop_data.get("candidate_index", 0),
                    inputs=prop_data.get("inputs", {}),
                    acquisition_value=prop_data.get("acquisition_value"),
                )
                self.proposal_repo.create(proposal)
        
        for dec_data in bundle.decisions:
            iter_index = dec_data.get("iteration_index", 0)
            if iter_index in iteration_map:
                decision = Decision(
                    id=uuid4(),
                    iteration_id=iteration_map[iter_index],
                    selected_indices=dec_data.get("selected_indices", []),
                    reason=dec_data.get("reason"),
                )
                self.decision_repo.create(decision)
        
        return campaign.id
    
    def _create_or_get_process(self, process_data: Dict[str, Any]) -> Process:
        """Create or get an existing process."""
        name = process_data.get("name", "Imported Process")
        
        # Check for existing process
        existing = self.process_repo.get_by_name(name)
        if existing:
            return existing
        
        # Create new process
        process = Process(
            id=uuid4(),
            name=name,
            version=1,
            spec_yaml=process_data.get("spec_yaml", ""),
            metadata=process_data.get("metadata", {}),
            is_active=True,
        )
        self.process_repo.create(process)
        
        return process
    
    def import_from_file(self, file_path: Path) -> UUID:
        """
        Import a campaign from a file.
        
        Args:
            file_path: Path to bundle file
            
        Returns:
            Created campaign ID
            
        Raises:
            FileNotFoundError: If file not found
            ValueError: If bundle is invalid
        """
        with open(file_path) as f:
            data = json.load(f)
        
        return self.import_from_dict(data)

