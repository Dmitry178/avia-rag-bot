const STORAGE_KEY = "avia-bot.composer-drafts";

type DraftsByChatId = Record<string, string>;

function readDrafts(): DraftsByChatId {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);

    if (!raw) {
      return {};
    }

    const parsed = JSON.parse(raw) as unknown;

    if (!parsed || typeof parsed !== "object") {
      return {};
    }

    return parsed as DraftsByChatId;
  } catch {
    return {};
  }
}

function writeDrafts(drafts: DraftsByChatId): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(drafts));
}

export function readComposerDraft(chatId: number): string {
  return readDrafts()[String(chatId)] ?? "";
}

export function writeComposerDraft(chatId: number, draft: string): void {
  const drafts = readDrafts();
  const key = String(chatId);

  if (draft === "") {
    delete drafts[key];
  } else {
    drafts[key] = draft;
  }

  writeDrafts(drafts);
}

export function clearComposerDraft(chatId: number): void {
  writeComposerDraft(chatId, "");
}
