import { Button } from "primereact/button";
import { SelectButton } from "primereact/selectbutton";

import { type ChatMode, useChatModeStore } from "@/features/chat/modeStore";
import { useChatUiStore } from "@/features/chats/store";
import { type Locale, useTranslation } from "@/shared/i18n";
import { useThemeStore } from "@/theme/store";
import type { ThemePreference } from "@/theme/types";

export function AppHeader() {
  const { t, locale, setLocale } = useTranslation();
  const theme = useThemeStore((state) => state.theme);
  const setTheme = useThemeStore((state) => state.setTheme);
  const chatMode = useChatModeStore((state) => state.mode);
  const setChatMode = useChatModeStore((state) => state.setMode);
  const requestComposerFocus = useChatUiStore((state) => state.requestComposerFocus);

  const themeOptions: { label: string; value: ThemePreference }[] = [
    { label: t("theme.system"), value: "system" },
    { label: t("theme.light"), value: "light" },
    { label: t("theme.dark"), value: "dark" },
  ];

  const localeOptions: { label: string; value: Locale }[] = [
    { label: t("locale.ru"), value: "ru" },
    { label: t("locale.en"), value: "en" },
  ];

  const modeOptions: { label: string; value: ChatMode }[] = [
    { label: t("mode.llm"), value: "llm" },
    { label: t("mode.rag"), value: "rag" },
  ];

  const subtitle =
    chatMode === "llm" ? t("app.subtitleLlm") : t("app.subtitleRag");

  return (
    <header className="app-header">
      <div>
        <h1 className="app-header__title">{t("app.title")}</h1>
        <p className="app-header__subtitle">{subtitle}</p>
      </div>

      <div className="app-header__controls">
        <SelectButton
          className="app-header__select"
          value={chatMode}
          options={modeOptions}
          onChange={(event) => {
            if (event.value) {
              setChatMode(event.value as ChatMode);
              requestComposerFocus();
            }
          }}
          allowEmpty={false}
        />

        <SelectButton
          className="app-header__select"
          value={locale}
          options={localeOptions}
          onChange={(event) => {
            if (event.value) {
              setLocale(event.value as Locale);
              requestComposerFocus();
            }
          }}
          allowEmpty={false}
        />

        <SelectButton
          className="app-header__select"
          value={theme}
          options={themeOptions}
          onChange={(event) => {
            if (event.value) {
              setTheme(event.value as ThemePreference);
              requestComposerFocus();
            }
          }}
          allowEmpty={false}
        />
      </div>
    </header>
  );
}

export function PanelHeader({
  title,
  action,
}: {
  title: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="app-panel__header">
      <h2 className="app-panel__title">{title}</h2>
      {action}
    </div>
  );
}

export function NewChatButton({
  label,
  onClick,
  loading,
}: {
  label: string;
  onClick: () => void;
  loading?: boolean;
}) {
  return (
    <Button
      label={label}
      icon="pi pi-plus"
      iconPos="left"
      size="small"
      onClick={onClick}
      loading={loading}
    />
  );
}
