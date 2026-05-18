/**
 * Cross-check: hit each endpoint on both the Python `api/` and the TS `apps/api/`
 * with the same Clerk JWT, diff the JSON responses. Exit non-zero if any mismatch.
 *
 * Usage:
 *   PY_URL=http://localhost:8000 TS_URL=http://localhost:8002 \
 *   CLERK_TOKEN=$(./mint-test-token) \
 *   pnpm tsx scripts/cross-check-against-py.ts
 */

const PY_URL = process.env.PY_URL ?? "http://localhost:8000";
const TS_URL = process.env.TS_URL ?? "http://localhost:8002";
const TOKEN = process.env.CLERK_TOKEN;

if (!TOKEN) {
  console.error("CLERK_TOKEN env var is required.");
  process.exit(1);
}

interface CheckResult {
  endpoint: string;
  match: boolean;
  py: unknown;
  ts: unknown;
  diff?: string;
}

const checks: CheckResult[] = [];

async function fetchBoth(path: string, init: RequestInit = {}): Promise<{ py: any; ts: any }> {
  const headers = new Headers(init.headers);
  headers.set("authorization", `Bearer ${TOKEN}`);
  const [pyRes, tsRes] = await Promise.all([
    fetch(`${PY_URL}${path}`, { ...init, headers }),
    fetch(`${TS_URL}${path}`, { ...init, headers }),
  ]);
  return {
    py: { status: pyRes.status, body: await safeJson(pyRes) },
    ts: { status: tsRes.status, body: await safeJson(tsRes) },
  };
}

async function safeJson(res: Response): Promise<unknown> {
  const text = await res.text();
  if (!text) return null;
  try { return JSON.parse(text); } catch { return text; }
}

function eq(a: unknown, b: unknown): boolean {
  return JSON.stringify(a, sortKeys) === JSON.stringify(b, sortKeys);
}

function sortKeys(_key: string, val: unknown): unknown {
  if (val && typeof val === "object" && !Array.isArray(val)) {
    return Object.fromEntries(
      Object.entries(val as Record<string, unknown>).sort(([a], [b]) => a.localeCompare(b)),
    );
  }
  return val;
}

async function check(name: string, path: string, init: RequestInit = {}): Promise<void> {
  const { py, ts } = await fetchBoth(path, init);
  const match = eq(py, ts);
  checks.push({ endpoint: name, match, py, ts });
  console.log(`${match ? "✓" : "✗"} ${name}`);
  if (!match) {
    console.log("  PY:", JSON.stringify(py, null, 2));
    console.log("  TS:", JSON.stringify(ts, null, 2));
  }
}

await check("GET /healthz", "/healthz");
await check("GET /me", "/me");
await check("GET /chat/sessions", "/chat/sessions");

// Create a session in BOTH and compare the response shape (IDs will differ; just
// check structure).
const { py: pyCreate, ts: tsCreate } = await fetchBoth("/chat/sessions", { method: "POST" });
const pyKeys = pyCreate.body ? Object.keys(pyCreate.body).sort() : [];
const tsKeys = tsCreate.body ? Object.keys(tsCreate.body).sort() : [];
const shapeMatch = JSON.stringify(pyKeys) === JSON.stringify(tsKeys);
console.log(
  `${shapeMatch ? "✓" : "✗"} POST /chat/sessions (response shape)`,
  shapeMatch ? "" : `\n  PY keys: ${pyKeys}\n  TS keys: ${tsKeys}`,
);

const allMatched = checks.every((c) => c.match) && shapeMatch;
process.exit(allMatched ? 0 : 1);
