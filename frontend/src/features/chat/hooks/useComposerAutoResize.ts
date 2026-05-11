import { type RefObject, useLayoutEffect, useRef } from "react";

const COMPOSER_MAX_ROWS = 5;

function readScrollHeight(textarea: HTMLTextAreaElement): number {
  textarea.style.height = "0px";
  return textarea.scrollHeight;
}

function measureMaxHeight(textarea: HTMLTextAreaElement): number {
  const saved = {
    value: textarea.value,
    rows: textarea.rows,
    height: textarea.style.height,
    overflowY: textarea.style.overflowY,
  };

  textarea.value = "x";
  textarea.rows = 1;
  textarea.style.overflowY = "hidden";
  const singleRowHeight = readScrollHeight(textarea);

  textarea.value = "x\nx";
  textarea.rows = 2;
  const lineStep = readScrollHeight(textarea) - singleRowHeight;
  const maxHeight = singleRowHeight + lineStep * (COMPOSER_MAX_ROWS - 1);

  textarea.value = saved.value;
  textarea.rows = saved.rows;
  textarea.style.height = saved.height;
  textarea.style.overflowY = saved.overflowY;

  return maxHeight;
}

function resizeComposer(textarea: HTMLTextAreaElement, maxHeight: number): void {
  textarea.style.overflowY = "hidden";
  const contentHeight = readScrollHeight(textarea);
  textarea.style.height = `${Math.min(contentHeight, maxHeight)}px`;
  textarea.style.overflowY = contentHeight > maxHeight ? "auto" : "hidden";
}

interface UseComposerAutoResizeOptions {
  textareaRef: RefObject<HTMLTextAreaElement | null>;
  value: string;
}

/** Keeps the composer at 1 row initially, grows up to 5 rows, then scrolls with padding intact. */
export function useComposerAutoResize({
  textareaRef,
  value,
}: UseComposerAutoResizeOptions): void {
  const maxHeightRef = useRef<number | null>(null);
  const lastWidthRef = useRef<number | null>(null);

  useLayoutEffect(() => {
    const textarea = textareaRef.current;

    if (!textarea) {
      return;
    }

    lastWidthRef.current = textarea.clientWidth;
    maxHeightRef.current = measureMaxHeight(textarea);
    resizeComposer(textarea, maxHeightRef.current);

    const observer = new ResizeObserver(() => {
      const width = textarea.clientWidth;

      if (lastWidthRef.current === width) {
        return;
      }

      lastWidthRef.current = width;
      maxHeightRef.current = measureMaxHeight(textarea);
      resizeComposer(textarea, maxHeightRef.current);
    });

    observer.observe(textarea);

    return () => observer.disconnect();
  }, [textareaRef]);

  useLayoutEffect(() => {
    const textarea = textareaRef.current;

    if (!textarea || maxHeightRef.current === null) {
      return;
    }

    resizeComposer(textarea, maxHeightRef.current);
  }, [textareaRef, value]);
}
