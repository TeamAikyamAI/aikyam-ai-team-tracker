import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { CreateProjectPayload, Project, ProjectQueueItem, UpdateProjectPayload } from "@/types";

export const projectsKey = ["projects"] as const;
export const projectQueueKey = ["projects", "queue"] as const;

export function useProjects() {
  return useQuery({
    queryKey: projectsKey,
    queryFn: async () => (await api.get<Project[]>("/projects")).data,
  });
}

export function useProjectQueue() {
  return useQuery({
    queryKey: projectQueueKey,
    queryFn: async () => (await api.get<ProjectQueueItem[]>("/projects/queue")).data,
  });
}

export function useCreateProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreateProjectPayload) => (await api.post<Project>("/projects", payload)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: projectsKey });
      qc.invalidateQueries({ queryKey: projectQueueKey });
    },
  });
}

export function useUpdateProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: UpdateProjectPayload }) =>
      (await api.patch<Project>(`/projects/${id}`, payload)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: projectsKey });
      qc.invalidateQueries({ queryKey: projectQueueKey });
    },
  });
}

export function useDeleteProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/projects/${id}`);
      return id;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: projectsKey });
      qc.invalidateQueries({ queryKey: projectQueueKey });
    },
  });
}
