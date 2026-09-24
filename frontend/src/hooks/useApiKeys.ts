import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { ApiKeyEntry, ApiKeyPayload, ApiProvider } from "@/types";

export const apiKeysKey = ["api-keys"] as const;
export const apiKeysExpiringKey = ["api-keys", "expiring"] as const;
export const apiProvidersKey = ["api-providers"] as const;

export function useApiKeys(enabled = true) {
  return useQuery({
    queryKey: apiKeysKey,
    enabled,
    queryFn: async () => (await api.get<ApiKeyEntry[]>("/api-keys")).data,
  });
}

/** Only the rows the dashboard card and the Monday digest care about. */
export function useExpiringApiKeys(enabled = true) {
  return useQuery({
    queryKey: apiKeysExpiringKey,
    enabled,
    staleTime: 5 * 60 * 1000,
    queryFn: async () => (await api.get<ApiKeyEntry[]>("/api-keys/expiring")).data,
  });
}

export function useApiProviders(enabled = true) {
  return useQuery({
    queryKey: apiProvidersKey,
    enabled,
    queryFn: async () => (await api.get<ApiProvider[]>("/api-providers")).data,
  });
}

function invalidate(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: apiKeysKey });
  qc.invalidateQueries({ queryKey: apiKeysExpiringKey });
}

export function useCreateApiKey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: ApiKeyPayload) => (await api.post<ApiKeyEntry>("/api-keys", payload)).data,
    onSuccess: () => invalidate(qc),
  });
}

export function useUpdateApiKey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: Partial<ApiKeyPayload> }) =>
      (await api.patch<ApiKeyEntry>(`/api-keys/${id}`, payload)).data,
    onSuccess: () => invalidate(qc),
  });
}

export function useDeleteApiKey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/api-keys/${id}`);
      return id;
    },
    onSuccess: () => invalidate(qc),
  });
}

export function useCreateApiProvider() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (name: string) => (await api.post<ApiProvider>("/api-providers", { name })).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: apiProvidersKey }),
  });
}

export function useUpdateApiProvider() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: Partial<ApiProvider> }) =>
      (await api.patch<ApiProvider>(`/api-providers/${id}`, payload)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: apiProvidersKey }),
  });
}
