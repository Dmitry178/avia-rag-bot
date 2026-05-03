import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { getChat, sendMessage } from "@/shared/api/chats";
import { chatsQueryKey } from "@/features/chats/hooks/useChats";
import { useChatUiStore } from "@/features/chats/store";

export function chatDetailQueryKey(chatId: number) {
  return ["chat", chatId] as const;
}

export function useChatDetailQuery(chatId: number | null) {
  return useQuery({
    queryKey: chatId ? chatDetailQueryKey(chatId) : ["chat", "empty"],
    queryFn: () => getChat(chatId as number),
    enabled: chatId !== null,
  });
}

export function useSendMessageMutation(chatId: number | null) {
  const queryClient = useQueryClient();
  const clientId = useChatUiStore((state) => state.clientId);

  return useMutation({
    mutationFn: (content: string) => {
      if (chatId === null) {
        throw new Error("Chat is not selected");
      }

      return sendMessage(chatId, content, clientId);
    },
    onSuccess: () => {
      if (chatId !== null) {
        void queryClient.invalidateQueries({ queryKey: chatDetailQueryKey(chatId) });
      }

      void queryClient.invalidateQueries({ queryKey: chatsQueryKey });
    },
  });
}
