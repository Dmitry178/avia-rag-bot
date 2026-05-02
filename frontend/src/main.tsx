import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "@/app/App";
import { applyDocumentLocale, readStoredLocale } from "@/shared/i18n";
import { applyTheme, readStoredTheme } from "@/theme/applyTheme";

import "primeicons/primeicons.css";
import "primereact/resources/themes/lara-dark-blue/theme.css";
import "primereact/resources/primereact.min.css";
import "@/styles/global.css";

applyTheme(readStoredTheme());
applyDocumentLocale(readStoredLocale());

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
