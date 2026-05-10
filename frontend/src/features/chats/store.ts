import { create } from "zustand";

interface ChatUiState {
  selectedChatId: number | null;
  clientId: string;
  composerFocusNonce: number;
  setSelectedChatId: (chatId: number | null) => void;
  requestComposerFocus: () => void;
}

export const useChatUiStore = create<ChatUiState>((set) => ({
  selectedChatId: null,
  clientId:
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : `client-${Date.now()}`,
  composerFocusNonce: 0,
  setSelectedChatId: (chatId) => set({ selectedChatId: chatId }),
  requestComposerFocus: () =>
    set((state) => ({ composerFocusNonce: state.composerFocusNonce + 1 })),
}));
