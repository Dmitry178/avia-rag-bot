import type { McpConnectionConfig } from "@/shared/api/types";
import type { Locale } from "@/shared/i18n";

export const MCP_SCHEMAS_DIR_ENV_KEY = "MCP_RAG__SCHEMAS_DIR";
export const MCP_LANGUAGE_ENV_KEY = "MCP_RAG__LANGUAGE";

export function buildDefaultMcpConnection(locale: Locale = "en"): McpConnectionConfig {
  return {
    command: "uv",
    args: ["run", "python", "-m", "src.server"],
    cwd: "../mcp-rag",
    env: {
      [MCP_SCHEMAS_DIR_ENV_KEY]: "../data",
      [MCP_LANGUAGE_ENV_KEY]: locale,
    },
  };
}

export function applyMcpLanguage(config: McpConnectionConfig, locale: Locale): McpConnectionConfig {
  return {
    ...config,
    env: {
      ...config.env,
      [MCP_SCHEMAS_DIR_ENV_KEY]: config.env?.[MCP_SCHEMAS_DIR_ENV_KEY] ?? "../data",
      [MCP_LANGUAGE_ENV_KEY]: locale,
    },
  };
}

export function formatMcpConfigText(
  mcp: McpConnectionConfig | null | undefined,
  locale: Locale = "en",
): string {
  return JSON.stringify(mcp ?? buildDefaultMcpConnection(locale), null, 2);
}

export function parseMcpConfigText(text: string): {
  config: McpConnectionConfig | null;
  error: boolean;
} {
  const trimmed = text.trim();
  if (!trimmed) {
    return { config: null, error: true };
  }

  try {
    const parsed: unknown = JSON.parse(trimmed);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      return { config: null, error: true };
    }

    const record = parsed as Record<string, unknown>;
    if (typeof record.command !== "string" || record.command.length === 0) {
      return { config: null, error: true };
    }

    if (!Array.isArray(record.args) || !record.args.every((item) => typeof item === "string")) {
      return { config: null, error: true };
    }

    let parsedEnv: Record<string, string> | undefined;
    if (record.env !== undefined) {
      if (
        record.env === null ||
        typeof record.env !== "object" ||
        Array.isArray(record.env) ||
        !Object.entries(record.env).every(([key, value]) => typeof key === "string" && typeof value === "string")
      ) {
        return { config: null, error: true };
      }

      parsedEnv = record.env as Record<string, string>;
    }

    let parsedCwd: string | undefined;
    if (record.cwd !== undefined && record.cwd !== null) {
      if (typeof record.cwd !== "string") {
        return { config: null, error: true };
      }

      parsedCwd = record.cwd;
    }

    return {
      config: {
        command: record.command,
        args: record.args,
        ...(parsedCwd !== undefined ? { cwd: parsedCwd } : {}),
        ...(parsedEnv !== undefined ? { env: parsedEnv } : {}),
      },
      error: false,
    };
  } catch {
    return { config: null, error: true };
  }
}
