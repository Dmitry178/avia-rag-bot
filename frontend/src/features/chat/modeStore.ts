import { create } from "zustand";
import { persist } from "zustand/middleware";

export type ChatMode = "rag" | "llm";

interface ChatModeState {
  mode: ChatMode;
  setMode: (mode: ChatMode) => void;
}

export const useChatModeStore = create<ChatModeState>()(
  persist(
    (set) => ({
      mode: "llm",
      setMode: (mode) => set({ mode }),
    }),
    {
      name: "avia-bot.chat-mode",
      partialize: (state) => ({ mode: state.mode }),
    },
  ),
);
