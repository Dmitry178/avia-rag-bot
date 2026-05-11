import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useChatModeStore } from "@/features/chat/modeStore";
import { useRagSettingsStore } from "@/features/rag/ragSettingsStore";
import { getChat, deleteMessage, sendMessage } from "@/shared/api/chats";
import type { SendMessagePayload } from "@/shared/api/types";
import { useChatUiStore } from "@/features/chats/store";

export function chatDetailQueryKey(chatId: number) {
  return ["chat", chatId] as const;
}

export function useChatDetailQuery(chatId: number | null) {
  return useQuery({
    queryKey: chatId ? chatDetailQueryKey(chatId) : ["chat", "empty"],
    queryFn: () => getChat(chatId as number),
    enabled: chatId !== null,
  });
}

export function useSendMessageMutation(chatId: number | null) {
  const queryClient = useQueryClient();
  const clientId = useChatUiStore((state) => state.clientId);
  const chatMode = useChatModeStore((state) => state.mode);
  const toPayload = useRagSettingsStore((state) => state.toPayload);

  return useMutation({
    mutationFn: (payload: SendMessagePayload) => {
      if (chatId === null) {
        throw new Error("Chat is not selected");
      }

      const ragPayload = chatMode === "rag" ? toPayload() : null;

      return sendMessage(chatId, payload.content, {
        clientId,
        ragConfig: chatMode === "rag" ? payload.rag_config ?? ragPayload?.rag_config : undefined,
        useHistory: chatMode === "rag" ? payload.use_history ?? ragPayload?.use_history : undefined,
      });
    },
    onSuccess: () => {
      if (chatId !== null) {
        void queryClient.invalidateQueries({ queryKey: chatDetailQueryKey(chatId) });
      }

      void queryClient.invalidateQueries({ queryKey: ["chats"] });
    },
  });
}

export function useDeleteMessageMutation(chatId: number | null) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (messageId: number) => {
      if (chatId === null) {
        throw new Error("Chat is not selected");
      }

      return deleteMessage(chatId, messageId);
    },
    onSuccess: () => {
      if (chatId !== null) {
        void queryClient.invalidateQueries({ queryKey: chatDetailQueryKey(chatId) });
      }

      void queryClient.invalidateQueries({ queryKey: ["chats"] });
    },
  });
}
