import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { PublicSettings, SettingItem } from "@/types";

export const publicSettingsKey = ["settings", "public"] as const;
export const settingsKey = ["settings", "all"] as const;

const FALLBACK: PublicSettings = {
  app_name: "Aikyam AI Team Tracker",
  org_name: "Aikyam Capital",
  login_footer: "",
  email_domain: "aikyamcapital.com",
  chatbot_enabled: false,
  chatbot_name: "Assistant",
  chatbot_greeting: "Hi! How can I help you?",
  chatbot_suggestions: "",
};

/** Public - the login screen needs these before anyone signs in. */
export function usePublicSettings() {
  const query = useQuery({
    queryKey: publicSettingsKey,
    queryFn: async () => (await api.get<PublicSettings>("/settings/public")).data,
    staleTime: 5 * 60 * 1000,
  });
  // Never render an empty shell if the API is briefly unreachable.
  return { ...query, settings: query.data ?? FALLBACK };
}

export function useAdminSettings() {
  return useQuery({
    queryKey: settingsKey,
    queryFn: async () => (await api.get<{ items: SettingItem[] }>("/settings")).data.items,
  });
}

export function useUpdateSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (values: Record<string, unknown>) =>
      (await api.patch<{ items: SettingItem[] }>("/settings", { values })).data.items,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: settingsKey });
      qc.invalidateQueries({ queryKey: publicSettingsKey });
    },
  });
}

export function useTestEmail() {
  return useMutation({
    mutationFn: async () => (await api.post<{ ok: boolean; detail: string }>("/settings/test-email")).data,
  });
}

export function useDigestPreview() {
  return useMutation({
    mutationFn: async () =>
      (await api.post<{ ok: boolean; emails_sent: number; detail: string }>("/settings/digest-preview")).data,
  });
}
