import { AppHeader } from "./AppHeader";
import { ChatPanel } from "@/features/chat/components/ChatPanel";
import { useChatModeStore } from "@/features/chat/modeStore";
import { ChatSidebar } from "@/features/chats/components/ChatSidebar";
import { LlmParametersPanel } from "@/features/llm/components/LlmParametersPanel";
import { TracePanel } from "@/features/trace/components/TracePanel";

export function AppLayout() {
  const chatMode = useChatModeStore((state) => state.mode);

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

        {chatMode === "rag" ? (
          <section className="app-panel app-panel--trace">
            <TracePanel />
          </section>
        ) : (
          <section className="app-panel app-panel--trace">
            <LlmParametersPanel />
          </section>
        )}
      </main>
    </div>
  );
}
