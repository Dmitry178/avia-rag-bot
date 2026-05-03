import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createChat, listChats } from "@/shared/api/chats";
import { useChatUiStore } from "../store";

export const chatsQueryKey = ["chats"] as const;

export function useChatsQuery() {
  return useQuery({
    queryKey: chatsQueryKey,
    queryFn: listChats,
  });
}

export function useCreateChatMutation() {
  const queryClient = useQueryClient();
  const setSelectedChatId = useChatUiStore((state) => state.setSelectedChatId);

  return useMutation({
    mutationFn: (title: string) => createChat(title),
    onSuccess: (chat) => {
      void queryClient.invalidateQueries({ queryKey: chatsQueryKey });
      setSelectedChatId(chat.id);
    },
  });
}
