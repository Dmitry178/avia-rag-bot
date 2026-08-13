import { create } from "zustand";

import type { McpConnectionConfig, RagConfig, RagRuntime } from "@/shared/api/types";
import type { Locale } from "@/shared/i18n";
import {
  DEFAULT_RAG_CONFIG,
  RAG_CONFIG_TO_METHOD,
  RAG_EXCLUSIVE_METHOD_KEYS,
  RAG_TOP_CHUNKS_MAX,
  RAG_TOP_CHUNKS_MIN,
  type RagMethodKey,
} from "./types";
import {
  applyMcpLanguage,
  buildDefaultMcpConnection,
  formatMcpConfigText,
  parseMcpConfigText,
} from "./mcpConfig";

interface RagSettingsState extends RagConfig {
  use_history: boolean | null;
  runtime: RagRuntime;
  mcpConfigText: string;
  mcpConfigError: boolean;
  mcpLocale: Locale;
  setMethodEnabled: (method: RagMethodKey, enabled: boolean) => void;
  setTopChunks: (value: number) => void;
  setUseHistory: (enabled: boolean) => void;
  setRuntime: (runtime: RagRuntime, locale?: Locale) => void;
  setMcpConfigText: (text: string) => void;
  validateMcpConfigText: () => boolean;
  resetMcpConfigText: (locale?: Locale) => void;
  syncMcpLanguage: (locale: Locale) => boolean;
  hydrateFromChat: (
    ragConfig: RagConfig | null | undefined,
    useHistory: boolean | null | undefined,
    locale: Locale,
  ) => void;
  toConfig: () => RagConfig;
  toPayload: () => { rag_config: RagConfig; use_history: boolean | null };
}

function clampTopChunks(value: number): number {
  return Math.min(RAG_TOP_CHUNKS_MAX, Math.max(RAG_TOP_CHUNKS_MIN, Math.round(value)));
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

function resolveMcpConfigText(
  ragConfig: RagConfig | null | undefined,
  locale: Locale,
): Pick<RagSettingsState, "mcpConfigText" | "mcpConfigError" | "mcpLocale"> {
  if (ragConfig?.mcp) {
    return {
      mcpConfigText: formatMcpConfigText(applyMcpLanguage(ragConfig.mcp, locale), locale),
      mcpConfigError: false,
      mcpLocale: locale,
    };
  }

  return {
    mcpConfigText: formatMcpConfigText(buildDefaultMcpConnection(locale), locale),
    mcpConfigError: false,
    mcpLocale: locale,
  };
}

function mergeRagConfig(
  ragConfig: RagConfig | null | undefined,
  locale: Locale,
): RagConfig & Pick<RagSettingsState, "runtime" | "mcpConfigText" | "mcpConfigError" | "mcpLocale"> {
  const merged = {
    use_hyde: ragConfig?.use_hyde ?? DEFAULT_RAG_CONFIG.use_hyde,
    use_multi_query: ragConfig?.use_multi_query ?? DEFAULT_RAG_CONFIG.use_multi_query,
    use_query_rewriting: ragConfig?.use_query_rewriting ?? DEFAULT_RAG_CONFIG.use_query_rewriting,
    use_rerank: ragConfig?.use_rerank ?? DEFAULT_RAG_CONFIG.use_rerank,
    top_chunks: ragConfig?.top_chunks ?? DEFAULT_RAG_CONFIG.top_chunks,
  };

  return {
    ...exclusiveRetrievalMethods(activeExclusiveMethod(merged)),
    use_rerank: merged.use_rerank,
    top_chunks: clampTopChunks(merged.top_chunks),
    runtime: ragConfig?.runtime ?? "embed",
    ...resolveMcpConfigText(ragConfig, locale),
  };
}

function buildMcpPayload(
  mcpConfigText: string,
): { mcp: McpConnectionConfig | null; mcpConfigError: boolean } {
  const { config, error } = parseMcpConfigText(mcpConfigText);
  return {
    mcp: config,
    mcpConfigError: error,
  };
}

export const useRagSettingsStore = create<RagSettingsState>((set, get) => ({
  ...DEFAULT_RAG_CONFIG,
  use_history: true,
  runtime: "embed",
  mcpConfigText: formatMcpConfigText(buildDefaultMcpConnection("en"), "en"),
  mcpConfigError: false,
  mcpLocale: "en",
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
  setTopChunks: (value) => set({ top_chunks: clampTopChunks(value) }),
  setRuntime: (runtime, locale = get().mcpLocale) => {
    if (runtime === "mcp") {
      set({
        runtime,
        mcpConfigText: formatMcpConfigText(buildDefaultMcpConnection(locale), locale),
        mcpConfigError: false,
        mcpLocale: locale,
      });
      return;
    }

    set({ runtime, mcpConfigError: false });
  },
  setMcpConfigText: (text) => set({ mcpConfigText: text, mcpConfigError: false }),
  validateMcpConfigText: () => {
    const { config, error } = parseMcpConfigText(get().mcpConfigText);
    set({ mcpConfigError: error });
    return config !== null;
  },
  resetMcpConfigText: (locale = get().mcpLocale) =>
    set({
      mcpConfigText: formatMcpConfigText(buildDefaultMcpConnection(locale), locale),
      mcpConfigError: false,
      mcpLocale: locale,
    }),
  syncMcpLanguage: (locale) => {
    const { mcpConfigText, mcpLocale, runtime } = get();
    if (runtime !== "mcp" || mcpLocale === locale) {
      return false;
    }

    const { config } = parseMcpConfigText(mcpConfigText);
    const nextConfig = applyMcpLanguage(config ?? buildDefaultMcpConnection(locale), locale);

    set({
      mcpConfigText: formatMcpConfigText(nextConfig, locale),
      mcpConfigError: false,
      mcpLocale: locale,
    });

    return true;
  },
  hydrateFromChat: (ragConfig, useHistory, locale) =>
    set({
      ...mergeRagConfig(ragConfig, locale),
      use_history: useHistory ?? true,
    }),
  toConfig: () => {
    const {
      use_hyde,
      use_multi_query,
      use_query_rewriting,
      use_rerank,
      top_chunks,
      runtime,
      mcpConfigText,
      mcpLocale,
    } = get();

    const base: RagConfig = {
      use_hyde,
      use_multi_query,
      use_query_rewriting,
      use_rerank,
      top_chunks: clampTopChunks(top_chunks ?? DEFAULT_RAG_CONFIG.top_chunks),
      runtime,
    };

    if (runtime !== "mcp") {
      return base;
    }

    const { mcp } = buildMcpPayload(mcpConfigText);

    return {
      ...base,
      mcp: applyMcpLanguage(mcp ?? buildDefaultMcpConnection(mcpLocale), mcpLocale),
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
