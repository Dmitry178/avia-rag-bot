import { create } from "zustand";

interface ChatUiState {
  selectedChatId: number | null;
  clientId: string;
  setSelectedChatId: (chatId: number | null) => void;
}

export const useChatUiStore = create<ChatUiState>((set) => ({
  selectedChatId: null,
  clientId:
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : `client-${Date.now()}`,
  setSelectedChatId: (chatId) => set({ selectedChatId: chatId }),
}));
