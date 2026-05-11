import en from "./locales/rag-methods.en.json";
import ru from "./locales/rag-methods.ru.json";
import type { Locale } from "./config";
import type { RagMethodKey } from "@/features/rag/types";

export type RagMethodHelp = {
  title: string;
  description: string;
};

const catalogs: Record<Locale, Record<RagMethodKey, RagMethodHelp>> = {
  ru,
  en,
};

export function getRagMethodHelp(locale: Locale, method: RagMethodKey): RagMethodHelp {
  return catalogs[locale][method];
}
