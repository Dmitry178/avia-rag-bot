import { useEffect, type ReactNode } from "react";
import { createPortal } from "react-dom";

type AppModalProps = {
  visible: boolean;
  title: string;
  footer?: ReactNode;
  onHide: () => void;
  children: ReactNode;
  className?: string;
  dismissableMask?: boolean;
};

export function AppModal({
  visible,
  title,
  footer,
  onHide,
  children,
  className,
  dismissableMask = true,
}: AppModalProps) {
  useEffect(() => {
    if (!visible) {
      return;
    }

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && dismissableMask) {
        onHide();
      }
    };

    document.addEventListener("keydown", onKeyDown);

    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [visible, onHide, dismissableMask]);

  if (!visible) {
    return null;
  }

  const rootClassName = ["app-modal", className].filter(Boolean).join(" ");

  const backdrop = dismissableMask ? (
    <button type="button" className="app-modal__backdrop" aria-label="Close" onClick={onHide} />
  ) : (
    <div className="app-modal__backdrop" aria-hidden="true" />
  );

  return createPortal(
    <div className={rootClassName}>
      {backdrop}
      <div className="app-modal__panel" role="dialog" aria-modal="true" aria-labelledby="app-modal-title">
        <header className="app-modal__header">
          <h2 id="app-modal-title" className="app-modal__title">
            {title}
          </h2>
        </header>
        <div className="app-modal__body">{children}</div>
        {footer ? <footer className="app-modal__footer">{footer}</footer> : null}
      </div>
    </div>,
    document.body,
  );
}
