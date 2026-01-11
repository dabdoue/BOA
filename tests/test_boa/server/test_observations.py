"""
Tests for BOA observation endpoints.
"""

import pytest
from fastapi.testclient import TestClient


class TestObservationEndpoints:
    """Tests for observation CRUD endpoints."""
    
    @pytest.fixture
    def campaign_id(self, client: TestClient, sample_spec_yaml: str) -> str:
        """Create a process and campaign, return campaign ID."""
        # Create process
        process_response = client.post(
            "/processes",
            json={
                "name": "obs_test_process",
                "spec_yaml": sample_spec_yaml,
            },
        )
        process_id = process_response.json()["id"]
        
        # Create campaign
        campaign_response = client.post(
            "/campaigns",
            json={
                "process_id": process_id,
                "name": "obs_test_campaign",
            },
        )
        return campaign_response.json()["id"]
    
    def test_create_observation(self, client: TestClient, campaign_id: str):
        """Test adding an observation."""
        response = client.post(
            f"/campaigns/{campaign_id}/observations",
            json={
                "x_raw": {"x1": 5.0, "x2": 0.0},
                "y": {"y": 10.0},
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["x_raw"] == {"x1": 5.0, "x2": 0.0}
        assert data["y"] == {"y": 10.0}
        assert data["source"] == "user"
    
    def test_create_observations_batch(self, client: TestClient, campaign_id: str):
        """Test adding multiple observations."""
        response = client.post(
            f"/campaigns/{campaign_id}/observations/batch",
            json={
                "observations": [
                    {"x_raw": {"x1": 1.0, "x2": 0.0}, "y": {"y": 1.0}},
                    {"x_raw": {"x1": 2.0, "x2": 1.0}, "y": {"y": 2.5}},
                    {"x_raw": {"x1": 3.0, "x2": -1.0}, "y": {"y": 3.0}},
                ],
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert len(data) == 3
    
    def test_list_observations(self, client: TestClient, campaign_id: str):
        """Test listing observations."""
        # Add some observations
        client.post(
            f"/campaigns/{campaign_id}/observations",
            json={"x_raw": {"x1": 1.0, "x2": 0.0}, "y": {"y": 1.0}},
        )
        client.post(
            f"/campaigns/{campaign_id}/observations",
            json={"x_raw": {"x1": 2.0, "x2": 0.0}, "y": {"y": 2.0}},
        )
        
        response = client.get(f"/campaigns/{campaign_id}/observations")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
    
    def test_get_observation(self, client: TestClient, campaign_id: str):
        """Test getting a specific observation."""
        # Create
        create_response = client.post(
            f"/campaigns/{campaign_id}/observations",
            json={"x_raw": {"x1": 5.0, "x2": 2.0}, "y": {"y": 7.0}},
        )
        obs_id = create_response.json()["id"]
        
        # Get
        response = client.get(f"/campaigns/{campaign_id}/observations/{obs_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == obs_id





