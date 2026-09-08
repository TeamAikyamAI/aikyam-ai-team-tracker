import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import type { FeatureKey, MyFeatures, PermissionMatrix } from "@/types";

export const myFeaturesKey = ["permissions", "me"] as const;
export const permissionMatrixKey = ["permissions", "matrix"] as const;

/** What the signed-in person may use. Drives the sidebar and the routes. */
export function useMyFeatures() {
  const { user } = useAuth();
  return useQuery({
    queryKey: myFeaturesKey,
    enabled: !!user,
    // Access rarely changes mid-session, and every screen reads this.
    staleTime: 5 * 60 * 1000,
    queryFn: async () => (await api.get<MyFeatures>("/permissions/me")).data,
  });
}

/**
 * `can("my_day")` - false while the answer is still loading, so a screen never
 * flashes content the person turns out not to be allowed to see.
 */
export function useCan() {
  const { data } = useMyFeatures();
  return (feature: FeatureKey) => !!data?.features.includes(feature);
}

export function usePermissionMatrix() {
  return useQuery({
    queryKey: permissionMatrixKey,
    queryFn: async () => (await api.get<PermissionMatrix>("/permissions")).data,
  });
}

export function useUpdatePermissions() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (changes: Record<string, Record<string, boolean>>) =>
      (await api.put<{ changed: string[]; features: PermissionMatrix["features"] }>("/permissions", { changes })).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: permissionMatrixKey });
      qc.invalidateQueries({ queryKey: myFeaturesKey });
    },
  });
}
