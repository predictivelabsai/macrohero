import { describe, expect, it } from "vitest";
import { createServer } from "../../src/server.js";

describe("POST /chat/start", () => {
  it("returns 401 without auth", async () => {
    const app = createServer({
      env: {
        CLERK_ISSUER: "https://x.test",
        CLERK_JWKS_URL: "https://x.test/jwks.json",
      },
    });
    const res = await app.request("/chat/start", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ content: "hi" }),
    });
    expect(res.status).toBe(401);
  });

  it("returns 400 for missing content", async () => {
    const app = createServer({ skipAuth: true });
    const res = await app.request("/chat/start", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({}),
    });
    expect(res.status).toBe(400);
  });
});
