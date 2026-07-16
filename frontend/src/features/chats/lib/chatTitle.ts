import type { QueryClient } from "@tanstack/react-query";

import { chatDetailQueryKey } from "@/features/chat/hooks/useChat";
import { chatsQueryKey } from "@/features/chats/hooks/useChats";
import type { ChatMode, ChatSummary } from "@/shared/api/types";

/** Matches backend `DEFAULT_CHAT_TITLES` in `app/core/chat_constants.py`. */
const DEFAULT_CHAT_TITLES = new Set(["New chat", "Новый чат"]);

/** Background title generation delay (2s) plus LLM latency. */
const TITLE_REFRESH_FALLBACK_MS = 5_000;

export function isDefaultChatTitle(title: string): boolean {
  return DEFAULT_CHAT_TITLES.has(title.trim());
}

export function applyChatTitle(
  queryClient: QueryClient,
  chatId: number,
  title: string,
): void {
  let updated = false;

  for (const chatType of ["llm", "rag"] satisfies ChatMode[]) {
    queryClient.setQueryData<ChatSummary[]>(chatsQueryKey(chatType), (current) => {
      if (!current?.some((item) => item.id === chatId)) {
        return current;
      }

      updated = true;

      return current.map((item) => (item.id === chatId ? { ...item, title } : item));
    });
  }

  queryClient.setQueryData(chatDetailQueryKey(chatId), (current) =>
    current ? { ...current, title } : current,
  );

  if (!updated) {
    void queryClient.invalidateQueries({ queryKey: ["chats"] });
    void queryClient.invalidateQueries({ queryKey: chatDetailQueryKey(chatId) });
  }
}

export function scheduleTitleRefreshFallback(
  queryClient: QueryClient,
  chatId: number,
  chatMode: ChatMode,
): void {
  window.setTimeout(() => {
    const chats = queryClient.getQueryData<ChatSummary[]>(chatsQueryKey(chatMode));
    const summary = chats?.find((item) => item.id === chatId);

    if (!summary || !isDefaultChatTitle(summary.title)) {
      return;
    }

    void queryClient.invalidateQueries({ queryKey: ["chats"] });
    void queryClient.invalidateQueries({ queryKey: chatDetailQueryKey(chatId) });
  }, TITLE_REFRESH_FALLBACK_MS);
}
