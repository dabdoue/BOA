const API_BASE = '/api';

export interface Process {
  id: string;
  name: string;
  description: string | null;
  version: number;
  is_active: boolean;
  spec_yaml: string;
  spec_parsed: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface Campaign {
  id: string;
  process_id: string;
  name: string;
  description: string | null;
  status: 'draft' | 'active' | 'paused' | 'completed' | 'failed';
  strategy_config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface Observation {
  id: string;
  campaign_id: string;
  x_raw: Record<string, unknown>;
  x_encoded: number[];
  y_raw: Record<string, number>;
  y_transformed: number[];
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface Iteration {
  id: string;
  campaign_id: string;
  index: number;
  strategy_snapshot: Record<string, unknown>;
  metrics: Record<string, unknown>;
  created_at: string;
}

export interface Proposal {
  id: string;
  iteration_id: string;
  campaign_id: string;
  candidates: Array<Record<string, unknown>>;
  acquisition_values: number[];
  created_at: string;
}

export interface CampaignMetrics {
  pareto_front: number[][];
  pareto_front_size: number;
  hypervolume: number | null;
  observation_count: number;
  iteration_count: number;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }
  return response.json();
}

// Processes
export async function listProcesses(): Promise<Process[]> {
  const response = await fetch(`${API_BASE}/processes`);
  return handleResponse<Process[]>(response);
}

export async function getProcess(id: string): Promise<Process> {
  const response = await fetch(`${API_BASE}/processes/${id}`);
  return handleResponse<Process>(response);
}

export async function createProcess(data: { name: string; description?: string; spec_yaml: string }): Promise<Process> {
  const response = await fetch(`${API_BASE}/processes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return handleResponse<Process>(response);
}

export async function deleteProcess(id: string): Promise<void> {
  const response = await fetch(`${API_BASE}/processes/${id}`, { method: 'DELETE' });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }
}

// Campaigns
export async function listCampaigns(): Promise<Campaign[]> {
  const response = await fetch(`${API_BASE}/campaigns`);
  return handleResponse<Campaign[]>(response);
}

export async function getCampaign(id: string): Promise<Campaign> {
  const response = await fetch(`${API_BASE}/campaigns/${id}`);
  return handleResponse<Campaign>(response);
}

export async function createCampaign(data: { process_id: string; name: string; description?: string; strategy_config?: Record<string, unknown> }): Promise<Campaign> {
  const response = await fetch(`${API_BASE}/campaigns`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return handleResponse<Campaign>(response);
}

export async function updateCampaign(id: string, data: { name?: string; description?: string; status?: string }): Promise<Campaign> {
  const response = await fetch(`${API_BASE}/campaigns/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return handleResponse<Campaign>(response);
}

// Observations
export async function listObservations(campaignId: string): Promise<Observation[]> {
  const response = await fetch(`${API_BASE}/campaigns/${campaignId}/observations`);
  return handleResponse<Observation[]>(response);
}

export async function createObservation(campaignId: string, data: { x_raw: Record<string, unknown>; y_raw: Record<string, number>; metadata?: Record<string, unknown> }): Promise<Observation> {
  const response = await fetch(`${API_BASE}/campaigns/${campaignId}/observations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return handleResponse<Observation>(response);
}

// Proposals
export async function propose(campaignId: string, nCandidates: number = 1): Promise<Proposal> {
  const response = await fetch(`${API_BASE}/campaigns/${campaignId}/propose?n_candidates=${nCandidates}`, {
    method: 'POST',
  });
  return handleResponse<Proposal>(response);
}

export async function listIterations(campaignId: string): Promise<Iteration[]> {
  const response = await fetch(`${API_BASE}/campaigns/${campaignId}/iterations`);
  return handleResponse<Iteration[]>(response);
}

// Metrics
export async function getCampaignMetrics(campaignId: string): Promise<CampaignMetrics> {
  const response = await fetch(`${API_BASE}/campaigns/${campaignId}/metrics`);
  return handleResponse<CampaignMetrics>(response);
}

// Health check
export async function getHealth(): Promise<{ status: string }> {
  const response = await fetch(`${API_BASE}/health`);
  return handleResponse<{ status: string }>(response);
}





