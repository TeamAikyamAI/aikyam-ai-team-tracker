import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, API_BASE_URL } from "@/lib/api";
import type { LogoMeta } from "@/types";

export const logoMetaKey = ["branding", "logo"] as const;

/** Public endpoint - the login screen needs the logo before anyone signs in. */
export function useLogoMeta() {
  return useQuery({
    queryKey: logoMetaKey,
    queryFn: async () => (await api.get<LogoMeta>("/branding/logo/meta")).data,
    staleTime: 5 * 60 * 1000,
  });
}

/** Absolute URL for the stored logo, version-stamped so a new upload shows up at once. */
export function logoSrc(meta?: LogoMeta): string {
  const version = meta?.version ?? "default";
  return `${API_BASE_URL}/branding/logo?v=${encodeURIComponent(version)}`;
}

export function useUploadLogo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData();
      form.append("file", file);
      // No explicit Content-Type: the browser must set the multipart boundary itself.
      return (await api.put<LogoMeta>("/branding/logo", form)).data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: logoMetaKey }),
  });
}

export function useDeleteLogo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => (await api.delete<LogoMeta>("/branding/logo")).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: logoMetaKey }),
  });
}
