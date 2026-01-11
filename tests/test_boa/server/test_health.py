"""
Tests for BOA health endpoints.
"""

import pytest
from fastapi.testclient import TestClient

from boa import __version__


class TestHealthEndpoints:
    """Tests for health check endpoints."""
    
    def test_health_check(self, client: TestClient):
        """Test health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == __version__
        assert data["database"] == "sqlite"





