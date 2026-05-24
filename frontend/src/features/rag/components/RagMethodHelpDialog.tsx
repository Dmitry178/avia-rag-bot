import { Button } from "primereact/button";

import { AppModal } from "@/shared/components/AppModal";
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
    <AppModal
      visible
      title={help.title}
      footer={footer}
      className="rag-help-dialog"
      onHide={onHide}
    >
      <p className="rag-help-dialog__description">{help.description}</p>
    </AppModal>
  );
}
