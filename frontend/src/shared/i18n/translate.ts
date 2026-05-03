import type { Locale, Messages } from "./config";
import { messages } from "./config";

export type TranslationParams = Record<string, string | number>;

function resolvePath(tree: Messages, key: string): string | undefined {
  const parts = key.split(".");
  let current: unknown = tree;

  for (const part of parts) {
    if (typeof current !== "object" || current === null || !(part in current)) {
      return undefined;
    }

    current = (current as Record<string, unknown>)[part];
  }

  return typeof current === "string" ? current : undefined;
}

function interpolate(template: string, params?: TranslationParams): string {
  if (!params) {
    return template;
  }

  return Object.entries(params).reduce(
    (result, [name, value]) => result.replaceAll(`{{${name}}}`, String(value)),
    template,
  );
}

export function translate(locale: Locale, key: string, params?: TranslationParams): string {
  const value = resolvePath(messages[locale], key);

  if (value === undefined) {
    return key;
  }

  return interpolate(value, params);
}

export function readStoredLocale(): Locale {
  const stored = localStorage.getItem("avia-bot.locale");

  if (stored === "ru" || stored === "en") {
    return stored;
  }

  return "ru";
}

export function applyDocumentLocale(locale: Locale): void {
  document.documentElement.lang = locale === "ru" ? "ru" : "en";
  document.title = translate(locale, "app.title");
}
