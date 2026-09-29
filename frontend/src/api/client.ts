import type { Session } from "./types";

const SESSION_KEY = "claimshub.session";

/** Error from the API, in the one format every endpoint uses. */
export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public correlationId: string | null,
    public details: { field: string; message: string }[] = [],
  ) {
    super(message);
  }

  /** Text for the user, with the correlation ID so support can find the logs. */
  describe(): string {
    const fields = this.details.map((d) => `${d.field || "request"}: ${d.message}`).join("; ");
    const ref = this.correlationId ? ` (ref ${this.correlationId})` : "";
    return `${this.message}${fields ? ` — ${fields}` : ""}${ref}`;
  }
}

export function loadSession(): Session | null {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY);
    if (!raw) return null;
    const s = JSON.parse(raw) as Session;
    return s.expires_at > Date.now() ? s : null;
  } catch {
    return null;
  }
}

export function saveSession(s: Session | null): void {
  try {
    if (s) sessionStorage.setItem(SESSION_KEY, JSON.stringify(s));
    else sessionStorage.removeItem(SESSION_KEY);
  } catch {
    /* storage blocked: session lives in memory only */
  }
}

let onUnauthorized: () => void = () => {};
export function setUnauthorizedHandler(fn: () => void): void {
  onUnauthorized = fn;
}

export function newCorrelationId(): string {
  return crypto.randomUUID().replace(/-/g, "");
}

type Query = Record<string, string | number | undefined | null>;

export async function api<T>(
  path: string,
  options: { method?: string; body?: unknown; query?: Query; headers?: Record<string, string> } = {},
): Promise<T> {
  const url = new URL(`/api/v1${path}`, window.location.origin);
  for (const [k, v] of Object.entries(options.query ?? {})) {
    if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, String(v));
  }
  const session = loadSession();
  const headers: Record<string, string> = {
    "X-Correlation-ID": newCorrelationId(),
    ...(options.body !== undefined ? { "Content-Type": "application/json" } : {}),
    ...(session ? { Authorization: `Bearer ${session.access_token}` } : {}),
    ...options.headers,
  };

  let res: Response;
  try {
    res = await fetch(url, {
      method: options.method ?? "GET",
      headers,
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    });
  } catch {
    throw new ApiError(0, "NETWORK", "Cannot reach the server", headers["X-Correlation-ID"]);
  }

  if (res.status === 401 && session) onUnauthorized();
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) {
    throw new ApiError(
      res.status,
      data?.code ?? "HTTP_ERROR",
      data?.message ?? `Request failed (${res.status})`,
      data?.correlation_id ?? res.headers.get("X-Correlation-ID"),
      data?.details ?? [],
    );
  }
  return data as T;
}
