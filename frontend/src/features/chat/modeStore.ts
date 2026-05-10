import { create } from "zustand";
import { persist } from "zustand/middleware";

import { readPersistedState } from "@/shared/persist";
import type { ChatMode } from "@/shared/api/types";

export type { ChatMode };

function readStoredChatMode(): ChatMode {
  const state = readPersistedState<{ mode?: unknown }>("avia-bot.chat-mode");

  if (state?.mode === "llm" || state?.mode === "rag") {
    return state.mode;
  }

  return "llm";
}

interface ChatModeState {
  mode: ChatMode;
  setMode: (mode: ChatMode) => void;
}

export const useChatModeStore = create<ChatModeState>()(
  persist(
    (set) => ({
      mode: readStoredChatMode(),
      setMode: (mode) => set({ mode }),
    }),
    {
      name: "avia-bot.chat-mode",
      partialize: (state) => ({ mode: state.mode }),
    },
  ),
);
