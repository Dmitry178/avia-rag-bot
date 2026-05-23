import { useEffect } from "react";

import type { ChatDetail, ChatSummary } from "@/shared/api/types";
import { useRagSettingsStore } from "../ragSettingsStore";

export function useHydrateRagSettings(chat: ChatSummary | ChatDetail | null | undefined) {
  const hydrateFromChat = useRagSettingsStore((state) => state.hydrateFromChat);

  useEffect(() => {
    if (!chat) {
      return;
    }

    hydrateFromChat(chat.rag_config, chat.use_history);
  }, [
    chat?.id,
    chat?.rag_config?.use_hyde,
    chat?.rag_config?.use_multi_query,
    chat?.rag_config?.use_query_rewriting,
    chat?.rag_config?.use_rerank,
    chat?.rag_config?.top_chunks,
    chat?.use_history,
    hydrateFromChat,
    chat,
  ]);
}
