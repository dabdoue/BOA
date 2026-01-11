"""
BOA Model Checkpointer

Save and load model states for campaign recovery.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import UUID
import pickle

import torch

from boa.db.models import Checkpoint, Campaign

logger = logging.getLogger(__name__)


class ModelCheckpointer:
    """
    Handles saving and loading model checkpoints.
    
    Enables:
    - Campaign recovery after crashes
    - Model persistence between sessions
    - Version tracking of model states
    """
    
    def __init__(
        self,
        checkpoint_dir: Path | str,
        campaign_id: Optional[UUID] = None,
    ):
        """
        Initialize checkpointer.
        
        Args:
            checkpoint_dir: Directory to store checkpoints
            campaign_id: Optional campaign ID for namespacing
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.campaign_id = campaign_id
        
        # Create checkpoint directory
        if campaign_id:
            self.campaign_dir = self.checkpoint_dir / str(campaign_id)
        else:
            self.campaign_dir = self.checkpoint_dir
        
        self.campaign_dir.mkdir(parents=True, exist_ok=True)
    
    def save(
        self,
        state_dict: Dict[str, Any],
        iteration_idx: int,
        strategy_name: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Save model checkpoint.
        
        Args:
            state_dict: Model state dictionary
            iteration_idx: Iteration index
            strategy_name: Name of the strategy
            metadata: Optional additional metadata
            
        Returns:
            Path to saved checkpoint (relative to checkpoint_dir)
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"checkpoint_iter{iteration_idx}_{strategy_name}_{timestamp}.pt"
        filepath = self.campaign_dir / filename
        
        # Build checkpoint data
        checkpoint_data = {
            "state_dict": state_dict,
            "iteration_idx": iteration_idx,
            "strategy_name": strategy_name,
            "timestamp": timestamp,
            "metadata": metadata or {},
        }
        
        # Save with torch
        torch.save(checkpoint_data, filepath)
        
        logger.info(f"Saved checkpoint: {filepath}")
        
        # Return relative path
        return str(filepath.relative_to(self.checkpoint_dir))
    
    def load(
        self,
        path: str,
    ) -> Dict[str, Any]:
        """
        Load model checkpoint.
        
        Args:
            path: Path to checkpoint (relative to checkpoint_dir)
            
        Returns:
            Checkpoint data dictionary
        """
        filepath = self.checkpoint_dir / path
        
        if not filepath.exists():
            raise FileNotFoundError(f"Checkpoint not found: {filepath}")
        
        checkpoint_data = torch.load(filepath, map_location="cpu", weights_only=False)
        
        logger.info(f"Loaded checkpoint: {filepath}")
        
        return checkpoint_data
    
    def load_latest(
        self,
        strategy_name: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Load the most recent checkpoint.
        
        Args:
            strategy_name: Optional filter by strategy name
            
        Returns:
            Checkpoint data or None if no checkpoints exist
        """
        pattern = f"checkpoint_*_{strategy_name}_*.pt" if strategy_name else "checkpoint_*.pt"
        checkpoints = sorted(
            self.campaign_dir.glob(pattern),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        
        if not checkpoints:
            return None
        
        return self.load(str(checkpoints[0].relative_to(self.checkpoint_dir)))
    
    def list_checkpoints(
        self,
        strategy_name: Optional[str] = None,
    ) -> list[str]:
        """
        List all checkpoints.
        
        Args:
            strategy_name: Optional filter by strategy name
            
        Returns:
            List of checkpoint paths
        """
        pattern = f"checkpoint_*_{strategy_name}_*.pt" if strategy_name else "checkpoint_*.pt"
        checkpoints = sorted(
            self.campaign_dir.glob(pattern),
            key=lambda p: p.stat().st_mtime,
        )
        
        return [str(p.relative_to(self.checkpoint_dir)) for p in checkpoints]
    
    def cleanup(
        self,
        keep_latest: int = 3,
        strategy_name: Optional[str] = None,
    ) -> int:
        """
        Remove old checkpoints.
        
        Args:
            keep_latest: Number of recent checkpoints to keep
            strategy_name: Optional filter by strategy name
            
        Returns:
            Number of checkpoints removed
        """
        pattern = f"checkpoint_*_{strategy_name}_*.pt" if strategy_name else "checkpoint_*.pt"
        checkpoints = sorted(
            self.campaign_dir.glob(pattern),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        
        to_remove = checkpoints[keep_latest:]
        
        for path in to_remove:
            path.unlink()
            logger.info(f"Removed old checkpoint: {path}")
        
        return len(to_remove)
    
    def get_file_size(self, path: str) -> int:
        """Get checkpoint file size in bytes."""
        filepath = self.checkpoint_dir / path
        return filepath.stat().st_size if filepath.exists() else 0





