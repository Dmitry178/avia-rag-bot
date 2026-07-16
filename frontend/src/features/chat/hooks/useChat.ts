import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useChatModeStore } from "@/features/chat/modeStore";
import { useLlmSettingsStore } from "@/features/llm/llmSettingsStore";
import { useRagSettingsStore } from "@/features/rag/ragSettingsStore";
import {
  isDefaultChatTitle,
  scheduleTitleRefreshFallback,
} from "@/features/chats/lib/chatTitle";
import { chatsQueryKey } from "@/features/chats/hooks/useChats";
import { getChat, deleteMessage, sendMessage } from "@/shared/api/chats";
import { findSendMessageResponse, isNetworkError } from "@/shared/api/networkError";
import type { ChatSummary, SendMessagePayload, SendMessageResponse } from "@/shared/api/types";
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
  const ragToPayload = useRagSettingsStore((state) => state.toPayload);
  const llmToPayload = useLlmSettingsStore((state) => state.toPayload);

  return useMutation({
    mutationKey: ["sendMessage"],
    retry: false,
    mutationFn: async (payload: SendMessagePayload): Promise<SendMessageResponse> => {
      if (chatId === null) {
        throw new Error("Chat is not selected");
      }

      const ragPayload = chatMode === "rag" ? ragToPayload() : null;
      const llmPayload = chatMode === "llm" ? llmToPayload() : null;

      try {
        return await sendMessage(chatId, payload.content, {
          clientId,
          clientMessageId: payload.client_message_id,
          ragConfig: chatMode === "rag" ? payload.rag_config ?? ragPayload?.rag_config : undefined,
          llmConfig: chatMode === "llm" ? payload.llm_config ?? llmPayload?.llm_config : undefined,
          useHistory:
            payload.use_history ??
            (chatMode === "rag" ? ragPayload?.use_history : llmPayload?.use_history),
        });
      } catch (error) {
        if (payload.client_message_id && isNetworkError(error)) {
          const chat = await getChat(chatId);
          const recovered = findSendMessageResponse(chat, payload.client_message_id);

          if (recovered) {
            return recovered;
          }
        }

        throw error;
      }
    },
    onMutate: () => {
      if (chatId === null) {
        return { needsTitleRefresh: false };
      }

      const chats = queryClient.getQueryData<ChatSummary[]>(chatsQueryKey(chatMode));
      const summary = chats?.find((item) => item.id === chatId);

      return {
        needsTitleRefresh:
          summary !== undefined &&
          isDefaultChatTitle(summary.title) &&
          summary.message_count === 0,
      };
    },
    onSuccess: (_data, _variables, context) => {
      if (chatId !== null) {
        void queryClient.invalidateQueries({ queryKey: chatDetailQueryKey(chatId) });
      }

      void queryClient.invalidateQueries({ queryKey: ["chats"] });

      if (context?.needsTitleRefresh && chatId !== null) {
        scheduleTitleRefreshFallback(queryClient, chatId, chatMode);
      }
    },
  });
}

export function useDeleteMessageMutation(chatId: number | null) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationKey: ["deleteMessage"],
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
