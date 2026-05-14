import { auth } from "@clerk/nextjs/server";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type FetchOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
};

export async function apiFetch<T>(path: string, options: FetchOptions = {}): Promise<T> {
  const { getToken } = await auth();
  const token = await getToken();

  const headers = new Headers(options.headers);
  headers.set("content-type", "application/json");
  if (token) headers.set("authorization", `Bearer ${token}`);

  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    cache: "no-store",
  });

  if (!res.ok) {
    let message = res.statusText || `Request failed with status ${res.status}`;
    const text = await res.text().catch(() => "");
    if (text) {
      try {
        const json = JSON.parse(text) as { detail?: unknown };
        const detail = json.detail;
        if (typeof detail === "string") {
          message = detail;
        } else if (Array.isArray(detail)) {
          // FastAPI validation errors come as [{loc, msg, type}, ...]
          message = detail
            .map((e) => {
              if (e && typeof e === "object" && "msg" in e) {
                return String((e as { msg: unknown }).msg);
              }
              return JSON.stringify(e);
            })
            .join("; ");
        } else if (detail !== undefined) {
          message = JSON.stringify(detail);
        } else {
          message = text;
        }
      } catch {
        message = text;
      }
    }
    throw new Error(message);
  }

  if (res.status === 204 || res.headers.get("content-length") === "0") {
    return undefined as T;
  }

  return (await res.json()) as T;
}
