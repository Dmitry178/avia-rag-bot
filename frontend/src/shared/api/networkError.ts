import { ApiError } from "./client";
import type { ChatDetail, SendMessageResponse } from "./types";

export function isNetworkError(error: unknown): boolean {
  if (error instanceof ApiError) {
    return false;
  }

  if (!(error instanceof Error)) {
    return false;
  }

  const message = error.message.toLowerCase();

  return (
    message.includes("failed to fetch") ||
    message.includes("networkerror") ||
    message.includes("connection reset") ||
    message.includes("network request failed") ||
    message.includes("load failed")
  );
}

export function findSendMessageResponse(
  chat: ChatDetail,
  clientMessageId: string,
): SendMessageResponse | null {
  for (let index = 0; index < chat.messages.length; index += 1) {
    const message = chat.messages[index];

    if (
      message.role !== "user" ||
      message.metadata.client_message_id !== clientMessageId
    ) {
      continue;
    }

    const assistantMessage = chat.messages[index + 1];

    if (!assistantMessage || assistantMessage.role !== "assistant") {
      return null;
    }

    return {
      user_message: message,
      assistant_message: assistantMessage,
    };
  }

  return null;
}
