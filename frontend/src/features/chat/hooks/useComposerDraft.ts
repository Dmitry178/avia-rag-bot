import { useCallback, useEffect, useRef, useState } from "react";

import {
  clearComposerDraft,
  readComposerDraft,
  writeComposerDraft,
} from "../composerDraftStorage";

export function useComposerDraft(chatId: number | null) {
  const [draft, setDraft] = useState("");
  const draftRef = useRef(draft);

  draftRef.current = draft;

  useEffect(() => {
    if (chatId === null) {
      setDraft("");
      return;
    }

    setDraft(readComposerDraft(chatId));

    return () => {
      writeComposerDraft(chatId, draftRef.current);
    };
  }, [chatId]);

  useEffect(() => {
    if (chatId === null) {
      return;
    }

    writeComposerDraft(chatId, draft);
  }, [chatId, draft]);

  useEffect(() => {
    const handleVisibilityChange = () => {
      if (chatId === null) {
        return;
      }

      if (document.visibilityState === "hidden") {
        writeComposerDraft(chatId, draftRef.current);
        return;
      }

      const storedDraft = readComposerDraft(chatId);

      if (storedDraft !== draftRef.current) {
        setDraft(storedDraft);
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => document.removeEventListener("visibilitychange", handleVisibilityChange);
  }, [chatId]);

  const clearDraft = useCallback(() => {
    if (chatId !== null) {
      clearComposerDraft(chatId);
    }

    setDraft("");
  }, [chatId]);

  return { draft, setDraft, clearDraft };
}
