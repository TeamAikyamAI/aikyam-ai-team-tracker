import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { ChatAskResponse, ChatConversation, ChatMessage } from "@/types";

export function useAskAssistant() {
  return useMutation({
    mutationFn: async ({ question, sessionId }: { question: string; sessionId: string | null }) =>
      (await api.post<ChatAskResponse>("/chatbot/ask", {
        question,
        session_id: sessionId,
      })).data,
  });
}

export async function fetchChatHistory(sessionId: string): Promise<ChatMessage[]> {
  return (await api.get<ChatMessage[]>("/chatbot/history", { params: { session_id: sessionId } })).data;
}

export const chatConversationsKey = ["chatbot", "conversations"] as const;

export function useChatConversations() {
  return useQuery({
    queryKey: chatConversationsKey,
    queryFn: async () => (await api.get<ChatConversation[]>("/chatbot/conversations")).data,
  });
}

export function useChatConversation(sessionId: string | null) {
  return useQuery({
    queryKey: ["chatbot", "conversation", sessionId],
    queryFn: async () =>
      (await api.get<ChatMessage[]>(`/chatbot/conversations/${sessionId}`)).data,
    enabled: Boolean(sessionId),
  });
}
