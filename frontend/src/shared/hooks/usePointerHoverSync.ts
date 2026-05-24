import { useEffect, useRef } from "react";

import { findElementUnderPointer } from "@/shared/lib/pointerPosition";

interface UsePointerHoverSyncOptions<T> {
  resetDeps: readonly unknown[];
  selector: string;
  getId: (element: Element) => T | null;
  onSync: (id: T | null) => void;
}

export function usePointerHoverSync<T>({
  resetDeps,
  selector,
  getId,
  onSync,
}: UsePointerHoverSyncOptions<T>): void {
  const getIdRef = useRef(getId);
  getIdRef.current = getId;

  useEffect(() => {
    const match = findElementUnderPointer(selector);
    onSync(match ? getIdRef.current(match) : null);
  }, [onSync, selector, ...resetDeps]);
}
