// Small fetch wrapper for the Smart Engineer API (proxied under /api, same origin).
// The session itself is an HttpOnly cookie the browser handles; this module only
// keeps the CSRF token (returned by login and /auth/me) in memory and sends it on
// state-changing requests.
import { messageForCode } from "./messages";

export class ApiError extends Error {
  status: number;
  code: string;
  details: unknown[];

  constructor(status: number, code: string, details: unknown[] = []) {
    super(code);
    this.status = status;
    this.code = code;
    this.details = details;
  }

  get userMessage(): string {
    return messageForCode(this.code);
  }
}

let csrfToken: string | null = null;

export function setCsrfToken(token: string | null): void {
  csrfToken = token;
}

export function toApiError(error: unknown): ApiError {
  return error instanceof ApiError ? error : new ApiError(0, "network_error");
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = {};
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  if (method !== "GET" && csrfToken) {
    headers["X-CSRF-Token"] = csrfToken;
  }

  let response: Response;
  try {
    response = await fetch(`/api/v1${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      credentials: "same-origin",
    });
  } catch {
    throw new ApiError(0, "network_error");
  }

  if (response.status === 204) {
    return undefined as T;
  }

  let data: unknown = null;
  try {
    data = await response.json();
  } catch {
    // Non-JSON body (for example a proxy error page): handled below.
  }

  if (!response.ok) {
    const envelope = data as { error?: { code?: unknown; details?: unknown } } | null;
    const code =
      typeof envelope?.error?.code === "string"
        ? envelope.error.code
        : `http_${response.status}`;
    const details = Array.isArray(envelope?.error?.details) ? envelope.error.details : [];
    throw new ApiError(response.status, code, details);
  }
  return data as T;
}

export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body ?? {}),
  patch: <T>(path: string, body: unknown) => request<T>("PATCH", path, body),
  put: <T>(path: string, body: unknown) => request<T>("PUT", path, body),
  delete: <T>(path: string) => request<T>("DELETE", path),
};
