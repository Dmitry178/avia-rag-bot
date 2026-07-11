import { LOCALE_INTL_TAG, type Locale } from "@/shared/i18n";

export function createClientId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }

  return `client-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function parseApiDateTime(value: string): Date {
  if (/[Zz]$|[+-]\d{2}:\d{2}$/.test(value)) {
    return new Date(value);
  }

  // API stores UTC in SQLite; naive ISO strings must be parsed as UTC.
  return new Date(`${value}Z`);
}

export function formatDateTime(value: string, locale: Locale): string {
  return new Intl.DateTimeFormat(LOCALE_INTL_TAG[locale], {
    dateStyle: "short",
    timeStyle: "short",
  }).format(parseApiDateTime(value));
}
