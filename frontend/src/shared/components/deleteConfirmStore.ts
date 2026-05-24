import { create } from "zustand";

export type DeleteConfirmRequest = {
  header: string;
  message: string;
  confirmLabel: string;
  cancelLabel: string;
  onConfirm: () => void;
};

type DeleteConfirmStore = {
  request: DeleteConfirmRequest | null;
  isPending: boolean;
  open: (request: DeleteConfirmRequest) => void;
  close: () => void;
  setPending: (isPending: boolean) => void;
};

export const useDeleteConfirmStore = create<DeleteConfirmStore>((set) => ({
  request: null,
  isPending: false,
  open: (request) => set({ request, isPending: false }),
  close: () => set({ request: null, isPending: false }),
  setPending: (isPending) => set({ isPending }),
}));
