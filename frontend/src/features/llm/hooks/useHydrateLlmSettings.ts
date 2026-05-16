import { useEffect } from "react";

import type { ChatDetail, ChatSummary } from "@/shared/api/types";
import { useLlmSettingsStore } from "../llmSettingsStore";

export function useHydrateLlmSettings(chat: ChatSummary | ChatDetail | null | undefined) {
  const hydrateFromChat = useLlmSettingsStore((state) => state.hydrateFromChat);

  useEffect(() => {
    if (!chat) {
      return;
    }

    hydrateFromChat(chat.llm_config, chat.use_history);
  }, [chat?.id, chat?.llm_config, chat?.use_history, hydrateFromChat, chat]);
}
