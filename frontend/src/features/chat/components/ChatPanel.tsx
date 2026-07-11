import { useEffect, useRef } from "react";
import { Button } from "primereact/button";
import { InputTextarea } from "primereact/inputtextarea";
import { ProgressSpinner } from "primereact/progressspinner";
import ReactMarkdown from "react-markdown";

import { PanelHeader } from "@/app/layout/AppHeader";
import { useDeleteConfirmStore } from "@/shared/components/deleteConfirmStore";
import { showErrorToast, showSuccessToast } from "@/shared/toast/showToast";
import { useChatModeStore } from "@/features/chat/modeStore";
import { useLlmSettingsStore } from "@/features/llm/llmSettingsStore";
import { useRagSettingsStore } from "@/features/rag/ragSettingsStore";
import { useSelectedChatId } from "@/features/chats/store";
import { useElementHover } from "@/shared/hooks/useElementHover";
import { useTranslation } from "@/shared/i18n";
import { useChatDetailQuery, useDeleteMessageMutation, useSendMessageMutation } from "../hooks/useChat";
import { useComposerAutoResize } from "../hooks/useComposerAutoResize";
import { useComposerDraft } from "../hooks/useComposerDraft";
import { useComposerFocus } from "../hooks/useComposerFocus";
import {
  parseDecisionTreeGuidance,
  type DecisionTreeGuidance,
} from "../lib/decisionTreeGuidance";

function DecisionTreeGuidanceBlock({ guidance }: { guidance: DecisionTreeGuidance }) {
  const { t } = useTranslation();

  return (
    <section className="decision-tree-guidance" aria-label={t("chat.decisionTree.title")}>
      <header className="decision-tree-guidance__header">
        <i className="pi pi-sitemap decision-tree-guidance__icon" aria-hidden="true" />
        <div>
          <p className="decision-tree-guidance__label">{t("chat.decisionTree.title")}</p>
          <p className="decision-tree-guidance__meta">
            {guidance.title}
            {guidance.section ? ` · ${guidance.section}` : ""}
          </p>
        </div>
      </header>
      <div className="decision-tree-guidance__content">
        <ReactMarkdown>{guidance.guidance}</ReactMarkdown>
      </div>
    </section>
  );
}

function MessageBubble({
  messageId,
  role,
  content,
  metadata,
  onDelete,
  isDeleteDisabled,
  hoverResetKey,
}: {
  messageId: number;
  role: "user" | "assistant" | "system";
  content: string;
  metadata?: Record<string, unknown>;
  onDelete: (messageId: number) => void;
  isDeleteDisabled: boolean;
  hoverResetKey: unknown;
}) {
  const { t } = useTranslation();
  const { ref, hovered, hoverProps } = useElementHover([hoverResetKey]);
  const decisionTreeGuidance =
    role === "assistant" && metadata ? parseDecisionTreeGuidance(metadata) : null;
  const label =
    role === "user"
      ? t("roles.user")
      : role === "assistant"
        ? t("roles.assistant")
        : t("roles.system");

  const showActions = role === "user" || role === "assistant";

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      showSuccessToast(t("chat.copyMessageSuccess"), t("common.ok"));
    } catch {
      showErrorToast(t("chat.copyMessageFailed"), t("errors.sseTitle"));
    }
  };

  const bubble = (
    <article
      ref={ref}
      {...hoverProps}
      className={`chat-message${
        role === "user" ? " chat-message--user" : role === "assistant" ? " chat-message--assistant" : ""
      }`}
    >
      {showActions ? (
        <div
          className={`chat-message__actions${
            hovered ? " chat-message__actions--visible" : ""
          }`}
        >
          <button
            type="button"
            className="chat-message__action chat-message__action--copy"
            aria-label={t("chat.copyMessage")}
            onClick={() => void handleCopy()}
          >
            <i className="pi pi-copy" aria-hidden="true" />
          </button>
          <button
            type="button"
            className="chat-message__action chat-message__action--delete"
            aria-label={t("chat.deleteMessage")}
            disabled={isDeleteDisabled}
            onClick={() => onDelete(messageId)}
          >
            <i className="pi pi-trash" aria-hidden="true" />
          </button>
        </div>
      ) : null}
      <p className="chat-message__role">{label}</p>
      {decisionTreeGuidance ? <DecisionTreeGuidanceBlock guidance={decisionTreeGuidance} /> : null}
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
  const useCustomPrompt = useLlmSettingsStore((state) => state.use_custom_prompt ?? false);
  const [selectedChatId] = useSelectedChatId();
  const chatQuery = useChatDetailQuery(selectedChatId);
  const sendMutation = useSendMessageMutation(selectedChatId);
  const deleteMessageMutation = useDeleteMessageMutation(selectedChatId);
  const openDeleteConfirm = useDeleteConfirmStore((state) => state.open);
  const closeDeleteConfirm = useDeleteConfirmStore((state) => state.close);
  const setDeleteConfirmPending = useDeleteConfirmStore((state) => state.setPending);
  const isDeleteConfirmOpen = useDeleteConfirmStore((state) => state.request !== null);
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
        ? useCustomPrompt
          ? t("chat.placeholderLlm")
          : t("chat.placeholderLlmAviation")
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

        {chatQuery.data ? (
          <div className="chat-messages">
            {chatQuery.data.messages.map((message) => (
              <MessageBubble
                key={message.id}
                messageId={message.id}
                role={message.role}
                content={message.content}
                metadata={message.metadata}
                hoverResetKey={chatMode}
                onDelete={(messageId) => {
                  openDeleteConfirm({
                    header: t("chat.deleteMessageConfirmTitle"),
                    message: t("chat.deleteMessageConfirmMessage"),
                    confirmLabel: t("chat.deleteMessage"),
                    cancelLabel: t("common.cancel"),
                    onConfirm: () => {
                      setDeleteConfirmPending(true);
                      deleteMessageMutation.mutate(messageId, {
                        onSuccess: () => closeDeleteConfirm(),
                        onSettled: () => setDeleteConfirmPending(false),
                      });
                    },
                  });
                }}
                isDeleteDisabled={deleteMessageMutation.isPending || isDeleteConfirmOpen}
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
    </>
  );
}
