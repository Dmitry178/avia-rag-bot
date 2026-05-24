import { useEffect } from "react";
import { PrimeReactProvider } from "primereact/api";
import { QueryClientProvider } from "@tanstack/react-query";

import { useChatEvents } from "@/features/chats/hooks/useChatEvents";
import { createAppQueryClient } from "@/shared/api/queryClient";
import { DeleteConfirmHost } from "@/shared/components/DeleteConfirmHost";
import { AppToast } from "@/shared/components/AppToast";
import { applyTheme, resolveTheme } from "@/theme/applyTheme";
import { useThemeStore } from "@/theme/store";

const queryClient = createAppQueryClient();

interface AppProvidersProps {
  children: React.ReactNode;
}

function ChatEventsBridge() {
  useChatEvents();
  return null;
}

export function AppProviders({ children }: AppProvidersProps) {
  const themePreference = useThemeStore((state) => state.theme);

  useEffect(() => {
    applyTheme(resolveTheme(themePreference));
  }, [themePreference]);

  useEffect(() => {
    if (themePreference !== "system") {
      return;
    }

    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    const onSystemThemeChange = () => applyTheme(resolveTheme("system"));

    mediaQuery.addEventListener("change", onSystemThemeChange);

    return () => mediaQuery.removeEventListener("change", onSystemThemeChange);
  }, [themePreference]);

  return (
    <PrimeReactProvider value={{ ripple: true }}>
      <QueryClientProvider client={queryClient}>
        <AppToast />
        <DeleteConfirmHost />
        <ChatEventsBridge />
        {children}
      </QueryClientProvider>
    </PrimeReactProvider>
  );
}
