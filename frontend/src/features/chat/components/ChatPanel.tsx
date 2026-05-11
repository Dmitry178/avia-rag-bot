import { useEffect, useRef, useState } from "react";
import { Button } from "primereact/button";
import { InputTextarea } from "primereact/inputtextarea";
import { Message } from "primereact/message";
import { ProgressSpinner } from "primereact/progressspinner";
import ReactMarkdown from "react-markdown";

import { PanelHeader } from "@/app/layout/AppHeader";
import { DeleteConfirmDialog } from "@/shared/components/DeleteConfirmDialog";
import { useChatModeStore } from "@/features/chat/modeStore";
import { useRagSettingsStore } from "@/features/rag/ragSettingsStore";
import { useSelectedChatId } from "@/features/chats/store";
import { useTranslation } from "@/shared/i18n";
import { useChatDetailQuery, useDeleteMessageMutation, useSendMessageMutation } from "../hooks/useChat";
import { useComposerAutoResize } from "../hooks/useComposerAutoResize";
import { useComposerDraft } from "../hooks/useComposerDraft";
import { useComposerFocus } from "../hooks/useComposerFocus";

function MessageBubble({
  messageId,
  role,
  content,
  onDelete,
  isDeleteDisabled,
}: {
  messageId: number;
  role: "user" | "assistant" | "system";
  content: string;
  onDelete: (messageId: number) => void;
  isDeleteDisabled: boolean;
}) {
  const { t } = useTranslation();
  const label =
    role === "user"
      ? t("roles.user")
      : role === "assistant"
        ? t("roles.assistant")
        : t("roles.system");

  const showDelete = role === "user" || role === "assistant";

  const bubble = (
    <article
      className={`chat-message${
        role === "user" ? " chat-message--user" : role === "assistant" ? " chat-message--assistant" : ""
      }`}
    >
      {showDelete ? (
        <button
          type="button"
          className="chat-message__delete"
          aria-label={t("chat.deleteMessage")}
          disabled={isDeleteDisabled}
          onClick={() => onDelete(messageId)}
        >
          <i className="pi pi-trash" aria-hidden="true" />
        </button>
      ) : null}
      <p className="chat-message__role">{label}</p>
      <div className="chat-message__content">
        {role === "assistant" ? <ReactMarkdown>{content}</ReactMarkdown> : <p>{content}</p>}
      </div>
    </article>
  );

  if (role === "assistant") {
    return (
      <div className="chat-message-row chat-message-row--assistant">
        <i className="pi pi-sparkles chat-message__avatar chat-message__avatar--assistant" aria-hidden="true" />
        {bubble}
      </div>
    );
  }

  if (role === "user") {
    return (
      <div className="chat-message-row chat-message-row--user">
        {bubble}
        <i className="pi pi-user chat-message__avatar chat-message__avatar--user" aria-hidden="true" />
      </div>
    );
  }

  return bubble;
}

export function ChatPanel() {
  const { t } = useTranslation();
  const chatMode = useChatModeStore((state) => state.mode);
  const toRagConfig = useRagSettingsStore((state) => state.toConfig);
  const [selectedChatId] = useSelectedChatId();
  const chatQuery = useChatDetailQuery(selectedChatId);
  const sendMutation = useSendMessageMutation(selectedChatId);
  const deleteMessageMutation = useDeleteMessageMutation(selectedChatId);
  const [messageToDelete, setMessageToDelete] = useState<number | null>(null);
  const { draft, setDraft, clearDraft } = useComposerDraft(selectedChatId);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const panelBodyRef = useRef<HTMLDivElement>(null);
  const prevChatIdRef = useRef<number | null>(null);
  const prevMessageCountRef = useRef(0);

  const isChatClosed = chatQuery.data?.is_closed === true;

  const isComposerDisabled =
    selectedChatId === null || isChatClosed || sendMutation.isPending;

  useComposerFocus({
    textareaRef,
    selectedChatId,
    isComposerDisabled,
    isSendPending: sendMutation.isPending,
  });

  useComposerAutoResize({ textareaRef, value: draft });

  const inputPlaceholder =
    selectedChatId === null
      ? t("chat.placeholderSelect")
      : chatMode === "llm"
        ? t("chat.placeholderLlm")
        : t("chat.placeholderInput");

  useEffect(() => {
    if (!chatQuery.isSuccess || selectedChatId === null) {
      return;
    }

    const container = panelBodyRef.current;

    if (!container) {
      return;
    }

    const messageCount = chatQuery.data?.messages.length ?? 0;
    const chatChanged = prevChatIdRef.current !== selectedChatId;

    if (chatChanged) {
      prevChatIdRef.current = selectedChatId;
      prevMessageCountRef.current = messageCount;
    } else if (messageCount <= prevMessageCountRef.current) {
      prevMessageCountRef.current = messageCount;
      return;
    }

    prevMessageCountRef.current = messageCount;

    const scrollToBottom = () => {
      container.scrollTop = container.scrollHeight;
    };

    scrollToBottom();
    const frameId = requestAnimationFrame(scrollToBottom);

    return () => cancelAnimationFrame(frameId);
  }, [selectedChatId, chatQuery.isSuccess, chatQuery.data?.messages.length]);

  const handleSend = () => {
    const content = draft.trim();
    if (!content || selectedChatId === null || sendMutation.isPending) {
      return;
    }

    sendMutation.mutate(
      {
        content,
        rag_config: chatMode === "rag" ? toRagConfig() : undefined,
      },
      {
        onSuccess: () => clearDraft(),
      },
    );
  };

  return (
    <>
      <DeleteConfirmDialog
        visible={messageToDelete !== null}
        header={t("chat.deleteMessageConfirmTitle")}
        message={t("chat.deleteMessageConfirmMessage")}
        confirmLabel={t("chat.deleteMessage")}
        cancelLabel={t("common.cancel")}
        isPending={deleteMessageMutation.isPending}
        onHide={() => setMessageToDelete(null)}
        onConfirm={() => {
          if (messageToDelete === null) {
            return;
          }

          deleteMessageMutation.mutate(messageToDelete, {
            onSuccess: () => setMessageToDelete(null),
          });
        }}
      />

      <PanelHeader title={t("panels.dialog")} />

      <div className="app-panel__body" ref={panelBodyRef}>
        {selectedChatId === null ? (
          <p className="trace-empty">{t("chat.selectOrCreate")}</p>
        ) : null}

        {selectedChatId !== null && chatQuery.isLoading ? (
          <div className="trace-empty">
            <ProgressSpinner style={{ width: "2rem", height: "2rem" }} />
          </div>
        ) : null}

        {chatQuery.isError ? (
          <div className="trace-empty">
            <Message severity="error" text={t("errors.loadChat")} />
          </div>
        ) : null}

        {chatQuery.data ? (
          <div className="chat-messages">
            {chatQuery.data.messages.map((message) => (
              <MessageBubble
                key={message.id}
                messageId={message.id}
                role={message.role}
                content={message.content}
                onDelete={setMessageToDelete}
                isDeleteDisabled={deleteMessageMutation.isPending || messageToDelete !== null}
              />
            ))}
          </div>
        ) : null}
      </div>

      <div className={`chat-composer${isChatClosed ? " chat-composer--closed" : ""}`}>
        {isChatClosed ? (
          <p className="chat-composer__closed">{t("chat.placeholderClosed")}</p>
        ) : (
          <>
            <InputTextarea
              ref={textareaRef}
              className="chat-composer__input"
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              rows={1}
              disabled={isComposerDisabled}
              placeholder={inputPlaceholder}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  handleSend();
                }
              }}
            />
            <Button
              className="chat-composer__send"
              icon="pi pi-send"
              label={t("common.send")}
              onClick={handleSend}
              loading={sendMutation.isPending}
              disabled={selectedChatId === null || !draft.trim()}
            />
          </>
        )}
      </div>

      {sendMutation.isError ? (
        <div style={{ padding: "0 1rem 1rem" }}>
          <Message severity="error" text={sendMutation.error.message} />
        </div>
      ) : null}
    </>
  );
}
