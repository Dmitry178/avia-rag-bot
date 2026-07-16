import { useCallback, useEffect, useRef, useState } from "react";
import { ProgressSpinner } from "primereact/progressspinner";

import { NewChatButton, PanelHeader } from "@/app/layout/AppHeader";
import { useDeleteConfirmStore } from "@/shared/components/deleteConfirmStore";
import { useTranslation } from "@/shared/i18n";
import { formatDateTime } from "@/shared/lib/format";
import { isPointerOverElement } from "@/shared/lib/pointerPosition";
import type { ChatSummary } from "@/shared/api/types";
import { useSelectedChatId, useChatUiStore } from "../store";
import { useChatsQuery, useCreateChatMutation, useDeleteChatMutation } from "../hooks/useChats";

type ChatListRowProps = {
  chat: ChatSummary;
  isActive: boolean;
  isHovered: boolean;
  isDeletePending: boolean;
  onMouseEnter: () => void;
  onMouseLeave: () => void;
  onSelect: () => void;
  onDelete: (chat: ChatSummary) => void;
};

function ChatListRow({
  chat,
  isActive,
  isHovered,
  isDeletePending,
  onMouseEnter,
  onMouseLeave,
  onSelect,
  onDelete,
}: ChatListRowProps) {
  const { t, locale } = useTranslation();

  return (
    <li
      data-chat-id={chat.id}
      className={`chat-list__row${isActive ? " chat-list__row--active" : ""}${
        isHovered ? " chat-list__row--hovered" : ""
      }`}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
    >
      <button
        type="button"
        className={`chat-list__item${isActive ? " chat-list__item--active" : ""}`}
        onClick={onSelect}
      >
        <span className="chat-list__title-row">
          {chat.is_closed ? (
            <i className="pi pi-lock chat-list__closed-icon" aria-hidden="true" />
          ) : null}
          <span className={`chat-list__title${chat.is_closed ? " chat-list__title--closed" : ""}`}>
            {chat.title}
          </span>
        </span>
        <span className="chat-list__meta">{formatDateTime(chat.created_at, locale)}</span>
      </button>
      <button
        type="button"
        className="chat-list__delete"
        aria-label={t("chat.delete")}
        disabled={isDeletePending}
        onMouseDown={(event) => event.preventDefault()}
        onClick={(event) => {
          event.stopPropagation();
          onDelete(chat);
        }}
      >
        <i className="pi pi-trash" aria-hidden="true" />
      </button>
    </li>
  );
}

function findHoveredChatId(listElement: HTMLUListElement | null): number | null {
  if (!listElement) {
    return null;
  }

  for (const row of listElement.querySelectorAll<HTMLLIElement>("li[data-chat-id]")) {
    if (isPointerOverElement(row)) {
      return Number(row.dataset.chatId);
    }
  }

  return null;
}

export function ChatSidebar() {
  const { t } = useTranslation();
  const [selectedChatId, setSelectedChatId] = useSelectedChatId();
  const requestComposerFocus = useChatUiStore((state) => state.requestComposerFocus);
  const chatsQuery = useChatsQuery();
  const createChatMutation = useCreateChatMutation();
  const deleteChatMutation = useDeleteChatMutation();
  const openDeleteConfirm = useDeleteConfirmStore((state) => state.open);
  const closeDeleteConfirm = useDeleteConfirmStore((state) => state.close);
  const setDeleteConfirmPending = useDeleteConfirmStore((state) => state.setPending);
  const listRef = useRef<HTMLUListElement>(null);
  const [hoveredChatId, setHoveredChatId] = useState<number | null>(null);
  const hoverResetKey = chatsQuery.data?.map((chat) => chat.id).join(",") ?? "";

  const clearHover = useCallback(() => {
    setHoveredChatId(null);

    if (document.activeElement instanceof HTMLElement) {
      document.activeElement.blur();
    }
  }, []);

  const syncHoverFromPointer = useCallback(() => {
    setHoveredChatId(findHoveredChatId(listRef.current));
  }, []);

  useEffect(() => {
    syncHoverFromPointer();
  }, [hoverResetKey, syncHoverFromPointer]);

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

  const handleDeleteChat = (chat: ChatSummary) => {
    clearHover();

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
  };

  return (
    <>
      <PanelHeader title={t("panels.chats")} />

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

      <div className="app-panel__body">
        {chatsQuery.isLoading ? (
          <div className="trace-empty">
            <ProgressSpinner style={{ width: "2rem", height: "2rem" }} />
          </div>
        ) : null}

        {chatsQuery.data?.length === 0 ? (
          <p className="trace-empty">{t("chat.createFirst")}</p>
        ) : null}

        <ul ref={listRef} className="chat-list">
          {chatsQuery.data?.map((chat) => (
            <ChatListRow
              key={chat.id}
              chat={chat}
              isActive={selectedChatId === chat.id}
              isHovered={hoveredChatId === chat.id}
              isDeletePending={
                deleteChatMutation.isPending && deleteChatMutation.variables === chat.id
              }
              onMouseEnter={() => setHoveredChatId(chat.id)}
              onMouseLeave={() => {
                setHoveredChatId((current) => (current === chat.id ? null : current));
              }}
              onSelect={() => {
                setSelectedChatId(chat.id);
                requestComposerFocus();
              }}
              onDelete={handleDeleteChat}
            />
          ))}
        </ul>
      </div>
    </>
  );
}
