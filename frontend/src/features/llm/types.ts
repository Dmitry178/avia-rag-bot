export type { LlmConfig } from "@/shared/api/types";

export const DEFAULT_LLM_CONFIG = {
  use_custom_prompt: false,
  custom_prompt: "",
} as const;
