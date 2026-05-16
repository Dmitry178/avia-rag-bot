import { create } from "zustand";

import type { LlmConfig } from "./types";
import { DEFAULT_LLM_CONFIG } from "./types";

interface LlmSettingsState extends LlmConfig {
  use_history: boolean | null;
  setUseHistory: (enabled: boolean) => void;
  setUseCustomPrompt: (enabled: boolean) => void;
  setCustomPrompt: (prompt: string) => void;
  hydrateFromChat: (
    llmConfig: LlmConfig | null | undefined,
    useHistory: boolean | null | undefined,
  ) => void;
  toPayload: () => { llm_config: LlmConfig; use_history: boolean | null };
}

function mergeLlmConfig(llmConfig: LlmConfig | null | undefined): LlmConfig {
  return {
    use_custom_prompt: llmConfig?.use_custom_prompt ?? DEFAULT_LLM_CONFIG.use_custom_prompt,
    custom_prompt: llmConfig?.custom_prompt ?? DEFAULT_LLM_CONFIG.custom_prompt,
  };
}

export const useLlmSettingsStore = create<LlmSettingsState>((set, get) => ({
  ...DEFAULT_LLM_CONFIG,
  use_history: true,
  setUseHistory: (enabled) => set({ use_history: enabled }),
  setUseCustomPrompt: (enabled) => set({ use_custom_prompt: enabled }),
  setCustomPrompt: (prompt) => set({ custom_prompt: prompt }),
  hydrateFromChat: (llmConfig, useHistory) =>
    set({
      ...mergeLlmConfig(llmConfig),
      use_history: useHistory ?? true,
    }),
  toPayload: () => {
    const { use_custom_prompt, custom_prompt, use_history } = get();

    return {
      llm_config: {
        use_custom_prompt,
        custom_prompt: custom_prompt?.trim() ? custom_prompt : null,
      },
      use_history,
    };
  },
}));
