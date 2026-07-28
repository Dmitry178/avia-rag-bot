import { create } from "zustand";
import { persist } from "zustand/middleware";

import { type ChatMode, useChatModeStore } from "@/features/chat/modeStore";
import { type Locale } from "@/shared/i18n";
import { useI18nStore } from "@/shared/i18n/store";
import { readPersistedState } from "@/shared/persist";

type SelectedByLocaleAndMode = Record<Locale, Record<ChatMode, number | null>>;

const EMPTY_SELECTIONS: SelectedByLocaleAndMode = {
  ru: { llm: null, rag: null },
  en: { llm: null, rag: null },
};

function readStoredSelections(): SelectedByLocaleAndMode {
  const state = readPersistedState<{
    selectedByLocaleAndMode?: unknown;
    selectedByMode?: unknown;
  }>("avia-bot.selected-chats");

  const nested = state?.selectedByLocaleAndMode;
  if (nested && typeof nested === "object") {
    const record = nested as Record<string, unknown>;

    return {
      ru: {
        llm: typeof record.ru === "object" && record.ru && typeof (record.ru as Record<string, unknown>).llm === "number"
          ? ((record.ru as Record<string, unknown>).llm as number)
          : null,
        rag: typeof record.ru === "object" && record.ru && typeof (record.ru as Record<string, unknown>).rag === "number"
          ? ((record.ru as Record<string, unknown>).rag as number)
          : null,
      },
      en: {
        llm: typeof record.en === "object" && record.en && typeof (record.en as Record<string, unknown>).llm === "number"
          ? ((record.en as Record<string, unknown>).llm as number)
          : null,
        rag: typeof record.en === "object" && record.en && typeof (record.en as Record<string, unknown>).rag === "number"
          ? ((record.en as Record<string, unknown>).rag as number)
          : null,
      },
    };
  }

  const legacy = state?.selectedByMode;
  if (legacy && typeof legacy === "object") {
    const record = legacy as Record<string, unknown>;

    return {
      ru: {
        llm: typeof record.llm === "number" ? record.llm : null,
        rag: typeof record.rag === "number" ? record.rag : null,
      },
      en: { llm: null, rag: null },
    };
  }

  return { ...EMPTY_SELECTIONS };
}

interface ChatUiState {
  selectedByLocaleAndMode: SelectedByLocaleAndMode;
  clientId: string;
  composerFocusNonce: number;
  setSelectedChatId: (locale: Locale, mode: ChatMode, chatId: number | null) => void;
  requestComposerFocus: () => void;
}

export const useChatUiStore = create<ChatUiState>()(
  persist(
    (set) => ({
      selectedByLocaleAndMode: readStoredSelections(),
      clientId:
        typeof crypto !== "undefined" && "randomUUID" in crypto
          ? crypto.randomUUID()
          : `client-${Date.now()}`,
      composerFocusNonce: 0,
      setSelectedChatId: (locale, mode, chatId) =>
        set((state) => ({
          selectedByLocaleAndMode: {
            ...state.selectedByLocaleAndMode,
            [locale]: { ...state.selectedByLocaleAndMode[locale], [mode]: chatId },
          },
        })),
      requestComposerFocus: () =>
        set((state) => ({ composerFocusNonce: state.composerFocusNonce + 1 })),
    }),
    {
      name: "avia-bot.selected-chats",
      partialize: (state) => ({ selectedByLocaleAndMode: state.selectedByLocaleAndMode }),
    },
  ),
);

export function useSelectedChatId(): [number | null, (chatId: number | null) => void] {
  const mode = useChatModeStore((state) => state.mode);
  const locale = useI18nStore((state) => state.locale);
  const selectedChatId = useChatUiStore((state) => state.selectedByLocaleAndMode[locale][mode]);
  const setSelectedChatId = useChatUiStore((state) => state.setSelectedChatId);

  return [selectedChatId, (chatId) => setSelectedChatId(locale, mode, chatId)];
}
