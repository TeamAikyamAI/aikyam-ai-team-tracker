import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { CreateUserPayload, UpdateUserPayload, User, UserBrief } from "@/types";

export const usersKey = ["users"] as const;

export function useUsers() {
  return useQuery({
    queryKey: usersKey,
    queryFn: async () => (await api.get<User[]>("/users")).data,
  });
}

/**
 * Names only. The dashboard shows who owns each project to everyone, but the
 * full directory (emails, roles, reporting chain) stays with the AI team, so
 * screens that only need a name use this instead of useUsers().
 */
export function useUserDirectory() {
  return useQuery({
    queryKey: ["users", "directory"],
    staleTime: 5 * 60 * 1000,
    queryFn: async () => (await api.get<UserBrief[]>("/users/directory")).data,
  });
}

export function useCreateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreateUserPayload) => (await api.post<User>("/users", payload)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: usersKey }),
  });
}

export function useUpdateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: UpdateUserPayload }) =>
      (await api.patch<User>(`/users/${id}`, payload)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: usersKey }),
  });
}
