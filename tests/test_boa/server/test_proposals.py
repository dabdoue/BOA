"""
Tests for BOA proposal endpoints.
"""

import pytest
from fastapi.testclient import TestClient


class TestProposalEndpoints:
    """Tests for proposal generation endpoints."""
    
    @pytest.fixture
    def campaign_id(self, client: TestClient, sample_spec_yaml: str) -> str:
        """Create a process and campaign, return campaign ID."""
        # Create process
        process_response = client.post(
            "/processes",
            json={
                "name": "proposal_test_process",
                "spec_yaml": sample_spec_yaml,
            },
        )
        process_id = process_response.json()["id"]
        
        # Create campaign
        campaign_response = client.post(
            "/campaigns",
            json={
                "process_id": process_id,
                "name": "proposal_test_campaign",
            },
        )
        return campaign_response.json()["id"]
    
    def test_initial_design(self, client: TestClient, campaign_id: str):
        """Test generating initial design."""
        response = client.post(
            f"/campaigns/{campaign_id}/initial-design",
            json={"n_samples": 5},
        )
        
        assert response.status_code == 201
        data = response.json()
        assert len(data) == 1  # One proposal
        assert len(data[0]["candidates_raw"]) == 5
    
    def test_propose_without_data(self, client: TestClient, campaign_id: str):
        """Test proposing without training data fails."""
        response = client.post(
            f"/campaigns/{campaign_id}/propose",
            json={"n_candidates": 1},
        )
        
        assert response.status_code == 400
        assert "No training data" in response.json()["detail"]
    
    def test_propose_with_data(self, client: TestClient, campaign_id: str):
        """Test generating proposals with training data."""
        # Add observations
        for i in range(10):
            client.post(
                f"/campaigns/{campaign_id}/observations",
                json={
                    "x_raw": {"x1": float(i), "x2": float(i - 5)},
                    "y": {"y": float(i * 2)},
                },
            )
        
        # Generate proposals
        response = client.post(
            f"/campaigns/{campaign_id}/propose",
            json={"n_candidates": 2},
        )
        
        assert response.status_code == 201
        data = response.json()
        assert len(data) >= 1
        assert len(data[0]["candidates_raw"]) == 2
    
    def test_list_iterations(self, client: TestClient, campaign_id: str):
        """Test listing iterations."""
        # Run initial design to create an iteration
        client.post(
            f"/campaigns/{campaign_id}/initial-design",
            json={"n_samples": 3},
        )
        
        response = client.get(f"/campaigns/{campaign_id}/iterations")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["index"] == 0
    
    def test_get_iteration_proposals(self, client: TestClient, campaign_id: str):
        """Test getting proposals for an iteration."""
        # Run initial design
        client.post(
            f"/campaigns/{campaign_id}/initial-design",
            json={"n_samples": 3},
        )
        
        response = client.get(f"/campaigns/{campaign_id}/iterations/0/proposals")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
    
    def test_create_decision(self, client: TestClient, campaign_id: str):
        """Test recording a decision."""
        # Run initial design
        design_response = client.post(
            f"/campaigns/{campaign_id}/initial-design",
            json={"n_samples": 3},
        )
        proposal_id = design_response.json()[0]["id"]
        
        # Record decision
        response = client.post(
            f"/campaigns/{campaign_id}/iterations/0/decision",
            json={
                "accepted": [
                    {"proposal_id": proposal_id, "candidate_indices": [0, 1]},
                ],
                "notes": "Accepted first two candidates",
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert len(data["accepted"]) == 1
        assert data["notes"] == "Accepted first two candidates"





