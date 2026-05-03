import { create } from "zustand";
import { persist } from "zustand/middleware";

import { DEFAULT_LOCALE, type Locale } from "./config";
import { applyDocumentLocale, readStoredLocale, translate, type TranslationParams } from "./translate";

interface I18nState {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: string, params?: TranslationParams) => string;
}

export const useI18nStore = create<I18nState>()(
  persist(
    (set, get) => ({
      locale: readStoredLocale(),
      setLocale: (locale) => {
        applyDocumentLocale(locale);
        set({ locale });
      },
      t: (key, params) => translate(get().locale, key, params),
    }),
    {
      name: "avia-bot.locale",
      partialize: (state) => ({ locale: state.locale }),
      onRehydrateStorage: () => (state) => {
        const locale = state?.locale ?? DEFAULT_LOCALE;
        applyDocumentLocale(locale);
      },
    },
  ),
);

export function useTranslation() {
  const locale = useI18nStore((state) => state.locale);
  const setLocale = useI18nStore((state) => state.setLocale);
  const t = useI18nStore((state) => state.t);

  return { locale, setLocale, t };
}
