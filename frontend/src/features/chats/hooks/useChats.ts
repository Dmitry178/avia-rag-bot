import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { chatDetailQueryKey } from "@/features/chat/hooks/useChat";
import { useChatModeStore } from "@/features/chat/modeStore";
import { useRagSettingsStore } from "@/features/rag/ragSettingsStore";
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
  const toPayload = useRagSettingsStore((state) => state.toPayload);

  return useMutation({
    mutationFn: (title: string) => {
      const ragPayload = chatType === "rag" ? toPayload() : null;

      return createChat(title, chatType, {
        ragConfig: ragPayload?.rag_config,
        useHistory: ragPayload?.use_history,
      });
    },
    onSuccess: (chat) => {
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
  const toPayload = useRagSettingsStore((state) => state.toPayload);

  return useMutation({
    mutationFn: () => {
      if (chatId === null) {
        throw new Error("Chat is not selected");
      }

      const payload = toPayload();

      return updateChat(chatId, {
        rag_config: payload.rag_config,
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
