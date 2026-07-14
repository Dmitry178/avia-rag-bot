export type RagMethodKey = "hyde" | "multi_query" | "query_rewriting" | "rerank";

export type { RagConfig } from "@/shared/api/types";

export const RAG_METHOD_KEYS: RagMethodKey[] = [
  "hyde",
  "multi_query",
  "query_rewriting",
  "rerank",
];

export const RAG_BOOLEAN_CONFIG_KEYS = [
  "use_hyde",
  "use_multi_query",
  "use_query_rewriting",
  "use_rerank",
] as const;

export type RagBooleanConfigKey = (typeof RAG_BOOLEAN_CONFIG_KEYS)[number];

/** Retrieval methods where only one may be active at a time (rerank is independent). */
export const RAG_EXCLUSIVE_METHOD_KEYS = [
  "hyde",
  "multi_query",
  "query_rewriting",
] as const satisfies readonly RagMethodKey[];

export const DEFAULT_RAG_CONFIG: Required<{
  use_hyde: boolean;
  use_multi_query: boolean;
  use_query_rewriting: boolean;
  use_rerank: boolean;
  top_chunks: number;
}> = {
  use_hyde: false,
  use_multi_query: false,
  use_query_rewriting: false,
  use_rerank: false,
  top_chunks: 5,
};

export const DEFAULT_RAG_CREATE_PAYLOAD = {
  rag_config: DEFAULT_RAG_CONFIG,
  use_history: true,
} as const;

export const RAG_TOP_CHUNKS_MIN = 3;
export const RAG_TOP_CHUNKS_MAX = 9;

export const RAG_CONFIG_TO_METHOD: Record<RagMethodKey, RagBooleanConfigKey> = {
  hyde: "use_hyde",
  multi_query: "use_multi_query",
  query_rewriting: "use_query_rewriting",
  rerank: "use_rerank",
};
