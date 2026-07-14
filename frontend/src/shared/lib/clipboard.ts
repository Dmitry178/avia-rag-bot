/**
 * Copy text via a hidden textarea (synchronous, for use inside a click handler).
 */
function copyViaExecCommand(text: string): void {
  const activeElement = document.activeElement;

  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.left = "-9999px";
  textarea.style.top = "0";
  textarea.style.opacity = "0";
  textarea.style.pointerEvents = "none";
  document.body.appendChild(textarea);
  textarea.focus({ preventScroll: true });
  textarea.select();
  textarea.setSelectionRange(0, text.length);

  try {
    if (!document.execCommand("copy")) {
      throw new Error("execCommand('copy') returned false");
    }
  } finally {
    document.body.removeChild(textarea);

    if (activeElement instanceof HTMLElement) {
      activeElement.focus({ preventScroll: true });
    }
  }
}

/**
 * Copy text to the system clipboard.
 *
 * Prefers the async Clipboard API. Falls back to execCommand when the API is
 * unavailable or rejects the write (e.g. non-secure context).
 */
export function copyToClipboard(text: string): Promise<void> {
  if (navigator.clipboard?.writeText) {
    return navigator.clipboard.writeText(text).catch(() => {
      copyViaExecCommand(text);
    });
  }

  return Promise.resolve(copyViaExecCommand(text));
}
