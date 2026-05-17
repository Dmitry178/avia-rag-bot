import { create } from "zustand";

import {
  DEFAULT_RAG_CONFIG,
  RAG_CONFIG_TO_METHOD,
  RAG_EXCLUSIVE_METHOD_KEYS,
  type RagConfig,
  type RagMethodKey,
} from "./types";

interface RagSettingsState extends RagConfig {
  use_history: boolean | null;
  setMethodEnabled: (method: RagMethodKey, enabled: boolean) => void;
  setUseHistory: (enabled: boolean) => void;
  hydrateFromChat: (ragConfig: RagConfig | null | undefined, useHistory: boolean | null | undefined) => void;
  toConfig: () => RagConfig;
  toPayload: () => { rag_config: RagConfig; use_history: boolean | null };
}

function exclusiveRetrievalMethods(activeMethod: RagMethodKey | null): Pick<
  RagConfig,
  "use_hyde" | "use_multi_query" | "use_query_rewriting"
> {
  return {
    use_hyde: activeMethod === "hyde",
    use_multi_query: activeMethod === "multi_query",
    use_query_rewriting: activeMethod === "query_rewriting",
  };
}

function activeExclusiveMethod(config: RagConfig): (typeof RAG_EXCLUSIVE_METHOD_KEYS)[number] | null {
  for (const method of RAG_EXCLUSIVE_METHOD_KEYS) {
    if (config[RAG_CONFIG_TO_METHOD[method]]) {
      return method;
    }
  }

  return null;
}

function mergeRagConfig(ragConfig: RagConfig | null | undefined): RagConfig {
  const merged = {
    use_hyde: ragConfig?.use_hyde ?? DEFAULT_RAG_CONFIG.use_hyde,
    use_multi_query: ragConfig?.use_multi_query ?? DEFAULT_RAG_CONFIG.use_multi_query,
    use_query_rewriting: ragConfig?.use_query_rewriting ?? DEFAULT_RAG_CONFIG.use_query_rewriting,
    use_rerank: ragConfig?.use_rerank ?? DEFAULT_RAG_CONFIG.use_rerank,
  };

  return {
    ...exclusiveRetrievalMethods(activeExclusiveMethod(merged)),
    use_rerank: merged.use_rerank,
  };
}

export const useRagSettingsStore = create<RagSettingsState>((set, get) => ({
  ...DEFAULT_RAG_CONFIG,
  use_history: true,
  setMethodEnabled: (method, enabled) => {
    if (method === "rerank") {
      set({ use_rerank: enabled });
      return;
    }

    if (enabled) {
      set({
        ...exclusiveRetrievalMethods(method),
        use_rerank: get().use_rerank,
      });
      return;
    }

    set({ [RAG_CONFIG_TO_METHOD[method]]: false });
  },
  setUseHistory: (enabled) => set({ use_history: enabled }),
  hydrateFromChat: (ragConfig, useHistory) =>
    set({
      ...mergeRagConfig(ragConfig),
      use_history: useHistory ?? true,
    }),
  toConfig: () => {
    const { use_hyde, use_multi_query, use_query_rewriting, use_rerank } = get();

    return {
      use_hyde,
      use_multi_query,
      use_query_rewriting,
      use_rerank,
    };
  },
  toPayload: () => {
    const { use_history } = get();

    return {
      rag_config: get().toConfig(),
      use_history,
    };
  },
}));
