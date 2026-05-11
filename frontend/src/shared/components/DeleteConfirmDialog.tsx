import { Button } from "primereact/button";
import { Dialog } from "primereact/dialog";

type DeleteConfirmDialogProps = {
  visible: boolean;
  header: string;
  message: string;
  confirmLabel: string;
  cancelLabel: string;
  isPending: boolean;
  onHide: () => void;
  onConfirm: () => void;
};

export function DeleteConfirmDialog({
  visible,
  header,
  message,
  confirmLabel,
  cancelLabel,
  isPending,
  onHide,
  onConfirm,
}: DeleteConfirmDialogProps) {
  const footer = (
    <div className="chat-delete-dialog__footer">
      <Button label={cancelLabel} text disabled={isPending} onClick={onHide} />
      <Button
        label={confirmLabel}
        className="chat-delete-dialog__confirm"
        loading={isPending}
        onClick={onConfirm}
      />
    </div>
  );

  return (
    <Dialog
      visible={visible}
      onHide={() => {
        if (!isPending) {
          onHide();
        }
      }}
      header={header}
      footer={footer}
      modal
      dismissableMask
      draggable={false}
      resizable={false}
      className="chat-delete-dialog"
    >
      <p className="chat-delete-dialog__message">{message}</p>
    </Dialog>
  );
}
