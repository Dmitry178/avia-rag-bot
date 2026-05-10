export function readPersistedState<T extends Record<string, unknown>>(
  storageKey: string,
): Partial<T> | null {
  try {
    const raw = localStorage.getItem(storageKey);

    if (!raw) {
      return null;
    }

    const parsed = JSON.parse(raw) as { state?: T };

    return parsed.state ?? null;
  } catch {
    return null;
  }
}
