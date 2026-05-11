export type RagMethodKey = "hyde" | "multi_query" | "query_rewriting" | "rerank";

export type { RagConfig } from "@/shared/api/types";

export const RAG_METHOD_KEYS: RagMethodKey[] = [
  "hyde",
  "multi_query",
  "query_rewriting",
  "rerank",
];

export const DEFAULT_RAG_CONFIG: Required<{
  use_hyde: boolean;
  use_multi_query: boolean;
  use_query_rewriting: boolean;
  use_rerank: boolean;
}> = {
  use_hyde: false,
  use_multi_query: false,
  use_query_rewriting: false,
  use_rerank: true,
};

export const RAG_CONFIG_TO_METHOD: Record<
  RagMethodKey,
  keyof Required<typeof DEFAULT_RAG_CONFIG>
> = {
  hyde: "use_hyde",
  multi_query: "use_multi_query",
  query_rewriting: "use_query_rewriting",
  rerank: "use_rerank",
};
