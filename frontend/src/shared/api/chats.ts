import { apiRequest } from "./client";
import type {
  ChatDetail,
  ChatMode,
  ChatSummary,
  RagConfig,
  SendMessageResponse,
  UpdateChatPayload,
} from "./types";

const BASE = "/api/chats";

export function listChats(chatType: ChatMode): Promise<ChatSummary[]> {
  return apiRequest<ChatSummary[]>(`${BASE}?chat_type=${chatType}`);
}

export function createChat(
  title: string,
  chatType: ChatMode,
  options?: { ragConfig?: RagConfig | null; useHistory?: boolean | null },
): Promise<ChatSummary> {
  const body: Record<string, unknown> = { title, chat_type: chatType };

  if (options?.ragConfig) {
    body.rag_config = options.ragConfig;
  }

  if (options?.useHistory !== undefined) {
    body.use_history = options.useHistory;
  }

  return apiRequest<ChatSummary>(BASE, {
    method: "POST",
    body,
  });
}

export function getChat(chatId: number): Promise<ChatDetail> {
  return apiRequest<ChatDetail>(`${BASE}/${chatId}`);
}

export function updateChat(chatId: number, payload: UpdateChatPayload): Promise<ChatSummary> {
  return apiRequest<ChatSummary>(`${BASE}/${chatId}`, {
    method: "PATCH",
    body: payload,
  });
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
  options?: {
    clientId?: string;
    ragConfig?: RagConfig;
    useHistory?: boolean | null;
  },
): Promise<SendMessageResponse> {
  const body: Record<string, unknown> = {
    content,
    client_id: options?.clientId ?? null,
  };

  if (options?.ragConfig) {
    body.rag_config = options.ragConfig;
  }

  if (options?.useHistory !== undefined) {
    body.use_history = options.useHistory;
  }

  return apiRequest<SendMessageResponse>(`${BASE}/${chatId}/messages`, {
    method: "POST",
    body,
  });
}

export function deleteMessage(chatId: number, messageId: number): Promise<void> {
  return apiRequest<void>(`${BASE}/${chatId}/messages/${messageId}`, { method: "DELETE" });
}
