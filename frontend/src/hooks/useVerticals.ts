import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { CreateVerticalPayload, UpdateVerticalPayload, Vertical } from "@/types";

export const verticalsKey = ["verticals"] as const;

export function useVerticals() {
  return useQuery({
    queryKey: verticalsKey,
    queryFn: async () => (await api.get<Vertical[]>("/verticals")).data,
  });
}

export function useCreateVertical() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreateVerticalPayload) =>
      (await api.post<Vertical>("/verticals", payload)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: verticalsKey }),
  });
}

export function useUpdateVertical() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: UpdateVerticalPayload }) =>
      (await api.patch<Vertical>(`/verticals/${id}`, payload)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: verticalsKey }),
  });
}
