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
  }, [chat?.id, chat?.rag_config, chat?.use_history, hydrateFromChat, chat]);
}
