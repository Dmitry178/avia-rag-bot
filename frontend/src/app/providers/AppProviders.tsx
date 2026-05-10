import { useEffect } from "react";
import { PrimeReactProvider } from "primereact/api";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { applyTheme, resolveTheme } from "@/theme/applyTheme";
import { useThemeStore } from "@/theme/store";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

interface AppProvidersProps {
  children: React.ReactNode;
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
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </PrimeReactProvider>
  );
}
