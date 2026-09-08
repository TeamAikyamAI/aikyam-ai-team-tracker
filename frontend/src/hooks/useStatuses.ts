import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { CreateStatusPayload, Status, UpdateStatusPayload } from "@/types";

export const statusesKey = ["statuses"] as const;

export function useStatuses() {
  return useQuery({
    queryKey: statusesKey,
    queryFn: async () => (await api.get<Status[]>("/statuses")).data,
  });
}

export function useCreateStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreateStatusPayload) => (await api.post<Status>("/statuses", payload)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: statusesKey }),
  });
}

export function useUpdateStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: UpdateStatusPayload }) =>
      (await api.patch<Status>(`/statuses/${id}`, payload)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: statusesKey }),
  });
}
