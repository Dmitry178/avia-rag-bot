import { PanelHeader } from "@/app/layout/AppHeader";
import { useChatDetailQuery } from "@/features/chat/hooks/useChat";
import { useChatsQuery } from "@/features/chats/hooks/useChats";
import { useSelectedChatId } from "@/features/chats/store";
import { RagSettingsPanel } from "@/features/rag/components/RagSettingsPanel";
import { useHydrateRagSettings } from "@/features/rag/hooks/useHydrateRagSettings";
import { useTranslation } from "@/shared/i18n";
import { useMemo } from "react";
import { findLatestRagTrace } from "../lib/ragTrace";
import { RagTraceStream } from "./RagTraceStream";

export function TracePanel() {
  const { t } = useTranslation();
  const [selectedChatId] = useSelectedChatId();
  const chatsQuery = useChatsQuery();
  const chatQuery = useChatDetailQuery(selectedChatId);

  const selectedChatSummary =
    selectedChatId === null
      ? null
      : chatsQuery.data?.find((chat) => chat.id === selectedChatId) ?? null;

  useHydrateRagSettings(chatQuery.data ?? selectedChatSummary);

  const latestTrace = useMemo(
    () => findLatestRagTrace(chatQuery.data?.messages ?? []),
    [chatQuery.data?.messages],
  );

  return (
    <>
      <PanelHeader title={t("panels.trace")} />

      <div className="app-panel__body app-panel__body--trace">
        <RagSettingsPanel />

        <div className="trace-panel__stream">
          <RagTraceStream trace={latestTrace} />
        </div>
      </div>
    </>
  );
}
