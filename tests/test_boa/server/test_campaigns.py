"""
Tests for BOA campaign endpoints.
"""

import pytest
from fastapi.testclient import TestClient


class TestCampaignEndpoints:
    """Tests for campaign CRUD endpoints."""
    
    @pytest.fixture
    def process_id(self, client: TestClient, sample_spec_yaml: str) -> str:
        """Create a process and return its ID."""
        response = client.post(
            "/processes",
            json={
                "name": "campaign_test_process",
                "spec_yaml": sample_spec_yaml,
            },
        )
        return response.json()["id"]
    
    def test_create_campaign(self, client: TestClient, process_id: str):
        """Test creating a campaign."""
        response = client.post(
            "/campaigns",
            json={
                "process_id": process_id,
                "name": "test_campaign",
                "description": "A test campaign",
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "test_campaign"
        assert data["status"] == "created"
        assert data["process_id"] == process_id
    
    def test_create_campaign_invalid_process(self, client: TestClient):
        """Test creating campaign with invalid process ID."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.post(
            "/campaigns",
            json={
                "process_id": fake_id,
                "name": "bad_campaign",
            },
        )
        
        assert response.status_code == 404
    
    def test_list_campaigns(self, client: TestClient, process_id: str):
        """Test listing campaigns."""
        # Create a campaign
        client.post(
            "/campaigns",
            json={
                "process_id": process_id,
                "name": "list_test",
            },
        )
        
        response = client.get("/campaigns")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
    
    def test_list_campaigns_by_process(self, client: TestClient, process_id: str):
        """Test filtering campaigns by process."""
        # Create campaign
        client.post(
            "/campaigns",
            json={
                "process_id": process_id,
                "name": "filter_test",
            },
        )
        
        response = client.get(f"/campaigns?process_id={process_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert all(c["process_id"] == process_id for c in data)
    
    def test_get_campaign(self, client: TestClient, process_id: str):
        """Test getting a campaign by ID."""
        # Create
        create_response = client.post(
            "/campaigns",
            json={
                "process_id": process_id,
                "name": "get_test",
            },
        )
        campaign_id = create_response.json()["id"]
        
        # Get
        response = client.get(f"/campaigns/{campaign_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == campaign_id
    
    def test_update_campaign(self, client: TestClient, process_id: str):
        """Test updating a campaign."""
        # Create
        create_response = client.post(
            "/campaigns",
            json={
                "process_id": process_id,
                "name": "update_test",
            },
        )
        campaign_id = create_response.json()["id"]
        
        # Update
        response = client.put(
            f"/campaigns/{campaign_id}",
            json={"name": "updated_name"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "updated_name"
    
    def test_campaign_lifecycle(self, client: TestClient, process_id: str):
        """Test campaign status transitions."""
        # Create
        create_response = client.post(
            "/campaigns",
            json={
                "process_id": process_id,
                "name": "lifecycle_test",
            },
        )
        campaign_id = create_response.json()["id"]
        
        # Initial status should be "created"
        assert create_response.json()["status"] == "created"
        
        # Generate initial design to activate
        client.post(
            f"/campaigns/{campaign_id}/initial-design",
            json={"n_samples": 3},
        )
        
        # Check status is now active
        get_response = client.get(f"/campaigns/{campaign_id}")
        assert get_response.json()["status"] == "active"
        
        # Pause
        pause_response = client.post(f"/campaigns/{campaign_id}/pause")
        assert pause_response.status_code == 200
        assert pause_response.json()["status"] == "paused"
        
        # Resume
        resume_response = client.post(f"/campaigns/{campaign_id}/resume")
        assert resume_response.status_code == 200
        assert resume_response.json()["status"] == "active"
        
        # Complete
        complete_response = client.post(f"/campaigns/{campaign_id}/complete")
        assert complete_response.status_code == 200
        assert complete_response.json()["status"] == "completed"





