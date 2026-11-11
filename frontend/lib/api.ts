"use client";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");
const TOKEN_KEY = "kasauti_token";

export const tokenStore = {
  get: () => (typeof window === "undefined" ? null : window.localStorage.getItem(TOKEN_KEY)),
  set: (t: string) => window.localStorage.setItem(TOKEN_KEY, t),
  clear: () => window.localStorage.removeItem(TOKEN_KEY),
};

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

function detailToMessage(detail: unknown, fallback: string): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    // FastAPI validation errors: [{loc: [...], msg: "..."}]
    return detail.map((d: { loc?: unknown[]; msg?: string }) => `${(d.loc || []).slice(1).join(".")}: ${d.msg}`).join("; ");
  }
  return fallback;
}

export function authHeaders(extra?: HeadersInit): HeadersInit {
  const t = tokenStore.get();
  return { ...(extra || {}), ...(t ? { Authorization: `Bearer ${t}` } : {}) };
}

function onUnauthorized() {
  tokenStore.clear();
  if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login") && !window.location.pathname.startsWith("/signup")) {
    window.location.href = "/login";
  }
}

export async function api<T = unknown>(path: string, opts: { method?: string; body?: unknown; form?: FormData } = {}): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      method: opts.method || (opts.body || opts.form ? "POST" : "GET"),
      headers: authHeaders(opts.form ? undefined : opts.body ? { "Content-Type": "application/json" } : undefined),
      body: opts.form ?? (opts.body ? JSON.stringify(opts.body) : undefined),
    });
  } catch {
    throw new ApiError(0, `Cannot reach the server at ${API_URL}. Is the backend running?`);
  }
  if (res.status === 401 && !path.startsWith("/auth/")) {
    onUnauthorized();
    throw new ApiError(401, "Session expired. Please log in again.");
  }
  if (!res.ok) {
    let detail: unknown;
    try {
      detail = (await res.json()).detail;
    } catch {}
    throw new ApiError(res.status, detailToMessage(detail, `Request failed (${res.status})`));
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export async function fetchBlob(path: string): Promise<Blob> {
  const res = await fetch(`${API_URL}${path}`, { headers: authHeaders() });
  if (res.status === 401) onUnauthorized();
  if (!res.ok) {
    let msg = `Request failed (${res.status})`;
    try {
      msg = detailToMessage((await res.json()).detail, msg);
    } catch {}
    throw new ApiError(res.status, msg);
  }
  return res.blob();
}

// ---- SSE chat (EventSource can't POST or send auth headers, so parse the stream by hand)
export type AgentEvent =
  | { type: "text"; delta: string }
  | { type: "tool_call"; name: string; input: Record<string, unknown> }
  | { type: "tool_result"; name: string; result: unknown }
  | { type: "pending_action"; id: string; summary: string }
  | { type: "error"; message: string }
  | { type: "done" };

export async function streamChat(messages: { role: "user" | "assistant"; content: string }[], onEvent: (e: AgentEvent) => void, signal?: AbortSignal) {
  const res = await fetch(`${API_URL}/agent/chat`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ messages }),
    signal,
  });
  if (res.status === 401) return onUnauthorized();
  if (!res.ok || !res.body) {
    let msg = `Request failed (${res.status})`;
    try {
      msg = detailToMessage((await res.json()).detail, msg);
    } catch {}
    throw new ApiError(res.status, msg);
  }
  const reader = res.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    let i: number;
    while ((i = buf.indexOf("\n\n")) >= 0) {
      const frame = buf.slice(0, i);
      buf = buf.slice(i + 2);
      if (frame.startsWith("data: ")) {
        try {
          onEvent(JSON.parse(frame.slice(6)) as AgentEvent);
        } catch {}
      }
    }
  }
}
