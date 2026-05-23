import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { chatDetailQueryKey } from "@/features/chat/hooks/useChat";
import { useChatModeStore } from "@/features/chat/modeStore";
import { useLlmSettingsStore } from "@/features/llm/llmSettingsStore";
import { DEFAULT_LLM_CREATE_PAYLOAD } from "@/features/llm/types";
import { useRagSettingsStore } from "@/features/rag/ragSettingsStore";
import { DEFAULT_RAG_CREATE_PAYLOAD } from "@/features/rag/types";
import { createChat, deleteChat, listChats, updateChat } from "@/shared/api/chats";
import type { ChatMode, ChatSummary } from "@/shared/api/types";
import { useChatUiStore } from "../store";

export const chatsQueryKey = (chatType: ChatMode) => ["chats", chatType] as const;

export function useChatsQuery() {
  const chatType = useChatModeStore((state) => state.mode);

  return useQuery({
    queryKey: chatsQueryKey(chatType),
    queryFn: () => listChats(chatType),
  });
}

export function useCreateChatMutation() {
  const queryClient = useQueryClient();
  const chatType = useChatModeStore((state) => state.mode);
  const setSelectedChatId = useChatUiStore((state) => state.setSelectedChatId);

  return useMutation({
    mutationFn: (title: string) => {
      if (chatType === "rag") {
        return createChat(title, chatType, {
          ragConfig: DEFAULT_RAG_CREATE_PAYLOAD.rag_config,
          useHistory: DEFAULT_RAG_CREATE_PAYLOAD.use_history,
        });
      }

      return createChat(title, chatType, {
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

      setSelectedChatId(chatType, chat.id);

      queryClient.setQueryData<ChatSummary[]>(chatsQueryKey(chatType), (current) => {
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

      void queryClient.invalidateQueries({ queryKey: chatsQueryKey(chatType) });
    },
  });
}

function pickNextChatId(chats: ChatSummary[], deletedChatId: number): number | null {
  const index = chats.findIndex((chat) => chat.id === deletedChatId);

  if (index === -1) {
    return null;
  }

  if (index > 0) {
    return chats[index - 1].id;
  }

  if (chats.length > 1) {
    return chats[index + 1].id;
  }

  return null;
}

export function useDeleteChatMutation() {
  const queryClient = useQueryClient();
  const chatType = useChatModeStore((state) => state.mode);
  const setSelectedChatId = useChatUiStore((state) => state.setSelectedChatId);

  return useMutation({
    mutationFn: (chatId: number) => deleteChat(chatId),
    onMutate: async (chatId) => {
      await queryClient.cancelQueries({ queryKey: chatsQueryKey(chatType) });

      const previousChats = queryClient.getQueryData<ChatSummary[]>(chatsQueryKey(chatType));
      const previousSelectedChatId = useChatUiStore.getState().selectedByMode[chatType];

      if (previousChats) {
        if (previousSelectedChatId === chatId) {
          setSelectedChatId(chatType, pickNextChatId(previousChats, chatId));
        }

        queryClient.setQueryData<ChatSummary[]>(
          chatsQueryKey(chatType),
          previousChats.filter((chat) => chat.id !== chatId),
        );
      }

      return { previousChats, previousSelectedChatId };
    },
    onError: (_error, chatId, context) => {
      if (context?.previousChats) {
        queryClient.setQueryData(chatsQueryKey(chatType), context.previousChats);
      }

      if (context?.previousSelectedChatId === chatId) {
        setSelectedChatId(chatType, context.previousSelectedChatId);
      }
    },
    onSuccess: (_data, chatId) => {
      queryClient.removeQueries({ queryKey: chatDetailQueryKey(chatId) });
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: chatsQueryKey(chatType) });
    },
  });
}

export function useUpdateChatSettingsMutation(chatId: number | null) {
  const queryClient = useQueryClient();
  const chatType = useChatModeStore((state) => state.mode);
  const ragToPayload = useRagSettingsStore((state) => state.toPayload);
  const llmToPayload = useLlmSettingsStore((state) => state.toPayload);

  return useMutation({
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

      queryClient.setQueryData<ChatSummary[]>(chatsQueryKey(chatType), (current) =>
        current?.map((item) => (item.id === chat.id ? { ...item, ...chat } : item)),
      );
    },
  });
}
