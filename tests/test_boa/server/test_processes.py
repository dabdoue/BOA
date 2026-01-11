"""
Tests for BOA process endpoints.
"""

import pytest
from fastapi.testclient import TestClient


class TestProcessEndpoints:
    """Tests for process CRUD endpoints."""
    
    def test_create_process(self, client: TestClient, sample_spec_yaml: str):
        """Test creating a process."""
        response = client.post(
            "/processes",
            json={
                "name": "test_process",
                "description": "A test process",
                "spec_yaml": sample_spec_yaml,
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "test_process"
        assert data["version"] == 1
        assert data["is_active"] is True
        assert "id" in data
    
    def test_create_process_invalid_spec(self, client: TestClient):
        """Test creating process with invalid spec."""
        response = client.post(
            "/processes",
            json={
                "name": "bad_process",
                "spec_yaml": "invalid: yaml: content",
            },
        )
        
        assert response.status_code == 400
    
    def test_list_processes(self, client: TestClient, sample_spec_yaml: str):
        """Test listing processes."""
        # Create a process first
        client.post(
            "/processes",
            json={
                "name": "list_test",
                "spec_yaml": sample_spec_yaml,
            },
        )
        
        response = client.get("/processes")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
    
    def test_get_process(self, client: TestClient, sample_spec_yaml: str):
        """Test getting a process by ID."""
        # Create
        create_response = client.post(
            "/processes",
            json={
                "name": "get_test",
                "spec_yaml": sample_spec_yaml,
            },
        )
        process_id = create_response.json()["id"]
        
        # Get
        response = client.get(f"/processes/{process_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == process_id
        assert data["name"] == "get_test"
        assert "spec_yaml" in data
        assert "spec_parsed" in data
    
    def test_get_process_not_found(self, client: TestClient):
        """Test getting non-existent process."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/processes/{fake_id}")
        
        assert response.status_code == 404
    
    def test_update_process_description(self, client: TestClient, sample_spec_yaml: str):
        """Test updating process description."""
        # Create
        create_response = client.post(
            "/processes",
            json={
                "name": "update_test",
                "spec_yaml": sample_spec_yaml,
            },
        )
        process_id = create_response.json()["id"]
        
        # Update
        response = client.put(
            f"/processes/{process_id}",
            json={"description": "Updated description"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Updated description"
    
    def test_delete_process(self, client: TestClient, sample_spec_yaml: str):
        """Test deleting (deactivating) a process."""
        # Create
        create_response = client.post(
            "/processes",
            json={
                "name": "delete_test",
                "spec_yaml": sample_spec_yaml,
            },
        )
        process_id = create_response.json()["id"]
        
        # Delete
        response = client.delete(f"/processes/{process_id}")
        
        assert response.status_code == 204
        
        # Verify it's inactive
        get_response = client.get(f"/processes/{process_id}")
        assert get_response.json()["is_active"] is False





