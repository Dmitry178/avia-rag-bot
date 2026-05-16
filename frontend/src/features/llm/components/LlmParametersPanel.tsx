import { InputTextarea } from "primereact/inputtextarea";

import { useChatDetailQuery } from "@/features/chat/hooks/useChat";
import { useSelectedChatId } from "@/features/chats/store";
import { useUpdateChatSettingsMutation } from "@/features/chats/hooks/useChats";
import { PanelHeader } from "@/app/layout/AppHeader";
import { useTranslation } from "@/shared/i18n";
import { useHydrateLlmSettings } from "../hooks/useHydrateLlmSettings";
import { useLlmSettingsStore } from "../llmSettingsStore";
import { LlmSettingsPanel } from "./LlmSettingsPanel";

export function LlmParametersPanel() {
  const { t } = useTranslation();
  const [selectedChatId] = useSelectedChatId();
  const chatQuery = useChatDetailQuery(selectedChatId);
  const updateSettingsMutation = useUpdateChatSettingsMutation(selectedChatId);
  const settings = useLlmSettingsStore();

  useHydrateLlmSettings(chatQuery.data);

  const persistSettings = () => {
    if (selectedChatId === null) {
      return;
    }

    updateSettingsMutation.mutate();
  };

  return (
    <>
      <PanelHeader title={t("panels.parameters")} />

      <div className="app-panel__body app-panel__body--trace">
        <LlmSettingsPanel />

        <div className="trace-panel__stream">
          <InputTextarea
            className="llm-settings__prompt"
            value={settings.custom_prompt ?? ""}
            onChange={(event) => settings.setCustomPrompt(event.target.value)}
            onBlur={persistSettings}
            disabled={!settings.use_custom_prompt}
            rows={8}
            autoResize
            placeholder={t("llm.customPromptPlaceholder")}
            aria-label={t("llm.customPromptAria")}
          />
        </div>
      </div>
    </>
  );
}
