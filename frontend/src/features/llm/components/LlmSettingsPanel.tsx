import { InputSwitch } from "primereact/inputswitch";

import { useSelectedChatId } from "@/features/chats/store";
import { useUpdateChatSettingsMutation } from "@/features/chats/hooks/useChats";
import { useTranslation } from "@/shared/i18n";
import { useLlmSettingsStore } from "../llmSettingsStore";

export function LlmSettingsPanel() {
  const { t } = useTranslation();
  const settings = useLlmSettingsStore();
  const [selectedChatId] = useSelectedChatId();
  const updateSettingsMutation = useUpdateChatSettingsMutation(selectedChatId);

  const persistSettings = () => {
    if (selectedChatId === null) {
      return;
    }

    updateSettingsMutation.mutate();
  };

  return (
    <section className="rag-settings llm-settings" aria-label={t("llm.settingsTitle")}>
      <h3 className="rag-settings__title">{t("llm.settingsTitle")}</h3>

      <ul className="rag-settings__list">
        <li className="rag-settings__item rag-settings__item--history">
          <InputSwitch
            className="rag-settings__switch"
            checked={settings.use_history ?? true}
            onChange={(event) => {
              settings.setUseHistory(event.value);
              persistSettings();
            }}
            aria-label={t("llm.useHistory")}
          />

          <div className="rag-settings__label-group">
            <span className="rag-settings__label">{t("llm.useHistory")}</span>
          </div>
        </li>

        <li className="rag-settings__item">
          <InputSwitch
            className="rag-settings__switch"
            checked={settings.use_custom_prompt ?? false}
            onChange={(event) => {
              settings.setUseCustomPrompt(event.value);
              persistSettings();
            }}
            aria-label={t("llm.useCustomPrompt")}
          />

          <div className="rag-settings__label-group">
            <span className="rag-settings__label">{t("llm.useCustomPrompt")}</span>
          </div>
        </li>
      </ul>
    </section>
  );
}
