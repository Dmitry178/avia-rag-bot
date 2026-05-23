export type { LlmConfig } from "@/shared/api/types";

export const DEFAULT_LLM_CONFIG = {
  use_custom_prompt: false,
  custom_prompt: null,
} as const satisfies { use_custom_prompt: boolean; custom_prompt: string | null };

export const DEFAULT_LLM_CREATE_PAYLOAD = {
  llm_config: DEFAULT_LLM_CONFIG,
  use_history: true,
} as const;
