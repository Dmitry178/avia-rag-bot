import en from "./locales/en.json";
import ru from "./locales/ru.json";

export const SUPPORTED_LOCALES = ["ru", "en"] as const;

export type Locale = (typeof SUPPORTED_LOCALES)[number];

export const DEFAULT_LOCALE: Locale = "ru";

export const LOCALE_STORAGE_KEY = "avia-bot.locale";

export const LOCALE_HTML_LANG: Record<Locale, string> = {
  ru: "ru",
  en: "en",
};

export const LOCALE_INTL_TAG: Record<Locale, string> = {
  ru: "ru-RU",
  en: "en-US",
};

export type Messages = typeof ru;

export const messages: Record<Locale, Messages> = {
  ru,
  en,
};
