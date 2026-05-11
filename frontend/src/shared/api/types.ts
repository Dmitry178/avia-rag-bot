export type MessageRole = "user" | "assistant" | "system";

export type ChatMode = "rag" | "llm";

export interface RagConfig {
  use_hyde?: boolean | null;
  use_multi_query?: boolean | null;
  use_query_rewriting?: boolean | null;
  use_rerank?: boolean | null;
}

export interface ChatSummary {
  id: number;
  title: string;
  chat_type: ChatMode;
  is_closed: boolean;
  message_count: number;
  rag_config: RagConfig | null;
  use_history: boolean | null;
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

export interface SendMessagePayload {
  content: string;
  rag_config?: RagConfig;
  use_history?: boolean | null;
}

export interface UpdateChatPayload {
  rag_config?: RagConfig;
  use_history?: boolean | null;
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
