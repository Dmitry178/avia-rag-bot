import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { chatDetailQueryKey } from "@/features/chat/hooks/useChat";
import { useChatModeStore } from "@/features/chat/modeStore";
import { createChat, deleteChat, listChats } from "@/shared/api/chats";
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
    mutationFn: (title: string) => createChat(title, chatType),
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
