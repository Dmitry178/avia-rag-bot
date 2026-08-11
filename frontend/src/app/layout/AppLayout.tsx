import { AppHeader } from "./AppHeader";
import { TracePanelShell } from "./TracePanelShell";
import { ChatPanel } from "@/features/chat/components/ChatPanel";
import { useChatModeStore } from "@/features/chat/modeStore";
import { ChatSidebar } from "@/features/chats/components/ChatSidebar";
import { LlmParametersPanel } from "@/features/llm/components/LlmParametersPanel";
import { TracePanel } from "@/features/trace/components/TracePanel";
import { useTranslation } from "@/shared/i18n";

export function AppLayout() {
  const { t } = useTranslation();
  const chatMode = useChatModeStore((state) => state.mode);
  const tracePanelTitle = chatMode === "rag" ? t("panels.trace") : t("panels.parameters");
  const tracePanelIcon = chatMode === "rag" ? "pi pi-list" : "pi pi-sliders-h";

  return (
    <div className="app-shell">
      <AppHeader />

      <main className="app-main">
        <section className="app-panel app-panel--sidebar">
          <ChatSidebar />
        </section>

        <section className="app-panel app-panel--chat">
          <ChatPanel />
        </section>

        <TracePanelShell title={tracePanelTitle} icon={tracePanelIcon}>
          {chatMode === "rag" ? <TracePanel /> : <LlmParametersPanel />}
        </TracePanelShell>
      </main>
    </div>
  );
}
