import { useEffect } from "react";

import type { ChatDetail, ChatSummary } from "@/shared/api/types";
import { useI18nStore } from "@/shared/i18n";
import { useRagSettingsStore } from "../ragSettingsStore";

export function useHydrateRagSettings(chat: ChatSummary | ChatDetail | null | undefined) {
  const locale = useI18nStore((state) => state.locale);
  const hydrateFromChat = useRagSettingsStore((state) => state.hydrateFromChat);

  useEffect(() => {
    if (!chat) {
      return;
    }

    hydrateFromChat(chat.rag_config, chat.use_history, locale);
  }, [
    chat?.id,
    chat?.rag_config?.use_hyde,
    chat?.rag_config?.use_multi_query,
    chat?.rag_config?.use_query_rewriting,
    chat?.rag_config?.use_rerank,
    chat?.rag_config?.top_chunks,
    chat?.rag_config?.runtime,
    chat?.rag_config?.mcp?.command,
    chat?.use_history,
    hydrateFromChat,
    locale,
    chat,
  ]);
}
