import { useEffect } from "react";
import { ProgressSpinner } from "primereact/progressspinner";

import { NewChatButton, PanelHeader } from "@/app/layout/AppHeader";
import { useDeleteConfirmStore } from "@/shared/components/deleteConfirmStore";
import { useTranslation } from "@/shared/i18n";
import { formatDateTime } from "@/shared/lib/format";
import { useSelectedChatId, useChatUiStore } from "../store";
import { useChatsQuery, useCreateChatMutation, useDeleteChatMutation } from "../hooks/useChats";

export function ChatSidebar() {
  const { t, locale } = useTranslation();
  const [selectedChatId, setSelectedChatId] = useSelectedChatId();
  const requestComposerFocus = useChatUiStore((state) => state.requestComposerFocus);
  const chatsQuery = useChatsQuery();
  const createChatMutation = useCreateChatMutation();
  const deleteChatMutation = useDeleteChatMutation();
  const openDeleteConfirm = useDeleteConfirmStore((state) => state.open);
  const closeDeleteConfirm = useDeleteConfirmStore((state) => state.close);
  const setDeleteConfirmPending = useDeleteConfirmStore((state) => state.setPending);

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
      <PanelHeader title={t("panels.chats")} />

      <div className="app-panel__body">
        <div className="chat-sidebar__toolbar">
          <NewChatButton
            label={t("chat.new")}
            onClick={() => {
              createChatMutation.mutate(t("chat.defaultTitle"), {
                onSuccess: () => requestComposerFocus(),
              });
            }}
            loading={createChatMutation.isPending}
          />
        </div>

        {chatsQuery.isLoading ? (
          <div className="trace-empty">
            <ProgressSpinner style={{ width: "2rem", height: "2rem" }} />
          </div>
        ) : null}

        {chatsQuery.data?.length === 0 ? (
          <p className="trace-empty">{t("chat.createFirst")}</p>
        ) : null}

        <ul className="chat-list">
          {chatsQuery.data?.map((chat) => (
            <li
              key={chat.id}
              data-chat-id={chat.id}
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
                <span className="chat-list__meta">{formatDateTime(chat.created_at, locale)}</span>
              </button>
              <button
                type="button"
                className="chat-list__delete"
                aria-label={t("chat.delete")}
                disabled={deleteChatMutation.isPending}
                onClick={(event) => {
                  event.stopPropagation();

                  if (chat.message_count === 0) {
                    deleteChatMutation.mutate(chat.id);
                    return;
                  }

                  openDeleteConfirm({
                    header: t("chat.deleteConfirmTitle", { title: chat.title }),
                    message: t("chat.deleteConfirmMessage"),
                    confirmLabel: t("chat.delete"),
                    cancelLabel: t("common.cancel"),
                    onConfirm: () => {
                      setDeleteConfirmPending(true);
                      deleteChatMutation.mutate(chat.id, {
                        onSuccess: () => closeDeleteConfirm(),
                        onSettled: () => setDeleteConfirmPending(false),
                      });
                    },
                  });
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
