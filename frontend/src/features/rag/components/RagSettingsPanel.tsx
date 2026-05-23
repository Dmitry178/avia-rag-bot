import { useState } from "react";
import { InputNumber } from "primereact/inputnumber";
import { InputSwitch } from "primereact/inputswitch";

import { useSelectedChatId } from "@/features/chats/store";
import { useUpdateChatSettingsMutation } from "@/features/chats/hooks/useChats";
import { useTranslation } from "@/shared/i18n";
import {
  RAG_CONFIG_TO_METHOD,
  RAG_METHOD_KEYS,
  RAG_TOP_CHUNKS_MAX,
  RAG_TOP_CHUNKS_MIN,
  type RagMethodKey,
} from "../types";
import { useRagSettingsStore } from "../ragSettingsStore";
import { RagMethodHelpDialog } from "./RagMethodHelpDialog";

export function RagSettingsPanel() {
  const { t } = useTranslation();
  const settings = useRagSettingsStore();
  const [selectedChatId] = useSelectedChatId();
  const updateSettingsMutation = useUpdateChatSettingsMutation(selectedChatId);
  const [helpMethod, setHelpMethod] = useState<RagMethodKey | null>(null);

  const persistSettings = () => {
    if (selectedChatId === null) {
      return;
    }

    updateSettingsMutation.mutate();
  };

  return (
    <>
      <RagMethodHelpDialog method={helpMethod} onHide={() => setHelpMethod(null)} />

      <section className="rag-settings" aria-label={t("rag.settingsTitle")}>
        <h3 className="rag-settings__title">{t("rag.settingsTitle")}</h3>

        <ul className="rag-settings__list">
          {RAG_METHOD_KEYS.map((method) => {
            const configKey = RAG_CONFIG_TO_METHOD[method];
            const enabled = settings[configKey] ?? false;

            return (
              <li key={method} className="rag-settings__item">
                <InputSwitch
                  className="rag-settings__switch"
                  checked={enabled}
                  onChange={(event) => {
                    settings.setMethodEnabled(method, event.value);
                    persistSettings();
                  }}
                  aria-label={t(`rag.methods.${method}`)}
                />

                <div className="rag-settings__label-group">
                  <span className="rag-settings__label">{t(`rag.methods.${method}`)}</span>
                  <button
                    type="button"
                    className="rag-settings__help"
                    aria-label={t("rag.methodHelpAria", { method: t(`rag.methods.${method}`) })}
                    onClick={() => setHelpMethod(method)}
                  >
                    <i className="pi pi-question-circle" aria-hidden="true" />
                  </button>
                </div>
              </li>
            );
          })}

          <li className="rag-settings__item rag-settings__item--top-chunks">
            <div className="rag-settings__top-chunks-col">
              <div className="rag-settings__label-group">
                <span className="rag-settings__label">{t("rag.topChunks")}</span>
              </div>
            </div>

            <div className="rag-settings__top-chunks-col">
              <InputNumber
              className="rag-settings__top-chunks"
              inputClassName="rag-settings__top-chunks-input"
              value={settings.top_chunks ?? 5}
              min={RAG_TOP_CHUNKS_MIN}
              max={RAG_TOP_CHUNKS_MAX}
              step={1}
              useGrouping={false}
              minFractionDigits={0}
              maxFractionDigits={0}
              allowEmpty={false}
              showButtons
              buttonLayout="horizontal"
              decrementButtonClassName="p-button-secondary p-button-text"
              incrementButtonClassName="p-button-secondary p-button-text"
              incrementButtonIcon="pi pi-plus"
              decrementButtonIcon="pi pi-minus"
              onKeyDown={(event) => {
                if (["e", "E", "+", "-", ".", ",", " "].includes(event.key)) {
                  event.preventDefault();
                }
              }}
              onValueChange={(event) => {
                if (event.value === null || event.value === undefined) {
                  return;
                }

                settings.setTopChunks(event.value);
                persistSettings();
              }}
              aria-label={t("rag.topChunks")}
              />
            </div>
          </li>

          <li className="rag-settings__item rag-settings__item--history">
            <InputSwitch
              className="rag-settings__switch"
              checked={settings.use_history ?? false}
              onChange={(event) => {
                settings.setUseHistory(event.value);
                persistSettings();
              }}
              aria-label={t("rag.useHistory")}
            />

            <div className="rag-settings__label-group">
              <span className="rag-settings__label">{t("rag.useHistory")}</span>
            </div>
          </li>
        </ul>
      </section>
    </>
  );
}
