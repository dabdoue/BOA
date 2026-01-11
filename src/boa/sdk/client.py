"""
BOA Python SDK Client

Main client for interacting with BOA server.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

import httpx

from boa.sdk.exceptions import (
    BOAConnectionError,
    BOANotFoundError,
    BOAValidationError,
    BOAServerError,
)


class BOAClient:
    """
    Python client for BOA server.
    
    Provides methods for all API operations.
    
    Example:
        client = BOAClient("http://localhost:8000")
        
        # Create process
        process = client.create_process(
            name="my_process",
            spec_yaml=open("spec.yaml").read()
        )
        
        # Create campaign
        campaign = client.create_campaign(
            process_id=process["id"],
            name="my_campaign"
        )
        
        # Run optimization
        proposals = client.initial_design(campaign["id"], n_samples=10)
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        timeout: float = 30.0,
        headers: Dict[str, str] | None = None,
    ):
        """
        Initialize BOA client.
        
        Args:
            base_url: BOA server URL
            timeout: Request timeout in seconds
            headers: Additional headers
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            headers=headers or {},
        )
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def close(self):
        """Close the client."""
        self._client.close()
    
    def _handle_response(self, response: httpx.Response) -> Any:
        """Handle HTTP response and raise appropriate exceptions."""
        if response.status_code == 404:
            detail = response.json().get("detail", "Not found")
            raise BOANotFoundError("Resource", detail)
        elif response.status_code == 400:
            detail = response.json().get("detail", "Validation error")
            raise BOAValidationError(detail)
        elif response.status_code >= 500:
            detail = response.json().get("detail", "Server error")
            raise BOAServerError(response.status_code, detail)
        elif response.status_code >= 400:
            detail = response.json().get("detail", "Request error")
            raise BOAServerError(response.status_code, detail)
        
        if response.status_code == 204:
            return None
        
        return response.json()
    
    def _request(
        self,
        method: str,
        path: str,
        json: Any = None,
        params: Dict[str, Any] | None = None,
    ) -> Any:
        """Make HTTP request."""
        try:
            response = self._client.request(
                method,
                path,
                json=json,
                params=params,
            )
            return self._handle_response(response)
        except httpx.ConnectError as e:
            raise BOAConnectionError(f"Failed to connect to {self.base_url}: {e}")
    
    # =========================================================================
    # Health
    # =========================================================================
    
    def health(self) -> Dict[str, Any]:
        """Check server health."""
        return self._request("GET", "/health")
    
    # =========================================================================
    # Processes
    # =========================================================================
    
    def create_process(
        self,
        name_or_spec: str,
        spec_yaml: str | None = None,
        description: str | None = None,
    ) -> Dict[str, Any]:
        """
        Create a new process.
        
        Args:
            name_or_spec: Process name (when spec_yaml provided) or spec YAML directly
            spec_yaml: Optional spec YAML (if name_or_spec is the name)
            description: Optional description
            
        For backwards compatibility:
            - create_process("name", spec_yaml) -> name="name", spec=spec_yaml
            - create_process(spec_yaml) -> spec=name_or_spec, name from spec
        """
        if spec_yaml is not None:
            # Old signature: create_process(name, spec_yaml)
            data = {"name": name_or_spec, "spec_yaml": spec_yaml}
        else:
            # New signature: create_process(spec_yaml) - name from spec
            data = {"spec_yaml": name_or_spec}
        
        if description is not None:
            data["description"] = description
        return self._request("POST", "/processes", json=data)
    
    def list_processes(
        self,
        name: str | None = None,
        is_active: bool | None = True,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List processes."""
        params = {
            "limit": limit,
            "offset": offset,
        }
        if is_active is not None:
            params["active_only"] = is_active
        if name:
            params["name"] = name
        return self._request("GET", "/processes", params=params)
    
    def get_process(self, process_id: str | UUID) -> Dict[str, Any]:
        """Get a process by ID."""
        return self._request("GET", f"/processes/{process_id}")
    
    def update_process(
        self,
        process_id: str | UUID,
        description: str | None = None,
        spec_yaml: str | None = None,
    ) -> Dict[str, Any]:
        """Update a process."""
        data = {}
        if description is not None:
            data["description"] = description
        if spec_yaml is not None:
            data["spec_yaml"] = spec_yaml
        return self._request("PUT", f"/processes/{process_id}", json=data)
    
    def delete_process(self, process_id: str | UUID) -> None:
        """Delete (deactivate) a process."""
        self._request("DELETE", f"/processes/{process_id}")
    
    # =========================================================================
    # Campaigns
    # =========================================================================
    
    def create_campaign(
        self,
        process_id: str | UUID,
        name: str,
        description: str | None = None,
        strategy_config: Dict[str, Any] | None = None,
        metadata: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """Create a new campaign."""
        return self._request("POST", "/campaigns", json={
            "process_id": str(process_id),
            "name": name,
            "description": description,
            "strategy_config": strategy_config or {},
            "metadata": metadata or {},
        })
    
    def list_campaigns(
        self,
        process_id: str | UUID | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List campaigns."""
        params = {"limit": limit, "offset": offset}
        if process_id:
            params["process_id"] = str(process_id)
        if status:
            params["status"] = status
        return self._request("GET", "/campaigns", params=params)
    
    def get_campaign(self, campaign_id: str | UUID) -> Dict[str, Any]:
        """Get a campaign by ID."""
        return self._request("GET", f"/campaigns/{campaign_id}")
    
    def update_campaign(
        self,
        campaign_id: str | UUID,
        name: str | None = None,
        description: str | None = None,
        strategy_config: Dict[str, Any] | None = None,
        metadata: Dict[str, Any] | None = None,
        status: str | None = None,
    ) -> Dict[str, Any]:
        """Update a campaign."""
        data = {}
        if name is not None:
            data["name"] = name
        if description is not None:
            data["description"] = description
        if strategy_config is not None:
            data["strategy_config"] = strategy_config
        if metadata is not None:
            data["metadata"] = metadata
        if status is not None:
            data["status"] = status
        return self._request("PUT", f"/campaigns/{campaign_id}", json=data)
    
    def pause_campaign(self, campaign_id: str | UUID) -> Dict[str, Any]:
        """Pause a campaign."""
        return self._request("POST", f"/campaigns/{campaign_id}/pause")
    
    def resume_campaign(self, campaign_id: str | UUID) -> Dict[str, Any]:
        """Resume a paused campaign."""
        return self._request("POST", f"/campaigns/{campaign_id}/resume")
    
    def complete_campaign(self, campaign_id: str | UUID) -> Dict[str, Any]:
        """Mark a campaign as completed."""
        return self._request("POST", f"/campaigns/{campaign_id}/complete")
    
    def get_campaign_metrics(self, campaign_id: str | UUID) -> Dict[str, Any]:
        """Get campaign metrics."""
        return self._request("GET", f"/campaigns/{campaign_id}/metrics")
    
    # =========================================================================
    # Observations
    # =========================================================================
    
    def add_observation(
        self,
        campaign_id: str | UUID,
        x_raw: Dict[str, Any],
        y: Dict[str, Any],
        source: str = "user",
    ) -> Dict[str, Any]:
        """Add an observation."""
        return self._request(
            "POST",
            f"/campaigns/{campaign_id}/observations",
            json={"x_raw": x_raw, "y": y, "source": source},
        )
    
    def add_observations_batch(
        self,
        campaign_id: str | UUID,
        observations: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Add multiple observations."""
        return self._request(
            "POST",
            f"/campaigns/{campaign_id}/observations/batch",
            json={"observations": observations},
        )
    
    def list_observations(
        self,
        campaign_id: str | UUID,
        source: str | None = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List observations."""
        params = {"limit": limit, "offset": offset}
        if source:
            params["source"] = source
        return self._request(
            "GET",
            f"/campaigns/{campaign_id}/observations",
            params=params,
        )
    
    def get_observation(
        self,
        campaign_id: str | UUID,
        observation_id: str | UUID,
    ) -> Dict[str, Any]:
        """Get a specific observation."""
        return self._request(
            "GET",
            f"/campaigns/{campaign_id}/observations/{observation_id}",
        )
    
    # =========================================================================
    # Proposals
    # =========================================================================
    
    def initial_design(
        self,
        campaign_id: str | UUID,
        n_samples: int,
        strategy_name: str | None = None,
    ) -> List[Dict[str, Any]]:
        """Generate initial design samples."""
        data = {"n_samples": n_samples}
        if strategy_name:
            data["strategy_name"] = strategy_name
        return self._request(
            "POST",
            f"/campaigns/{campaign_id}/initial-design",
            json=data,
        )
    
    def propose(
        self,
        campaign_id: str | UUID,
        n_candidates: int = 1,
        strategy_names: List[str] | None = None,
        ref_point: List[float] | None = None,
    ) -> List[Dict[str, Any]]:
        """Generate optimization proposals."""
        data = {"n_candidates": n_candidates}
        if strategy_names:
            data["strategy_names"] = strategy_names
        if ref_point:
            data["ref_point"] = ref_point
        return self._request(
            "POST",
            f"/campaigns/{campaign_id}/propose",
            json=data,
        )
    
    def list_iterations(
        self,
        campaign_id: str | UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List iterations."""
        return self._request(
            "GET",
            f"/campaigns/{campaign_id}/iterations",
            params={"limit": limit, "offset": offset},
        )
    
    def get_iteration_proposals(
        self,
        campaign_id: str | UUID,
        iteration_index: int,
    ) -> List[Dict[str, Any]]:
        """Get proposals for an iteration."""
        return self._request(
            "GET",
            f"/campaigns/{campaign_id}/iterations/{iteration_index}/proposals",
        )
    
    def record_decision(
        self,
        campaign_id: str | UUID,
        iteration_index: int,
        accepted: List[Dict[str, Any]],
        notes: str | None = None,
    ) -> Dict[str, Any]:
        """Record a decision."""
        return self._request(
            "POST",
            f"/campaigns/{campaign_id}/iterations/{iteration_index}/decision",
            json={"accepted": accepted, "notes": notes},
        )
    
    # =========================================================================
    # Jobs
    # =========================================================================
    
    def list_jobs(
        self,
        campaign_id: str | UUID | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List jobs."""
        params = {"limit": limit, "offset": offset}
        if campaign_id:
            params["campaign_id"] = str(campaign_id)
        if status:
            params["status_filter"] = status
        return self._request("GET", "/jobs", params=params)
    
    def get_job(self, job_id: str | UUID) -> Dict[str, Any]:
        """Get a job by ID."""
        return self._request("GET", f"/jobs/{job_id}")
    
    def cancel_job(self, job_id: str | UUID) -> Dict[str, Any]:
        """Cancel a pending job."""
        return self._request("POST", f"/jobs/{job_id}/cancel")
    
    # =========================================================================
    # Export/Import
    # =========================================================================
    
    def export_campaign(self, campaign_id: str | UUID) -> Dict[str, Any]:
        """Export a campaign to a bundle dictionary."""
        return self._request("GET", f"/campaigns/{campaign_id}/export")
    
    def import_campaign(self, bundle: Dict[str, Any]) -> Dict[str, Any]:
        """Import a campaign from a bundle dictionary."""
        return self._request("POST", "/campaigns/import", json=bundle)
    
    # =========================================================================
    # Aliases for CLI compatibility
    # =========================================================================
    
    def generate_initial_design(
        self,
        campaign_id: str | UUID,
        n_samples: int,
        method: str = "lhs",
    ) -> Dict[str, Any]:
        """Generate initial design (alias for initial_design)."""
        samples = self.initial_design(campaign_id, n_samples, strategy_name=method)
        return {"samples": samples}
    
    def get_next_proposals(
        self,
        campaign_id: str | UUID,
        n_candidates: int = 1,
    ) -> Dict[str, Any]:
        """Get next proposals (alias for propose)."""
        proposals = self.propose(campaign_id, n_candidates=n_candidates)
        return {"proposals": proposals}

