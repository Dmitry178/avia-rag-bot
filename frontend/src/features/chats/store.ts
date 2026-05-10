import { create } from "zustand";
import { persist } from "zustand/middleware";

import { type ChatMode, useChatModeStore } from "@/features/chat/modeStore";
import { readPersistedState } from "@/shared/persist";

type SelectedByMode = Record<ChatMode, number | null>;

const EMPTY_SELECTIONS: SelectedByMode = { llm: null, rag: null };

function readStoredSelections(): SelectedByMode {
  const state = readPersistedState<{ selectedByMode?: unknown }>("avia-bot.selected-chats");
  const stored = state?.selectedByMode;

  if (!stored || typeof stored !== "object") {
    return { ...EMPTY_SELECTIONS };
  }

  const record = stored as Record<string, unknown>;

  return {
    llm: typeof record.llm === "number" ? record.llm : null,
    rag: typeof record.rag === "number" ? record.rag : null,
  };
}

interface ChatUiState {
  selectedByMode: SelectedByMode;
  clientId: string;
  composerFocusNonce: number;
  setSelectedChatId: (mode: ChatMode, chatId: number | null) => void;
  requestComposerFocus: () => void;
}

export const useChatUiStore = create<ChatUiState>()(
  persist(
    (set) => ({
      selectedByMode: readStoredSelections(),
      clientId:
        typeof crypto !== "undefined" && "randomUUID" in crypto
          ? crypto.randomUUID()
          : `client-${Date.now()}`,
      composerFocusNonce: 0,
      setSelectedChatId: (mode, chatId) =>
        set((state) => ({
          selectedByMode: { ...state.selectedByMode, [mode]: chatId },
        })),
      requestComposerFocus: () =>
        set((state) => ({ composerFocusNonce: state.composerFocusNonce + 1 })),
    }),
    {
      name: "avia-bot.selected-chats",
      partialize: (state) => ({ selectedByMode: state.selectedByMode }),
    },
  ),
);

export function useSelectedChatId(): [number | null, (chatId: number | null) => void] {
  const mode = useChatModeStore((state) => state.mode);
  const selectedChatId = useChatUiStore((state) => state.selectedByMode[mode]);
  const setSelectedChatId = useChatUiStore((state) => state.setSelectedChatId);

  return [selectedChatId, (chatId) => setSelectedChatId(mode, chatId)];
}
