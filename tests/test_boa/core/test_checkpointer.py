"""
Tests for BOA model checkpointer.
"""

import tempfile
from pathlib import Path
from uuid import uuid4

import pytest
import torch

from boa.core.checkpointer import ModelCheckpointer


class TestModelCheckpointer:
    """Tests for ModelCheckpointer."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def sample_state_dict(self):
        """Create sample model state dict."""
        return {
            "weight": torch.randn(10, 5),
            "bias": torch.randn(10),
            "hyperparams": {"lengthscale": 0.5, "noise": 0.1},
        }
    
    def test_save_checkpoint(self, temp_dir: Path, sample_state_dict):
        """Test saving a checkpoint."""
        checkpointer = ModelCheckpointer(temp_dir)
        
        path = checkpointer.save(
            sample_state_dict,
            iteration_idx=0,
            strategy_name="default",
        )
        
        assert path is not None
        assert (temp_dir / path).exists()
    
    def test_load_checkpoint(self, temp_dir: Path, sample_state_dict):
        """Test loading a checkpoint."""
        checkpointer = ModelCheckpointer(temp_dir)
        
        path = checkpointer.save(
            sample_state_dict,
            iteration_idx=1,
            strategy_name="test",
        )
        
        loaded = checkpointer.load(path)
        
        assert "state_dict" in loaded
        assert loaded["iteration_idx"] == 1
        assert loaded["strategy_name"] == "test"
        torch.testing.assert_close(
            loaded["state_dict"]["weight"],
            sample_state_dict["weight"]
        )
    
    def test_load_latest(self, temp_dir: Path, sample_state_dict):
        """Test loading latest checkpoint."""
        checkpointer = ModelCheckpointer(temp_dir)
        
        # Save multiple checkpoints
        checkpointer.save(sample_state_dict, 0, "strategy1")
        checkpointer.save(sample_state_dict, 1, "strategy1")
        checkpointer.save(sample_state_dict, 2, "strategy1")
        
        latest = checkpointer.load_latest("strategy1")
        
        assert latest is not None
        assert latest["iteration_idx"] == 2
    
    def test_list_checkpoints(self, temp_dir: Path, sample_state_dict):
        """Test listing checkpoints."""
        checkpointer = ModelCheckpointer(temp_dir)
        
        checkpointer.save(sample_state_dict, 0, "default")
        checkpointer.save(sample_state_dict, 1, "default")
        checkpointer.save(sample_state_dict, 0, "other")
        
        all_checkpoints = checkpointer.list_checkpoints()
        assert len(all_checkpoints) == 3
        
        default_checkpoints = checkpointer.list_checkpoints("default")
        assert len(default_checkpoints) == 2
    
    def test_cleanup(self, temp_dir: Path, sample_state_dict):
        """Test cleaning up old checkpoints."""
        checkpointer = ModelCheckpointer(temp_dir)
        
        # Save 5 checkpoints
        for i in range(5):
            checkpointer.save(sample_state_dict, i, "default")
        
        # Keep only 2
        removed = checkpointer.cleanup(keep_latest=2, strategy_name="default")
        
        assert removed == 3
        remaining = checkpointer.list_checkpoints("default")
        assert len(remaining) == 2
    
    def test_campaign_namespacing(self, temp_dir: Path, sample_state_dict):
        """Test that campaign ID creates subdirectory."""
        campaign_id = uuid4()
        checkpointer = ModelCheckpointer(temp_dir, campaign_id)
        
        path = checkpointer.save(sample_state_dict, 0, "default")
        
        # Check subdirectory was created
        assert (temp_dir / str(campaign_id)).exists()
        assert (temp_dir / str(campaign_id) / path.split("/")[-1]).exists()
    
    def test_metadata_storage(self, temp_dir: Path, sample_state_dict):
        """Test storing metadata with checkpoint."""
        checkpointer = ModelCheckpointer(temp_dir)
        
        metadata = {"custom_key": "custom_value", "training_loss": 0.05}
        
        path = checkpointer.save(
            sample_state_dict,
            iteration_idx=0,
            strategy_name="default",
            metadata=metadata,
        )
        
        loaded = checkpointer.load(path)
        
        assert loaded["metadata"]["custom_key"] == "custom_value"
        assert loaded["metadata"]["training_loss"] == 0.05
    
    def test_file_size(self, temp_dir: Path, sample_state_dict):
        """Test getting file size."""
        checkpointer = ModelCheckpointer(temp_dir)
        
        path = checkpointer.save(sample_state_dict, 0, "default")
        
        size = checkpointer.get_file_size(path)
        
        assert size > 0





