import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { chatDetailQueryKey } from "@/features/chat/hooks/useChat";
import { chatsQueryKey } from "@/features/chats/hooks/useChats";
import { useChatUiStore } from "@/features/chats/store";
import { apiUrl } from "@/shared/config/env";
import { useTranslation } from "@/shared/i18n";
import { showErrorToast } from "@/shared/toast/showToast";
import type { ChatMode, ChatSSEErrorPayload, ChatSummary } from "@/shared/api/types";

interface ChatTitleEventPayload {
  chat_id: number;
  title: string;
}

function applyChatTitle(
  queryClient: ReturnType<typeof useQueryClient>,
  chatId: number,
  title: string,
) {
  for (const chatType of ["llm", "rag"] satisfies ChatMode[]) {
    queryClient.setQueryData<ChatSummary[]>(chatsQueryKey(chatType), (current) =>
      current?.map((item) => (item.id === chatId ? { ...item, title } : item)),
    );
  }

  queryClient.setQueryData(chatDetailQueryKey(chatId), (current) =>
    current ? { ...current, title } : current,
  );
}

/**
 * Subscribes to chat SSE sideband events (title updates, errors, trace).
 */
export function useChatEvents() {
  const clientId = useChatUiStore((state) => state.clientId);
  const queryClient = useQueryClient();
  const { t } = useTranslation();

  useEffect(() => {
    const url = apiUrl(`/api/chats/events?client_id=${encodeURIComponent(clientId)}`);
    const source = new EventSource(url);

    const onChatTitle = (event: MessageEvent<string>) => {
      try {
        const payload = JSON.parse(event.data) as ChatTitleEventPayload;

        if (typeof payload.chat_id !== "number" || typeof payload.title !== "string") {
          return;
        }

        applyChatTitle(queryClient, payload.chat_id, payload.title);
      } catch {
        // Ignore malformed SSE payloads.
      }
    };

    const onError = (event: MessageEvent<string>) => {
      try {
        const payload = JSON.parse(event.data) as ChatSSEErrorPayload;

        if (typeof payload.message !== "string" || !payload.message) {
          return;
        }

        // Background sideband errors only; HTTP failures use react-query toasts.
        if (payload.error_code !== "chat_title_error") {
          return;
        }

        showErrorToast(payload.message, t("errors.chatTitleFailed"));
      } catch {
        // Ignore malformed SSE payloads.
      }
    };

    source.addEventListener("chat_title", onChatTitle);
    source.addEventListener("error", onError);

    return () => {
      source.removeEventListener("chat_title", onChatTitle);
      source.removeEventListener("error", onError);
      source.close();
    };
  }, [clientId, queryClient, t]);
}
