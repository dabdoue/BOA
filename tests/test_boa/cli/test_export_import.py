"""
Tests for BOA export/import functionality.
"""

import json
import pytest
from pathlib import Path
import tempfile
from uuid import uuid4

from boa.cli.export_import import (
    ExportBundle,
    CampaignExporter,
    CampaignImporter,
    validate_bundle,
)
from boa.db.models import Process, Campaign, Observation, CampaignStatus
from boa.db.repository import ProcessRepository, CampaignRepository, ObservationRepository
from boa.db.connection import create_db_and_tables, drop_db_and_tables, get_session


@pytest.fixture
def temp_dir():
    """Create a temporary directory for exports."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestExportBundle:
    """Tests for ExportBundle dataclass."""
    
    def test_bundle_creation(self):
        """Test creating an export bundle."""
        bundle = ExportBundle(
            version="1.0",
            process={
                "name": "test_process",
                "spec_yaml": "inputs: []",
            },
            campaign={
                "name": "test_campaign",
            },
            observations=[
                {"inputs": {"x": 1}, "outputs": {"y": 2}},
            ],
        )
        
        assert bundle.version == "1.0"
        assert bundle.process["name"] == "test_process"
        assert len(bundle.observations) == 1
    
    def test_bundle_to_json(self):
        """Test serializing bundle to JSON."""
        bundle = ExportBundle(
            version="1.0",
            process={"name": "test"},
            campaign={"name": "campaign"},
        )
        
        data = bundle.to_dict()
        json_str = json.dumps(data)
        
        assert "version" in json_str
        assert "process" in json_str


class TestValidateBundle:
    """Tests for bundle validation."""
    
    def test_valid_bundle(self):
        """Test validating a valid bundle."""
        data = {
            "version": "1.0",
            "process": {"name": "test", "spec_yaml": "inputs: []"},
            "campaign": {"name": "campaign"},
        }
        
        bundle = validate_bundle(data)
        
        assert bundle.version == "1.0"
        assert bundle.process["name"] == "test"
    
    def test_invalid_bundle_missing_version(self):
        """Test validating bundle with missing version."""
        data = {
            "process": {"name": "test"},
            "campaign": {"name": "campaign"},
        }
        
        with pytest.raises(ValueError, match="version"):
            validate_bundle(data)
    
    def test_invalid_bundle_missing_process(self):
        """Test validating bundle with missing process."""
        data = {
            "version": "1.0",
            "campaign": {"name": "campaign"},
        }
        
        with pytest.raises(ValueError, match="process"):
            validate_bundle(data)


class TestCampaignExporter:
    """Tests for CampaignExporter."""
    
    def test_export_to_dict(self, session, sample_process, sample_campaign, temp_dir):
        """Test exporting campaign to dictionary."""
        # Add to session
        session.add(sample_process)
        session.add(sample_campaign)
        session.commit()
        
        # Add observations
        obs = Observation(
            id=uuid4(),
            campaign_id=sample_campaign.id,
            x_raw={"x": 0.5},
            y={"y": 1.0},
        )
        session.add(obs)
        session.commit()
        
        # Export
        exporter = CampaignExporter(session)
        bundle = exporter.export(sample_campaign.id)
        
        assert bundle["version"] == "1.0"
        assert bundle["process"]["name"] == sample_process.name
        assert bundle["campaign"]["name"] == sample_campaign.name
        assert len(bundle.get("observations", [])) == 1
    
    def test_export_to_file(self, session, sample_process, sample_campaign, temp_dir):
        """Test exporting campaign to file."""
        session.add(sample_process)
        session.add(sample_campaign)
        session.commit()
        
        exporter = CampaignExporter(session)
        output_path = temp_dir / "campaign.json"
        
        exporter.export_to_file(sample_campaign.id, output_path)
        
        assert output_path.exists()
        
        with open(output_path) as f:
            data = json.load(f)
        
        assert data["version"] == "1.0"
        assert data["process"]["name"] == sample_process.name


class TestCampaignImporter:
    """Tests for CampaignImporter."""
    
    def test_import_from_dict(self, session, temp_dir):
        """Test importing campaign from dictionary."""
        bundle_data = {
            "version": "1.0",
            "process": {
                "name": "imported_process",
                "spec_yaml": """
inputs:
  - name: x
    type: continuous
    bounds: [0, 1]
objectives:
  - name: y
    target: minimize
""",
            },
            "campaign": {
                "name": "imported_campaign",
                "metadata": {"source": "import"},
            },
            "observations": [
                {"inputs": {"x": 0.5}, "outputs": {"y": 1.0}},
            ],
        }
        
        importer = CampaignImporter(session)
        campaign_id = importer.import_from_dict(bundle_data)
        
        assert campaign_id is not None
        
        # Verify campaign was created
        campaign_repo = CampaignRepository(session)
        campaign = campaign_repo.get(campaign_id)
        
        assert campaign is not None
        assert campaign.name == "imported_campaign"
        
        # Verify observations
        obs_repo = ObservationRepository(session)
        observations = obs_repo.list(campaign_id)
        
        assert len(observations) == 1
    
    def test_import_from_file(self, session, temp_dir):
        """Test importing campaign from file."""
        bundle_data = {
            "version": "1.0",
            "process": {
                "name": "file_imported_process",
                "spec_yaml": """
inputs:
  - name: x
    type: continuous
    bounds: [0, 1]
objectives:
  - name: y
    target: minimize
""",
            },
            "campaign": {
                "name": "file_imported_campaign",
            },
        }
        
        file_path = temp_dir / "import.json"
        with open(file_path, "w") as f:
            json.dump(bundle_data, f)
        
        importer = CampaignImporter(session)
        campaign_id = importer.import_from_file(file_path)
        
        assert campaign_id is not None
        
        campaign_repo = CampaignRepository(session)
        campaign = campaign_repo.get(campaign_id)
        
        assert campaign.name == "file_imported_campaign"

