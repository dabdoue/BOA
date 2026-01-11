import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as api from '@/api/client';

// Process hooks
export function useProcesses() {
  return useQuery({
    queryKey: ['processes'],
    queryFn: api.listProcesses,
  });
}

export function useProcess(id: string) {
  return useQuery({
    queryKey: ['processes', id],
    queryFn: () => api.getProcess(id),
    enabled: !!id,
  });
}

export function useCreateProcess() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.createProcess,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['processes'] });
    },
  });
}

export function useDeleteProcess() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.deleteProcess,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['processes'] });
    },
  });
}

// Campaign hooks
export function useCampaigns() {
  return useQuery({
    queryKey: ['campaigns'],
    queryFn: api.listCampaigns,
  });
}

export function useCampaign(id: string) {
  return useQuery({
    queryKey: ['campaigns', id],
    queryFn: () => api.getCampaign(id),
    enabled: !!id,
  });
}

export function useCreateCampaign() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.createCampaign,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
    },
  });
}

export function useUpdateCampaign() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Parameters<typeof api.updateCampaign>[1] }) =>
      api.updateCampaign(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
      queryClient.invalidateQueries({ queryKey: ['campaigns', variables.id] });
    },
  });
}

// Observation hooks
export function useObservations(campaignId: string) {
  return useQuery({
    queryKey: ['observations', campaignId],
    queryFn: () => api.listObservations(campaignId),
    enabled: !!campaignId,
  });
}

export function useCreateObservation(campaignId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof api.createObservation>[1]) =>
      api.createObservation(campaignId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['observations', campaignId] });
      queryClient.invalidateQueries({ queryKey: ['iterations', campaignId] });
      queryClient.invalidateQueries({ queryKey: ['metrics', campaignId] });
    },
  });
}

// Proposal hooks
export function usePropose(campaignId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (nCandidates: number = 1) => api.propose(campaignId, nCandidates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['iterations', campaignId] });
    },
  });
}

export function useIterations(campaignId: string) {
  return useQuery({
    queryKey: ['iterations', campaignId],
    queryFn: () => api.listIterations(campaignId),
    enabled: !!campaignId,
  });
}

// Metrics hook
export function useCampaignMetrics(campaignId: string) {
  return useQuery({
    queryKey: ['metrics', campaignId],
    queryFn: () => api.getCampaignMetrics(campaignId),
    enabled: !!campaignId,
    refetchInterval: 5000, // Auto-refresh every 5 seconds
  });
}

// Health hook
export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: api.getHealth,
    refetchInterval: 10000, // Check every 10 seconds
    retry: 1,
  });
}





