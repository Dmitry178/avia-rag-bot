import { create } from "zustand";
import { persist } from "zustand/middleware";

import { applyTheme, readStoredThemePreference, resolveTheme } from "./applyTheme";
import type { ThemeName, ThemePreference } from "./types";

interface ThemeState {
  theme: ThemePreference;
  setTheme: (theme: ThemePreference) => void;
  toggleTheme: () => void;
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      theme: readStoredThemePreference(),
      setTheme: (theme) => {
        applyTheme(resolveTheme(theme));
        set({ theme });
      },
      toggleTheme: () => {
        const resolved: ThemeName = resolveTheme(get().theme);
        const next: ThemeName = resolved === "dark" ? "light" : "dark";
        applyTheme(next);
        set({ theme: next });
      },
    }),
    {
      name: "avia-bot.theme",
      partialize: (state) => ({ theme: state.theme }),
      onRehydrateStorage: () => (state) => {
        const preference = state?.theme ?? "system";
        applyTheme(resolveTheme(preference));
      },
    },
  ),
);
