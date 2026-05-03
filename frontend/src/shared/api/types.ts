export type MessageRole = "user" | "assistant" | "system";

export interface ChatSummary {
  id: number;
  title: string;
  is_closed: boolean;
  created_at: string;
  updated_at: string;
  closed_at: string | null;
}

export interface ChatMessage {
  id: number;
  chat_id: number;
  role: MessageRole;
  content: string;
  rating: number | null;
  rating_comment: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface ChatDetail extends ChatSummary {
  messages: ChatMessage[];
}

export interface SendMessageResponse {
  user_message: ChatMessage;
  assistant_message: ChatMessage;
}

export interface ChatSSEErrorPayload {
  message: string;
  chat_id?: number | null;
  error_code?: string | null;
}

export interface TraceEvent {
  step: string;
  timestamp: string;
  duration_ms: number;
  data: Record<string, unknown>;
}
