import darkPrimeThemeUrl from "primereact/resources/themes/lara-dark-blue/theme.css?url";
import lightPrimeThemeUrl from "primereact/resources/themes/lara-light-blue/theme.css?url";

import { readPersistedState } from "@/shared/persist";

import type { ColorTokenKey, ThemeName, ThemePreference, ThemeTokens } from "./types";
import { themesConfig } from "./types";

const CSS_VAR_PREFIX = "--color";
const PRIME_THEME_LINK_ID = "prime-react-theme";

function toCssVarName(token: ColorTokenKey): string {
  return `${CSS_VAR_PREFIX}-${token.replaceAll(".", "-")}`;
}

function toPrimeCssVarName(primeKey: string): string {
  return `--p-${primeKey.replaceAll(".", "-")}`;
}

export function getThemeTokens(theme: ThemeName): ThemeTokens {
  return themesConfig.themes[theme];
}

function applyPrimeReactStylesheet(theme: ThemeName): void {
  const href = theme === "dark" ? darkPrimeThemeUrl : lightPrimeThemeUrl;
  let link = document.getElementById(PRIME_THEME_LINK_ID) as HTMLLinkElement | null;

  if (!link) {
    link = document.createElement("link");
    link.id = PRIME_THEME_LINK_ID;
    link.rel = "stylesheet";
    document.head.appendChild(link);
  }

  if (link.getAttribute("href") !== href) {
    link.href = href;
  }
}

export function applyTheme(theme: ThemeName): void {
  const root = document.documentElement;
  const tokens = getThemeTokens(theme);

  applyPrimeReactStylesheet(theme);
  root.dataset.theme = theme;

  for (const [token, value] of Object.entries(tokens) as [ColorTokenKey, string][]) {
    root.style.setProperty(toCssVarName(token), value);
  }

  root.style.setProperty("--focus-ring", tokens["focus.ring"]);

  for (const [primeKey, tokenKey] of Object.entries(themesConfig.primeReactMapping)) {
    root.style.setProperty(toPrimeCssVarName(primeKey), tokens[tokenKey]);
  }

  root.style.colorScheme = theme === "dark" ? "dark" : "light";
}

export function resolveTheme(preference: ThemePreference): ThemeName {
  if (preference === "system") {
    return window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  }

  return preference;
}

export function readStoredThemePreference(): ThemePreference {
  const state = readPersistedState<{ theme?: unknown }>("avia-bot.theme");

  if (state?.theme === "system" || state?.theme === "light" || state?.theme === "dark") {
    return state.theme;
  }

  return "system";
}

export function readStoredTheme(): ThemeName {
  return resolveTheme(readStoredThemePreference());
}
