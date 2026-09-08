import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { ReviewRequestPayload, ServiceRequest } from "@/types";
import { projectsKey, projectQueueKey } from "@/hooks/useProjects";

export const requestsKey = ["requests"] as const;

export function useRequests() {
  return useQuery({
    queryKey: requestsKey,
    queryFn: async () => (await api.get<ServiceRequest[]>("/requests")).data,
  });
}

export function useCreateRequest() {
  const qc = useQueryClient();
  return useMutation({
    // Do not set a Content-Type header manually: the browser must generate
    // the multipart boundary itself when sending a FormData body. Overriding
    // it here would strip the boundary and the backend's multipart parser
    // would fail to read the file.
    mutationFn: async (form: FormData) => (await api.post<ServiceRequest>("/requests", form)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: requestsKey }),
  });
}

export function useReviewRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: ReviewRequestPayload }) =>
      (await api.post<ServiceRequest>(`/requests/${id}/review`, payload)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: requestsKey });
      qc.invalidateQueries({ queryKey: projectsKey });
      qc.invalidateQueries({ queryKey: projectQueueKey });
    },
  });
}
