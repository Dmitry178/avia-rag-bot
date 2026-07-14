import { useCallback, useEffect, useRef, useState } from "react";

import { isPointerOverElement } from "@/shared/lib/pointerPosition";

export function useElementHover(resetDeps: readonly unknown[] = []) {
  const ref = useRef<HTMLElement>(null);
  const [hovered, setHovered] = useState(false);

  const syncHover = useCallback(() => {
    setHovered(isPointerOverElement(ref.current));
  }, []);

  useEffect(() => {
    syncHover();
  }, [syncHover, ...resetDeps]);

  return {
    ref,
    hovered,
    syncHover,
    hoverProps: {
      onMouseEnter: () => setHovered(true),
      onMouseLeave: () => setHovered(false),
    },
  };
}
