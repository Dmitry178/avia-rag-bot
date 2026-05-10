import { apiRequest } from "./client";
import type { ChatDetail, ChatMode, ChatSummary, SendMessageResponse } from "./types";

const BASE = "/api/chats";

export function listChats(chatType: ChatMode): Promise<ChatSummary[]> {
  return apiRequest<ChatSummary[]>(`${BASE}?chat_type=${chatType}`);
}

export function createChat(title: string, chatType: ChatMode): Promise<ChatSummary> {
  return apiRequest<ChatSummary>(BASE, {
    method: "POST",
    body: { title, chat_type: chatType },
  });
}

export function getChat(chatId: number): Promise<ChatDetail> {
  return apiRequest<ChatDetail>(`${BASE}/${chatId}`);
}

export function deleteChat(chatId: number): Promise<void> {
  return apiRequest<void>(`${BASE}/${chatId}`, { method: "DELETE" });
}

export function closeChat(chatId: number): Promise<ChatSummary> {
  return apiRequest<ChatSummary>(`${BASE}/${chatId}/close`, { method: "POST" });
}

export function sendMessage(
  chatId: number,
  content: string,
  clientId?: string,
): Promise<SendMessageResponse> {
  return apiRequest<SendMessageResponse>(`${BASE}/${chatId}/messages`, {
    method: "POST",
    body: {
      content,
      client_id: clientId ?? null,
    },
  });
}
