import { useEffect, useRef, useState } from "react";
import { Button } from "primereact/button";
import { InputTextarea } from "primereact/inputtextarea";
import { Message } from "primereact/message";
import { ProgressSpinner } from "primereact/progressspinner";
import ReactMarkdown from "react-markdown";

import { PanelHeader } from "@/app/layout/AppHeader";
import { useChatModeStore } from "@/features/chat/modeStore";
import { useChatUiStore } from "@/features/chats/store";
import { useTranslation } from "@/shared/i18n";
import { useChatDetailQuery, useSendMessageMutation } from "../hooks/useChat";
import { useComposerFocus } from "../hooks/useComposerFocus";

function MessageBubble({
  role,
  content,
}: {
  role: "user" | "assistant" | "system";
  content: string;
}) {
  const { t } = useTranslation();
  const label =
    role === "user"
      ? t("roles.user")
      : role === "assistant"
        ? t("roles.assistant")
        : t("roles.system");

  return (
    <article
      className={`chat-message${
        role === "user" ? " chat-message--user" : role === "assistant" ? " chat-message--assistant" : ""
      }`}
    >
      <p className="chat-message__role">{label}</p>
      <div className="chat-message__content">
        {role === "assistant" ? <ReactMarkdown>{content}</ReactMarkdown> : <p>{content}</p>}
      </div>
    </article>
  );
}

export function ChatPanel() {
  const { t } = useTranslation();
  const chatMode = useChatModeStore((state) => state.mode);
  const selectedChatId = useChatUiStore((state) => state.selectedChatId);
  const chatQuery = useChatDetailQuery(selectedChatId);
  const sendMutation = useSendMessageMutation(selectedChatId);
  const [draft, setDraft] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const panelBodyRef = useRef<HTMLDivElement>(null);

  const isComposerDisabled =
    selectedChatId === null || chatQuery.data?.is_closed === true || sendMutation.isPending;

  useComposerFocus({
    textareaRef,
    selectedChatId,
    isComposerDisabled,
    isSendPending: sendMutation.isPending,
  });

  const inputPlaceholder =
    selectedChatId === null
      ? t("chat.placeholderSelect")
      : chatQuery.data?.is_closed
        ? t("chat.placeholderClosed")
        : chatMode === "llm"
          ? t("chat.placeholderLlm")
          : t("chat.placeholderInput");

  useEffect(() => {
    setDraft("");
  }, [selectedChatId]);

  useEffect(() => {
    if (!chatQuery.isSuccess || selectedChatId === null) {
      return;
    }

    const container = panelBodyRef.current;

    if (!container) {
      return;
    }

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

    sendMutation.mutate(content, {
      onSuccess: () => setDraft(""),
    });
  };

  return (
    <>
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
              <MessageBubble key={message.id} role={message.role} content={message.content} />
            ))}
          </div>
        ) : null}
      </div>

      <div className="chat-composer">
        <InputTextarea
          ref={textareaRef}
          className="chat-composer__input"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          rows={3}
          autoResize
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
          icon="pi pi-send"
          label={t("common.send")}
          onClick={handleSend}
          loading={sendMutation.isPending}
          disabled={selectedChatId === null || !draft.trim() || chatQuery.data?.is_closed}
        />
      </div>

      {sendMutation.isError ? (
        <div style={{ padding: "0 1rem 1rem" }}>
          <Message severity="error" text={sendMutation.error.message} />
        </div>
      ) : null}
    </>
  );
}
