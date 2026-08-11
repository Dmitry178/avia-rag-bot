import { Button } from "primereact/button";
import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

import { useTranslation } from "@/shared/i18n";
import { useMediaQuery } from "@/shared/hooks/useMediaQuery";

const TRACE_PANEL_FLOATING_BREAKPOINT = "(max-width: 1100px)";

interface TracePanelLayoutContextValue {
  isFloating: boolean;
  onClose: () => void;
}

const TracePanelLayoutContext = createContext<TracePanelLayoutContextValue | null>(
  null,
);

interface TracePanelShellProps {
  title: string;
  icon: string;
  children: ReactNode;
}

export function TracePanelShell({ title, icon, children }: TracePanelShellProps) {
  const { t } = useTranslation();
  const isFloating = useMediaQuery(TRACE_PANEL_FLOATING_BREAKPOINT);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    if (!isFloating) {
      setIsOpen(false);
    }
  }, [isFloating]);

  useEffect(() => {
    if (!isFloating || !isOpen) {
      return;
    }

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsOpen(false);
      }
    };

    document.addEventListener("keydown", onKeyDown);

    return () => document.removeEventListener("keydown", onKeyDown);
  }, [isFloating, isOpen]);

  if (!isFloating) {
    return <section className="app-panel app-panel--trace">{children}</section>;
  }

  return (
    <TracePanelLayoutContext.Provider
      value={{ isFloating: true, onClose: () => setIsOpen(false) }}
    >
      {!isOpen ? (
        <button
          type="button"
          className="trace-panel-toggle"
          onClick={() => setIsOpen(true)}
          aria-expanded={false}
          aria-label={title}
        >
          <i className={icon} aria-hidden="true" />
          <span className="trace-panel-toggle__label">{title}</span>
        </button>
      ) : (
        <>
          <button
            type="button"
            className="trace-panel-floating__backdrop"
            aria-label={t("panels.close")}
            onClick={() => setIsOpen(false)}
          />
          <section className="app-panel app-panel--trace app-panel--trace-floating">
            {children}
          </section>
        </>
      )}
    </TracePanelLayoutContext.Provider>
  );
}

export function useTracePanelCloseAction(): ReactNode {
  const layout = useContext(TracePanelLayoutContext);
  const { t } = useTranslation();

  if (!layout?.isFloating) {
    return undefined;
  }

  return (
    <Button
      type="button"
      icon="pi pi-times"
      rounded
      text
      size="small"
      severity="secondary"
      onClick={layout.onClose}
      aria-label={t("panels.close")}
    />
  );
}
