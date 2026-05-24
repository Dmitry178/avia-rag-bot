import type { Toast } from "primereact/toast";
import type { RefObject } from "react";

let toastRef: RefObject<Toast | null> | null = null;

export function registerAppToast(ref: RefObject<Toast | null>) {
  toastRef = ref;
}

export function showErrorToast(detail: string, summary: string) {
  toastRef?.current?.show({
    severity: "error",
    summary,
    detail,
    life: 10_000,
  });
}

export function showSuccessToast(detail: string, summary: string) {
  toastRef?.current?.show({
    severity: "success",
    summary,
    detail,
    life: 3000,
  });
}
