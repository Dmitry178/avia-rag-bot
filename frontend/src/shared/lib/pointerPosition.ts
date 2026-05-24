type PointerPosition = { x: number; y: number };

const pointer: PointerPosition = { x: 0, y: 0 };
let listening = false;

function ensurePointerListener(): void {
  if (listening || typeof window === "undefined") {
    return;
  }

  listening = true;
  window.addEventListener(
    "mousemove",
    (event) => {
      pointer.x = event.clientX;
      pointer.y = event.clientY;
    },
    { passive: true },
  );
}

export function isPointerOverElement(element: Element | null): boolean {
  if (!element) {
    return false;
  }

  const rect = element.getBoundingClientRect();

  return (
    pointer.x >= rect.left &&
    pointer.x <= rect.right &&
    pointer.y >= rect.top &&
    pointer.y <= rect.bottom
  );
}

export function findElementUnderPointer(selector: string): Element | null {
  ensurePointerListener();

  return document.elementFromPoint(pointer.x, pointer.y)?.closest(selector) ?? null;
}
