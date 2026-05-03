import { create } from "zustand";
import { persist } from "zustand/middleware";

import { applyTheme, readStoredTheme } from "./applyTheme";
import type { ThemeName } from "./types";
import { themesConfig } from "./types";

interface ThemeState {
  theme: ThemeName;
  setTheme: (theme: ThemeName) => void;
  toggleTheme: () => void;
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      theme: readStoredTheme(),
      setTheme: (theme) => {
        applyTheme(theme);
        set({ theme });
      },
      toggleTheme: () => {
        const next: ThemeName = get().theme === "dark" ? "light" : "dark";
        applyTheme(next);
        set({ theme: next });
      },
    }),
    {
      name: "avia-bot.theme",
      partialize: (state) => ({ theme: state.theme }),
      onRehydrateStorage: () => (state) => {
        const theme = state?.theme ?? themesConfig.defaultTheme;
        applyTheme(theme);
      },
    },
  ),
);
