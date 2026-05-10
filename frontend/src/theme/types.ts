import themesJson from "./themes.json";

export type ThemeName = keyof typeof themesJson.themes;

export type ThemePreference = ThemeName | "system";

export type ColorTokenKey = keyof typeof themesJson.themes.dark;

export type ThemeTokens = Record<ColorTokenKey, string>;

export interface ThemesConfig {
  defaultTheme: ThemeName;
  colorTokens: Record<ColorTokenKey, string>;
  themes: Record<ThemeName, ThemeTokens>;
  primeReactMapping: Record<string, ColorTokenKey>;
}

export const themesConfig = themesJson as ThemesConfig;

export const THEME_STORAGE_KEY = "avia-bot.theme";

export const themeNames = Object.keys(themesConfig.themes) as ThemeName[];
