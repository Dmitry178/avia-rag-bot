import { type RefObject, useCallback, useEffect, useRef } from "react";

import { useChatUiStore } from "@/features/chats/store";

interface UseComposerFocusOptions {
  textareaRef: RefObject<HTMLTextAreaElement | null>;
  selectedChatId: number | null;
  isComposerDisabled: boolean;
  isSendPending: boolean;
}

export function useComposerFocus({
  textareaRef,
  selectedChatId,
  isComposerDisabled,
  isSendPending,
}: UseComposerFocusOptions): void {
  const composerFocusNonce = useChatUiStore((state) => state.composerFocusNonce);
  const pendingChatIdRef = useRef<number | null>(null);
  const wasSendPendingRef = useRef(false);

  const focusComposer = useCallback(() => {
    const textarea = textareaRef.current;

    if (!textarea || textarea.disabled) {
      return;
    }

    textarea.focus();
  }, [textareaRef]);

  useEffect(() => {
    if (isComposerDisabled) {
      return;
    }

    const frameId = requestAnimationFrame(focusComposer);
    return () => cancelAnimationFrame(frameId);
  }, [selectedChatId, composerFocusNonce, isComposerDisabled, focusComposer]);

  useEffect(() => {
    if (isSendPending) {
      if (!wasSendPendingRef.current) {
        pendingChatIdRef.current = selectedChatId;
      }

      wasSendPendingRef.current = true;
      return;
    }

    if (
      wasSendPendingRef.current &&
      pendingChatIdRef.current === selectedChatId &&
      !isComposerDisabled
    ) {
      const frameId = requestAnimationFrame(focusComposer);
      wasSendPendingRef.current = false;
      pendingChatIdRef.current = null;
      return () => cancelAnimationFrame(frameId);
    }

    wasSendPendingRef.current = false;
  }, [isSendPending, selectedChatId, isComposerDisabled, focusComposer]);
}
