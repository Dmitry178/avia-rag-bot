import { DeleteConfirmDialog } from "@/shared/components/DeleteConfirmDialog";
import { useDeleteConfirmStore } from "@/shared/components/deleteConfirmStore";

export function DeleteConfirmHost() {
  const request = useDeleteConfirmStore((state) => state.request);
  const isPending = useDeleteConfirmStore((state) => state.isPending);
  const close = useDeleteConfirmStore((state) => state.close);

  if (!request) {
    return null;
  }

  return (
    <DeleteConfirmDialog
      visible
      header={request.header}
      message={request.message}
      confirmLabel={request.confirmLabel}
      cancelLabel={request.cancelLabel}
      isPending={isPending}
      onHide={close}
      onConfirm={() => request?.onConfirm()}
    />
  );
}
