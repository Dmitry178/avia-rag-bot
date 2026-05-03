import type { ColorTokenKey, ThemeName, ThemeTokens } from "./types";
import { themesConfig } from "./types";

const CSS_VAR_PREFIX = "--color";

function toCssVarName(token: ColorTokenKey): string {
  return `${CSS_VAR_PREFIX}-${token.replaceAll(".", "-")}`;
}

function toPrimeCssVarName(primeKey: string): string {
  return `--p-${primeKey.replaceAll(".", "-")}`;
}

export function getThemeTokens(theme: ThemeName): ThemeTokens {
  return themesConfig.themes[theme];
}

export function applyTheme(theme: ThemeName): void {
  const root = document.documentElement;
  const tokens = getThemeTokens(theme);

  root.dataset.theme = theme;

  for (const [token, value] of Object.entries(tokens) as [ColorTokenKey, string][]) {
    root.style.setProperty(toCssVarName(token), value);
  }

  for (const [primeKey, tokenKey] of Object.entries(themesConfig.primeReactMapping)) {
    root.style.setProperty(toPrimeCssVarName(primeKey), tokens[tokenKey]);
  }

  root.style.colorScheme = theme === "dark" ? "dark" : "light";
}

export function readStoredTheme(): ThemeName {
  const stored = localStorage.getItem("avia-bot.theme");

  if (stored === "light" || stored === "dark") {
    return stored;
  }

  return themesConfig.defaultTheme;
}
