import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { AskPayload, AskResult } from "@/types";

export function useAskTracker() {
  return useMutation({
    mutationFn: async (payload: AskPayload) => (await api.post<AskResult>("/ai/ask", payload)).data,
  });
}
