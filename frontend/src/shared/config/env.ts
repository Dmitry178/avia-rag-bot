/** Backend API origin without trailing slash (e.g. http://127.0.0.1:8000). */
const configuredApiBaseUrl =
  (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") ?? "";

/**
 * In Vite dev, use same-origin `/api` so the dev-server proxy avoids CORS.
 * Production builds use `VITE_API_URL` when set (empty = same-origin `/api` behind nginx).
 */
export const API_BASE_URL = import.meta.env.DEV ? "" : configuredApiBaseUrl;

export function apiUrl(path: string): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE_URL}${normalizedPath}`;
}
