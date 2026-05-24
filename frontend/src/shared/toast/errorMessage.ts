import { ApiError } from "@/shared/api/client";

function detailFromApiBody(body: unknown): string | null {
  if (typeof body !== "object" || body === null) {
    return null;
  }

  const record = body as Record<string, unknown>;
  const detail = record.detail;

  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }

  const extra = record.extra;
  if (typeof extra === "object" && extra !== null) {
    const extraBody = (extra as { body?: unknown }).body;
    if (typeof extraBody === "string" && extraBody.trim()) {
      return extraBody.slice(0, 300);
    }
  }

  return null;
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const fromBody = detailFromApiBody(error.body);
    if (fromBody && fromBody !== "Service error") {
      return fromBody;
    }

    if (error.message.trim()) {
      return error.message;
    }

    return fromBody ?? "Request failed";
  }

  if (error instanceof Error) {
    return error.message;
  }

  return String(error);
}
