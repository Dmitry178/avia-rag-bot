import { MutationCache, QueryCache, QueryClient } from "@tanstack/react-query";

import { useI18nStore } from "@/shared/i18n/store";
import { errorMessage } from "@/shared/toast/errorMessage";
import { showErrorToast } from "@/shared/toast/showToast";

function t(key: string): string {
  return useI18nStore.getState().t(key);
}

function mutationErrorSummary(mutationKey: readonly unknown[] | undefined): string {
  const root = mutationKey?.[0];

  switch (root) {
    case "sendMessage":
      return t("errors.sendMessage");
    case "deleteMessage":
      return t("errors.deleteMessage");
    case "createChat":
      return t("errors.createChat");
    case "deleteChat":
      return t("errors.deleteChat");
    case "updateChatSettings":
      return t("errors.updateChatSettings");
    default:
      return t("errors.sseTitle");
  }
}

function queryErrorSummary(queryKey: readonly unknown[]): string {
  if (queryKey[0] === "chats") {
    return t("errors.loadChats");
  }

  if (queryKey[0] === "chat" && typeof queryKey[1] === "number") {
    return t("errors.loadChat");
  }

  return t("errors.sseTitle");
}

export function createAppQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        retry: 1,
        refetchOnWindowFocus: false,
      },
    },
    queryCache: new QueryCache({
      onError: (error, query) => {
        showErrorToast(errorMessage(error), queryErrorSummary(query.queryKey));
      },
    }),
    mutationCache: new MutationCache({
      onError: (error, _variables, _context, mutation) => {
        showErrorToast(errorMessage(error), mutationErrorSummary(mutation.options.mutationKey));
      },
    }),
  });
}
