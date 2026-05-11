import { useEffect, useState } from "react";
import { Message } from "primereact/message";
import { ProgressSpinner } from "primereact/progressspinner";

import { NewChatButton, PanelHeader } from "@/app/layout/AppHeader";
import { DeleteConfirmDialog } from "@/shared/components/DeleteConfirmDialog";
import { useTranslation } from "@/shared/i18n";
import { formatDateTime } from "@/shared/lib/format";
import type { ChatSummary } from "@/shared/api/types";
import { useSelectedChatId, useChatUiStore } from "../store";
import { useChatsQuery, useCreateChatMutation, useDeleteChatMutation } from "../hooks/useChats";

export function ChatSidebar() {
  const { t, locale } = useTranslation();
  const [selectedChatId, setSelectedChatId] = useSelectedChatId();
  const requestComposerFocus = useChatUiStore((state) => state.requestComposerFocus);
  const chatsQuery = useChatsQuery();
  const createChatMutation = useCreateChatMutation();
  const deleteChatMutation = useDeleteChatMutation();
  const [chatToDelete, setChatToDelete] = useState<ChatSummary | null>(null);

  useEffect(() => {
    if (!chatsQuery.isSuccess || selectedChatId === null || chatsQuery.isFetching) {
      return;
    }

    const chatExists = chatsQuery.data.some((chat) => chat.id === selectedChatId);

    if (!chatExists) {
      setSelectedChatId(null);
    }
  }, [
    chatsQuery.isSuccess,
    chatsQuery.data,
    chatsQuery.isFetching,
    selectedChatId,
    setSelectedChatId,
  ]);

  return (
    <>
      <DeleteConfirmDialog
        visible={chatToDelete !== null}
        header={chatToDelete ? t("chat.deleteConfirmTitle", { title: chatToDelete.title }) : ""}
        message={t("chat.deleteConfirmMessage")}
        confirmLabel={t("chat.delete")}
        cancelLabel={t("common.cancel")}
        isPending={deleteChatMutation.isPending}
        onHide={() => setChatToDelete(null)}
        onConfirm={() => {
          if (chatToDelete === null) {
            return;
          }

          deleteChatMutation.mutate(chatToDelete.id, {
            onSuccess: () => setChatToDelete(null),
          });
        }}
      />

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
            <li
              key={chat.id}
              className={`chat-list__row${
                selectedChatId === chat.id ? " chat-list__row--active" : ""
              }`}
            >
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
                <span className="chat-list__title-row">
                  {chat.is_closed ? (
                    <i className="pi pi-lock chat-list__closed-icon" aria-hidden="true" />
                  ) : null}
                  <span
                    className={`chat-list__title${
                      chat.is_closed ? " chat-list__title--closed" : ""
                    }`}
                  >
                    {chat.title}
                  </span>
                </span>
                <span className="chat-list__meta">{formatDateTime(chat.updated_at, locale)}</span>
              </button>
              <button
                type="button"
                className="chat-list__delete"
                aria-label={t("chat.delete")}
                disabled={deleteChatMutation.isPending}
                onClick={(event) => {
                  event.stopPropagation();
                  setChatToDelete(chat);
                }}
              >
                <i className="pi pi-trash" aria-hidden="true" />
              </button>
            </li>
          ))}
        </ul>
      </div>
    </>
  );
}
