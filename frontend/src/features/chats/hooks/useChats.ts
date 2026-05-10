import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useChatModeStore } from "@/features/chat/modeStore";
import { createChat, listChats } from "@/shared/api/chats";
import type { ChatMode } from "@/shared/api/types";
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
      void queryClient.invalidateQueries({ queryKey: chatsQueryKey(chatType) });
      setSelectedChatId(chatType, chat.id);
    },
  });
}
