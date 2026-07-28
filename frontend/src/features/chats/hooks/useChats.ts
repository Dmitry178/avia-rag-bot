import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { chatDetailQueryKey } from "@/features/chat/hooks/useChat";
import { useChatModeStore } from "@/features/chat/modeStore";
import { useLlmSettingsStore } from "@/features/llm/llmSettingsStore";
import { DEFAULT_LLM_CREATE_PAYLOAD } from "@/features/llm/types";
import { useRagSettingsStore } from "@/features/rag/ragSettingsStore";
import { DEFAULT_RAG_CREATE_PAYLOAD } from "@/features/rag/types";
import { createChat, deleteChat, listChats, updateChat } from "@/shared/api/chats";
import type { ChatMode, ChatSummary } from "@/shared/api/types";
import { type Locale, useI18nStore } from "@/shared/i18n";
import { useChatUiStore } from "../store";

export const chatsQueryKey = (chatType: ChatMode, locale: Locale) =>
  ["chats", chatType, locale] as const;

export function useChatsQuery() {
  const chatType = useChatModeStore((state) => state.mode);
  const locale = useI18nStore((state) => state.locale);

  return useQuery({
    queryKey: chatsQueryKey(chatType, locale),
    queryFn: () => listChats(chatType, locale),
  });
}

export function useCreateChatMutation() {
  const queryClient = useQueryClient();
  const chatType = useChatModeStore((state) => state.mode);
  const locale = useI18nStore((state) => state.locale);
  const setSelectedChatId = useChatUiStore((state) => state.setSelectedChatId);

  return useMutation({
    mutationKey: ["createChat"],
    mutationFn: (title: string) => {
      if (chatType === "rag") {
        return createChat(title, chatType, locale, {
          ragConfig: DEFAULT_RAG_CREATE_PAYLOAD.rag_config,
          useHistory: DEFAULT_RAG_CREATE_PAYLOAD.use_history,
        });
      }

      return createChat(title, chatType, locale, {
        llmConfig: DEFAULT_LLM_CREATE_PAYLOAD.llm_config,
        useHistory: DEFAULT_LLM_CREATE_PAYLOAD.use_history,
      });
    },
    onSuccess: (chat) => {
      if (chatType === "llm") {
        useLlmSettingsStore.getState().hydrateFromChat(chat.llm_config, chat.use_history);
      }

      if (chatType === "rag") {
        useRagSettingsStore.getState().hydrateFromChat(chat.rag_config, chat.use_history);
      }

      setSelectedChatId(locale, chatType, chat.id);

      queryClient.setQueryData<ChatSummary[]>(chatsQueryKey(chatType, locale), (current) => {
        if (!current) {
          return [chat];
        }

        if (current.some((item) => item.id === chat.id)) {
          return current;
        }

        return [chat, ...current];
      });

      queryClient.setQueryData(chatDetailQueryKey(chat.id), {
        ...chat,
        messages: [],
      });

      void queryClient.invalidateQueries({ queryKey: chatsQueryKey(chatType, locale) });
    },
  });
}

export function useDeleteChatMutation() {
  const queryClient = useQueryClient();
  const chatType = useChatModeStore((state) => state.mode);
  const locale = useI18nStore((state) => state.locale);
  const setSelectedChatId = useChatUiStore((state) => state.setSelectedChatId);

  return useMutation({
    mutationKey: ["deleteChat"],
    mutationFn: (chatId: number) => deleteChat(chatId),
    onMutate: async (chatId) => {
      await queryClient.cancelQueries({ queryKey: chatsQueryKey(chatType, locale) });

      const previousChats = queryClient.getQueryData<ChatSummary[]>(chatsQueryKey(chatType, locale));
      const previousSelectedChatId =
        useChatUiStore.getState().selectedByLocaleAndMode[locale][chatType];

      if (previousChats) {
        if (previousSelectedChatId === chatId) {
          setSelectedChatId(locale, chatType, null);
        }

        queryClient.setQueryData<ChatSummary[]>(
          chatsQueryKey(chatType, locale),
          previousChats.filter((chat) => chat.id !== chatId),
        );
      }

      return { previousChats, previousSelectedChatId };
    },
    onError: (_error, chatId, context) => {
      if (context?.previousChats) {
        queryClient.setQueryData(chatsQueryKey(chatType, locale), context.previousChats);
      }

      if (context?.previousSelectedChatId === chatId) {
        setSelectedChatId(locale, chatType, context.previousSelectedChatId);
      }
    },
    onSuccess: (_data, chatId) => {
      queryClient.removeQueries({ queryKey: chatDetailQueryKey(chatId) });
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: chatsQueryKey(chatType, locale) });
    },
  });
}

export function useUpdateChatSettingsMutation(chatId: number | null) {
  const queryClient = useQueryClient();
  const chatType = useChatModeStore((state) => state.mode);
  const locale = useI18nStore((state) => state.locale);
  const ragToPayload = useRagSettingsStore((state) => state.toPayload);
  const llmToPayload = useLlmSettingsStore((state) => state.toPayload);

  return useMutation({
    mutationKey: ["updateChatSettings"],
    mutationFn: () => {
      if (chatId === null) {
        throw new Error("Chat is not selected");
      }

      if (chatType === "rag") {
        const payload = ragToPayload();

        return updateChat(chatId, {
          rag_config: payload.rag_config,
          use_history: payload.use_history,
        });
      }

      const payload = llmToPayload();

      return updateChat(chatId, {
        llm_config: payload.llm_config,
        use_history: payload.use_history,
      });
    },
    onSuccess: (chat) => {
      if (chatId !== null) {
        queryClient.setQueryData(chatDetailQueryKey(chatId), (current) =>
          current ? { ...current, ...chat } : current,
        );
      }

      queryClient.setQueryData<ChatSummary[]>(chatsQueryKey(chatType, locale), (current) =>
        current?.map((item) => (item.id === chat.id ? { ...item, ...chat } : item)),
      );
    },
  });
}
