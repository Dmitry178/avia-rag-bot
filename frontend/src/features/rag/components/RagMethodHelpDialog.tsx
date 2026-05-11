import { Button } from "primereact/button";
import { Dialog } from "primereact/dialog";

import { getRagMethodHelp } from "@/shared/i18n/ragMethods";
import { useTranslation } from "@/shared/i18n";
import type { RagMethodKey } from "../types";

type RagMethodHelpDialogProps = {
  method: RagMethodKey | null;
  onHide: () => void;
};

export function RagMethodHelpDialog({ method, onHide }: RagMethodHelpDialogProps) {
  const { t, locale } = useTranslation();

  if (method === null) {
    return null;
  }

  const help = getRagMethodHelp(locale, method);

  const footer = (
    <div className="rag-help-dialog__footer">
      <Button label={t("common.ok")} onClick={onHide} />
    </div>
  );

  return (
    <Dialog
      visible
      onHide={onHide}
      header={help.title}
      footer={footer}
      modal
      dismissableMask
      draggable={false}
      resizable={false}
      className="rag-help-dialog"
      style={{ width: "min(32rem, 92vw)" }}
      breakpoints={{ "960px": "92vw" }}
    >
      <p className="rag-help-dialog__description">{help.description}</p>
    </Dialog>
  );
}
