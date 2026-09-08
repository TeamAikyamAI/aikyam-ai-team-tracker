import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { CreateUpdatePayload, ProjectUpdate, QuickFillPayload, QuickFillResult } from "@/types";
import { projectsKey } from "@/hooks/useProjects";

export function projectUpdatesKey(projectId: number | undefined) {
  return ["updates", "project", projectId] as const;
}

export function useProjectUpdates(projectId: number | undefined) {
  return useQuery({
    queryKey: projectUpdatesKey(projectId),
    queryFn: async () => (await api.get<ProjectUpdate[]>(`/updates/project/${projectId}`)).data,
    enabled: typeof projectId === "number" && Number.isFinite(projectId),
  });
}

export function useCreateUpdate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreateUpdatePayload) => (await api.post<ProjectUpdate>("/updates", payload)).data,
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: projectUpdatesKey(data.project_id) });
      qc.invalidateQueries({ queryKey: projectsKey });
    },
  });
}

export function useQuickFill() {
  return useMutation({
    mutationFn: async (payload: QuickFillPayload) =>
      (await api.post<QuickFillResult>("/updates/quick-fill", payload)).data,
  });
}
