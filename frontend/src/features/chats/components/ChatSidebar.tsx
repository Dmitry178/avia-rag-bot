import { useEffect } from "react";
import { Message } from "primereact/message";
import { ProgressSpinner } from "primereact/progressspinner";

import { NewChatButton, PanelHeader } from "@/app/layout/AppHeader";
import { useTranslation } from "@/shared/i18n";
import { formatDateTime } from "@/shared/lib/format";
import { useSelectedChatId, useChatUiStore } from "../store";
import { useChatsQuery, useCreateChatMutation } from "../hooks/useChats";

export function ChatSidebar() {
  const { t, locale } = useTranslation();
  const [selectedChatId, setSelectedChatId] = useSelectedChatId();
  const requestComposerFocus = useChatUiStore((state) => state.requestComposerFocus);
  const chatsQuery = useChatsQuery();
  const createChatMutation = useCreateChatMutation();

  useEffect(() => {
    if (!chatsQuery.isSuccess || selectedChatId === null) {
      return;
    }

    const chatExists = chatsQuery.data.some((chat) => chat.id === selectedChatId);

    if (!chatExists) {
      setSelectedChatId(null);
    }
  }, [chatsQuery.isSuccess, chatsQuery.data, selectedChatId, setSelectedChatId]);

  return (
    <>
      <PanelHeader
        title={t("panels.chats")}
        action={
          <NewChatButton
            label={t("chat.new")}
            onClick={() => {
              createChatMutation.mutate(t("chat.defaultTitle"), {
                onSuccess: () => requestComposerFocus(),
              });
            }}
            loading={createChatMutation.isPending}
          />
        }
      />

      <div className="app-panel__body">
        {chatsQuery.isLoading ? (
          <div className="trace-empty">
            <ProgressSpinner style={{ width: "2rem", height: "2rem" }} />
          </div>
        ) : null}

        {chatsQuery.isError ? (
          <div className="trace-empty">
            <Message severity="error" text={t("errors.loadChats")} />
          </div>
        ) : null}

        {chatsQuery.data?.length === 0 ? (
          <p className="trace-empty">{t("chat.createFirst")}</p>
        ) : null}

        <ul className="chat-list">
          {chatsQuery.data?.map((chat) => (
            <li key={chat.id}>
              <button
                type="button"
                className={`chat-list__item${
                  selectedChatId === chat.id ? " chat-list__item--active" : ""
                }`}
                onClick={() => {
                  setSelectedChatId(chat.id);
                  requestComposerFocus();
                }}
              >
                <span className="chat-list__title">{chat.title}</span>
                <span className="chat-list__meta">{formatDateTime(chat.updated_at, locale)}</span>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </>
  );
}
